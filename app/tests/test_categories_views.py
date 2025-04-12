# D:\3xDigital\app\tests\test_categories_views.py
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
    - test_list_categories_with_pagination(test_client_fixture)
"""

import pytest
from app.tests.utils.auth_utils import get_admin_token, get_user_token

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
        - A resposta contém metadados de paginação.
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
    
    # Verifica a estrutura dos dados
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) >= 2
    
    # Verifica os metadados de paginação
    assert "meta" in data
    assert "page" in data["meta"]
    assert "page_size" in data["meta"]
    assert "total_count" in data["meta"]
    assert "total_pages" in data["meta"]
    assert data["meta"]["page"] == 1  # Página padrão

@pytest.mark.asyncio
async def test_list_categories_with_pagination(test_client_fixture):
    """
    Testa a paginação e pesquisa na listagem de categorias.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Os parâmetros de paginação (page, page_size) funcionam corretamente.
        - O filtro de pesquisa por nome funciona corretamente.
        - Os metadados de paginação correspondem aos parâmetros fornecidos.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    
    # Cria várias categorias para testar paginação
    category_names = ["Esporte Aquático", "Esporte Radical", "Esporte Coletivo", 
                       "Esporte Individual", "Esporte Eletrônico"]
    for name in category_names:
        await client.post("/categories", json={"name": name},
                         headers={"Authorization": f"Bearer {token}"})
    
    # Testa a primeira página com 2 itens por página
    resp = await client.get("/categories?page=1&page_size=2",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    
    assert len(data["categories"]) <= 2  # Não mais que o page_size
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 2
    assert data["meta"]["total_count"] >= 5  # Pelo menos as 5 que criamos
    
    # Testa a segunda página
    resp = await client.get("/categories?page=2&page_size=2",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data2 = await resp.json()
    
    assert len(data2["categories"]) <= 2
    assert data2["meta"]["page"] == 2
    
    # Verifica se as categorias da página 2 são diferentes das da página 1
    page1_ids = [c["id"] for c in data["categories"]]
    page2_ids = [c["id"] for c in data2["categories"]]
    
    # Garante que não há categorias duplicadas entre as páginas
    for cid in page2_ids:
        assert cid not in page1_ids
    
    # Testa o filtro de pesquisa
    resp = await client.get("/categories?search=Radical",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    search_data = await resp.json()
    
    assert len(search_data["categories"]) >= 1
    assert any("Radical" in cat["name"] for cat in search_data["categories"])
