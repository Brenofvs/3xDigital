# D:\3xDigital\app\views\products_views.py

"""
products_views.py

Este módulo define os endpoints para o gerenciamento de produtos, incluindo operações CRUD.

Endpoints:
    GET /products: Lista todos os produtos – acesso para usuários autenticados (admin, user ou affiliate).
    GET /products/{product_id}: Obtém os detalhes de um produto – acesso para usuários autenticados.
    POST /products: Cria um novo produto – somente admin.
    PUT /products/{product_id}: Atualiza um produto existente – somente admin.
    DELETE /products/{product_id}: Deleta um produto – somente admin.
    
Dependências:
    - AIOHTTP para manipulação de requisições.
    - ProductService para lógica de negócios de produtos.
    - Middleware de autenticação para proteção dos endpoints.
"""

import os
from aiohttp import web
from app.models.database import Product, Category
from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.services.product_service import ProductService

routes = web.RouteTableDef()

@routes.get("/products")
@require_role(["admin", "user", "affiliate"])
async def list_products(request: web.Request) -> web.Response:
    """
    Lista todos os produtos cadastrados com suporte a paginação.

    Query params:
        category_id (int, opcional): Filtra produtos por categoria
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)

    Returns:
        web.Response: Resposta JSON contendo a lista de produtos e metadados de paginação.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Extrai parâmetros da query
    category_id = request.rel_url.query.get("category_id")
    page = int(request.rel_url.query.get("page", 1))
    page_size = int(request.rel_url.query.get("page_size", 20))
    
    # Limita o tamanho da página para evitar sobrecarga
    page_size = min(page_size, 100)
    
    # Usar ProductService em vez de acessar o banco diretamente
    product_service = ProductService(db)
    
    if category_id:
        try:
            category_id = int(category_id)
        except ValueError:
            return web.json_response({"error": "ID de categoria inválido"}, status=400)
            
    result = await product_service.list_products(category_id, page, page_size)
    
    return web.json_response(result["data"], status=200)

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
    
    # Usar ProductService em vez de acessar o banco diretamente
    product_service = ProductService(db)
    result = await product_service.get_product(product_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response({"product": result["data"]}, status=200)

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
    product_service = ProductService(db)
    
    if request.content_type.startswith("multipart/"):
        # Processamento de formulário multipart
        reader = await request.multipart()
        name = None
        description = ""
        price = None
        stock = None
        category_id = None
        image_file = None

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
                if field.filename:
                    image_file = field  # Guarda a referência ao campo para processar depois
                
        if not name or price is None or stock is None:
            return web.json_response({"error": "Campos obrigatórios ausentes"}, status=400)
            
        # Criar produto usando o service
        result = await product_service.create_product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_file=image_file
        )
    else:
        # Processamento JSON
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

        # Criar produto usando o service
        result = await product_service.create_product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_url=image_url
        )
    
    # Processar resultado da operação    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, 
                              status=404 if "não encontrada" in result["error"] else 400)
    
    return web.json_response(
        {"message": "Produto criado com sucesso", "product": result["data"]}, 
        status=201
    )

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
    product_service = ProductService(db)
    
    # Verificar primeiro se o produto existe
    product_result = await product_service.get_product(product_id)
    if not product_result["success"]:
        return web.json_response({"error": product_result["error"]}, status=404)
    
    # Processar formulário multipart ou JSON
    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        updated_fields = {}
        image_file = None

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
                category_text = await field.text()
                if category_text:
                    try:
                        updated_fields["category_id"] = int(category_text)
                    except ValueError:
                        return web.json_response({"error": "Valor inválido para 'category_id'"}, status=400)
            elif field.name == "image":
                if field.filename:
                    image_file = field
                    updated_fields["image_file"] = field

        # Atualizar usando o service
        if image_file:
            updated_fields["image_file"] = image_file
        result = await product_service.update_product(product_id, **updated_fields)
    else:
        # Processamento JSON
        try:
            data = await request.json()
            result = await product_service.update_product(product_id, **data)
        except ValueError:
            return web.json_response({"error": "Dados inválidos no JSON"}, status=400)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, 
                              status=404 if "não encontrado" in result["error"] else 400)
    
    return web.json_response(
        {"message": "Produto atualizado com sucesso", "product": result["data"]}, 
        status=200
    )

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
    
    # Usar ProductService em vez de acessar o banco diretamente
    product_service = ProductService(db)
    result = await product_service.delete_product(product_id)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response({"message": "Produto deletado com sucesso"}, status=200)

@routes.put("/products/{product_id}/stock")
@require_role(["admin"])
async def update_product_stock(request: web.Request) -> web.Response:
    """
    Atualiza o estoque de um produto.
    
    JSON de entrada:
        {
            "stock": 50
        }
        
    Returns:
        web.Response: Resposta JSON com mensagem de sucesso e os dados atualizados do produto.
    """
    product_id = request.match_info.get("product_id")
    db = request.app[DB_SESSION_KEY]
    
    try:
        data = await request.json()
        new_stock = int(data.get("stock", 0))
    except (ValueError, TypeError):
        return web.json_response({"error": "Valor de estoque inválido"}, status=400)
    
    # Usar ProductService em vez de acessar o banco diretamente
    product_service = ProductService(db)
    result = await product_service.update_stock(product_id, new_stock)
    
    if not result["success"]:
        return web.json_response({"error": result["error"]}, status=404)
    
    return web.json_response(
        {"message": "Estoque atualizado com sucesso", "product": result["data"]}, 
        status=200
    )
