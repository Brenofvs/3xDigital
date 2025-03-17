# D:\3xDigital\app\tests\test_payment_views.py

"""
test_payment_views.py

Módulo de testes para os endpoints de pagamento (payment_views.py).
Testa a funcionalidade das rotas de processamento de pagamento, configuração
de gateway e relatórios de transações.

Testes:
    - Configuração de gateway de pagamento
    - Processamento de pagamento
    - Recebimento de webhook
    - Listagem de transações
    - Geração de relatórios
"""

import pytest
import pytest_asyncio
import json
from aiohttp import web
from unittest import mock
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import User, Order


@pytest_asyncio.fixture
async def payment_views_data(test_client_fixture, async_db_session):
    """
    Configura dados de teste para os endpoints de pagamento.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de teste para as operações de pagamento.
    """
    # Cria usuário admin para testes
    admin_data = {
        "name": "Admin Pagamentos",
        "email": "admin_payments@example.com",
        "cpf": "12345678901",
        "password": "adminpass",
        "role": "admin"
    }
    
    admin_resp = await test_client_fixture.post('/auth/register', json=admin_data)
    admin_data = await admin_resp.json()
    admin_id = admin_data['user_id']
    
    # Login do admin
    admin_login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "admin_payments@example.com",
        "password": "adminpass"
    })
    admin_login_data = await admin_login_resp.json()
    admin_token = admin_login_data['access_token']
    
    # Cria um usuário comum para testes
    user_data = {
        "name": "Cliente Pagamentos",
        "email": "cliente_payments@example.com",
        "cpf": "98765432109",
        "password": "clientpass",
        "role": "user"
    }
    
    user_resp = await test_client_fixture.post('/auth/register', json=user_data)
    user_data = await user_resp.json()
    user_id = user_data['user_id']
    
    # Login do usuário comum
    user_login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "cliente_payments@example.com",
        "password": "clientpass"
    })
    user_login_data = await user_login_resp.json()
    user_token = user_login_data['access_token']
    
    # Cria um pedido para o usuário
    order_data = {
        "items": [
            {"product_id": 1, "quantity": 2, "price": 50.0}
        ],
        "shipping_address": {
            "street": "Rua Teste",
            "number": "123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567"
        }
    }
    
    order_resp = await test_client_fixture.post(
        '/orders',
        json=order_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    order_resp_data = await order_resp.json()
    order_id = order_resp_data.get('order_id', 1)  # Fallback para 1 se a rota não retornar ID
    
    # Insere algumas transações diretamente no banco de dados
    transaction1 = PaymentTransaction(
        order_id=order_id,
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
    await async_db_session.commit()
    
    return {
        "admin_id": admin_id,
        "admin_token": admin_token,
        "user_id": user_id,
        "user_token": user_token,
        "order_id": order_id
    }


@pytest.mark.asyncio
async def test_configure_payment_gateway(test_client_fixture, payment_views_data):
    """
    Testa a configuração de um gateway de pagamento.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        payment_views_data: Fixture com dados de teste para pagamentos.
    """
    # Só admin deve poder configurar gateways
    admin_token = payment_views_data["admin_token"]
    
    # Tenta configurar o gateway Stripe
    config_data = {
        "gateway_name": "stripe",
        "api_key": "pk_test_123456789",
        "api_secret": "sk_test_123456789",
        "webhook_secret": "whsec_test_123456789",
        "configuration": {
            "public_key": "pk_test_123456789"
        }
    }
    
    response = await test_client_fixture.post(
        '/payments/configure-gateway',
        json=config_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert data["success"] is True
    assert "gateway_config" in data
    assert data["gateway_config"]["gateway_name"] == "stripe"
    
    # Tenta configurar gateway sem autenticação
    response = await test_client_fixture.post(
        '/payments/configure-gateway',
        json=config_data
    )
    
    assert response.status == 401
    
    # Tenta configurar gateway como usuário comum
    user_token = payment_views_data["user_token"]
    response = await test_client_fixture.post(
        '/payments/configure-gateway',
        json=config_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert response.status == 403


@pytest.mark.asyncio
async def test_process_payment(test_client_fixture, payment_views_data):
    """
    Testa o processamento de um pagamento.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        payment_views_data: Fixture com dados de teste para pagamentos.
    """
    user_token = payment_views_data["user_token"]
    order_id = payment_views_data["order_id"]
    
    # Define dados de pagamento
    payment_data = {
        "gateway": "stripe",
        "payment_method": "credit_card",
        "customer_details": {
            "name": "Cliente Teste",
            "email": "cliente@teste.com",
            "tax_id": "12345678901"
        }
    }
    
    # Mock para o serviço de pagamento
    with mock.patch('app.services.payment_service.PaymentService.process_payment') as mock_process:
        mock_process.return_value = (
            True,
            None,
            {
                "payment_intent_id": "pi_test_987654321",
                "client_secret": "test_secret_key",
                "amount": 100.0,
                "status": "requires_payment_method"
            }
        )
        
        response = await test_client_fixture.post(
            f'/payments/process/{order_id}',
            json=payment_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status == 200
        data = await response.json()
        assert data["success"] is True
        assert "payment_data" in data
        assert data["payment_data"]["payment_intent_id"] == "pi_test_987654321"
        
        # Verifica se foi chamado com os parâmetros corretos
        mock_process.assert_called_once()
        _, call_args, _ = mock_process.mock_calls[0]
        assert call_args[0] == "stripe"  # gateway_name
        assert call_args[1] == order_id  # order_id
        
    # Tenta processar sem autenticação
    response = await test_client_fixture.post(
        f'/payments/process/{order_id}',
        json=payment_data
    )
    
    assert response.status == 401
    
    # Tenta processar com um ID de pedido inválido
    response = await test_client_fixture.post(
        '/payments/process/9999',
        json=payment_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert response.status == 404


@pytest.mark.asyncio
async def test_receive_payment_webhook(test_client_fixture, payment_views_data):
    """
    Testa o recebimento de um webhook de pagamento.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        payment_views_data: Fixture com dados de teste para pagamentos.
    """
    # Não requer autenticação, pois vem do provedor de pagamento
    
    # Define dados do webhook
    webhook_data = {
        "gateway": "stripe",
        "payload": {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123456789",
                    "status": "succeeded"
                }
            }
        },
        "signature": "test_signature"
    }
    
    # Mock para o serviço de pagamento
    with mock.patch('app.services.payment_service.PaymentService.process_webhook') as mock_webhook:
        mock_webhook.return_value = (
            True,
            None,
            {"transaction_id": "pi_test_123456789", "status": "approved"}
        )
        
        response = await test_client_fixture.post(
            '/payments/webhook',
            json=webhook_data
        )
        
        assert response.status == 200
        data = await response.json()
        assert data["success"] is True
        
        # Verifica se foi chamado com os parâmetros corretos
        mock_webhook.assert_called_once()
        _, call_args, _ = mock_webhook.mock_calls[0]
        assert call_args[0] == "stripe"  # gateway_name
        
    # Tenta processar webhook sem gateway
    invalid_webhook = {
        "payload": {"type": "payment_intent.succeeded"},
        "signature": "test_signature"
    }
    
    response = await test_client_fixture.post(
        '/payments/webhook',
        json=invalid_webhook
    )
    
    assert response.status == 400


@pytest.mark.asyncio
async def test_list_payment_transactions(test_client_fixture, payment_views_data):
    """
    Testa a listagem de transações de pagamento.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        payment_views_data: Fixture com dados de teste para pagamentos.
    """
    admin_token = payment_views_data["admin_token"]
    
    # Listagem simples como admin
    response = await test_client_fixture.get(
        '/payments/transactions',
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert "transactions" in data
    assert "pagination" in data
    assert len(data["transactions"]) > 0
    
    # Listagem com filtros
    response = await test_client_fixture.get(
        '/payments/transactions?status=approved&gateway=stripe',
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert "transactions" in data
    assert len(data["transactions"]) > 0
    assert all(t["status"] == "approved" for t in data["transactions"])
    assert all(t["gateway"] == "stripe" for t in data["transactions"])
    
    # Tenta listar sem autenticação
    response = await test_client_fixture.get('/payments/transactions')
    assert response.status == 401
    
    # Usuário comum só deve ver suas próprias transações
    user_token = payment_views_data["user_token"]
    response = await test_client_fixture.get(
        '/payments/transactions',
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert response.status == 403  # Usuário comum não deve ter acesso


@pytest.mark.asyncio
async def test_generate_payment_report(test_client_fixture, payment_views_data):
    """
    Testa a geração de relatório de pagamentos.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        payment_views_data: Fixture com dados de teste para pagamentos.
    """
    admin_token = payment_views_data["admin_token"]
    
    # Gera relatório como admin
    response = await test_client_fixture.get(
        '/payments/report',
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert "report" in data
    assert "total_transactions" in data["report"]
    assert "total_amount" in data["report"]
    assert "by_status" in data["report"]
    assert "by_gateway" in data["report"]
    
    # Relatório com filtros
    response = await test_client_fixture.get(
        '/payments/report?gateway=stripe',
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert "report" in data
    
    # Tenta gerar relatório sem autenticação
    response = await test_client_fixture.get('/payments/report')
    assert response.status == 401
    
    # Usuário comum não deve poder gerar relatório (acesso apenas para admin)
    user_token = payment_views_data["user_token"]
    response = await test_client_fixture.get(
        '/payments/report',
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert response.status == 403 