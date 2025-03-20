# D:\3xDigital\app\views\dashboard_views.py
"""
dashboard_views.py

Módulo responsável pelos endpoints relacionados aos dashboards e relatórios
do sistema 3xDigital, incluindo métricas gerais, dados para gráficos e
funcionalidades de exportação.

Endpoints:
    - GET /dashboard/admin/metrics: Métricas gerais para o dashboard administrativo
    - GET /dashboard/admin/sales-chart: Dados para gráfico de vendas
    - GET /dashboard/admin/top-products: Produtos mais vendidos
    - GET /dashboard/admin/top-affiliates: Afiliados com melhor desempenho
    - GET /dashboard/affiliate/metrics: Métricas específicas para o dashboard de afiliado
    - GET /dashboard/affiliate/sales-chart: Dados para gráfico de vendas do afiliado
    - GET /dashboard/affiliate/top-products: Produtos mais vendidos pelo afiliado
    - GET /dashboard/export: Exportação de relatórios em diferentes formatos

Regras de Negócio:
    - Afiliados só podem visualizar seus próprios dados
    - Administradores podem visualizar dados de todos os afiliados
    - Dados podem ser filtrados por período (dia, semana, mês, ano)
    - Relatórios podem ser exportados em CSV ou Excel

Dependências:
    - aiohttp para rotas
    - app.services.dashboard_service para lógica de dashboards
    - app.middleware.authorization_middleware para autenticação
"""

import io
import json
import csv
import datetime
from zipfile import ZipFile
from aiohttp import web
from sqlalchemy import select

from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.models.database import Affiliate
from app.services.dashboard_service import (
    get_admin_dashboard_metrics,
    get_sales_by_time,
    get_top_products,
    get_top_affiliates,
    get_affiliate_dashboard_metrics
)

# Definição das rotas
routes = web.RouteTableDef()


@routes.get('/dashboard/admin/metrics')
@require_role(['admin'])
async def get_admin_metrics(request: web.Request) -> web.Response:
    """
    Retorna métricas gerais para o dashboard administrativo.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        
    Returns:
        web.Response: JSON com métricas do dashboard
    """
    period = request.query.get('period', 'month')
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Obtém as métricas
    db = request.app[DB_SESSION_KEY]
    metrics = await get_admin_dashboard_metrics(db, period)
    
    return web.json_response(metrics, status=200)


@routes.get('/dashboard/admin/sales-chart')
@require_role(['admin'])
async def get_admin_sales_chart(request: web.Request) -> web.Response:
    """
    Retorna dados para o gráfico de vendas no dashboard administrativo.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        
    Returns:
        web.Response: JSON com dados para o gráfico
    """
    period = request.query.get('period', 'month')
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Obtém os dados para o gráfico
    db = request.app[DB_SESSION_KEY]
    chart_data = await get_sales_by_time(db, period)
    
    return web.json_response(chart_data, status=200)


@routes.get('/dashboard/admin/top-products')
@require_role(['admin'])
async def get_admin_top_products(request: web.Request) -> web.Response:
    """
    Retorna os produtos mais vendidos para o dashboard administrativo.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        limit (int, opcional): Limite de produtos a retornar (padrão: 5)
        
    Returns:
        web.Response: JSON com lista dos produtos mais vendidos
    """
    period = request.query.get('period', 'month')
    limit = int(request.query.get('limit', 5))
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Obtém os produtos mais vendidos
    db = request.app[DB_SESSION_KEY]
    top_products = await get_top_products(db, limit, period)
    
    return web.json_response(top_products, status=200)


@routes.get('/dashboard/admin/top-affiliates')
@require_role(['admin'])
async def get_admin_top_affiliates(request: web.Request) -> web.Response:
    """
    Retorna os afiliados com melhor desempenho para o dashboard administrativo.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        limit (int, opcional): Limite de afiliados a retornar (padrão: 5)
        
    Returns:
        web.Response: JSON com lista dos afiliados com melhor desempenho
    """
    period = request.query.get('period', 'month')
    limit = int(request.query.get('limit', 5))
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Obtém os afiliados com melhor desempenho
    db = request.app[DB_SESSION_KEY]
    top_affiliates = await get_top_affiliates(db, limit, period)
    
    return web.json_response(top_affiliates, status=200)


@routes.get('/dashboard/affiliate/metrics')
@require_role(['affiliate', 'admin'])
async def get_affiliate_metrics(request: web.Request) -> web.Response:
    """
    Retorna métricas para o dashboard de um afiliado.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        
    Returns:
        web.Response: JSON com métricas do dashboard do afiliado
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    period = request.query.get('period', 'month')
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém as métricas
    db = request.app[DB_SESSION_KEY]
    metrics = await get_affiliate_dashboard_metrics(db, affiliate_id, period)
    
    return web.json_response(metrics, status=200)


@routes.get('/dashboard/affiliate/sales-chart')
@require_role(['affiliate', 'admin'])
async def get_affiliate_sales_chart(request: web.Request) -> web.Response:
    """
    Retorna dados para o gráfico de vendas no dashboard do afiliado.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        
    Returns:
        web.Response: JSON com dados para o gráfico
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    period = request.query.get('period', 'month')
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém os dados para o gráfico
    db = request.app[DB_SESSION_KEY]
    chart_data = await get_sales_by_time(db, period, affiliate_id)
    
    return web.json_response(chart_data, status=200)


