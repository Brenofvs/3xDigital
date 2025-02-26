# D:\#3xDigital\app\views\affiliates_views.py

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
    - SQLAlchemy assíncrono para interagir com o banco de dados.
    - Middleware de autenticação para proteção dos endpoints.
"""

import uuid
from aiohttp import web
from sqlalchemy import select
from app.models.database import Affiliate, Sale
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role

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
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user["id"]))
    affiliate = result.scalar()
    if not affiliate:
        return web.json_response({"error": "Afiliado não encontrado."}, status=404)
    if affiliate.request_status != 'approved':
        return web.json_response({"error": "Afiliado inativo. Solicitação pendente ou rejeitada."}, status=403)
    base_url = str(request.url.with_path("").with_query({}))
    link = f"{base_url}/?ref={affiliate.referral_code}"
    return web.json_response({"affiliate_link": link}, status=200)

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
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user["id"]))
    affiliate = result.scalar()
    if not affiliate:
        return web.json_response({"error": "Afiliado não encontrado."}, status=404)
    if affiliate.request_status != 'approved':
        return web.json_response({"error": "Afiliado inativo. Solicitação pendente ou rejeitada."}, status=403)
    result = await db.execute(
        select(Sale).join(Affiliate).where(Affiliate.user_id == user["id"])
    )
    sales = result.scalars().all()
    sales_list = [{"order_id": sale.order_id, "commission": sale.commission} for sale in sales]
    return web.json_response({"sales": sales_list}, status=200)

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
    # Verifica se já existe registro de afiliação para o usuário
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user["id"]))
    existing = result.scalar()
    if existing:
        return web.json_response({"error": "Solicitação de afiliação já existente."}, status=400)
    # Gera um código de referência único
    referral_code = f"REF{uuid.uuid4().hex[:8].upper()}"
    data = await request.json()
    commission_rate = data.get("commission_rate", 0.05)
    new_affiliate = Affiliate(
        user_id=user["id"],
        referral_code=referral_code,
        commission_rate=commission_rate,
        request_status='pending'
    )
    db.add(new_affiliate)
    await db.commit()
    await db.refresh(new_affiliate)
    return web.json_response(
        {"message": "Solicitação de afiliação registrada com sucesso.", "referral_code": new_affiliate.referral_code},
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
    result = await db.execute(select(Affiliate).where(Affiliate.id == affiliate_id))
    affiliate = result.scalar()
    if not affiliate:
        return web.json_response({"error": "Afiliado não encontrado."}, status=404)
    if "commission_rate" in data:
        affiliate.commission_rate = data["commission_rate"]
    if "request_status" in data:
        affiliate.request_status = data["request_status"]
    await db.commit()
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
    result = await db.execute(select(Affiliate).where(Affiliate.request_status == 'pending'))
    affiliates = result.scalars().all()
    affiliates_list = [
        {"id": a.id, "user_id": a.user_id, "referral_code": a.referral_code, "commission_rate": a.commission_rate}
        for a in affiliates
    ]
    return web.json_response({"affiliate_requests": affiliates_list}, status=200)
