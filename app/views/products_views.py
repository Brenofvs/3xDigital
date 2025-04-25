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
async def list_products(request: web.Request) -> web.Response:
    """
    Lista todos os produtos cadastrados com suporte a paginação e múltiplos filtros.

    Query params:
        category_id (int, opcional): Filtra produtos por categoria
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)
        name (str, opcional): Filtra produtos cujo nome contenha o texto informado
        description (str, opcional): Filtra produtos cuja descrição contenha o texto informado
        product_id (int, opcional): Filtra produto pelo ID exato
        price_min (float, opcional): Filtra produtos com preço maior ou igual ao valor
        price_max (float, opcional): Filtra produtos com preço menor ou igual ao valor
        price_between (str, opcional): Filtra produtos por faixa de preço no formato "min.xtomax.y"
        in_stock (bool, opcional): Se "true", filtra produtos com estoque disponível
        sort_by (str, opcional): Campo para ordenação (price, name, stock)
        sort_order (str, opcional): Direção da ordenação (asc ou desc)

    Returns:
        web.Response: Resposta JSON contendo a lista de produtos e metadados de paginação.
    """
    db = request.app[DB_SESSION_KEY]
    
    # Extrai parâmetros da query
    category_id = request.rel_url.query.get("category_id")
    page = int(request.rel_url.query.get("page", 1))
    page_size = int(request.rel_url.query.get("page_size", 20))
    name = request.rel_url.query.get("name")
    description = request.rel_url.query.get("description")
    
    # Processa ID do produto
    product_id = None
    if "product_id" in request.rel_url.query:
        try:
            product_id = int(request.rel_url.query["product_id"])
        except ValueError:
            return web.json_response({"error": "ID de produto inválido"}, status=400)
    
    # Processa filtros de preço
    price_min = None
    price_max = None
    
    # Verificar se há um filtro price_between no formato "min.xtomax.y"
    price_between = request.rel_url.query.get("price_between")
    if price_between:
        try:
            # Divide a string em valores mínimo e máximo
            if "to" in price_between:
                min_value, max_value = price_between.split("to")
                if min_value:
                    price_min = float(min_value)
                if max_value:
                    price_max = float(max_value)
        except (ValueError, TypeError):
            return web.json_response({"error": "Formato inválido para 'price_between'. Use 'min.xtomax.y'"}, status=400)
    else:
        # Processamento individual de price_min e price_max
        if "price_min" in request.rel_url.query:
            try:
                price_min = float(request.rel_url.query["price_min"])
            except (ValueError, TypeError):
                return web.json_response({"error": "Valor inválido para 'price_min'"}, status=400)
                
        if "price_max" in request.rel_url.query:
            try:
                price_max = float(request.rel_url.query["price_max"])
            except (ValueError, TypeError):
                return web.json_response({"error": "Valor inválido para 'price_max'"}, status=400)
    
    # Processa filtro de disponibilidade em estoque
    in_stock = None
    if "in_stock" in request.rel_url.query:
        in_stock_param = request.rel_url.query["in_stock"].lower()
        in_stock = in_stock_param in ('true', '1', 'yes', 'sim')
    
    # Processa parâmetros de ordenação
    sort_by = request.rel_url.query.get("sort_by")
    if sort_by and sort_by not in ["price", "name", "stock"]:
        return web.json_response({"error": "Campo de ordenação inválido. Use 'price', 'name' ou 'stock'"}, status=400)
        
    sort_order = request.rel_url.query.get("sort_order", "asc").lower()
    if sort_order not in ["asc", "desc"]:
        return web.json_response({"error": "Direção de ordenação inválida. Use 'asc' ou 'desc'"}, status=400)
    
    # Limita o tamanho da página para evitar sobrecarga
    page_size = min(page_size, 100)
    
    # Usar ProductService em vez de acessar o banco diretamente
    product_service = ProductService(db)
    
    if category_id:
        try:
            category_id = int(category_id)
        except ValueError:
            return web.json_response({"error": "ID de categoria inválido"}, status=400)
            
    result = await product_service.list_products(
        category_id=category_id, 
        page=page, 
        page_size=page_size,
        name=name,
        description=description,
        product_id=product_id,
        price_min=price_min,
        price_max=price_max,
        in_stock=in_stock,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return web.json_response(result["data"], status=200)

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
                "image_url": "URL ou caminho da imagem",  # Opcional
                "has_custom_commission": false,  # Opcional
                "commission_type": "percentage",  # Opcional, 'percentage' ou 'fixed'
                "commission_value": 10.0  # Opcional, percentual ou valor fixo
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
        has_custom_commission = False
        commission_type = None
        commission_value = None

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
            elif field.name == "has_custom_commission":
                value = await field.text()
                has_custom_commission = value.lower() in ('true', '1', 'yes', 'sim')
            elif field.name == "commission_type":
                commission_type = await field.text()
            elif field.name == "commission_value":
                try:
                    value = await field.text()
                    if value:
                        commission_value = float(value)
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'commission_value'"}, status=400)
                
        if not name or price is None or stock is None:
            return web.json_response({"error": "Campos obrigatórios ausentes"}, status=400)
            
        # Criar produto usando o service
        result = await product_service.create_product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_file=image_file,
            has_custom_commission=has_custom_commission,
            commission_type=commission_type,
            commission_value=commission_value
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
            has_custom_commission = data.get("has_custom_commission", False)
            commission_type = data.get("commission_type")
            commission_value = data.get("commission_value")
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
            image_url=image_url,
            has_custom_commission=has_custom_commission,
            commission_type=commission_type,
            commission_value=commission_value
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
            "image_url": "URL ou caminho da nova imagem",  # Opcional via JSON
            "has_custom_commission": true,  # Opcional
            "commission_type": "percentage",  # Opcional, 'percentage' ou 'fixed'
            "commission_value": 10.0  # Opcional, percentual ou valor fixo
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
            elif field.name == "has_custom_commission":
                value = await field.text()
                updated_fields["has_custom_commission"] = value.lower() in ('true', '1', 'yes', 'sim')
            elif field.name == "commission_type":
                updated_fields["commission_type"] = await field.text()
            elif field.name == "commission_value":
                try:
                    value = await field.text()
                    if value:
                        updated_fields["commission_value"] = float(value)
                except ValueError:
                    return web.json_response({"error": "Valor inválido para 'commission_value'"}, status=400)
                    
        # Processar imagem, se fornecida
        if image_file:
            try:
                image_path, image_url = await product_service.save_image(image_file)
                updated_fields["image_path"] = image_path
                updated_fields["image_url"] = image_url
            except Exception as e:
                return web.json_response({"error": f"Erro ao salvar imagem: {str(e)}"}, status=400)

    else:  # JSON
        try:
            data = await request.json()
            updated_fields = {}
            
            if "name" in data:
                updated_fields["name"] = data["name"]
            if "description" in data:
                updated_fields["description"] = data["description"]
            if "price" in data:
                updated_fields["price"] = float(data["price"])
            if "stock" in data:
                updated_fields["stock"] = int(data["stock"])
            if "category_id" in data:
                updated_fields["category_id"] = data["category_id"]
            if "image_url" in data:
                updated_fields["image_url"] = data["image_url"]
            if "has_custom_commission" in data:
                updated_fields["has_custom_commission"] = bool(data["has_custom_commission"])
            if "commission_type" in data:
                updated_fields["commission_type"] = data["commission_type"]
            if "commission_value" in data:
                updated_fields["commission_value"] = float(data["commission_value"])
                
        except (ValueError, TypeError):
            return web.json_response({"error": "Dados inválidos no payload JSON"}, status=400)

    # Executar a atualização
    result = await product_service.update_product(product_id, **updated_fields)
    
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
