# D:\3xDigital\app\tests\test_user_service.py

"""
test_user_service.py

Módulo de testes para o serviço de usuários (user_service.py).
Testa as operações relacionadas a gerenciamento de usuários, autenticação,
e funcionalidades de perfil como atualização de dados pessoais, troca de
senha e gerenciamento de email.

Testes:
    - Obtenção de detalhes do usuário
    - Atualização de dados do perfil
    - Alteração de senha
    - Atualização de email
    - Desativação e reativação de conta
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest import mock
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import (
    get_user_details, update_user_profile_data, change_password, 
    update_user_email, deactivate_user_account, list_users,
    update_user_role, reset_user_password, request_account_deletion
)
from app.models.database import User, Affiliate, UserAddress


@pytest_asyncio.fixture
async def user_test_data(async_db_session):
    """
    Configura dados de teste para as operações de usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de teste para as operações de usuário.
    """
    # Cria um usuário normal
    hashed_password = bcrypt.hashpw("testpass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user = User(
        name="Usuário de Teste",
        email="user_teste@example.com",
        password_hash=hashed_password,
        cpf="12345678901",
        role="user",
        phone="11999887766",
        created_at=datetime.now(),
        active=True
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    # Adiciona endereço ao usuário
    user_address = UserAddress(
        user_id=user.id,
        street="Rua de Teste",
        number="123",
        city="São Paulo",
        state="SP",
        zip_code="01234-567"
    )
    async_db_session.add(user_address)
    await async_db_session.commit()
    
    # Cria um usuário afiliado
    affiliate_user = User(
        name="Afiliado de Teste",
        email="afiliado_teste@example.com",
        password_hash=hashed_password,
        cpf="98765432109",
        role="affiliate",
        phone="11988776655",
        created_at=datetime.now(),
        active=True
    )
    async_db_session.add(affiliate_user)
    await async_db_session.commit()
    await async_db_session.refresh(affiliate_user)

    # Adiciona endereço ao afiliado
    affiliate_address = UserAddress(
        user_id=affiliate_user.id,
        street="Rua do Afiliado",
        number="456",
        city="São Paulo",
        state="SP",
        zip_code="04567-890"
    )
    async_db_session.add(affiliate_address)
    await async_db_session.commit()
    
    # Cria registro de afiliado para o usuário afiliado
    affiliate = Affiliate(
        user_id=affiliate_user.id,
        commission_rate=10.0,
        payment_info={"bank": "Banco Teste", "agency": "1234", "account": "56789-0"},
        request_status="approved",
        referral_code="TESTREF123",
        created_at=datetime.now()
    )
    async_db_session.add(affiliate)
    await async_db_session.commit()
    
    # Cria um usuário admin
    admin_user = User(
        name="Admin de Teste",
        email="admin_teste@example.com",
        password_hash=hashed_password,
        cpf="11122233344",
        role="admin",
        phone="11977665544",
        created_at=datetime.now(),
        active=True
    )
    async_db_session.add(admin_user)
    await async_db_session.commit()
    await async_db_session.refresh(admin_user)

    # Adiciona endereço ao admin
    admin_address = UserAddress(
        user_id=admin_user.id,
        street="Rua do Admin",
        number="789",
        city="São Paulo",
        state="SP",
        zip_code="07890-123"
    )
    async_db_session.add(admin_address)
    await async_db_session.commit()
    
    # Cria um usuário inativo (desativado)
    inactive_user = User(
        name="Usuário Inativo",
        email="inativo_teste@example.com",
        password_hash=hashed_password,
        cpf="55566677788",
        role="user",
        phone="11966554433",
        created_at=datetime.now(),
        active=False,
        deactivation_reason="Conta de teste desativada"
    )
    async_db_session.add(inactive_user)
    await async_db_session.commit()
    await async_db_session.refresh(inactive_user)
    
    return {
        "user": user,
        "affiliate_user": affiliate_user,
        "admin_user": admin_user,
        "inactive_user": inactive_user,
        "plain_password": "testpass123"
    }


@pytest.mark.asyncio
async def test_get_user_details(async_db_session, user_test_data):
    """
    Testa a obtenção de detalhes do usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    # Obtém detalhes de um usuário normal
    user = user_test_data["user"]
    user_details = await get_user_details(async_db_session, user.id)
    
    assert user_details is not None
    assert user_details["id"] == user.id
    assert user_details["name"] == user.name
    assert user_details["email"] == user.email
    assert user_details["role"] == user.role
    assert "password" not in user_details  # Não deve retornar senha
    assert "affiliate" not in user_details or user_details["affiliate"] is None  # Usuário normal não tem info de afiliado
    
    # Obtém detalhes de um usuário afiliado
    affiliate_user = user_test_data["affiliate_user"]
    affiliate_details = await get_user_details(async_db_session, affiliate_user.id)
    
    assert affiliate_details is not None
    assert affiliate_details["id"] == affiliate_user.id
    assert affiliate_details["role"] == "affiliate"
    assert "affiliate" in affiliate_details and affiliate_details["affiliate"] is not None
    assert affiliate_details["affiliate"]["commission_rate"] == 10.0
    
    # Tenta obter usuário inexistente
    non_existent = await get_user_details(async_db_session, 9999)
    assert non_existent is None


