# D:\#3xDigital\app\views\orders_views.py

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
    - Apenas administradores podem alterar o status de pedidos.

Dependências:
    - AIOHTTP para manipulação de requisições.
    - SQLAlchemy assíncrono para interagir com o banco de dados.
    - Middleware de autenticação para proteção dos endpoints.

"""

from aiohttp import web
from sqlalchemy import select
from app.models.database import Order, OrderItem, Product
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role

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

    Returns:
        web.Response: JSON com detalhes do pedido criado.

    Regras:
        - Apenas usuários autenticados podem criar pedidos.
        - Valida se os produtos existem e têm estoque disponível.
        - Deduz a quantidade do estoque após criação do pedido.
    """
    data = await request.json()
    items = data.get("items", [])

    if not items:
        return web.json_response({"error": "O pedido deve conter pelo menos um item."}, status=400)

    user_id = request["user"]["id"]
    db = request.app[DB_SESSION_KEY]

    total = 0
    order_items = []

    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        # Verifica se o produto existe e tem estoque suficiente
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        if not product:
            return web.json_response({"error": f"Produto ID {product_id} não encontrado."}, status=404)
        if product.stock < quantity:
            return web.json_response({"error": f"Estoque insuficiente para o produto ID {product_id}."}, status=400)

        # Atualiza estoque e calcula total do pedido
        product.stock -= quantity
        total += product.price * quantity

        order_items.append(OrderItem(product_id=product_id, quantity=quantity, price=product.price))

    # Cria o pedido
    new_order = Order(user_id=user_id, status="processing", total=total)
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    # Associa os itens ao pedido
    for order_item in order_items:
        order_item.order_id = new_order.id
        db.add(order_item)

    await db.commit()

    return web.json_response(
        {"message": "Pedido criado com sucesso!", "order_id": new_order.id, "total": total},
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
    result = await db.execute(select(Order))
    orders = result.scalars().all()

    orders_list = [{"id": o.id, "user_id": o.user_id, "status": o.status, "total": o.total} for o in orders]
    
    return web.json_response({"orders": orders_list}, status=200)


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
    db = request.app[DB_SESSION_KEY]

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar()

    if not order:
        return web.json_response({"error": "Pedido não encontrado."}, status=404)

    # Permitir que usuários visualizem apenas seus próprios pedidos
    user_role = request["user"]["role"]
    if user_role != "admin" and request["user"]["id"] != order.user_id:
        return web.json_response({"error": "Acesso negado."}, status=403)

    order_data = {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "total": order.total,
        "items": [{"product_id": i.product_id, "quantity": i.quantity, "price": i.price} for i in order.items]
    }

    return web.json_response({"order": order_data}, status=200)


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

    valid_statuses = ["processing", "shipped", "delivered", "returned"]
    if new_status not in valid_statuses:
        return web.json_response({"error": "Status inválido."}, status=400)

    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar()

    if not order:
        return web.json_response({"error": "Pedido não encontrado."}, status=404)

    order.status = new_status
    await db.commit()
    return web.json_response({"message": f"Status do pedido atualizado para '{new_status}'"}, status=200)


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

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar()

    if not order:
        return web.json_response({"error": "Pedido não encontrado."}, status=404)

    await db.delete(order)
    await db.commit()

    return web.json_response({"message": "Pedido deletado com sucesso."}, status=200)
