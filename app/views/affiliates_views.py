# D:\3xDigital\app\views\affiliates_views.py

"""
affiliates_views.py

Este módulo define os endpoints para gerenciamento de afiliados e rastreamento de vendas.

Endpoints:
    - GET /affiliates/link: Retorna o link de afiliado único para o usuário logado.
    - GET /affiliates/sales: Lista as vendas atribuídas ao afiliado, com informações de comissão.
    - POST /affiliates/request: Permite que um usuário solicite a afiliação.
    - PUT /affiliates/{affiliate_id}: Permite que um administrador atualize os dados do afiliado.
    - GET /affiliates/requests: Lista as solicitações de afiliação pendentes, com paginação e dados completos do usuário.
    - GET /affiliates/list: Lista todos os afiliados aprovados, com paginação e dados completos do usuário.
    - GET /affiliates/status: Consulta o status da solicitação de afiliação do usuário autenticado.

Regras de Negócio:
    - Apenas usuários com papel 'affiliate' podem acessar os endpoints /affiliates/link e /affiliates/sales.
    - Usuários com papel 'user' podem solicitar afiliação através de /affiliates/request.
    - Qualquer usuário autenticado pode verificar o status da sua solicitação de afiliação via /affiliates/status.
    - O link de afiliado é construído a partir de um código de referência único.
    - As vendas atribuídas são obtidas a partir dos registros na tabela Sale.
    - Apenas administradores podem atualizar os dados do afiliado, listar as solicitações pendentes e listar todos os afiliados.

Dependências:
    - AIOHTTP para manipulação de requisições.
    - AffiliateService para lógica de negócios de afiliados.
    - Middleware de autenticação para proteção dos endpoints.
"""

from aiohttp import web
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role, require_auth
from app.services.affiliate_service import AffiliateService
import json
from datetime import datetime, timedelta

routes = web.RouteTableDef()

@routes.get("/affiliates/link")
@require_role(["affiliate"])
async def get_affiliate_link(request: web.Request) -> web.Response:
    """
    Retorna o link de afiliado para o usuário logado.

    O link é gerado utilizando o código de referência do afiliado. É necessário que:
    1. O usuário tenha o papel 'affiliate'
    2. O status da solicitação esteja como 'approved'

    Returns:
        web.Response: JSON contendo o link de afiliado ou mensagem de erro.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    
    # Verificar se o usuário pode gerar links de afiliado
    check_result = await affiliate_service.can_generate_affiliate_link(user["id"])
    if not check_result["can_generate"]:
        return web.json_response(
            {"error": check_result["reason"]}, 
            status=403
        )
    
    # Se pode gerar, obter o link
    base_url = str(request.url.with_path("").with_query({}))
    result = await affiliate_service.get_affiliate_link(user["id"], base_url)
    
    if not result["success"]:
        return web.json_response(
            {"error": result["error"]}, 
            status=404 if "não encontrado" in result["error"] else 403
        )
    
    # Formato padronizado da resposta
    return web.json_response({"data": {"affiliate_link": result["data"]}}, status=200)

@routes.get("/affiliates/sales")
@require_role(["affiliate"])
async def get_affiliate_sales(request: web.Request) -> web.Response:
    """
    Retorna a lista de vendas e comissões atribuídas ao afiliado logado.

    É necessário que:
    1. O usuário tenha o papel 'affiliate'
    2. O status da solicitação esteja como 'approved'

    Query params:
        page (int, opcional): Número da página atual. Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de vendas do afiliado, cada uma com detalhes
                     do produto, pedido e comissão.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    # Obter parâmetros de paginação
    try:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "10"))
        
        # Validação básica
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        page = 1
        per_page = 10
    
    affiliate_service = AffiliateService(db)
    
    # Verificar se o usuário pode gerar links de afiliado (mesmas regras para acessar vendas)
    check_result = await affiliate_service.can_generate_affiliate_link(user["id"])
    if not check_result["can_generate"]:
        return web.json_response(
            {"error": check_result["reason"]}, 
            status=403
        )
    
    # Se pode gerar links, também pode ver suas vendas
    result = await affiliate_service.get_affiliate_sales(user["id"])
    
    if not result["success"]:
        return web.json_response(
            {"error": result["error"]}, 
            status=404 if "não encontrado" in result["error"] else 403
        )
    
    # Obter todas as vendas
    sales = result["data"]
    
    # Implementar paginação manual
    total_sales = len(sales)
    total_pages = (total_sales + per_page - 1) // per_page if total_sales > 0 else 1
    
    # Calcular índices de início e fim para a página atual
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_sales)
    
    # Obter apenas os itens da página atual
    page_sales = sales[start_idx:end_idx] if start_idx < total_sales else []
    
    # Formato padronizado da resposta
    response_data = {
        "data": page_sales,
        "meta": {
            "page": page,
            "page_size": per_page,
            "total_count": total_sales,
            "total_pages": total_pages
        }
    }
    
    return web.json_response(response_data, status=200)

