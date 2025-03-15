# D:\3xDigital\app\services\category_service.py
"""
category_service.py

Este módulo contém a lógica de negócios para gerenciamento de categorias,
incluindo criação, atualização e consulta de categorias de produtos.

Classes:
    CategoryService: Provedor de serviços relacionados a categorias.
"""

from typing import List, Optional, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.database import Category, Product

class CategoryService:
    """
    Serviço para gerenciamento de categorias.

    Attributes:
        db_session (AsyncSession): Sessão do banco de dados.

    Methods:
        list_categories: Lista todas as categorias.
        get_category: Obtém detalhes de uma categoria específica.
        create_category: Cria uma nova categoria.
        update_category: Atualiza uma categoria existente.
        delete_category: Remove uma categoria.
        has_associated_products: Verifica se a categoria possui produtos associados.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o serviço com a sessão do banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do SQLAlchemy.
        """
        self.db_session = db_session

    async def list_categories(self) -> Dict[str, Union[List[Dict], str, bool]]:
        """
        Lista todas as categorias cadastradas.

        Returns:
            Dict[str, Union[List[Dict], str, bool]]: Lista de categorias.
                Estrutura: {"success": bool, "data": List[Dict], "error": str}
        """
        result = await self.db_session.execute(select(Category))
        categories = result.scalars().all()
        
        categories_list = [{"id": c.id, "name": c.name} for c in categories]
        
        return {"success": True, "data": categories_list, "error": None}

    async def get_category(self, category_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Obtém os detalhes de uma categoria específica.

        Args:
            category_id (int): ID da categoria.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Detalhes da categoria.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se a categoria não for encontrada.
        """
        result = await self.db_session.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        
        if not category:
            return {"success": False, "error": "Categoria não encontrada.", "data": None}
        
        category_data = {"id": category.id, "name": category.name}
        
        return {"success": True, "data": category_data, "error": None}

    async def create_category(self, name: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Cria uma nova categoria.

        Args:
            name (str): Nome da categoria.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o nome da categoria for inválido.
        """
        if not name or len(name.strip()) == 0:
            return {"success": False, "error": "Nome da categoria não pode ser vazio.", "data": None}
            
        # Verificar se já existe uma categoria com o mesmo nome
        result = await self.db_session.execute(
            select(Category).where(func.lower(Category.name) == name.lower())
        )
        if result.scalar_one_or_none():
            return {"success": False, "error": "já existe uma categoria com este nome.", "data": None}
        
        new_category = Category(name=name)
        self.db_session.add(new_category)
        await self.db_session.commit()
        await self.db_session.refresh(new_category)
        
        category_data = {"id": new_category.id, "name": new_category.name}
        
        return {"success": True, "data": category_data, "error": None}

    async def update_category(self, category_id: int, name: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza uma categoria existente.

        Args:
            category_id (int): ID da categoria.
            name (str): Novo nome da categoria.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se a categoria não for encontrada ou o nome for inválido.
        """
        if not name or len(name.strip()) == 0:
            return {"success": False, "error": "Nome da categoria não pode ser vazio.", "data": None}
            
        result = await self.db_session.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        
        if not category:
            return {"success": False, "error": "Categoria não encontrada.", "data": None}
            
        # Verificar se já existe outra categoria com o mesmo nome
        result = await self.db_session.execute(
            select(Category).where(and_(
                func.lower(Category.name) == name.lower(),
                Category.id != category_id
            ))
        )
        if result.scalar_one_or_none():
            return {"success": False, "error": "já existe outra categoria com este nome.", "data": None}
        
        category.name = name
        await self.db_session.commit()
        await self.db_session.refresh(category)
        
        updated_data = {"id": category.id, "name": category.name}
        
        return {"success": True, "data": updated_data, "error": None}

    async def delete_category(self, category_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Remove uma categoria existente.

        Args:
            category_id (int): ID da categoria.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se a categoria não for encontrada ou possuir produtos associados.
        """
        result = await self.db_session.execute(select(Category).where(Category.id == category_id))
        category = result.scalar()
        
        if not category:
            return {"success": False, "error": "Categoria não encontrada.", "data": None}
            
        # Verificar se existem produtos associados à categoria
        has_products = await self.has_associated_products(category_id)
        if has_products:
            return {
                "success": False, 
                "error": "Não é possível excluir a categoria porque existem produtos associados a ela.", 
                "data": None
            }
        
        await self.db_session.delete(category)
        await self.db_session.commit()
        
        return {
            "success": True, 
            "data": {"id": category_id, "name": category.name},
            "error": None
        }

    async def has_associated_products(self, category_id: int) -> bool:
        """
        Verifica se a categoria possui produtos associados.

        Args:
            category_id (int): ID da categoria.

        Returns:
            bool: True se a categoria possuir produtos associados, False caso contrário.
        """
        result = await self.db_session.execute(
            select(Product).where(Product.category_id == category_id).limit(1)
        )
        product = result.scalar()
        return product is not None 