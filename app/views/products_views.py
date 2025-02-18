# D:\#3xDigital\app\views\categories_views.py

"""
products_views.py

Este módulo define os endpoints para o gerenciamento de produtos, incluindo operações CRUD.

Endpoints:
    GET /products: Lista todos os produtos – acesso para usuários autenticados (admin, user ou affiliate).
    GET /products/{product_id}: Obtém os detalhes de um produto – acesso para usuários autenticados.
    POST /products: Cria um novo produto – somente admin.
    PUT /products/{product_id}: Atualiza um produto existente – somente admin.
    DELETE /products/{product_id}: Deleta um produto – somente admin.
"""

import os
import time
import aiofiles

from aiohttp import web
from sqlalchemy import select
from app.models.database import Product, Category
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role

routes = web.RouteTableDef()

@routes.get("/products")
@require_role(["admin", "user", "affiliate"])
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
        "category_id": p.category_id,
        "image_url": p.image_url
    } for p in products]
    return web.json_response({"products": products_list}, status=200)

@routes.get("/products/{product_id}")
@require_role(["admin", "user", "affiliate"])
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
        "category_id": product.category_id,
        "image_url": product.image_url
    }
    return web.json_response({"product": product_data}, status=200)

@routes.post("/products")
@require_role(["admin"])
async def create_product(request: web.Request) -> web.Response:
    """
    Cria um novo produto.

    JSON ou multipart/form-data de entrada:
        Caso JSON:
            {
                "name": "Nome do produto",
                "description": "Descrição do produto",
                "price": 100.0,
                "stock": 10,
                "category_id": 1,
                "image_url": "URL ou caminho da imagem"  # Opcional
            }
        Caso multipart/form-data:
            Campos enviados individualmente e o arquivo de imagem no campo "image".

    Args:
        request (web.Request): Requisição contendo os dados do produto.

    Returns:
        web.Response: Resposta JSON com a mensagem de sucesso e os dados do produto criado.
    """
    db = request.app[DB_SESSION_KEY]
    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        name = None
        description = ""
        price = None
        stock = None
        category_id = None
        image_url = None

        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == "name":
                name = await field.text()
            elif field.name == "description":
                description = await field.text()
            elif field.name == "price":
                try:
                    price = float(await field.text())
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'price'"}, status=400)
            elif field.name == "stock":
                try:
                    stock = int(await field.text())
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'stock'"}, status=400)
            elif field.name == "category_id":
                category_text = await field.text()
                if category_text:
                    try:
                        category_id = int(category_text)
                    except ValueError:
                        return web.json_response({"error": "Valor inválido para 'category_id'"}, status=400)
            elif field.name == "image":
                filename = field.filename
                if filename:
                    upload_dir = os.path.join("static", "uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    timestamp = int(time.time())
                    safe_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(upload_dir, safe_filename)
                    async with aiofiles.open(file_path, 'wb') as f:
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            await f.write(chunk)
                    image_url = f"/static/uploads/{safe_filename}"
        if not name or price is None or stock is None:
            return web.json_response({"error": "Campos obrigatórios ausentes"}, status=400)
    else:
        try:
            data = await request.json()
            name = data["name"]
            description = data.get("description", "")
            price = float(data["price"])
            stock = int(data["stock"])
            category_id = data.get("category_id")
            image_url = data.get("image_url")
        except KeyError as e:
            return web.json_response({"error": f"Campo ausente: {str(e)}"}, status=400)
        except (ValueError, TypeError):
            return web.json_response({"error": "Dados inválidos para 'price' ou 'stock'"}, status=400)

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
        category_id=category_id,
        image_url=image_url
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
        "category_id": new_product.category_id,
        "image_url": new_product.image_url
    }
    return web.json_response({"message": "Produto criado com sucesso", "product": product_data}, status=201)

@routes.put("/products/{product_id}")
@require_role(["admin"])
async def update_product(request: web.Request) -> web.Response:
    """
    Atualiza os dados de um produto existente.

    JSON ou multipart/form-data de entrada pode conter:
        {
            "name": "Novo nome",
            "description": "Nova descrição",
            "price": 150.0,
            "stock": 20,
            "category_id": 2,
            "image_url": "URL ou caminho da nova imagem"  # Opcional via JSON
        }
        Ou via multipart/form-data com o arquivo no campo "image".

    Args:
        request (web.Request): Requisição contendo o ID do produto e os dados a atualizar.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso e os dados atualizados do produto,
                      ou mensagem de erro se o produto ou categoria não for encontrado.
    """
    product_id = request.match_info.get("product_id")
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar()
    if not product:
        return web.json_response({"error": "Produto não encontrado"}, status=404)

    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        updated_fields = {}
        new_image_url = None

        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == "name":
                updated_fields["name"] = await field.text()
            elif field.name == "description":
                updated_fields["description"] = await field.text()
            elif field.name == "price":
                try:
                    updated_fields["price"] = float(await field.text())
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'price'"}, status=400)
            elif field.name == "stock":
                try:
                    updated_fields["stock"] = int(await field.text())
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'stock'"}, status=400)
            elif field.name == "category_id":
                try:
                    updated_fields["category_id"] = int(await field.text())
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'category_id'"}, status=400)
            elif field.name == "image":
                filename = field.filename
                if filename:
                    upload_dir = os.path.join("static", "uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    timestamp = int(time.time())
                    safe_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(upload_dir, safe_filename)
                    async with aiofiles.open(file_path, 'wb') as f:
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            await f.write(chunk)
                    new_image_url = f"/static/uploads/{safe_filename}"
        if "category_id" in updated_fields:
            result = await db.execute(select(Category).where(Category.id == updated_fields["category_id"]))
            category = result.scalar()
            if not category:
                return web.json_response({"error": "Categoria não encontrada"}, status=404)
        for key, value in updated_fields.items():
            setattr(product, key, value)
        if new_image_url is not None:
            product.image_url = new_image_url
    else:
        data = await request.json()
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
        if "image_url" in data:
            product.image_url = data["image_url"]

    await db.commit()
    await db.refresh(product)
    updated_data = {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "category_id": product.category_id,
        "image_url": product.image_url
    }
    return web.json_response({"message": "Produto atualizado com sucesso", "product": updated_data}, status=200)

@routes.delete("/products/{product_id}")
@require_role(["admin"])
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
