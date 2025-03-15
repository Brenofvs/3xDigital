"""
test_gateway_factory.py

Módulo de testes para a factory de gateways de pagamento (PaymentGatewayFactory).
Valida se a factory consegue registrar e fornecer implementações de gateway
corretamente.

Testes:
    - Obtenção de gateways existentes
    - Erro ao solicitar gateway não registrado
    - Registro de novos gateways
    - Lista de gateways suportados
"""

import pytest
from typing import Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment.gateway_interface import PaymentGatewayInterface
from app.services.payment.gateway_factory import PaymentGatewayFactory
from app.services.payment.stripe_gateway import StripeGateway
from app.services.payment.mercadopago_gateway import MercadoPagoGateway


class CustomGateway(PaymentGatewayInterface):
    """
    Implementação de gateway personalizada para testes.
    """
    
    async def initialize_client(self, session: AsyncSession) -> Tuple[bool, Optional[str], Optional[Any]]:
        return True, None, {"client": "custom_client"}
        
    async def create_payment(
        self, 
        session: AsyncSession, 
        order_id: int, 
        amount: float, 
        payment_method: str, 
        customer_details: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        return True, None, {"payment_id": "custom_payment"}
        
    async def process_webhook(
        self, 
        session: AsyncSession, 
        webhook_data: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        return True, None, {"processed": True}
        
    async def get_gateway_config(
        self,
        session: AsyncSession
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        return True, None, {"api_key": "custom_key"}


def test_get_existing_gateway():
    """
    Testa a obtenção de gateways existentes.
    
    Verifica se a factory retorna as implementações corretas para
    gateways registrados por padrão (Stripe e Mercado Pago).
    """
    # Obtém gateway Stripe
    stripe_gateway = PaymentGatewayFactory.get_gateway("stripe")
    assert isinstance(stripe_gateway, StripeGateway)
    
    # Obtém gateway Mercado Pago
    mp_gateway = PaymentGatewayFactory.get_gateway("mercado_pago")
    assert isinstance(mp_gateway, MercadoPagoGateway)
    
    # Verifica case insensitive
    stripe_upper = PaymentGatewayFactory.get_gateway("STRIPE")
    assert isinstance(stripe_upper, StripeGateway)


def test_get_nonexistent_gateway():
    """
    Testa o comportamento ao solicitar um gateway não registrado.
    
    Verifica se a factory levanta a exceção apropriada quando um
    gateway não suportado é solicitado.
    """
    with pytest.raises(ValueError) as exc_info:
        PaymentGatewayFactory.get_gateway("nonexistent_gateway")
    
    assert "Gateway não suportado" in str(exc_info.value)


def test_register_new_gateway():
    """
    Testa o registro de um novo gateway na factory.
    
    Verifica se é possível registrar e usar uma nova implementação
    de gateway que não estava disponível originalmente.
    """
    # Registra um novo gateway
    PaymentGatewayFactory.register_gateway("custom", CustomGateway)
    
    # Obtém o gateway registrado
    custom_gateway = PaymentGatewayFactory.get_gateway("custom")
    assert isinstance(custom_gateway, CustomGateway)
    
    # Limpa o registro para não afetar outros testes
    PaymentGatewayFactory._GATEWAYS.pop("custom", None)


def test_register_invalid_gateway():
    """
    Testa o comportamento ao tentar registrar uma classe que não implementa
    a interface PaymentGatewayInterface.
    """
    class InvalidClass:
        pass
    
    with pytest.raises(TypeError) as exc_info:
        PaymentGatewayFactory.register_gateway("invalid", InvalidClass)
    
    assert "deve implementar PaymentGatewayInterface" in str(exc_info.value)


def test_get_supported_gateways():
    """
    Testa a obtenção da lista de gateways suportados.
    
    Verifica se o método retorna corretamente todos os gateways
    registrados na factory.
    """
    gateways = PaymentGatewayFactory.get_supported_gateways()
    
    assert isinstance(gateways, dict)
    assert "stripe" in gateways
    assert "mercado_pago" in gateways
    assert gateways["stripe"] == StripeGateway
    assert gateways["mercado_pago"] == MercadoPagoGateway 