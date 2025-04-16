# D:\3xDigital\app\tests\test_affiliate_service.py

"""
test_affiliate_service.py

Este módulo contém os testes unitários para o AffiliateService, responsável pela lógica
de gerenciamento de afiliados, comissões e vendas.

Fixtures:
    async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

Test Functions:
    - test_request_affiliation: Testa a solicitação de afiliação.
    - test_get_affiliate_link: Testa a obtenção do link de afiliado.
    - test_get_affiliate_sales: Testa a obtenção das vendas e comissões de um afiliado.
    - test_update_affiliate: Testa a atualização dos dados de um afiliado.
    - test_list_affiliate_requests: Testa a listagem de solicitações de afiliação pendentes.
    - test_register_sale: Testa o registro de uma venda para um afiliado.
"""

import pytest
from sqlalchemy import select
from app.services.affiliate_service import AffiliateService
from app.services.auth_service import AuthService
from app.models.database import Order, Sale, Category, Product, OrderItem, Affiliate

@pytest.mark.asyncio
async def test_request_affiliation(async_db_session):
    """
    Testa a solicitação de afiliação por um usuário.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a solicitação foi criada com sucesso.
        - Verifica se o código de referência foi gerado.
        - Verifica se o status inicial é 'pending'.
    """
    # Criar um usuário para o teste
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Affiliate Test",
        email="affiliate@example.com",
        cpf="12345678901",
        password="testpass",
        role="user"
    )
    
    # Solicitar afiliação
    affiliate_service = AffiliateService(async_db_session)
    result = await affiliate_service.request_affiliation(user.id, 0.05)
    
    # Verificações
    assert result["success"] is True
    assert "referral_code" in result["data"]
    assert result["data"]["status"] == "pending"
    
    # Verificar que não é possível solicitar novamente
    result2 = await affiliate_service.request_affiliation(user.id, 0.05)
    assert result2["success"] is False
    assert "já existente" in result2["error"]

@pytest.mark.asyncio
async def test_get_affiliate_link(async_db_session):
    """
    Testa a obtenção do link de afiliado.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o link é gerado corretamente para afiliados aprovados.
        - Verifica se afiliados pendentes/bloqueados não podem obter link.
    """
    # Criar um usuário e afiliado para o teste
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Link Tester",
        email="linktester@example.com",
        cpf="98765432101",
        password="testpass",
        role="user"
    )
    
    # Solicitar afiliação
    affiliate_service = AffiliateService(async_db_session)
    result = await affiliate_service.request_affiliation(user.id, 0.05)
    affiliate_id = result["data"]["id"]
    
    # Tentar obter link com status pendente
    result = await affiliate_service.get_affiliate_link(user.id, "https://example.com")
    assert result["success"] is False
    assert "inativo" in result["error"]
    
    # Aprovar afiliado
    await affiliate_service.update_affiliate(affiliate_id, request_status="approved")
    
    # Tentar obter link com status aprovado
    result = await affiliate_service.get_affiliate_link(user.id, "https://example.com")
    assert result["success"] is True
    assert "https://example.com/?ref=" in result["data"]

@pytest.mark.asyncio
async def test_get_affiliate_sales(async_db_session):
    """
    Testa a obtenção das vendas e comissões de um afiliado.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se as vendas são listadas corretamente.
        - Verifica se afiliados pendentes/bloqueados não podem ver vendas.
    """
    # Criar usuário e afiliado
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Sales Tester",
        email="salestester@example.com",
        cpf="45678912301",
        password="testpass",
        role="user"
    )
    
    # Solicitar e aprovar afiliação
    affiliate_service = AffiliateService(async_db_session)
    result = await affiliate_service.request_affiliation(user.id, 0.05)
    affiliate_id = result["data"]["id"]
    await affiliate_service.update_affiliate(affiliate_id, request_status="approved")
    
    # Obter o afiliado para uso direto
    affiliate = await affiliate_service.get_affiliate_by_id(affiliate_id)
    
    # Criar um pedido e uma venda manualmente (simulando o fluxo)
    order = Order(user_id=user.id, status="processing", total=100.0)
    async_db_session.add(order)
    await async_db_session.commit()
    await async_db_session.refresh(order)
    
    sale = Sale(
        affiliate_id=affiliate.id,
        order_id=order.id,
        commission=5.0  # 5% de R$100
    )
    async_db_session.add(sale)
    await async_db_session.commit()
    
    # Obter vendas do afiliado
    result = await affiliate_service.get_affiliate_sales(user.id)
    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["order_id"] == order.id
    assert result["data"][0]["commission"] == 5.0
    
    # Bloquear afiliado e verificar que não pode mais ver vendas
    await affiliate_service.update_affiliate(affiliate_id, request_status="blocked")
    result = await affiliate_service.get_affiliate_sales(user.id)
    assert result["success"] is False
    assert "inativo" in result["error"]

