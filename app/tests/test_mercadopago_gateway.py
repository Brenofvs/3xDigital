# D:\3xDigital\app\tests\test_mercadopago_gateway.py

"""
test_mercadopago_gateway.py

Módulo de testes para a implementação do gateway de pagamento Mercado Pago.
Utiliza mocks para simular as chamadas à API externa do Mercado Pago.

Testes:
    - Obtenção de configuração do gateway
    - Inicialização do cliente Mercado Pago
    - Criação de pagamento
    - Processamento de webhook
"""

import pytest
import pytest_asyncio
from unittest import mock
from datetime import datetime
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment.mercadopago_gateway import MercadoPagoGateway
from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import Order, User


@pytest_asyncio.fixture
async def mercadopago_config(async_db_session):
    """
    Configura dados de teste para o gateway Mercado Pago.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de configuração do Mercado Pago.
    """
    # Adiciona uma configuração de gateway
    config = PaymentGatewayConfig(
        gateway_name="mercado_pago",
        api_key="TEST-abcd-1234-efgh-5678",
        api_secret="TEST-12345678901234-012345-12345678901234567890",
        webhook_secret="TEST-webhook-secret-12345",
        configuration='{"public_key": "TEST-abcd-1234-efgh-5678"}',
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    async_db_session.add(config)
    await async_db_session.commit()
    await async_db_session.refresh(config)
    
    return {
        "id": config.id,
        "access_token": config.api_secret,
        "api_key": config.api_key,
        "webhook_secret": config.webhook_secret,
        "public_key": "TEST-abcd-1234-efgh-5678"
    }


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


@pytest.mark.asyncio
async def test_get_gateway_config(async_db_session, mercadopago_config):
    """
    Testa a obtenção da configuração do gateway Mercado Pago.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        mercadopago_config: Fixture com dados de configuração do Mercado Pago.
    """
    gateway = MercadoPagoGateway()
    success, error, config = await gateway.get_gateway_config(async_db_session)
    
    assert success is True
    assert error is None
    assert config is not None
    assert config["api_key"] == mercadopago_config["api_key"]
    assert config["api_secret"] == mercadopago_config["access_token"]
    assert "public_key" in config.get("configuration", {})


@pytest.mark.asyncio
async def test_initialize_client(async_db_session, mercadopago_config):
    """
    Testa a inicialização do cliente Mercado Pago.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        mercadopago_config: Fixture com dados de configuração do Mercado Pago.
    """
    # Mock do SDK do Mercado Pago
    with mock.patch('mercadopago.SDK') as mock_sdk:
        mock_instance = mock_sdk.return_value
        
        gateway = MercadoPagoGateway()
        
        # Mock para garantir que get_gateway_config retorne os dados corretos
        with mock.patch.object(gateway, 'get_gateway_config', return_value=(True, None, {
            "api_key": mercadopago_config["api_key"]
        })):
            success, error, client_info = await gateway.initialize_client(async_db_session)
            
            assert success is True
            assert error is None
            assert client_info is not None
            
            # Verifica se o SDK foi inicializado com o token correto
            mock_sdk.assert_called_once()


@pytest.mark.asyncio
async def test_create_payment(async_db_session, mercadopago_config, setup_test_data):
    """
    Testa a criação de um pagamento no Mercado Pago.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        mercadopago_config: Fixture com dados de configuração do Mercado Pago.
        setup_test_data: Fixture com dados de teste (usuário e pedido).
    """
    # Mock do SDK do Mercado Pago
    with mock.patch('mercadopago.SDK') as mock_sdk:
        mock_instance = mock_sdk.return_value
        mock_payment = mock.MagicMock()
        mock_instance.payment.return_value = mock_payment
        
        # Configura o mock para retornar uma resposta simulada de pagamento
        mock_payment.create.return_value = {
            "status": 201,  # Criado com sucesso
            "response": {
                "id": 12345678,
                "status": "pending",
                "status_detail": "pending_contingency",
                "transaction_details": {
                    "payment_method_reference_id": "bolbradesco_1234"
                },
                "transaction_amount": 100.0,
                "payment_method_id": "bolbradesco"
            }
        }
        
        gateway = MercadoPagoGateway()
        
        # Mock para garantir que o initialize_client retorne um SDK válido com os mocks configurados
        with mock.patch.object(gateway, 'initialize_client', return_value=(
            True, None, {"sdk": mock_instance}
        )):
            success, error, payment_data = await gateway.create_payment(
                async_db_session,
                order_id=setup_test_data["order_id"],  # Usar o ID do pedido criado na fixture
                amount=100.0,
                payment_method="bolbradesco",  # Alterado para corresponder ao que a API espera
                customer_details={
                    "email": "cliente_mp@teste.com",
                    "document_type": "CPF",  # Adicionado tipo de documento
                    "document_number": "98765432109",  # Alterado para usar o formato correto
                    "first_name": "Cliente",  # Dividido o nome em primeiro e último nome
                    "last_name": "Teste MP"
                }
            )
            
            if not success:
                print(f"Erro no teste: {error}")
                
            assert success is True
            assert error is None
            assert payment_data is not None
            assert "payment_id" in payment_data
            assert payment_data["payment_id"] == 12345678
            
            # Verifica se a transação foi registrada no banco
            result = await async_db_session.execute(
                select(PaymentTransaction).where(PaymentTransaction.order_id == setup_test_data["order_id"])
            )
            transaction = result.scalar_one_or_none()
            
            assert transaction is not None
            assert transaction.gateway == "mercado_pago"
            assert transaction.amount == 100.0
            assert transaction.status == "pending"


@pytest.mark.asyncio
async def test_process_webhook_payment_success(async_db_session, mercadopago_config, setup_test_data):
    """
    Testa o processamento de um webhook de pagamento bem-sucedido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        mercadopago_config: Fixture com dados de configuração do Mercado Pago.
        setup_test_data: Fixture com dados de teste (usuário e pedido).
    """
    # Primeiro, cria uma transação pendente
    transaction = PaymentTransaction(
        order_id=setup_test_data["order_id"],
        gateway="mercado_pago",
        gateway_transaction_id="12345678",  # Corrigido para o nome correto do campo
        amount=100.0,
        status="pending",
        payment_method="boleto",
        currency="BRL",
        payment_details="{}",  # Alterado para um JSON string vazio
        created_at=datetime.now()
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    # Mock do SDK do Mercado Pago
    with mock.patch('mercadopago.SDK') as mock_sdk:
        mock_instance = mock_sdk.return_value
        mock_payment = mock.MagicMock()
        mock_instance.payment.return_value = mock_payment
        
        # Configura o mock para retornar uma resposta simulada de consulta de pagamento
        mock_payment.get.return_value = {
            "status": 200,
            "response": {
                "id": 12345678,
                "status": "approved",
                "status_detail": "accredited",
                "transaction_amount": 100.0,
                "payment_method_id": "bolbradesco",
                "payment_type_id": "bank_transfer",
                "date_approved": "2023-03-15T10:30:00.000-03:00",
                "payer": {
                    "email": "cliente_mp@teste.com"
                }
            }
        }
        
        gateway = MercadoPagoGateway()
        
        # Mock para garantir que o initialize_client retorne um SDK válido com os mocks configurados
        with mock.patch.object(gateway, 'initialize_client', return_value=(
            True, None, {"sdk": mock_instance}
        )):
            success, error, result = await gateway.process_webhook(
                async_db_session,
                webhook_data={
                    "action": "payment.updated",
                    "type": "payment",
                    "data": {
                        "id": "12345678"
                    }
                }
            )
            
            assert success is True
            assert error is None
            assert result is not None
            
            # Verifica se a transação foi atualizada
            result = await async_db_session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.gateway_transaction_id == "12345678"
                )
            )
            updated_transaction = result.scalar_one_or_none()
            
            assert updated_transaction is not None
            assert updated_transaction.status == "approved"


