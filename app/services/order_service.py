# D:\#3xDigital\app\services\order_service.py
"""
order_service.py

Este módulo contém a lógica de negócios para gerenciamento de pedidos,
incluindo criação, atualização, consulta e processamento de pedidos.

Classes:
    OrderService: Provedor de serviços relacionados a pedidos.
"""

from typing import List, Optional, Dict, Union, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Order, OrderItem, Product, User, Affiliate, Sale

class OrderService:
    """
    Serviço para gerenciamento de pedidos.

    Attributes:
        db_session (AsyncSession): Sessão do banco de dados.

    Methods:
        create_order: Cria um novo pedido.
        list_orders: Lista todos os pedidos.
        get_order: Obtém detalhes de um pedido específico.
        update_order_status: Atualiza o status de um pedido.
        delete_order: Remove um pedido.
        validate_order_items: Valida os itens do pedido.
        process_affiliate_sale: Processa uma venda de afiliado.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o serviço com a sessão do banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do SQLAlchemy.
        """
        self.db_session = db_session

    async def create_order(
        self, 
        user_id: int, 
        items: List[Dict[str, Any]], 
        ref_code: Optional[str] = None
    ) -> Dict[str, Union[Dict, str, bool]]:
        """
        Cria um novo pedido com os itens especificados.

        Args:
            user_id (int): ID do usuário que está fazendo o pedido.
            items (List[Dict[str, Any]]): Lista de itens do pedido.
                Cada item é um dicionário com product_id e quantity.
            ref_code (Optional[str]): Código de referência do afiliado.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se os itens do pedido forem inválidos.
        """
        if not items:
            return {"success": False, "error": "O pedido deve conter pelo menos um item.", "data": None}

        # Valida os itens e calcula o total
        validation_result = await self.validate_order_items(items)
        if not validation_result["success"]:
            return validation_result

        order_items = validation_result["data"]["order_items"]
        total = validation_result["data"]["total"]

        # Cria o pedido
        new_order = Order(user_id=user_id, status="processing", total=total)
        self.db_session.add(new_order)
        await self.db_session.commit()
        await self.db_session.refresh(new_order)

        # Associa os itens ao pedido
        for order_item in order_items:
            order_item.order_id = new_order.id
            self.db_session.add(order_item)

        # Atualiza o estoque dos produtos
        for product_id, quantity in [(item["product_id"], item["quantity"]) for item in items]:
            result = await self.db_session.execute(select(Product).where(Product.id == product_id))
            product = result.scalar()
            product.stock -= quantity

        await self.db_session.commit()

        # Se for enviado um código de afiliado, registra a venda
        sale_info = None
        if ref_code:
            sale_info = await self.process_affiliate_sale(new_order.id, total, ref_code)

        return {
            "success": True, 
            "data": {
                "order_id": new_order.id, 
                "total": total,
                "status": new_order.status,
                "sale_info": sale_info
            },
            "error": None
        }

    async def list_orders(self) -> Dict[str, Union[List[Dict], str, bool]]:
        """
        Lista todos os pedidos do sistema.

        Returns:
            Dict[str, Union[List[Dict], str, bool]]: Lista de pedidos.
                Estrutura: {"success": bool, "data": List[Dict], "error": str}
        """
        result = await self.db_session.execute(select(Order))
        orders = result.scalars().all()

        orders_list = [
            {
                "id": o.id, 
                "user_id": o.user_id, 
                "status": o.status, 
                "total": o.total
            } 
            for o in orders
        ]
        
        return {"success": True, "data": orders_list, "error": None}

    async def get_order(self, order_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Union[Dict, str, bool]]:
        """
        Obtém os detalhes de um pedido específico.

        Args:
            order_id (int): ID do pedido.
            user_id (Optional[int]): ID do usuário solicitante.
            is_admin (bool): Se o usuário é administrador.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Detalhes do pedido.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o pedido não for encontrado ou o usuário não tiver permissão.
        """
        result = await self.db_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar()

        if not order:
            return {"success": False, "error": "Pedido não encontrado.", "data": None}

        # Verifica permissão: apenas o próprio usuário ou admin pode ver o pedido
        if not is_admin and user_id != order.user_id:
            return {"success": False, "error": "Acesso negado.", "data": None}

        # Busca os itens do pedido
        result = await self.db_session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = result.scalars().all()
        
        items_list = [
            {
                "product_id": item.product_id, 
                "quantity": item.quantity, 
                "price": item.price
            } 
            for item in items
        ]
        
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status,
            "total": order.total,
            "items": items_list
        }
        
        return {"success": True, "data": order_data, "error": None}

    async def update_order_status(self, order_id: int, status: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza o status de um pedido.

        Args:
            order_id (int): ID do pedido.
            status (str): Novo status do pedido.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o pedido não for encontrado ou o status for inválido.
        """
        valid_statuses = ["processing", "shipped", "delivered", "returned"]
        if status not in valid_statuses:
            return {"success": False, "error": "Status inválido.", "data": None}

        result = await self.db_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar()

        if not order:
            return {"success": False, "error": "Pedido não encontrado.", "data": None}

        order.status = status
        await self.db_session.commit()
        
        return {
            "success": True, 
            "data": {
                "id": order.id,
                "status": order.status
            },
            "error": None
        }

    async def delete_order(self, order_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Remove um pedido existente.

        Args:
            order_id (int): ID do pedido a ser removido.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o pedido não for encontrado.
        """
        result = await self.db_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar()

        if not order:
            return {"success": False, "error": "Pedido não encontrado.", "data": None}

        await self.db_session.delete(order)
        await self.db_session.commit()
        
        return {
            "success": True, 
            "data": {"id": order_id},
            "error": None
        }

    async def validate_order_items(self, items: List[Dict[str, Any]]) -> Dict[str, Union[Dict, str, bool]]:
        """
        Valida os itens do pedido e calcula o total.

        Args:
            items (List[Dict[str, Any]]): Lista de itens do pedido.
                Cada item é um dicionário com product_id e quantity.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da validação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se algum item for inválido.
        """
        total = 0
        order_items = []

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            # Verifica se o produto existe e tem estoque suficiente
            result = await self.db_session.execute(select(Product).where(Product.id == product_id))
            product = result.scalar()
            
            if not product:
                return {"success": False, "error": f"Produto ID {product_id} não encontrado.", "data": None}
                
            if product.stock < quantity:
                return {"success": False, "error": f"Estoque insuficiente para o produto ID {product_id}.", "data": None}

            # Calcula subtotal
            subtotal = product.price * quantity
            total += subtotal

            # Cria item do pedido
            order_items.append(OrderItem(
                product_id=product_id, 
                quantity=quantity, 
                price=product.price
            ))

        return {
            "success": True, 
            "data": {
                "order_items": order_items,
                "total": total
            },
            "error": None
        }

    async def process_affiliate_sale(self, order_id: int, total: float, ref_code: str) -> Optional[Dict]:
        """
        Processa uma venda de afiliado.

        Args:
            order_id (int): ID do pedido.
            total (float): Valor total do pedido.
            ref_code (str): Código de referência do afiliado.

        Returns:
            Optional[Dict]: Informações da venda registrada ou None se o afiliado não for válido.
        """
        result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.referral_code == ref_code)
        )
        affiliate = result.scalar()
        
        if not affiliate or affiliate.request_status != 'approved':
            return None

        # Calcula a comissão e registra a venda
        commission = total * affiliate.commission_rate
        sale = Sale(
            affiliate_id=affiliate.id, 
            order_id=order_id, 
            commission=commission
        )
        
        self.db_session.add(sale)
        await self.db_session.commit()
        await self.db_session.refresh(sale)
        
        return {
            "affiliate_id": affiliate.id,
            "commission": commission,
            "sale_id": sale.id
        } 