@pytest.mark.asyncio
async def test_update_user_profile_data(async_db_session, user_test_data):
    """
    Testa a atualização de dados do perfil do usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    user = user_test_data["user"]
    
    # Dados para atualização
    update_data = {
        "name": "Nome Atualizado",
        "phone": "11944332211",
        "address": {
            "street": "Nova Rua de Teste",
            "number": "456",
            "neighborhood": "Bairro Teste",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "04567-890"
        }
    }
    
    # Atualiza o perfil do usuário
    success, error, updated_user = await update_user_profile_data(async_db_session, user.id, update_data)
    
    assert success is True
    assert error is None
    assert updated_user is not None
    assert updated_user["name"] == update_data["name"]
    assert updated_user["phone"] == update_data["phone"]
    assert updated_user["address"]["street"] == update_data["address"]["street"]
    assert updated_user["address"]["number"] == update_data["address"]["number"]
    
    # Verifica persistência consultando o banco
    query = select(User).where(User.id == user.id)
    result = await async_db_session.execute(query)
    db_user = result.scalar_one()
    
    assert db_user.name == update_data["name"]
    assert db_user.phone == update_data["phone"]
    
    # Verifica o endereço no banco
    query = select(UserAddress).where(UserAddress.user_id == user.id)
    result = await async_db_session.execute(query)
    db_address = result.scalar_one()
    
    assert db_address.street == update_data["address"]["street"]
    assert db_address.number == update_data["address"]["number"]
    
    # Tenta atualizar usuário inexistente
    success, error, non_existent = await update_user_profile_data(async_db_session, 9999, update_data)
    assert success is False
    assert error is not None
    assert "Usuário não encontrado" in error
    
    # Tenta atualizar campos restritos (não deve alterar)
    restricted_data = {
        "name": "Outro Nome",
        "email": "novo_email@example.com",  # Não deve ser atualizado por essa função
        "role": "admin"  # Não deve ser atualizado por essa função
    }
    
    success, error, restricted_updated = await update_user_profile_data(async_db_session, user.id, restricted_data)
    
    assert success is True
    assert restricted_updated is not None
    assert restricted_updated["name"] == "Outro Nome"  # Nome deve ser atualizado
    assert restricted_updated["email"] != "novo_email@example.com"  # Email não deve ser atualizado
    assert restricted_updated["role"] != "admin"  # Role não deve ser atualizado


@pytest.mark.asyncio
async def test_change_password(async_db_session, user_test_data):
    """
    Testa a alteração de senha do usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    user = user_test_data["user"]
    current_password = user_test_data["plain_password"]
    new_password = "NovoPass@123"
    
    # Troca a senha com sucesso
    result, message = await change_password(
        async_db_session, 
        user.id, 
        current_password, 
        new_password
    )
    
    assert result is True
    assert message is None or "sucesso" in message.lower()
    
    # Verifica se a senha foi alterada
    query = select(User).where(User.id == user.id)
    result = await async_db_session.execute(query)
    db_user = result.scalar_one()
    
    # Verifica se o hash da senha corresponde à nova senha
    assert bcrypt.checkpw(new_password.encode('utf-8'), db_user.password_hash.encode('utf-8'))
    
    # Tenta alterar com senha atual incorreta
    result, message = await change_password(
        async_db_session, 
        user.id, 
        "senhaErrada", 
        "OutraSenha@456"
    )
    
    assert result is False
    assert message is not None
    assert "atual" in message.lower() or "incorreta" in message.lower()  # Menção à senha atual incorreta
    
    # Tenta alterar senha de usuário inexistente
    result, message = await change_password(
        async_db_session, 
        9999, 
        current_password, 
        new_password
    )
    
    assert result is False
    assert message is not None
    assert "encontrado" in message.lower()  # Usuário não encontrado


