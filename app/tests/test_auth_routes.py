# D:\#3xDigital\app\tests\test_auth_routes.py

"""
test_auth_routes.py

Este módulo contém os testes para as rotas de autenticação, incluindo registro,
login, logout e acesso a rotas protegidas.

Fixtures:
    test_client_fixture: Um cliente de teste configurado para a aplicação AIOHTTP.

Test Functions:
    test_register_user_aiohttp(test_client_fixture):
        Testa o registro de um novo usuário com sucesso.

    test_register_user_missing_fields(test_client_fixture):
        Testa o registro de usuário com campos ausentes no corpo da requisição.

    test_login_user_valid_credentials(test_client_fixture):
        Testa o login de um usuário com credenciais válidas.

    test_login_user_invalid_credentials(test_client_fixture):
        Testa o login de um usuário com credenciais inválidas.

    test_logout(test_client_fixture):
        Testa a funcionalidade de logout.

    test_protected_route_valid_token(test_client_fixture):
        Testa o acesso a uma rota protegida com um token válido.

    test_protected_route_invalid_token(test_client_fixture):
        Testa o acesso a uma rota protegida com um token inválido.

    test_protected_route_no_token(test_client_fixture):
        Testa o acesso a uma rota protegida sem fornecer um token.
"""

import pytest

@pytest.mark.asyncio
async def test_register_user_aiohttp(test_client_fixture):
    """
    Testa o registro de um novo usuário com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 201.
        Verifica se a resposta contém o campo "user_id".
        Verifica se a mensagem de sucesso é retornada.
    """
    test_client = test_client_fixture
    resp = await test_client.post("/auth/register", json={
        "name": "John",
        "email": "john@example.com",
        "cpf": "12345678901",
        "password": "123456",
        "role": "manager"
    })
    assert resp.status == 201
    data = await resp.json()
    assert "user_id" in data
    assert data["message"] == "Usuário criado com sucesso"

@pytest.mark.asyncio
async def test_register_user_missing_fields(test_client_fixture):
    """
    Testa o registro de usuário com campos ausentes no corpo da requisição.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 400.
        Verifica se a mensagem de erro contém "Campo ausente".
    """
    test_client = test_client_fixture
    resp = await test_client.post("/auth/register", json={
        "name": "Alice",
        "password": "123456"
    })
    assert resp.status == 400
    data = await resp.json()
    assert "Campo ausente" in data["error"]

@pytest.mark.asyncio
async def test_login_with_email(test_client_fixture):
    """
    Testa o login de um usuário com credenciais válidas.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 200.
        Verifica se o campo "access_token" está presente na resposta.
    """
    test_client = test_client_fixture
    await test_client.post("/auth/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "cpf": "98765432100",
        "password": "mypassword"
    })
    login_resp = await test_client.post("/auth/login", json={
        "identifier": "bob@example.com",
        "password": "mypassword"
    })
    assert login_resp.status == 200
    data = await login_resp.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_login_with_cpf(test_client_fixture):
    """
    Testa o login de um usuário com CPF.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 200.
        Verifica se o campo "access_token" está presente na resposta.
    """
    test_client = test_client_fixture
    await test_client.post("/auth/register", json={
        "name": "Bru",
        "email": "bru@example.com",
        "cpf": "10020030000",
        "password": "mypassword"
    })
    login_resp = await test_client.post("/auth/login", json={
        "identifier": "10020030000",
        "password": "mypassword"
    })
    assert login_resp.status == 200
    data = await login_resp.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_login_user_invalid_credentials(test_client_fixture):
    """
    Testa o login de um usuário com credenciais inválidas.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 401.
        Verifica se a mensagem de erro contém "Credenciais inválidas".
    """
    test_client = test_client_fixture
    login_resp = await test_client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpass"
    })
    assert login_resp.status == 401
    data = await login_resp.json()
    assert "Credenciais inválidas" in data["error"]

@pytest.mark.asyncio
async def test_logout(test_client_fixture):
    """
    Testa a funcionalidade de logout.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 200.
        Verifica se a mensagem de sucesso é retornada.
    """
    test_client = test_client_fixture
    resp = await test_client.post("/auth/logout")
    assert resp.status == 200
    data = await resp.json()
    assert data["message"] == "Logout efetuado com sucesso"

