# D:\3xDigital\app\services\finance_service.py
"""
finance_service.py

Módulo responsável pela lógica financeira do sistema 3xDigital, incluindo gerenciamento
de saldos, transações, saques e integração com gateways de pagamento.

Funcionalidades principais:
    - Criação e atualização de saldo de afiliados
    - Registro de transações (comissões e saques)
    - Processamento de solicitações de saque
    - Geração de relatórios financeiros

Regras de Negócio:
    - Saldo não pode ficar negativo
    - Comissões são registradas automaticamente após confirmação de vendas
    - Saques precisam ser aprovados por um administrador
    - Toda movimentação financeira é registrada no extrato do afiliado

Dependências:
    - SQLAlchemy para persistência de dados
    - app.models.finance_models para estrutura de dados financeiros
    - app.models.database para acesso a dados de afiliados e vendas
"""

from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Affiliate, Sale, Order
from app.models.finance_models import (
    AffiliateBalance, AffiliateTransaction, WithdrawalRequest,
    PaymentGatewayConfig, PaymentTransaction
)
from app.config.settings import TIMEZONE


async def get_or_create_balance(session: AsyncSession, affiliate_id: int) -> AffiliateBalance:
    """
    Obtém ou cria um registro de saldo para um afiliado.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (int): ID do afiliado
        
    Returns:
        AffiliateBalance: Registro de saldo do afiliado
    """
    # Busca o saldo existente
    result = await session.execute(
        select(AffiliateBalance).where(AffiliateBalance.affiliate_id == affiliate_id)
    )
    balance = result.scalar_one_or_none()
    
    # Se não existir, cria um novo
    if not balance:
        balance = AffiliateBalance(
            affiliate_id=affiliate_id,
            current_balance=0.0,
            total_earned=0.0,
            total_withdrawn=0.0,
            last_updated=TIMEZONE()
        )
        session.add(balance)
        await session.commit()
        await session.refresh(balance)
    
    return balance


