# D:\3xDigital\app\services\payment_service.py
"""
payment_service.py

Módulo responsável pela coordenação dos serviços de pagamento, utilizando
diferentes gateways conforme necessário. Este serviço atua como uma fachada
para os diversos gateways de pagamento implementados.

Classes:
    PaymentService: Serviço central para processamento de pagamentos.
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance_models import PaymentGatewayConfig, PaymentTransaction
from app.models.database import Order, Affiliate, Sale
from app.services.payment.gateway_factory import PaymentGatewayFactory
from app.services.finance_service import update_affiliate_balance_from_sale
from app.config.settings import TIMEZONE


class PaymentService:
    """
    Serviço central para processamento de pagamentos.
    
    Esta classe fornece uma interface unificada para todas as operações relacionadas
    a pagamentos, independentemente do gateway utilizado. Ela atua como uma camada
    de abstração entre as views e as implementações específicas de gateway.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Inicializa o serviço de pagamento.
        
        Args:
            session (AsyncSession): Sessão do banco de dados para as operações.
        """
        self.session = session
    
    async def get_gateway_configs(self) -> List[Dict]:
        """
        Obtém todas as configurações de gateway ativas.
        
        Returns:
            List[Dict]: Lista de configurações de gateway.
        """
        result = await self.session.execute(
            select(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.is_active == True)
        )
        configs = result.scalars().all()
        
        return [
            {
                "id": config.id,
                "gateway_name": config.gateway_name,
                "is_active": config.is_active,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
            for config in configs
        ]
    
    async def get_gateway_config(self, gateway_name: str) -> Optional[Dict]:
        """
        Obtém a configuração de um gateway específico.
        
        Args:
            gateway_name (str): Nome do gateway.
            
        Returns:
            Optional[Dict]: Configuração do gateway ou None se não encontrado.
        """
        try:
            # Obtém o gateway apropriado
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            
            # Usa o método específico do gateway para obter configuração
            success, error, config = await gateway.get_gateway_config(self.session)
            
            if not success or config is None:
                print(f"Falha ao obter configuração do gateway {gateway_name}: {error}")
                return None
                
            # Adiciona o nome do gateway para consistência com os testes
            if "gateway_name" not in config:
                config["gateway_name"] = gateway_name
                
            return config
        except Exception as e:
            print(f"Erro ao obter configuração do gateway {gateway_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def create_or_update_gateway_config(
        self,
        gateway_name: str,
        api_key: str,
        api_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        additional_config: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str], Optional[PaymentGatewayConfig]]:
        """
        Cria ou atualiza a configuração de um gateway de pagamento.
        
        Args:
            gateway_name (str): Nome do gateway.
            api_key (str): Chave da API do gateway.
            api_secret (Optional[str]): Segredo da API, se aplicável.
            webhook_secret (Optional[str]): Segredo para validação de webhooks.
            additional_config (Optional[Dict]): Configurações adicionais.
            
        Returns:
            Tuple[bool, Optional[str], Optional[PaymentGatewayConfig]]:
                - Sucesso da operação
                - Mensagem de erro, se houver
                - Configuração criada/atualizada, se sucesso
        """
        try:
            # Verifica se já existe uma configuração para o gateway
            result = await self.session.execute(
                select(PaymentGatewayConfig)
                .where(PaymentGatewayConfig.gateway_name == gateway_name)
            )
            config = result.scalars().first()
            
            if config:
                # Atualiza configuração existente
                config.api_key = api_key
                if api_secret:
                    config.api_secret = api_secret
                if webhook_secret:
                    config.webhook_secret = webhook_secret
                if additional_config:
                    config.configuration = json.dumps(additional_config)
                
                config.is_active = True
            else:
                # Cria nova configuração
                config = PaymentGatewayConfig(
                    gateway_name=gateway_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    webhook_secret=webhook_secret,
                    configuration=json.dumps(additional_config) if additional_config else None,
                    is_active=True
                )
                self.session.add(config)
            
            await self.session.commit()
            await self.session.refresh(config)
            
            return True, None, config
        except Exception as e:
            await self.session.rollback()
            return False, f"Erro ao configurar gateway: {str(e)}", None
    
    async def process_payment(
        self,
        gateway_name: str,
        order_id: int,
        amount: float,
        payment_method: str,
        customer_details: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Processa um pagamento utilizando o gateway especificado.
        
        Args:
            gateway_name (str): Nome do gateway a ser utilizado.
            order_id (int): ID do pedido.
            amount (float): Valor a ser cobrado.
            payment_method (str): Método de pagamento.
            customer_details (Dict): Detalhes do cliente.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]:
                - Sucesso da operação
                - Mensagem de erro, se houver
                - Dados do pagamento criado, se sucesso
        """
        try:
            # Obtém o gateway apropriado
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            
            # Inicializa o cliente do gateway
            init_success, init_error, client = await gateway.initialize_client(self.session)
            if not init_success:
                print(f"Falha ao inicializar cliente do gateway {gateway_name}: {init_error}")
                return False, f"Falha ao inicializar gateway: {init_error}", None
            
            # Usa o método específico do gateway para processar pagamento
            success, error, payment_data = await gateway.create_payment(
                self.session,
                order_id,
                amount,
                payment_method,
                customer_details
            )
            
            if not success:
                print(f"Falha ao processar pagamento com {gateway_name}: {error}")
                return False, error, None
                
            return True, None, payment_data
        except ValueError as e:
            print(f"Valor inválido ao processar pagamento: {str(e)}")
            return False, str(e), None
        except Exception as e:
            print(f"Erro ao processar pagamento: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Erro ao processar pagamento: {str(e)}", None
    
    async def process_webhook(
        self,
        gateway_name: str,
        webhook_data: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Processa um webhook recebido de um gateway de pagamento.
        
        Args:
            gateway_name (str): Nome do gateway que enviou o webhook.
            webhook_data (Dict): Dados do webhook.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]:
                - Sucesso da operação
                - Mensagem de erro, se houver
                - Resultado do processamento, se sucesso
        """
        try:
            # Obtém o gateway apropriado
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            
            # Inicializa o cliente do gateway
            init_success, init_error, client = await gateway.initialize_client(self.session)
            if not init_success:
                print(f"Falha ao inicializar cliente do gateway {gateway_name}: {init_error}")
                return False, f"Falha ao inicializar gateway: {init_error}", None
            
            # Usa o método específico do gateway para processar webhook
            success, error, webhook_result = await gateway.process_webhook(self.session, webhook_data)
            
            if not success:
                print(f"Falha ao processar webhook com {gateway_name}: {error}")
                return False, error, None
                
            return True, None, webhook_result
        except ValueError as e:
            print(f"Valor inválido ao processar webhook: {str(e)}")
            return False, str(e), None
        except Exception as e:
            print(f"Erro ao processar webhook: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Erro ao processar webhook: {str(e)}", None
    
    async def get_transaction_by_id(
        self,
        transaction_id: int
    ) -> Optional[PaymentTransaction]:
        """
        Obtém uma transação pelo ID.
        
        Args:
            transaction_id (int): ID da transação.
            
        Returns:
            Optional[PaymentTransaction]: Transação encontrada ou None.
        """
        result = await self.session.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.id == transaction_id)
        )
        return result.scalars().first()
    
    async def get_transactions_by_order(
        self,
        order_id: int
    ) -> List[PaymentTransaction]:
        """
        Obtém todas as transações relacionadas a um pedido.
        
        Args:
            order_id (int): ID do pedido.
            
        Returns:
            List[PaymentTransaction]: Lista de transações.
        """
        result = await self.session.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.order_id == order_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_payment_transactions(
        self,
        status: Optional[str] = None,
        gateway: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[PaymentTransaction], int]:
        """
        Obtém transações de pagamento com filtros.
        
        Args:
            status (Optional[str]): Filtro por status.
            gateway (Optional[str]): Filtro por gateway.
            start_date (Optional[str]): Data de início para filtro.
            end_date (Optional[str]): Data de fim para filtro.
            page (int): Página para paginação.
            page_size (int): Tamanho da página.
            
        Returns:
            Tuple[List[PaymentTransaction], int]:
                - Lista de transações
                - Contagem total de transações que atendem aos filtros
        """
        query = select(PaymentTransaction)
        
        # Aplicar filtros
        filters = []
        if status:
            filters.append(PaymentTransaction.status == status)
        if gateway:
            filters.append(PaymentTransaction.gateway == gateway)
        if start_date:
            filters.append(PaymentTransaction.created_at >= start_date)
        if end_date:
            filters.append(PaymentTransaction.created_at <= end_date)
            
        if filters:
            query = query.where(and_(*filters))
            
        # Ordenar por data de criação (mais recentes primeiro)
        query = query.order_by(PaymentTransaction.created_at.desc())
        
        # Executar query para contagem total
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.session.scalar(count_query)
        
        # Aplicar paginação
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Executar query final
        result = await self.session.execute(query)
        transactions = result.scalars().all()
        
        return transactions, total_count 