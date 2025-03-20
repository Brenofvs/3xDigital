"""
test_dashboard_views.py

Testes unitários para os endpoints relacionados aos dashboards.
Valida as diferentes rotas de visualização de dados e relatórios.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from aiohttp.test_utils import make_mocked_request
from types import SimpleNamespace
import warnings

from app.views.dashboard_views import (
    get_admin_metrics,
    get_admin_sales_chart,
    get_admin_top_products,
    get_admin_top_affiliates,
    get_affiliate_metrics,
    get_affiliate_sales_chart,
    get_affiliate_top_products,
    export_data
)
from app.config.settings import DB_SESSION_KEY

# Função auxiliar para injetar temporariamente uma sessão de banco de dados
# com supressão de warnings de depreciação
def setup_db_session(app, mock_db):
    """Configura uma middleware para injetar a sessão de banco de dados."""
    
    @pytest.fixture
    async def db_middleware(request, handler):
        """Middleware que injeta a sessão de banco de dados no contexto da requisição."""
        request.app[DB_SESSION_KEY] = mock_db
        response = await handler(request)
        return response
    
    # Adiciona middleware à aplicação
    app.middlewares.append(db_middleware)
    return db_middleware

# Função auxiliar para criar um mock de DB session
def create_db_mock(query_results=None):
    """Cria um mock para a sessão de banco de dados."""
    mock_db = AsyncMock()
    
    if query_results is not None:  # Modificado para verificar None explicitamente
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = query_results
        mock_db.execute.return_value = query_result
        
    return mock_db

# Função para mockar o middleware de autenticação/autorização
def mock_auth_middleware(user=None):
    """Cria um mock para o middleware de autenticação."""
    async def middleware_mock(request, handler):
        request["user"] = user
        response = await handler(request)
        return response
    return middleware_mock

# Testes para endpoint de métricas administrativas
@pytest.mark.asyncio
async def test_get_admin_metrics(test_client_fixture, admin_user):
    """Testa o endpoint de métricas do dashboard administrativo."""
    
    # Mock para a função de serviço
    metrics_data = {
        "period": "month",
        "start_date": "2023-06-01T00:00:00+00:00",
        "end_date": "2023-06-15T10:30:00+00:00",
        "sales": {
            "total_count": 10,
            "total_revenue": 1000.0,
            "total_commissions": 100.0
        },
        "affiliates": {
            "active_count": 5,
        },
        "orders": {
            "total_count": 8,
            "total": 800.0,
            "pending_count": 2
        },
        "users": {
            "new_count": 15
        }
    }
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.views.dashboard_views.get_admin_dashboard_metrics', return_value=metrics_data), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/admin/metrics',
                                        headers=headers,
                                        params={'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 200
        data = await resp.json()
        assert data['period'] == 'month'
        assert data['sales']['total_count'] == 10
        assert data['sales']['total_revenue'] == 1000.0
        assert data['orders']['pending_count'] == 2


@pytest.mark.asyncio
async def test_get_admin_metrics_invalid_period(test_client_fixture, admin_user):
    """Testa o endpoint com um período inválido."""
    
    # Mock do middleware de autorização
    with patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user):
        
        # Executa a requisição com período inválido
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/admin/metrics',
                                    headers=headers,
                                    params={'period': 'invalid'})
        
        # Verifica o resultado
        assert resp.status == 400
        data = await resp.json()
        assert 'error' in data


# Testes para endpoint de gráficos de vendas
@pytest.mark.asyncio
async def test_get_admin_sales_chart(test_client_fixture, admin_user):
    """Testa o endpoint de gráfico de vendas do dashboard administrativo."""
    
    # Mock para a função de serviço
    chart_data = [
        {"label": "01", "count": 5, "amount": 500.0, "commission": 50.0},
        {"label": "02", "count": 10, "amount": 1000.0, "commission": 100.0},
        {"label": "03", "count": 7, "amount": 700.0, "commission": 70.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.views.dashboard_views.get_sales_by_time', return_value=chart_data), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/admin/sales-chart',
                                        headers=headers,
                                        params={'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 3
        assert data[0]['label'] == '01'
        assert data[0]['count'] == 5
        assert data[0]['amount'] == 500.0


# Testes para endpoint de produtos mais vendidos
@pytest.mark.asyncio
async def test_get_admin_top_products(test_client_fixture, admin_user):
    """Testa o endpoint de produtos mais vendidos do dashboard administrativo."""
    
    # Mock para a função de serviço
    products_data = [
        {"id": 1, "name": "Produto A", "price": 100.0, "total_sold": 10, "total_revenue": 1000.0},
        {"id": 2, "name": "Produto B", "price": 50.0, "total_sold": 8, "total_revenue": 400.0},
        {"id": 3, "name": "Produto C", "price": 150.0, "total_sold": 5, "total_revenue": 750.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.views.dashboard_views.get_top_products', return_value=products_data), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/admin/top-products',
                                        headers=headers,
                                        params={'period': 'month', 'limit': '3'})
        
        # Verifica o resultado
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 3
        assert data[0]['id'] == 1
        assert data[0]['name'] == 'Produto A'
        assert data[0]['total_sold'] == 10


# Testes para endpoint de afiliados com melhor desempenho
@pytest.mark.asyncio
async def test_get_admin_top_affiliates(test_client_fixture, admin_user):
    """Testa o endpoint de afiliados com melhor desempenho do dashboard administrativo."""
    
    # Mock para a função de serviço
    affiliates_data = [
        {"id": 1, "name": "Afiliado A", "email": "a@example.com", "total_sales": 20, "total": 2000.0, "total_commission": 200.0},
        {"id": 2, "name": "Afiliado B", "email": "b@example.com", "total_sales": 15, "total": 1500.0, "total_commission": 150.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.views.dashboard_views.get_top_affiliates', return_value=affiliates_data), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/admin/top-affiliates',
                                        headers=headers,
                                        params={'period': 'month', 'limit': '2'})
        
        # Verifica o resultado
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 2
        assert data[0]['id'] == 1
        assert data[0]['name'] == 'Afiliado A'
        assert data[0]['total_sales'] == 20


# Testes para endpoint de métricas do afiliado
@pytest.mark.asyncio
async def test_get_affiliate_metrics_as_affiliate(test_client_fixture, affiliate_user):
    """Testa o endpoint de métricas do dashboard do afiliado (como afiliado)."""
    
    # Mock para a consulta do afiliado
    affiliate_id = 1  # ID do afiliado
    
    # Mock para a função de serviço
    metrics_data = {
        "period": "month",
        "start_date": "2023-06-01T00:00:00+00:00",
        "end_date": "2023-06-15T10:30:00+00:00",
        "sales": {
            "current": 20,
            "previous": 15,
            "change_percent": 33.33
        },
        "revenue": {
            "current": 2000.0,
            "previous": 1500.0,
            "change_percent": 33.33
        },
        "commission": {
            "current": 200.0,
            "previous": 150.0,
            "change_percent": 33.33
        },
        "withdrawals": {
            "pending": 2,
            "approved": 3,
            "rejected": 0,
            "paid": 5
        }
    }
    
    # Mock para o banco de dados
    mock_db = create_db_mock(affiliate_id)
    
    # Mocking direto da obtenção de banco de dados com supressão de warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        test_client_fixture.app[DB_SESSION_KEY] = mock_db
        
        # Mock da função de serviço e middleware de autorização
        with patch('app.middleware.authorization_middleware.validate_token', return_value=affiliate_user), \
             patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
             patch('app.views.dashboard_views.get_affiliate_dashboard_metrics', return_value=metrics_data):
            
            # Executa a requisição
            headers = {'Authorization': 'Bearer valid_token'}
            resp = await test_client_fixture.get('/dashboard/affiliate/metrics',
                                            headers=headers,
                                            params={'period': 'month'})
            
            # Verifica o resultado
            assert resp.status == 200
            data = await resp.json()
            assert data['period'] == 'month'
            assert data['sales']['current'] == 20
            assert data['sales']['previous'] == 15
            assert data['withdrawals']['pending'] == 2


@pytest.mark.asyncio
async def test_get_affiliate_metrics_as_admin(test_client_fixture, admin_user):
    """Testa o endpoint de métricas do dashboard do afiliado (como admin)."""
    
    # Mock para a função de serviço
    metrics_data = {
        "period": "month",
        "start_date": "2023-06-01T00:00:00+00:00",
        "end_date": "2023-06-15T10:30:00+00:00",
        "sales": {
            "current": 20,
            "previous": 15,
            "change_percent": 33.33
        },
        "revenue": {
            "current": 2000.0,
            "previous": 1500.0,
            "change_percent": 33.33
        },
        "commission": {
            "current": 200.0,
            "previous": 150.0,
            "change_percent": 33.33
        },
        "withdrawals": {
            "pending": 2,
            "approved": 3,
            "rejected": 0,
            "paid": 5
        }
    }
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.views.dashboard_views.get_affiliate_dashboard_metrics', return_value=metrics_data):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/affiliate/metrics',
                                        headers=headers,
                                        params={'period': 'month', 'affiliate_id': '1'})
        
        # Verifica o resultado
        assert resp.status == 200
        data = await resp.json()
        assert data['period'] == 'month'
        assert data['sales']['current'] == 20
        assert data['sales']['previous'] == 15


# Testes para endpoint de gráfico de vendas do afiliado
@pytest.mark.asyncio
async def test_get_affiliate_sales_chart(test_client_fixture, affiliate_user):
    """Testa o endpoint de gráfico de vendas do dashboard do afiliado."""
    
    # Mock para a consulta do afiliado
    affiliate_id = 1  # ID do afiliado
    
    # Mock para a função de serviço
    chart_data = [
        {"label": "01", "count": 5, "amount": 500.0, "commission": 50.0},
        {"label": "02", "count": 10, "amount": 1000.0, "commission": 100.0},
        {"label": "03", "count": 7, "amount": 700.0, "commission": 70.0}
    ]
    
    # Mock para o banco de dados
    mock_db = create_db_mock(affiliate_id)
    
    # Mocking direto da obtenção de banco de dados com supressão de warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        test_client_fixture.app[DB_SESSION_KEY] = mock_db
        
        # Mock da função de serviço e middleware de autorização
        with patch('app.middleware.authorization_middleware.validate_token', return_value=affiliate_user), \
             patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
             patch('app.views.dashboard_views.get_sales_by_time', return_value=chart_data):
            
            # Executa a requisição
            headers = {'Authorization': 'Bearer valid_token'}
            resp = await test_client_fixture.get('/dashboard/affiliate/sales-chart',
                                            headers=headers,
                                            params={'period': 'month'})
            
            # Verifica o resultado
            assert resp.status == 200
            data = await resp.json()
            assert len(data) == 3
            assert data[0]['label'] == '01'
            assert data[0]['count'] == 5
            assert data[0]['amount'] == 500.0


# Testes para endpoint de produtos mais vendidos pelo afiliado
@pytest.mark.asyncio
async def test_get_affiliate_top_products(test_client_fixture, affiliate_user):
    """Testa o endpoint de produtos mais vendidos pelo afiliado."""
    
    # Mock para a consulta do afiliado
    affiliate_id = 1  # ID do afiliado
    
    # Mock para a função de serviço
    products_data = [
        {"id": 1, "name": "Produto A", "price": 100.0, "total_sold": 10, "total_revenue": 1000.0},
        {"id": 2, "name": "Produto B", "price": 50.0, "total_sold": 8, "total_revenue": 400.0}
    ]
    
    # Mock para o banco de dados
    mock_db = create_db_mock(affiliate_id)
    
    # Mocking direto da obtenção de banco de dados com supressão de warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        test_client_fixture.app[DB_SESSION_KEY] = mock_db
        
        # Mock da função de serviço e middleware de autorização
        with patch('app.middleware.authorization_middleware.validate_token', return_value=affiliate_user), \
             patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
             patch('app.views.dashboard_views.get_top_products', return_value=products_data):
            
            # Executa a requisição
            headers = {'Authorization': 'Bearer valid_token'}
            resp = await test_client_fixture.get('/dashboard/affiliate/top-products',
                                            headers=headers,
                                            params={'period': 'month', 'limit': '2'})
            
            # Verifica o resultado
            assert resp.status == 200
            data = await resp.json()
            assert len(data) == 2
            assert data[0]['id'] == 1
            assert data[0]['name'] == 'Produto A'
            assert data[0]['total_sold'] == 10


# Testes para endpoint de exportação de dados
@pytest.mark.asyncio
async def test_export_data_sales(test_client_fixture, admin_user):
    """Testa o endpoint de exportação de dados de vendas."""
    
    # Mock para a função de serviço
    sales_data = [
        {"label": "01", "count": 5, "amount": 500.0, "commission": 50.0},
        {"label": "02", "count": 10, "amount": 1000.0, "commission": 100.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.views.dashboard_views.get_sales_by_time', return_value=sales_data):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/export',
                                        headers=headers,
                                        params={'type': 'sales', 'format': 'csv', 'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 200
        assert resp.content_type == 'text/csv'
        # Verifica se o cabeçalho de download está presente
        assert 'attachment' in resp.headers['Content-Disposition']
        assert 'sales_month_' in resp.headers['Content-Disposition']


@pytest.mark.asyncio
async def test_export_data_products(test_client_fixture, admin_user):
    """Testa o endpoint de exportação de dados de produtos."""
    
    # Mock para a função de serviço
    products_data = [
        {"id": 1, "name": "Produto A", "price": 100.0, "total_sold": 10, "total_revenue": 1000.0},
        {"id": 2, "name": "Produto B", "price": 50.0, "total_sold": 8, "total_revenue": 400.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.views.dashboard_views.get_top_products', return_value=products_data):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/export',
                                        headers=headers,
                                        params={'type': 'products', 'format': 'csv', 'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 200
        assert resp.content_type == 'text/csv'
        # Verifica se o cabeçalho de download está presente
        assert 'attachment' in resp.headers['Content-Disposition']
        assert 'products_month_' in resp.headers['Content-Disposition']


@pytest.mark.asyncio
async def test_export_data_invalid_type(test_client_fixture, admin_user):
    """Testa o endpoint de exportação com tipo inválido."""
    
    # Mock da autenticação e autorização
    with patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler):
        
        # Executa a requisição com tipo inválido
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/export',
                                        headers=headers,
                                        params={'type': 'invalid', 'format': 'csv', 'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 400
        data = await resp.json()
        assert 'error' in data


@pytest.mark.asyncio
async def test_export_data_affiliates(test_client_fixture, admin_user):
    """Testa o endpoint de exportação de dados de afiliados."""
    
    # Mock para a função de serviço
    affiliates_data = [
        {"id": 1, "name": "Afiliado A", "email": "a@example.com", "total_sales": 20, "total": 2000.0, "total_commission": 200.0},
        {"id": 2, "name": "Afiliado B", "email": "b@example.com", "total_sales": 15, "total": 1500.0, "total_commission": 150.0}
    ]
    
    # Mock da função de serviço e do middleware de autorização
    with patch('app.middleware.authorization_middleware.validate_token', return_value=admin_user), \
         patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
         patch('app.views.dashboard_views.get_top_affiliates', return_value=affiliates_data):
        
        # Executa a requisição
        headers = {'Authorization': 'Bearer valid_token'}
        resp = await test_client_fixture.get('/dashboard/export',
                                        headers=headers,
                                        params={'type': 'affiliates', 'format': 'csv', 'period': 'month'})
        
        # Verifica o resultado
        assert resp.status == 200
        assert resp.content_type == 'text/csv'
        # Verifica se o cabeçalho de download está presente
        assert 'attachment' in resp.headers['Content-Disposition']
        assert 'affiliates_month_' in resp.headers['Content-Disposition']


@pytest.mark.asyncio
async def test_export_data_as_affiliate(test_client_fixture, affiliate_user):
    """Testa o endpoint de exportação de dados de vendas como afiliado."""
    
    # Mock para a consulta do afiliado
    affiliate_id = 1  # ID do afiliado
    
    # Mock para a função de serviço
    sales_data = [
        {"label": "01", "count": 5, "amount": 500.0, "commission": 50.0},
        {"label": "02", "count": 10, "amount": 1000.0, "commission": 100.0}
    ]
    
    # Mock para o banco de dados
    mock_db = create_db_mock(affiliate_id)
    
    # Mocking direto da obtenção de banco de dados com supressão de warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        test_client_fixture.app[DB_SESSION_KEY] = mock_db
        
        # Mock da função de serviço e middleware de autorização
        with patch('app.middleware.authorization_middleware.validate_token', return_value=affiliate_user), \
             patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler), \
             patch('app.views.dashboard_views.get_sales_by_time', return_value=sales_data):
            
            # Executa a requisição
            headers = {'Authorization': 'Bearer valid_token'}
            resp = await test_client_fixture.get('/dashboard/export',
                                            headers=headers,
                                            params={'type': 'sales', 'format': 'csv', 'period': 'month'})
            
            # Verifica o resultado
            assert resp.status == 200
            assert resp.content_type == 'text/csv'
            # Verifica se o cabeçalho de download está presente
            assert 'attachment' in resp.headers['Content-Disposition']
            assert 'sales_month_' in resp.headers['Content-Disposition']


@pytest.mark.asyncio
async def test_get_affiliate_metrics_user_not_affiliate(test_client_fixture, customer_user):
    """Testa o caso de um usuário não afiliado tentando acessar as métricas de afiliado."""
    
    # Mock para o banco de dados retornando None (indicando que não é afiliado)
    mock_db = create_db_mock(None)
    
    # Mocking direto da obtenção de banco de dados com supressão de warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        test_client_fixture.app[DB_SESSION_KEY] = mock_db
        
        # Mock da injeção do DB e autenticação/autorização
        with patch('app.middleware.authorization_middleware.validate_token', return_value=customer_user), \
             patch('app.middleware.authorization_middleware.require_role', lambda roles: lambda handler: handler):
            
            # Executa a requisição
            headers = {'Authorization': 'Bearer valid_token'}
            resp = await test_client_fixture.get('/dashboard/affiliate/metrics',
                                            headers=headers,
                                            params={'period': 'month'})
            
            # Verifica o resultado
            assert resp.status == 403
            data = await resp.json()
            assert 'error' in data
            # Corrigido para verificar a mensagem de erro real retornada pelo middleware de autorização
            assert 'Acesso negado: privilégio insuficiente.' in data['error'] 