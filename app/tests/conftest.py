# D:\#3xDigital\app\tests\conftest.py

"""
conftest.py

Este módulo contém fixtures para configuração de banco de dados e cliente de teste
utilizados nos testes da aplicação.

Fixtures:
    async_db_session: Configura uma sessão de banco de dados assíncrona para testes.
    test_client_fixture: Configura um cliente de teste para a aplicação AIOHTTP.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base

from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.views.auth_views import routes
from app.config.settings import DB_SESSION_KEY

@pytest_asyncio.fixture
async def async_db_session():
    """
    Configura uma sessão de banco de dados assíncrona para testes.

    Cria um banco de dados em memória utilizando SQLite, inicializa as tabelas,
    e fornece uma sessão para os testes. Após a execução dos testes, o engine
    do banco de dados é fechado.

    Yields:
        AsyncSession: Sessão de banco de dados assíncrona configurada para testes.
    """
    # Banco em memória para testes
    TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Cria as tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Cria o sessionmaker
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Fornece a sessão para o teste
    async with SessionLocal() as session:
        yield session

    # Fecha o engine ao final
    await engine.dispose()

@pytest_asyncio.fixture
async def test_client_fixture():
    """
    Configura um cliente de teste para a aplicação AIOHTTP.

    Cria um banco de dados em memória utilizando SQLite, inicializa as tabelas,
    e monta a aplicação AIOHTTP para testes. Injeta uma sessão de banco de dados
    na aplicação e fornece um cliente de teste.

    Yields:
        TestClient: Cliente de teste configurado para a aplicação.
    """
    TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Cria as tabelas antes de iniciar o app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Cria a sessão
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async_session = SessionLocal()

    # Monta a aplicação
    app = web.Application()
    
    # Injeta a sessão usando a key do AIOHTTP
    app[DB_SESSION_KEY] = async_session

    app.add_routes(routes)

    server = TestServer(app)
    client = TestClient(server)

    async with server, client:
        yield client

    await async_session.close()
    await engine.dispose()
