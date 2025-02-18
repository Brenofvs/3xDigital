# D:\#3xDigital\app\tests\test_categories_views.py
"""
test_categories_views.py

Este módulo contém os testes de integração para os endpoints de CRUD de categorias.

Fixtures:
    test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

Test Functions:
    - test_create_category_success(test_client_fixture)
    - test_get_category_success(test_client_fixture)
    - test_update_category_success(test_client_fixture)
    - test_delete_category_success(test_client_fixture)
    - test_list_categories(test_client_fixture)
"""

import pytest
import uuid
import asyncio

async def get_admin_token(client):
    """
    Gera um token de acesso para um usuário administrador com dados únicos.

    Args:
        client: Cliente de teste configurado para a aplicação AIOHTTP.

    Returns:
        str: Token JWT do administrador.

    Raises:
        Exception: Se o login falhar.
    """
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
    admin_password = "admin123"
    admin_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    reg_resp = await client.post("/auth/register", json={
        "name": "Admin Test",
        "email": admin_email,
        "cpf": admin_cpf,
        "password": admin_password,
        "role": "admin"
    })
    await asyncio.sleep(0.2)
    if reg_resp.status != 201:
        print("Registro ignorado:", await reg_resp.json())
    login_resp = await client.post("/auth/login", json={
        "identifier": admin_email,
        "password": admin_password
    })
    login_data = await login_resp.json()
    if "access_token" not in login_data:
        raise Exception(f"Falha no login. Resposta recebida: {login_data}")
    return login_data["access_token"]

@pytest.mark.asyncio
async def test_create_category_success(test_client_fixture):
    """
    Testa a criação de uma categoria com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 201.
        - A categoria criada contém os campos 'id' e 'name' com os valores corretos.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    resp = await client.post("/categories", json={"name": "Eletrônicos"},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 201
    data = await resp.json()
    assert "category" in data
    assert data["category"]["name"] == "Eletrônicos"
    assert "id" in data["category"]

@pytest.mark.asyncio
async def test_get_category_success(test_client_fixture):
    """
    Testa a obtenção dos detalhes de uma categoria existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - Os dados da categoria retornada correspondem aos cadastrados.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    create_resp = await client.post("/categories", json={"name": "Roupas"},
                                    headers={"Authorization": f"Bearer {token}"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    resp = await client.get(f"/categories/{category_id}",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "category" in data
    assert data["category"]["id"] == category_id
    assert data["category"]["name"] == "Roupas"

@pytest.mark.asyncio
async def test_update_category_success(test_client_fixture):
    """
    Testa a atualização de uma categoria existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - O nome da categoria é atualizado conforme esperado.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    create_resp = await client.post("/categories", json={"name": "Livros"},
                                    headers={"Authorization": f"Bearer {token}"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    update_resp = await client.put(f"/categories/{category_id}", json={"name": "Literatura"},
                                   headers={"Authorization": f"Bearer {token}"})
    assert update_resp.status == 200
    update_data = await update_resp.json()
    assert "category" in update_data
    assert update_data["category"]["name"] == "Literatura"

@pytest.mark.asyncio
async def test_delete_category_success(test_client_fixture):
    """
    Testa a deleção de uma categoria existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A resposta contém a mensagem de sucesso na deleção.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    create_resp = await client.post("/categories", json={"name": "Móveis"},
                                    headers={"Authorization": f"Bearer {token}"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    delete_resp = await client.delete(f"/categories/{category_id}",
                                      headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status == 200
    delete_data = await delete_resp.json()
    assert "Categoria deletada com sucesso" in delete_data["message"]

@pytest.mark.asyncio
async def test_list_categories(test_client_fixture):
    """
    Testa a listagem de todas as categorias.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A lista de categorias contém ao menos os itens cadastrados.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria categorias para teste.
    await client.post("/categories", json={"name": "Esportes"},
                      headers={"Authorization": f"Bearer {token}"})
    await client.post("/categories", json={"name": "Beleza"},
                      headers={"Authorization": f"Bearer {token}"})

    resp = await client.get("/categories",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) >= 2
