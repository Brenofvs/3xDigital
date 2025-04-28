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
    
    return web.json_response({"affiliate_link": result["data"]}, status=200)

@routes.get("/affiliates/sales")
@require_role(["affiliate"])
async def get_affiliate_sales(request: web.Request) -> web.Response:
    """
    Retorna a lista de vendas e comissões atribuídas ao afiliado logado.

    É necessário que:
    1. O usuário tenha o papel 'affiliate'
    2. O status da solicitação esteja como 'approved'

    Returns:
        web.Response: JSON contendo a lista de vendas, cada uma com order_id e commission.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
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
    
    return web.json_response({"sales": result["data"]}, status=200)

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
    data = await request.json()
    commission_rate = data.get("commission_rate", 0.05)
    
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


@routes.get("/affiliates/requests")
@require_role(["admin"])
async def list_affiliate_requests(request: web.Request) -> web.Response:
    """
    Lista todas as solicitações de afiliação pendentes (afiliados com request_status == 'pending') com paginação.

    Query params:
        page (int, opcional): Número da página atual (começando em 1). Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de solicitações de afiliação com os dados completos do usuário.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Obtendo parâmetros de paginação da query string
    try:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "10"))
        
        # Validação básica
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        # Se houver erro na conversão, usa valores padrão
        page = 1
        per_page = 10
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.list_affiliate_requests(page, per_page)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(result["data"], status=200)

@routes.get("/affiliates/list")
@require_role(["admin"])
async def list_approved_affiliates(request: web.Request) -> web.Response:
    """
    Lista todos os afiliados aprovados no sistema, com paginação.

    Query params:
        page (int, opcional): Número da página atual (começando em 1). Valor padrão: 1.
        per_page (int, opcional): Quantidade de registros por página. Valor padrão: 10.

    Returns:
        web.Response: JSON contendo a lista de afiliados aprovados, cada um com os dados completos do usuário.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Obtendo parâmetros de paginação da query string
    try:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "10"))
        
        # Validação básica
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        # Se houver erro na conversão, usa valores padrão
        page = 1
        per_page = 10
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.list_approved_affiliates(page, per_page)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(result["data"], status=200)

@routes.get("/affiliates/status")
@require_auth
async def get_affiliation_status(request: web.Request) -> web.Response:
    """
    Consulta o status da solicitação de afiliação do usuário autenticado.

    Este endpoint permite que qualquer usuário autenticado consulte o status
    da sua solicitação de afiliação, independentemente do seu papel no sistema.

    Returns:
        web.Response: JSON contendo as informações de status da solicitação:
            - status: 'pending', 'approved' ou 'blocked'
            - created_at: data de criação da solicitação
            - updated_at: data da última atualização
            - message: mensagem informativa sobre o status
            - rejection_reason: motivo da recusa (se houver e status for 'blocked')
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.get_affiliation_status(user["id"])
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response(result["data"], status=200)
