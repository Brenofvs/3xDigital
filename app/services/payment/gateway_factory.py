# D:\3xDigital\app\services\payment\gateway_factory.py

"""
gateway_factory.py

Este módulo fornece uma factory para selecionar a implementação de gateway
de pagamento apropriada, com base no nome do gateway solicitado.

Classes:
    PaymentGatewayFactory: Factory para criação de instâncias de gateway de pagamento.
"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .gateway_interface import PaymentGatewayInterface
from .stripe_gateway import StripeGateway
from .mercadopago_gateway import MercadoPagoGateway


class PaymentGatewayFactory:
    """
    Factory para criar instâncias de gateways de pagamento.
    
    Esta classe facilita a obtenção de implementações específicas de gateway
    com base no nome do gateway solicitado, sem que o código cliente precise
    conhecer os detalhes de implementação de cada gateway.
    """
    
    # Registra os gateways suportados
    _GATEWAYS = {
        "stripe": StripeGateway,
        "mercado_pago": MercadoPagoGateway
    }
    
    @classmethod
    def get_gateway(cls, gateway_name: str) -> Optional[PaymentGatewayInterface]:
        """
        Retorna uma instância de gateway de pagamento com base no nome.
        
        Args:
            gateway_name (str): Nome do gateway a ser instanciado 
                               ('stripe', 'mercado_pago', etc.)
            
        Returns:
            Optional[PaymentGatewayInterface]: Instância do gateway ou None se 
                                              o gateway solicitado não for suportado.
                                              
        Raises:
            ValueError: Se o gateway solicitado não for suportado.
        """
        gateway_class = cls._GATEWAYS.get(gateway_name.lower())
        
        if not gateway_class:
            raise ValueError(f"Gateway não suportado: {gateway_name}")
            
        return gateway_class()
    
    @classmethod
    def register_gateway(cls, gateway_name: str, gateway_class: type) -> None:
        """
        Registra um novo tipo de gateway na factory.
        
        Esta função permite que novas implementações de gateway sejam registradas
        dinamicamente, facilitando a extensibilidade do sistema.
        
        Args:
            gateway_name (str): Nome do gateway a ser registrado.
            gateway_class (type): Classe que implementa PaymentGatewayInterface.
            
        Raises:
            TypeError: Se a classe fornecida não implementar PaymentGatewayInterface.
        """
        # Verifica se a classe implementa a interface
        if not issubclass(gateway_class, PaymentGatewayInterface):
            raise TypeError(
                f"A classe {gateway_class.__name__} deve implementar PaymentGatewayInterface"
            )
            
        cls._GATEWAYS[gateway_name.lower()] = gateway_class
        
    @classmethod
    def get_supported_gateways(cls) -> Dict[str, type]:
        """
        Retorna um dicionário com todos os gateways suportados.
        
        Returns:
            Dict[str, type]: Dicionário com os nomes dos gateways como chaves
                            e as classes correspondentes como valores.
        """
        return dict(cls._GATEWAYS) 