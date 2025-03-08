# D:\#3xDigital\app\models\finance_models.py
"""
finance_models.py

Módulo que define os modelos de dados (ORM) relacionados às funcionalidades financeiras
do sistema 3xDigital, usando SQLAlchemy.

Funcionalidades principais:
    - Armazenamento de saldo de afiliados
    - Registro de transações financeiras (entrada de comissões, saída de saques)
    - Controle de solicitações de saque
    - Integração com gateways de pagamento externos

Regras de Negócio:
    - Cada afiliado possui um saldo único que é atualizado com comissões e saques
    - Toda movimentação financeira é registrada com timestamp e descrição
    - Saques devem ser solicitados e aprovados antes de serem processados
    - Pagamentos são registrados com informações do gateway utilizado

Dependências:
    - SQLAlchemy para ORM
    - Models de usuários e afiliados existentes
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from app.config.settings import TIMEZONE
from app.models.database import Base


class AffiliateBalance(Base):
    """
    Representa o saldo atual de um afiliado no sistema.
    
    Attributes:
        id (int): ID único do registro de saldo.
        affiliate_id (int): ID do afiliado associado.
        current_balance (float): Saldo atual do afiliado.
        total_earned (float): Total ganho histórico (total de comissões).
        total_withdrawn (float): Total sacado histórico.
        last_updated (datetime): Data da última atualização do saldo.
        
    Relacionamentos:
        affiliate: Relação com o afiliado dono do saldo.
        transactions: Relação com as transações do afiliado.
    """
    __tablename__ = 'affiliate_balances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id', ondelete="CASCADE"), nullable=False, unique=True)
    current_balance = Column(Float, nullable=False, default=0.0)
    total_earned = Column(Float, nullable=False, default=0.0)
    total_withdrawn = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    
    # Relacionamentos
    affiliate = relationship("Affiliate", back_populates="balance")
    transactions = relationship("AffiliateTransaction", back_populates="balance", cascade="all, delete-orphan")


class AffiliateTransaction(Base):
    """
    Representa uma transação financeira de um afiliado (entrada ou saída).
    
    Attributes:
        id (int): ID único da transação.
        balance_id (int): ID do saldo do afiliado associado.
        type (enum): Tipo da transação ('commission', 'withdrawal', 'adjustment').
        amount (float): Valor da transação.
        description (str): Descrição detalhada da transação.
        reference_id (int): ID de referência (venda, saque, etc).
        transaction_date (datetime): Data e hora da transação.
        
    Relacionamentos:
        balance: Relação com o saldo do afiliado.
    """
    __tablename__ = 'affiliate_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    balance_id = Column(Integer, ForeignKey('affiliate_balances.id', ondelete="CASCADE"), nullable=False)
    type = Column(Enum('commission', 'withdrawal', 'adjustment', name='transaction_types'), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    reference_id = Column(Integer, nullable=True)  # ID da venda ou saque relacionado
    transaction_date = Column(DateTime, default=TIMEZONE)
    
    # Relacionamentos
    balance = relationship("AffiliateBalance", back_populates="transactions")


class WithdrawalRequest(Base):
    """
    Representa uma solicitação de saque realizada por um afiliado.
    
    Attributes:
        id (int): ID único da solicitação.
        affiliate_id (int): ID do afiliado que solicitou o saque.
        amount (float): Valor solicitado para saque.
        status (enum): Status da solicitação ('pending', 'approved', 'rejected', 'paid').
        payment_method (str): Método de pagamento solicitado (pix, transferência, etc).
        payment_details (str): Detalhes para o pagamento (chave pix, dados bancários, etc).
        requested_at (datetime): Data da solicitação.
        processed_at (datetime): Data do processamento (aprovação/rejeição).
        admin_notes (str): Notas do administrador sobre a solicitação.
        transaction_id (int): ID da transação gerada após aprovação.
        
    Relacionamentos:
        affiliate: Relação com o afiliado que solicitou o saque.
    """
    __tablename__ = 'withdrawal_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(
        Enum('pending', 'approved', 'rejected', 'paid', name='withdrawal_status'),
        nullable=False,
        default='pending'
    )
    payment_method = Column(String(50), nullable=False)
    payment_details = Column(Text, nullable=False)
    requested_at = Column(DateTime, default=TIMEZONE)
    processed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    transaction_id = Column(Integer, nullable=True)  # ID da transação gerada após aprovação
    
    # Relacionamentos
    affiliate = relationship("Affiliate", backref="withdrawal_requests")


class PaymentGatewayConfig(Base):
    """
    Representa a configuração de um gateway de pagamento no sistema.
    
    Attributes:
        id (int): ID único da configuração.
        gateway_name (str): Nome do gateway (stripe, mercado_pago, etc).
        is_active (bool): Se o gateway está ativo no sistema.
        api_key (str): Chave API do gateway.
        api_secret (str): Segredo API do gateway.
        webhook_secret (str): Segredo para validação de webhooks.
        configuration (str): Configurações adicionais em formato JSON.
        created_at (datetime): Data de criação do registro.
        updated_at (datetime): Data da última atualização.
    """
    __tablename__ = 'payment_gateway_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    gateway_name = Column(String(50), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    configuration = Column(Text, nullable=True)  # JSON com configurações adicionais
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)


class PaymentTransaction(Base):
    """
    Representa uma transação de pagamento processada por um gateway.
    
    Attributes:
        id (int): ID único da transação.
        order_id (int): ID do pedido associado à transação.
        gateway (str): Nome do gateway utilizado.
        amount (float): Valor da transação.
        currency (str): Moeda da transação (BRL, USD, etc).
        gateway_transaction_id (str): ID da transação no gateway externo.
        status (enum): Status da transação ('pending', 'approved', 'refused', 'refunded').
        payment_method (str): Método de pagamento utilizado (credit_card, pix, etc).
        payment_details (str): Detalhes do pagamento em formato JSON.
        created_at (datetime): Data de criação da transação.
        updated_at (datetime): Data da última atualização.
        
    Relacionamentos:
        order: Relação com o pedido associado à transação.
    """
    __tablename__ = 'payment_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    gateway = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default='BRL')
    gateway_transaction_id = Column(String(255), nullable=False, unique=True)
    status = Column(
        Enum('pending', 'approved', 'refused', 'refunded', name='payment_transaction_status'),
        nullable=False,
        default='pending'
    )
    payment_method = Column(String(50), nullable=False)
    payment_details = Column(Text, nullable=True)  # JSON com detalhes do pagamento
    created_at = Column(DateTime, default=TIMEZONE)
    updated_at = Column(DateTime, default=TIMEZONE, onupdate=TIMEZONE)
    
    # Relacionamentos
    order = relationship("Order", backref="payment_transactions")