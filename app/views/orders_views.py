# D:\3xDigital\app\views\orders_views.py

"""
orders_views.py

Este módulo define os endpoints para o gerenciamento de pedidos no sistema.

Endpoints:
    - POST /orders: Cria um novo pedido.
    - GET /orders: Lista todos os pedidos.
    - GET /orders/{order_id}: Obtém os detalhes de um pedido específico.
    - PUT /orders/{order_id}/status: Atualiza o status de um pedido.
    - DELETE /orders/{order_id}: Deleta um pedido.

Regras de Negócio:
    - Apenas usuários autenticados podem criar pedidos.
    - O pedido deve conter pelo menos um item válido.
    - O estoque dos produtos será atualizado ao criar um pedido.
    - Se for enviado um parâmetro de query "ref" (código de afiliado), o sistema
      registra a venda e calcula a comissão.
    - Apenas administradores podem alterar o status de pedidos.

Dependências:
    - AIOHTTP para manipulação de requisições.
    - OrderService para lógica de negócios de pedidos.
    - Middleware de autenticação para proteção dos endpoints.
"""

from aiohttp import web
from app.models.database import Order, OrderItem, Product, Affiliate, Sale
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.services.order_service import OrderService

routes = web.RouteTableDef()


@routes.post("/orders")
@require_role(["user", "admin", "affiliate"])
async def create_order(request: web.Request) -> web.Response:
    """
    Cria um novo pedido com base nos itens enviados no corpo da requisição.

    JSON de entrada:
        {
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 3, "quantity": 1}
            ]
        }

    Se a query string contiver o parâmetro "ref", o sistema tenta associar o pedido
    ao afiliado correspondente e calcular a comissão com base na taxa do afiliado.

    Returns:
        web.Response: JSON com detalhes do pedido criado.
    
    Regras:
        - Apenas usuários autenticados podem criar pedidos.
        - Valida se os produtos existem e têm estoque disponível.
        - Deduz a quantidade do estoque após criação do pedido.
        - Se fornecido, o código de referência é validado e a venda é registrada.
    """
    data = await request.json()
    items = data.get("items", [])

    # Obter dados do usuário autenticado (injetados pelo middleware)
    try:
        user_id = request["user"]["id"]
    except KeyError:
        return web.json_response({"error": "Dados do usuário não encontrados na requisição."}, status=401)

    db = request.app[DB_SESSION_KEY]
    
    # Usar OrderService em vez de acessar o banco diretamente
    order_service = OrderService(db)
    ref_code = request.rel_url.query.get("ref")
    
    result = await order_service.create_order(user_id, items, ref_code)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(
        {
            "message": "Pedido criado com sucesso!", 
            "order_id": result["data"]["order_id"], 
            "total": result["data"]["total"]
        },
        status=201
    )


@routes.get("/orders")
@require_role(["admin"])
async def list_orders(request: web.Request) -> web.Response:
    """
    Lista todos os pedidos do sistema.

    Returns:
        web.Response: JSON contendo a lista de pedidos.
    
    Apenas administradores podem visualizar todos os pedidos.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Usar OrderService em vez de acessar o banco diretamente
    order_service = OrderService(db)
    result = await order_service.list_orders()
    
    return web.json_response({"orders": result["data"]}, status=200)


@routes.get("/orders/{order_id}")
@require_role(["user", "admin"])
async def get_order(request: web.Request) -> web.Response:
    """
    Obtém os detalhes de um pedido específico.

    Args:
        request (web.Request): Contém o 'order_id' na URL.

    Returns:
        web.Response: JSON com detalhes do pedido.
    
    Usuários podem visualizar apenas seus próprios pedidos.
    Administradores podem visualizar qualquer pedido.
    """
    order_id = request.match_info.get("order_id")
    user = request["user"]
    is_admin = user["role"] == "admin"
    user_id = user["id"]
    db = request.app[DB_SESSION_KEY]

    # Usar OrderService em vez de acessar o banco diretamente
    order_service = OrderService(db)
    result = await order_service.get_order(order_id, user_id, is_admin)
    
    if not result["success"]:
        status = 403 if result["error"] == "Acesso negado." else 404
        return web.json_response({"error": result["error"]}, status=status)
    
    return web.json_response({"order": result["data"]}, status=200)


@routes.put("/orders/{order_id}/status")
@require_role(["admin"])
async def update_order_status(request: web.Request) -> web.Response:
    """
    Atualiza o status de um pedido.

    JSON de entrada:
        {
            "status": "shipped"
        }

    Returns:
        web.Response: JSON informando sucesso ou erro.

    Apenas administradores podem alterar o status do pedido.
    """
    order_id = request.match_info.get("order_id")
    data = await request.json()
    new_status = data.get("status")
    db = request.app[DB_SESSION_KEY]
    
    # Usar OrderService em vez de acessar o banco diretamente
    order_service = OrderService(db)
    result = await order_service.update_order_status(order_id, new_status)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, 
                               status=400 if "inválido" in result["error"] else 404)
    
    return web.json_response(
        {"message": f"Status do pedido atualizado para '{new_status}'"},
        status=200
    )


@routes.delete("/orders/{order_id}")
@require_role(["admin"])
async def delete_order(request: web.Request) -> web.Response:
    """
    Deleta um pedido existente.

    Returns:
        web.Response: JSON com mensagem de sucesso ou erro.
    
    Apenas administradores podem excluir pedidos.
    """
    order_id = request.match_info.get("order_id")
    db = request.app[DB_SESSION_KEY]
    
    # Usar OrderService em vez de acessar o banco diretamente
    order_service = OrderService(db)
    result = await order_service.delete_order(order_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response({"message": "Pedido deletado com sucesso."}, status=200)
