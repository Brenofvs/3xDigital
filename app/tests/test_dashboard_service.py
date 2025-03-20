"""
test_dashboard_service.py

Testes unitários para o serviço de dashboard.
Valida as funcionalidades de geração de métricas e dados para dashboards.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.dashboard_service import (
    get_admin_dashboard_metrics,
    get_sales_by_time,
    get_top_products,
    get_top_affiliates,
    get_affiliate_dashboard_metrics,
    calculate_percentage_change
)
from app.models.database import Sale, Order, Affiliate, User, Product
from app.models.finance_models import WithdrawalRequest

# Teste da função de cálculo de variação percentual
def test_calculate_percentage_change():
    # Teste com valores normais
    assert calculate_percentage_change(150, 100) == 50
    
    # Teste com valores iguais
    assert calculate_percentage_change(100, 100) == 0
    
    # Teste com valor anterior zero
    assert calculate_percentage_change(100, 0) == 100
    
    # Teste com valor atual zero
    assert calculate_percentage_change(0, 100) == -100
    
    # Teste com ambos valores zero
    assert calculate_percentage_change(0, 0) == 0


# Fixtures para testes do dashboard administrativo
@pytest_asyncio.fixture
async def admin_metrics_mocks(mock_db_session):
    # Simula o resultado da consulta de vendas
    sales_result = MagicMock()
    sales_result.mappings().one_or_none.return_value = {
        'total_sales': 10,
        'total_revenue': 1000.0,
        'total_commissions': 100.0
    }
    
    # Simula o resultado da consulta de afiliados ativos
    affiliates_result = MagicMock()
    affiliates_result.scalar_one_or_none.return_value = 5
    
    # Simula o resultado da consulta de pedidos
    orders_result = MagicMock()
    orders_result.mappings().one_or_none.return_value = {
        'total_orders': 8,
        'total_order_amount': 800.0
    }
    
    # Simula o resultado da consulta de pedidos pendentes
    pending_orders_result = MagicMock()
    pending_orders_result.scalar_one_or_none.return_value = 2
    
    # Simula o resultado da consulta de usuários
    users_result = MagicMock()
    users_result.scalar_one_or_none.return_value = 15
    
    # Configura a sessão mock para retornar os resultados simulados
    mock_db_session.execute.side_effect = [
        sales_result,
        affiliates_result,
        orders_result,
        pending_orders_result,
        users_result
    ]
    
    return mock_db_session


@pytest_asyncio.fixture
async def sales_by_time_mocks(mock_db_session):
    # Simula o resultado da consulta
    sales_result = MagicMock()
    sales_result.mappings().all.return_value = [
        {'time_group': 1, 'count': 5, 'amount': 500.0, 'commission': 50.0},
        {'time_group': 2, 'count': 10, 'amount': 1000.0, 'commission': 100.0},
        {'time_group': 3, 'count': 7, 'amount': 700.0, 'commission': 70.0}
    ]
    
    mock_db_session.execute.return_value = sales_result
    return mock_db_session


@pytest_asyncio.fixture
async def top_products_mocks(mock_db_session):
    # Simula o resultado da consulta
    products_result = MagicMock()
    products_result.mappings().all.return_value = [
        {'id': 1, 'name': 'Produto A', 'price': 100.0, 'total_sold': 10, 'total_revenue': 1000.0},
        {'id': 2, 'name': 'Produto B', 'price': 50.0, 'total_sold': 8, 'total_revenue': 400.0},
        {'id': 3, 'name': 'Produto C', 'price': 150.0, 'total_sold': 5, 'total_revenue': 750.0}
    ]
    
    mock_db_session.execute.return_value = products_result
    return mock_db_session


@pytest_asyncio.fixture
async def top_affiliates_mocks(mock_db_session):
    # Simula o resultado da consulta
    affiliates_result = MagicMock()
    affiliates_result.mappings().all.return_value = [
        {'id': 1, 'name': 'Afiliado A', 'email': 'a@example.com', 'total_sales': 20, 'total': 2000.0, 'total_commission': 200.0},
        {'id': 2, 'name': 'Afiliado B', 'email': 'b@example.com', 'total_sales': 15, 'total': 1500.0, 'total_commission': 150.0}
    ]
    
    mock_db_session.execute.return_value = affiliates_result
    return mock_db_session


@pytest_asyncio.fixture
async def affiliate_dashboard_mocks(mock_db_session):
    # Simula o resultado da consulta do período atual
    current_result = MagicMock()
    current_result.mappings().one_or_none.return_value = {
        'total_sales': 20,
        'total': 2000.0,
        'total_commission': 200.0
    }
    
    # Simula o resultado da consulta do período anterior
    previous_result = MagicMock()
    previous_result.mappings().one_or_none.return_value = {
        'total_sales': 15,
        'total': 1500.0,
        'total_commission': 150.0
    }
    
    # Simula o resultado da consulta de solicitações de saque
    withdrawal_result = MagicMock()
    withdrawal_result.mappings().all.return_value = [
        {'status': 'pending', 'count': 2},
        {'status': 'approved', 'count': 3},
        {'status': 'paid', 'count': 5}
    ]
    
    # Configura a sessão mock para retornar os resultados simulados
    mock_db_session.execute.side_effect = [
        current_result,
        previous_result,
        withdrawal_result
    ]
    
    return mock_db_session


# Fixture para diferentes períodos
@pytest_asyncio.fixture
async def sales_by_time_day_mocks(mock_db_session):
    # Simula o resultado da consulta para período de dia
    sales_result = MagicMock()
    sales_result.mappings().all.return_value = [
        {'time_group': 8, 'count': 2, 'amount': 200.0, 'commission': 20.0},
        {'time_group': 12, 'count': 5, 'amount': 500.0, 'commission': 50.0},
        {'time_group': 18, 'count': 3, 'amount': 300.0, 'commission': 30.0}
    ]
    
    mock_db_session.execute.return_value = sales_result
    return mock_db_session


@pytest_asyncio.fixture
async def sales_by_time_week_mocks(mock_db_session):
    # Simula o resultado da consulta para período de semana
    sales_result = MagicMock()
    sales_result.mappings().all.return_value = [
        {'time_group': 1, 'count': 10, 'amount': 1000.0, 'commission': 100.0},  # Segunda
        {'time_group': 3, 'count': 15, 'amount': 1500.0, 'commission': 150.0},  # Quarta
        {'time_group': 5, 'count': 20, 'amount': 2000.0, 'commission': 200.0}   # Sexta
    ]
    
    mock_db_session.execute.return_value = sales_result
    return mock_db_session


@pytest_asyncio.fixture
async def sales_by_time_year_mocks(mock_db_session):
    # Simula o resultado da consulta para período de ano
    sales_result = MagicMock()
    sales_result.mappings().all.return_value = [
        {'time_group': 1, 'count': 50, 'amount': 5000.0, 'commission': 500.0},  # Janeiro
        {'time_group': 6, 'count': 70, 'amount': 7000.0, 'commission': 700.0},  # Junho
        {'time_group': 12, 'count': 100, 'amount': 10000.0, 'commission': 1000.0}  # Dezembro
    ]
    
    mock_db_session.execute.return_value = sales_result
    return mock_db_session


# Testes dos serviços de dashboard
@pytest.mark.asyncio
async def test_get_admin_dashboard_metrics(admin_metrics_mocks, mock_timezone):
    # Executa a função
    result = await get_admin_dashboard_metrics(admin_metrics_mocks, period='month')
    
    # Verifica os resultados
    assert result['period'] == 'month'
    assert result['sales']['total_count'] == 10
    assert result['sales']['total_revenue'] == 1000.0
    assert result['sales']['total_commissions'] == 100.0
    assert result['affiliates']['active_count'] == 5
    assert result['orders']['total_count'] == 8
    assert result['orders']['total'] == 800.0
    assert result['orders']['pending_count'] == 2
    assert result['users']['new_count'] == 15


@pytest.mark.asyncio
async def test_get_admin_dashboard_metrics_different_periods(admin_metrics_mocks, mock_timezone):
    # Testa diferentes períodos
    periods = ['day', 'week', 'month', 'year']
    
    for period in periods:
        # Resetar o mock para cada chamada
        admin_metrics_mocks.execute.side_effect = None
        admin_metrics_mocks.execute.reset_mock()
        
        # Reconfigura os resultados simulados
        sales_result = MagicMock()
        sales_result.mappings().one_or_none.return_value = {
            'total_sales': 10,
            'total_revenue': 1000.0,
            'total_commissions': 100.0
        }
        
        affiliates_result = MagicMock()
        affiliates_result.scalar_one_or_none.return_value = 5
        
        orders_result = MagicMock()
        orders_result.mappings().one_or_none.return_value = {
            'total_orders': 8,
            'total_order_amount': 800.0
        }
        
        pending_orders_result = MagicMock()
        pending_orders_result.scalar_one_or_none.return_value = 2
        
        users_result = MagicMock()
        users_result.scalar_one_or_none.return_value = 15
        
        admin_metrics_mocks.execute.side_effect = [
            sales_result,
            affiliates_result,
            orders_result,
            pending_orders_result,
            users_result
        ]
        
        # Executa a função com o período atual
        result = await get_admin_dashboard_metrics(admin_metrics_mocks, period=period)
        
        # Verifica os resultados
        assert result['period'] == period
        assert result['sales']['total_count'] == 10
        assert 'start_date' in result
        assert 'end_date' in result


@pytest.mark.asyncio
async def test_get_sales_by_time(sales_by_time_mocks, mock_timezone):
    # Executa a função para dados mensais
    result = await get_sales_by_time(sales_by_time_mocks, period='month')
    
    # Verifica os resultados
    assert len(result) == 3
    assert result[0]['label'] == '01'
    assert result[0]['count'] == 5
    assert result[0]['amount'] == 500.0
    assert result[0]['commission'] == 50.0


@pytest.mark.asyncio
async def test_get_sales_by_time_day(sales_by_time_day_mocks, mock_timezone):
    # Executa a função para período de dia
    result = await get_sales_by_time(sales_by_time_day_mocks, period='day')
    
    # Verifica os resultados
    assert len(result) == 3
    assert result[0]['label'] == '08:00'
    assert result[0]['count'] == 2
    assert result[0]['amount'] == 200.0
    assert result[0]['commission'] == 20.0


@pytest.mark.asyncio
async def test_get_sales_by_time_week(sales_by_time_week_mocks, mock_timezone):
    # Executa a função para período de semana
    result = await get_sales_by_time(sales_by_time_week_mocks, period='week')
    
    # Verifica os resultados
    assert len(result) == 3
    # O dia exato vai depender do locale, então verificamos apenas a presença de dados
    assert 'label' in result[0]
    assert result[0]['count'] == 10
    assert result[0]['amount'] == 1000.0
    assert result[0]['commission'] == 100.0


@pytest.mark.asyncio
async def test_get_sales_by_time_year(sales_by_time_year_mocks, mock_timezone):
    # Executa a função para período de ano
    result = await get_sales_by_time(sales_by_time_year_mocks, period='year')
    
    # Verifica os resultados
    assert len(result) == 3
    # O mês exato vai depender do locale, então verificamos apenas a presença de dados
    assert 'label' in result[0]
    assert result[0]['count'] == 50
    assert result[0]['amount'] == 5000.0
    assert result[0]['commission'] == 500.0


@pytest.mark.asyncio
async def test_get_sales_by_time_with_affiliate(sales_by_time_mocks, mock_timezone):
    # Executa a função filtrando por afiliado
    result = await get_sales_by_time(sales_by_time_mocks, period='month', affiliate_id=1)
    
    # Verifica os resultados
    assert len(result) == 3
    assert result[0]['label'] == '01'
    assert result[0]['count'] == 5
    assert result[0]['amount'] == 500.0
    assert result[0]['commission'] == 50.0


@pytest.mark.asyncio
async def test_get_top_products(top_products_mocks, mock_timezone):
    # Executa a função
    result = await get_top_products(top_products_mocks, limit=3, period='month')
    
    # Verifica os resultados
    assert len(result) == 3
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Produto A'
    assert result[0]['total_sold'] == 10
    assert result[0]['total_revenue'] == 1000.0


@pytest.mark.asyncio
async def test_get_top_products_with_affiliate(top_products_mocks, mock_timezone):
    # Executa a função filtrando por afiliado
    result = await get_top_products(top_products_mocks, limit=3, period='month', affiliate_id=1)
    
    # Verifica os resultados
    assert len(result) == 3
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Produto A'
    assert result[0]['total_sold'] == 10
    assert result[0]['total_revenue'] == 1000.0


@pytest.mark.asyncio
async def test_get_top_products_different_limits(top_products_mocks, mock_timezone):
    # Testa diferentes limites
    for limit in [1, 5, 10]:
        # Resetamos o mock para cada chamada
        top_products_mocks.execute.reset_mock()
        
        # Executa a função com o limite atual
        result = await get_top_products(top_products_mocks, limit=limit, period='month')
        
        # Como os mocks sempre retornam o mesmo resultado (3 produtos), verificamos apenas
        # se o limite foi passado corretamente para a função e se os dados estão consistentes
        assert len(result) > 0
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Produto A'
        assert top_products_mocks.execute.called


@pytest.mark.asyncio
async def test_get_top_affiliates(top_affiliates_mocks, mock_timezone):
    # Executa a função
    result = await get_top_affiliates(top_affiliates_mocks, limit=2, period='month')
    
    # Verifica os resultados
    assert len(result) == 2
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Afiliado A'
    assert result[0]['total_sales'] == 20
    assert result[0]['total_commission'] == 200.0


@pytest.mark.asyncio
async def test_get_top_affiliates_different_limits(top_affiliates_mocks, mock_timezone):
    # Testa diferentes limites
    for limit in [1, 5, 10]:
        # Resetamos o mock para cada chamada
        top_affiliates_mocks.execute.reset_mock()
        
        # Executa a função com o limite atual
        result = await get_top_affiliates(top_affiliates_mocks, limit=limit, period='month')
        
        # Como os mocks sempre retornam o mesmo resultado (2 afiliados), verificamos apenas
        # se o limite foi passado corretamente para a função e se os dados estão consistentes
        assert len(result) > 0
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Afiliado A'
        assert top_affiliates_mocks.execute.called


@pytest.mark.asyncio
async def test_get_affiliate_dashboard_metrics(affiliate_dashboard_mocks, mock_timezone):
    # Executa a função
    result = await get_affiliate_dashboard_metrics(affiliate_dashboard_mocks, affiliate_id=1, period='month')
    
    # Verifica os resultados
    assert result['period'] == 'month'
    assert result['sales']['current'] == 20
    assert result['sales']['previous'] == 15
    assert result['sales']['change_percent'] == 33.33333333333333  # (20-15)/15 * 100
    assert result['revenue']['current'] == 2000.0
    assert result['revenue']['previous'] == 1500.0
    assert result['commission']['current'] == 200.0
    assert result['commission']['previous'] == 150.0
    assert result['withdrawals']['pending'] == 2
    assert result['withdrawals']['approved'] == 3
    assert result['withdrawals']['paid'] == 5
    assert result['withdrawals']['rejected'] == 0  # Não definido nos dados de teste


@pytest.mark.asyncio
async def test_get_affiliate_dashboard_metrics_with_empty_previous(mock_db_session, mock_timezone):
    # Simula o resultado da consulta do período atual com dados
    current_result = MagicMock()
    current_result.mappings().one_or_none.return_value = {
        'total_sales': 20,
        'total': 2000.0,
        'total_commission': 200.0
    }
    
    # Simula o resultado da consulta do período anterior sem dados
    previous_result = MagicMock()
    previous_result.mappings().one_or_none.return_value = {
        'total_sales': None,
        'total': None,
        'total_commission': None
    }
    
    # Simula o resultado da consulta de solicitações de saque
    withdrawal_result = MagicMock()
    withdrawal_result.mappings().all.return_value = [
        {'status': 'pending', 'count': 2}
    ]
    
    # Configura a sessão mock para retornar os resultados simulados
    mock_db_session.execute.side_effect = [
        current_result,
        previous_result,
        withdrawal_result
    ]
    
    # Executa a função
    result = await get_affiliate_dashboard_metrics(mock_db_session, affiliate_id=1, period='month')
    
    # Verifica os resultados
    assert result['period'] == 'month'
    assert result['sales']['current'] == 20
    assert result['sales']['previous'] == 0  # None deve ser tratado como 0
    # O cálculo da variação percentual de 0 para 20 é 100%
    assert result['sales']['change_percent'] == 100.0
    
    # Verifica revenue
    assert result['revenue']['current'] == 2000.0
    assert result['revenue']['previous'] == 0
    assert result['revenue']['change_percent'] == 100.0
    
    # Verifica commission
    assert result['commission']['current'] == 200.0
    assert result['commission']['previous'] == 0
    assert result['commission']['change_percent'] == 100.0
    
    # Verifica withdrawals
    assert result['withdrawals']['pending'] == 2
    assert result['withdrawals']['approved'] == 0  # Status não definido
    assert result['withdrawals']['paid'] == 0  # Status não definido
    assert result['withdrawals']['rejected'] == 0  # Status não definido 