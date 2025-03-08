# D:\#3xDigital\app\tests\test_order_service.py

"""
test_order_service.py

Este módulo contém os testes unitários para o OrderService, responsável pela lógica
de gerenciamento de pedidos, itens, status e integração com afiliados.

Fixtures:
    async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

Test Functions:
    - test_create_order: Testa a criação de um pedido.
    - test_validate_order_items: Testa a validação de itens do pedido.
    - test_list_orders: Testa a listagem de pedidos.
    - test_get_order: Testa a obtenção de detalhes de um pedido.
    - test_update_order_status: Testa a atualização do status de um pedido.
    - test_delete_order: Testa a exclusão de um pedido.
    - test_process_affiliate_sale: Testa o processamento de vendas por afiliados.
"""

import pytest
from app.services.order_service import OrderService
from app.services.auth_service import AuthService
from app.services.affiliate_service import AffiliateService
from app.models.database import Product, Category, User

@pytest.mark.asyncio
async def test_create_order(async_db_session):
    """
    Testa a criação de um pedido com itens válidos.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o pedido é criado com sucesso.
        - Verifica se o estoque dos produtos é atualizado.
        - Verifica se o processo falha com itens inválidos.
    """
    # Criar um usuário
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Order Test User",
        email="order_user@example.com",
        cpf="12345678901",
        password="testpass",
        role="user"
    )
    
    # Criar uma categoria
    category = Category(name="Test Category")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Criar produtos
    product1 = Product(
        name="Test Product 1",
        description="Description 1",
        price=50.0,
        stock=10,
        category_id=category.id
    )
    product2 = Product(
        name="Test Product 2",
        description="Description 2",
        price=75.0,
        stock=5,
        category_id=category.id
    )
    async_db_session.add_all([product1, product2])
    await async_db_session.commit()
    await async_db_session.refresh(product1)
    await async_db_session.refresh(product2)
    
    # Definir itens do pedido
    items = [
        {"product_id": product1.id, "quantity": 2},
        {"product_id": product2.id, "quantity": 1}
    ]
    
    # Criar pedido
    order_service = OrderService(async_db_session)
    result = await order_service.create_order(user.id, items)
    
    # Verificações
    assert result["success"] is True
    assert result["data"]["order_id"] is not None
    assert result["data"]["total"] == (2 * 50.0) + (1 * 75.0)  # 175.0
    
    # Verificar se o estoque foi atualizado
    await async_db_session.refresh(product1)
    await async_db_session.refresh(product2)
    assert product1.stock == 8  # 10 - 2
    assert product2.stock == 4  # 5 - 1
    
    # Testar com produto inexistente
    invalid_items = [{"product_id": 9999, "quantity": 1}]
    result = await order_service.create_order(user.id, invalid_items)
    assert result["success"] is False
    assert "não encontrado" in result["error"]
    
    # Testar com estoque insuficiente
    over_stock_items = [{"product_id": product2.id, "quantity": 10}]  # Só tem 4 em estoque
    result = await order_service.create_order(user.id, over_stock_items)
    assert result["success"] is False
    assert "insuficiente" in result["error"]

