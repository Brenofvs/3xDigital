"""
test_stripe_gateway.py

Módulo de testes para a implementação do gateway de pagamento Stripe.
Utiliza mocks para simular as chamadas à API externa do Stripe.

Testes:
    - Obtenção de configuração do gateway
    - Inicialização do cliente Stripe
    - Criação de pagamento
    - Processamento de webhook
"""

import pytest
import pytest_asyncio
from unittest import mock
from datetime import datetime
import stripe
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment.stripe_gateway import StripeGateway
from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import Order, User


@pytest_asyncio.fixture
async def setup_test_data(async_db_session):
    """
    Configura dados de teste para realizar os testes de pagamento.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de teste.
    """
    # Criar usuário de teste
    user = User(
        name="Usuário Teste",
        email="teste@example.com",
        cpf="12345678901",
        password_hash="hashed_password",
        role="user",
        active=True
    )
    async_db_session.add(user)
    await async_db_session.flush()
    
    # Criar pedido de teste
    order = Order(
        user_id=user.id,
        status="pending",
        total=100.0
    )
    async_db_session.add(order)
    await async_db_session.commit()
    await async_db_session.refresh(order)
    
    return {
        "user_id": user.id,
        "order_id": order.id
    }


@pytest_asyncio.fixture
async def stripe_config(async_db_session):
    """
    Configura dados de teste para o gateway Stripe.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de configuração do Stripe.
    """
    # Adiciona uma configuração de gateway
    config = PaymentGatewayConfig(
        gateway_name="stripe",
        api_key="sk_test_123456789",
        api_secret="sk_test_123456789",
        webhook_secret="whsec_test_123456789",
        configuration='{"public_key": "pk_test_123456789"}',
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    async_db_session.add(config)
    await async_db_session.commit()
    await async_db_session.refresh(config)
    
    return {
        "id": config.id,
        "api_key": config.api_key,
        "webhook_secret": config.webhook_secret,
        "public_key": "pk_test_123456789"
    }


@pytest.mark.asyncio
async def test_get_gateway_config(async_db_session, stripe_config):
    """
    Testa a obtenção da configuração do gateway Stripe.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        stripe_config: Fixture com dados de configuração do Stripe.
    """
    gateway = StripeGateway()
    success, error, config = await gateway.get_gateway_config(async_db_session)
    
    assert success is True
    assert error is None
    assert config is not None
    assert config["api_key"] == stripe_config["api_key"]
    assert config["webhook_secret"] == stripe_config["webhook_secret"]
    assert "public_key" in config.get("configuration", {})


@pytest.mark.asyncio
async def test_initialize_client(async_db_session, stripe_config):
    """
    Testa a inicialização do cliente Stripe.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        stripe_config: Fixture com dados de configuração do Stripe.
    """
    # Utilizando patch diretamente no módulo stripe
    with mock.patch('stripe.api_key', new=None) as mock_api_key:
        gateway = StripeGateway()
        # Patch para garantir que o property mock seja chamado
        with mock.patch.object(gateway, 'get_gateway_config', return_value=(True, None, stripe_config)):
            success, error, client_info = await gateway.initialize_client(async_db_session)
            
            assert success is True
            assert error is None
            assert client_info is not None
            # Verificamos se stripe.api_key foi definido em algum momento
            assert hasattr(stripe, 'api_key')
            # A verificação do mock chamado não funciona com as abordagens atuais
            # Vamos verificar se a chave foi configurada corretamente
            assert stripe.api_key == stripe_config["api_key"]


@pytest.mark.asyncio
async def test_create_payment(async_db_session, stripe_config, setup_test_data):
    """
    Testa a criação de um pagamento no Stripe.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        stripe_config: Fixture com dados de configuração do Stripe.
        setup_test_data: Fixture com dados de teste para usuário e pedido.
    """
    # Mock para PaymentIntent.create do Stripe
    with mock.patch('stripe.PaymentIntent.create') as mock_create:
        # Configura o mock para retornar um objeto simulado de PaymentIntent
        mock_create.return_value = {
            "id": "pi_test_123456789",
            "client_secret": "pi_test_secret_123456789",
            "amount": 10000,  # centavos
            "currency": "brl",
            "status": "requires_payment_method"
        }
        
        # Mock para initialize_client
        stripe_mock = mock.MagicMock()
        stripe_mock.PaymentIntent.create.return_value = mock_create.return_value
        
        with mock.patch.object(StripeGateway, 'initialize_client', 
                              return_value=(True, None, stripe_mock)):
            
            gateway = StripeGateway()
            success, error, payment_data = await gateway.create_payment(
                async_db_session,
                order_id=setup_test_data["order_id"],  # Usar pedido da fixture
                amount=100.0,
                payment_method="credit_card",
                customer_details={
                    "name": "Cliente Teste",
                    "email": "cliente@teste.com",
                    "tax_id": "12345678901"
                }
            )
            
            assert success is True
            assert error is None
            assert payment_data is not None
            assert "payment_intent_id" in payment_data
            assert "client_secret" in payment_data
            assert payment_data["payment_intent_id"] == "pi_test_123456789"
            
            # Verifica se a transação foi registrada no banco
            result = await async_db_session.execute(
                select(PaymentTransaction).where(PaymentTransaction.order_id == setup_test_data["order_id"])
            )
            transaction = result.scalar_one_or_none()
            
            assert transaction is not None
            assert transaction.gateway == "stripe"
            assert transaction.amount == 100.0
            assert transaction.status == "pending"


@pytest.mark.asyncio
async def test_process_webhook_payment_success(async_db_session, stripe_config, setup_test_data):
    """
    Testa o processamento de um webhook de pagamento bem-sucedido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        stripe_config: Fixture com dados de configuração do Stripe.
        setup_test_data: Fixture com dados de teste para usuário e pedido.
    """
    # Primeiro, cria uma transação pendente
    transaction = PaymentTransaction(
        order_id=setup_test_data["order_id"],  # Usar pedido da fixture
        gateway="stripe",
        gateway_transaction_id="pi_test_123456789",
        amount=100.0,
        status="pending",
        payment_method="credit_card",
        currency="BRL",
        payment_details="{}",
        created_at=datetime.now()
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    # Mock para Webhook.construct_event do Stripe
    with mock.patch('stripe.Webhook.construct_event') as mock_construct_event:
        # Configura o mock para retornar um evento simulado
        mock_construct_event.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123456789",
                    "amount": 10000,
                    "currency": "brl",
                    "status": "succeeded",
                    "charges": {
                        "data": [
                            {
                                "id": "ch_test_123456789",
                                "payment_method_details": {
                                    "type": "card",
                                    "card": {
                                        "brand": "visa",
                                        "last4": "4242",
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        gateway = StripeGateway()
        success, error, result = await gateway.process_webhook(
            async_db_session,
            webhook_data={
                "payload": "raw_payload",
                "signature": "test_signature"
            }
        )
        
        assert success is True
        assert error is None
        assert result is not None
        
        # Verifica se a transação foi atualizada
        result = await async_db_session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.gateway_transaction_id == "pi_test_123456789"
            )
        )
        updated_transaction = result.scalar_one_or_none()
        
        assert updated_transaction is not None
        assert updated_transaction.status == "approved"


@pytest.mark.asyncio
async def test_process_webhook_payment_failed(async_db_session, stripe_config, setup_test_data):
    """
    Testa o processamento de um webhook de pagamento falho.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        stripe_config: Fixture com dados de configuração do Stripe.
        setup_test_data: Fixture com dados de teste para usuário e pedido.
    """
    # Primeiro, cria uma transação pendente
    transaction = PaymentTransaction(
        order_id=setup_test_data["order_id"],  # Usar pedido da fixture
        gateway="stripe",
        gateway_transaction_id="pi_test_failure",
        amount=100.0,
        status="pending",
        payment_method="credit_card",
        currency="BRL",
        payment_details="{}",
        created_at=datetime.now()
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    # Mock para Webhook.construct_event do Stripe
    with mock.patch('stripe.Webhook.construct_event') as mock_construct_event:
        # Configura o mock para retornar um evento simulado de falha
        mock_construct_event.return_value = {
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_test_failure",
                    "amount": 10000,
                    "currency": "brl",
                    "status": "failed",
                    "last_payment_error": {
                        "message": "Cartão recusado"
                    }
                }
            }
        }
        
        gateway = StripeGateway()
        success, error, result = await gateway.process_webhook(
            async_db_session,
            webhook_data={
                "payload": "raw_payload",
                "signature": "test_signature"
            }
        )
        
        assert success is True
        assert error is None
        assert result is not None
        
        # Verifica se a transação foi atualizada
        result = await async_db_session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.gateway_transaction_id == "pi_test_failure"
            )
        )
        updated_transaction = result.scalar_one_or_none()
        
        assert updated_transaction is not None
        assert updated_transaction.status == "refused"
        import json
        payment_details = json.loads(updated_transaction.payment_details)
        assert "Cartão recusado" in payment_details.get("error_message", "") 