@pytest.mark.asyncio
async def test_process_webhook_payment_failed(async_db_session, mercadopago_config, setup_test_data):
    """
    Testa o processamento de um webhook de pagamento falho.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        mercadopago_config: Fixture com dados de configuração do Mercado Pago.
        setup_test_data: Fixture com dados de teste (usuário e pedido).
    """
    # Primeiro, cria uma transação pendente
    transaction = PaymentTransaction(
        order_id=setup_test_data["order_id"],
        gateway="mercado_pago",
        gateway_transaction_id="87654321",  # Corrigido para o nome correto do campo
        amount=100.0,
        status="pending",
        payment_method="boleto",
        currency="BRL",
        payment_details="{}",  # Alterado para um JSON string vazio
        created_at=datetime.now()
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    # Mock do SDK do Mercado Pago
    with mock.patch('mercadopago.SDK') as mock_sdk:
        mock_instance = mock_sdk.return_value
        mock_payment = mock.MagicMock()
        mock_instance.payment.return_value = mock_payment
        
        # Configura o mock para retornar uma resposta simulada de consulta de pagamento falho
        mock_payment.get.return_value = {
            "status": 200,
            "response": {
                "id": 87654321,
                "status": "rejected",
                "status_detail": "cc_rejected_insufficient_amount",
                "transaction_amount": 100.0,
                "payment_method_id": "visa",
                "payment_type_id": "credit_card",
                "payer": {
                    "email": "cliente_mp@teste.com"
                }
            }
        }
        
        gateway = MercadoPagoGateway()
        
        # Mock para garantir que o initialize_client retorne um SDK válido com os mocks configurados
        with mock.patch.object(gateway, 'initialize_client', return_value=(
            True, None, {"sdk": mock_instance}
        )):
            success, error, result = await gateway.process_webhook(
                async_db_session,
                webhook_data={
                    "action": "payment.updated",
                    "type": "payment",
                    "data": {
                        "id": "87654321"
                    }
                }
            )
            
            assert success is True
            assert error is None
            assert result is not None
            
            # Verifica se a transação foi atualizada
            result = await async_db_session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.gateway_transaction_id == "87654321"
                )
            )
            updated_transaction = result.scalar_one_or_none()
            
            assert updated_transaction is not None
            assert updated_transaction.status == "refused"
            assert "cc_rejected_insufficient_amount" in str(updated_transaction.payment_details) 