async def register_commission(
    session: AsyncSession, 
    affiliate_id: int,
    sale_id: int,
    commission_amount: float,
    order_id: Optional[int] = None
) -> Tuple[bool, Optional[str], Optional[AffiliateTransaction]]:
    """
    Registra uma comissão para um afiliado e atualiza seu saldo.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (int): ID do afiliado
        sale_id (int): ID da venda relacionada
        commission_amount (float): Valor da comissão
        order_id (Optional[int]): ID do pedido relacionado (opcional)
        
    Returns:
        Tuple[bool, Optional[str], Optional[AffiliateTransaction]]: 
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Transação gerada (se sucesso)
    """
    # Validações básicas
    if commission_amount <= 0:
        return False, "Valor da commission must be positive", None
    
    # Verifica se o afiliado existe
    result = await session.execute(
        select(Affiliate).where(Affiliate.id == affiliate_id)
    )
    affiliate = result.scalar_one_or_none()
    
    if not affiliate:
        return False, "Afiliate not found", None
    
    # Verifica se a venda existe
    result = await session.execute(
        select(Sale).where(Sale.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if not sale:
        return False, "Sale not found", None
    
    # Verifica se já existe uma transação para esta venda
    result = await session.execute(
        select(AffiliateTransaction)
        .join(AffiliateBalance)
        .where(
            and_(
                AffiliateTransaction.type == 'commission',
                AffiliateTransaction.reference_id == sale_id,
                AffiliateBalance.affiliate_id == affiliate_id
            )
        )
    )
    existing_transaction = result.scalar_one_or_none()
    
    if existing_transaction:
        return False, "Commission already registered for this sale", None
    
    # Obtém ou cria o saldo do afiliado
    balance = await get_or_create_balance(session, affiliate_id)
    
    # Cria a transação de comissão
    description = f"Commission from sale #{sale_id}"
    if order_id:
        description += f" - Order #{order_id}"
    description += f" - R$ {commission_amount:.2f}"
    
    transaction = AffiliateTransaction(
        balance_id=balance.id,
        type='commission',
        amount=commission_amount,
        description=description,
        reference_id=sale_id,
        transaction_date=TIMEZONE()
    )
    
    # Atualiza o saldo
    balance.current_balance += commission_amount
    balance.total_earned += commission_amount
    balance.last_updated = TIMEZONE()
    
    # Salva as alterações
    session.add(transaction)
    session.add(balance)
    await session.commit()
    await session.refresh(transaction)
    
    return True, None, transaction


async def update_affiliate_balance_from_sale(
    session: AsyncSession, 
    sale_id: int
) -> Tuple[bool, Optional[str], Optional[AffiliateTransaction]]:
    """
    Atualiza o saldo do afiliado com base em uma venda registrada.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        sale_id (int): ID da venda
        
    Returns:
        Tuple[bool, Optional[str], Optional[AffiliateTransaction]]: 
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Transação gerada (se sucesso)
    """
    # Busca a venda com dados do afiliado e pedido
    result = await session.execute(
        select(Sale).options(joinedload(Sale.affiliate), joinedload(Sale.order)).where(Sale.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if not sale:
        return False, "Sale not found", None
    
    # Verifica status do pedido
    # Nota: Em sistema real, poderia ser um hook após confirmação de pagamento
    if sale.order and sale.order.status not in ['delivered', 'shipped']:
        return False, f"Order with status '{sale.order.status}' not eligible for commission", None
    
    # Registra a comissão
    return await register_commission(
        session,
        sale.affiliate_id,
        sale_id, 
        sale.commission,
        sale.order_id if sale.order else None
    )


async def create_withdrawal_request(
    session: AsyncSession,
    affiliate_id: int,
    amount: float,
    payment_method: str,
    payment_details: str
) -> Tuple[bool, Optional[str], Optional[WithdrawalRequest]]:
    """
    Cria uma nova solicitação de saque para um afiliado.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (int): ID do afiliado
        amount (float): Valor solicitado para saque
        payment_method (str): Método de pagamento (pix, transferência, etc)
        payment_details (str): Detalhes do pagamento
        
    Returns:
        Tuple[bool, Optional[str], Optional[WithdrawalRequest]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Solicitação de saque criada (se sucesso)
    """
    # Verifica se o valor é válido
    if amount <= 0:
        return False, "Withdrawal amount must be greater than zero", None
    
    # Verifica se o afiliado existe
    result = await session.execute(
        select(Affiliate).where(Affiliate.id == affiliate_id)
    )
    affiliate = result.scalar_one_or_none()
    
    if not affiliate:
        return False, "Afiliate not found", None
    
    # Verifica se o afiliado está ativo
    if affiliate.request_status != 'approved':
        return False, "Afiliate not approved for withdrawals", None
    
    # Verifica o saldo disponível
    balance = await get_or_create_balance(session, affiliate_id)
    
    if balance.current_balance < amount:
        return False, f"Insufficient balance. Available: R$ {balance.current_balance:.2f}", None
    
    # Verifica se já existe uma solicitação pendente
    result = await session.execute(
        select(WithdrawalRequest)
        .where(
            and_(
                WithdrawalRequest.affiliate_id == affiliate_id,
                WithdrawalRequest.status == 'pending'
            )
        )
    )
    pending_request = result.scalar_one_or_none()
    
    if pending_request:
        return False, "There is already a pending withdrawal request", None
    
    # Cria a solicitação de saque
    withdrawal_request = WithdrawalRequest(
        affiliate_id=affiliate_id,
        amount=amount,
        status='pending',
        payment_method=payment_method,
        payment_details=payment_details,
        requested_at=TIMEZONE()
    )
    
    session.add(withdrawal_request)
    await session.commit()
    await session.refresh(withdrawal_request)
    
    return True, None, withdrawal_request


async def process_withdrawal_request(
    session: AsyncSession,
    request_id: int,
    status: str,
    admin_notes: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[AffiliateTransaction]]:
    """
    Processa uma solicitação de saque (aprovar, rejeitar, marcar como paga).
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        request_id (int): ID da solicitação de saque
        status (str): Novo status ('approved', 'rejected', 'paid')
        admin_notes (Optional[str]): Notas do administrador sobre a decisão
        
    Returns:
        Tuple[bool, Optional[str], Optional[AffiliateTransaction]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Transação gerada (se for aprovado)
    """
    # Verifica se o status é válido
    valid_statuses = ['approved', 'rejected', 'paid']
    if status not in valid_statuses:
        return False, f"Invalid status. Use one of the following: {', '.join(valid_statuses)}", None
    
    # Busca a solicitação
    result = await session.execute(
        select(WithdrawalRequest).options(joinedload(WithdrawalRequest.affiliate)).where(WithdrawalRequest.id == request_id)
    )
    withdrawal = result.scalar_one_or_none()
    
    if not withdrawal:
        return False, "Withdrawal request not found", None
    
    # Verifica se já foi processada
    if withdrawal.status != 'pending' and status != 'paid':
        return False, f"Request already {withdrawal.status}", None
    
    # Verifica se está tentando marcar como pago algo que não está aprovado
    if status == 'paid' and withdrawal.status != 'approved':
        return False, "Only approved requests can be marked as paid", None
    
    # Processa de acordo com o status
    transaction = None
    
    # Aprovação: cria a transação e atualiza o saldo
    if status == 'approved' and withdrawal.status == 'pending':
        balance = await get_or_create_balance(session, withdrawal.affiliate_id)
        
        # Verifica saldo novamente
        if balance.current_balance < withdrawal.amount:
            return False, "Insufficient balance to approve withdrawal", None
        
        # Cria a transação de saque
        description = f"Withdrawal approved #{withdrawal.id} - {withdrawal.payment_method}"
        transaction = AffiliateTransaction(
            balance_id=balance.id,
            type='withdrawal',
            amount=-withdrawal.amount,  # Valor negativo para saques
            description=description,
            reference_id=withdrawal.id,
            transaction_date=TIMEZONE()
        )
        
        # Atualiza o saldo
        balance.current_balance -= withdrawal.amount
        balance.total_withdrawn += withdrawal.amount
        balance.last_updated = TIMEZONE()
        
        session.add(transaction)
        session.add(balance)
        
        # Atualiza a solicitação
        withdrawal.status = status
        withdrawal.processed_at = TIMEZONE()
        withdrawal.admin_notes = admin_notes
    
    # Rejeição: apenas atualiza o status
    elif status == 'rejected' and withdrawal.status == 'pending':
        withdrawal.status = status
        withdrawal.processed_at = TIMEZONE()
        withdrawal.admin_notes = admin_notes
    
    # Pagamento: atualiza para pago se já estiver aprovado
    elif status == 'paid' and withdrawal.status == 'approved':
        withdrawal.status = status
        withdrawal.processed_at = TIMEZONE()
        withdrawal.admin_notes = admin_notes or withdrawal.admin_notes
    
    # Salva as alterações
    session.add(withdrawal)
    await session.commit()
    
    if transaction:
        await session.refresh(transaction)
        # Atualiza o ID da transação na solicitação de saque
        withdrawal.transaction_id = transaction.id
        await session.commit()
    
    return True, None, transaction


async def get_affiliate_transactions(
    session: AsyncSession,
    affiliate_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[AffiliateTransaction], int]:
    """
    Obtém o extrato de transações de um afiliado com opções de filtragem.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (int): ID do afiliado
        start_date (Optional[datetime]): Data inicial para filtro
        end_date (Optional[datetime]): Data final para filtro
        transaction_type (Optional[str]): Tipo de transação ('commission', 'withdrawal', 'adjustment')
        page (int): Página de resultados
        page_size (int): Tamanho da página
        
    Returns:
        Tuple[List[AffiliateTransaction], int]:
            - Lista de transações
            - Total de transações encontradas
    """
    # Obtém o saldo do afiliado
    result = await session.execute(
        select(AffiliateBalance).where(AffiliateBalance.affiliate_id == affiliate_id)
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        return [], 0
    
    # Constrói a query base
    query = select(AffiliateTransaction).where(AffiliateTransaction.balance_id == balance.id)
    
    # Aplica filtros
    if start_date:
        query = query.where(AffiliateTransaction.transaction_date >= start_date)
    
    if end_date:
        query = query.where(AffiliateTransaction.transaction_date <= end_date)
    
    if transaction_type:
        query = query.where(AffiliateTransaction.type == transaction_type)
    
    # Conta o total
    count_query = select(func.count()).select_from(query.subquery())
    result = await session.execute(count_query)
    total_count = result.scalar_one()
    
    # Aplica paginação e ordenação
    query = query.order_by(desc(AffiliateTransaction.transaction_date))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Executa a query
    result = await session.execute(query)
    transactions = result.scalars().all()
    
    return transactions, total_count


async def get_withdrawal_requests(
    session: AsyncSession,
    affiliate_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[WithdrawalRequest], int]:
    """
    Obtém solicitações de saque com opções de filtragem.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (Optional[int]): Filtrar por ID do afiliado
        status (Optional[str]): Filtrar por status
        page (int): Página de resultados
        page_size (int): Tamanho da página
        
    Returns:
        Tuple[List[WithdrawalRequest], int]:
            - Lista de solicitações
            - Total de solicitações encontradas
    """
    # Constrói a query base
    query = select(WithdrawalRequest)
    
    # Aplica filtros
    if affiliate_id:
        query = query.where(WithdrawalRequest.affiliate_id == affiliate_id)
    
    if status:
        query = query.where(WithdrawalRequest.status == status)
    
    # Conta o total
    count_query = select(func.count()).select_from(query.subquery())
    result = await session.execute(count_query)
    total_count = result.scalar_one()
    
    # Aplica paginação e ordenação
    query = query.order_by(desc(WithdrawalRequest.requested_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Executa a query
    result = await session.execute(query)
    requests = result.scalars().all()
    
    return requests, total_count


async def generate_financial_report(
    session: AsyncSession,
    affiliate_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict:
    """
    Gera um relatório financeiro detalhado do sistema ou de um afiliado específico.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        affiliate_id (Optional[int]): ID do afiliado (None para relatório geral)
        start_date (Optional[datetime]): Data inicial para relatório
        end_date (Optional[datetime]): Data final para relatório
        
    Returns:
        Dict: Dados do relatório financeiro
    """
    # Define período padrão se não especificado
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    
    if not end_date:
        end_date = datetime.now()
    
    # Inicializa o relatório
    report = {
        "periodo": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "comissoes": {
            "total": 0.0,
            "count": 0
        },
        "saques": {
            "total": 0.0,
            "count": 0,
            "pendentes": {
                "total": 0.0,
                "count": 0
            },
            "aprovados": {
                "total": 0.0,
                "count": 0
            },
            "pagos": {
                "total": 0.0,
                "count": 0
            },
            "rejeitados": {
                "total": 0.0,
                "count": 0
            }
        }
    }
    
    # Adiciona dados do afiliado
    if affiliate_id:
        # Busca o afiliado
        result = await session.execute(
            select(Affiliate).options(joinedload(Affiliate.user)).where(Affiliate.id == affiliate_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if affiliate:
            # Busca o saldo
            result = await session.execute(
                select(AffiliateBalance).where(AffiliateBalance.affiliate_id == affiliate_id)
            )
            balance = result.scalar_one_or_none()
            
            report["afiliado"] = {
                "id": affiliate.id,
                "name": affiliate.user.name if affiliate.user else "N/A",
                "email": affiliate.user.email if affiliate.user else "N/A",
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "current_balance": balance.current_balance if balance else 0.0,
                "total_earned": balance.total_earned if balance else 0.0,
                "total_withdrawn": balance.total_withdrawn if balance else 0.0
            }
    
    # Obtém dados de comissões
    if affiliate_id:
        # Para um afiliado específico
        result = await session.execute(
            select(
                func.count(AffiliateTransaction.id).label("count"),
                func.sum(AffiliateTransaction.amount).label("total")
            )
            .join(AffiliateBalance)
            .where(
                and_(
                    AffiliateTransaction.type == 'commission',
                    AffiliateTransaction.transaction_date.between(start_date, end_date),
                    AffiliateBalance.affiliate_id == affiliate_id
                )
            )
        )
    else:
        # Para todos os afiliados
        result = await session.execute(
            select(
                func.count(AffiliateTransaction.id).label("count"),
                func.sum(AffiliateTransaction.amount).label("total")
            )
            .where(
                and_(
                    AffiliateTransaction.type == 'commission',
                    AffiliateTransaction.transaction_date.between(start_date, end_date)
                )
            )
        )
    
    commission_data = result.one_or_none()
    if commission_data:
        report["comissoes"]["count"] = commission_data[0] or 0
        report["comissoes"]["total"] = float(commission_data[1] or 0)
    
    # Obtém dados de saques
    withdrawal_statuses = ["pending", "approved", "paid", "rejected"]
    for status in withdrawal_statuses:
        if affiliate_id:
            # Para um afiliado específico
            result = await session.execute(
                select(
                    func.count(WithdrawalRequest.id).label("count"),
                    func.sum(WithdrawalRequest.amount).label("total")
                )
                .where(
                    and_(
                        WithdrawalRequest.status == status,
                        WithdrawalRequest.requested_at.between(start_date, end_date),
                        WithdrawalRequest.affiliate_id == affiliate_id
                    )
                )
            )
        else:
            # Para todos os afiliados
            result = await session.execute(
                select(
                    func.count(WithdrawalRequest.id).label("count"),
                    func.sum(WithdrawalRequest.amount).label("total")
                )
                .where(
                    and_(
                        WithdrawalRequest.status == status,
                        WithdrawalRequest.requested_at.between(start_date, end_date)
                    )
                )
            )
        
        withdrawal_data = result.one_or_none()
        
        if status == "pending":
            report["saques"]["pendentes"]["count"] = withdrawal_data[0] or 0
            report["saques"]["pendentes"]["total"] = float(withdrawal_data[1] or 0)
        elif status == "approved":
            report["saques"]["aprovados"]["count"] = withdrawal_data[0] or 0
            report["saques"]["aprovados"]["total"] = float(withdrawal_data[1] or 0)
            # Adiciona aos totais
            report["saques"]["count"] += withdrawal_data[0] or 0
            report["saques"]["total"] += float(withdrawal_data[1] or 0)
        elif status == "paid":
            report["saques"]["pagos"]["count"] = withdrawal_data[0] or 0
            report["saques"]["pagos"]["total"] = float(withdrawal_data[1] or 0)
            # Adiciona aos totais
            report["saques"]["count"] += withdrawal_data[0] or 0
            report["saques"]["total"] += float(withdrawal_data[1] or 0)
        elif status == "rejected":
            report["saques"]["rejeitados"]["count"] = withdrawal_data[0] or 0
            report["saques"]["rejeitados"]["total"] = float(withdrawal_data[1] or 0)
    
    return report