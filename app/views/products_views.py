# D:\#3xDigital\app\views\products_views.py

"""
products_views.py

Este módulo define os endpoints para o gerenciamento de produtos, incluindo operações CRUD.

Endpoints:
    GET /products: Lista todos os produtos.
    GET /products/{product_id}: Obtém os detalhes de um produto específico.
    POST /products: Cria um novo produto.
    PUT /products/{product_id}: Atualiza um produto existente.
    DELETE /products/{product_id}: Deleta um produto.
"""

from aiohttp import web
from sqlalchemy import select
from app.models.database import Product, Category
from app.config.settings import DB_SESSION_KEY

routes = web.RouteTableDef()

@routes.get("/products")
async def list_products(request: web.Request) -> web.Response:
    """
    Lista todos os produtos cadastrados.

    Returns:
        web.Response: Resposta JSON contendo a lista de produtos.
    """
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Product))
    products = result.scalars().all()
    products_list = [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "price": p.price,
        "stock": p.stock,
        "category_id": p.category_id
    } for p in products]
    return web.json_response({"products": products_list}, status=200)

@routes.get("/products/{product_id}")
async def get_product(request: web.Request) -> web.Response:
    """
    Obtém os detalhes de um produto específico.

    Args:
        request (web.Request): Requisição contendo o parâmetro 'product_id'.

    Returns:
        web.Response: Resposta JSON com os dados do produto ou mensagem de erro se não encontrado.
    """
    product_id = request.match_info.get("product_id")
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar()
    if not product:
        return web.json_response({"error": "Produto não encontrado"}, status=404)
    product_data = {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "category_id": product.category_id
    }
    return web.json_response({"product": product_data}, status=200)

@routes.post("/products")
async def create_product(request: web.Request) -> web.Response:
    """
    Cria um novo produto.

    JSON de entrada:
        {
            "name": "Nome do produto",
            "description": "Descrição do produto",
            "price": 100.0,
            "stock": 10,
            "category_id": 1  # Opcional: ID da categoria associada
        }

    Args:
        request (web.Request): Requisição contendo os dados do produto em JSON.

    Returns:
        web.Response: Resposta JSON com a mensagem de sucesso e os dados do produto criado.
    """
    try:
        data = await request.json()
        name = data["name"]
        description = data.get("description", "")
        price = float(data["price"])
        stock = int(data["stock"])
        category_id = data.get("category_id")
    except KeyError as e:
        return web.json_response({"error": f"Campo ausente: {str(e)}"}, status=400)
    except (ValueError, TypeError):
        return web.json_response({"error": "Dados inválidos para 'price' ou 'stock'"}, status=400)
    
    db = request.app[DB_SESSION_KEY]
    # Valida se a categoria existe, caso seja informada.
    if category_id is not None:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        if not category:
            return web.json_response({"error": "Categoria não encontrada"}, status=404)
    new_product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        category_id=category_id
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    product_data = {
        "id": new_product.id,
        "name": new_product.name,
        "description": new_product.description,
        "price": new_product.price,
        "stock": new_product.stock,
        "category_id": new_product.category_id
    }
    return web.json_response({"message": "Produto criado com sucesso", "product": product_data}, status=201)

@routes.put("/products/{product_id}")
async def update_product(request: web.Request) -> web.Response:
    """
    Atualiza os dados de um produto existente.

    JSON de entrada pode conter:
        {
            "name": "Novo nome",
            "description": "Nova descrição",
            "price": 150.0,
            "stock": 20,
            "category_id": 2
        }

    Args:
        request (web.Request): Requisição contendo o ID do produto e os dados a atualizar.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso e os dados atualizados do produto,
                      ou mensagem de erro se o produto ou categoria não for encontrado.
    """
    product_id = request.match_info.get("product_id")
    data = await request.json()
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar()
    if not product:
        return web.json_response({"error": "Produto não encontrado"}, status=404)
    if "name" in data:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "price" in data:
        try:
            product.price = float(data["price"])
        except (ValueError, TypeError):
            return web.json_response({"error": "Valor de 'price' inválido"}, status=400)
    if "stock" in data:
        try:
            product.stock = int(data["stock"])
        except (ValueError, TypeError):
            return web.json_response({"error": "Valor de 'stock' inválido"}, status=400)
    if "category_id" in data:
        category_id = data["category_id"]
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        if not category:
            return web.json_response({"error": "Categoria não encontrada"}, status=404)
        product.category_id = category_id
    await db.commit()
    await db.refresh(product)
    updated_data = {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "category_id": product.category_id
    }
    return web.json_response({"message": "Produto atualizado com sucesso", "product": updated_data}, status=200)

@routes.delete("/products/{product_id}")
async def delete_product(request: web.Request) -> web.Response:
    """
    Deleta um produto existente.

    Args:
        request (web.Request): Requisição contendo o ID do produto.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso ou erro se o produto não for encontrado.
    """
    product_id = request.match_info.get("product_id")
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar()
    if not product:
        return web.json_response({"error": "Produto não encontrado"}, status=404)
    await db.delete(product)
    await db.commit()
    return web.json_response({"message": "Produto deletado com sucesso"}, status=200)
