from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Enum, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'manager', 'affiliate', name='user_roles'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")

Category.products = relationship("Product", order_by=Product.id, back_populates="category")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum('processing', 'shipped', 'delivered', 'returned', name='order_status'), nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")

User.orders = relationship("Order", order_by=Order.id, back_populates="user")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

Order.items = relationship("OrderItem", order_by=OrderItem.id, back_populates="order")
Product.order_items = relationship("OrderItem", order_by=OrderItem.id, back_populates="product")

class Affiliate(Base):
    __tablename__ = 'affiliates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referral_code = Column(String(255), nullable=False, unique=True)
    commission_rate = Column(Float, nullable=False)

    user = relationship("User", back_populates="affiliate")

User.affiliate = relationship("Affiliate", uselist=False, back_populates="user")

class Sale(Base):
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    commission = Column(Float, nullable=False)

    affiliate = relationship("Affiliate", back_populates="sales")
    order = relationship("Order", back_populates="sales")

Affiliate.sales = relationship("Sale", order_by=Sale.id, back_populates="affiliate")
Order.sales = relationship("Sale", order_by=Sale.id, back_populates="order")

class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum('pending', 'paid', 'failed', name='payment_status'), nullable=False)
    transaction_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")

User.payments = relationship("Payment", order_by=Payment.id, back_populates="user")

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")

User.logs = relationship("Log", order_by=Log.id, back_populates="user")

class APIToken(Base):
    __tablename__ = 'api_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(255), nullable=False)
    token = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="api_tokens")

User.api_tokens = relationship("APIToken", order_by=APIToken.id, back_populates="user")

def create_database(db_url="sqlite:///3x_digital.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    print("Banco de dados criado com sucesso.")
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    engine = create_database()
    session = get_session(engine)
