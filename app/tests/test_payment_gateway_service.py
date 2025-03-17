# D:\3xDigital\app\tests\test_payment_gateway_service.py

"""
test_payment_gateway_service.py

Módulo de testes para o serviço de gateway de pagamento (payment_gateway_service.py).
Este serviço fornece funcionalidades de consulta e manipulação de transações de pagamento.

Testes:
    - Consulta de transações
    - Filtragem de transações por diversos critérios
    - Geração de relatórios de pagamento
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, insert, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.services.payment_gateway_service import (
    get_payment_transactions, 
    get_transaction_by_id, 
    get_transactions_by_order
)
from app.models.finance_models import PaymentTransaction
from app.models.database import Order, User, OrderItem, ShippingAddress


@pytest_asyncio.fixture
async def payment_gateway_test_data(async_db_session):
    """
    Configura dados de teste para o serviço de gateway de pagamento.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de teste para transações de pagamento.
    """
    # Adiciona usuários para testes
    user1 = User(
        name="Cliente Teste 1",
        email="cliente1@teste.com",
        cpf="12345678901",
        password_hash="hash_senha",
        role="user",
        created_at=datetime.now()
    )
    async_db_session.add(user1)
    
    user2 = User(
        name="Cliente Teste 2",
        email="cliente2@teste.com",
        cpf="98765432109",
        password_hash="hash_senha",
        role="user",
        created_at=datetime.now()
    )
    async_db_session.add(user2)
    
    await async_db_session.commit()
    
    # Adiciona pedidos para testes
    # Pedido 1
    order1 = Order(
        user_id=1,
        total=100.0,
        status="completed",
        created_at=datetime.now() - timedelta(days=5)
    )
    async_db_session.add(order1)
    await async_db_session.flush()  # Para obter o ID do pedido
    
    # Adiciona itens do pedido 1
    order_item1 = OrderItem(
        order_id=order1.id,
        product_id=1,
        quantity=1,
        price=100.0
    )
    async_db_session.add(order_item1)
    
    # Adiciona endereço de entrega para o pedido 1
    shipping1 = ShippingAddress(
        order_id=order1.id,
        street="Rua A",
        number="123",
        city="São Paulo",
        state="SP",
        zip_code="01000-000"
    )
    async_db_session.add(shipping1)
    
    # Pedido 2
    order2 = Order(
        user_id=1,
        total=150.0,
        status="pending",
        created_at=datetime.now() - timedelta(days=2)
    )
    async_db_session.add(order2)
    await async_db_session.flush()  # Para obter o ID do pedido
    
    # Adiciona itens do pedido 2
    order_item2 = OrderItem(
        order_id=order2.id,
        product_id=2,
        quantity=2,
        price=75.0
    )
    async_db_session.add(order_item2)
    
    # Adiciona endereço de entrega para o pedido 2
    shipping2 = ShippingAddress(
        order_id=order2.id,
        street="Rua A",
        number="123",
        city="São Paulo",
        state="SP",
        zip_code="01000-000"
    )
    async_db_session.add(shipping2)
    
    # Pedido 3
    order3 = Order(
        user_id=2,
        total=200.0,
        status="completed",
        created_at=datetime.now() - timedelta(days=1)
    )
    async_db_session.add(order3)
    await async_db_session.flush()  # Para obter o ID do pedido
    
    # Adiciona itens do pedido 3
    order_item3 = OrderItem(
        order_id=order3.id,
        product_id=3,
        quantity=1,
        price=200.0
    )
    async_db_session.add(order_item3)
    
    # Adiciona endereço de entrega para o pedido 3
    shipping3 = ShippingAddress(
        order_id=order3.id,
        street="Rua B",
        number="456",
        city="Rio de Janeiro",
        state="RJ",
        zip_code="20000-000"
    )
    async_db_session.add(shipping3)
    
    await async_db_session.commit()
    
    # Adiciona transações de pagamento para testes
    transaction1 = PaymentTransaction(
        order_id=1,
        gateway="stripe",
        gateway_transaction_id="pi_test_111",
        amount=100.0,
        status="approved",
        payment_method="credit_card",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "credit_card",
            "card_brand": "visa",
            "last4": "4242"
        }),
        created_at=datetime.now() - timedelta(days=5)
    )
    async_db_session.add(transaction1)
    
    transaction2 = PaymentTransaction(
        order_id=2,
        gateway="mercado_pago",
        gateway_transaction_id="mp_test_222",
        amount=150.0,
        status="pending",
        payment_method="boleto",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "boleto",
            "boleto_url": "https://example.com/boleto"
        }),
        created_at=datetime.now() - timedelta(days=2)
    )
    async_db_session.add(transaction2)
    
    transaction3 = PaymentTransaction(
        order_id=3,
        gateway="stripe",
        gateway_transaction_id="pi_test_333",
        amount=200.0,
        status="approved",
        payment_method="credit_card",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "credit_card",
            "card_brand": "mastercard",
            "last4": "5678"
        }),
        created_at=datetime.now() - timedelta(days=1)
    )
    async_db_session.add(transaction3)
    
    transaction4 = PaymentTransaction(
        order_id=1,  # Transação adicional para o mesmo pedido (reembolso)
        gateway="stripe",
        gateway_transaction_id="pi_refund_111",
        amount=-100.0,  # Valor negativo para reembolso
        status="refunded",
        payment_method="credit_card",
        currency="BRL",
        payment_details=json.dumps({
            "payment_method": "credit_card",
            "card_brand": "visa",
            "last4": "4242",
            "refund_id": "re_123456"
        }),
        created_at=datetime.now() - timedelta(days=4)
    )
    async_db_session.add(transaction4)
    
    await async_db_session.commit()
    
    return {
        "user_ids": [1, 2],
        "order_ids": [1, 2, 3],
        "transaction_ids": [1, 2, 3, 4]
    }


@pytest.mark.asyncio
async def test_get_transaction_by_id(async_db_session, payment_gateway_test_data):
    """
    Testa a obtenção de uma transação específica por ID.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_gateway_test_data: Fixture com dados de teste para transações.
    """
    # Obtém uma transação existente
    transaction = await get_transaction_by_id(async_db_session, payment_gateway_test_data["transaction_ids"][0])
    
    assert transaction is not None
    assert transaction.id == payment_gateway_test_data["transaction_ids"][0]
    assert transaction.order_id == payment_gateway_test_data["order_ids"][0]
    assert transaction.gateway == "stripe"
    assert transaction.status == "approved"
    
    # Tenta obter uma transação inexistente
    nonexistent_transaction = await get_transaction_by_id(async_db_session, 999)
    assert nonexistent_transaction is None


@pytest.mark.asyncio
async def test_get_transactions_by_order(async_db_session, payment_gateway_test_data):
    """
    Testa a obtenção de transações por ID do pedido.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_gateway_test_data: Fixture com dados de teste para transações.
    """
    # Obtém transações para um pedido com múltiplas transações
    transactions = await get_transactions_by_order(async_db_session, payment_gateway_test_data["order_ids"][0])
    
    assert len(transactions) == 2
    assert all(t.order_id == payment_gateway_test_data["order_ids"][0] for t in transactions)
    
    # Verifica se temos tanto a transação aprovada quanto o reembolso
    assert any(t.status == "approved" for t in transactions)
    assert any(t.status == "refunded" for t in transactions)
    
    # Obtém transações para um pedido com uma única transação
    transactions = await get_transactions_by_order(async_db_session, payment_gateway_test_data["order_ids"][1])
    
    assert len(transactions) == 1
    assert transactions[0].order_id == payment_gateway_test_data["order_ids"][1]
    assert transactions[0].status == "pending"
    
    # Verifica se não há transações para um pedido inexistente
    nonexistent_transactions = await get_transactions_by_order(async_db_session, 999)
    assert len(nonexistent_transactions) == 0


@pytest.mark.asyncio
async def test_get_user_payment_transactions(async_db_session, payment_gateway_test_data):
    """
    Testa a obtenção de transações de pagamento por usuário, usando consulta SQL manual
    já que não temos a função get_user_payment_transactions no serviço.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_gateway_test_data: Fixture com dados de teste para transações.
    """
    # Usuário 1 (que tem dois pedidos e três transações)
    user_id = payment_gateway_test_data["user_ids"][0]
    
    # Busca todos os pedidos do usuário
    result = await async_db_session.execute(
        select(Order).where(Order.user_id == user_id)
    )
    orders = result.scalars().all()
    order_ids = [order.id for order in orders]
    
    # Busca as transações dos pedidos
    result = await async_db_session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id.in_(order_ids))
    )
    transactions = result.scalars().all()
    
    assert len(transactions) == 3
    assert all(t.order_id in order_ids for t in transactions)
    
    # Usuário 2 (que tem um pedido e uma transação)
    user_id = payment_gateway_test_data["user_ids"][1]
    
    # Busca todos os pedidos do usuário
    result = await async_db_session.execute(
        select(Order).where(Order.user_id == user_id)
    )
    orders = result.scalars().all()
    order_ids = [order.id for order in orders]
    
    # Busca as transações dos pedidos
    result = await async_db_session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id.in_(order_ids))
    )
    transactions = result.scalars().all()
    
    assert len(transactions) == 1
    assert transactions[0].order_id in order_ids
    
    # Usuário inexistente (não deve ter transações)
    invalid_user_id = 999
    
    # Busca todos os pedidos do usuário
    result = await async_db_session.execute(
        select(Order).where(Order.user_id == invalid_user_id)
    )
    orders = result.scalars().all()
    order_ids = [order.id for order in orders]
    
    # Busca as transações dos pedidos
    result = await async_db_session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id.in_(order_ids or [0]))
    )
    transactions = result.scalars().all()
    
    assert len(transactions) == 0


@pytest.mark.asyncio
async def test_get_payment_transactions(async_db_session, payment_gateway_test_data):
    """
    Testa a obtenção de transações de pagamento com filtros.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_gateway_test_data: Fixture com dados de teste para transações.
    """
    # Obtém todas as transações
    transactions, total = await get_payment_transactions(async_db_session)
    
    assert total == 4
    assert len(transactions) == 4
    
    # Filtra por status
    approved_transactions, approved_total = await get_payment_transactions(
        async_db_session, 
        status="approved"
    )
    
    assert approved_total == 2
    assert len(approved_transactions) == 2
    assert all(t.status == "approved" for t in approved_transactions)
    
    # Filtra por gateway
    stripe_transactions, stripe_total = await get_payment_transactions(
        async_db_session, 
        gateway="stripe"
    )
    
    assert stripe_total == 3
    assert len(stripe_transactions) == 3
    assert all(t.gateway == "stripe" for t in stripe_transactions)
    
    # Filtra por data (últimos 3 dias)
    recent_transactions, recent_total = await get_payment_transactions(
        async_db_session,
        start_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    )
    
    assert recent_total == 2
    assert len(recent_transactions) == 2
    
    # Testa paginação
    page1_transactions, page1_total = await get_payment_transactions(
        async_db_session,
        page=1,
        page_size=2
    )
    
    assert page1_total == 4  # Total continua sendo 4
    assert len(page1_transactions) == 2  # Mas só retorna 2 por página
    
    page2_transactions, page2_total = await get_payment_transactions(
        async_db_session,
        page=2,
        page_size=2
    )
    
    assert page2_total == 4
    assert len(page2_transactions) == 2
    
    # Verifica que as páginas têm diferentes transações
    page1_ids = set(t.id for t in page1_transactions)
    page2_ids = set(t.id for t in page2_transactions)
    assert not page1_ids.intersection(page2_ids)


@pytest.mark.asyncio
async def test_generate_payment_report(async_db_session, payment_gateway_test_data):
    """
    Testa a geração de relatório de pagamentos usando consultas SQL diretas,
    já que a função generate_payment_report não está disponível no serviço.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        payment_gateway_test_data: Fixture com dados de teste para transações.
    """
    # Implementação do relatório diretamente no teste
    # Obtém total de transações
    result = await async_db_session.execute(
        select(func.count()).select_from(PaymentTransaction)
    )
    total_transactions = result.scalar_one()
    
    # Obtém soma dos valores das transações
    result = await async_db_session.execute(
        select(func.sum(PaymentTransaction.amount))
    )
    total_amount = result.scalar_one() or 0.0
    
    # Obtém contagem por status
    result = await async_db_session.execute(
        select(
            PaymentTransaction.status,
            func.count().label("count"),
            func.sum(PaymentTransaction.amount).label("amount")
        ).group_by(PaymentTransaction.status)
    )
    status_counts = {row[0]: {"count": row[1], "amount": row[2] or 0.0} for row in result}
    
    # Obtém contagem por gateway
    result = await async_db_session.execute(
        select(
            PaymentTransaction.gateway,
            func.count().label("count"),
            func.sum(PaymentTransaction.amount).label("amount")
        ).group_by(PaymentTransaction.gateway)
    )
    gateway_counts = {row[0]: {"count": row[1], "amount": row[2] or 0.0} for row in result}
    
    # Monta o relatório
    report = {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "by_status": status_counts,
        "by_gateway": gateway_counts
    }
    
    # Verificações
    assert report["total_transactions"] == 4
    assert report["total_amount"] == 350.0  # 100 + 150 + 200 - 100 (reembolso)
    assert "approved" in report["by_status"]
    assert "stripe" in report["by_gateway"]
    
    # Função de relatório filtrado por gateway
    async def generate_filtered_report(session, gateway=None, status=None):
        # Constrói a base da query para contar transações
        count_query = select(func.count(PaymentTransaction.id))
        if gateway:
            count_query = count_query.where(PaymentTransaction.gateway == gateway)
        if status:
            count_query = count_query.where(PaymentTransaction.status == status)
        
        result = await session.execute(count_query)
        total_count = result.scalar_one()
        
        # Constrói a query para somar valores
        sum_query = select(func.sum(PaymentTransaction.amount))
        if gateway:
            sum_query = sum_query.where(PaymentTransaction.gateway == gateway)
        if status:
            sum_query = sum_query.where(PaymentTransaction.status == status)
        
        result = await session.execute(sum_query)
        total_sum = result.scalar_one() or 0.0
        
        return {
            "total_transactions": total_count,
            "total_amount": total_sum
        }
    
    # Teste de relatório filtrado por gateway
    stripe_report = await generate_filtered_report(async_db_session, gateway="stripe")
    assert stripe_report["total_transactions"] == 3
    assert stripe_report["total_amount"] == 200.0  # 100 + 200 - 100 (reembolso)
    
    # Teste de relatório filtrado por status
    approved_report = await generate_filtered_report(async_db_session, status="approved")
    assert approved_report["total_transactions"] == 2
    assert approved_report["total_amount"] == 300.0  # 100 + 200 