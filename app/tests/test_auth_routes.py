# D:\#3xDigital\app\tests\test_auth_routes.py
import pytest

@pytest.mark.asyncio
async def test_register_user_aiohttp(test_client_fixture):
    test_client = test_client_fixture
    resp = await test_client.post("/auth/register", json={
        "name": "John",
        "email": "john@example.com",
        "password": "123456",
        "role": "manager"
    })
    assert resp.status == 201
    data = await resp.json()
    assert "user_id" in data
    assert data["message"] == "Usuário criado com sucesso"

@pytest.mark.asyncio
async def test_register_user_missing_fields(test_client_fixture):
    test_client = test_client_fixture
    # Falta o campo 'email'
    resp = await test_client.post("/auth/register", json={
        "name": "Alice",
        "password": "123456"
    })
    assert resp.status == 400
    data = await resp.json()
    assert "Campo ausente" in data["error"]

@pytest.mark.asyncio
async def test_login_user_valid_credentials(test_client_fixture):
    test_client = test_client_fixture
    # Cria usuário
    await test_client.post("/auth/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "mypassword"
    })
    # Login
    login_resp = await test_client.post("/auth/login", json={
        "email": "bob@example.com",
        "password": "mypassword"
    })
    assert login_resp.status == 200
    data = await login_resp.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_login_user_invalid_credentials(test_client_fixture):
    test_client = test_client_fixture
    # Login sem registro ou senha incorreta
    login_resp = await test_client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpass"
    })
    assert login_resp.status == 401
    data = await login_resp.json()
    assert "Credenciais inválidas" in data["error"]

@pytest.mark.asyncio
async def test_logout(test_client_fixture):
    test_client = test_client_fixture
    resp = await test_client.post("/auth/logout")
    assert resp.status == 200
    data = await resp.json()
    assert data["message"] == "Logout efetuado com sucesso"

@pytest.mark.asyncio
async def test_protected_route_valid_token(test_client_fixture):
    test_client = test_client_fixture
    # Registra + loga
    await test_client.post("/auth/register", json={
        "name": "Charlie",
        "email": "charlie@example.com",
        "password": "secret"
    })
    login_resp = await test_client.post("/auth/login", json={
        "email": "charlie@example.com",
        "password": "secret"
    })
    assert login_resp.status == 200
    token_data = await login_resp.json()
    token = token_data["access_token"]

    # Chama rota protegida
    protected_resp = await test_client.get(
        "/auth/protected", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert protected_resp.status == 200
    result = await protected_resp.json()
    assert "Access granted" in result["message"]

@pytest.mark.asyncio
async def test_protected_route_invalid_token(test_client_fixture):
    test_client = test_client_fixture
    headers = {"Authorization": "Bearer INVALID_TOKEN"}
    protected_resp = await test_client.get("/auth/protected", headers=headers)
    assert protected_resp.status == 401
    result = await protected_resp.json()
    assert "Token inválido." in result["error"] or "Token expirado." in result["error"]


@pytest.mark.asyncio
async def test_protected_route_no_token(test_client_fixture):
    test_client = test_client_fixture
    protected_resp = await test_client.get("/auth/protected")
    assert protected_resp.status == 401
    result = await protected_resp.json()
    assert "Missing or invalid Authorization header" in result["error"]