@pytest.mark.asyncio
async def test_protected_route_valid_token(test_client_fixture):
    """
    Testa o acesso a uma rota protegida com um token válido.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 200.
        Verifica se a mensagem de sucesso contém "Access granted".
    """
    test_client = test_client_fixture
    await test_client.post("/auth/register", json={
        "name": "Charlie",
        "email": "charlie@example.com",
        "cpf": "90080070000",
        "password": "secret"
    })
    login_resp = await test_client.post("/auth/login", json={
        "identifier": "charlie@example.com",
        "password": "secret"
    })
    assert login_resp.status == 200
    token_data = await login_resp.json()
    token = token_data["access_token"]

    protected_resp = await test_client.get(
        "/auth/protected", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert protected_resp.status == 200
    result = await protected_resp.json()
    assert "Access granted" in result["message"]

@pytest.mark.asyncio
async def test_protected_route_invalid_token(test_client_fixture):
    """
    Testa o acesso a uma rota protegida com um token inválido.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 401.
        Verifica se a mensagem de erro contém "Token inválido" ou "Token expirado".
    """
    test_client = test_client_fixture
    headers = {"Authorization": "Bearer INVALID_TOKEN"}
    protected_resp = await test_client.get("/auth/protected", headers=headers)
    assert protected_resp.status == 401
    result = await protected_resp.json()
    assert "Token inválido." in result["error"] or "Token expirado." in result["error"]

@pytest.mark.asyncio
async def test_protected_route_no_token(test_client_fixture):
    """
    Testa o acesso a uma rota protegida sem fornecer um token.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        Verifica se a resposta retorna o status 401.
        Verifica se a mensagem de erro contém "Missing or invalid Authorization header".
    """
    test_client = test_client_fixture
    protected_resp = await test_client.get("/auth/protected")
    assert protected_resp.status == 401
    result = await protected_resp.json()
    assert "Missing or invalid Authorization header" in result["error"]

@pytest.mark.asyncio
async def test_admin_only_route_valid_admin(test_client_fixture):
    """
    Testa o acesso à rota restrita com papel 'admin'.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 200.
        - Verifica se a mensagem de sucesso é retornada.
    """
    test_client = test_client_fixture
    await test_client.post("/auth/register", json={
        "name": "Admin User",
        "email": "admin@example.com",
        "cpf": "12345678909",
        "password": "securepassword",
        "role": "admin"
    })
    login_resp = await test_client.post("/auth/login", json={
        "identifier": "admin@example.com",
        "password": "securepassword"
    })
    assert login_resp.status == 200
    token_data = await login_resp.json()
    token = token_data["access_token"]

    resp = await test_client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["message"] == "Bem-vindo à rota de admin!"

@pytest.mark.asyncio
async def test_admin_only_route_invalid_role(test_client_fixture):
    """
    Testa o acesso à rota restrita com papel insuficiente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 403.
        - Verifica se a mensagem de erro indica acesso negado.
    """
    test_client = test_client_fixture
    await test_client.post("/auth/register", json={
        "name": "Regular User",
        "email": "user@example.com",
        "cpf": "98765432101",
        "password": "securepassword",
        "role": "affiliate"
    })
    login_resp = await test_client.post("/auth/login", json={
        "identifier": "user@example.com",
        "password": "securepassword"
    })
    assert login_resp.status == 200
    token_data = await login_resp.json()
    token = token_data["access_token"]

    resp = await test_client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status == 403
    data = await resp.json()
    assert "Acesso negado" in data["error"]

@pytest.mark.asyncio
async def test_admin_only_route_no_token(test_client_fixture):
    """
    Testa o acesso à rota restrita sem fornecer token.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 401.
        - Verifica se a mensagem de erro indica ausência de token.
    """
    test_client = test_client_fixture
    resp = await test_client.get("/admin-only")
    assert resp.status == 401
    data = await resp.json()
    assert "Missing or invalid Authorization header" in data["error"]