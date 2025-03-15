# D:\3xDigital\app\views\affiliates_views.py

"""
affiliates_views.py

Este módulo define os endpoints para gerenciamento de afiliados e rastreamento de vendas.

Endpoints:
    - GET /affiliates/link: Retorna o link de afiliado único para o usuário logado.
    - GET /affiliates/sales: Lista as vendas atribuídas ao afiliado, com informações de comissão.
    - POST /affiliates/request: Permite que um usuário solicite a afiliação.
    - PUT /affiliates/{affiliate_id}: Permite que um administrador atualize os dados do afiliado.
    - GET /affiliates/requests: Lista as solicitações de afiliação pendentes.

Regras de Negócio:
    - Apenas usuários com papel 'affiliate' podem acessar os endpoints /affiliates/link e /affiliates/sales.
    - Usuários com papel 'user' podem solicitar afiliação através de /affiliates/request.
    - O link de afiliado é construído a partir de um código de referência único.
    - As vendas atribuídas são obtidas a partir dos registros na tabela Sale.
    - Apenas administradores podem atualizar os dados do afiliado e listar as solicitações pendentes.

Dependências:
    - AIOHTTP para manipulação de requisições.
    - AffiliateService para lógica de negócios de afiliados.
    - Middleware de autenticação para proteção dos endpoints.
"""

from aiohttp import web
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.services.affiliate_service import AffiliateService

routes = web.RouteTableDef()

@routes.get("/affiliates/link")
@require_role(["affiliate"])
async def get_affiliate_link(request: web.Request) -> web.Response:
    """
    Retorna o link de afiliado para o usuário logado.

    O link é gerado utilizando o código de referência do afiliado. Se o afiliado estiver inativo,
    retorna um erro informando que a afiliação não está aprovada.

    Returns:
        web.Response: JSON contendo o link de afiliado.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    base_url = str(request.url.with_path("").with_query({}))
    result = await affiliate_service.get_affiliate_link(user["id"], base_url)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, 
                                status=404 if "não encontrado" in result["error"] else 403)
    
    return web.json_response({"affiliate_link": result["data"]}, status=200)

@routes.get("/affiliates/sales")
@require_role(["affiliate"])
async def get_affiliate_sales(request: web.Request) -> web.Response:
    """
    Retorna a lista de vendas e comissões atribuídas ao afiliado logado.

    Se o afiliado estiver inativo, retorna um erro.

    Returns:
        web.Response: JSON contendo a lista de vendas, cada uma com order_id e commission.
    """
    user = request["user"]
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.get_affiliate_sales(user["id"])
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, 
                                status=404 if "não encontrado" in result["error"] else 403)
    
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
            "request_status": "approved"  # ou "blocked"
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
    
    return web.json_response({"message": "Dados do afiliado atualizados com sucesso."}, status=200)


@routes.get("/affiliates/requests")
@require_role(["admin"])
async def list_affiliate_requests(request: web.Request) -> web.Response:
    """
    Lista todas as solicitações de afiliação pendentes (afiliados com request_status == 'pending').

    Returns:
        web.Response: JSON contendo a lista de solicitações de afiliação.
    """
    db = request.app[DB_SESSION_KEY]
    
    affiliate_service = AffiliateService(db)
    result = await affiliate_service.list_affiliate_requests()
    
    return web.json_response({"affiliate_requests": result["data"]}, status=200)
