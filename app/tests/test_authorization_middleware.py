# D:\#3xDigital\app\tests\test_authorization_middleware.py
"""
test_authorization_middleware.py

Este módulo contém testes unitários para o decorador de autorização definido em
authorization_middleware.py. Ele verifica cenários de ausência de token, token inválido,
papel insuficiente e papel adequado.

Fixtures:
    aiohttp_client: Fixture padrão do pytest para criar clientes de teste AIOHTTP.

Test Functions:
    test_require_role_no_token(aiohttp_client):
        Testa requisição sem cabeçalho Authorization, esperando HTTP 401.

    test_require_role_invalid_token(aiohttp_client):
        Testa requisição com token JWT inválido, esperando HTTP 401.

    test_require_role_insufficient_role(aiohttp_client):
        Testa usuário com papel insuficiente para acessar a rota, esperando HTTP 403.

    test_require_role_success(aiohttp_client):
        Testa usuário com papel suficiente para acessar a rota, esperando HTTP 200.
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient
from app.middleware.authorization_middleware import require_role
from app.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_require_role_no_token(aiohttp_client):
    """
    Testa requisição sem cabeçalho Authorization, resultando em HTTP 401.

    Args:
        aiohttp_client: Fixture do pytest para criar um cliente de teste AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 401 ao faltar o token.
        - Verifica se a mensagem de erro contém "Missing or invalid Authorization header".
    """
    async def admin_handler(request: web.Request) -> web.Response:
        return web.json_response({"message": "Acesso concedido"}, status=200)

    app = web.Application()
    app.router.add_get("/admin-only", require_role(["admin"])(admin_handler))

    client: TestClient = await aiohttp_client(app)
    resp = await client.get("/admin-only")
    assert resp.status == 401
    data = await resp.json()
    assert "Missing or invalid Authorization header" in data["error"]


@pytest.mark.asyncio
async def test_require_role_invalid_token(aiohttp_client):
    """
    Testa requisição com token JWT inválido, resultando em HTTP 401.

    Args:
        aiohttp_client: Fixture do pytest para criar um cliente de teste AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 401 ao usar token inválido.
        - Verifica se a mensagem de erro indica token expirado ou inválido.
    """
    async def admin_handler(request: web.Request) -> web.Response:
        return web.json_response({"message": "Acesso concedido"}, status=200)

    app = web.Application()
    app.router.add_get("/admin-only", require_role(["admin"])(admin_handler))

    client: TestClient = await aiohttp_client(app)

    # Usa um token inválido de forma intencional
    headers = {"Authorization": "Bearer INVALID_TOKEN"}
    resp = await client.get("/admin-only", headers=headers)
    assert resp.status == 401
    data = await resp.json()
    # Depende do que AuthService retorna: "Token expirado." ou "Token inválido."
    assert "Token" in data["error"]


@pytest.mark.asyncio
async def test_require_role_insufficient_role(aiohttp_client):
    """
    Testa usuário com papel insuficiente para acessar o recurso, resultando em HTTP 403.

    Args:
        aiohttp_client: Fixture do pytest para criar um cliente de teste AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 403 ao papel não estar entre os permitidos.
        - Verifica se a mensagem de erro corresponde a acesso negado.
    """
    async def admin_handler(request: web.Request) -> web.Response:
        return web.json_response({"message": "Acesso concedido"}, status=200)

    app = web.Application()
    app.router.add_get("/admin-only", require_role(["admin"])(admin_handler))

    # Gera token para usuário com papel "manager", mas a rota exige "admin"
    class MockUser:
        id = 123
        role = "manager"

    manager_token = AuthService(None).generate_jwt_token(MockUser())

    client: TestClient = await aiohttp_client(app)
    headers = {"Authorization": f"Bearer {manager_token}"}
    resp = await client.get("/admin-only", headers=headers)
    assert resp.status == 403
    data = await resp.json()
    assert "Acesso negado" in data["error"]


@pytest.mark.asyncio
async def test_require_role_success(aiohttp_client):
    """
    Testa usuário com papel suficiente para acessar a rota, resultando em HTTP 200.

    Args:
        aiohttp_client: Fixture do pytest para criar um cliente de teste AIOHTTP.

    Asserts:
        - Verifica se a resposta retorna status 200 quando o papel do usuário é permitido.
        - Verifica se a mensagem de sucesso é retornada.
    """
    async def admin_handler(request: web.Request) -> web.Response:
        return web.json_response({"message": "Acesso concedido"}, status=200)

    app = web.Application()
    app.router.add_get("/admin-only", require_role(["admin"])(admin_handler))

    class MockUser:
        id = 999
        role = "admin"

    admin_token = AuthService(None).generate_jwt_token(MockUser())

    client: TestClient = await aiohttp_client(app)
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/admin-only", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert "Acesso concedido" in data["message"]
