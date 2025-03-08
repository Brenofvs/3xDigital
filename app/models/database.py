# D:\#3xDigital\app\models\database.py
"""
database.py

Este módulo define os modelos de dados (ORM) usando SQLAlchemy e os métodos para
criação e interação com o banco de dados de forma assíncrona.

Classes:
    User: Representa um usuário no sistema.
    Category: Representa uma categoria de produtos.
    Product: Representa um produto no sistema.
    Order: Representa um pedido realizado por um usuário.
    OrderItem: Representa os itens de um pedido.
    Affiliate: Representa um afiliado no sistema.
    Sale: Representa uma venda associada a um afiliado.
    Payment: Representa um pagamento realizado por um usuário.
    Log: Representa logs de ações de usuários.
    APIToken: Representa tokens de API associados a usuários.

Functions:
    create_database(db_url: str) -> None:
        Cria o schema do banco de dados assíncrono, se não existir.

    get_async_engine(db_url: str):
        Retorna o motor assíncrono configurado para o banco de dados.

    get_session_maker(engine):
        Retorna o criador de sessões assíncronas para o banco de dados.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Enum, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from app.config.settings import TIMEZONE

Base = declarative_base()

# ========== Declaramos nossas Entidades (Models) como antes: ==========

class User(Base):
    """
    Representa um usuário no sistema.

    Attributes:
        id (int): ID único do usuário.
        name (str): Nome do usuário.
        email (str): Email do usuário, único.
        password_hash (str): Hash da senha do usuário.
        role (Enum): Papel do usuário (admin, manager, affiliate).
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    cpf = Column(String(11), nullable=False, unique=True)  # Novo campo para CPF
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'manager', 'affiliate', 'user', name='user_roles'), nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    orders = relationship("Order", back_populates="user")
    affiliate = relationship("Affiliate", uselist=False, back_populates="user")
    payments = relationship("Payment", order_by="Payment.id", back_populates="user")
    logs = relationship("Log", order_by="Log.id", back_populates="user")
    api_tokens = relationship("APIToken", order_by="APIToken.id", back_populates="user")


class Category(Base):
    """
    Representa uma categoria de produtos.

    Attributes:
        id (int): ID único da categoria.
        name (str): Nome da categoria.
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

    products = relationship("Product", order_by="Product.id", back_populates="category")


class Product(Base):
    """
    Representa um produto no sistema.

    Attributes:
        id (int): ID único do produto.
        name (str): Nome do produto.
        description (str): Descrição do produto.
        price (float): Preço do produto.
        stock (int): Quantidade em estoque.
        category_id (int): ID da categoria associada.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
        image_url (str, opcional): URL da imagem do produto.
    """
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    image_url = Column(String(255), nullable=True)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", order_by="OrderItem.id", back_populates="product")


class Order(Base):
    """
    Representa um pedido realizado por um usuário.

    Attributes:
        id (int): ID único do pedido.
        user_id (int): ID do usuário associado ao pedido.
        status (Enum): Status do pedido (processing, shipped, delivered, returned).
        total (float): Valor total do pedido.
        created_at (datetime): Data de criação do pedido.
        updated_at (datetime): Data da última atualização do pedido.
    """
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    status = Column(Enum('processing', 'shipped', 'delivered', 'returned', name='order_status'), nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", order_by="OrderItem.id", back_populates="order", cascade="all, delete-orphan", passive_deletes=True)
    sales = relationship("Sale", order_by="Sale.id", back_populates="order")


class OrderItem(Base):
    """
    Representa os itens de um pedido.

    Attributes:
        id (int): ID único do item do pedido.
        order_id (int): ID do pedido associado.
        product_id (int): ID do produto associado.
        quantity (int): Quantidade do produto.
        price (float): Preço unitário do produto.
    """
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


# Trecho modificado de D:\#3xDigital\app\models\database.py

class Affiliate(Base):
    """
    Representa um afiliado no sistema.

    Attributes:
        id (int): ID único do afiliado.
        user_id (int): ID do usuário associado ao afiliado.
        referral_code (str): Código de referência do afiliado.
        commission_rate (float): Taxa de comissão do afiliado.
        request_status (str): Status da solicitação de afiliação, podendo ser 'pending', 'approved' ou 'blocked'.
    """
    __tablename__ = 'affiliates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referral_code = Column(String(255), nullable=False, unique=True)
    commission_rate = Column(Float, nullable=False)
    request_status = Column(
        Enum('pending', 'approved', 'blocked', name='affiliate_status'),
        nullable=False,
        default='pending'
    )

    user = relationship("User", back_populates="affiliate")
    sales = relationship("Sale", order_by="Sale.id", back_populates="affiliate")
    balance = relationship("AffiliateBalance", uselist=False, back_populates="affiliate", cascade="all, delete-orphan")



class Sale(Base):
    """
    Representa uma venda associada a um afiliado.

    Attributes:
        id (int): ID único da venda.
        affiliate_id (int): ID do afiliado associado à venda.
        order_id (int): ID do pedido associado à venda.
        commission (float): Comissão gerada pela venda.
    """
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    commission = Column(Float, nullable=False)

    affiliate = relationship("Affiliate", back_populates="sales")
    order = relationship("Order", back_populates="sales")


class Payment(Base):
    """
    Representa um pagamento realizado por um usuário.

    Attributes:
        id (int): ID único do pagamento.
        user_id (int): ID do usuário associado ao pagamento.
        amount (float): Valor do pagamento.
        status (Enum): Status do pagamento (pending, paid, failed).
        transaction_id (str): ID da transação, único.
        created_at (datetime): Data de criação do registro.
    """
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum('pending', 'paid', 'failed', name='payment_status'), nullable=False)
    transaction_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=TIMEZONE)

    user = relationship("User", back_populates="payments")


class Log(Base):
    """
    Representa logs de ações realizadas por um usuário.

    Attributes:
        id (int): ID único do log.
        user_id (int): ID do usuário associado ao log.
        action (str): Descrição da ação realizada.
        timestamp (datetime): Data e hora da ação.
    """
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=TIMEZONE)

    user = relationship("User", back_populates="logs")


class APIToken(Base):
    """
    Representa tokens de API associados a usuários.

    Attributes:
        id (int): ID único do token.
        service_name (str): Nome do serviço associado ao token.
        token (str): Valor do token.
        user_id (int): ID do usuário associado ao token.
    """
    __tablename__ = 'api_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(255), nullable=False)
    token = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="api_tokens")


# ========== Métodos para criação do banco de dados de forma assíncrona ==========

async def create_database(db_url: str = "sqlite+aiosqlite:///./3x_digital.db"):
    """
    Cria o schema no banco de dados assíncrono, se não existir.

    Args:
        db_url (str): URL do banco de dados. O padrão é um SQLite local.

    Returns:
        None
    """
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def get_async_engine(db_url: str = "sqlite+aiosqlite:///./3x_digital.db"):
    """
    Retorna o motor assíncrono configurado para o banco de dados.

    Args:
        db_url (str): URL do banco de dados. O padrão é um SQLite local.

    Returns:
        create_async_engine: Instância do motor assíncrono.
    """
    return create_async_engine(db_url, echo=False)


def get_session_maker(engine):
    """
    Retorna o criador de sessões assíncronas para o banco de dados.

    Args:
        engine: Instância do motor do banco de dados.

    Returns:
        async_sessionmaker: Criador de sessões assíncronas.
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False)
