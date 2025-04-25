# D:\3xDigital\app\services\cart_service.py
"""
cart_service.py

Este módulo contém a lógica de negócios para gerenciamento de carrinhos de compras,
incluindo carrinhos temporários para usuários não autenticados e sincronização
com usuários autenticados.

Classes:
    CartService: Provedor de serviços relacionados a carrinhos de compras.
"""

from typing import List, Optional, Dict, Union, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.database import TempCart, TempCartItem, Product, Order, OrderItem

class CartService:
    """
    Serviço para gerenciamento de carrinhos de compras.

    Attributes:
        db_session (AsyncSession): Sessão do banco de dados.

    Methods:
        get_temp_cart: Obtém ou cria um carrinho temporário para um ID de sessão.
        add_to_cart: Adiciona um produto ao carrinho.
        remove_from_cart: Remove um produto do carrinho.
        update_cart_item: Atualiza a quantidade de um item no carrinho.
        get_cart_items: Obtém todos os itens de um carrinho.
        clear_cart: Limpa todos os itens de um carrinho.
        convert_to_order: Converte o carrinho em um pedido para um usuário autenticado.
        merge_with_user: Sincroniza o carrinho temporário com o usuário após autenticação.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o serviço com a sessão do banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do SQLAlchemy.
        """
        self.db_session = db_session

    async def get_temp_cart(self, session_id: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Obtém ou cria um carrinho temporário para um ID de sessão.

        Args:
            session_id (str): ID da sessão do usuário não autenticado.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Busca carrinho existente
        result = await self.db_session.execute(
            select(TempCart).where(TempCart.session_id == session_id)
        )
        cart = result.scalar()

        # Se não existir, cria um novo
        if not cart:
            cart = TempCart(session_id=session_id)
            self.db_session.add(cart)
            await self.db_session.commit()
            await self.db_session.refresh(cart)

        return {"success": True, "data": cart, "error": None}

    async def add_to_cart(
        self, session_id: str, product_id: int, quantity: int
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Adiciona um produto ao carrinho.

        Args:
            session_id (str): ID da sessão do usuário.
            product_id (int): ID do produto a ser adicionado.
            quantity (int): Quantidade do produto.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Verificar se o produto existe e tem estoque suficiente
        result = await self.db_session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar()

        if not product:
            return {"success": False, "error": f"Produto ID {product_id} não encontrado.", "data": None}
            
        if product.stock < quantity:
            return {"success": False, "error": f"Estoque insuficiente para o produto ID {product_id}.", "data": None}

        # Obter ou criar carrinho temporário
        cart_result = await self.get_temp_cart(session_id)
        cart = cart_result["data"]

        # Verificar se o produto já está no carrinho
        result = await self.db_session.execute(
            select(TempCartItem).where(
                TempCartItem.cart_id == cart.id,
                TempCartItem.product_id == product_id
            )
        )
        cart_item = result.scalar()

        # Se já existe, atualiza a quantidade
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            
            # Verifica se a nova quantidade excede o estoque
            if new_quantity > product.stock:
                return {"success": False, "error": f"Estoque insuficiente para o produto ID {product_id}.", "data": None}
                
            cart_item.quantity = new_quantity
        else:
            # Senão, cria um novo item
            cart_item = TempCartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity
            )
            self.db_session.add(cart_item)

        await self.db_session.commit()
        
        return await self.get_cart_items(session_id)

    async def remove_from_cart(
        self, session_id: str, product_id: int
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Remove um produto do carrinho.

        Args:
            session_id (str): ID da sessão do usuário.
            product_id (int): ID do produto a ser removido.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Obter carrinho temporário
        cart_result = await self.get_temp_cart(session_id)
        cart = cart_result["data"]

        # Remover o item do carrinho
        await self.db_session.execute(
            delete(TempCartItem).where(
                TempCartItem.cart_id == cart.id,
                TempCartItem.product_id == product_id
            )
        )
        
        await self.db_session.commit()
        
        return await self.get_cart_items(session_id)

    async def update_cart_item(
        self, session_id: str, product_id: int, quantity: int
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza a quantidade de um item no carrinho.

        Args:
            session_id (str): ID da sessão do usuário.
            product_id (int): ID do produto a ser atualizado.
            quantity (int): Nova quantidade do produto.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Verificar se o produto existe e tem estoque suficiente
        result = await self.db_session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar()

        if not product:
            return {"success": False, "error": f"Produto ID {product_id} não encontrado.", "data": None}
            
        if quantity <= 0:
            # Se a quantidade for zero ou negativa, remove o item
            return await self.remove_from_cart(session_id, product_id)
            
        if product.stock < quantity:
            return {"success": False, "error": f"Estoque insuficiente para o produto ID {product_id}.", "data": None}

        # Obter carrinho temporário
        cart_result = await self.get_temp_cart(session_id)
        cart = cart_result["data"]

        # Verificar se o produto está no carrinho
        result = await self.db_session.execute(
            select(TempCartItem).where(
                TempCartItem.cart_id == cart.id,
                TempCartItem.product_id == product_id
            )
        )
        cart_item = result.scalar()

        if not cart_item:
            # Se não existe, cria um novo item
            cart_item = TempCartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity
            )
            self.db_session.add(cart_item)
        else:
            # Senão, atualiza a quantidade
            cart_item.quantity = quantity

        await self.db_session.commit()
        
        return await self.get_cart_items(session_id)

    async def get_cart_items(self, session_id: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Obtém todos os itens de um carrinho com detalhes dos produtos.

        Args:
            session_id (str): ID da sessão do usuário.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Obter carrinho temporário
        cart_result = await self.get_temp_cart(session_id)
        cart = cart_result["data"]

        # Buscar todos os itens do carrinho
        result = await self.db_session.execute(
            select(TempCartItem).where(TempCartItem.cart_id == cart.id)
        )
        cart_items = result.scalars().all()

        # Carregar detalhes dos produtos
        items_with_details = []
        total = 0

        for item in cart_items:
            # Buscar detalhes do produto
            result = await self.db_session.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar()
            
            # Calcular subtotal
            subtotal = product.price * item.quantity
            total += subtotal
            
            # Adicionar item com detalhes
            items_with_details.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": product.price,
                "subtotal": subtotal,
                "name": product.name,
                "image_url": product.image_url,
                "image_path": product.image_path
            })

        cart_data = {
            "items": items_with_details,
            "total": total,
            "item_count": len(items_with_details)
        }

        return {"success": True, "data": cart_data, "error": None}

    async def clear_cart(self, session_id: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Limpa todos os itens de um carrinho.

        Args:
            session_id (str): ID da sessão do usuário.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Obter carrinho temporário
        cart_result = await self.get_temp_cart(session_id)
        cart = cart_result["data"]

        # Remover todos os itens do carrinho
        await self.db_session.execute(
            delete(TempCartItem).where(TempCartItem.cart_id == cart.id)
        )
        
        await self.db_session.commit()
        
        return {"success": True, "data": {"items": [], "total": 0, "item_count": 0}, "error": None}

    async def convert_to_order(
        self, session_id: str, user_id: int, ref_code: Optional[str] = None
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Converte o carrinho em um pedido para um usuário autenticado.

        Args:
            session_id (str): ID da sessão do usuário.
            user_id (int): ID do usuário autenticado.
            ref_code (Optional[str]): Código de referência do afiliado.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Obter itens do carrinho
        cart_items_result = await self.get_cart_items(session_id)
        
        if not cart_items_result["success"]:
            return cart_items_result
            
        cart_data = cart_items_result["data"]
        
        if not cart_data["items"]:
            return {"success": False, "error": "O carrinho está vazio.", "data": None}

        # Preparar dados do pedido
        items_for_order = []
        for item in cart_data["items"]:
            items_for_order.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"]
            })

        # Usar serviço de ordem para criar o pedido
        from app.services.order_service import OrderService
        order_service = OrderService(self.db_session)
        
        # Criar pedido
        result = await order_service.create_order(user_id, items_for_order, ref_code)
        
        if result["success"]:
            # Limpar o carrinho após criar o pedido com sucesso
            await self.clear_cart(session_id)
            
        return result

    async def merge_with_user(
        self, session_id: str, user_id: int
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Sincroniza o carrinho temporário com o usuário após autenticação.
        Esta função é útil quando um usuário faz login após adicionar itens ao carrinho.

        Args:
            session_id (str): ID da sessão do usuário.
            user_id (int): ID do usuário autenticado.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}
        """
        # Obter itens do carrinho
        cart_items_result = await self.get_cart_items(session_id)
        
        if not cart_items_result["success"]:
            return cart_items_result
            
        cart_data = cart_items_result["data"]
        
        if not cart_data["items"]:
            return {"success": True, "data": {"message": "Nenhum item para sincronizar."}, "error": None}

        # A sincronização pode envolver a criação de um pedido em estado pendente
        # ou simplesmente associar o carrinho temporário ao usuário
        # Neste exemplo, vamos apenas retornar as informações do carrinho
        # que podem ser usadas para criar um pedido
        
        return {
            "success": True, 
            "data": {
                "user_id": user_id,
                "items": cart_data["items"],
                "total": cart_data["total"],
                "message": "Carrinho sincronizado com sucesso."
            }, 
            "error": None
        } 