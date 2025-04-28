# D:\3xDigital\app\services\affiliate_service.py
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
from sqlalchemy import select, and_, update
from sqlalchemy.orm import joinedload
from app.models.database import Affiliate, Sale, User, Order, OrderItem, Product

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
        register_sale: Registra uma venda para o afiliado pelo código de referência.
        list_approved_affiliates: Lista todos os afiliados aprovados com paginação.
        get_affiliation_status: Consulta o status da solicitação de afiliação do usuário.
        can_generate_affiliate_link: Verifica se um usuário está autorizado a gerar links de afiliado.
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
        from sqlalchemy import select
        from app.models.database import User
        
        # Verifica se o usuário existe
        result = await self.db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "Usuário não encontrado.", "data": None}
        
        # Verifica se existe registro de afiliado
        affiliate = await self.get_affiliate_by_user_id(user_id)
        
        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        # Verifica se o afiliado está aprovado
        if affiliate.request_status != 'approved':
            return {
                "success": False, 
                "error": "Afiliado inativo. Solicitação pendente ou rejeitada.",
                "data": None
            }
        
        # Verifica se o usuário tem o papel correto
        if user.role != 'affiliate':
            return {
                "success": False, 
                "error": "Usuário não possui permissão de afiliado.",
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
        from sqlalchemy import select
        from app.models.database import User
        
        # Verifica se o usuário existe
        result = await self.db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "Usuário não encontrado.", "data": None}
        
        # Verifica se existe registro de afiliado
        affiliate = await self.get_affiliate_by_user_id(user_id)

        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        # Verifica se o afiliado está aprovado
        if affiliate.request_status != 'approved':
            return {
                "success": False, 
                "error": "Afiliado inativo. Solicitação pendente ou rejeitada.",
                "data": None
            }
        
        # Verifica se o usuário tem o papel correto
        if user.role != 'affiliate':
            return {
                "success": False, 
                "error": "Usuário não possui permissão de afiliado.",
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
            **kwargs: Campos a serem atualizados:
                - commission_rate (float): Nova taxa de comissão
                - request_status (str): Novo status ('approved', 'pending', 'blocked')
                - reason (str): Motivo da recusa (quando request_status='blocked')

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo o resultado da operação.
                Estrutura: {"success": bool, "data": Dict, "error": str}

        Raises:
            ValueError: Se o afiliado não for encontrado.
        """
        from sqlalchemy import select, update
        from app.models.database import User

        affiliate = await self.get_affiliate_by_id(affiliate_id)
        
        if not affiliate:
            return {"success": False, "error": "Afiliado não encontrado.", "data": None}
        
        if "commission_rate" in kwargs:
            affiliate.commission_rate = kwargs["commission_rate"]
        
        if "request_status" in kwargs:
            old_status = affiliate.request_status
            affiliate.request_status = kwargs["request_status"]
            
            # Atualiza o campo reason quando o status for 'blocked' (rejeitado)
            if kwargs["request_status"] == "blocked" and "reason" in kwargs:
                affiliate.reason = kwargs["reason"]
            
            # Quando aprovar o afiliado, atualizar o campo role do usuário para 'affiliate'
            if kwargs["request_status"] == "approved" and old_status != "approved":
                # Atualiza o role do usuário para 'affiliate'
                await self.db_session.execute(
                    update(User)
                    .where(User.id == affiliate.user_id)
                    .values(role='affiliate')
                )
            
            # Quando rejeitar um afiliado que estava aprovado, reverte o role para 'user'
            if kwargs["request_status"] == "blocked" and old_status == "approved":
                # Atualiza o role do usuário para 'user'
                await self.db_session.execute(
                    update(User)
                    .where(User.id == affiliate.user_id)
                    .values(role='user')
                )
        
        await self.db_session.commit()
        await self.db_session.refresh(affiliate)
        
        # Busca o usuário atualizado para verificar se o role foi realmente alterado
        result = await self.db_session.execute(
            select(User).where(User.id == affiliate.user_id)
        )
        user = result.scalar_one_or_none()
        
        return {
            "success": True, 
            "data": {
                "id": affiliate.id,
                "user_id": affiliate.user_id,
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "request_status": affiliate.request_status,
                "reason": affiliate.reason,
                "user_role": user.role if user else None
            },
            "error": None
        }

    async def list_affiliate_requests(self, page: int = 1, per_page: int = 10) -> Dict[str, Union[Dict, str, bool]]:
        """
        Lista todas as solicitações de afiliação pendentes com paginação.

        Args:
            page (int): Número da página atual (começando em 1). Valor padrão: 1.
            per_page (int): Quantidade de registros por página. Valor padrão: 10.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo o resultado da operação.
                Estrutura: {
                    "success": bool,
                    "data": {
                        "requests": List[Dict],
                        "total": int,
                        "page": int,
                        "per_page": int,
                        "total_pages": int
                    },
                    "error": str
                }
        """
        # Calculando o offset para paginação
        offset = (page - 1) * per_page
        
        # Contando o total de solicitações de afiliação pendentes
        count_result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.request_status == 'pending')
        )
        total_requests = len(count_result.scalars().all())
        
        # Buscando solicitações pendentes com paginação e carregando os dados de usuário
        result = await self.db_session.execute(
            select(Affiliate)
            .options(joinedload(Affiliate.user))
            .where(Affiliate.request_status == 'pending')
            .order_by(Affiliate.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        affiliates = result.scalars().all()
        
        # Calculando o total de páginas
        total_pages = (total_requests + per_page - 1) // per_page
        
        # Convertendo para dicionário com dados completos de usuário
        requests_list = []
        for affiliate in affiliates:
            user = affiliate.user
            if user is None:
                # Se não encontrar o usuário, continue para o próximo afiliado
                continue
                
            affiliate_data = {
                "id": affiliate.id,
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "request_status": affiliate.request_status,
                "created_at": affiliate.created_at.isoformat(),
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "cpf": user.cpf,
                    "role": user.role,
                    "phone": user.phone,
                    "active": user.active,
                    "created_at": user.created_at.isoformat()
                }
            }
            requests_list.append(affiliate_data)
        
        return {
            "success": True,
            "data": {
                "requests": requests_list,
                "total": total_requests,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            },
            "error": None
        }

    async def list_approved_affiliates(self, page: int = 1, per_page: int = 10) -> Dict[str, Union[Dict, str, bool]]:
        """
        Lista todos os afiliados aprovados com paginação.

        Args:
            page (int): Número da página atual (começando em 1). Valor padrão: 1.
            per_page (int): Quantidade de registros por página. Valor padrão: 10.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo o resultado da operação.
                Estrutura: {
                    "success": bool,
                    "data": {
                        "affiliates": List[Dict],
                        "total": int,
                        "page": int,
                        "per_page": int,
                        "total_pages": int
                    },
                    "error": str
                }
        """
        # Calculando o offset para paginação
        offset = (page - 1) * per_page
        
        # Contando o total de afiliados aprovados
        count_result = await self.db_session.execute(
            select(Affiliate).where(Affiliate.request_status == 'approved')
        )
        total_affiliates = len(count_result.scalars().all())
        
        # Buscando afiliados aprovados com paginação e carregando os dados de usuário
        result = await self.db_session.execute(
            select(Affiliate)
            .options(joinedload(Affiliate.user))
            .where(Affiliate.request_status == 'approved')
            .order_by(Affiliate.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        affiliates = result.scalars().all()
        
        # Calculando o total de páginas
        total_pages = (total_affiliates + per_page - 1) // per_page
        
        # Convertendo para dicionário com dados completos de usuário
        affiliates_list = []
        for affiliate in affiliates:
            user = affiliate.user
            if user is None:
                # Se não encontrar o usuário, continue para o próximo afiliado
                continue
                
            affiliate_data = {
                "id": affiliate.id,
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "request_status": affiliate.request_status,
                "created_at": affiliate.created_at.isoformat(),
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "cpf": user.cpf,
                    "role": user.role,
                    "phone": user.phone,
                    "active": user.active,
                    "created_at": user.created_at.isoformat()
                }
            }
            affiliates_list.append(affiliate_data)
        
        return {
            "success": True,
            "data": {
                "affiliates": affiliates_list,
                "total": total_affiliates,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            },
            "error": None
        }

    async def get_affiliation_status(self, user_id: int) -> Dict[str, Union[Dict, str, bool]]:
        """
        Consulta o status da solicitação de afiliação do usuário.

        Args:
            user_id (int): ID do usuário.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Dicionário contendo as informações de status.
                Estrutura: {
                    "success": bool,
                    "data": {
                        "status": str,
                        "created_at": str,
                        "updated_at": str,
                        "message": str,
                        "reason": str (opcional)
                    },
                    "error": str
                }
        """
        affiliate = await self.get_affiliate_by_user_id(user_id)
        
        if not affiliate:
            return {
                "success": True, 
                "data": {
                    "status": "not_requested",
                    "message": "Você ainda não solicitou afiliação."
                },
                "error": None
            }
        
        # Mensagem e status específicos para cada status
        message = "Sua solicitação está em análise."
        if affiliate.request_status == 'approved':
            message = "Sua solicitação foi aprovada. Você pode gerar seu link de afiliado."
        elif affiliate.request_status == 'blocked':
            message = "Sua solicitação foi rejeitada."
        
        status_data = {
            "status": affiliate.request_status,
            "created_at": affiliate.created_at.isoformat() if affiliate.created_at else None,
            "updated_at": affiliate.updated_at.isoformat() if affiliate.updated_at else None,
            "message": message
        }
        
        # Inclui o motivo da rejeição, se houver
        if affiliate.request_status == 'blocked' and affiliate.reason:
            status_data["reason"] = affiliate.reason
        
        return {"success": True, "data": status_data, "error": None}

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

    async def register_sale(self, order_id: int, referral_code: str) -> Dict[str, Union[Dict, str, bool]]:
        """
        Registra uma venda para o afiliado pelo código de referência.

        Args:
            order_id (int): ID do pedido.
            referral_code (str): Código de referência do afiliado.

        Returns:
            Dict[str, Union[Dict, str, bool]]: Resultado da operação com detalhes da venda.
                Estrutura: {"success": bool, "message": str, "data": Dict}
        """
        # Verificar se o afiliado existe e está aprovado
        affiliate = await self.get_affiliate_by_referral_code(referral_code)
        if not affiliate:
            return {
                "success": False, 
                "message": f"Afiliado não encontrado com código de referência: {referral_code}",
                "data": None
            }
            
        if affiliate.request_status != 'approved':
            return {
                "success": False, 
                "message": f"Afiliado não está aprovado (status: {affiliate.request_status})",
                "data": None
            }
            
        # Buscar o pedido e verificar se existe
        result = await self.db_session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar()
        if not order:
            return {
                "success": False, 
                "message": f"Pedido não encontrado: {order_id}",
                "data": None
            }
        
        # Verificar se já existe uma venda registrada para este pedido e afiliado
        result = await self.db_session.execute(
            select(Sale).where(
                and_(
                    Sale.order_id == order_id,
                    Sale.affiliate_id == affiliate.id
                )
            )
        )
        existing_sale = result.scalar()
        if existing_sale:
            return {
                "success": True, 
                "message": "Venda já registrada para este pedido e afiliado.",
                "data": {
                    "sale_id": existing_sale.id,
                    "affiliate_id": existing_sale.affiliate_id,
                    "order_id": existing_sale.order_id,
                    "commission": existing_sale.commission
                }
            }
        
        # Buscar itens do pedido para calcular comissões personalizadas
        result = await self.db_session.execute(
            select(OrderItem)
            .join(Product)
            .filter(OrderItem.order_id == order_id)
            .options(joinedload(OrderItem.product))
        )
        order_items = result.scalars().all()
        
        if not order_items:
            return {
                "success": False, 
                "message": f"Pedido {order_id} não possui itens",
                "data": None
            }
            
        # Calcular a comissão considerando comissões personalizadas por produto
        total_commission = 0.0
        commission_details = []
        
        for item in order_items:
            product = item.product
            item_total = item.price * item.quantity
            
            if product.has_custom_commission and product.commission_type and product.commission_value is not None:
                if product.commission_type == 'percentage':
                    # Percentual do valor do produto
                    item_commission = item_total * (product.commission_value / 100)
                    commission_details.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "type": "percentage",
                        "value": product.commission_value,
                        "item_total": item_total,
                        "commission": item_commission
                    })
                elif product.commission_type == 'fixed':
                    # Valor fixo por unidade
                    item_commission = product.commission_value * item.quantity
                    commission_details.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "type": "fixed",
                        "value": product.commission_value,
                        "quantity": item.quantity,
                        "commission": item_commission
                    })
            else:
                # Usa a taxa de comissão padrão do afiliado
                item_commission = item_total * affiliate.commission_rate
                commission_details.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "type": "standard",
                    "rate": affiliate.commission_rate,
                    "item_total": item_total,
                    "commission": item_commission
                })
                
            total_commission += item_commission
        
        # Registra a venda com a comissão calculada
        sale = Sale(
            affiliate_id=affiliate.id, 
            order_id=order.id, 
            commission=total_commission
        )
        self.db_session.add(sale)
        await self.db_session.commit()
        await self.db_session.refresh(sale)
        
        return {
            "success": True,
            "message": "Venda registrada com sucesso para o afiliado.",
            "data": {
                "sale_id": sale.id,
                "affiliate_id": sale.affiliate_id,
                "order_id": sale.order_id,
                "commission": total_commission,
                "details": commission_details
            }
        }

    async def can_generate_affiliate_link(self, user_id: int) -> Dict[str, Union[bool, str]]:
        """
        Verifica se um usuário está autorizado a gerar links de afiliado.
        
        Para gerar links, o usuário deve:
        1. Ter papel 'affiliate' na tabela User
        2. Ter uma entrada na tabela Affiliate com request_status='approved'

        Args:
            user_id (int): ID do usuário a ser verificado.

        Returns:
            Dict[str, Union[bool, str]]: Dicionário com resultado da verificação:
                {
                    "can_generate": bool,
                    "reason": str (opcional, presente quando can_generate é False)
                }
        """
        from sqlalchemy import select
        from app.models.database import User
        
        # Verifica se o usuário existe e tem o papel correto
        result = await self.db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"can_generate": False, "reason": "Usuário não encontrado."}
        
        if user.role != 'affiliate':
            return {
                "can_generate": False,
                "reason": "Usuário não possui o papel de afiliado."
            }
        
        # Verifica se o afiliado existe e está aprovado
        affiliate = await self.get_affiliate_by_user_id(user_id)
        if not affiliate:
            return {
                "can_generate": False,
                "reason": "Registro de afiliado não encontrado."
            }
        
        if affiliate.request_status != 'approved':
            return {
                "can_generate": False,
                "reason": "Solicitação de afiliação pendente ou rejeitada."
            }
        
        # Se chegou até aqui, o usuário pode gerar links
        return {"can_generate": True} 