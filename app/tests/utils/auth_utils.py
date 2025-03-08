# D:\#3xDigital\app\tests\utils\auth_utils.py

"""
auth_utils.py

Este módulo fornece funções utilitárias relacionadas à autenticação para testes,
permitindo a geração de tokens de acesso para usuários com diferentes papéis.

Functions:
    - get_admin_token(client): Gera e retorna um token JWT para um usuário administrador.
    - get_user_token(client): Gera e retorna um token JWT para um usuário com papel 'user'.
    - get_affiliate_request_token(client): Gera e retorna um token JWT para um usuário que solicita afiliação,
      além de retornar o ID do registro de afiliação.
    - get_affiliate_token(client, status="approved", referral_code=None): Registra, loga e solicita afiliação para
      um usuário, retornando seu token e o ID do registro de afiliado. Se desejado, atualiza o status e o referral_code.
"""

import uuid
import asyncio
import time
from app.config.settings import DB_SESSION_KEY

async def wait_for_token(client, identifier, password, max_wait=10):
    """
    Tenta fazer login repetidamente até obter um token JWT válido ou atingir o tempo máximo.

    Útil para testar cenários em que o usuário acabou de ser criado e pode haver um pequeno
    atraso até que o registro esteja disponível para autenticação.

    Args:
        client (TestClient): Cliente de teste para realizar as requisições.
        identifier (str): Identificador do usuário (email ou CPF).
        password (str): Senha do usuário.
        max_wait (int, opcional): Tempo máximo de espera, em segundos (padrão 10).

    Returns:
        str ou None: Token JWT se obtido, caso contrário None.
    """
    start = time.monotonic()
    token = None
    while time.monotonic() - start < max_wait:
        try:
            login_resp = await client.post("/auth/login", json={
                "identifier": identifier,
                "password": password
            })
            if login_resp.status == 200:
                login_data = await login_resp.json()
                if "access_token" in login_data:
                    token = login_data["access_token"]
                    break
            # Espera um pouco antes de tentar novamente
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Erro ao tentar login: {str(e)}")
            await asyncio.sleep(0.5)
    return token

async def get_admin_token(client):
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
    admin_password = "admin123"
    admin_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
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
    
    token = await wait_for_token(client, admin_email.lower(), admin_password)
    if not token:
        raise Exception(f"Falha no login do admin. Resposta recebida: {reg_data}")
    
    return token

async def get_user_token(client):
    user_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    user_password = "user123"
    user_cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
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

    token = await wait_for_token(client, user_email.lower(), user_password)
    if not token:
        raise Exception(f"Falha no login do user. Resposta recebida: {reg_data}")
    
    return token

async def get_affiliate_token(client, status="approved", referral_code=None):
    """
    Gera um token de acesso para um usuário que se torna afiliado.

    Este método realiza o seguinte fluxo:
      1. Registra um usuário com papel "user".
      2. Realiza login para obter o token JWT.
      3. Chama o endpoint /affiliates/request para solicitar afiliação.
      4. Consulta o registro de afiliado associado.
      5. (Opcional) Atualiza o status do afiliado e/ou o referral_code, facilitando a verificação em testes.
      6. Atualiza o papel do usuário para "affiliate" e reemite um novo token refletindo essa mudança.

    Args:
        client: Cliente de teste configurado para a aplicação AIOHTTP.
        status (str, opcional): Status desejado para o registro do afiliado (padrão "approved").
        referral_code (str, opcional): Código de referência a ser definido no registro do afiliado.

    Returns:
        tuple: (token: str, affiliate_id: int)

    Raises:
        Exception: Em caso de falha no fluxo de registro, login, solicitação de afiliação,
                   atualização do registro de afiliado ou reemissão do token.
    """
    # Gera dados fictícios para o usuário afiliado
    user_email = f"affiliate_{uuid.uuid4().hex[:6]}@test.com"
    user_password = "affiliate123"
    user_cpf = str(uuid.uuid4().int % 10**11).zfill(11)

    # Registra o usuário com papel "user"
    reg_resp = await client.post("/auth/register", json={
        "name": "Affiliate Test",
        "email": user_email.lower(),
        "cpf": user_cpf,
        "password": user_password,
        "role": "user"
    })
    if reg_resp.status != 201:
        raise Exception("Erro no registro do usuário afiliado.")

    # Realiza login para obter o token inicial
    token = await wait_for_token(client, user_email.lower(), user_password, max_wait=10)
    if not token:
        raise Exception("Falha no login do usuário afiliado.")

    # Solicita afiliação
    req_resp = await client.post("/affiliates/request", json={"commission_rate": 0.05},
                                 headers={"Authorization": f"Bearer {token}"})
    req_data = await req_resp.json()
    if req_resp.status != 201:
        raise Exception(f"Erro ao solicitar afiliação: {req_data}")

    # Recupera o registro do afiliado
    from sqlalchemy import select
    from app.models.database import Affiliate
    db = client.app[DB_SESSION_KEY]
    result = await db.execute(select(Affiliate).where(Affiliate.user.has(email=user_email.lower())))
    affiliate = result.scalar()
    if not affiliate:
        raise Exception("Afiliado não encontrado após solicitação.")

    # Atualiza o status e o referral_code se necessário
    if status != "pending":
        affiliate.request_status = status
    if referral_code is not None:
        affiliate.referral_code = referral_code
    await db.commit()
    await db.refresh(affiliate)

    # Atualiza o papel do usuário para "affiliate"
    from app.models.database import User
    result = await db.execute(select(User).where(User.email == user_email.lower()))
    user = result.scalar()
    if user:
        user.role = "affiliate"
        await db.commit()
        await db.refresh(user)
    else:
        raise Exception("Usuário não encontrado para atualização de papel.")

    # Reemite um novo token para refletir a mudança de papel
    new_token = await wait_for_token(client, user_email.lower(), user_password, max_wait=10)
    if not new_token:
        raise Exception("Falha ao reemitir token após atualizar o papel para affiliate.")

    return new_token, affiliate.id
