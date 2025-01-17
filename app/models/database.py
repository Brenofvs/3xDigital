# D:\#3xDigital\app\models\database.py
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, Enum, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

# Import específico para assíncrono
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
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'manager', 'affiliate', name='user_roles'), nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    orders = relationship("Order", back_populates="user")
    affiliate = relationship("Affiliate", uselist=False, back_populates="user")
    payments = relationship("Payment", order_by="Payment.id", back_populates="user")
    logs = relationship("Log", order_by="Log.id", back_populates="user")
    api_tokens = relationship("APIToken", order_by="APIToken.id", back_populates="user")

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

    products = relationship("Product", order_by="Product.id", back_populates="category")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", order_by="OrderItem.id", back_populates="product")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum('processing', 'shipped', 'delivered', 'returned', name='order_status'), nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", order_by="OrderItem.id", back_populates="order")
    sales = relationship("Sale", order_by="Sale.id", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Affiliate(Base):
    __tablename__ = 'affiliates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referral_code = Column(String(255), nullable=False, unique=True)
    commission_rate = Column(Float, nullable=False)

    user = relationship("User", back_populates="affiliate")
    sales = relationship("Sale", order_by="Sale.id", back_populates="affiliate")

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    commission = Column(Float, nullable=False)

    affiliate = relationship("Affiliate", back_populates="sales")
    order = relationship("Order", back_populates="sales")

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum('pending', 'paid', 'failed', name='payment_status'), nullable=False)
    transaction_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=TIMEZONE)

    user = relationship("User", back_populates="payments")

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=TIMEZONE)

    user = relationship("User", back_populates="logs")

class APIToken(Base):
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
    """
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

def get_async_engine(db_url: str = "sqlite+aiosqlite:///./3x_digital.db"):
    return create_async_engine(db_url, echo=False)

def get_session_maker(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False)

