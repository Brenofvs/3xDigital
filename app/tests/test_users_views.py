# D:\#3xDigital\app\tests\test_users_views.py
"""
test_users_views.py

Módulo de testes para os endpoints de gerenciamento avançado de usuários.

Funcionalidades testadas:
    - Listagem e busca de usuários
    - Obtenção de detalhes de usuário
    - Atualização de papel (role) de usuário
    - Bloqueio/desbloqueio de usuários
    - Redefinição de senha

Dependências:
    - pytest e pytest-asyncio para testes assíncronos
    - app.models.database para acesso às entidades de usuário
    - app.services.user_service para serviços de gerenciamento de usuários
"""

import pytest
import pytest_asyncio
import bcrypt
from sqlalchemy import select
from app.config.settings import DB_SESSION_KEY

from app.models.database import User, Affiliate


@pytest_asyncio.fixture
async def users_test_data(test_client_fixture):
    """
    Configura dados de teste para gestão de usuários.
    
    Cria:
        - Usuário administrador
        - Vários usuários com diferentes papéis
        
    Returns:
        dict: Dados de teste (tokens, ids, etc)
    """
    # Dados a serem retornados
    data = {}
    
    # Cria usuário admin
    admin_data = {
        "name": "Admin Teste Usuários",
        "email": "admin_users@example.com",
        "cpf": "12345678901",
        "password": "adminpass456",
        "role": "admin"
    }
    
    admin_resp = await test_client_fixture.post('/auth/register', json=admin_data)
    admin_data = await admin_resp.json()
    admin_id = admin_data['user_id']
    
    # Login do admin
    admin_login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "admin_users@example.com",
        "password": "adminpass456"
    })
    admin_login_data = await admin_login_resp.json()
    admin_token = admin_login_data['access_token']
    
    # Cria usuários diversos
    user_types = [
        {"role": "manager", "name": "Gerente Teste", "email": "gerente@example.com", "cpf": "23456789012"},
        {"role": "affiliate", "name": "Afiliado Teste", "email": "afiliado@example.com", "cpf": "34567890123"},
        {"role": "user", "name": "Usuário Teste", "email": "usuario@example.com", "cpf": "45678901234"}
    ]
    
    user_ids = {}
    
    for user_info in user_types:
        user_data = {
            "name": user_info["name"],
            "email": user_info["email"],
            "cpf": user_info["cpf"],
            "password": "userpass123",
            "role": user_info["role"]
        }
        
        user_resp = await test_client_fixture.post('/auth/register', json=user_data)
        user_data = await user_resp.json()
        user_ids[user_info["role"]] = user_data['user_id']
    
    # Se for afiliado, cria registro na tabela Affiliate
    if "affiliate" in user_ids:
        db = test_client_fixture.app[DB_SESSION_KEY]
        affiliate = Affiliate(
            user_id=user_ids["affiliate"],
            referral_code="USERTST123",
            commission_rate=0.1,
            request_status="approved"
        )
        db.add(affiliate)
        await db.commit()
        await db.refresh(affiliate)
        data["affiliate_id"] = affiliate.id
    
    # Armazena dados para testes
    data["admin_token"] = admin_token
    data["admin_id"] = admin_id
    data["user_ids"] = user_ids
    
    return data


