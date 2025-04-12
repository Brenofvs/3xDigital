# D:\3xDigital\app\tests\test_orders_views.py


"""
test_orders_views.py

Este módulo contém os testes de integração para os endpoints de gerenciamento de pedidos.

Fixtures:
    test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.
    get_admin_token: Função auxiliar que gera um token JWT para um usuário administrador.
    get_user_token: Função auxiliar que gera um token JWT para um usuário com papel 'affiliate' (ou 'user').

Test Functions:
    - test_create_order_success(test_client_fixture)
    - test_create_order_insufficient_stock(test_client_fixture)
    - test_list_orders_as_admin(test_client_fixture)
    - test_list_orders_as_user_forbidden(test_client_fixture)
    - test_update_order_status_as_admin(test_client_fixture)
    - test_delete_order_as_admin(test_client_fixture)
    - test_list_orders_with_pagination(test_client_fixture)
"""

import pytest
from app.tests.utils.auth_utils import get_admin_token, get_user_token

@pytest.mark.asyncio
async def test_create_order_success(test_client_fixture):
    """
    Testa a criação de um pedido com sucesso.

    O teste registra um usuário (por meio do token de usuário) e cria um produto para
    então criar um pedido com uma quantidade válida. Verifica se o endpoint retorna
    status HTTP 201 e se a resposta contém um 'order_id' e o total calculado.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 201.
        - A resposta contém 'order_id' e 'total'.
    """
    client = test_client_fixture
    # Obter token de usuário para criar pedido (qualquer usuário autenticado pode criar pedido)
    admin = await get_admin_token(client)
    token = await get_user_token(client)

    # 1. Cria um produto (como admin) para ser usado no pedido
    prod_resp = await client.post(
        "/products",
        json={
            "name": "Teclado Mecânico",
            "description": "Teclado RGB",
            "price": 250.00,
            "stock": 10
        },
        headers={"Authorization": f"Bearer {admin}"}
    )
    assert prod_resp.status == 201, "Falha ao criar produto."
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    # 2. Cria o pedido (como user) com 2 unidades do produto
    order_resp = await client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert order_resp.status == 201, "Falha na criação do pedido."
    order_data = await order_resp.json()
    assert "order_id" in order_data, "ID do pedido não retornado."
    assert "total" in order_data, "Total do pedido não retornado."


@pytest.mark.asyncio
async def test_create_order_insufficient_stock(test_client_fixture):
    """
    Testa a criação de um pedido com quantidade superior ao estoque disponível.

    O teste registra um usuário, cria um produto com estoque limitado e tenta criar
    um pedido com quantidade maior que o disponível, esperando status HTTP 400.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 400.
        - A mensagem de erro indica "Estoque insuficiente".
    """
    client = test_client_fixture
    # Tokens
    admin = await get_admin_token(client)
    token = await get_user_token(client)

    # 1. Cria um produto com estoque 1 (como admin)
    prod_resp = await client.post(
        "/products",
        json={
            "name": "Mouse Gamer",
            "description": "Mouse 16000 DPI",
            "price": 150.00,
            "stock": 1
        },
        headers={"Authorization": f"Bearer {admin}"}
    )
    assert prod_resp.status == 201, "Falha ao criar produto com estoque limitado."
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    # 2. Tenta criar um pedido (como user) com quantidade 5 (acima do estoque)
    order_resp = await client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 5}]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert order_resp.status == 400, "O pedido com estoque insuficiente deveria retornar 400."
    error_data = await order_resp.json()
    assert "Estoque insuficiente" in error_data["error"]