@pytest.mark.asyncio
async def test_update_affiliate(async_db_session):
    """
    Testa a atualização dos dados de um afiliado.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a comissão e o status são atualizados corretamente.
        - Verifica se o erro é tratado para um ID inexistente.
    """
    # Criar usuário e afiliado
    auth_service = AuthService(async_db_session)
    user = await auth_service.create_user(
        name="Update Tester",
        email="updatetester@example.com",
        cpf="78945612301",
        password="testpass",
        role="user"
    )
    
    # Solicitar afiliação
    affiliate_service = AffiliateService(async_db_session)
    result = await affiliate_service.request_affiliation(user.id, 0.05)
    affiliate_id = result["data"]["id"]
    
    # Atualizar comissão e status
    result = await affiliate_service.update_affiliate(
        affiliate_id, 
        commission_rate=0.10, 
        request_status="approved"
    )
    
    # Verificações
    assert result["success"] is True
    assert result["data"]["commission_rate"] == 0.10
    assert result["data"]["request_status"] == "approved"
    
    # Tentar atualizar um ID inexistente
    result = await affiliate_service.update_affiliate(999999, commission_rate=0.15)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_list_affiliate_requests(async_db_session):
    """
    Testa a listagem de solicitações de afiliação pendentes.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se todas as solicitações pendentes são listadas.
        - Verifica se solicitações aprovadas/bloqueadas não são listadas.
    """
    # Criar vários usuários com diferentes status de afiliação
    auth_service = AuthService(async_db_session)
    affiliate_service = AffiliateService(async_db_session)
    
    # Usuário 1 - Pendente
    user1 = await auth_service.create_user(
        name="Pending User 1",
        email="pending1@example.com",
        cpf="11111111111",
        password="testpass",
        role="user"
    )
    await affiliate_service.request_affiliation(user1.id, 0.05)
    
    # Usuário 2 - Pendente
    user2 = await auth_service.create_user(
        name="Pending User 2",
        email="pending2@example.com",
        cpf="22222222222",
        password="testpass",
        role="user"
    )
    await affiliate_service.request_affiliation(user2.id, 0.06)
    
    # Usuário 3 - Aprovado
    user3 = await auth_service.create_user(
        name="Approved User",
        email="approved@example.com",
        cpf="33333333333",
        password="testpass",
        role="user"
    )
    result = await affiliate_service.request_affiliation(user3.id, 0.07)
    await affiliate_service.update_affiliate(result["data"]["id"], request_status="approved")
    
    # Listar solicitações pendentes
    result = await affiliate_service.list_affiliate_requests()
    assert result["success"] is True
    assert len(result["data"]) == 2
    
    # Verificar que apenas solicitações pendentes estão na lista
    for item in result["data"]:
        assert item["user_id"] in [user1.id, user2.id]

