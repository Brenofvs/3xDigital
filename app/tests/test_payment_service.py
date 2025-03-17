# D:\3xDigital\app\tests\test_payment_service.py

"""
test_payment_service.py

Módulo de testes para o serviço de pagamento (PaymentService) que coordena
as operações de pagamento usando diferentes gateways.

Testes:
    - Configuração de gateways de pagamento
    - Processamento de pagamentos
    - Manipulação de webhooks de pagamento
    - Consulta de transações
"""

import pytest
import pytest_asyncio
from unittest import mock
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.services.payment_service import PaymentService
from app.services.payment.gateway_factory import PaymentGatewayFactory
from app.services.payment.stripe_gateway import StripeGateway
from app.services.payment.mercadopago_gateway import MercadoPagoGateway
from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import Order, User, OrderItem, ShippingAddress
from app.services.payment.gateway_interface import PaymentGatewayInterface


@pytest_asyncio.fixture
async def payment_test_data(async_db_session):
    """
    Configura dados de teste para o serviço de pagamento.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Returns:
        Dict: Dados de teste para pagamentos.
    """
    # Configuração do Stripe
    stripe_config = PaymentGatewayConfig(
        gateway_name="stripe",
        api_key="pk_test_123456789",
        api_secret="sk_test_123456789",
        webhook_secret="whsec_test_123456789",
        configuration='{"public_key": "pk_test_123456789"}',
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    async_db_session.add(stripe_config)
    
    # Configuração do Mercado Pago
    mp_config = PaymentGatewayConfig(
        gateway_name="mercado_pago",
        api_key="TEST-abcd-1234-efgh-5678",
        api_secret="TEST-12345678901234-012345-12345678901234567890",
        webhook_secret="TEST-webhook-secret-12345",
        configuration='{"public_key": "TEST-abcd-1234-efgh-5678"}',
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    async_db_session.add(mp_config)
    
    # Usuário para testes
    user = User(
        name="Usuário Teste",
        email="usuario@teste.com",
        cpf="12345678901",
        password_hash="hash_senha",
        role="user",
        created_at=datetime.now()
    )
    async_db_session.add(user)
    
    await async_db_session.commit()
    
    # Pedidos para testes
    # Pedido 1
    order1 = Order(
        user_id=1,
        total=100.0,
        status="pending",
        created_at=datetime.now()
    )
    async_db_session.add(order1)
    await async_db_session.flush()  # Para obter o ID do pedido
    
    # Adiciona itens do pedido 1
    order_item1 = OrderItem(
        order_id=order1.id,
        product_id=1,
        quantity=1,
        price=100.0
    )
    async_db_session.add(order_item1)
    
    # Adiciona endereço de entrega para o pedido 1
    shipping1 = ShippingAddress(
        order_id=order1.id,
        street="Rua Teste",
        number="123",
        city="São Paulo",
        state="SP",
        zip_code="01000-000"
    )
    async_db_session.add(shipping1)
    
    # Pedido 2
    order2 = Order(
        user_id=1,
        total=150.0,
        status="pending",
        created_at=datetime.now()
    )
    async_db_session.add(order2)
    await async_db_session.flush()  # Para obter o ID do pedido
    
    # Adiciona itens do pedido 2
    order_item2 = OrderItem(
        order_id=order2.id,
        product_id=2,
        quantity=2,
        price=75.0
    )
    async_db_session.add(order_item2)
    
    # Adiciona endereço de entrega para o pedido 2
    shipping2 = ShippingAddress(
        order_id=order2.id,
        street="Rua Teste",
        number="123",
        city="São Paulo",
        state="SP",
        zip_code="01000-000"
    )
    async_db_session.add(shipping2)
    
    await async_db_session.commit()
    
    # Transação para o pedido 1 (Stripe)
    transaction1 = PaymentTransaction(
        order_id=order1.id,
        gateway="stripe",
        gateway_transaction_id="pi_test_123456789",
        amount=100.0,
        status="approved",
        payment_method="credit_card",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "credit_card",
            "card_brand": "visa",
            "last4": "4242"
        }),
        created_at=datetime.now() - timedelta(days=1)
    )
    async_db_session.add(transaction1)
    
    # Transação para o pedido 2 (Mercado Pago)
    transaction2 = PaymentTransaction(
        order_id=order2.id,
        gateway="mercado_pago",
        gateway_transaction_id="mp_test_987654321",
        amount=150.0,
        status="pending",
        payment_method="boleto",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "boleto",
            "boleto_url": "https://example.com/boleto"
        }),
        created_at=datetime.now()
    )
    async_db_session.add(transaction2)
    
    await async_db_session.commit()
    await async_db_session.refresh(transaction1)
    await async_db_session.refresh(transaction2)
    
    return {
        "user_id": user.id,
        "order_ids": [order1.id, order2.id],
        "transaction_ids": [transaction1.id, transaction2.id],
        "gateway_configs": {
            "stripe": stripe_config.id,
            "mercado_pago": mp_config.id
        }
    }