@routes.get('/dashboard/affiliate/top-products')
@require_role(['affiliate', 'admin'])
async def get_affiliate_top_products(request: web.Request) -> web.Response:
    """
    Retorna os produtos mais vendidos pelo afiliado.
    
    Query params:
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        limit (int, opcional): Limite de produtos a retornar (padrão: 5)
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        
    Returns:
        web.Response: JSON com lista dos produtos mais vendidos pelo afiliado
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    period = request.query.get('period', 'month')
    limit = int(request.query.get('limit', 5))
    
    # Valida o período
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém os produtos mais vendidos
    db = request.app[DB_SESSION_KEY]
    top_products = await get_top_products(db, limit, period, affiliate_id)
    
    return web.json_response(top_products, status=200)


@routes.get('/dashboard/export')
@require_role(['admin', 'affiliate'])
async def export_data(request: web.Request) -> web.Response:
    """
    Exporta dados em diferentes formatos (CSV, Excel).
    
    Query params:
        type (str): Tipo de dados a exportar ('sales', 'commissions', 'products', 'affiliates')
        format (str): Formato de exportação ('csv')
        period (str, opcional): Período para filtrar dados ('day', 'week', 'month', 'year')
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        
    Returns:
        web.Response: Arquivo para download
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    
    # Parâmetros da query
    export_type = request.query.get('type')
    export_format = request.query.get('format', 'csv')
    period = request.query.get('period', 'month')
    
    # Validações
    if not export_type or export_type not in ['sales', 'commissions', 'products', 'affiliates']:
        return web.json_response(
            {"error": "Tipo de exportação inválido. Use 'sales', 'commissions', 'products' ou 'affiliates'"},
            status=400
        )
    
    if export_format != 'csv':
        return web.json_response(
            {"error": "Formato de exportação inválido. Use 'csv'"},
            status=400
        )
    
    if period not in ['day', 'week', 'month', 'year']:
        return web.json_response(
            {"error": "Período inválido. Use 'day', 'week', 'month' ou 'year'"},
            status=400
        )
    
    # Determina o afiliado (se necessário)
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    elif user_role == 'affiliate':
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém os dados com base no tipo solicitado
    db = request.app[DB_SESSION_KEY]
    data = []
    filename = f"{export_type}_{period}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if export_type == 'sales':
        # Dados de vendas
        sales_data = await get_sales_by_time(db, period, affiliate_id)
        data = [
            {
                "Data": item["label"],
                "Vendas": item["count"],
                "Valor Total": f"R$ {item['amount']:.2f}",
                "Comissão": f"R$ {item['commission']:.2f}"
            }
            for item in sales_data
        ]
    elif export_type == 'products':
        # Dados de produtos
        products_data = await get_top_products(db, 100, period, affiliate_id)  # Aumenta o limite para exportação
        data = [
            {
                "ID": item["id"],
                "Nome": item["name"],
                "Preço": f"R$ {item['price']:.2f}",
                "Quantidade Vendida": item["total_sold"],
                "Receita Total": f"R$ {item['total_revenue']:.2f}"
            }
            for item in products_data
        ]
    elif export_type == 'affiliates' and user_role == 'admin':
        # Dados de afiliados (apenas para admin)
        affiliates_data = await get_top_affiliates(db, 100, period)  # Aumenta o limite para exportação
        data = [
            {
                "ID": item["id"],
                "Nome": item["name"],
                "Email": item["email"],
                "Vendas": item["total_sales"],
                "Valor Total": f"R$ {item['total']:.2f}",
                "Comissão Total": f"R$ {item['total_commission']:.2f}"
            }
            for item in affiliates_data
        ]
    elif export_type == 'commissions':
        # Dados específicos de comissões
        if affiliate_id:
            from app.services.finance_service import get_affiliate_transactions
            transactions, _ = await get_affiliate_transactions(
                db, affiliate_id, transaction_type='commission', page=1, page_size=1000
            )
            data = [
                {
                    "ID": t.id,
                    "Valor": f"R$ {t.amount:.2f}",
                    "Descrição": t.description,
                    "Referência": t.reference_id,
                    "Data": t.transaction_date.strftime('%d/%m/%Y %H:%M') if t.transaction_date else ''
                }
                for t in transactions
            ]
    
    # Se não houver dados, retorna erro
    if not data:
        return web.json_response(
            {"error": "Nenhum dado encontrado para os parâmetros especificados"},
            status=404
        )
    
    # Gera o arquivo CSV
    output = io.StringIO()
    fieldnames = data[0].keys()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    
    # Prepara a resposta
    response = web.Response(
        body=output.getvalue().encode('utf-8'),
        content_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
    
    return response 