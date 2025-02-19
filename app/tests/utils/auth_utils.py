# D:\#3xDigital\app\tests\utils\auth_utils.py

"""
auth_utils.py

Este módulo fornece funções utilitárias relacionadas à autenticação para testes,
permitindo a geração de tokens de acesso para usuários com diferentes papéis.

Functions:
    - get_admin_token(client): Gera e retorna um token JWT para um usuário administrador.
"""

import uuid
import asyncio

async def get_admin_token(client):
    """
    Gera um token de acesso para um usuário administrador com dados únicos.

    Args:
        client: Cliente de teste configurado para a aplicação AIOHTTP.

    Returns:
        str: Token JWT do administrador.

    Raises:
        Exception: Se o login falhar.
    """
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
    admin_password = "admin123"
    admin_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    # Tenta registrar o usuário administrador
    reg_resp = await client.post("/auth/register", json={
        "name": "Admin Test",
        "email": admin_email.lower(),
        "cpf": admin_cpf,
        "password": admin_password,
        "role": "admin"
    })
    
    reg_data = await reg_resp.json()
    
    if reg_resp.status != 201:
        raise Exception(f"Erro ao registrar admin: {reg_data}")
    
    # Espera para garantir que o usuário foi persistido no banco
    for _ in range(5):  # Tenta até 5 vezes
        await asyncio.sleep(0.2)
        
        # Tenta fazer login
        login_resp = await client.post("/auth/login", json={
            "identifier": admin_email.lower(),  # Certifica que o email bate com o formato salvo
            "password": admin_password
        })
        login_data = await login_resp.json()
        
        if "access_token" in login_data:
            return login_data["access_token"]
    
    raise Exception(f"Falha no login do admin. Resposta recebida: {login_data}")


async def get_user_token(client):
    """
    Gera um token de acesso para um usuário user com dados únicos.

    Args:
        client: Cliente de teste configurado para a aplicação AIOHTTP.

    Returns:
        str: Token JWT do user.

    Raises:
        Exception: Se o login falhar.
    """
    user_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    user_password = "user123"
    user_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    # Tenta registrar o usuário user
    reg_resp = await client.post("/auth/register", json={
        "name": "User Test",
        "email": user_email.lower(),
        "cpf": user_cpf,
        "password": user_password,
        "role": "user"
    })
    
    reg_data = await reg_resp.json()
    
    if reg_resp.status != 201:
        raise Exception(f"Erro ao registrar user: {reg_data}")

    # Espera para garantir que o usuário foi persistido no banco
    for _ in range(5):  # Tenta até 5 vezes
        await asyncio.sleep(0.2)
        
        # Tenta fazer login
        login_resp = await client.post("/auth/login", json={
            "identifier": user_email.lower(),
            "password": user_password
        })
        login_data = await login_resp.json()
        
        if "access_token" in login_data:
            return login_data["access_token"]

    raise Exception(f"Falha no login do user. Resposta recebida: {login_data}")