@pytest.mark.asyncio
async def test_get_gateway_configs(async_db_session, payment_test_data):
    """
    Testa a obtenção de todas as configurações de gateway.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
    """
    payment_service = PaymentService(async_db_session)
    configs = await payment_service.get_gateway_configs()
    
    assert len(configs) == 2
    assert any(config["gateway_name"] == "stripe" for config in configs)
    assert any(config["gateway_name"] == "mercado_pago" for config in configs)


@pytest.mark.asyncio
async def test_get_gateway_config(async_db_session, payment_test_data, mock_payment_gateways):
    """
    Testa a obtenção de uma configuração específica de gateway.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
        mock_payment_gateways: Fixture com mocks para os gateways de pagamento.
    """
    payment_service = PaymentService(async_db_session)
    
    # Obtém configuração do Stripe
    stripe_config = await payment_service.get_gateway_config("stripe")
    assert stripe_config is not None
    assert stripe_config["gateway_name"] == "stripe"
    assert stripe_config["api_key"] == "test_key"
    
    # Obtém configuração do Mercado Pago
    mp_config = await payment_service.get_gateway_config("mercado_pago")
    assert mp_config is not None
    assert mp_config["gateway_name"] == "mercado_pago"
    assert mp_config["api_key"] == "test_mp_key"
    
    # Tenta obter configuração inexistente
    nonexistent_config = await payment_service.get_gateway_config("nonexistent")
    assert nonexistent_config is None


@pytest.mark.asyncio
async def test_create_or_update_gateway_config(async_db_session):
    """
    Testa a criação e atualização de configurações de gateway.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
    """
    payment_service = PaymentService(async_db_session)
    
    # Cria uma nova configuração
    success, error, config = await payment_service.create_or_update_gateway_config(
        gateway_name="paypal",
        api_key="paypal_api_key",
        api_secret="paypal_api_secret",
        additional_config={"sandbox": True}
    )
    
    assert success is True
    assert error is None
    assert config is not None
    assert config.gateway_name == "paypal"
    assert config.api_key == "paypal_api_key"
    assert config.api_secret == "paypal_api_secret"
    assert "sandbox" in config.configuration
    
    # Atualiza a configuração existente
    success, error, updated_config = await payment_service.create_or_update_gateway_config(
        gateway_name="paypal",
        api_key="new_paypal_api_key",
        api_secret="new_paypal_api_secret"
    )
    
    assert success is True
    assert error is None
    assert updated_config is not None
    assert updated_config.gateway_name == "paypal"
    assert updated_config.api_key == "new_paypal_api_key"
    assert updated_config.api_secret == "new_paypal_api_secret"


