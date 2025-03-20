# D:\3xDigital\app\services\dashboard_service.py
"""
dashboard_service.py

Módulo responsável pela geração de métricas e dados para os dashboards
e relatórios do sistema 3xDigital.

Funcionalidades principais:
    - Cálculo de métricas gerais para o dashboard administrativo
    - Cálculo de métricas de vendas e comissões para afiliados
    - Geração de dados para gráficos e visualizações
    - Preparação de dados para exportação de relatórios

Regras de Negócio:
    - Dados são filtrados por período (dia, semana, mês, ano)
    - Afiliados só visualizam dados relacionados a suas próprias vendas
    - Administradores podem visualizar dados de todos os afiliados
    - Relatórios podem ser exportados em diferentes formatos

Dependências:
    - SQLAlchemy para consultas de dados
    - app.models.database para acesso às entidades
    - app.models.finance_models para dados financeiros
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import extract

from app.models.database import Affiliate, Sale, Order, Product, User
from app.models.finance_models import AffiliateTransaction, WithdrawalRequest
from app.config.settings import TIMEZONE


async def get_admin_dashboard_metrics(
    session: AsyncSession,
    period: str = 'month'
) -> Dict:
    """
    Retorna métricas gerais para o dashboard administrativo.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        period (str): Período para filtrar dados ('day', 'week', 'month', 'year')
        
    Returns:
        Dict: Métricas para o dashboard administrativo
    """
    # Define o intervalo de datas baseado no período
    now = TIMEZONE()
    start_date = None
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        # Padrão: mês atual
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Total de vendas e receita no período
    sales_query = select(
        func.count(Sale.id).label('total_sales'),
        func.sum(Order.total).label('total_revenue'),
        func.sum(Sale.commission).label('total_commissions')
    ).join(
        Order, Sale.order_id == Order.id
    ).where(Sale.created_at >= start_date)
    
    result = await session.execute(sales_query)
    sales_metrics = result.mappings().one_or_none()
    
    # Total de afiliados ativos (com pelo menos uma venda no período)
    active_affiliates_query = select(
        func.count(func.distinct(Sale.affiliate_id))
    ).where(Sale.created_at >= start_date)
    
    result = await session.execute(active_affiliates_query)
    active_affiliates = result.scalar_one_or_none() or 0
    
    # Total de pedidos completos no período
    orders_query = select(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total).label('total_order_amount')
    ).where(
        and_(
            Order.created_at >= start_date,
            Order.status.in_(['delivered', 'shipped'])
        )
    )
    
    result = await session.execute(orders_query)
    orders_metrics = result.mappings().one_or_none()
    
    # Total de pedidos pendentes
    pending_orders_query = select(
        func.count(Order.id)
    ).where(
        and_(
            Order.created_at >= start_date,
            Order.status.in_(['pending', 'processing'])
        )
    )
    
    result = await session.execute(pending_orders_query)
    pending_orders = result.scalar_one_or_none() or 0
    
    # Total de usuários cadastrados no período
    new_users_query = select(
        func.count(User.id)
    ).where(User.created_at >= start_date)
    
    result = await session.execute(new_users_query)
    new_users = result.scalar_one_or_none() or 0
    
    # Compilando todas as métricas
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "sales": {
            "total_count": sales_metrics['total_sales'] or 0,
            "total_revenue": sales_metrics['total_revenue'] or 0,
            "total_commissions": sales_metrics['total_commissions'] or 0
        },
        "affiliates": {
            "active_count": active_affiliates,
        },
        "orders": {
            "total_count": orders_metrics['total_orders'] or 0,
            "total": orders_metrics['total_order_amount'] or 0,
            "pending_count": pending_orders
        },
        "users": {
            "new_count": new_users
        }
    }


async def get_sales_by_time(
    session: AsyncSession,
    period: str = 'month',
    affiliate_id: Optional[int] = None
) -> List[Dict]:
    """
    Retorna dados de vendas agrupados por tempo para gráficos.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        period (str): Período para filtrar dados ('day', 'week', 'month', 'year')
        affiliate_id (Optional[int]): ID do afiliado para filtrar dados
        
    Returns:
        List[Dict]: Dados de vendas agrupados por tempo
    """
    now = TIMEZONE()
    start_date = None
    group_by = None
    
    # Define o intervalo e agrupamento com base no período
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        group_by = extract('hour', Sale.created_at)
        label_format = "%H:00"
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        group_by = extract('day', Sale.created_at)
        label_format = "%A"  # dia da semana
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = extract('day', Sale.created_at)
        label_format = "%d"  # dia do mês
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = extract('month', Sale.created_at)
        label_format = "%B"  # nome do mês
    else:
        # Padrão: mês atual, agrupado por dia
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = extract('day', Sale.created_at)
        label_format = "%d"
    
    # Constrói a query base
    query = select(
        group_by.label('time_group'),
        func.count(Sale.id).label('count'),
        func.sum(Order.total).label('amount'),
        func.sum(Sale.commission).label('commission')
    ).join(
        Order, Sale.order_id == Order.id
    ).where(Sale.created_at >= start_date)
    
    # Filtra por afiliado se especificado
    if affiliate_id is not None:
        query = query.where(Sale.affiliate_id == affiliate_id)
    
    # Agrupa e ordena
    query = query.group_by(group_by).order_by(group_by)
    
    # Executa a query
    result = await session.execute(query)
    sales_by_time = result.mappings().all()
    
    # Formata o resultado
    formatted_data = []
    for row in sales_by_time:
        # Para dia e semana, precisamos reconstruir a data
        date_value = None
        if period == 'day':
            date_value = start_date.replace(hour=int(row['time_group']))
        elif period == 'week':
            # Calcula o dia da semana
            weekday = int(row['time_group']) - 1
            date_value = start_date + timedelta(days=weekday)
        elif period == 'month':
            date_value = start_date.replace(day=int(row['time_group']))
        elif period == 'year':
            date_value = start_date.replace(month=int(row['time_group']))
        
        label = date_value.strftime(label_format) if date_value else str(row['time_group'])
        
        formatted_data.append({
            "label": label,
            "count": row['count'] or 0,
            "amount": row['amount'] or 0,
            "commission": row['commission'] or 0
        })
    
    return formatted_data


async def get_top_products(
    session: AsyncSession,
    limit: int = 5,
    period: str = 'month',
    affiliate_id: Optional[int] = None
) -> List[Dict]:
    """
    Retorna os produtos mais vendidos no período.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        limit (int): Limite de produtos a retornar
        period (str): Período para filtrar dados ('day', 'week', 'month', 'year')
        affiliate_id (Optional[int]): ID do afiliado para filtrar dados
        
    Returns:
        List[Dict]: Lista dos produtos mais vendidos
    """
    # Define o intervalo de datas baseado no período
    now = TIMEZONE()
    start_date = None
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        # Padrão: mês atual
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Constrói a query base para contar produtos vendidos
    from app.models.database import OrderItem
    
    query = select(
        Product.id,
        Product.name,
        Product.price,
        func.sum(OrderItem.quantity).label('total_sold'),
        func.sum(OrderItem.quantity * OrderItem.price).label('total_revenue')
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).where(
        Order.created_at >= start_date
    )
    
    # Filtra por afiliado se especificado
    if affiliate_id is not None:
        query = query.join(
            Sale, Order.id == Sale.order_id
        ).where(
            Sale.affiliate_id == affiliate_id
        )
    
    # Agrupa, ordena e limita os resultados
    query = query.group_by(
        Product.id
    ).order_by(
        desc('total_sold')
    ).limit(limit)
    
    # Executa a query
    result = await session.execute(query)
    top_products = result.mappings().all()
    
    # Formata o resultado
    return [
        {
            "id": p['id'],
            "name": p['name'],
            "price": p['price'],
            "total_sold": p['total_sold'] or 0,
            "total_revenue": p['total_revenue'] or 0
        }
        for p in top_products
    ]


async def get_top_affiliates(
    session: AsyncSession,
    limit: int = 5,
    period: str = 'month'
) -> List[Dict]:
    """
    Retorna os afiliados com melhor desempenho no período.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        limit (int): Limite de afiliados a retornar
        period (str): Período para filtrar dados ('day', 'week', 'month', 'year')
        
    Returns:
        List[Dict]: Lista dos afiliados com melhor desempenho
    """
    # Define o intervalo de datas baseado no período
    now = TIMEZONE()
    start_date = None
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        # Padrão: mês atual
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Query para afiliados com mais vendas e comissões
    query = select(
        Affiliate.id,
        User.name,
        User.email,
        func.count(Sale.id).label('total_sales'),
        func.sum(Order.total).label('total'),
        func.sum(Sale.commission).label('total_commission')
    ).join(
        User, Affiliate.user_id == User.id
    ).join(
        Sale, Affiliate.id == Sale.affiliate_id
    ).join(
        Order, Sale.order_id == Order.id
    ).where(
        Sale.created_at >= start_date
    ).group_by(
        Affiliate.id, User.name, User.email
    ).order_by(
        desc('total_commission')
    ).limit(limit)
    
    # Executa a query
    result = await session.execute(query)
    top_affiliates = result.mappings().all()
    
    # Formata o resultado
    return [
        {
            "id": a['id'],
            "name": a['name'],
            "email": a['email'],
            "total_sales": a['total_sales'] or 0,
            "total": a['total'] or 0,
            "total_commission": a['total_commission'] or 0
        }
        for a in top_affiliates
    ]


async def get_affiliate_dashboard_metrics(
    session: AsyncSession,
    affiliate_id: int,
    period: str = 'month'
) -> Dict:
    """
    Retorna métricas específicas para o dashboard de um afiliado.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (int): ID do afiliado
        period (str): Período para filtrar dados ('day', 'week', 'month', 'year')
        
    Returns:
        Dict: Métricas para o dashboard do afiliado
    """
    # Define o intervalo de datas baseado no período
    now = TIMEZONE()
    start_date = None
    previous_start = None
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        previous_start = start_date - timedelta(days=1)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        previous_start = start_date - timedelta(weeks=1)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 1:
            previous_start = start_date.replace(year=start_date.year - 1, month=12)
        else:
            previous_start = start_date.replace(month=start_date.month - 1)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_start = start_date.replace(year=start_date.year - 1)
    else:
        # Padrão: mês atual
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 1:
            previous_start = start_date.replace(year=start_date.year - 1, month=12)
        else:
            previous_start = start_date.replace(month=start_date.month - 1)
    
    # Total de vendas e comissões no período atual
    current_query = select(
        func.count(Sale.id).label('total_sales'),
        func.sum(Order.total).label('total'),
        func.sum(Sale.commission).label('total_commission')
    ).join(
        Order, Sale.order_id == Order.id
    ).where(
        and_(
            Sale.affiliate_id == affiliate_id,
            Sale.created_at >= start_date,
            Sale.created_at <= now
        )
    )
    
    result = await session.execute(current_query)
    current_metrics = result.mappings().one_or_none()
    
    # Total de vendas e comissões no período anterior
    previous_query = select(
        func.count(Sale.id).label('total_sales'),
        func.sum(Order.total).label('total'),
        func.sum(Sale.commission).label('total_commission')
    ).join(
        Order, Sale.order_id == Order.id
    ).where(
        and_(
            Sale.affiliate_id == affiliate_id,
            Sale.created_at >= previous_start,
            Sale.created_at < start_date
        )
    )
    
    result = await session.execute(previous_query)
    previous_metrics = result.mappings().one_or_none()
    
    # Calcula variações percentuais
    current_sales = current_metrics['total_sales'] or 0
    previous_sales = previous_metrics['total_sales'] or 0
    sales_change = calculate_percentage_change(current_sales, previous_sales)
    
    current_amount = current_metrics['total'] or 0
    previous_amount = previous_metrics['total'] or 0
    amount_change = calculate_percentage_change(current_amount, previous_amount)
    
    current_commission = current_metrics['total_commission'] or 0
    previous_commission = previous_metrics['total_commission'] or 0
    commission_change = calculate_percentage_change(current_commission, previous_commission)
    
    # Obtém status das solicitações de saque
    withdrawal_query = select(
        WithdrawalRequest.status,
        func.count(WithdrawalRequest.id).label('count')
    ).where(
        WithdrawalRequest.affiliate_id == affiliate_id
    ).group_by(
        WithdrawalRequest.status
    )
    
    result = await session.execute(withdrawal_query)
    withdrawal_stats = {r['status']: r['count'] for r in result.mappings().all()}
    
    # Compila todas as métricas
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "sales": {
            "current": current_sales,
            "previous": previous_sales,
            "change_percent": sales_change
        },
        "revenue": {
            "current": current_amount,
            "previous": previous_amount,
            "change_percent": amount_change
        },
        "commission": {
            "current": current_commission,
            "previous": previous_commission,
            "change_percent": commission_change
        },
        "withdrawals": {
            "pending": withdrawal_stats.get('pending', 0),
            "approved": withdrawal_stats.get('approved', 0),
            "rejected": withdrawal_stats.get('rejected', 0),
            "paid": withdrawal_stats.get('paid', 0)
        }
    }


def calculate_percentage_change(current_value, previous_value):
    """
    Calcula a variação percentual entre dois valores.
    
    Args:
        current_value: Valor atual
        previous_value: Valor anterior
        
    Returns:
        float: Variação percentual ou 0 se não for possível calcular
    """
    if previous_value == 0:
        return 100 if current_value > 0 else 0
    
    return ((current_value - previous_value) / previous_value) * 100 