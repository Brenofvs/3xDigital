# D:\3xDigital\app\tests\test_auth.py

"""
test_auth.py

Este módulo contém os testes unitários e assíncronos para os serviços de autenticação,
incluindo criação de usuários, autenticação, e geração/verificação de tokens JWT.

Classes:
    Nenhuma.

Functions:
    test_create_user(async_db_session):
        Testa a criação de um usuário com sucesso.

    test_authenticate_user_success(async_db_session):
        Testa a autenticação de um usuário com credenciais válidas.

    test_authenticate_user_failure(async_db_session):
        Testa a falha de autenticação de um usuário com credenciais inválidas.

    test_jwt_generation_and_verification(async_db_session):
        Testa a geração e verificação de tokens JWT para um usuário.
"""

import pytest
import pytest_asyncio
from app.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_create_user(async_db_session):
    """
    Testa a criação de um usuário com sucesso.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se o ID do usuário foi gerado.
        Verifica se o email e o papel (role) do usuário correspondem aos valores fornecidos.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Test User",
        email="test@example.com",
        cpf="19810957188",
        password="testpassword",
        role="admin"
    )

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == "admin"

@pytest.mark.asyncio
async def test_authenticate_user_success(async_db_session):
    """
    Testa a autenticação de um usuário com credenciais válidas.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se o usuário autenticado não é None.
        Verifica se o email do usuário autenticado corresponde ao email fornecido.
    """
    auth_service = AuthService(async_db_session)
    # Cria usuário
    await auth_service.create_user("Test User", "login@example.com", "14175410972", "mypassword")

    # Autentica
    user = await auth_service.authenticate_user("login@example.com", "mypassword")
    assert user is not None
    assert user.email == "login@example.com"

@pytest.mark.asyncio
async def test_authenticate_user_failure(async_db_session):
    """
    Testa a falha de autenticação de um usuário com credenciais inválidas.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se o retorno da autenticação é None quando as credenciais são inválidas.
    """
    auth_service = AuthService(async_db_session)
    # Tenta autenticar sem criar usuário
    user = await auth_service.authenticate_user("wrong@example.com", "wrongpass")
    assert user is None

@pytest.mark.asyncio
async def test_jwt_generation_and_verification(async_db_session):
    """
    Testa a geração e verificação de tokens JWT para um usuário.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se o campo "sub" do payload decodificado corresponde ao ID do usuário criado.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user("JWT User", "jwt@example.com", "87634500000", "jwtpass")

    token = auth_service.generate_jwt_token(user)
    decoded = auth_service.verify_jwt_token(token)
    # Convertendo "sub" para int OU user.id para string
    assert decoded["sub"] == str(user.id)