@pytest.mark.asyncio
async def test_process_payment(async_db_session, payment_test_data, mock_payment_gateways):
    """
    Testa o processamento de um pagamento.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
        mock_payment_gateways: Fixture com mocks para os gateways de pagamento.
    """
    payment_service = PaymentService(async_db_session)
    
    # Configura o mock para o teste
    mock_payment_gateways["stripe"].create_payment.return_value = (
        True,
        None,
        {
            "payment_id": "new_payment_123",
            "status": "pending",
            "client_secret": "test_secret"
        }
    )
    
    # Processa o pagamento
    success, error, payment_data = await payment_service.process_payment(
        gateway_name="stripe",
        order_id=payment_test_data["order_ids"][0],
        amount=100.0,
        payment_method="credit_card",
        customer_details={
            "name": "Cliente Teste",
            "email": "cliente@teste.com"
        }
    )
    
    # Verifica o resultado
    assert success is True
    assert error is None
    assert payment_data is not None
    assert payment_data["payment_id"] == "new_payment_123"
    
    # Verifica se o método do gateway foi chamado com os parâmetros corretos
    mock_payment_gateways["stripe"].create_payment.assert_called_once_with(
        async_db_session,
        payment_test_data["order_ids"][0],
        100.0,
        "credit_card",
        {
            "name": "Cliente Teste",
            "email": "cliente@teste.com"
        }
    )


@pytest.mark.asyncio
async def test_process_webhook(async_db_session, payment_test_data, mock_payment_gateways):
    """
    Testa o processamento de um webhook de pagamento.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
        mock_payment_gateways: Fixture com mocks para os gateways de pagamento.
    """
    payment_service = PaymentService(async_db_session)
    
    # Configura o mock para o teste
    mock_payment_gateways["stripe"].process_webhook.return_value = (
        True,
        None,
        {
            "transaction_id": "12345",
            "status": "approved"
        }
    )
    
    # Processa o webhook
    webhook_data = {"event": "payment.success", "data": {"payment_id": "12345"}}
    success, error, webhook_result = await payment_service.process_webhook(
        gateway_name="stripe",
        webhook_data=webhook_data
    )
    
    # Verifica o resultado
    assert success is True
    assert error is None
    assert webhook_result is not None
    assert webhook_result["transaction_id"] == "12345"
    
    # Verifica se o método do gateway foi chamado com os parâmetros corretos
    mock_payment_gateways["stripe"].process_webhook.assert_called_once_with(
        async_db_session,
        webhook_data
    )


@pytest.mark.asyncio
async def test_get_transaction_by_id(async_db_session, payment_test_data):
    """
    Testa a obtenção de uma transação por ID.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
    """
    payment_service = PaymentService(async_db_session)
    
    # Obtém uma transação existente
    transaction = await payment_service.get_transaction_by_id(payment_test_data["transaction_ids"][0])
    assert transaction is not None
    assert transaction.id == payment_test_data["transaction_ids"][0]
    assert transaction.order_id == payment_test_data["order_ids"][0]
    
    # Tenta obter uma transação inexistente
    nonexistent_transaction = await payment_service.get_transaction_by_id(999)
    assert nonexistent_transaction is None


@pytest.mark.asyncio
async def test_get_transactions_by_order(async_db_session, payment_test_data):
    """
    Testa a obtenção de transações por ID do pedido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
    """
    payment_service = PaymentService(async_db_session)
    
    # Obtém transações para um pedido existente
    transactions = await payment_service.get_transactions_by_order(payment_test_data["order_ids"][0])
    assert len(transactions) == 1
    assert transactions[0].order_id == payment_test_data["order_ids"][0]
    
    # Tenta obter transações para um pedido inexistente
    nonexistent_transactions = await payment_service.get_transactions_by_order(999)
    assert len(nonexistent_transactions) == 0


@pytest.mark.asyncio
async def test_get_payment_transactions(async_db_session, payment_test_data):
    """
    Testa a obtenção de transações de pagamento com filtros.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_test_data: Fixture com dados de teste para pagamentos.
    """
    payment_service = PaymentService(async_db_session)
    
    # Obtém todas as transações
    transactions, total = await payment_service.get_payment_transactions()
    assert len(transactions) == 2
    assert total == 2
    
    # Filtra por status
    approved_transactions, approved_total = await payment_service.get_payment_transactions(status="approved")
    assert len(approved_transactions) == 1
    assert approved_total == 1
    assert approved_transactions[0].status == "approved"
    
    # Filtra por gateway
    stripe_transactions, stripe_total = await payment_service.get_payment_transactions(gateway="stripe")
    assert len(stripe_transactions) == 1
    assert stripe_total == 1
    assert stripe_transactions[0].gateway == "stripe" 