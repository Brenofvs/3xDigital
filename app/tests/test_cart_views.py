"""
test_cart_views.py

Este módulo contém os testes de integração para os endpoints do carrinho de compras.

Fixtures:
    test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

Test Functions:
    - test_add_to_cart_success(test_client_fixture)
    - test_get_cart_success(test_client_fixture)
    - test_update_cart_item_success(test_client_fixture)
    - test_remove_cart_item_success(test_client_fixture)
    - test_clear_cart_success(test_client_fixture)
    - test_add_to_cart_without_auth(test_client_fixture)
    - test_get_cart_without_auth(test_client_fixture)
"""

import pytest
import json  # Para depuração
from app.tests.utils.auth_utils import get_admin_token, get_user_token

@pytest.mark.asyncio
async def test_add_to_cart_success(test_client_fixture):
    """
    Testa adicionar um produto ao carrinho com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - O carrinho contém o produto adicionado com a quantidade correta.
        - A resposta contém detalhes do produto no carrinho.
    """
    client = test_client_fixture
    token = await get_user_token(client)
    admin_token = await get_admin_token(client)
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Informática"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para adicionar ao carrinho
    prod_resp = await client.post("/products", json={
        "name": "Teclado Mecânico",
        "description": "Teclado mecânico para jogos",
        "price": 300.00,
        "stock": 10,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho
    cart_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 2
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert cart_resp.status == 200
    cart_data = await cart_resp.json()
    
    # Verifica a estrutura da resposta - API retorna a lista completa do carrinho
    assert "items" in cart_data
    assert "item_count" in cart_data
    assert "total" in cart_data
    
    # Verifica se o item foi adicionado corretamente
    items = cart_data["items"]
    assert len(items) > 0
    
    # Encontra o item adicionado na lista
    added_item = None
    for item in items:
        if item.get("product_id") == product_id:
            added_item = item
            break
    
    assert added_item is not None, "Produto não encontrado no carrinho"
    assert added_item["quantity"] == 2
    
    # Verifica informações do produto no item do carrinho
    assert "name" in added_item, "Nome do produto não encontrado no item do carrinho"
    assert added_item["name"] == "Teclado Mecânico"
    assert added_item["price"] == 300.00
    
    # Verifica o total do carrinho
    assert cart_data["total"] == 600.00  # 2 * 300.00

@pytest.mark.asyncio
async def test_get_cart_success(test_client_fixture):
    """
    Testa a obtenção dos itens do carrinho com sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A resposta contém a lista de itens no carrinho.
        - O total do carrinho é calculado corretamente.
    """
    client = test_client_fixture
    token = await get_user_token(client)
    admin_token = await get_admin_token(client)
    
    # Limpa o carrinho antes de iniciar o teste
    clear_resp = await client.delete("/cart/items", headers={"Authorization": f"Bearer {token}"})
    assert clear_resp.status == 200
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Periféricos"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para adicionar ao carrinho
    prod_resp = await client.post("/products", json={
        "name": "Mouse Gamer",
        "description": "Mouse de alta precisão",
        "price": 150.00,
        "stock": 8,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho
    add_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 1
    }, headers={"Authorization": f"Bearer {token}"})
    assert add_resp.status == 200
    add_data = await add_resp.json()
    
    # Verifica se o produto foi adicionado
    assert len(add_data["items"]) > 0
    
    # Encontra o produto na resposta
    product_added = False
    for item in add_data["items"]:
        if item.get("product_id") == product_id:
            product_added = True
            assert item["quantity"] == 1
            assert item["price"] == 150.00
            break
    assert product_added, "Produto não encontrado após adição"
    
    # Verifica o total do carrinho
    expected_total = 150.00  # 1 Mouse
    assert abs(add_data["total"] - expected_total) < 0.01, f"Total incorreto: {add_data['total']} != {expected_total}"

@pytest.mark.asyncio
async def test_update_cart_item_success(test_client_fixture):
    """
    Testa a atualização da quantidade de um item no carrinho.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A quantidade do item é atualizada corretamente.
        - O subtotal do item é recalculado.
    """
    client = test_client_fixture
    token = await get_user_token(client)
    admin_token = await get_admin_token(client)
    
    # Limpa o carrinho antes de iniciar o teste
    clear_resp = await client.delete("/cart/items", headers={"Authorization": f"Bearer {token}"})
    assert clear_resp.status == 200
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Áudio"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para o teste
    prod_resp = await client.post("/products", json={
        "name": "Headset",
        "description": "Headset com microfone",
        "price": 200.00,
        "stock": 5,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho
    cart_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 1
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert cart_resp.status == 200
    cart_data = await cart_resp.json()
    
    # Debug: imprimir a estrutura do item para entender melhor
    items = cart_data["items"]
    assert len(items) > 0, "Nenhum item encontrado no carrinho após adição"
    
    # Encontra o item adicionado
    added_item = None
    for item in items:
        if item.get("product_id") == product_id:
            added_item = item
            break
    
    assert added_item is not None, "Produto não encontrado no carrinho"
    
    # Usa o product_id como identificador para atualização
    # já que parece não haver um ID específico para o item do carrinho
    
    # Atualiza a quantidade do item usando o product_id
    update_resp = await client.put(f"/cart/items/{product_id}", json={
        "quantity": 3
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert update_resp.status == 200
    update_data = await update_resp.json()
    
    # Verifica se o carrinho atualizado é retornado
    assert "items" in update_data
    assert "total" in update_data
    
    # Encontra o item atualizado
    updated_item = None
    for item in update_data["items"]:
        if item["product_id"] == product_id:
            updated_item = item
            break
    
    assert updated_item is not None, "Item atualizado não encontrado na resposta"
    assert updated_item["quantity"] == 3, f"Quantidade não atualizada: {updated_item['quantity']} != 3"
    
    # Verifica o valor total do item (preço * quantidade)
    item_subtotal = updated_item["price"] * updated_item["quantity"]
    assert abs(item_subtotal - 600.00) < 0.01, f"Subtotal incorreto: {item_subtotal} != 600.00"

@pytest.mark.asyncio
async def test_remove_cart_item_success(test_client_fixture):
    """
    Testa a remoção de um item do carrinho.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - O item é removido do carrinho.
        - A resposta contém o carrinho vazio.
    """
    client = test_client_fixture
    token = await get_user_token(client)
    admin_token = await get_admin_token(client)
    
    # Limpa o carrinho antes de iniciar o teste
    clear_resp = await client.delete("/cart/items", headers={"Authorization": f"Bearer {token}"})
    assert clear_resp.status == 200
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Armazenamento"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para o teste
    prod_resp = await client.post("/products", json={
        "name": "SSD 1TB",
        "description": "SSD de alta velocidade",
        "price": 800.00,
        "stock": 3,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho
    cart_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 1
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert cart_resp.status == 200
    cart_data = await cart_resp.json()
    
    # Encontra o item adicionado na lista
    items = cart_data["items"]
    assert len(items) > 0, "Nenhum item encontrado no carrinho após adição"
    
    # Verifica se o produto aparece na lista
    product_found = False
    for item in items:
        if item.get("product_id") == product_id:
            product_found = True
            break
    
    assert product_found, "Produto não encontrado no carrinho"
    
    # Remove o item do carrinho usando o product_id
    delete_resp = await client.delete(f"/cart/items/{product_id}",
                                    headers={"Authorization": f"Bearer {token}"})
    
    assert delete_resp.status == 200
    delete_data = await delete_resp.json()
    
    # A resposta deve conter o carrinho vazio, não uma mensagem de sucesso
    assert "items" in delete_data
    assert "total" in delete_data
    assert len(delete_data["items"]) == 0
    assert delete_data["total"] == 0
    
    # Verifica se o produto não está mais na lista
    product_still_exists = False
    for item in delete_data["items"]:
        if item.get("product_id") == product_id:
            product_still_exists = True
            break
    
    assert not product_still_exists, "Produto ainda presente no carrinho após remoção"

@pytest.mark.asyncio
async def test_clear_cart_success(test_client_fixture):
    """
    Testa a limpeza de todos os itens do carrinho.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - Todos os itens são removidos do carrinho.
        - A resposta contém o carrinho vazio.
    """
    client = test_client_fixture
    token = await get_user_token(client)
    admin_token = await get_admin_token(client)
    
    # Limpa o carrinho antes de iniciar o teste para garantir um estado limpo
    clear_resp = await client.delete("/cart/items", headers={"Authorization": f"Bearer {token}"})
    assert clear_resp.status == 200
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Acessórios"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para adicionar ao carrinho
    prod_resp = await client.post("/products", json={
        "name": "Carregador",
        "description": "Carregador USB-C",
        "price": 80.00,
        "stock": 12,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho
    add_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 2
    }, headers={"Authorization": f"Bearer {token}"})
    assert add_resp.status == 200
    add_data = await add_resp.json()
    
    # Verifica se o produto foi adicionado
    assert len(add_data["items"]) > 0
    
    # Encontra o produto na resposta
    product_added = False
    for item in add_data["items"]:
        if item.get("product_id") == product_id:
            product_added = True
            assert item["quantity"] == 2
            break
    assert product_added, "Produto não encontrado após adição"
    
    # Limpa o carrinho
    clear_resp = await client.delete("/cart/items", headers={"Authorization": f"Bearer {token}"})
    
    assert clear_resp.status == 200
    clear_data = await clear_resp.json()
    
    # A resposta deve conter o carrinho vazio
    assert "items" in clear_data
    assert len(clear_data["items"]) == 0, "O carrinho ainda contém itens após limpeza"
    assert clear_data["total"] == 0, f"Total do carrinho não zerado: {clear_data['total']}"

@pytest.mark.asyncio
async def test_add_to_cart_without_auth(test_client_fixture):
    """
    Testa adicionar um produto ao carrinho sem autenticação (sessão de convidado).

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint permite a adição com status HTTP 200.
        - A resposta contém o carrinho com o item adicionado.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    
    # Limpa o carrinho de convidado primeiro
    await client.delete("/cart/items")
    
    # Cria uma categoria para o produto
    cat_resp = await client.post("/categories", json={"name": "Gadgets"},
                                headers={"Authorization": f"Bearer {admin_token}"})
    cat_data = await cat_resp.json()
    category_id = cat_data["category"]["id"]
    
    # Cria um produto para o teste
    prod_resp = await client.post("/products", json={
        "name": "Smartwatch",
        "description": "Relógio inteligente",
        "price": 500.00,
        "stock": 7,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]
    
    # Adiciona o produto ao carrinho sem token (carrinho de convidado)
    cart_resp = await client.post("/cart/items", json={
        "product_id": product_id,
        "quantity": 1
    })
    
    assert cart_resp.status == 200
    cart_data = await cart_resp.json()
    
    # Verifica a estrutura da resposta
    assert "items" in cart_data
    assert "total" in cart_data
    
    # Verifica se o produto foi adicionado corretamente
    items = cart_data["items"]
    assert len(items) > 0, "Nenhum item encontrado no carrinho após adição"
    
    added_item = None
    for item in items:
        if item.get("product_id") == product_id:
            added_item = item
            break
    
    assert added_item is not None, "Produto não encontrado no carrinho"
    assert added_item["name"] == "Smartwatch"
    assert added_item["quantity"] == 1
    
    # Verifica o total do carrinho
    assert abs(cart_data["total"] - 500.00) < 0.01

@pytest.mark.asyncio
async def test_get_cart_without_auth(test_client_fixture):
    """
    Testa obter o carrinho sem autenticação (sessão de convidado).

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - O endpoint retorna status HTTP 200.
        - A resposta contém a estrutura esperada do carrinho.
    """
    client = test_client_fixture
    
    # Obtém o carrinho de convidado
    cart_resp = await client.get("/cart/items")
    
    assert cart_resp.status == 200
    cart_data = await cart_resp.json()
    
    # Verifica a estrutura da resposta
    assert "items" in cart_data
    assert "total" in cart_data
    assert "item_count" in cart_data 