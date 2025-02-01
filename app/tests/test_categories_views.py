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

@pytest.mark.asyncio
async def test_create_category_success(test_client_fixture):
    """
    Testa a criação de uma categoria com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 201.
        - Categoria criada contém 'id' e 'name' corretos.
    """
    client = test_client_fixture
    resp = await client.post("/categories", json={"name": "Eletrônicos"})
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
        - Status HTTP 200.
        - Dados da categoria correspondem ao cadastro.
    """
    client = test_client_fixture
    create_resp = await client.post("/categories", json={"name": "Roupas"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    resp = await client.get(f"/categories/{category_id}")
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
        - Status HTTP 200.
        - Nome da categoria é atualizado conforme esperado.
    """
    client = test_client_fixture
    create_resp = await client.post("/categories", json={"name": "Livros"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    update_resp = await client.put(f"/categories/{category_id}", json={"name": "Literatura"})
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
        - Status HTTP 200.
        - Mensagem de sucesso na deleção.
    """
    client = test_client_fixture
    create_resp = await client.post("/categories", json={"name": "Móveis"})
    create_data = await create_resp.json()
    category_id = create_data["category"]["id"]

    delete_resp = await client.delete(f"/categories/{category_id}")
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
        - Status HTTP 200.
        - Lista de categorias contém ao menos os itens criados.
    """
    client = test_client_fixture
    # Cria categorias para teste.
    await client.post("/categories", json={"name": "Esportes"})
    await client.post("/categories", json={"name": "Beleza"})

    resp = await client.get("/categories")
    assert resp.status == 200
    data = await resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) >= 2
