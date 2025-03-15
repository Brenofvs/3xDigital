# D:\3xDigital\app\services\payment\gateway_interface.py

"""
gateway_interface.py

Módulo que define a interface base para todos os gateways de pagamento.
Esta interface funciona como um contrato que todas as implementações
específicas de gateway devem seguir, garantindo consistência entre
diferentes provedores de pagamento.

Classes:
    PaymentGatewayInterface: Interface abstrata base para gateways de pagamento.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

class PaymentGatewayInterface(ABC):
    """
    Interface abstrata base para implementações de gateway de pagamento.
    
    Cada gateway de pagamento (Stripe, Mercado Pago, etc.) deve implementar
    esta interface para garantir compatibilidade com o sistema.
    """
    
    @abstractmethod
    async def initialize_client(self, session: AsyncSession) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Inicializa o cliente do gateway de pagamento com as configurações necessárias.
        
        Args:
            session (AsyncSession): Sessão do banco de dados para obter configurações.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Any]]: 
                - Sucesso da operação (bool)
                - Mensagem de erro, se houver (str ou None)
                - Cliente inicializado ou qualquer outro dado relevante (Any ou None)
        """
        pass
        
    @abstractmethod
    async def create_payment(
        self, 
        session: AsyncSession, 
        order_id: int, 
        amount: float, 
        payment_method: str, 
        customer_details: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Cria uma intenção/requisição de pagamento no gateway.
        
        Args:
            session (AsyncSession): Sessão do banco de dados.
            order_id (int): ID do pedido associado ao pagamento.
            amount (float): Valor a ser cobrado.
            payment_method (str): Método de pagamento (cartão, boleto, etc).
            customer_details (Dict): Detalhes do cliente para o pagamento.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]:
                - Sucesso da operação (bool)
                - Mensagem de erro, se houver (str ou None)
                - Detalhes do pagamento criado (Dict ou None)
        """
        pass
        
    @abstractmethod
    async def process_webhook(
        self, 
        session: AsyncSession, 
        webhook_data: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Processa webhooks recebidos do gateway de pagamento.
        
        Args:
            session (AsyncSession): Sessão do banco de dados.
            webhook_data (Dict): Dados recebidos no webhook.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]:
                - Sucesso da operação (bool)
                - Mensagem de erro, se houver (str ou None)
                - Detalhes do processamento do webhook (Dict ou None)
        """
        pass
        
    @abstractmethod
    async def get_gateway_config(
        self,
        session: AsyncSession
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Obtém as configurações do gateway armazenadas no banco de dados.
        
        Args:
            session (AsyncSession): Sessão do banco de dados.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]:
                - Sucesso da operação (bool)
                - Mensagem de erro, se houver (str ou None)
                - Configurações do gateway (Dict ou None)
        """
        pass 