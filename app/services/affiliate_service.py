# D:\#3xDigital\app\services\affiliate_service.py
"""
affiliate_service.py

Este módulo contém a lógica de negócios para gerenciamento de afiliados,
incluindo criação, atualização e consulta de afiliados, bem como
gerenciamento de suas comissões e status.

Classes:
    AffiliateService: Provedor de serviços relacionados a afiliados.
"""

import uuid
from typing import List, Optional, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import Affiliate, Sale, User, Order

class AffiliateService:
    """
    Serviço para gerenciamento de afiliados.

    Attributes:
        db_session (AsyncSession): Sessão do banco de dados.

    Methods:
        get_affiliate_link: Obtém o link de afiliado para o usuário.
        get_affiliate_sales: Obtém vendas e comissões do afiliado.
        request_affiliation: Registra solicitação de afiliação.
        update_affiliate: Atualiza informações do afiliado.
        list_affiliate_requests: Lista solicitações de afiliação pendentes.
        get_affiliate_by_user_id: Busca afiliado pelo ID do usuário.
        get_affiliate_by_id: Busca afiliado pelo ID do afiliado.
        get_affiliate_by_referral_code: Busca afiliado pelo código de referência.
        generate_referral_code: Gera código de referência único.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o serviço com a sessão do banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do SQLAlchemy.
        """
        self.db_session = db_session

    async def get_affiliate_link(self, user_id: int, base_url: str) -> Dict[str, Union[str, bool]]:
        """
        Obtém o link de afiliado para o usuário especificado.

        Args:
            user_id (int): ID do usuário.
            base_url (str): URL base para construir o link de afiliado.

        Returns:
            Dict[str, Union[str, bool]]: Dicionário contendo o link do afiliado ou informações de erro.
                Estrutura: {"success": bool, "data": str, "error": str}

        Raises:
            ValueError: Se o afiliado não for encontrado ou estiver inativo.
        """
        affiliate = await self.get_affiliate_by_user_id(user_id)

        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        if affiliate.request_status != 'approved':
            return {
                "success": False, 
                "error": "Afiliado inativo. Solicitação pendente ou rejeitada.",
                "data": None
            }
        
        link = f"{base_url}/?ref={affiliate.referral_code}"
        return {"success": True, "data": link, "error": None}

    async def get_affiliate_sales(self, user_id: int) -> Dict[str, Union[List[Dict], str, bool]]:
        """
        Obtém a lista de vendas e comissões do afiliado.

        Args:
            user_id (int): ID do usuário afiliado.

        Returns:
            Dict[str, Union[List[Dict], str, bool]]: Dicionário contendo a lista de vendas ou informações de erro.
                Estrutura: {"success": bool, "data": List[Dict], "error": str}

        Raises:
            ValueError: Se o afiliado não for encontrado ou estiver inativo.
        """
        affiliate = await self.get_affiliate_by_user_id(user_id)

        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        if affiliate.request_status != 'approved':
            return {
                "success": False, 
                "error": "Afiliado inativo. Solicitação pendente ou rejeitada.",
                "data": None
            }
        
        result = await self.db_session.execute(
            select(Sale).where(Sale.affiliate_id == affiliate.id)
        )
        sales = result.scalars().all()
        sales_list = [{"order_id": sale.order_id, "commission": sale.commission} for sale in sales]
        
        return {"success": True, "data": sales_list, "error": None}

    async def request_affiliation(self, user_id: int, commission_rate: float = 0.05) -> Dict[str, Union[Dict, str, bool]]:
        """
        Registra uma solicitação de afiliação para o usuário.

        Args:
            user_id (int): ID do usuário.
            commission_rate (float, optional): Taxa de comissão proposta. Padrão é 0.05 (5%).

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo o resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o usuário já tiver uma solicitação existente.
        """
        # Verifica se já existe registro de afiliação para o usuário
        affiliate = await self.get_affiliate_by_user_id(user_id)
        
        if affiliate:
            return {"success": False, "error": "Solicitação de afiliação já existente.", "data": None}
        
        # Gera um código de referência único
        referral_code = await self.generate_referral_code()
        
        new_affiliate = Affiliate(
            user_id=user_id,
            referral_code=referral_code,
            commission_rate=commission_rate,
            request_status='pending'
        )
        
        self.db_session.add(new_affiliate)
        await self.db_session.commit()
        await self.db_session.refresh(new_affiliate)
        
        return {
            "success": True, 
            "data": {
                "referral_code": new_affiliate.referral_code,
                "id": new_affiliate.id,
                "status": new_affiliate.request_status
            },
            "error": None
        }

    async def update_affiliate(self, affiliate_id: int, **kwargs) -> Dict[str, Union[Dict, str, bool]]:
        """
        Atualiza os dados de um afiliado.

        Args:
            affiliate_id (int): ID do afiliado.
            **kwargs: Campos a serem atualizados (commission_rate, request_status).

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo o resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o afiliado não for encontrado.
        """
        affiliate = await self.get_affiliate_by_id(affiliate_id)
        
        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        if "commission_rate" in kwargs:
            affiliate.commission_rate = kwargs["commission_rate"]
        
        if "request_status" in kwargs:
            affiliate.request_status = kwargs["request_status"]
        
        await self.db_session.commit()
        await self.db_session.refresh(affiliate)
        
        return {
            "success": True, 
            "data": {
                "id": affiliate.id,
                "user_id": affiliate.user_id,
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "request_status": affiliate.request_status
            },
            "error": None
        }

    async def list_affiliate_requests(self) -> Dict[str, Union[List[Dict], str, bool]]:
        """
        Lista todas as solicitações de afiliação pendentes.

        Returns:
            Dict[str, Union[List[Dict], str, bool]]: Dicionário contendo a lista de solicitações.
                Estrutura: {"success": bool, "data": List[Dict], "error": str}
        """
        result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.request_status == 'pending')
        )
        affiliates = result.scalars().all()
        
        affiliates_list = [
            {
                "id": a.id, 
                "user_id": a.user_id, 
                "referral_code": a.referral_code, 
                "commission_rate": a.commission_rate
            }
            for a in affiliates
        ]
        
        return {"success": True, "data": affiliates_list, "error": None}

    async def get_affiliate_by_user_id(self, user_id: int) -> Optional[Affiliate]:
        """
        Busca um afiliado pelo ID do usuário.

        Args:
            user_id (int): ID do usuário.

        Returns:
            Optional[Affiliate]: Objeto do afiliado ou None se não encontrado.
        """
        result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.user_id == user_id)
        )
        return result.scalar()

    async def get_affiliate_by_id(self, affiliate_id: int) -> Optional[Affiliate]:
        """
        Busca um afiliado pelo ID do afiliado.

        Args:
            affiliate_id (int): ID do afiliado.

        Returns:
            Optional[Affiliate]: Objeto do afiliado ou None se não encontrado.
        """
        result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.id == affiliate_id)
        )
        return result.scalar()

    async def get_affiliate_by_referral_code(self, referral_code: str) -> Optional[Affiliate]:
        """
        Busca um afiliado pelo código de referência.

        Args:
            referral_code (str): Código de referência.

        Returns:
            Optional[Affiliate]: Objeto do afiliado ou None se não encontrado.
        """
        result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.referral_code == referral_code)
        )
        return result.scalar()
        
    async def generate_referral_code(self) -> str:
        """
        Gera um código de referência único para o afiliado.

        Returns:
            str: Código de referência único.
        """
        while True:
            referral_code = f"REF{uuid.uuid4().hex[:8].upper()}"
            existing = await self.get_affiliate_by_referral_code(referral_code)
            if not existing:
                return referral_code

    async def register_sale(self, order_id: int, referral_code: str) -> Optional[Dict]:
        """
        Registra uma venda para o afiliado pelo código de referência.

        Args:
            order_id (int): ID do pedido.
            referral_code (str): Código de referência do afiliado.

        Returns:
            Optional[Dict]: Dados da venda registrada ou None se o afiliado ou pedido não forem encontrados.
        """
        affiliate = await self.get_affiliate_by_referral_code(referral_code)
        if not affiliate or affiliate.request_status != 'approved':
            return None
            
        result = await self.db_session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar()
        if not order:
            return None
            
        # Calcula a comissão baseada no total do pedido
        commission = order.total * affiliate.commission_rate
        
        # Registra a venda
        sale = Sale(
            affiliate_id=affiliate.id, 
            order_id=order.id, 
            commission=commission
        )
        self.db_session.add(sale)
        await self.db_session.commit()
        await self.db_session.refresh(sale)
        
        return {
            "sale_id": sale.id,
            "affiliate_id": sale.affiliate_id,
            "order_id": sale.order_id,
            "commission": sale.commission
        } 