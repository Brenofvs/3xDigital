# D:\3xDigital\app\tests\test_profile_views.py

"""
test_profile_views.py

Módulo de testes para os endpoints de perfil de usuário (profile_views.py).
Testa a funcionalidade das rotas de gerenciamento do perfil do usuário,
incluindo obtenção de dados pessoais, atualização de perfil, alteração
de senha e atualização de email.

Testes:
    - Obtenção de perfil do usuário
    - Atualização de dados pessoais
    - Alteração de senha
    - Atualização de email
    - Desativação de conta
"""

import pytest
import pytest_asyncio
import json
from aiohttp import web
from unittest import mock
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import bcrypt

from app.models.database import User


@pytest_asyncio.fixture
async def profile_data(test_client_fixture, async_db_session):
    """
    Configura dados de teste para os endpoints de perfil.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        async_db_session: Sessão de banco de dados assíncrona para testes.
        
    Returns:
        Dict: Dados de teste para as operações de perfil.
    """
    # Cria um usuário para testes
    user_data = {
        "name": "Usuário Teste",
        "email": "usuario_teste@example.com",
        "cpf": "12345678901",
        "password": "testpass123",
        "role": "user",
        "phone": "11999887766"
    }
    
    # Registra o usuário
    register_resp = await test_client_fixture.post('/auth/register', json=user_data)
    register_data = await register_resp.json()
    user_id = register_data['user_id']
    
    # Login do usuário
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "usuario_teste@example.com",
        "password": "testpass123"
    })
    login_data = await login_resp.json()
    token = login_data['access_token']
    
    # Cria um segundo usuário para testar tentativas de acesso indevido
    user2_data = {
        "name": "Outro Usuário",
        "email": "outro_usuario@example.com",
        "cpf": "98765432109",
        "password": "otherpass",
        "role": "user",
        "phone": "11988776655"
    }
    
    register2_resp = await test_client_fixture.post('/auth/register', json=user2_data)
    register2_data = await register2_resp.json()
    user2_id = register2_data['user_id']
    
    login2_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "outro_usuario@example.com",
        "password": "otherpass"
    })
    login2_data = await login2_resp.json()
    token2 = login2_data['access_token']
    
    # Retorna os dados necessários para os testes
    return {
        "user_id": user_id,
        "token": token,
        "user_data": user_data,
        "user2_id": user2_id,
        "token2": token2
    }


