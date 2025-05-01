# D:\3xDigital\app\models\database.py
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
    ShippingAddress: Representa o endereço de entrega de um pedido.
    RefreshToken: Representa um token de atualização (refresh token) usado para gerar novos access tokens.
    UserAddress: Representa o endereço de um usuário.
    TempCart: Representa um carrinho temporário para usuários não autenticados.
    TempCartItem: Representa um item no carrinho temporário.
    ProductAffiliate: Representa a relação entre um afiliado e um produto específico.

Functions:
    create_database(db_url: str) -> None:
        Cria o schema do banco de dados assíncrono, se não existir.

    get_async_engine(db_url: str):
        Retorna o motor assíncrono configurado para o banco de dados.

    get_session_maker(engine):
        Retorna o criador de sessões assíncronas para o banco de dados.
"""

import enum
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Enum, DateTime, ForeignKey, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base, composite
from sqlalchemy.ext.hybrid import hybrid_property
from app.config.settings import TIMEZONE

Base = declarative_base()

# A classe AffiliateBalance é definida em finance_models.py mas é referenciada aqui
AffiliateBalance = None  # Será definida externamente

# ========== Declaramos nossas Entidades (Models) como antes: ==========

class UserAddress(Base):
    """
    Representa o endereço de um usuário.

    Attributes:
        id (int): ID único do endereço
        user_id (int): ID do usuário associado
        street (str): Nome da rua
        number (str): Número do endereço
        complement (str): Complemento do endereço
        neighborhood (str): Bairro
        city (str): Cidade
        state (str): Estado
        zip_code (str): CEP
        created_at (datetime): Data de criação do registro
        updated_at (datetime): Data da última atualização
    """
    __tablename__ = 'user_addresses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    street = Column(String(255), nullable=False)
    number = Column(String(20), nullable=False)
    complement = Column(String(255), nullable=True)
    neighborhood = Column(String(255), nullable=True)
    city = Column(String(255), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="addresses")


class User(Base):
    """
    Representa um usuário no sistema.

    Attributes:
        id (int): ID único do usuário.
        name (str): Nome do usuário.
        email (str): Email do usuário, único.
        cpf (str): CPF do usuário, único.
        password_hash (str): Hash da senha do usuário.
        role (Enum): Papel do usuário (admin, manager, affiliate, user).
        phone (str): Número de telefone do usuário.
        active (bool): Indica se o usuário está ativo no sistema.
        deactivation_reason (str): Razão da desativação da conta.
        deletion_requested (bool): Indica se o usuário solicitou a exclusão da conta.
        deletion_request_date (datetime): Data da solicitação de exclusão da conta.
        notification_preferences (dict): Preferências de notificação do usuário.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    cpf = Column(String(11), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'manager', 'affiliate', 'user', name='user_roles'), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    active = Column(Boolean, default=True)
    deactivation_reason = Column(String(255), nullable=True)
    deletion_requested = Column(Boolean, default=False)
    deletion_request_date = Column(DateTime, nullable=True)
    _notification_preferences = Column("notification_preferences", Text, nullable=True)  # Armazena JSON

    orders = relationship("Order", back_populates="user")
    affiliate = relationship("Affiliate", uselist=False, back_populates="user")
    payments = relationship("Payment", order_by="Payment.id", back_populates="user")
    logs = relationship("Log", order_by="Log.id", back_populates="user")
    api_tokens = relationship("APIToken", order_by="APIToken.id", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")

    @property
    def notification_preferences(self) -> dict:
        """
        Desserializa as preferências de notificação do formato JSON.
        
        Returns:
            dict: Preferências de notificação do usuário
        """
        if self._notification_preferences:
            return json.loads(self._notification_preferences)
        return {}
        
    @notification_preferences.setter
    def notification_preferences(self, value: dict):
        """
        Serializa as preferências de notificação para JSON antes de salvar.
        
        Args:
            value (dict): Novas preferências de notificação
        """
        if value is not None:
            self._notification_preferences = json.dumps(value)
        else:
            self._notification_preferences = None

    @property
    def is_active(self):
        """
        Propriedade que retorna se o usuário está ativo ou não.
        """
        return self.active


class Category(Base):
    """
    Representa uma categoria de produtos.

    Attributes:
        id (int): ID único da categoria.
        name (str): Nome da categoria.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

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
        image_url (str, opcional): URL externa da imagem do produto (obsoleto).
        image_path (str, opcional): Caminho relativo do arquivo de imagem do produto no servidor.
        has_custom_commission (bool): Indica se o produto tem comissão personalizada.
        commission_type (str): Tipo de comissão ('percentage' ou 'fixed').
        commission_value (float): Valor da comissão (percentual ou fixo em reais).
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
    image_url = Column(String(255), nullable=True)  # Mantido para compatibilidade
    image_path = Column(String(255), nullable=True)  # Caminho relativo da imagem no servidor
    has_custom_commission = Column(Boolean, default=False)
    commission_type = Column(Enum('percentage', 'fixed', name='commission_types'), nullable=True)
    commission_value = Column(Float, nullable=True)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", order_by="OrderItem.id", back_populates="product")


class TempCart(Base):
    """
    Representa um carrinho temporário para usuários não autenticados.

    Attributes:
        id (int): ID único do carrinho temporário.
        session_id (str): ID da sessão do usuário, usado para identificar carrinhos anônimos.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'temp_carts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    
    items = relationship("TempCartItem", order_by="TempCartItem.id", back_populates="cart", cascade="all, delete-orphan")


class TempCartItem(Base):
    """
    Representa um item no carrinho temporário.

    Attributes:
        id (int): ID único do item no carrinho temporário.
        cart_id (int): ID do carrinho temporário associado.
        product_id (int): ID do produto associado.
        quantity (int): Quantidade do produto.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'temp_cart_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey('temp_carts.id', ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    
    cart = relationship("TempCart", back_populates="items")
    product = relationship("Product")


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
    status = Column(Enum('processing', 'shipped', 'delivered', 'returned', 'pending', 'completed', name='order_status'), nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", order_by="OrderItem.id", back_populates="order", cascade="all, delete-orphan", passive_deletes=True)
    sales = relationship("Sale", order_by="Sale.id", back_populates="order")
    shipping_address = relationship("ShippingAddress", uselist=False, back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """
    Representa os itens de um pedido.

    Attributes:
        id (int): ID único do item do pedido.
        order_id (int): ID do pedido associado.
        product_id (int): ID do produto associado.
        quantity (int): Quantidade do produto.
        price (float): Preço unitário do produto.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class ProductAffiliate(Base):
    """
    Representa a relação entre um afiliado e um produto específico.

    Attributes:
        id (int): ID único da relação.
        affiliate_id (int): ID do afiliado.
        product_id (int): ID do produto.
        commission_type (str): Tipo de comissão ('percentage' ou 'fixed').
        commission_value (float): Valor da comissão (percentual ou fixo em reais).
        status (str): Status da afiliação ('pending', 'approved', 'blocked').
        reason (str): Motivo da recusa (quando status='blocked').
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'product_affiliates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id', ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    commission_type = Column(Enum('percentage', 'fixed', name='product_commission_types'), nullable=False, default='percentage')
    commission_value = Column(Float, nullable=False)
    status = Column(
        Enum('pending', 'approved', 'blocked', name='product_affiliate_status'),
        nullable=False,
        default='pending'
    )
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    
    # Relacionamentos
    affiliate = relationship("Affiliate", backref="product_affiliations")
    product = relationship("Product", backref="affiliates")
    
    # Definimos uma constraint para que um afiliado não possa ser vinculado 
    # ao mesmo produto mais de uma vez
    __table_args__ = (
        UniqueConstraint('affiliate_id', 'product_id', name='unique_product_affiliate'),
    )


class Affiliate(Base):
    """
    Representa um afiliado no sistema.

    Attributes:
        id (int): ID único do afiliado.
        user_id (int): ID do usuário associado ao afiliado.
        referral_code (str): Código de referência do afiliado.
        commission_rate (float): Taxa de comissão global do afiliado.
        is_global_affiliate (bool): Indica se o afiliado pode promover todos os produtos.
        request_status (str): Status da solicitação de afiliação, podendo ser 'pending', 'approved' ou 'blocked'.
        reason (str): Motivo da recusa de solicitação, quando aplicável.
        payment_info (dict): Informações de pagamento do afiliado (banco, agência, conta, etc).
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'affiliates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referral_code = Column(String(255), nullable=False, unique=True)
    commission_rate = Column(Float, nullable=False)
    is_global_affiliate = Column(Boolean, default=False)
    _payment_info = Column("payment_info", Text, nullable=True)  # Renomeando para _payment_info
    request_status = Column(
        Enum('pending', 'approved', 'blocked', name='affiliate_status'),
        nullable=False,
        default='pending'
    )
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="affiliate")
    sales = relationship("Sale", order_by="Sale.id", back_populates="affiliate")
    balance = relationship("AffiliateBalance", uselist=False, back_populates="affiliate", cascade="all, delete-orphan")
    
    @property
    def payment_info(self):
        """
        Desserializa o campo payment_info de texto para dicionário.
        """
        if self._payment_info:
            return json.loads(self._payment_info)
        return None
    
    @payment_info.setter
    def payment_info(self, value):
        """
        Serializa o dicionário payment_info para texto ao salvar.
        """
        if value is not None:
            self._payment_info = json.dumps(value)
        else:
            self._payment_info = None


