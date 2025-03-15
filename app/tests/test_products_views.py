# D:\3xDigital\app\tests\test_products_views.py
"""
test_products_views.py

Este módulo contém os testes de integração para os endpoints de CRUD de produtos.

Fixtures:
    test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

Test Functions:
    - test_create_product_success(test_client_fixture)
    - test_get_product_success(test_client_fixture)
    - test_update_product_success(test_client_fixture)
    - test_delete_product_success(test_client_fixture)
    - test_list_products(test_client_fixture)
"""

import pytest
from app.tests.utils.auth_utils import get_admin_token, get_user_token

@pytest.mark.asyncio
async def test_create_product_success(test_client_fixture):
    """
    Testa a criação de um produto com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 201.
        - O produto criado contém os dados corretos, incluindo a associação com categoria.
        - O campo 'image_url' existe (com valor nulo se não informado).
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria uma categoria para associação.
    cat_resp = await client.post("/categories", json={"name": "Informática"},
                                 headers={"Authorization": f"Bearer {token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]

    prod_resp = await client.post("/products", json={
        "name": "Notebook",
        "description": "Notebook de última geração",
        "price": 2500.50,
        "stock": 5,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})
    assert prod_resp.status == 201
    prod_data = await prod_resp.json()
    assert "product" in prod_data
    product = prod_data["product"]
    assert product["name"] == "Notebook"
    assert product["category_id"] == category_id
    assert "image_url" in product
    assert product["image_url"] is None

@pytest.mark.asyncio
async def test_get_product_success(test_client_fixture):
    """
    Testa a obtenção dos detalhes de um produto existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - Os dados do produto retornado correspondem ao cadastro.
        - O campo 'image_url' está presente.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria uma categoria e um produto.
    cat_resp = await client.post("/categories", json={"name": "Gaming"},
                                 headers={"Authorization": f"Bearer {token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]

    prod_resp = await client.post("/products", json={
        "name": "Console",
        "description": "Console de última geração",
        "price": 1500.00,
        "stock": 10,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    resp = await client.get(f"/products/{product_id}",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "product" in data
    product = data["product"]
    assert product["id"] == product_id
    assert product["name"] == "Console"
    assert "image_url" in product

@pytest.mark.asyncio
async def test_update_product_success(test_client_fixture):
    """
    Testa a atualização dos dados de um produto existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - Os dados do produto são atualizados conforme esperado.
        - O campo 'image_url' está presente.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria uma categoria e um produto.
    cat_resp = await client.post("/categories", json={"name": "Acessórios"},
                                 headers={"Authorization": f"Bearer {token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]

    prod_resp = await client.post("/products", json={
        "name": "Fone de Ouvido",
        "description": "Fone com cancelamento de ruído",
        "price": 300.00,
        "stock": 15,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    update_resp = await client.put(f"/products/{product_id}", json={
        "name": "Fone de Ouvido Wireless",
        "price": 350.00
    }, headers={"Authorization": f"Bearer {token}"})
    assert update_resp.status == 200
    update_data = await update_resp.json()
    product = update_data["product"]
    assert product["name"] == "Fone de Ouvido Wireless"
    assert product["price"] == 350.00
    assert "image_url" in product

@pytest.mark.asyncio
async def test_delete_product_success(test_client_fixture):
    """
    Testa a deleção de um produto existente.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A resposta contém a mensagem de sucesso na deleção.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria uma categoria e um produto.
    cat_resp = await client.post("/categories", json={"name": "Eletrodomésticos"},
                                 headers={"Authorization": f"Bearer {token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]

    prod_resp = await client.post("/products", json={
        "name": "Geladeira",
        "description": "Geladeira duplex",
        "price": 2000.00,
        "stock": 3,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    delete_resp = await client.delete(f"/products/{product_id}",
                                      headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status == 200
    delete_data = await delete_resp.json()
    assert "Produto deletado com sucesso" in delete_data["message"]

@pytest.mark.asyncio
async def test_list_products(test_client_fixture):
    """
    Testa a listagem de todos os produtos.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A lista de produtos contém os itens cadastrados.
        - Cada produto possui o campo 'image_url'.
    """
    client = test_client_fixture
    token = await get_admin_token(client)
    # Cria uma categoria e alguns produtos para teste.
    cat_resp = await client.post("/categories", json={"name": "Utilidades"},
                                 headers={"Authorization": f"Bearer {token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]

    await client.post("/products", json={
        "name": "Liquidificador",
        "description": "Liquidificador potente",
        "price": 150.00,
        "stock": 8,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})
    await client.post("/products", json={
        "name": "Micro-ondas",
        "description": "Micro-ondas digital",
        "price": 500.00,
        "stock": 4,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get("/products",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "products" in data
    assert isinstance(data["products"], list)
    assert len(data["products"]) >= 2
    for prod in data["products"]:
        assert "image_url" in prod