@pytest.mark.asyncio
async def test_list_users(test_client_fixture, users_test_data):
    """
    Testa listagem de usuários.
    
    Args:
        client: Cliente de teste
        users_test_data: Dados de teste
        
    Asserts:
        - Admin consegue listar todos os usuários
        - Filtros de busca e papel funcionam corretamente
    """
    data = users_test_data
    
    # Teste listagem completa
    resp = await test_client_fixture.get('/users',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    users_data = await resp.json()
    
    assert "users" in users_data
    assert len(users_data["users"]) >= 4  # admin + 3 usuários criados
    
    # Teste com filtro de papel
    resp = await test_client_fixture.get('/users?role=manager',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    filtered_data = await resp.json()
    
    assert len(filtered_data["users"]) >= 1
    for user in filtered_data["users"]:
        assert user["role"] == "manager"
    
    # Teste com busca por nome
    resp = await test_client_fixture.get('/users?search=Gerente',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    search_data = await resp.json()
    
    assert len(search_data["users"]) >= 1
    assert any("Gerente" in user["name"] for user in search_data["users"])


@pytest.mark.asyncio
async def test_get_user_details(test_client_fixture, users_test_data):
    """
    Testa obtenção de detalhes de usuário.
    
    Args:
        client: Cliente de teste
        users_test_data: Dados de teste
        
    Asserts:
        - Admin consegue ver detalhes de qualquer usuário
        - Detalhes de afiliado incluem informações específicas
    """
    data = users_test_data
    
    # Teste detalhes de usuário comum
    user_id = data["user_ids"]["user"]
    resp = await test_client_fixture.get(f'/users/{user_id}',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    user_data = await resp.json()
    
    assert user_data["id"] == user_id
    assert user_data["role"] == "user"
    assert user_data["is_affiliate"] == False
    
    # Teste detalhes de afiliado
    affiliate_id = data["user_ids"]["affiliate"]
    resp = await test_client_fixture.get(f'/users/{affiliate_id}',
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    affiliate_data = await resp.json()
    
    assert affiliate_data["id"] == affiliate_id
    assert affiliate_data["role"] == "affiliate"
    assert affiliate_data["is_affiliate"] == True
    assert "affiliate" in affiliate_data
    assert "referral_code" in affiliate_data["affiliate"]


@pytest.mark.asyncio
async def test_update_user_role(test_client_fixture, users_test_data):
    """
    Testa atualização de papel de usuário.
    
    Args:
        client: Cliente de teste
        users_test_data: Dados de teste
        
    Asserts:
        - Admin consegue alterar papel de outro usuário
        - Admin não consegue alterar seu próprio papel
    """
    data = users_test_data
    
    # Teste alteração de papel de usuário comum
    user_id = data["user_ids"]["user"]
    role_data = {
        "role": "manager"
    }
    
    resp = await test_client_fixture.put(f'/users/{user_id}/role',
                           json=role_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    result = await resp.json()
    
    assert "message" in result
    assert "manager" in result["message"]
    
    # Verifica se o papel foi alterado no banco
    db = test_client_fixture.app[DB_SESSION_KEY]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    assert user.role == "manager"
    
    # Teste tentativa de alterar próprio papel
    admin_id = data["admin_id"]
    role_data = {
        "role": "user"
    }
    
    resp = await test_client_fixture.put(f'/users/{admin_id}/role',
                           json=role_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 400
    error_data = await resp.json()
    
    assert "error" in error_data
    assert "próprio papel" in error_data["error"]


@pytest.mark.asyncio
async def test_toggle_user_status(test_client_fixture, users_test_data):
    """
    Testa bloqueio e desbloqueio de usuários.
    
    Args:
        client: Cliente de teste
        users_test_data: Dados de teste
        
    Asserts:
        - Admin consegue bloquear um afiliado
        - Admin consegue desbloquear um afiliado
        - Admin não consegue bloquear a si mesmo
    """
    data = users_test_data
    
    # Teste bloqueio de afiliado
    affiliate_id = data["user_ids"]["affiliate"]
    status_data = {
        "blocked": True
    }
    
    resp = await test_client_fixture.put(f'/users/{affiliate_id}/status',
                           json=status_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    result = await resp.json()
    
    assert "message" in result
    assert "bloqueado" in result["message"]
    
    # Verifica se o afiliado foi bloqueado
    db = test_client_fixture.app[DB_SESSION_KEY]
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == affiliate_id))
    affiliate = result.scalar_one_or_none()
    
    assert affiliate.request_status == "blocked"
    
    # Teste desbloqueio de afiliado
    status_data = {
        "blocked": False
    }
    
    resp = await test_client_fixture.put(f'/users/{affiliate_id}/status',
                           json=status_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    result = await resp.json()
    
    assert "message" in result
    assert "desbloqueado" in result["message"]
    
    # Verifica se o afiliado foi desbloqueado
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == affiliate_id))
    affiliate = result.scalar_one_or_none()
    
    assert affiliate.request_status == "approved"
    
    # Teste tentativa de bloquear a si mesmo
    admin_id = data["admin_id"]
    status_data = {
        "blocked": True
    }
    
    resp = await test_client_fixture.put(f'/users/{admin_id}/status',
                           json=status_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 400
    error_data = await resp.json()
    
    assert "error" in error_data
    assert "próprio usuário" in error_data["error"]


@pytest.mark.asyncio
async def test_reset_password(test_client_fixture, users_test_data):
    """
    Testa redefinição de senha pelo administrador.
    
    Args:
        client: Cliente de teste
        users_test_data: Dados de teste
        
    Asserts:
        - Admin consegue redefinir senha de outro usuário
        - Senha é atualizada corretamente no banco
        - Usuário consegue fazer login com a nova senha
    """
    data = users_test_data
    
    # Teste redefinição de senha
    user_id = data["user_ids"]["user"]
    password_data = {
        "new_password": "novasenha456"
    }
    
    resp = await test_client_fixture.put(f'/users/{user_id}/reset-password',
                           json=password_data,
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
    
    assert resp.status == 200
    result = await resp.json()
    
    assert "message" in result
    assert "redefinida" in result["message"]
    
    # Verifica se a senha foi atualizada no banco
    db = test_client_fixture.app[DB_SESSION_KEY]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    assert bcrypt.checkpw("novasenha456".encode("utf-8"), user.password_hash.encode("utf-8"))
    
    # Testa login com nova senha
    login_resp = await test_client_fixture.post('/auth/login', json={
        "identifier": "usuario@example.com",
        "password": "novasenha456"
    })
    
    assert login_resp.status == 200
    login_data = await login_resp.json()
    
    assert "access_token" in login_data