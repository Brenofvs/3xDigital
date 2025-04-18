# D:\3xDigital\app\services\product_service.py
"""
product_service.py

Este módulo contém a lógica de negócios para gerenciamento de produtos,
incluindo criação, atualização, consulta e gerenciamento de estoque.

Classes:
    ProductService: Provedor de serviços relacionados a produtos.
"""

import os
import time
import aiofiles
from typing import List, Optional, Dict, Union, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import Product, Category

class ProductService:
    """
    Serviço para gerenciamento de produtos.

    Attributes:
        db_session (AsyncSession): Sessão do banco de dados.

    Methods:
        list_products: Lista todos os produtos.
        get_product: Obtém detalhes de um produto específico.
        create_product: Cria um novo produto.
        update_product: Atualiza um produto existente.
        delete_product: Remove um produto.
        update_stock: Atualiza o estoque de um produto.
        save_image: Salva uma imagem de produto.
        validate_category: Valida a existência de uma categoria.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o serviço com a sessão do banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do SQLAlchemy.
        """
        self.db_session = db_session

    async def list_products(
        self, 
        category_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        description: Optional[str] = None,
        product_id: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        in_stock: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc"
    ) -> Dict[str, Union[dict, str, bool]]:
        """
        Lista produtos cadastrados com suporte a paginação e múltiplos filtros.

        Args:
            category_id (Optional[int]): Filtra produtos por categoria.
            page (int): Número da página (padrão: 1)
            page_size (int): Tamanho da página (padrão: 20)
            name (Optional[str]): Filtra produtos cujo nome contenha o texto informado.
            description (Optional[str]): Filtra produtos cuja descrição contenha o texto informado.
            product_id (Optional[int]): Filtra produto pelo ID exato.
            price_min (Optional[float]): Filtra produtos com preço maior ou igual ao valor.
            price_max (Optional[float]): Filtra produtos com preço menor ou igual ao valor.
            in_stock (Optional[bool]): Se True, filtra produtos com estoque disponível.
            sort_by (Optional[str]): Campo para ordenação (price, name, stock).
            sort_order (Optional[str]): Direção da ordenação (asc ou desc).

        Returns:
            Dict[str, Union[dict, str, bool]]: Lista de produtos e metadados.
                Estrutura: {"success": bool, "data": dict, "error": str}
        """
        # Construção da query base
        base_query = select(Product)
        
        # Aplicar filtros
        if product_id is not None:
            base_query = base_query.where(Product.id == product_id)
            
        if category_id:
            base_query = base_query.where(Product.category_id == category_id)
            
        if name:
            # Busca case-insensitive usando LIKE
            base_query = base_query.where(Product.name.ilike(f"%{name}%"))
            
        if description:
            # Busca case-insensitive na descrição
            base_query = base_query.where(Product.description.ilike(f"%{description}%"))
            
        if price_min is not None:
            base_query = base_query.where(Product.price >= price_min)
            
        if price_max is not None:
            base_query = base_query.where(Product.price <= price_max)
            
        if in_stock:
            base_query = base_query.where(Product.stock > 0)
            
        # Aplicar ordenação
        if sort_by:
            # Determinar a coluna para ordenação
            if sort_by == "price":
                order_column = Product.price
            elif sort_by == "name":
                order_column = Product.name
            elif sort_by == "stock":
                order_column = Product.stock
            else:
                # Se o sort_by não for válido, usa ordenação padrão
                order_column = Product.id
                
            # Aplicar direção da ordenação
            if sort_order and sort_order.lower() == "desc":
                base_query = base_query.order_by(order_column.desc())
            else:
                base_query = base_query.order_by(order_column.asc())
        else:
            # Ordenação padrão por ID
            base_query = base_query.order_by(Product.id)
        
        # Consulta para contar o total de produtos após aplicar os filtros
        count_query = select(func.count()).select_from(base_query.subquery())
        result = await self.db_session.execute(count_query)
        total_count = result.scalar_one()
        
        # Aplicar paginação
        query = base_query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db_session.execute(query)
        products = result.scalars().all()
        
        products_list = []
        for p in products:
            # Determinar a URL da imagem a partir do caminho
            image_url = None
            if p.image_path:
                image_url = self.get_image_url(p.image_path)
            elif p.image_url:
                image_url = p.image_url
                
            products_list.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock,
                "category_id": p.category_id,
                "image_url": image_url,
                "has_custom_commission": p.has_custom_commission,
                "commission_type": p.commission_type,
                "commission_value": p.commission_value
            })
        
        # Retornar produtos e metadados de paginação
        return {
            "success": True, 
            "data": {
                "products": products_list,
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "filters_applied": {
                        "category_id": category_id,
                        "name": name,
                        "description": description,
                        "product_id": product_id,
                        "price_min": price_min,
                        "price_max": price_max,
                        "in_stock": in_stock,
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                }
            }, 
            "error": None
        }

    async def get_product(self, product_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Obtém os detalhes de um produto específico.

        Args:
            product_id (int): ID do produto.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Detalhes do produto.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o produto não for encontrado.
        """
        result = await self.db_session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado.", "data": None}
        
        # Determinar a URL da imagem a partir do caminho
        image_url = None
        if product.image_path:
            image_url = self.get_image_url(product.image_path)
        elif product.image_url:
            image_url = product.image_url
        
        product_data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": image_url,
            "has_custom_commission": product.has_custom_commission,
            "commission_type": product.commission_type,
            "commission_value": product.commission_value
        }
        
        return {"success": True, "data": product_data, "error": None}

    async def create_product(
        self,
        name: str,
        description: str,
        price: float,
        stock: int,
        category_id: Optional[int] = None,
        image_url: Optional[str] = None,
        image_file: Optional[Any] = None,
        has_custom_commission: bool = False,
        commission_type: Optional[str] = None,
        commission_value: Optional[float] = None
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Cria um novo produto.

        Args:
            name (str): Nome do produto.
            description (str): Descrição do produto.
            price (float): Preço do produto.
            stock (int): Quantidade em estoque.
            category_id (Optional[int]): ID da categoria.
            image_url (Optional[str]): URL externa da imagem, se fornecida via URL.
            image_file (Optional[Any]): Arquivo de imagem, se for upload.
            has_custom_commission (bool): Indica se o produto tem comissão personalizada.
            commission_type (Optional[str]): Tipo de comissão ('percentage' ou 'fixed').
            commission_value (Optional[float]): Valor da comissão (percentual ou fixo).

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se os dados forem inválidos ou a categoria não existir.
        """
        # Validações básicas
        if not name or len(name.strip()) == 0:
            return {"success": False, "error": "Nome do produto não pode ser vazio.", "data": None}
            
        if price < 0:
            return {"success": False, "error": "Preço não pode ser negativo.", "data": None}
            
        if stock < 0:
            return {"success": False, "error": "Estoque não pode ser negativo.", "data": None}
        
        # Validar comissão personalizada
        if not has_custom_commission:
            # Se não tem comissão personalizada, definir campos como None
            commission_type = None
            commission_value = None
        elif has_custom_commission:
            if not commission_type or commission_type not in ['percentage', 'fixed']:
                return {"success": False, "error": "Tipo de comissão deve ser 'percentage' ou 'fixed'.", "data": None}
            
            if commission_value is None or commission_value < 0:
                return {"success": False, "error": "Valor da comissão não pode ser negativo.", "data": None}
            
            if commission_type == 'percentage' and commission_value > 100:
                return {"success": False, "error": "Percentual de comissão não pode ser maior que 100%.", "data": None}
            
        # Verificar se a categoria existe, se fornecida
        if category_id is not None:
            category_exists = await self.validate_category(category_id)
            if not category_exists:
                return {"success": False, "error": "Categoria não encontrada.", "data": None}
        
        # Processar imagem, se fornecida
        final_image_url = None
        image_path = None
        
        if image_file:
            try:
                image_path, final_image_url = await self.save_image(image_file)
            except Exception as e:
                return {"success": False, "error": f"Erro ao salvar imagem: {str(e)}", "data": None}
        elif image_url:
            # Se foi fornecida apenas a URL externa da imagem
            final_image_url = image_url
        
        # Criar o produto no banco de dados
        new_product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_url=final_image_url,  # Para compatibilidade
            image_path=image_path,
            has_custom_commission=has_custom_commission,
            commission_type=commission_type,
            commission_value=commission_value
        )
        
        self.db_session.add(new_product)
        await self.db_session.commit()
        await self.db_session.refresh(new_product)
        
        product_data = {
            "id": new_product.id,
            "name": new_product.name,
            "description": new_product.description,
            "price": new_product.price,
            "stock": new_product.stock,
            "category_id": new_product.category_id,
            "image_url": final_image_url,
            "has_custom_commission": new_product.has_custom_commission,
            "commission_type": new_product.commission_type,
            "commission_value": new_product.commission_value
        }
        
        return {"success": True, "data": product_data, "error": None}

    async def update_product(
        self, 
        product_id: int, 
        **kwargs
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza um produto existente.

        Args:
            product_id (int): ID do produto a ser atualizado.
            **kwargs: Campos a serem atualizados, que podem incluir:
                - name (str): Novo nome do produto.
                - description (str): Nova descrição.
                - price (float): Novo preço.
                - stock (int): Nova quantidade em estoque.
                - category_id (int): Nova categoria.
                - image_url (str): Nova URL externa da imagem.
                - image_file: Novo arquivo de imagem para upload.
                - has_custom_commission (bool): Novo status de comissão personalizada.
                - commission_type (str): Novo tipo de comissão.
                - commission_value (float): Novo valor de comissão.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o produto não for encontrado ou os dados forem inválidos.
        """
        # Buscar o produto
        result = await self.db_session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado.", "data": None}
        
        # Validar dados básicos
        if 'price' in kwargs and kwargs['price'] < 0:
            return {"success": False, "error": "Preço não pode ser negativo.", "data": None}
            
        if 'stock' in kwargs and kwargs['stock'] < 0:
            return {"success": False, "error": "Estoque não pode ser negativo.", "data": None}
            
        # Verificar categoria se for fornecida
        if 'category_id' in kwargs and kwargs['category_id'] is not None:
            category_exists = await self.validate_category(kwargs['category_id'])
            if not category_exists:
                return {"success": False, "error": "Categoria não encontrada.", "data": None}
        
        # Processar imagem, se fornecida
        if 'image_file' in kwargs and kwargs['image_file']:
            try:
                image_path, image_url = await self.save_image(kwargs['image_file'])
                kwargs['image_path'] = image_path
                kwargs['image_url'] = image_url
                # Remover image_file para não tentar atribuir ao modelo
                del kwargs['image_file']
            except Exception as e:
                return {"success": False, "error": f"Erro ao salvar imagem: {str(e)}", "data": None}
        
        # Verificar se has_custom_commission foi fornecido e é False
        if 'has_custom_commission' in kwargs and kwargs['has_custom_commission'] is False:
            # Se desativou a comissão personalizada, limpar os outros campos relacionados
            kwargs['commission_type'] = None
            kwargs['commission_value'] = None
        # Validar comissão personalizada, se aplicável
        elif 'has_custom_commission' in kwargs and kwargs['has_custom_commission']:
            if 'commission_type' in kwargs:
                if kwargs['commission_type'] not in ['percentage', 'fixed']:
                    return {"success": False, "error": "Tipo de comissão deve ser 'percentage' ou 'fixed'.", "data": None}
            elif not product.commission_type:
                return {"success": False, "error": "Tipo de comissão obrigatório para comissão personalizada.", "data": None}
                
            if 'commission_value' in kwargs:
                if kwargs['commission_value'] is None or kwargs['commission_value'] < 0:
                    return {"success": False, "error": "Valor da comissão não pode ser negativo.", "data": None}
                
                if ('commission_type' in kwargs and kwargs['commission_type'] == 'percentage' or 
                        product.commission_type == 'percentage') and kwargs['commission_value'] > 100:
                    return {"success": False, "error": "Percentual de comissão não pode ser maior que 100%.", "data": None}
            elif not product.commission_value:
                return {"success": False, "error": "Valor da comissão obrigatório para comissão personalizada.", "data": None}
        
        # Atualizar os campos
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        await self.db_session.commit()
        
        # Obter a URL da imagem correta para o retorno
        image_url = None
        if product.image_path:
            image_url = self.get_image_url(product.image_path)
        elif product.image_url:
            image_url = product.image_url
        
        # Retornar os dados atualizados
        updated_data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": image_url,
            "has_custom_commission": product.has_custom_commission,
            "commission_type": product.commission_type,
            "commission_value": product.commission_value
        }
        
        return {"success": True, "data": updated_data, "error": None}

    async def delete_product(self, product_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Remove um produto existente.

        Args:
            product_id (int): ID do produto.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o produto não for encontrado.
        """
        result = await self.db_session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado.", "data": None}
        
        # Verificar se o produto está em algum pedido (poderia ser adicionado)
        # Mas não está na atual implementação
        
        product_data = {
            "id": product.id,
            "name": product.name
        }
        
        await self.db_session.delete(product)
        await self.db_session.commit()
        
        return {"success": True, "data": product_data, "error": None}

    async def update_stock(self, product_id: int, quantity: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza o estoque de um produto.

        Args:
            product_id (int): ID do produto.
            quantity (int): Nova quantidade em estoque.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o produto não for encontrado ou a quantidade for inválida.
        """
        if quantity < 0:
            return {"success": False, "error": "Estoque não pode ser negativo.", "data": None}
            
        result = await self.db_session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado.", "data": None}
            
        product.stock = quantity
        await self.db_session.commit()
        await self.db_session.refresh(product)
        
        return {
            "success": True, 
            "data": {
                "id": product.id,
                "name": product.name,
                "stock": product.stock
            },
            "error": None
        }

    async def save_image(self, image_file) -> tuple[str, str]:
        """
        Salva uma imagem de produto e retorna tanto o caminho relativo quanto a URL da imagem.

        Args:
            image_file: Objeto de arquivo de imagem.

        Returns:
            tuple[str, str]: Tupla contendo o caminho relativo da imagem e a URL completa.

        Raises:
            Exception: Se houver erro ao salvar o arquivo.
        """
        # Criar diretório de uploads se não existir
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Criar nome único para o arquivo
        timestamp = int(time.time())
        filename = getattr(image_file, "filename", f"image_{timestamp}.jpg")
        # Remover caracteres especiais e espaços do nome do arquivo
        import re
        safe_name = re.sub(r'[^\w\.-]', '_', filename)
        safe_filename = f"{timestamp}_{safe_name}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Salvar o arquivo
        async with aiofiles.open(file_path, 'wb') as f:
            if hasattr(image_file, "read_chunk"):
                # Se for um objeto de arquivo do aiohttp
                while True:
                    chunk = await image_file.read_chunk()
                    if not chunk:
                        break
                    await f.write(chunk)
            elif hasattr(image_file, "read"):
                # Se for um objeto de arquivo comum
                content = image_file.read()
                await f.write(content)
            else:
                # Se for conteúdo binário direto
                await f.write(image_file)
        
        # Caminho relativo para armazenar no banco de dados (usando sempre barras normais)
        rel_path = "uploads/" + safe_filename
        # URL completa para retornar ao cliente
        url_path = f"/static/uploads/{safe_filename}"
        
        return rel_path, url_path

    def get_image_url(self, image_path: str) -> str:
        """
        Converte um caminho relativo de imagem em URL completa.

        Args:
            image_path (str): Caminho relativo da imagem.

        Returns:
            str: URL completa da imagem.
        """
        if not image_path:
            return None
            
        # Normalizar o caminho para usar barras normais
        normalized_path = image_path.replace('\\', '/')
            
        # Se já for uma URL completa, retorna como está
        if normalized_path.startswith(('http://', 'https://')):
            return normalized_path
            
        # Se começar com '/static/', é um caminho já formatado como URL
        if normalized_path.startswith('/static/'):
            return normalized_path
            
        # Caso contrário, é um caminho relativo que precisa ser convertido
        if normalized_path.startswith('uploads/'):
            return f"/static/{normalized_path}"
            
        return f"/static/uploads/{os.path.basename(normalized_path)}"

    async def validate_category(self, category_id: int) -> bool:
        """
        Valida a existência de uma categoria.

        Args:
            category_id (int): ID da categoria.

        Returns:
            bool: True se a categoria existir, False caso contrário.
        """
        result = await self.db_session.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        return category is not None 