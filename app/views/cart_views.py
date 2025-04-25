# D:\3xDigital\app\views\cart_views.py

"""
cart_views.py

Este módulo define os endpoints para o gerenciamento de carrinhos de compras,
incluindo operações que não exigem autenticação.

Endpoints:
    - POST /cart/items: Adiciona um item ao carrinho.
    - PUT /cart/items/{product_id}: Atualiza a quantidade de um item no carrinho.
    - DELETE /cart/items/{product_id}: Remove um item do carrinho.
    - GET /cart/items: Lista todos os itens do carrinho.
    - DELETE /cart/items: Limpa o carrinho (remove todos os itens).
    - POST /cart/checkout: Converte o carrinho em um pedido (requer autenticação).

Regras de Negócio:
    - Carrinhos são associados a uma sessão para usuários não autenticados.
    - O ID da sessão é enviado pelos clientes no cabeçalho "X-Session-ID".
    - A validação de estoque é feita ao adicionar/atualizar itens no carrinho.
    - O checkout requer autenticação, mas as demais operações não.
    - Após um login bem-sucedido, o carrinho temporário é associado ao usuário.

Dependências:
    - AIOHTTP para manipulação de requisições.
    - CartService para lógica de negócios de carrinhos.
    - Middleware de autenticação para proteção do endpoint de checkout.
"""

import uuid
from aiohttp import web
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.services.cart_service import CartService

routes = web.RouteTableDef()

def get_session_id(request: web.Request) -> str:
    """
    Obtém o ID da sessão do cabeçalho da requisição ou gera um novo.
    
    Args:
        request (web.Request): A requisição HTTP.
        
    Returns:
        str: O ID da sessão.
    """
    session_id = request.headers.get("X-Session-ID")
    
    if not session_id:
        session_id = str(uuid.uuid4())
        
    return session_id

@routes.post("/cart/items")
async def add_to_cart(request: web.Request) -> web.Response:
    """
    Adiciona um item ao carrinho.
    
    JSON de entrada:
        {
            "product_id": 1,
            "quantity": 2
        }
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        
    Returns:
        web.Response: JSON com os itens atualizados do carrinho.
    """
    data = await request.json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    
    if not product_id:
        return web.json_response({"error": "ID do produto é obrigatório."}, status=400)
        
    if not isinstance(quantity, int) or quantity <= 0:
        return web.json_response({"error": "Quantidade deve ser um número inteiro positivo."}, status=400)
    
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    
    cart_service = CartService(db)
    result = await cart_service.add_to_cart(session_id, product_id, quantity)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response(result["data"])
    response.headers["X-Session-ID"] = session_id
    return response

@routes.put("/cart/items/{product_id}")
async def update_cart_item(request: web.Request) -> web.Response:
    """
    Atualiza a quantidade de um item no carrinho.
    
    JSON de entrada:
        {
            "quantity": 3
        }
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        
    Returns:
        web.Response: JSON com os itens atualizados do carrinho.
    """
    product_id = int(request.match_info.get("product_id"))
    data = await request.json()
    quantity = data.get("quantity", 1)
    
    if not isinstance(quantity, int) or quantity < 0:
        return web.json_response({"error": "Quantidade deve ser um número inteiro não negativo."}, status=400)
    
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    
    cart_service = CartService(db)
    result = await cart_service.update_cart_item(session_id, product_id, quantity)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response(result["data"])
    response.headers["X-Session-ID"] = session_id
    return response

@routes.delete("/cart/items/{product_id}")
async def remove_from_cart(request: web.Request) -> web.Response:
    """
    Remove um item do carrinho.
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        
    Returns:
        web.Response: JSON com os itens atualizados do carrinho.
    """
    product_id = int(request.match_info.get("product_id"))
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    
    cart_service = CartService(db)
    result = await cart_service.remove_from_cart(session_id, product_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response(result["data"])
    response.headers["X-Session-ID"] = session_id
    return response

@routes.get("/cart/items")
async def get_cart_items(request: web.Request) -> web.Response:
    """
    Lista todos os itens do carrinho.
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        
    Returns:
        web.Response: JSON com os itens do carrinho.
    """
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    
    cart_service = CartService(db)
    result = await cart_service.get_cart_items(session_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response(result["data"])
    response.headers["X-Session-ID"] = session_id
    return response

@routes.delete("/cart/items")
async def clear_cart(request: web.Request) -> web.Response:
    """
    Limpa o carrinho, removendo todos os itens.
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        
    Returns:
        web.Response: JSON com o carrinho vazio.
    """
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    
    cart_service = CartService(db)
    result = await cart_service.clear_cart(session_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response(result["data"])
    response.headers["X-Session-ID"] = session_id
    return response

@routes.post("/cart/checkout")
@require_role(["user", "admin", "affiliate"])
async def checkout(request: web.Request) -> web.Response:
    """
    Converte o carrinho em um pedido para um usuário autenticado.
    
    Headers:
        X-Session-ID: ID da sessão do usuário (opcional, um novo será gerado se ausente).
        Authorization: Bearer token JWT (obrigatório).
        
    Query params:
        ref (str, opcional): Código de referência do afiliado.
        
    Returns:
        web.Response: JSON com os detalhes do pedido criado.
    """
    # Obter dados do usuário autenticado (injetados pelo middleware)
    try:
        user_id = request["user"]["id"]
    except KeyError:
        return web.json_response({"error": "Dados do usuário não encontrados na requisição."}, status=401)
    
    session_id = get_session_id(request)
    db = request.app[DB_SESSION_KEY]
    ref_code = request.rel_url.query.get("ref")
    
    cart_service = CartService(db)
    result = await cart_service.convert_to_order(session_id, user_id, ref_code)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    response = web.json_response({
        "message": "Pedido criado com sucesso!", 
        "order_id": result["data"]["order_id"], 
        "total": result["data"]["total"]
    }, status=201)
    
    response.headers["X-Session-ID"] = session_id
    return response 