@pytest.mark.asyncio
async def test_list_orders_as_admin(test_client_fixture):
    """
    Testa a listagem de todos os pedidos como administrador.

    O teste utiliza um token de administrador para acessar o endpoint de listagem de pedidos,
    que deve retornar status HTTP 200 e uma lista de pedidos com metadados de paginação.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 200.
        - A resposta contém a chave 'orders'.
        - A resposta contém metadados de paginação.
    """
    client = test_client_fixture
    token = await get_admin_token(client)

    # Nenhum pedido criado ainda, mas deve retornar 200 e lista vazia
    resp = await client.get("/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200, "Admin deve conseguir listar todos os pedidos."
    data = await resp.json()
    assert "orders" in data, "Chave 'orders' ausente na resposta."
    
    # Verifica os metadados de paginação
    assert "meta" in data, "Metadados de paginação ausentes."
    assert "page" in data["meta"]
    assert "page_size" in data["meta"]
    assert "total_count" in data["meta"]
    assert "total_pages" in data["meta"]
    assert data["meta"]["page"] == 1  # Página padrão


@pytest.mark.asyncio
async def test_list_orders_as_user_forbidden(test_client_fixture):
    """
    Testa que um usuário comum não pode listar todos os pedidos.

    Utiliza um token de usuário comum para acessar o endpoint de listagem, que deve retornar
    status HTTP 403, pois apenas administradores podem visualizar todos os pedidos.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 403.
    """
    client = test_client_fixture
    token = await get_user_token(client)

    resp = await client.get("/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403, "Usuário não admin não deve listar todos os pedidos."


@pytest.mark.asyncio
async def test_update_order_status_as_admin(test_client_fixture):
    """
    Testa a atualização do status de um pedido por um administrador.

    O teste cria um produto e um pedido, em seguida utiliza um token de administrador para
    alterar o status do pedido para 'shipped'. O endpoint deve retornar status HTTP 200
    e uma mensagem confirmando a atualização.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 200.
        - A mensagem confirma a alteração para o novo status.
    """
    client = test_client_fixture
    token = await get_admin_token(client)

    # 1. Criar produto (como admin)
    prod_resp = await client.post(
        "/products",
        json={
            "name": "SSD 1TB",
            "description": "SSD rápido",
            "price": 500.00,
            "stock": 2
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert prod_resp.status == 201, "Falha ao criar produto para teste de pedido."
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    # 2. Criar um pedido usando esse produto (como admin; pois admin também é um user válido)
    order_resp = await client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert order_resp.status == 201, "Falha na criação do pedido para atualização."
    order_data = await order_resp.json()
    order_id = order_data["order_id"]

    # 3. Atualizar status do pedido para "shipped"
    update_resp = await client.put(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert update_resp.status == 200, "Admin deve conseguir atualizar o status do pedido."
    update_data = await update_resp.json()
    assert "shipped" in update_data["message"], "Mensagem não indica mudança para 'shipped'."


@pytest.mark.asyncio
async def test_delete_order_as_admin(test_client_fixture):
    """
    Testa a deleção de um pedido por um administrador.

    O teste cria um produto e um pedido, depois utiliza um token de administrador
    para deletá-lo. O endpoint deve retornar status HTTP 200 e uma mensagem de sucesso.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Status HTTP 200.
        - A resposta contém a mensagem de sucesso na deleção.
    """
    client = test_client_fixture
    token = await get_admin_token(client)

    # 1. Criar produto (como admin)
    prod_resp = await client.post(
        "/products",
        json={
            "name": "Cadeira Gamer",
            "description": "Cadeira ergonômica",
            "price": 1200.00,
            "stock": 5
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert prod_resp.status == 201, "Falha ao criar produto para teste de deleção de pedido."
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    # 2. Criar um pedido com esse produto (como admin)
    order_resp = await client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert order_resp.status == 201, "Falha na criação do pedido para deleção."
    order_data = await order_resp.json()
    order_id = order_data["order_id"]

    # 3. Deletar o pedido
    delete_resp = await client.delete(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_resp.status == 200, "Admin deve conseguir deletar o pedido."
    delete_data = await delete_resp.json()
    assert "Pedido deletado com sucesso" in delete_data["message"], "Mensagem de sucesso ausente."


@pytest.mark.asyncio
async def test_list_orders_with_pagination(test_client_fixture):
    """
    Testa a paginação na listagem de pedidos.

    Cria vários pedidos e testa a paginação com diferentes parâmetros.

    Args:
        test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.

    Asserts:
        - Os parâmetros de paginação (page, page_size) funcionam corretamente.
        - O filtro por status funciona corretamente.
        - Os metadados de paginação correspondem aos parâmetros fornecidos.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)

    # 1. Cria um produto para usar nos pedidos
    prod_resp = await client.post(
        "/products",
        json={
            "name": "Produto para Pedidos",
            "description": "Produto para testar paginação de pedidos",
            "price": 50.00,
            "stock": 100  # Estoque suficiente para vários pedidos
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert prod_resp.status == 201, "Falha ao criar produto para testes."
    prod_data = await prod_resp.json()
    product_id = prod_data["product"]["id"]

    # 2. Cria vários pedidos (5)
    for i in range(5):
        await client.post(
            "/orders",
            json={"items": [{"product_id": product_id, "quantity": 1}]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    # 3. Testa a paginação: primeira página com 2 itens por página
    resp = await client.get(
        "/orders?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status == 200
    data = await resp.json()
    
    assert len(data["orders"]) <= 2  # Não mais que o page_size
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 2
    assert data["meta"]["total_count"] >= 5  # Pelo menos os 5 que criamos
    
    # 4. Testa a segunda página
    resp = await client.get(
        "/orders?page=2&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status == 200
    data2 = await resp.json()
    
    assert len(data2["orders"]) <= 2
    assert data2["meta"]["page"] == 2
    
    # 5. Verifica se os pedidos da página 2 são diferentes dos da página 1
    page1_ids = [o["id"] for o in data["orders"]]
    page2_ids = [o["id"] for o in data2["orders"]]
    
    # Garante que não há pedidos duplicados entre as páginas
    for oid in page2_ids:
        assert oid not in page1_ids
    
    # 6. Testa o filtro por status (todos os pedidos devem ter status inicial "processing")
    resp = await client.get(
        "/orders?status=processing",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status == 200
    status_data = await resp.json()
    
    assert len(status_data["orders"]) >= 5
    assert all(order["status"] == "processing" for order in status_data["orders"])