class Sale(Base):
    """
    Representa uma venda associada a um afiliado.

    Attributes:
        id (int): ID único da venda.
        affiliate_id (int): ID do afiliado associado à venda.
        order_id (int): ID do pedido associado à venda.
        product_id (int): ID do produto específico que gerou a comissão.
        commission (float): Comissão gerada pela venda.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    commission = Column(Float, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    affiliate = relationship("Affiliate", back_populates="sales")
    order = relationship("Order", back_populates="sales")
    product = relationship("Product")


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
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=TIMEZONE)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="logs")


class APIToken(Base):
    """
    Representa tokens de API associados a usuários.

    Attributes:
        id (int): ID único do token.
        service_name (str): Nome do serviço associado ao token.
        token (str): Valor do token.
        user_id (int): ID do usuário associado ao token.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'api_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(255), nullable=False)
    token = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="api_tokens")


class ShippingAddress(Base):
    """
    Representa o endereço de entrega de um pedido.

    Attributes:
        id (int): ID único do endereço.
        order_id (int): ID do pedido associado.
        street (str): Nome da rua.
        number (str): Número do endereço.
        complement (str): Complemento do endereço.
        neighborhood (str): Bairro.
        city (str): Cidade.
        state (str): Estado.
        zip_code (str): CEP.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'shipping_addresses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="CASCADE"), nullable=False, unique=True)
    street = Column(String(255), nullable=False)
    number = Column(String(20), nullable=False)
    complement = Column(String(255), nullable=True)
    neighborhood = Column(String(255), nullable=True)
    city = Column(String(255), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    order = relationship("Order", back_populates="shipping_address")


class RefreshToken(Base):
    """
    Representa um token de atualização (refresh token) usado para gerar novos access tokens.

    Attributes:
        id (int): ID único do token.
        token (str): Valor do token de atualização.
        user_id (int): ID do usuário associado ao token.
        expires_at (datetime): Data de expiração do token.
        is_revoked (bool): Indica se o token foi revogado.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização do registro.
    """
    __tablename__ = 'refresh_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(255), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_expired(self):
        """
        Verifica se o token está expirado.
        
        Returns:
            bool: True se o token estiver expirado, False caso contrário.
        """
        current_time = datetime.now(self.expires_at.tzinfo)
        return current_time > self.expires_at
    
    @property
    def is_valid(self):
        """
        Verifica se o token é válido (não expirado e não revogado).
        
        Returns:
            bool: True se o token for válido, False caso contrário.
        """
        return not (self.is_expired or self.is_revoked)


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

# Importação no final para evitar referência circular
from app.models.finance_models import AffiliateBalance
