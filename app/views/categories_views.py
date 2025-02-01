# D:\#3xDigital\app\views\categories_views.py

"""
categories_views.py

Este módulo define os endpoints para o gerenciamento de categorias, incluindo operações CRUD.

Endpoints:
    GET /categories: Lista todas as categorias.
    GET /categories/{category_id}: Obtém os detalhes de uma categoria específica.
    POST /categories: Cria uma nova categoria.
    PUT /categories/{category_id}: Atualiza uma categoria existente.
    DELETE /categories/{category_id}: Deleta uma categoria.
"""

from aiohttp import web
from sqlalchemy import select
from app.models.database import Category
from app.config.settings import DB_SESSION_KEY

routes = web.RouteTableDef()

@routes.get("/categories")
async def list_categories(request: web.Request) -> web.Response:
    """
    Lista todas as categorias cadastradas.

    Returns:
        web.Response: Resposta JSON contendo a lista de categorias.
    """
    # Obtém a instância de AsyncSession injetada na aplicação
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    categories_list = [{"id": c.id, "name": c.name} for c in categories]
    return web.json_response({"categories": categories_list}, status=200)

@routes.get("/categories/{category_id}")
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
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar()
    if not category:
        return web.json_response({"error": "Categoria não encontrada"}, status=404)
    category_data = {"id": category.id, "name": category.name}
    return web.json_response({"category": category_data}, status=200)

@routes.post("/categories")
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
    new_category = Category(name=name)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    category_data = {"id": new_category.id, "name": new_category.name}
    return web.json_response({"message": "Categoria criada com sucesso", "category": category_data}, status=201)

@routes.put("/categories/{category_id}")
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
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar()
    if not category:
        return web.json_response({"error": "Categoria não encontrada"}, status=404)
    if "name" in data:
        category.name = data["name"]
    await db.commit()
    await db.refresh(category)
    updated_data = {"id": category.id, "name": category.name}
    return web.json_response({"message": "Categoria atualizada com sucesso", "category": updated_data}, status=200)

@routes.delete("/categories/{category_id}")
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
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar()
    if not category:
        return web.json_response({"error": "Categoria não encontrada"}, status=404)
    await db.delete(category)
    await db.commit()
    return web.json_response({"message": "Categoria deletada com sucesso"}, status=200)