@pytest.mark.asyncio
async def test_update_user_email(async_db_session, user_test_data):
    """
    Testa a atualização do email do usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    user = user_test_data["user"]
    # Usamos a senha original em vez de depender do teste anterior
    current_password = user_test_data["plain_password"]
    new_email = "novo_email_teste@example.com"
    
    # Atualiza o email com sucesso
    result, message = await update_user_email(
        async_db_session,
        user.id,
        current_password,
        new_email
    )
    
    assert result is True
    assert message is None or "sucesso" in message.lower()
    
    # Verifica se o email foi alterado no banco de dados
    query = select(User).where(User.id == user.id)
    result = await async_db_session.execute(query)
    db_user = result.scalar_one()
    
    assert db_user.email == new_email
    
    # Tenta atualizar com senha incorreta
    result, message = await update_user_email(
        async_db_session,
        user.id,
        "senhaErrada",
        "outro_email@example.com"
    )
    
    assert result is False
    assert message is not None
    assert "senha" in message.lower()  # Menção à senha incorreta
    
    # Tenta atualizar para um email já existente
    existing_email = user_test_data["affiliate_user"].email
    
    result, message = await update_user_email(
        async_db_session,
        user.id,
        current_password,
        existing_email
    )
    
    assert result is False
    assert message is not None
    assert "já está em uso" in message.lower() or "já existe" in message.lower()  # Email já em uso
    
    # Tenta atualizar email de usuário inexistente
    result, message = await update_user_email(
        async_db_session,
        9999,
        current_password,
        "email_inexistente@example.com"
    )
    
    assert result is False
    assert message is not None
    assert "encontrado" in message.lower()  # Usuário não encontrado


@pytest.mark.asyncio
async def test_deactivate_user_account(async_db_session, user_test_data):
    """
    Testa a desativação da conta do usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    # Vamos usar o usuário admin para evitar conflitos com outros testes
    admin_user = user_test_data["admin_user"]
    current_password = user_test_data["plain_password"]  # Usa a senha original
    
    # Desativa a conta com sucesso
    result, message = await deactivate_user_account(
        async_db_session,
        admin_user.id,
        current_password
    )
    
    assert result is True
    assert message is None or "desativada" in message.lower()
    
    # Verifica se a conta foi desativada no banco de dados
    query = select(User).where(User.id == admin_user.id)
    result = await async_db_session.execute(query)
    db_user = result.scalar_one()
    
    assert db_user.is_active is False
    
    # Tenta desativar conta com senha incorreta
    affiliate_user = user_test_data["affiliate_user"]
    
    result, message = await deactivate_user_account(
        async_db_session,
        affiliate_user.id,
        "senhaErrada"
    )
    
    assert result is False
    assert message is not None
    assert "senha" in message.lower()  # Menção à senha incorreta
    
    # Tenta desativar conta de usuário já inativo
    result, message = await deactivate_user_account(
        async_db_session,
        admin_user.id,  # Agora esse usuário já está inativo
        current_password
    )
    
    assert result is False
    assert message is not None
    assert "já está desativada" in message.lower()
    
    # Tenta desativar conta de usuário inexistente
    result, message = await deactivate_user_account(
        async_db_session,
        9999,
        "qualquersenha"
    )
    
    assert result is False
    assert message is not None
    assert "encontrado" in message.lower()  # Usuário não encontrado


