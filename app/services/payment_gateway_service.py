# D:\3xDigital\app\services\payment_gateway_service.py

"""
payment_gateway_service.py

Módulo responsável pela integração com gateways de pagamento externos como
Stripe e Mercado Pago, bem como processamento de pagamentos e divisão (split)
entre afiliados e a loja.

Funcionalidades principais:
    - Configuração e gerenciamento de gateways de pagamento
    - Processamento de pagamentos via diferentes gateways
    - Split de pagamentos entre afiliados e loja
    - Registro de transações de pagamento
    - Webhooks para receber callbacks dos gateways

Dependências:
    - Stripe para pagamentos via Stripe
    - mercadopago para pagamentos via Mercado Pago
    - SQLAlchemy para persistência de dados
    - app.models.finance_models para estrutura de transações
"""

import json
import uuid
import stripe
import mercadopago
from typing import Dict, List, Optional, Tuple, Any, Union
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import Order, Affiliate, Sale
from app.services.finance_service import register_commission, update_affiliate_balance_from_sale
from app.config.settings import TIMEZONE


async def get_gateway_config(session: AsyncSession, gateway_name: str) -> Optional[PaymentGatewayConfig]:
    """
    Obtém a configuração ativa de um gateway específico.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        gateway_name (str): Nome do gateway ('stripe', 'mercado_pago')
        
    Returns:
        Optional[PaymentGatewayConfig]: Configuração do gateway ou None se não encontrada
    """
    result = await session.execute(
        select(PaymentGatewayConfig)
        .where(
            and_(
                PaymentGatewayConfig.gateway_name == gateway_name,
                PaymentGatewayConfig.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


async def create_or_update_gateway_config(
    session: AsyncSession,
    gateway_name: str,
    api_key: str,
    api_secret: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    additional_config: Optional[Dict] = None
) -> Tuple[bool, Optional[str], Optional[PaymentGatewayConfig]]:
    """
    Cria ou atualiza a configuração de um gateway de pagamento.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        gateway_name (str): Nome do gateway ('stripe', 'mercado_pago')
        api_key (str): Chave API do gateway
        api_secret (Optional[str]): Segredo da API (se aplicável)
        webhook_secret (Optional[str]): Segredo para validação de webhooks
        additional_config (Optional[Dict]): Configurações adicionais em formato dict
        
    Returns:
        Tuple[bool, Optional[str], Optional[PaymentGatewayConfig]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Configuração criada/atualizada (se sucesso)
    """
    # Validações básicas
    if not gateway_name or not api_key:
        return False, "Gateway name and API key are required", None
    
    if gateway_name not in ["stripe", "mercado_pago"]:
        return False, f"Unsupported gateway: {gateway_name}", None
    
    # Busca configuração existente
    result = await session.execute(
        select(PaymentGatewayConfig)
        .where(PaymentGatewayConfig.gateway_name == gateway_name)
    )
    config = result.scalar_one_or_none()
    
    # Converte configurações adicionais para JSON
    additional_config_json = None
    if additional_config:
        try:
            additional_config_json = json.dumps(additional_config)
        except Exception as e:
            return False, f"Error serializing additional config: {str(e)}", None
    
    # Cria nova configuração ou atualiza existente
    if not config:
        config = PaymentGatewayConfig(
            gateway_name=gateway_name,
            is_active=True,
            api_key=api_key,
            api_secret=api_secret,
            webhook_secret=webhook_secret,
            configuration=additional_config_json
        )
        session.add(config)
    else:
        # Desativa todas as configurações existentes para este gateway
        result = await session.execute(
            select(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.gateway_name == gateway_name)
        )
        existing_configs = result.scalars().all()
        
        for existing in existing_configs:
            existing.is_active = False
        
        # Cria nova configuração ativa
        config = PaymentGatewayConfig(
            gateway_name=gateway_name,
            is_active=True,
            api_key=api_key,
            api_secret=api_secret,
            webhook_secret=webhook_secret,
            configuration=additional_config_json
        )
        session.add(config)
    
    await session.commit()
    await session.refresh(config)
    
    return True, None, config


async def initialize_stripe_client(session: AsyncSession) -> Tuple[bool, Optional[str], Optional[Any]]:
    """
    Inicializa o cliente Stripe com as credenciais configuradas.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        
    Returns:
        Tuple[bool, Optional[str], Optional[stripe]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Cliente Stripe inicializado (se sucesso)
    """
    try:
        # Obtém configuração do Stripe
        config = await get_gateway_config(session, "stripe")
        if not config:
            return False, "Stripe configuration not found", None
        
        # Inicializa Stripe
        stripe.api_key = config.api_key
        
        return True, None, stripe
    except Exception as e:
        return False, f"Error initializing Stripe: {str(e)}", None


async def initialize_mercadopago_client(session: AsyncSession) -> Tuple[bool, Optional[str], Optional[Any]]:
    """
    Inicializa o cliente Mercado Pago com as credenciais configuradas.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        
    Returns:
        Tuple[bool, Optional[str], Optional[mercadopago.SDK]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Cliente Mercado Pago inicializado (se sucesso)
    """
    try:
        # Obtém configuração do Mercado Pago
        config = await get_gateway_config(session, "mercado_pago")
        if not config:
            return False, "Mercado Pago configuration not found", None
        
        # Inicializa Mercado Pago
        sdk = mercadopago.SDK(config.api_key)
        
        return True, None, sdk
    except Exception as e:
        return False, f"Error initializing Mercado Pago: {str(e)}", None


async def create_payment_intent_stripe(
    session: AsyncSession,
    order_id: int,
    amount: float,
    payment_method: str,
    customer_details: Dict
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Cria uma intenção de pagamento (payment intent) no Stripe.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        order_id (int): ID do pedido
        amount (float): Valor da transação
        payment_method (str): Método de pagamento
        customer_details (Dict): Detalhes do cliente
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Dados da intenção de pagamento (se sucesso)
    """
    # Inicializa o cliente Stripe
    success, error, stripe_client = await initialize_stripe_client(session)
    if not success:
        return False, error, None
    
    try:
        # Obtém o order para verificar detalhes
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return False, "Order not found", None
        
        # Converte o valor de reais para centavos (Stripe usa a menor unidade da moeda)
        amount_cents = int(amount * 100)
        
        # Cria o payment intent
        payment_intent = stripe_client.PaymentIntent.create(
            amount=amount_cents,
            currency="brl",
            payment_method_types=[payment_method],
            metadata={
                "order_id": order_id,
                "customer_id": order.user_id
            },
            receipt_email=customer_details.get("email")
        )
        
        # Registra a transação no banco
        transaction = PaymentTransaction(
            order_id=order_id,
            gateway="stripe",
            amount=amount,
            currency="BRL",
            gateway_transaction_id=payment_intent.id,
            status="pending",
            payment_method=payment_method,
            payment_details=json.dumps({
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "customer_details": customer_details
            })
        )
        
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        
        return True, None, {
            "transaction_id": transaction.id,
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "status": payment_intent.status
        }
        
    except Exception as e:
        return False, f"Error creating Stripe payment intent: {str(e)}", None


async def create_payment_mercadopago(
    session: AsyncSession,
    order_id: int,
    amount: float,
    payment_method: str,
    customer_details: Dict
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Cria um pagamento no Mercado Pago.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        order_id (int): ID do pedido
        amount (float): Valor da transação
        payment_method (str): Método de pagamento
        customer_details (Dict): Detalhes do cliente
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Dados do pagamento (se sucesso)
    """
    # Inicializa o cliente Mercado Pago
    success, error, mp_client = await initialize_mercadopago_client(session)
    if not success:
        return False, error, None
    
    try:
        # Obtém o order para verificar detalhes
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return False, "Order not found", None
        
        # Gera ID de referência único
        reference_id = str(uuid.uuid4())
        
        # Cria o pagamento
        preference_data = {
            "items": [
                {
                    "title": f"Pedido #{order_id}",
                    "quantity": 1,
                    "unit_price": amount
                }
            ],
            "payer": {
                "name": customer_details.get("name", ""),
                "email": customer_details.get("email", ""),
                "identification": {
                    "type": "CPF",
                    "number": customer_details.get("cpf", "")
                }
            },
            "payment_methods": {
                "excluded_payment_types": []
            },
            "external_reference": reference_id,
            "back_urls": {
                "success": f"{customer_details.get('base_url', 'http://localhost:8000')}/checkout/success",
                "failure": f"{customer_details.get('base_url', 'http://localhost:8000')}/checkout/failure",
                "pending": f"{customer_details.get('base_url', 'http://localhost:8000')}/checkout/pending"
            },
            "auto_return": "approved"
        }
        
        preference_result = mp_client.preference().create(preference_data)
        
        if "response" not in preference_result:
            return False, "Error creating Mercado Pago preference", None
        
        # Registra a transação no banco
        transaction = PaymentTransaction(
            order_id=order_id,
            gateway="mercado_pago",
            amount=amount,
            currency="BRL",
            gateway_transaction_id=preference_result["response"]["id"],
            status="pending",
            payment_method=payment_method,
            payment_details=json.dumps({
                "preference_id": preference_result["response"]["id"],
                "init_point": preference_result["response"]["init_point"],
                "reference_id": reference_id,
                "customer_details": customer_details
            })
        )
        
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        
        return True, None, {
            "transaction_id": transaction.id,
            "preference_id": preference_result["response"]["id"],
            "init_point": preference_result["response"]["init_point"],
            "status": "pending"
        }
        
    except Exception as e:
        return False, f"Error creating Mercado Pago payment: {str(e)}", None


async def process_payment_webhook_stripe(
    session: AsyncSession,
    webhook_data: Dict
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Processa um webhook recebido do Stripe para atualizar o status de pagamento.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        webhook_data (Dict): Dados do webhook
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Dados da transação processada (se sucesso)
    """
    try:
        # Obtém configuração do Stripe
        config = await get_gateway_config(session, "stripe")
        if not config:
            return False, "Stripe configuration not found", None
        
        # Verifica o tipo de evento
        event_type = webhook_data.get("type")
        
        # Processa apenas eventos de payment_intent
        if not event_type.startswith("payment_intent."):
            return True, "Event type not relevant for payment processing", None
        
        # Obtém o payment intent
        payment_intent = webhook_data.get("data", {}).get("object", {})
        payment_intent_id = payment_intent.get("id")
        
        if not payment_intent_id:
            return False, "Missing payment intent ID", None
        
        # Busca a transação correspondente
        result = await session.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.gateway_transaction_id == payment_intent_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return False, f"Transaction not found for payment intent {payment_intent_id}", None
        
        # Atualiza o status da transação com base no evento
        new_status = "pending"
        
        if event_type == "payment_intent.succeeded":
            new_status = "approved"
        elif event_type == "payment_intent.payment_failed":
            new_status = "refused"
        elif event_type == "payment_intent.canceled":
            new_status = "refused"
        
        # Atualiza a transação
        transaction.status = new_status
        transaction.updated_at = TIMEZONE()
        
        # Se o pagamento foi aprovado, processa o split e comissão
        if new_status == "approved":
            # Busca o pedido associado
            result = await session.execute(
                select(Order).where(Order.id == transaction.order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                # Busca informações de venda para afiliado, se existir
                result = await session.execute(
                    select(Sale).where(Sale.order_id == order.id)
                )
                sale = result.scalar_one_or_none()
                
                if sale:
                    # Atualiza o saldo do afiliado com a comissão da venda
                    await update_affiliate_balance_from_sale(session, sale.id)
        
        await session.commit()
        
        return True, None, {
            "transaction_id": transaction.id,
            "status": new_status,
            "payment_intent_id": payment_intent_id
        }
        
    except Exception as e:
        return False, f"Error processing Stripe webhook: {str(e)}", None


async def process_payment_webhook_mercadopago(
    session: AsyncSession,
    webhook_data: Dict
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Processa um webhook recebido do Mercado Pago para atualizar o status de pagamento.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        webhook_data (Dict): Dados do webhook
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Dados da transação processada (se sucesso)
    """
    try:
        # Inicializa o cliente Mercado Pago
        success, error, mp_client = await initialize_mercadopago_client(session)
        if not success:
            return False, error, None
        
        # Verifica o tipo de notificação
        if "type" not in webhook_data:
            return False, "Invalid webhook data: missing type", None
        
        # Processa apenas notificações de pagamento
        if webhook_data["type"] != "payment":
            return True, "Notification type not relevant for payment processing", None
        
        # Obtém ID do recurso (pagamento)
        if "data" not in webhook_data or "id" not in webhook_data["data"]:
            return False, "Invalid webhook data: missing resource ID", None
        
        payment_id = webhook_data["data"]["id"]
        
        # Obtém detalhes do pagamento via API
        payment_info = mp_client.payment().get(payment_id)
        
        if "response" not in payment_info:
            return False, "Failed to get payment information", None
        
        payment = payment_info["response"]
        
        # Obtém o ID de preferência (usado para associar à nossa transação)
        preference_id = payment.get("preference_id")
        if not preference_id:
            return False, "Missing preference ID in payment data", None
        
        # Busca a transação correspondente
        result = await session.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.gateway_transaction_id == preference_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return False, f"Transaction not found for preference {preference_id}", None
        
        # Atualiza o status da transação com base no status do pagamento
        new_status = "pending"
        
        if payment["status"] == "approved":
            new_status = "approved"
        elif payment["status"] == "rejected":
            new_status = "refused"
        elif payment["status"] == "cancelled":
            new_status = "refused"
        elif payment["status"] == "refunded":
            new_status = "refunded"
        
        # Adiciona informações do pagamento aos detalhes
        payment_details = json.loads(transaction.payment_details) if transaction.payment_details else {}
        payment_details["payment_id"] = payment_id
        payment_details["payment_status"] = payment["status"]
        payment_details["payment_status_detail"] = payment.get("status_detail")
        
        # Atualiza a transação
        transaction.status = new_status
        transaction.payment_details = json.dumps(payment_details)
        transaction.updated_at = TIMEZONE()
        
        # Se o pagamento foi aprovado, processa o split e comissão
        if new_status == "approved":
            # Busca o pedido associado
            result = await session.execute(
                select(Order).where(Order.id == transaction.order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                # Busca informações de venda para afiliado, se existir
                result = await session.execute(
                    select(Sale).where(Sale.order_id == order.id)
                )
                sale = result.scalar_one_or_none()
                
                if sale:
                    # Atualiza o saldo do afiliado com a comissão da venda
                    await update_affiliate_balance_from_sale(session, sale.id)
        
        await session.commit()
        
        return True, None, {
            "transaction_id": transaction.id,
            "status": new_status,
            "payment_id": payment_id
        }
        
    except Exception as e:
        return False, f"Error processing Mercado Pago webhook: {str(e)}", None


async def get_transaction_by_id(
    session: AsyncSession,
    transaction_id: int
) -> Optional[PaymentTransaction]:
    """
    Obtém uma transação de pagamento pelo ID.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        transaction_id (int): ID da transação
        
    Returns:
        Optional[PaymentTransaction]: Transação encontrada ou None
    """
    result = await session.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
    )
    return result.scalar_one_or_none()


async def get_transactions_by_order(
    session: AsyncSession,
    order_id: int
) -> List[PaymentTransaction]:
    """
    Obtém todas as transações de pagamento associadas a um pedido.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        order_id (int): ID do pedido
        
    Returns:
        List[PaymentTransaction]: Lista de transações do pedido
    """
    result = await session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
    )
    return result.scalars().all()


async def get_payment_transactions(
    session: AsyncSession,
    status: Optional[str] = None,
    gateway: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[PaymentTransaction], int]:
    """
    Obtém transações de pagamento com filtros e paginação.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        status (Optional[str]): Filtro por status
        gateway (Optional[str]): Filtro por gateway
        start_date (Optional[str]): Data inicial
        end_date (Optional[str]): Data final
        page (int): Página de resultados
        page_size (int): Tamanho da página
        
    Returns:
        Tuple[List[PaymentTransaction], int]:
            - Lista de transações
            - Total de transações
    """
    # Constrói a query base
    query = select(PaymentTransaction)
    
    # Aplica filtros
    if status:
        query = query.where(PaymentTransaction.status == status)
    
    if gateway:
        query = query.where(PaymentTransaction.gateway == gateway)
    
    if start_date:
        query = query.where(PaymentTransaction.created_at >= start_date)
    
    if end_date:
        query = query.where(PaymentTransaction.created_at <= end_date)
    
    # Conta o total
    count_query = select(func.count()).select_from(query.subquery())
    result = await session.execute(count_query)
    total_count = result.scalar_one()
    
    # Aplica paginação
    query = query.order_by(PaymentTransaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Executa a query
    result = await session.execute(query)
    transactions = result.scalars().all()
    
    return transactions, total_count 