@routes.post("/affiliates/request")
@require_role(["user"])
async def request_affiliation(request: web.Request) -> web.Response:
    """
    Permite que um usuário com papel 'user' solicite a afiliação.

    JSON de entrada (opcional):
        {
            "commission_rate": 0.05  # Valor sugerido; padrão é 0.05 se não informado.
        }

    Returns:
        web.Response: JSON informando que a solicitação de afiliação foi registrada, juntamente
                      com o código de referência gerado.

    Regras:
        - Se o usuário já tiver uma solicitação de afiliação (registro na tabela Affiliate), retorna erro.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    # Tentar obter dados JSON, se falhar, usar valores padrão
    try:
        data = await request.json()
        commission_rate = data.get("commission_rate", 0.05)
    except json.JSONDecodeError:
        # Se o corpo não for um JSON válido, use o valor padrão
        commission_rate = 0.05
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.request_affiliation(user["id"], commission_rate)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(
        {
            "message": "Solicitação de afiliação registrada com sucesso.",
            "referral_code": result["data"]["referral_code"]
        },
        status=201
    )

@routes.post("/affiliates/products/{product_id}/request")
@require_role(["user"])
async def request_product_affiliation(request: web.Request) -> web.Response:
    """
    Permite que um usuário solicite a afiliação a um produto específico.

    URL params:
        product_id (int): ID do produto para afiliação.

    JSON de entrada (opcional):
        {
            "commission_type": "percentage",  # Tipo de comissão ('percentage' ou 'fixed')
            "commission_value": 0.05  # Valor da comissão (porcentagem ou valor fixo)
        }

    Returns:
        web.Response: JSON informando que a solicitação de afiliação foi registrada.
    """
    user = request["user"]
    product_id = int(request.match_info.get("product_id"))
    db = request.app[DB_SESSION_KEY]
    
    # Tentar obter dados JSON, se falhar, usar valores padrão
    try:
        data = await request.json()
        commission_type = data.get("commission_type", "percentage")
        commission_value = data.get("commission_value", 0.05)
    except json.JSONDecodeError:
        # Se o corpo não for um JSON válido, use valores padrão
        commission_type = "percentage"
        commission_value = 0.05
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.request_product_affiliation(
        user["id"], 
        product_id, 
        commission_type, 
        commission_value
    )
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(
        {
            "message": "Solicitação de afiliação ao produto registrada com sucesso.",
            "data": result["data"]
        },
        status=201
    )

@routes.put("/affiliates/{affiliate_id}")
@require_role(["admin"])
async def update_affiliate(request: web.Request) -> web.Response:
    """
    Permite que um administrador atualize os dados de um afiliado, incluindo a taxa de comissão
    e o status da solicitação de afiliação.

    JSON de entrada:
        {
            "commission_rate": 0.07,
            "request_status": "approved",  # ou "blocked"
            "reason": "Motivo da recusa" # opcional, apenas quando request_status="blocked"
        }

    Returns:
        web.Response: JSON informando o sucesso da atualização.
    """
    affiliate_id = request.match_info.get("affiliate_id")
    data = await request.json()
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.update_affiliate(affiliate_id, **data)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    # Mensagem específica para cada status
    if "request_status" in data:
        if data["request_status"] == "approved":
            message = "Solicitação de afiliação aprovada com sucesso."
        elif data["request_status"] == "blocked":
            message = "Solicitação de afiliação rejeitada com sucesso."
        else:
            message = "Dados do afiliado atualizados com sucesso."
    else:
        message = "Dados do afiliado atualizados com sucesso."
    
    return web.json_response({"message": message, "data": result["data"]}, status=200)

@routes.put("/affiliates/{affiliate_id}/global")
@require_role(["admin"])
async def set_global_affiliation(request: web.Request) -> web.Response:
    """
    Permite que um administrador defina um afiliado como global.

    URL params:
        affiliate_id (int): ID do afiliado.

    JSON de entrada:
        {
            "is_global": true,  # Se o afiliado deve ser global
            "commission_rate": 0.05  # Taxa de comissão global do afiliado
        }

    Returns:
        web.Response: JSON informando o sucesso da operação.
    """
    affiliate_id = int(request.match_info.get("affiliate_id"))
    data = await request.json()
    is_global = data.get("is_global", True)
    commission_rate = data.get("commission_rate")
    
    db = request.app[DB_SESSION_KEY]
    affiliate_service = AffiliateService(db)
    
    result = await affiliate_service.set_global_affiliation(
        affiliate_id, 
        is_global, 
        commission_rate
    )
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    message = "Afiliação global configurada com sucesso." if is_global else "Afiliação global removida com sucesso."
    
    return web.json_response({
        "message": message,
        "data": result["data"]
    }, status=200)

@routes.put("/affiliates/products/{product_affiliation_id}")
@require_role(["admin"])
async def update_product_affiliation(request: web.Request) -> web.Response:
    """
    Permite que um administrador atualize o status de uma afiliação de produto.

    URL params:
        product_affiliation_id (int): ID da relação entre afiliado e produto.

    JSON de entrada:
        {
            "status": "approved",  # Status da afiliação ('pending', 'approved', 'blocked')
            "commission_type": "percentage",  # Tipo de comissão (opcional)
            "commission_value": 0.05,  # Valor da comissão (opcional)
            "reason": "Motivo da recusa" # Motivo da recusa quando status='blocked' (opcional)
        }

    Returns:
        web.Response: JSON informando o sucesso da operação.
    """
    product_affiliation_id = int(request.match_info.get("product_affiliation_id"))
    data = await request.json()
    
    db = request.app[DB_SESSION_KEY]
    affiliate_service = AffiliateService(db)
    
    result = await affiliate_service.update_product_affiliation(
        product_affiliation_id, 
        data.get("status"),
        data.get("commission_type"),
        data.get("commission_value"),
        data.get("reason")
    )
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    # Mensagem específica para cada status
    if "status" in data:
        if data["status"] == "approved":
            message = "Afiliação ao produto aprovada com sucesso."
        elif data["status"] == "blocked":
            message = "Afiliação ao produto rejeitada com sucesso."
        else:
            message = "Dados da afiliação ao produto atualizados com sucesso."
    else:
        message = "Dados da afiliação ao produto atualizados com sucesso."
    
    return web.json_response({"message": message, "data": result["data"]}, status=200)

@routes.get("/products/{product_id}/affiliates")
@require_role(["admin"])
async def list_product_affiliates(request: web.Request) -> web.Response:
    """
    Lista todos os afiliados de um produto específico.

    URL params:
        product_id (int): ID do produto.

    Query params:
        status (str, optional): Filtrar por status ('pending', 'approved', 'blocked').
        page (int, opcional): Número da página atual. Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de afiliados do produto.
    """
    product_id = int(request.match_info.get("product_id"))
    status = request.query.get("status")
    
    # Obtenção dos parâmetros de paginação
    try:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "10"))
        
        # Validação básica
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        page = 1
        per_page = 10
    
    db = request.app[DB_SESSION_KEY]
    affiliate_service = AffiliateService(db)
    
    # Implementar este método no serviço
    result = await affiliate_service.list_product_affiliates(
        product_id, 
        status=status,
        page=page, 
        per_page=per_page
    )
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    # Obter os dados e total
    affiliates = result["data"].get("affiliates", result["data"])
    total = result["data"].get("total", len(affiliates))
    
    # Padronização conforme o padrão da API (users_views.py)
    response_data = {
        "affiliates": affiliates,
        "meta": {
            "page": page,
            "page_size": per_page,
            "total_count": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }
    
    return web.json_response(response_data, status=200)

@routes.get("/r/{referral_code}")
async def redirect_with_referral(request: web.Request) -> web.Response:
    """
    Redireciona o usuário para a página principal, configurando um cookie com o código de referência.

    URL params:
        referral_code (str): Código de referência do afiliado.

    Returns:
        web.Response: Redirecionamento para a página principal.
    """
    referral_code = request.match_info.get("referral_code")
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    affiliate = await affiliate_service.get_affiliate_by_referral_code(referral_code)
    
    if not affiliate or affiliate.request_status != 'approved':
        # Redireciona para a página principal sem configurar cookie
        return web.HTTPFound('/')
    
    # Configuração da resposta com cookie
    response = web.HTTPFound('/')
    
    # Configurar cookie de 30 dias para o código de referência
    max_age = 60 * 60 * 24 * 30  # 30 dias em segundos
    expires = (datetime.now() + timedelta(days=30)).strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )
    
    response.set_cookie(
        name='referral_code',
        value=referral_code,
        max_age=max_age,
        expires=expires,
        domain=None,  # Domínio atual
        path='/',
        secure=request.url.scheme == 'https',
        httponly=True,
        samesite='Lax'
    )
    
    return response

@routes.get("/products/{product_id}/referral/{referral_code}")
async def redirect_with_product_referral(request: web.Request) -> web.Response:
    """
    Redireciona o usuário para a página do produto, configurando cookies de rastreamento.

    URL params:
        product_id (int): ID do produto.
        referral_code (str): Código de referência do afiliado.

    Returns:
        web.Response: Redirecionamento para a página do produto.
    """
    product_id = request.match_info.get("product_id")
    referral_code = request.match_info.get("referral_code")
    db = request.app[DB_SESSION_KEY]
    
    # Verificar se o produto existe
    from sqlalchemy import select
    from app.models.database import Product
    
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        # Produto não encontrado, redireciona para a página principal
        return web.HTTPFound('/')
    
    # Verificar se o afiliado existe e está aprovado
    affiliate_service = AffiliateService(db)
    affiliate = await affiliate_service.get_affiliate_by_referral_code(referral_code)
    
    if not affiliate or affiliate.request_status != 'approved':
        # Afiliado inválido, redireciona para a página do produto sem configurar cookie
        return web.HTTPFound(f'/products/{product_id}')
    
    # Verificar se o afiliado pode promover este produto específico
    can_promote = await affiliate_service.can_promote_product(affiliate.id, product_id)
    
    if not can_promote:
        # Afiliado não tem permissão para este produto
        return web.HTTPFound(f'/products/{product_id}')
    
    # Configuração da resposta com cookies
    response = web.HTTPFound(f'/products/{product_id}')
    
    # Configurar cookies de 30 dias
    max_age = 60 * 60 * 24 * 30  # 30 dias em segundos
    expires = (datetime.now() + timedelta(days=30)).strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )
    
    # Cookie para o código de referência geral
    response.set_cookie(
        name='referral_code',
        value=referral_code,
        max_age=max_age,
        expires=expires,
        domain=None,
        path='/',
        secure=request.url.scheme == 'https',
        httponly=True,
        samesite='Lax'
    )
    
    # Cookie específico para este produto
    response.set_cookie(
        name=f'product_{product_id}_referral',
        value=referral_code,
        max_age=max_age,
        expires=expires,
        domain=None,
        path='/',
        secure=request.url.scheme == 'https',
        httponly=True,
        samesite='Lax'
    )
    
    return response

@routes.get("/affiliates")
@require_role(["admin"])
async def list_affiliates(request: web.Request) -> web.Response:
    """
    Lista afiliados com filtragem por status e paginação.
    
    Este endpoint unifica as funcionalidades de:
    - /affiliates/requests (status=pending)
    - /affiliates/list (status=approved)
    
    Query params:
        status (str, opcional): Filtrar por status ('pending', 'approved', 'blocked', 'all'). 
                              Valor padrão: 'all'.
        page (int, opcional): Número da página atual. Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.
        user_id (int, opcional): Filtrar por ID do usuário específico.
    
    Returns:
        web.Response: JSON contendo a lista de afiliados que correspondem aos filtros,
                     incluindo objetos User e Sales completos (não apenas IDs).
    """
    db = request.app[DB_SESSION_KEY]
    
    # Obter parâmetros de filtro e paginação
    status = request.query.get("status", "all")
    user_id = request.query.get("user_id")
    
    # Obter parâmetros de paginação
    try:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "10"))
        
        # Validação básica
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        page = 1
        per_page = 10
    
    # Verificar se está buscando um usuário específico
    if user_id is not None:
        try:
            # Se o ID do usuário logado é solicitado, não precisamos ser admin
            current_user = request.get("user", {})
            if str(current_user.get("id")) == user_id:
                affiliate_service = AffiliateService(db)
                result = await affiliate_service.get_affiliation_status(int(user_id))
                
                if not result["success"]:
                    return web.json_response({"error": result["error"]}, status=404)
                
                # O formato já está correto, apenas retornar
                return web.json_response({"data": result["data"]}, status=200)
            
            # Caso contrário, é necessário ser admin para obter informações de outro usuário
            if "admin" not in request.get("user", {}).get("roles", []):
                return web.json_response(
                    {"error": "Permissão negada para acessar informações de outro usuário"},
                    status=403
                )
        except ValueError:
            return web.json_response(
                {"error": "ID de usuário inválido"},
                status=400
            )
    
    # Buscar afiliados com filtro
    affiliate_service = AffiliateService(db)
    
    # Chamada genérica para o serviço
    result = await affiliate_service.list_affiliates(
        status=status,
        page=page,
        per_page=per_page,
        user_id=user_id
    )
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    # Obter dados e total
    affiliates = result["data"].get("affiliates", result["data"])
    total = result["data"].get("total", len(affiliates))
    
    # Padronização conforme o padrão da API
    response_data = {
        "data": affiliates,
        "meta": {
            "page": page,
            "page_size": per_page,
            "total_count": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }
    
    return web.json_response(response_data, status=200)

@routes.get("/affiliates/requests")
@require_role(["admin"])
async def list_affiliate_requests(request: web.Request) -> web.Response:
    """
    [DEPRECIADO] Lista todas as solicitações de afiliação pendentes com paginação.
    Use /affiliates?status=pending em vez disso.

    Query params:
        page (int, opcional): Número da página atual (começando em 1). Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de solicitações de afiliação pendentes.
    """
    # Reencaminhar para o novo endpoint com o parâmetro status=pending
    url = request.url.with_path('/affiliates').with_query(
        f"status=pending&{request.query_string}"
    )
    
    # Avisar sobre depreciação nos logs
    import logging
    logging.warning("Endpoint /affiliates/requests está depreciado. Use /affiliates?status=pending em vez disso.")
    
    # Redirecionar internamente para o novo endpoint
    return await list_affiliates(request)

@routes.get("/affiliates/list")
@require_role(["admin"])
async def list_approved_affiliates(request: web.Request) -> web.Response:
    """
    [DEPRECIADO] Lista todos os afiliados aprovados no sistema, com paginação.
    Use /affiliates?status=approved em vez disso.

    Query params:
        page (int, opcional): Número da página atual (começando em 1). Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de afiliados aprovados.
    """
    # Reencaminhar para o novo endpoint com o parâmetro status=approved
    url = request.url.with_path('/affiliates').with_query(
        f"status=approved&{request.query_string}"
    )
    
    # Avisar sobre depreciação nos logs
    import logging
    logging.warning("Endpoint /affiliates/list está depreciado. Use /affiliates?status=approved em vez disso.")
    
    # Redirecionar internamente para o novo endpoint
    return await list_affiliates(request)

@routes.get("/affiliates/status")
@require_auth
async def get_affiliation_status(request: web.Request) -> web.Response:
    """
    [DEPRECIADO] Consulta o status da solicitação de afiliação do usuário autenticado.
    Use /affiliates?user_id=<ID_DO_USUÁRIO> em vez disso.

    Returns:
        web.Response: JSON contendo as informações de status da solicitação.
    """
    # Obter o ID do usuário das informações de autenticação
    user_id = request["user"]["id"]
    
    # Avisar sobre depreciação nos logs
    import logging
    logging.warning("Endpoint /affiliates/status está depreciado. Use /affiliates?user_id=<ID_DO_USUÁRIO> em vez disso.")
    
    # Criar uma nova request com o parâmetro user_id
    new_request = request.clone()
    new_request._query = {"user_id": str(user_id)}
    
    # Redirecionar internamente para o novo endpoint
    return await list_affiliates(new_request)
