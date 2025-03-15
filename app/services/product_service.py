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
from sqlalchemy import select
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

    async def list_products(self, category_id: Optional[int] = None) -> Dict[str, Union[List[Dict], str, bool]]:
        """
        Lista todos os produtos cadastrados.

        Args:
            category_id (Optional[int]): Filtra produtos por categoria, se fornecido.

        Returns:
            Dict[str, Union[List[Dict], str, bool]]: Lista de produtos.
                Estrutura: {"success": bool, "data": List[Dict], "error": str}
        """
        if category_id:
            result = await self.db_session.execute(
                select(Product).where(Product.category_id == category_id)
            )
        else:
            result = await self.db_session.execute(select(Product))
            
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
        
        return {"success": True, "data": products_list, "error": None}

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
        
        product_data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url
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
        image_file: Optional[Any] = None
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Cria um novo produto.

        Args:
            name (str): Nome do produto.
            description (str): Descrição do produto.
            price (float): Preço do produto.
            stock (int): Quantidade em estoque.
            category_id (Optional[int]): ID da categoria.
            image_url (Optional[str]): URL da imagem, se for fornecida via URL.
            image_file (Optional[Any]): Arquivo de imagem, se for upload.

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
            
        # Verificar se a categoria existe, se fornecida
        if category_id is not None:
            category_valid = await self.validate_category(category_id)
            if not category_valid:
                return {"success": False, "error": "Categoria não encontrada.", "data": None}
                
        # Processar upload de imagem, se fornecido
        processed_image_url = image_url
        if image_file:
            try:
                processed_image_url = await self.save_image(image_file)
            except Exception as e:
                return {"success": False, "error": f"Erro ao salvar imagem: {str(e)}", "data": None}
        
        # Criar o produto
        new_product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_url=processed_image_url
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
            "image_url": new_product.image_url
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
            product_id (int): ID do produto.
            **kwargs: Campos a serem atualizados (name, description, price, stock, category_id, image_url).
                Também aceita image_file para upload de nova imagem.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o produto não for encontrado ou os dados forem inválidos.
        """
        result = await self.db_session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado.", "data": None}
            
        # Validações
        if "price" in kwargs and kwargs["price"] < 0:
            return {"success": False, "error": "Preço não pode ser negativo.", "data": None}
            
        if "stock" in kwargs and kwargs["stock"] < 0:
            return {"success": False, "error": "Estoque não pode ser negativo.", "data": None}
            
        if "category_id" in kwargs and kwargs["category_id"] is not None:
            category_valid = await self.validate_category(kwargs["category_id"])
            if not category_valid:
                return {"success": False, "error": "Categoria não encontrada.", "data": None}
        
        # Processar upload de imagem, se fornecido
        if "image_file" in kwargs and kwargs["image_file"]:
            try:
                kwargs["image_url"] = await self.save_image(kwargs["image_file"])
                # Remover o image_file para não tentar atribuí-lo ao modelo
                del kwargs["image_file"]
            except Exception as e:
                return {"success": False, "error": f"Erro ao salvar imagem: {str(e)}", "data": None}
        
        # Atualizar atributos do produto
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        await self.db_session.commit()
        await self.db_session.refresh(product)
        
        product_data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url
        }
        
        return {"success": True, "data": product_data, "error": None}

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

    async def save_image(self, image_file) -> str:
        """
        Salva uma imagem de produto.

        Args:
            image_file: Objeto de arquivo de imagem.

        Returns:
            str: URL da imagem salva.

        Raises:
            Exception: Se houver erro ao salvar o arquivo.
        """
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Criar nome único para o arquivo
        timestamp = int(time.time())
        filename = getattr(image_file, "filename", f"image_{timestamp}.jpg")
        safe_filename = f"{timestamp}_{filename}"
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
        
        return f"/static/uploads/{safe_filename}"

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