@pytest.mark.asyncio
async def test_register_sale(async_db_session):
    """Testa o registro de venda com comissões personalizadas."""
    # Criar usuário e afiliado
    user = await AuthService(async_db_session).create_user(
        name="Usuário Teste",
        email="teste@email.com",
        cpf="12345678901",
        password="testpass",
        role="user"
    )
    
    # Criar um afiliado aprovado
    affiliate = await AffiliateService(async_db_session).request_affiliation(user.id, 0.10)
    affiliate_id = affiliate["data"]["id"]
    referral_code = affiliate["data"]["referral_code"]
    await AffiliateService(async_db_session).update_affiliate(affiliate_id, request_status="approved")
    
    # Criar categoria
    category = Category(name="Categoria Teste")
    async_db_session.add(category)
    await async_db_session.commit()
    
    # Criar produtos com diferentes tipos de comissão
    # Produto 1 - comissão padrão
    product1 = Product(
        name="Produto comissão padrão", 
        description="Descrição do produto 1",
        price=100.0,
        stock=5,
        category_id=category.id,
        has_custom_commission=False
    )
    
    # Produto 2 - comissão percentual personalizada
    product2 = Product(
        name="Produto comissão percentual", 
        description="Descrição do produto 2",
        price=200.0,
        stock=5,
        category_id=category.id,
        has_custom_commission=True,
        commission_type='percentage',
        commission_value=5.0  # 5%
    )
    
    # Produto 3 - comissão fixa personalizada
    product3 = Product(
        name="Produto comissão fixa", 
        description="Descrição do produto 3",
        price=150.0,
        stock=5,
        category_id=category.id,
        has_custom_commission=True,
        commission_type='fixed',
        commission_value=8.0  # R$8 por unidade
    )
    
    async_db_session.add_all([product1, product2, product3])
    await async_db_session.commit()
    await async_db_session.refresh(product1)
    await async_db_session.refresh(product2)
    await async_db_session.refresh(product3)
    
    # Criar um pedido
    order = Order(user_id=user.id, status="completed", total=500.0)
    async_db_session.add(order)
    await async_db_session.commit()  # Comitar o pedido primeiro para obter o ID
    await async_db_session.refresh(order)
    
    # Adicionar itens ao pedido
    order_item1 = OrderItem(
        order_id=order.id, 
        product_id=product1.id, 
        quantity=1, 
        price=product1.price
    )
    
    order_item2 = OrderItem(
        order_id=order.id, 
        product_id=product2.id, 
        quantity=1, 
        price=product2.price
    )
    
    order_item3 = OrderItem(
        order_id=order.id, 
        product_id=product3.id, 
        quantity=2, 
        price=product3.price
    )
    
    async_db_session.add_all([order_item1, order_item2, order_item3])
    await async_db_session.commit()
    
    # Testar registro de venda com cálculo de comissão personalizada
    affiliate_service = AffiliateService(async_db_session)
    result = await affiliate_service.register_sale(order_id=order.id, referral_code=referral_code)
    
    # Verificar sucesso da operação
    assert result["success"] is True
    assert "Venda registrada com sucesso" in result["message"]
    assert result["data"] is not None
    
    # Verificar comissão total
    # Produto 1: 100.0 * 0.10 = 10.0
    # Produto 2: 200.0 * 0.05 = 10.0
    # Produto 3: 8.0 * 2 = 16.0
    expected_commission = 36.0
    assert round(result["data"]["commission"], 2) == expected_commission
    
    # Verificar se a venda foi registrada no banco
    sale_query = await async_db_session.execute(
        select(Sale).where(Sale.order_id == order.id)
    )
    sale = sale_query.scalar_one_or_none()
    assert sale is not None
    assert sale.affiliate_id == affiliate_id
    assert sale.order_id == order.id
    assert round(sale.commission, 2) == expected_commission
    
    # Testar com código de referência inválido
    result = await affiliate_service.register_sale(order_id=999, referral_code="CODIGO_INVALIDO")
    assert result["success"] is False
    assert "Afiliado não encontrado com código de referência" in result["message"]
    assert result["data"] is None
    
    # Testar com afiliado bloqueado
    # Alterar status do afiliado para bloqueado
    await affiliate_service.update_affiliate(affiliate_id, request_status="blocked")
    result = await affiliate_service.register_sale(order_id=order.id, referral_code=referral_code)
    assert result["success"] is False
    assert "Afiliado não está aprovado" in result["message"]
    assert result["data"] is None 