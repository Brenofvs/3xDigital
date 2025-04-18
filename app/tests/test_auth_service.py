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

    test_create_user_with_address(async_db_session):
        Testa a criação de um usuário com endereço.

    test_authenticate_user_success(async_db_session):
        Testa a autenticação de um usuário com credenciais válidas.

    test_authenticate_user_failure(async_db_session):
        Testa a falha de autenticação de um usuário com credenciais inválidas.

    test_jwt_generation_and_verification(async_db_session):
        Testa a geração e verificação de tokens JWT para um usuário.
        
    test_generate_refresh_token(async_db_session):
        Testa a geração de um refresh token para um usuário.
        
    test_verify_refresh_token_valid(async_db_session):
        Testa a verificação de um refresh token válido.
        
    test_verify_refresh_token_invalid(async_db_session):
        Testa a verificação de um refresh token inválido.
        
    test_refresh_access_token(async_db_session):
        Testa a atualização de um access token usando um refresh token válido.
        
    test_revoke_refresh_token(async_db_session):
        Testa a revogação de um refresh token.
"""

import pytest
import pytest_asyncio
from app.services.auth_service import AuthService
from app.models.database import User, UserAddress
from sqlalchemy import select

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
async def test_create_user_with_address(async_db_session):
    """
    Testa a criação de um usuário com endereço.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se o usuário foi criado com sucesso.
        Verifica se o endereço foi associado corretamente ao usuário.
        Verifica se todos os campos do endereço foram salvos corretamente.
    """
    auth_service = AuthService(async_db_session)
    
    # Dados do endereço
    address_data = {
        "street": "Rua dos Testes",
        "number": "123",
        "complement": "Apto 45",
        "neighborhood": "Bairro Teste",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01234-567"
    }
    
    # Criar usuário com endereço
    user = await auth_service.create_user(
        name="Test User with Address",
        email="test.address@example.com",
        cpf="98765432100",
        password="testpass123",
        role="user",
        address=address_data
    )

    assert user.id is not None
    assert user.email == "test.address@example.com"
    
    # Buscar o endereço do usuário
    result = await async_db_session.execute(
        select(UserAddress).where(UserAddress.user_id == user.id)
    )
    address = result.scalar_one_or_none()
    
    # Verificar se o endereço foi criado e está correto
    assert address is not None
    assert address.street == address_data["street"]
    assert address.number == address_data["number"]
    assert address.complement == address_data["complement"]
    assert address.neighborhood == address_data["neighborhood"]
    assert address.city == address_data["city"]
    assert address.state == address_data["state"]
    assert address.zip_code == address_data["zip_code"]

@pytest.mark.asyncio
async def test_create_user_with_invalid_address(async_db_session):
    """
    Testa a criação de um usuário com dados de endereço inválidos.

    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

    Asserts:
        Verifica se a tentativa de criar usuário com endereço inválido gera erro.
        Verifica se a mensagem de erro é apropriada.
    """
    auth_service = AuthService(async_db_session)
    
    # Dados do endereço incompletos
    invalid_address = {
        "street": "Rua dos Testes",
        "number": "123"
        # Faltando campos obrigatórios
    }
    
    with pytest.raises(ValueError) as exc_info:
        await auth_service.create_user(
            name="Test User Invalid Address",
            email="test.invalid@example.com",
            cpf="12345678901",
            password="testpass123",
            role="user",
            address=invalid_address
        )
    
    assert "Campos obrigatórios de endereço faltando" in str(exc_info.value)

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

@pytest.mark.asyncio
async def test_generate_refresh_token(async_db_session):
    """
    Testa a geração de um refresh token para um usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Asserts:
        Verifica se o token gerado não é None ou string vazia.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        "Refresh User", 
        "refresh@example.com", 
        "12345678900", 
        "refreshpass"
    )
    
    refresh_token = await auth_service.generate_refresh_token(user)
    assert refresh_token is not None
    assert len(refresh_token) > 0
    
@pytest.mark.asyncio
async def test_verify_refresh_token_valid(async_db_session):
    """
    Testa a verificação de um refresh token válido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Asserts:
        Verifica se o token é válido e retorna o usuário correto.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        "Valid Token User", 
        "valid@example.com", 
        "11122233344", 
        "validpass"
    )
    
    refresh_token = await auth_service.generate_refresh_token(user)
    is_valid, returned_user = await auth_service.verify_refresh_token(refresh_token)
    
    assert is_valid is True
    assert returned_user is not None
    assert returned_user.id == user.id
    
@pytest.mark.asyncio
async def test_verify_refresh_token_invalid(async_db_session):
    """
    Testa a verificação de um refresh token inválido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Asserts:
        Verifica se um token inválido é rejeitado.
    """
    auth_service = AuthService(async_db_session)
    is_valid, returned_user = await auth_service.verify_refresh_token("invalid_token")
    
    assert is_valid is False
    assert returned_user is None
    
@pytest.mark.asyncio
async def test_refresh_access_token(async_db_session):
    """
    Testa a atualização de um access token usando um refresh token válido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Asserts:
        Verifica se um novo access token é gerado.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        "Refresh Access User", 
        "refreshaccess@example.com", 
        "99988877766", 
        "refreshpass"
    )
    
    refresh_token = await auth_service.generate_refresh_token(user)
    success, message, tokens = await auth_service.refresh_access_token(refresh_token)
    
    assert success is True
    assert "Token atualizado com sucesso" in message
    assert "access_token" in tokens
    assert tokens["access_token"] is not None
    
@pytest.mark.asyncio
async def test_revoke_refresh_token(async_db_session):
    """
    Testa a revogação de um refresh token.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
        
    Asserts:
        Verifica se o token é revogado com sucesso e não pode mais ser usado.
    """
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        "Revoke Token User", 
        "revoke@example.com", 
        "55566677788", 
        "revokepass"
    )
    
    refresh_token = await auth_service.generate_refresh_token(user)
    
    # Verifica que o token é válido inicialmente
    is_valid_before, _ = await auth_service.verify_refresh_token(refresh_token)
    assert is_valid_before is True
    
    # Revoga o token
    revoked = await auth_service.revoke_refresh_token(refresh_token)
    assert revoked is True
    
    # Verifica que o token foi invalidado
    is_valid_after, _ = await auth_service.verify_refresh_token(refresh_token)
    assert is_valid_after is False