@pytest.mark.asyncio
async def test_validate_order_items(async_db_session):
    """
    Testa a validação de itens do pedido.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se itens válidos são aceitos.
        - Verifica se o total é calculado corretamente.
        - Verifica se validações de estoque e produto inexistente funcionam.
    """
    # Criar produtos para teste
    category = Category(name="Validation Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="Validation Product",
        description="For validation",
        price=100.0,
        stock=5,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Inicializar service
    order_service = OrderService(async_db_session)
    
    # Testar com itens válidos
    valid_items = [{"product_id": product.id, "quantity": 2}]
    result = await order_service.validate_order_items(valid_items)
    assert result["success"] is True
    assert result["data"]["total"] == 200.0
    assert len(result["data"]["order_items"]) == 1
    
    # Testar com produto inexistente
    invalid_items = [{"product_id": 9999, "quantity": 1}]
    result = await order_service.validate_order_items(invalid_items)
    assert result["success"] is False
    assert "não encontrado" in result["error"]
    
    # Testar com estoque insuficiente
    over_stock_items = [{"product_id": product.id, "quantity": 10}]
    result = await order_service.validate_order_items(over_stock_items)
    assert result["success"] is False
    assert "insuficiente" in result["error"]

@pytest.mark.asyncio
async def test_list_orders(async_db_session):
    """
    Testa a listagem de pedidos.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a lista de pedidos é retornada corretamente.
        - Verifica se os dados dos pedidos estão completos.
    """
    # Criar usuário
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="List Orders User",
        email="list_orders@example.com",
        cpf="98765432101",
        password="testpass",
        role="user"
    )
    
    # Criar dois pedidos diretamente no banco
    order_service = OrderService(async_db_session)
    
    # Criar categoria e produto para os pedidos
    category = Category(name="List Orders Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="List Orders Product",
        description="For listing",
        price=25.0,
        stock=20,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Criar dois pedidos
    items = [{"product_id": product.id, "quantity": 1}]
    await order_service.create_order(user.id, items)
    await order_service.create_order(user.id, items)
    
    # Listar pedidos
    result = await order_service.list_orders()
    
    # Verificações
    assert result["success"] is True
    assert len(result["data"]) == 2
    for order in result["data"]:
        assert "id" in order
        assert "user_id" in order
        assert order["user_id"] == user.id
        assert "total" in order
        assert order["total"] == 25.0
        assert "status" in order
        assert order["status"] == "processing"

@pytest.mark.asyncio
async def test_get_order(async_db_session):
    """
    Testa a obtenção dos detalhes de um pedido.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se os detalhes do pedido são retornados corretamente.
        - Verifica controle de acesso (usuário só pode ver próprios pedidos).
        - Verifica comportamento com pedido inexistente.
    """
    # Criar dois usuários
    auth_service = AuthService(async_db_session)
    user1 = await auth_service.create_user(
        name="Order Owner",
        email="order_owner@example.com",
        cpf="11223344556",
        password="testpass",
        role="user"
    )
    user2 = await auth_service.create_user(
        name="Other User",
        email="other_user@example.com",
        cpf="66778899001",
        password="testpass",
        role="user"
    )
    
    # Criar categoria e produto
    category = Category(name="Get Order Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="Get Order Product",
        description="For getting",
        price=30.0,
        stock=10,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Criar pedido para user1
    order_service = OrderService(async_db_session)
    items = [{"product_id": product.id, "quantity": 2}]
    create_result = await order_service.create_order(user1.id, items)
    order_id = create_result["data"]["order_id"]
    
    # User1 buscando o próprio pedido
    result = await order_service.get_order(order_id, user1.id, False)
    assert result["success"] is True
    assert result["data"]["id"] == order_id
    assert result["data"]["user_id"] == user1.id
    assert result["data"]["total"] == 60.0
    assert "items" in result["data"]
    assert len(result["data"]["items"]) == 1
    
    # User2 tentando acessar o pedido do User1 (não admin)
    result = await order_service.get_order(order_id, user2.id, False)
    assert result["success"] is False
    assert "Acesso negado" in result["error"]
    
    # Admin pode acessar qualquer pedido
    result = await order_service.get_order(order_id, user2.id, True)
    assert result["success"] is True
    
    # Tentar acessar pedido inexistente
    result = await order_service.get_order(9999, user1.id, False)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_update_order_status(async_db_session):
    """
    Testa a atualização do status de um pedido.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o status é atualizado corretamente.
        - Verifica validação de status inválido.
        - Verifica comportamento com pedido inexistente.
    """
    # Criar usuário
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Status Update User",
        email="status_update@example.com",
        cpf="99887766554",
        password="testpass",
        role="user"
    )
    
    # Criar categoria e produto
    category = Category(name="Status Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="Status Product",
        description="For status update",
        price=40.0,
        stock=10,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Criar pedido
    order_service = OrderService(async_db_session)
    items = [{"product_id": product.id, "quantity": 1}]
    create_result = await order_service.create_order(user.id, items)
    order_id = create_result["data"]["order_id"]
    
    # Atualizar status - válido
    result = await order_service.update_order_status(order_id, "shipped")
    assert result["success"] is True
    assert result["data"]["status"] == "shipped"
    
    # Atualizar status - inválido
    result = await order_service.update_order_status(order_id, "invalid_status")
    assert result["success"] is False
    assert "inválido" in result["error"]
    
    # Atualizar status - pedido inexistente
    result = await order_service.update_order_status(9999, "delivered")
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_delete_order(async_db_session):
    """
    Testa a exclusão de um pedido.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o pedido é excluído corretamente.
        - Verifica comportamento com pedido inexistente.
    """
    # Criar usuário
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Delete Order User",
        email="delete_order@example.com",
        cpf="12312312312",
        password="testpass",
        role="user"
    )
    
    # Criar categoria e produto
    category = Category(name="Delete Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="Delete Product",
        description="For deletion",
        price=35.0,
        stock=8,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Criar pedido
    order_service = OrderService(async_db_session)
    items = [{"product_id": product.id, "quantity": 1}]
    create_result = await order_service.create_order(user.id, items)
    order_id = create_result["data"]["order_id"]
    
    # Excluir pedido
    result = await order_service.delete_order(order_id)
    assert result["success"] is True
    assert result["data"]["id"] == order_id
    
    # Tentar obter o pedido excluído
    get_result = await order_service.get_order(order_id, user.id, False)
    assert get_result["success"] is False
    assert "não encontrado" in get_result["error"]
    
    # Tentar excluir pedido inexistente
    result = await order_service.delete_order(9999)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_process_affiliate_sale(async_db_session):
    """
    Testa o processamento de vendas por afiliados.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a comissão é calculada e registrada corretamente.
        - Verifica comportamento com código de afiliado inválido.
        - Verifica comportamento com afiliado bloqueado.
    """
    # Criar usuário comprador
    auth_service = AuthService(async_db_session)
    buyer = await auth_service.create_user(
        name="Affiliate Buyer",
        email="affiliate_buyer@example.com",
        cpf="45645645645",
        password="testpass",
        role="user"
    )
    
    # Criar usuário afiliado
    affiliate_user = await auth_service.create_user(
        name="Order Affiliate",
        email="order_affiliate@example.com",
        cpf="78978978978",
        password="testpass",
        role="user"
    )
    
    # Criar afiliado aprovado
    affiliate_service = AffiliateService(async_db_session)
    affiliate_result = await affiliate_service.request_affiliation(affiliate_user.id, 0.08)  # 8% de comissão
    affiliate_id = affiliate_result["data"]["id"]
    referral_code = affiliate_result["data"]["referral_code"]
    await affiliate_service.update_affiliate(affiliate_id, request_status="approved")
    
    # Criar categoria e produto
    category = Category(name="Affiliate Sale Category")
    async_db_session.add(category)
    await async_db_session.commit()
    
    product = Product(
        name="Affiliate Sale Product",
        description="For affiliate commission",
        price=200.0,
        stock=5,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    # Criar pedido
    order_service = OrderService(async_db_session)
    items = [{"product_id": product.id, "quantity": 1}]
    create_result = await order_service.create_order(buyer.id, items)
    order_id = create_result["data"]["order_id"]
    
    # Processar venda com código de afiliado
    result = await order_service.process_affiliate_sale(order_id, 200.0, referral_code)
    assert result is not None
    assert result["affiliate_id"] == affiliate_id
    assert result["commission"] == 16.0  # 8% de R$200
    
    # Processar com código inválido
    result = await order_service.process_affiliate_sale(order_id, 200.0, "INVALID")
    assert result is None
    
    # Bloquear afiliado e tentar processar
    await affiliate_service.update_affiliate(affiliate_id, request_status="blocked")
    result = await order_service.process_affiliate_sale(order_id, 200.0, referral_code)
    assert result is None 