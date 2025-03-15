# D:\3xDigital\app\tests\test_gateway_interface.py

"""
test_gateway_interface.py

Módulo de testes para a interface de gateway de pagamento (PaymentGatewayInterface).
Como é uma interface abstrata, testamos principalmente se ela funciona corretamente
como um contrato para implementações concretas.

Testes:
    - Verificação de métodos abstratos
    - Implementação concreta da interface
"""

import pytest
from typing import Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment.gateway_interface import PaymentGatewayInterface


class TestImplementation(PaymentGatewayInterface):
    """
    Implementação concreta da interface para testes.
    """
    
    async def initialize_client(self, session: AsyncSession) -> Tuple[bool, Optional[str], Optional[Any]]:
        return True, None, {"client": "test_client"}
        
    async def create_payment(
        self, 
        session: AsyncSession, 
        order_id: int, 
        amount: float, 
        payment_method: str, 
        customer_details: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        return True, None, {"payment_id": "test_payment"}
        
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
        return True, None, {"api_key": "test_key"}


def test_interface_contract():
    """
    Verifica se a interface funciona corretamente como contrato.
    
    Este teste confirma que:
    - Não é possível instanciar a interface diretamente
    - É possível criar e usar uma implementação concreta
    """
    # Não deve ser possível instanciar a interface diretamente
    with pytest.raises(TypeError):
        PaymentGatewayInterface()  # type: ignore
    
    # Deve ser possível criar uma implementação concreta
    implementation = TestImplementation()
    assert isinstance(implementation, PaymentGatewayInterface)


@pytest.mark.asyncio
async def test_implementation_methods(async_db_session):
    """
    Testa se os métodos da implementação concreta funcionam corretamente.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.
    """
    implementation = TestImplementation()
    
    # Testa initialize_client
    success, error, client = await implementation.initialize_client(async_db_session)
    assert success is True
    assert error is None
    assert client == {"client": "test_client"}
    
    # Testa create_payment
    success, error, payment = await implementation.create_payment(
        async_db_session, 
        order_id=1, 
        amount=100.0, 
        payment_method="credit_card", 
        customer_details={"name": "Test Customer"}
    )
    assert success is True
    assert error is None
    assert payment == {"payment_id": "test_payment"}
    
    # Testa process_webhook
    success, error, result = await implementation.process_webhook(
        async_db_session,
        webhook_data={"event": "payment.success"}
    )
    assert success is True
    assert error is None
    assert result == {"processed": True}
    
    # Testa get_gateway_config
    success, error, config = await implementation.get_gateway_config(async_db_session)
    assert success is True
    assert error is None
    assert config == {"api_key": "test_key"} 