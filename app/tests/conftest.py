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
    
    server = TestServer(app)
    client = TestClient(server)

    async with server, client:
        yield client

    await async_session.close()