@pytest.mark.asyncio
async def test_list_users(async_db_session, user_test_data):
    """
    Testa a listagem de usuários com filtros.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    # Lista todos os usuários
    users, total = await list_users(async_db_session)
    assert total >= 4  # Pelo menos os 4 usuários criados na fixture
    assert len(users) >= 4
    
    # Filtra por papel (role)
    admin_users, admin_total = await list_users(async_db_session, role="admin")
    assert admin_total >= 1
    assert all(u.role == "admin" for u in admin_users)
    
    # Busca por termo
    search_users, search_total = await list_users(async_db_session, search_term="Afiliado")
    assert search_total >= 1
    assert any("Afiliado" in u.name for u in search_users)
    
    # Testa paginação
    page1_users, page1_total = await list_users(async_db_session, page=1, page_size=2)
    assert page1_total >= 4  # Total continua sendo pelo menos 4
    assert len(page1_users) == 2  # Mas só retorna 2 por página


@pytest.mark.asyncio
async def test_update_user_role(async_db_session, user_test_data):
    """
    Testa a atualização do papel (role) de um usuário.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    admin_user = user_test_data["admin_user"]
    user = user_test_data["user"]
    
    # Atualiza o papel do usuário
    success, error = await update_user_role(
        async_db_session,
        user.id,
        "affiliate",
        admin_user.id
    )
    
    assert success is True
    assert error is None
    
    # Verifica se o papel foi atualizado
    query = select(User).where(User.id == user.id)
    result = await async_db_session.execute(query)
    updated_user = result.scalar_one()
    
    assert updated_user.role == "affiliate"
    
    # Tenta atualizar para um papel inválido
    success, error = await update_user_role(
        async_db_session,
        user.id,
        "invalid_role",
        admin_user.id
    )
    
    assert success is False
    assert error is not None
    assert "inválido" in error.lower()
    
    # Tenta atualizar o próprio papel (não deve ser permitido)
    success, error = await update_user_role(
        async_db_session,
        admin_user.id,
        "user",
        admin_user.id
    )
    
    assert success is False
    assert error is not None
    assert "próprio papel" in error.lower()


@pytest.mark.asyncio
async def test_reset_user_password(async_db_session, user_test_data):
    """
    Testa a redefinição de senha de um usuário por um administrador.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    admin_user = user_test_data["admin_user"]
    user = user_test_data["user"]
    new_password = "SenhaRedefinida@123"
    
    # Redefine a senha do usuário
    success, error = await reset_user_password(
        async_db_session,
        user.id,
        new_password,
        admin_user.id
    )
    
    assert success is True
    assert error is None
    
    # Verifica se a senha foi atualizada
    query = select(User).where(User.id == user.id)
    result = await async_db_session.execute(query)
    updated_user = result.scalar_one()
    
    assert bcrypt.checkpw(new_password.encode('utf-8'), updated_user.password_hash.encode('utf-8'))
    
    # Tenta definir uma senha muito curta
    success, error = await reset_user_password(
        async_db_session,
        user.id,
        "short",
        admin_user.id
    )
    
    assert success is False
    assert error is not None
    assert "caracteres" in error.lower()


@pytest.mark.asyncio
async def test_request_account_deletion(async_db_session, user_test_data):
    """
    Testa a solicitação de exclusão de conta.
    
    Args:
        async_db_session: Sessão de banco de dados assíncrona para testes.
        user_test_data: Fixture com dados de teste para usuários.
    """
    # Usamos o usuário affiliate para este teste
    affiliate_user = user_test_data["affiliate_user"]
    current_password = user_test_data["plain_password"]  # Usa a senha original
    reason = "Teste de solicitação de exclusão"
    
    # Solicita exclusão de conta
    success, error = await request_account_deletion(
        async_db_session,
        affiliate_user.id,
        current_password,
        reason
    )
    
    assert success is True
    assert error is None
    
    # Verifica se a solicitação foi registrada
    query = select(User).where(User.id == affiliate_user.id)
    result = await async_db_session.execute(query)
    updated_user = result.scalar_one()
    
    assert updated_user.deletion_requested is True
    assert updated_user.deletion_request_date is not None
    
    # Tenta solicitar novamente (já existe uma solicitação)
    success, error = await request_account_deletion(
        async_db_session,
        affiliate_user.id,
        current_password,
        reason
    )
    
    assert success is False
    assert error is not None
    assert "já existe" in error.lower()
    
    # Tenta solicitar com senha incorreta
    user = user_test_data["user"]
    success, error = await request_account_deletion(
        async_db_session,
        user.id,
        "senhaErrada",
        reason
    )
    
    assert success is False
    assert error is not None
    assert "senha" in error.lower() 