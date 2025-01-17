# D:\#3xDigital\app\tests\test_auth.py
import pytest
import pytest_asyncio
from app.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_create_user(async_db_session):
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Test User",
        email="test@example.com",
        password="testpassword",
        role="admin"
    )

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == "admin"

@pytest.mark.asyncio
async def test_authenticate_user_success(async_db_session):
    auth_service = AuthService(async_db_session)
    # Cria usuário
    await auth_service.create_user("Test User", "login@example.com", "mypassword")

    # Autentica
    user = await auth_service.authenticate_user("login@example.com", "mypassword")
    assert user is not None
    assert user.email == "login@example.com"

@pytest.mark.asyncio
async def test_authenticate_user_failure(async_db_session):
    auth_service = AuthService(async_db_session)
    # Tenta autenticar sem criar usuário
    user = await auth_service.authenticate_user("wrong@example.com", "wrongpass")
    assert user is None

@pytest.mark.asyncio
async def test_jwt_generation_and_verification(async_db_session):
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user("JWT User", "jwt@example.com", "jwtpass")

    token = auth_service.generate_jwt_token(user)
    decoded = auth_service.verify_jwt_token(token)
    # Convertendo "sub" para int OU user.id para string
    assert decoded["sub"] == str(user.id)
