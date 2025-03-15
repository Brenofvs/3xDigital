# D:\3xDigital\app\tests\test_finance_views.py
"""
test_finance_views.py

Testes unitários e de integração para os endpoints financeiros do sistema 3xDigital.

Funcionalidades testadas:
    - Consulta de saldo de afiliado
    - Listagem de transações financeiras
    - Solicitação e processamento de saques
    - Geração de relatórios financeiros

Dependências:
    - pytest e pytest-asyncio para testes assíncronos
    - aiohttp.test_utils para simulação de requisições HTTP
    - app.services.finance_service para serviços financeiros
    - app.models.finance_models para modelos de dados
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import asyncio

from app.models.database import Affiliate, User
from app.models.finance_models import (
    AffiliateBalance, AffiliateTransaction, WithdrawalRequest
)
from app.config.settings import DB_SESSION_KEY
from app.services.auth_service import AuthService
from sqlalchemy import select


@pytest_asyncio.fixture
async def finance_test_data(test_client_fixture):
    """
    Configura dados de teste para os testes financeiros.
    
    Cria:
        - Usuário administrador
        - Usuário afiliado com saldo
        - Algumas transações
        
    Returns:
        dict: Dados de teste (tokens, ids, etc)
    """
    # Dados a serem retornados
    data = {}
    
    # Cria usuário admin
    admin_data = {
        "name": "Admin Teste Financeiro",
        "email": "admin_finance@example.com",
        "cpf": "12378945601",
        "password": "adminpass123",
        "role": "admin"
    }
    
    admin_resp = await test_client_fixture.post('/auth/register', json=admin_data)
    admin_data = await admin_resp.json()
    admin_id = admin_data['user_id']
    
    # Login do admin
    admin_login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "admin_finance@example.com",
        "password": "adminpass123"
    })
    admin_login_data = await admin_login_resp.json()
    admin_token = admin_login_data['access_token']
    
    # Cria usuário afiliado
    affiliate_user_data = {
        "name": "Afiliado Teste Financeiro",
        "email": "afiliado_finance@example.com",
        "cpf": "98712345609",
        "password": "afiliadopass123",
        "role": "affiliate"
    }
    
    affiliate_resp = await test_client_fixture.post('/auth/register', json=affiliate_user_data)
    affiliate_data = await affiliate_resp.json()
    affiliate_user_id = affiliate_data['user_id']
    
    # Login do afiliado
    max_attempts = 3
    affiliate_token = None
    
    for attempt in range(max_attempts):
        affiliate_login_resp = await test_client_fixture.post('/auth/login', json={
            "identifier": "afiliado_finance@example.com",
            "password": "afiliadopass123"
        })
        
        if affiliate_login_resp.status == 200:
            affiliate_login_data = await affiliate_login_resp.json()
            if 'access_token' in affiliate_login_data:
                affiliate_token = affiliate_login_data['access_token']
                break
        await asyncio.sleep(0.5)  # Pequena pausa entre tentativas
    
    if not affiliate_token:
        # Se não conseguir o token após tentativas, crie um token manualmente para testes
        auth_service = AuthService(db)
        user_result = await db.execute(select(User).where(User.email == "afiliado_finance@example.com"))
        user = user_result.scalar_one_or_none()
        if user:
            affiliate_token = auth_service.generate_jwt_token(user)
        else:
            raise ValueError("Não foi possível autenticar o usuário afiliado para testes")
    
    # Cria registro de afiliado
    db = test_client_fixture.app[DB_SESSION_KEY]
    affiliate = Affiliate(
        user_id=affiliate_user_id,
        referral_code="TESTFIN123",
        commission_rate=0.1,
        request_status="approved"
    )
    db.add(affiliate)
    await db.flush()
    
    # Cria saldo de afiliado
    balance = AffiliateBalance(
        affiliate_id=affiliate.id,
        current_balance=1000.0,
        total_earned=1500.0,
        total_withdrawn=500.0
    )
    db.add(balance)
    await db.flush()
    
    # Cria transações
    today = datetime.now()
    transactions = [
        AffiliateTransaction(
            balance_id=balance.id,
            type="commission",
            amount=100.0,
            description="Comissão de teste #1",
            reference_id=1,
            transaction_date=today - timedelta(days=5)
        ),
        AffiliateTransaction(
            balance_id=balance.id,
            type="commission",
            amount=200.0,
            description="Comissão de teste #2",
            reference_id=2,
            transaction_date=today - timedelta(days=3)
        ),
        AffiliateTransaction(
            balance_id=balance.id,
            type="withdrawal",
            amount=-300.0,
            description="Saque de teste",
            reference_id=1,
            transaction_date=today - timedelta(days=1)
        )
    ]
    
    for t in transactions:
        db.add(t)
    
    # Cria solicitação de saque pendente
    withdrawal = WithdrawalRequest(
        affiliate_id=affiliate.id,
        amount=200.0,
        status="pending",
        payment_method="pix",
        payment_details='{"key": "test@example.com"}',
        requested_at=today
    )
    db.add(withdrawal)
    
    await db.commit()
    
    # Armazena dados para testes
    data["admin_token"] = admin_token
    data["affiliate_token"] = affiliate_token
    data["admin_id"] = admin_id
    data["affiliate_user_id"] = affiliate_user_id
    data["affiliate_id"] = affiliate.id
    data["balance_id"] = balance.id
    data["withdrawal_id"] = withdrawal.id
    
    return data


@pytest.mark.asyncio
async def test_get_balance(test_client_fixture, finance_test_data):
    """
    Testa a consulta de saldo do afiliado.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Afiliado consegue consultar seu próprio saldo
        - Admin consegue consultar saldo de qualquer afiliado
    """
    data = finance_test_data
    
    # Teste como afiliado
    resp = await test_client_fixture.get('/finance/balance',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    balance_data = await resp.json()
    
    assert "current_balance" in balance_data
    assert balance_data["current_balance"] == 1000.0
    assert balance_data["total_earned"] == 1500.0
    assert balance_data["total_withdrawn"] == 500.0
    
    # Teste como admin consultando afiliado específico
    resp = await test_client_fixture.get(f'/finance/balance?affiliate_id={data["affiliate_id"]}',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    balance_data = await resp.json()
    
    assert balance_data["affiliate_id"] == data["affiliate_id"]
    assert balance_data["current_balance"] == 1000.0


@pytest.mark.asyncio
async def test_get_transactions(test_client_fixture, finance_test_data):
    """
    Testa a listagem de transações do afiliado.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Afiliado consegue listar suas próprias transações
        - Filtragem por tipo de transação funciona
    """
    data = finance_test_data
    
    # Teste como afiliado
    resp = await test_client_fixture.get('/finance/transactions',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    transactions_data = await resp.json()
    
    assert "transactions" in transactions_data
    assert len(transactions_data["transactions"]) == 3
    
    # Teste com filtro de tipo
    resp = await test_client_fixture.get('/finance/transactions?type=commission',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    filtered_data = await resp.json()
    
    assert len(filtered_data["transactions"]) == 2
    for t in filtered_data["transactions"]:
        assert t["type"] == "commission"


@pytest.mark.asyncio
async def test_request_withdrawal(test_client_fixture, finance_test_data):
    """
    Testa a solicitação de saque pelo afiliado.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Afiliado consegue solicitar saque
        - Validação de valor negativo funciona
    """
    data = finance_test_data
    
    # Processa qualquer solicitação pendente primeiro
    resp = await test_client_fixture.get('/finance/withdrawals',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    withdrawals = await resp.json()
    
    for w in withdrawals["withdrawals"]:
        if w["status"] == "pending":
            await test_client_fixture.put(
                f'/finance/withdrawals/{w["id"]}/process',
                json={"status": "rejected", "admin_notes": "Rejeitado para teste"},
                headers={"Authorization": f"Bearer {data['admin_token']}"}
            )
    
    # Dados do saque
    withdrawal_data = {
        "amount": 100.0,
        "payment_method": "pix",
        "payment_details": '{"key": "saquetest@example.com"}'
    }
    
    # Teste como afiliado
    resp = await test_client_fixture.post('/finance/withdrawals/request',
                            json=withdrawal_data,
                            headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 201
    result = await resp.json()
    
    assert "withdrawal_id" in result
    assert result["status"] == "pending"
    assert result["amount"] == 100.0
    
    # Teste com valor inválido
    invalid_data = {
        "amount": -100.0,
        "payment_method": "pix",
        "payment_details": '{"key": "invalid@example.com"}'
    }
    
    resp = await test_client_fixture.post('/finance/withdrawals/request',
                            json=invalid_data,
                            headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 400
    error_data = await resp.json()
    assert "error" in error_data


@pytest.mark.asyncio
async def test_list_withdrawals(test_client_fixture, finance_test_data):
    """
    Testa a listagem de solicitações de saque.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Afiliado consegue listar suas próprias solicitações de saque
        - Admin consegue listar todas as solicitações
    """
    data = finance_test_data
    
    # Teste como afiliado
    resp = await test_client_fixture.get('/finance/withdrawals',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    withdrawals_data = await resp.json()
    
    assert "withdrawals" in withdrawals_data
    assert len(withdrawals_data["withdrawals"]) > 0
    
    # Teste como admin vendo todas as solicitações
    resp = await test_client_fixture.get('/finance/withdrawals',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    admin_withdrawals_data = await resp.json()
    
    assert len(admin_withdrawals_data["withdrawals"]) > 0


@pytest.mark.asyncio
async def test_process_withdrawal(test_client_fixture, finance_test_data):
    """
    Testa o processamento de solicitações de saque por administradores.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Admin consegue aprovar solicitações de saque
        - Status da solicitação é atualizado corretamente
        - Saldo do afiliado é debitado após aprovação
    """
    data = finance_test_data
    
    # Verifica se há uma solicitação de saque criada nos dados de teste
    if "withdrawal_id" not in data:
        # Cria uma solicitação de saque para o teste
        withdrawal_data = {
            "amount": 50.0,  # Valor baixo para garantir que está dentro do saldo
            "payment_method": "pix",
            "payment_details": "teste@example.com"
        }
        
        # Submete a solicitação como afiliado
        resp = await test_client_fixture.post('/finance/withdrawals/request',
                               json=withdrawal_data,
                               headers={"Authorization": f"Bearer {data['affiliate_token']}"})
        
        assert resp.status == 201
        result = await resp.json()
        withdrawal_id = result["withdrawal_id"]
    else:
        withdrawal_id = data["withdrawal_id"]
    
    # Dados para aprovação
    approval_data = {
        "status": "approved",
        "admin_notes": "Aprovado para pagamento via teste"
    }
    
    # Teste como admin
    resp = await test_client_fixture.put(f'/finance/withdrawals/{withdrawal_id}/process',
                           json=approval_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    if resp.status != 200:
        error_data = await resp.json()
        print(f"Erro ao processar saque: {error_data}")
    
    assert resp.status == 200
    result = await resp.json()
    
    # Verifica se a resposta contém os campos esperados
    assert "message" in result
    assert "withdrawal_id" in result
    assert "status" in result
    assert result["status"] == "approved"
    
    # Verifica se a solicitação foi atualizada no banco de dados
    resp = await test_client_fixture.get('/finance/withdrawals',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    withdrawals_data = await resp.json()
    
    found = False
    for withdrawal in withdrawals_data["withdrawals"]:
        if withdrawal["id"] == withdrawal_id:
            assert withdrawal["status"] == "approved"
            found = True
            break
    
    assert found, "Solicitação de saque não encontrada após processamento"


@pytest.mark.asyncio
async def test_financial_report(test_client_fixture, finance_test_data):
    """
    Testa a geração de relatórios financeiros.
    
    Args:
        client: Cliente de teste
        finance_test_data: Dados de teste
        
    Asserts:
        - Afiliado consegue gerar relatório de suas finanças
        - Admin consegue gerar relatório geral e por afiliado
        - Diferentes formatos de relatório são gerados corretamente
    """
    data = finance_test_data
    
    # Teste como afiliado - formato JSON
    resp = await test_client_fixture.get('/finance/reports',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    report_data = await resp.json()
    
    assert "periodo" in report_data
    assert "comissoes" in report_data
    assert "saques" in report_data
    
    # Teste como admin - com filtro de afiliado
    resp = await test_client_fixture.get(f'/finance/reports?affiliate_id={data["affiliate_id"]}',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    filtered_report = await resp.json()
    
    assert "afiliado" in filtered_report
    assert filtered_report["afiliado"]["id"] == data["affiliate_id"]
    
    # Teste formato CSV
    resp = await test_client_fixture.get('/finance/reports?format=csv',
                           headers={"Authorization": f"Bearer {data['affiliate_token']}"})
    
    assert resp.status == 200
    assert resp.headers['Content-Type'] == 'text/csv'
    assert 'attachment; filename=' in resp.headers['Content-Disposition']
    
    csv_content = await resp.text()
    assert "Comissões - Total" in csv_content
    assert "Saques - Total" in csv_content