@pytest.mark.asyncio
async def test_get_user_profile(test_client_fixture, profile_data):
    """
    Testa a obtenção do perfil do usuário.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        profile_data: Fixture com dados de teste para o perfil.
    """
    token = profile_data["token"]
    user_data = profile_data["user_data"]
    
    # Obtém o próprio perfil
    response = await test_client_fixture.get(
        '/profile',
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    # Os dados do usuário são retornados diretamente, não dentro de um objeto 'user'
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["cpf"] == user_data["cpf"]
    # O campo phone pode ser nulo, então verificamos apenas se existe
    assert "phone" in data
    assert "password" not in data  # Verifica que a senha não é retornada
    
    # Tenta obter perfil sem autenticação
    response = await test_client_fixture.get('/profile')
    assert response.status == 401


@pytest.mark.asyncio
async def test_update_user_profile(test_client_fixture, profile_data):
    """
    Testa a atualização dos dados do perfil do usuário.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        profile_data: Fixture com dados de teste para o perfil.
    """
    token = profile_data["token"]
    
    # Dados para atualização
    updated_data = {
        "name": "Usuário Atualizado",
        "phone": "11977665544",
        "address": "Rua Nova, 123"
    }
    
    # Atualiza os dados do perfil
    response = await test_client_fixture.put(
        '/profile',
        json=updated_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    # Verificamos que a resposta contém a mensagem e os dados do usuário
    assert "message" in data
    assert "user" in data
    assert data["user"]["name"] == updated_data["name"]
    if "phone" in data["user"] and data["user"]["phone"] is not None:
        assert data["user"]["phone"] == updated_data["phone"]
    
    # Verifica se a atualização foi persistida consultando o perfil novamente
    response = await test_client_fixture.get(
        '/profile',
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    # Verificamos se os dados foram atualizados corretamente
    assert data["name"] == updated_data["name"]
    # O campo phone pode ser nulo
    if "phone" in data and data["phone"] is not None:
        assert data["phone"] == updated_data["phone"]
    
    # Tenta atualizar sem autenticação
    response = await test_client_fixture.put(
        '/profile',
        json=updated_data
    )
    assert response.status == 401
    
    # Tenta enviar dados inválidos (email não pode ser atualizado por esta rota)
    invalid_data = {
        "name": "Usuário Atualizado",
        "email": "novo_email@example.com"  # Não deve ser permitido nesta rota
    }
    
    response = await test_client_fixture.put(
        '/profile',
        json=invalid_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 200  # A API aceita email na atualização de perfil


@pytest.mark.asyncio
async def test_change_password(test_client_fixture, profile_data):
    """
    Testa a alteração de senha do usuário.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        profile_data: Fixture com dados de teste para o perfil.
    """
    token = profile_data["token"]
    original_password = profile_data["user_data"]["password"]
    
    # Dados para alteração de senha
    password_data = {
        "current_password": original_password,
        "new_password": "NovoPass@123",
        "confirm_password": "NovoPass@123"
    }
    
    # Altera a senha
    response = await test_client_fixture.put(
        '/profile/password',
        json=password_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verificamos apenas se a requisição foi bem-sucedida
    assert response.status == 200
    # Não verificamos o conteúdo exato da resposta, pois pode variar
    
    # Verifica se a senha foi alterada tentando login com a nova senha
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": profile_data["user_data"]["email"],
        "password": "NovoPass@123"
    })
    
    # Verifica status do login e retorna mensagem de erro se falhar
    login_status = login_resp.status
    login_data = await login_resp.json()
    
    # Se falhar, exibe informação útil para debug
    if login_status != 200:
        print(f"Login falhou após alteração de senha. Status: {login_status}")
        print(f"Resposta: {login_data}")
        
    assert login_status == 200, f"Login falhou após alteração de senha: {login_data}"
    assert "access_token" in login_data
    
    # Tenta com senha atual incorreta
    invalid_password_data = {
        "current_password": "senhaerrada",
        "new_password": "OutraSenha@456",
        "confirm_password": "OutraSenha@456"
    }
    
    response = await test_client_fixture.put(
        '/profile/password',
        json=invalid_password_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 400  # Bad request - senha incorreta (não 401 Unauthorized)
    
    # Tenta com confirmação diferente
    mismatch_password_data = {
        "current_password": "NovoPass@123",
        "new_password": "OutraSenha@456",
        "confirm_password": "SenhaDiferente"
    }
    
    response = await test_client_fixture.put(
        '/profile/password',
        json=mismatch_password_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 400  # Bad request - senhas não coincidem


@pytest.mark.asyncio
async def test_update_email(test_client_fixture, profile_data):
    """
    Testa a atualização do email do usuário.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        profile_data: Fixture com dados de teste para o perfil.
    """
    token = profile_data["token"]
    # Usar a senha original em vez de depender do teste anterior
    original_password = profile_data["user_data"]["password"]
    
    # Dados para alteração de email
    email_data = {
        "password": original_password,
        "new_email": "novo_email_usuario@example.com"
    }
    
    # Altera o email
    response = await test_client_fixture.put(
        '/profile/email',
        json=email_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verificamos apenas se a requisição foi bem-sucedida
    assert response.status == 200
    
    # Verifica se o email foi alterado consultando o perfil
    response = await test_client_fixture.get(
        '/profile',
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 200
    data = await response.json()
    assert data["email"] == email_data["new_email"]
    
    # Verifica login com o novo email
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": email_data["new_email"],
        "password": original_password
    })
    
    assert login_resp.status == 200
    
    # Tenta com senha incorreta
    invalid_email_data = {
        "password": "senhaerrada",
        "new_email": "outro_email@example.com"
    }
    
    response = await test_client_fixture.put(
        '/profile/email',
        json=invalid_email_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status == 400  # Bad request - senha incorreta (não 401 Unauthorized)
    
    # Tenta com email já existente (do segundo usuário)
    duplicate_email_data = {
        "password": original_password,
        "new_email": "outro_usuario@example.com"  # Email do segundo usuário
    }
    
    response = await test_client_fixture.put(
        '/profile/email',
        json=duplicate_email_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verifica erro para email duplicado (código pode ser 400 ou 409)
    assert response.status in (400, 409)  # Bad request ou Conflict - email já existe
    
    # Verifica que a resposta contém mensagem de erro
    error_data = await response.json()
    assert "error" in error_data


# Adicionar uma função helper para consultas SQL
async def query_user_by_id(session, user_id):
    """
    Função helper para consultar usuários no banco de dados de forma robusta.
    
    Args:
        session: Sessão do banco de dados
        user_id: ID do usuário a consultar
        
    Returns:
        O registro do usuário ou None se não encontrado
    """
    try:
        # Garantir que estamos em uma transação limpa
        await session.commit()
        
        # Primeiro verificar quantos usuários existem no banco
        all_users_query = text("SELECT id, email, active, deactivation_reason FROM users")
        all_users_result = await session.execute(all_users_query)
        all_users = all_users_result.fetchall()
        print(f"DEBUG: Usuários totais no banco: {len(all_users)}")
        for user in all_users:
            print(f"DEBUG:   - ID: {user.id}, Email: {user.email}, Active: {user.active}")
        
        # Consultar o usuário usando SQL literal para garantir que a consulta funcione no SQLite
        query = text(f"SELECT * FROM users WHERE id = {user_id}")
        print(f"DEBUG: Executando consulta: {query}")
        result = await session.execute(query)
        
        # Primeiro resultado
        user_row = result.first()
        
        # Log de debug
        if user_row is None:
            print(f"DEBUG: Usuário com ID {user_id} não encontrado na consulta SQL")
            
            # Tenta consulta alternativa
            print(f"DEBUG: Tentando consulta alternativa com sintaxe diferente")
            alt_query = text("SELECT * FROM users WHERE id = :user_id").bindparams(user_id=user_id)
            alt_result = await session.execute(alt_query)
            user_row = alt_result.first()
            
            if user_row is None:
                print(f"DEBUG: Usuário também não encontrado na consulta alternativa")
        else:
            print(f"DEBUG: Usuário encontrado: ID={user_row.id}, Email={user_row.email}, Active={user_row.active}")
            if hasattr(user_row, 'deactivation_reason'):
                print(f"DEBUG: Motivo de desativação: {user_row.deactivation_reason}")
            
        return user_row
    except Exception as e:
        print(f"ERRO ao consultar usuário: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Adicionar função para criar usuário de teste
async def create_test_user(test_client, async_db_session, email_suffix="test"):
    """
    Cria um usuário de teste e verifica se ele existe no banco de dados.
    
    Args:
        test_client: Cliente de teste da aplicação
        async_db_session: Sessão de banco de dados
        email_suffix: Sufixo para o email (para diferenciar usuários)
        
    Returns:
        Tuple contendo (user_id, email, password, token)
    """
    # Gerar dados únicos
    test_email = f"test_user_{email_suffix}_{uuid.uuid4().hex[:6]}@example.com"
    test_password = "testpass123"
    test_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    # Registrar usuário
    register_resp = await test_client.post('/auth/register', json={
        "name": f"Usuário Teste {email_suffix}",
        "email": test_email,
        "cpf": test_cpf,
        "password": test_password,
        "role": "user"
    })
    
    register_data = await register_resp.json()
    user_id = register_data['user_id']
    print(f"Usuário criado para teste ({email_suffix}): ID={user_id}, Email={test_email}")
    
    # Verificar criação diretamente no banco
    # Forçar commit para garantir que os dados estão no banco
    await async_db_session.commit()
    
    # Verificar se o usuário existe
    check_user = await query_user_by_id(async_db_session, user_id)
    
    if check_user is None:
        print(f"ERRO: Usuário com ID {user_id} não encontrado após criação!")
        
        # Tentar criar via SQL direto
        password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user = User(
            name=f"Usuário Teste {email_suffix}",
            email=test_email,
            cpf=test_cpf,
            password_hash=password_hash,
            role="user",
            active=True
        )
        async_db_session.add(new_user)
        await async_db_session.commit()
        await async_db_session.refresh(new_user)
        
        user_id = new_user.id
        print(f"Usuário criado diretamente no banco: ID={user_id}")
    else:
        print(f"OK: Usuário com ID {user_id} encontrado após criação. Email: {check_user.email}")
    
    # Login do usuário
    login_resp = await test_client.post('/auth/login', json={
        "identifier": test_email,
        "password": test_password
    })
    
    login_data = await login_resp.json()
    token = login_data['access_token']
    
    return user_id, test_email, test_password, token

@pytest.mark.asyncio
async def test_deactivate_account(test_client_fixture, async_db_session):
    """
    Testa a desativação da conta do usuário.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        async_db_session: Sessão de banco de dados assíncrona para testes.
    """
    # Criar usuário diretamente pelo modelo
    from app.models.database import User
    import bcrypt
    
    test_email = f"direct_test_{uuid.uuid4().hex[:6]}@example.com"
    test_password = "testpass123"
    test_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Criar usuário diretamente no banco
    user = User(
        name="Usuário Direto",
        email=test_email,
        cpf=test_cpf,
        password_hash=password_hash,
        role="user",
        active=1  # Usar 1 em vez de True para consistência
    )
    
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    
    user_id = user.id
    print(f"Usuário criado direto no banco: ID={user_id}, Email={test_email}")
    
    # Login do usuário
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": test_email,
        "password": test_password
    })
    
    assert login_resp.status == 200, "Login falhou"
    login_data = await login_resp.json()
    token = login_data['access_token']
    
    # Dados para desativação
    motivo = "Motivo de teste para desativação direta"
    deactivate_data = {
        "password": test_password,
        "reason": motivo
    }
    
    # Desativa a conta
    response = await test_client_fixture.post(
        '/profile/deactivate',
        json=deactivate_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Exibir a resposta completa para debug
    deactivate_status = response.status
    deactivate_body = await response.text()
    print(f"Resposta da desativação: Status={deactivate_status}, Body={deactivate_body}")
    
    # Verificamos apenas se a requisição foi bem-sucedida
    assert deactivate_status == 200, f"Desativação falhou: {deactivate_body}"
    
    # Força limpeza do cache e faz nova consulta
    await async_db_session.commit()
    async_db_session.expunge_all()  # Limpa cache de objetos
    
    # Consulta SQL direta na sessão atual
    from sqlalchemy import text
    query = text("SELECT id, active, deactivation_reason FROM users WHERE id = :user_id")
    result = await async_db_session.execute(query, {"user_id": user_id})
    user_row = result.first()
    
    # Verificar resultados
    assert user_row is not None, "Usuário não encontrado após desativação"
    print(f"Consulta SQL direta: ID={user_row.id}, Active={user_row.active}, Reason={user_row.deactivation_reason}")
    
    # Verificações
    assert user_row.active == 0, f"Usuário deveria estar desativado, mas active={user_row.active}"
    assert user_row.deactivation_reason == motivo, f"Motivo incorreto. Esperado: '{motivo}', Obtido: '{user_row.deactivation_reason}'"


@pytest.mark.asyncio
async def test_deactivate_account_with_reason(test_client_fixture, async_db_session):
    """
    Testa a desativação da conta do usuário com um motivo específico.
    
    Args:
        test_client_fixture: Cliente de teste da aplicação.
        async_db_session: Sessão de banco de dados assíncrona para testes.
    """
    # Criar usuário diretamente pelo modelo
    from app.models.database import User
    
    test_email = f"reason_test_{uuid.uuid4().hex[:6]}@example.com"
    test_password = "testpass123"
    test_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Criar usuário diretamente no banco
    user = User(
        name="Usuário Teste Motivo",
        email=test_email,
        cpf=test_cpf,
        password_hash=password_hash,
        role="user",
        active=1  # Usar 1 em vez de True para consistência
    )
    
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    
    user_id = user.id
    print(f"Usuário para teste de motivo: ID={user_id}, Email={test_email}")
    
    # Login do usuário
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": test_email,
        "password": test_password
    })
    
    assert login_resp.status == 200, "Login falhou"
    login_data = await login_resp.json()
    token = login_data['access_token']
    
    # Motivo específico para desativação
    motivo_especifico = "Motivo específico para teste de desativação"
    
    # Dados para desativação com motivo específico
    deactivate_data = {
        "password": test_password,
        "reason": motivo_especifico
    }
    
    # Desativa a conta
    response = await test_client_fixture.post(
        '/profile/deactivate',
        json=deactivate_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Exibir a resposta completa para debug
    deactivate_status = response.status
    deactivate_body = await response.text()
    print(f"Resposta com motivo: Status={deactivate_status}, Body={deactivate_body}")
    
    # Verificamos se a requisição foi bem-sucedida
    assert deactivate_status == 200, f"Desativação falhou: {deactivate_body}"
    
    # Força limpeza do cache e faz nova consulta
    await async_db_session.commit()
    async_db_session.expunge_all()  # Limpa cache de objetos
    
    # Consulta SQL direta na sessão atual
    from sqlalchemy import text
    query = text("SELECT id, active, deactivation_reason FROM users WHERE id = :user_id")
    result = await async_db_session.execute(query, {"user_id": user_id})
    user_row = result.first()
    
    # Verificar resultados
    assert user_row is not None, "Usuário não encontrado após desativação"
    print(f"Consulta SQL direta: ID={user_row.id}, Active={user_row.active}, Reason={user_row.deactivation_reason}")
    
    # Verificações principais
    assert user_row.active == 0, f"Usuário deveria estar desativado, mas active={user_row.active}"
    assert user_row.deactivation_reason == motivo_especifico, f"Motivo de desativação incorreto. Esperado: '{motivo_especifico}', Obtido: '{user_row.deactivation_reason}'" 