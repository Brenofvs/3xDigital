# D:\3xDigital\app\views\categories_views.py

"""
categories_views.py

Este módulo define os endpoints para o gerenciamento de categorias, incluindo operações CRUD.

Endpoints:
    GET /categories: Lista todas as categorias – acesso para usuários autenticados (admin, user ou affiliate).
    GET /categories/{category_id}: Obtém os detalhes de uma categoria – acesso para usuários autenticados.
    POST /categories: Cria uma nova categoria – somente admin.
    PUT /categories/{category_id}: Atualiza uma categoria existente – somente admin.
    DELETE /categories/{category_id}: Deleta uma categoria – somente admin.
    
Dependências:
    - AIOHTTP para manipulação de requisições.
    - CategoryService para lógica de negócios de categorias.
    - Middleware de autenticação para proteção dos endpoints.
"""

from aiohttp import web
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.services.category_service import CategoryService

routes = web.RouteTableDef()

@routes.get("/categories")
@require_role(["admin", "user", "affiliate"])
async def list_categories(request: web.Request) -> web.Response:
    """
    Lista todas as categorias cadastradas com suporte a paginação.

    Query params:
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)
        search (str, opcional): Termo de busca para filtrar categorias por nome

    Returns:
        web.Response: Resposta JSON contendo a lista de categorias e metadados de paginação.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Extrai parâmetros da query
    page = int(request.rel_url.query.get("page", 1))
    page_size = int(request.rel_url.query.get("page_size", 20))
    search = request.rel_url.query.get("search")
    
    # Limita o tamanho da página para evitar sobrecarga
    page_size = min(page_size, 100)
    
    category_service = CategoryService(db)
    result = await category_service.list_categories(page, page_size, search)
    
    return web.json_response(result["data"], status=200)

@routes.get("/categories/{category_id}")
@require_role(["admin", "user", "affiliate"])
async def get_category(request: web.Request) -> web.Response:
    """
    Obtém os detalhes de uma categoria específica.

    Args:
        request (web.Request): Requisição contendo o parâmetro 'category_id'.

    Returns:
        web.Response: Resposta JSON com os dados da categoria ou mensagem de erro se não encontrada.
    """
    category_id = request.match_info.get("category_id")
    db = request.app[DB_SESSION_KEY]

    category_service = CategoryService(db)
    result = await category_service.get_category(category_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response({"category": result["data"]}, status=200)

@routes.post("/categories")
@require_role(["admin"])
async def create_category(request: web.Request) -> web.Response:
    """
    Cria uma nova categoria.

    JSON de entrada:
        {
            "name": "Nome da categoria"
        }

    Args:
        request (web.Request): Requisição contendo os dados da categoria em JSON.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso e os dados da categoria criada.
    """
    try:
        data = await request.json()
        name = data["name"]
    except KeyError as e:
        return web.json_response({"error": f"Campo ausente: {str(e)}"}, status=400)
    
    db = request.app[DB_SESSION_KEY]

    category_service = CategoryService(db)
    result = await category_service.create_category(name)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=400)
    
    return web.json_response(
        {"message": "Categoria criada com sucesso", "category": result["data"]}, 
        status=201
    )

@routes.put("/categories/{category_id}")
@require_role(["admin"])
async def update_category(request: web.Request) -> web.Response:
    """
    Atualiza os dados de uma categoria existente.

    JSON de entrada:
        {
            "name": "Novo nome da categoria"
        }

    Args:
        request (web.Request): Requisição contendo o ID da categoria e os dados a atualizar.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso e os dados atualizados da categoria,
                      ou mensagem de erro se a categoria não for encontrada.
    """
    category_id = request.match_info.get("category_id")
    data = await request.json()
    name = data.get("name")
    
    if not name:
        return web.json_response({"error": "Nome da categoria é obrigatório"}, status=400)
    
    db = request.app[DB_SESSION_KEY]

    category_service = CategoryService(db)
    result = await category_service.update_category(category_id, name)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response(
        {"message": "Categoria atualizada com sucesso", "category": result["data"]}, 
        status=200
    )

@routes.delete("/categories/{category_id}")
@require_role(["admin"])
async def delete_category(request: web.Request) -> web.Response:
    """
    Deleta uma categoria existente.

    Args:
        request (web.Request): Requisição contendo o ID da categoria.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso ou erro se a categoria não for encontrada.
    """
    category_id = request.match_info.get("category_id")
    db = request.app[DB_SESSION_KEY]

    category_service = CategoryService(db)
    result = await category_service.delete_category(category_id)
    
    if not result["success"]:
        # Verificar se o erro é devido a produtos vinculados à categoria
        if "produtos associados" in result["error"]:
            return web.json_response({"error": result["error"]}, status=400)
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response({"message": "Categoria deletada com sucesso"}, status=200)
