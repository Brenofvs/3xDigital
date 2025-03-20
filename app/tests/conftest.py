# D:\3xDigital\app\tests\conftest.py

"""
conftest.py

Este módulo contém fixtures para configuração de banco de dados e cliente de teste
utilizados nos testes da aplicação.

Fixtures:
    async_db_session: Configura uma sessão de banco de dados assíncrona para testes.
    test_client_fixture: Configura um cliente de teste para a aplicação AIOHTTP.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient
from app.config.settings import DB_SESSION_KEY
import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Importa os módulos de rotas
from app.views.auth_views import routes as auth_routes
from app.views.categories_views import routes as categories_routes
from app.views.products_views import routes as products_routes
from app.views.orders_views import routes as orders_routes
from app.views.affiliates_views import routes as affiliates_routes
from app.views.finance_views import routes as finance_routes
from app.views.users_views import routes as users_routes
from app.views.payment_views import routes as payment_routes
from app.views.profile_views import routes as profile_routes
from app.views.dashboard_views import routes as dashboard_routes

# Adiciona o diretório raiz ao path para facilitar imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Usar um banco de dados em memória nomeado para ser compartilhado entre sessões
TEST_DB_URL = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

@pytest_asyncio.fixture(scope="function")
async def setup_database():
    """
    Configura um banco de dados compartilhado para todas as sessões.
    
    Cria um único banco de dados em memória nomeado que pode ser 
    acessado por várias sessões simultâneas.
    """
    # Usar um banco nomeado para compartilhar entre sessões
    engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
    
    # Cria as tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Limpeza após o teste
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def async_db_session(setup_database):
    """
    Configura uma sessão de banco de dados assíncrona para testes.

    Utiliza o banco de dados compartilhado criado pelo setup_database.

    Yields:
        AsyncSession: Sessão de banco de dados assíncrona configurada para testes.
    """
    # Usa o engine compartilhado
    engine = setup_database
    
    # Cria o sessionmaker
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Fornece a sessão para o teste
    async with SessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def test_client_fixture(setup_database):
    """
    Configura um cliente de teste para a aplicação AIOHTTP.

    Utiliza o banco de dados compartilhado criado pelo setup_database.

    Yields:
        TestClient: Cliente de teste configurado para a aplicação.
    """
    # Usa o engine compartilhado
    engine = setup_database

    # Cria o sessionmaker
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async_session = SessionLocal()

    # Monta a aplicação AIOHTTP
    app = web.Application()
    # Injeta a sessão usando a key do AIOHTTP
    app[DB_SESSION_KEY] = async_session

    # Adiciona as rotas
    app.add_routes(auth_routes)
    app.add_routes(categories_routes)
    app.add_routes(products_routes)
    app.add_routes(orders_routes)
    app.add_routes(affiliates_routes)
    app.add_routes(finance_routes)
    app.add_routes(users_routes)
    app.add_routes(payment_routes)
    app.add_routes(profile_routes)
    app.add_routes(dashboard_routes)
    
    server = TestServer(app)
    client = TestClient(server)

    async with server, client:
        yield client

    await async_session.close()

@pytest.fixture
def mock_payment_gateways(monkeypatch):
    """
    Fixture que substitui temporariamente os gateways de pagamento por mocks.
    
    Esta fixture modifica o comportamento da factory para retornar
    implementações de teste dos gateways, o que facilita a realização
    de testes sem dependências externas.
    
    Args:
        monkeypatch: Fixture do pytest para modificar objetos temporariamente.
        
    Returns:
        dict: Dicionário com os mocks de gateway.
    """
    from unittest import mock
    from app.services.payment.gateway_factory import PaymentGatewayFactory
    import asyncio
    
    # Cria mocks para os diferentes gateways
    mock_stripe = mock.MagicMock()
    mock_mp = mock.MagicMock()
    
    # Configura o comportamento padrão dos mocks como coroutines
    # Stripe
    mock_stripe.get_gateway_config = mock.AsyncMock(return_value=(True, None, {"gateway_name": "stripe", "api_key": "test_key"}))
    mock_stripe.create_payment = mock.AsyncMock(return_value=(True, None, {"payment_id": "test_stripe_payment", "status": "pending"}))
    mock_stripe.process_webhook = mock.AsyncMock(return_value=(True, None, {"transaction_id": "test_stripe_transaction", "status": "approved"}))
    mock_stripe.initialize_client = mock.AsyncMock(return_value=(True, None, {"client": "test_stripe_client"}))
    
    # Mercado Pago
    mock_mp.get_gateway_config = mock.AsyncMock(return_value=(True, None, {"gateway_name": "mercado_pago", "api_key": "test_mp_key"}))
    mock_mp.create_payment = mock.AsyncMock(return_value=(True, None, {"payment_id": "test_mp_payment", "status": "pending"}))
    mock_mp.process_webhook = mock.AsyncMock(return_value=(True, None, {"transaction_id": "test_mp_transaction", "status": "approved"}))
    mock_mp.initialize_client = mock.AsyncMock(return_value=(True, None, {"client": "test_mp_client"}))
    
    # Função mock para get_gateway
    def mock_get_gateway(gateway_name):
        if gateway_name.lower() == "stripe":
            return mock_stripe
        elif gateway_name.lower() == "mercado_pago":
            return mock_mp
        else:
            raise ValueError(f"Gateway não suportado: {gateway_name}")
    
    # Substitui a função get_gateway da factory pelo nosso mock
    monkeypatch.setattr(PaymentGatewayFactory, "get_gateway", mock_get_gateway)
    
    # Retorna os mocks para uso nos testes
    return {"stripe": mock_stripe, "mercado_pago": mock_mp}

# Fixtures que foram importadas do arquivo conftest.py da pasta payment
# Estas fixtures foram movidas para cá para unificar todos os testes em uma única estrutura
# e evitar conflitos de importação e coleta do pytest

# Nota: A fixture mercadopago_gateway já foi movida diretamente para o arquivo test_mercadopago_gateway.py
# para evitar duplicidade de código, já que era usada apenas naquele arquivo

# Fixtures gerais para banco de dados
@pytest.fixture
def mock_db_session():
    """Fornece uma sessão de banco de dados simulada para testes."""
    session = AsyncMock()
    return session


# Fixtures para simulação de usuários
@pytest.fixture
def admin_user():
    """
    Fixture que cria um usuário admin para testes.
    """
    return {
        "id": 1,
        "username": "admin_test",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture
def affiliate_user():
    """
    Fixture que cria um usuário afiliado para testes.
    """
    return {
        "id": 2,
        "username": "affiliate_test",
        "email": "affiliate@example.com",
        "role": "affiliate",
        "is_active": True,
        "affiliate_id": 1
    }


@pytest.fixture
def customer_user():
    """
    Fixture que cria um usuário cliente comum para testes.
    """
    return {
        "id": 3,
        "username": "customer_test",
        "email": "customer@example.com",
        "role": "customer",
        "is_active": True
    }


# Fixture para pular verificações de autenticação
@pytest.fixture
def mock_auth_check():
    """
    Simula o middleware de autenticação para testes,
    permitindo que as requisições passem pela verificação.
    """
    with patch('app.middleware.authorization_middleware.require_role', 
              lambda roles: lambda handler: handler):
        yield


# Fixture para simular data e hora atual
@pytest.fixture
def mock_current_datetime():
    """Retorna uma data e hora fixa para testes."""
    return datetime(2023, 6, 15, 10, 30, 0, tzinfo=timezone.utc)


# Fixture para simular a configuração de fuso horário
@pytest.fixture
def mock_timezone():
    """Simula a função TIMEZONE da configuração."""
    fixed_dt = datetime(2023, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    with patch('app.config.settings.TIMEZONE', return_value=fixed_dt):
        yield fixed_dt
