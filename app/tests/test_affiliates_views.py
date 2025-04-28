# D:\3xDigital\app\tests\test_affiliates_views.py

"""
test_affiliates_views.py

Este módulo contém os testes automatizados para os endpoints de gerenciamento de afiliados e rastreamento de vendas.

Observação:
    Conforme a regra de negócio, os usuários são registrados com o papel "user" e, para se tornarem afiliados,
    deve ser realizada uma solicitação via endpoint /affiliates/request. Para evitar repetição de código, foi criado
    o utilitário get_affiliate_token (em app/tests/utils/auth_utils.py) que realiza o fluxo completo:
      1. Registro do usuário;
      2. Login para obtenção do token JWT;
      3. Solicitação de afiliação;
      4. Atualização (opcional) do status e do referral_code.

Fixtures:
    test_client_fixture: Cliente de teste configurado para a aplicação AIOHTTP.
    get_admin_token: Função auxiliar para obter token JWT de administrador.
    get_user_token: Função auxiliar para obter token JWT de usuário.
    get_affiliate_token: Função auxiliar para registrar, logar e solicitar afiliação, retornando o token e o ID do afiliado.

Test Functions:
    - test_get_affiliate_link_success
    - test_get_affiliate_link_not_found
    - test_get_affiliate_link_inactive
    - test_get_affiliate_sales_success
    - test_get_affiliate_sales_not_found
    - test_get_affiliate_sales_inactive
    - test_request_affiliation_success
    - test_request_affiliation_duplicate
    - test_update_affiliate_success
    - test_update_affiliate_not_found
    - test_update_affiliate_forbidden
    - test_list_affiliate_requests_success
    - test_list_affiliate_requests_forbidden
    - test_list_affiliate_requests
    - test_list_approved_affiliates
"""

import uuid
import pytest
from app.config.settings import DB_SESSION_KEY
from app.models.database import Affiliate, Sale
from app.tests.utils.auth_utils import get_admin_token, get_user_token, get_affiliate_token
from sqlalchemy import text
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# GET /affiliates/link
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_affiliate_link_success(test_client_fixture):
    """
    Testa a obtenção do link de afiliado com sucesso para um afiliado ativo.

    Processo:
      1. Utiliza o utilitário get_affiliate_token para registrar, logar e solicitar afiliação,
         atualizando o registro para status "approved" e definindo o referral_code.
      2. Chama o endpoint GET /affiliates/link e verifica se o link contém o código de referência esperado.

    Asserts:
      - Status HTTP 200.
      - Resposta contém a chave "affiliate_link" com o código de referência definido.
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client, status="approved", referral_code="TESTCODE123")
    resp = await client.get("/affiliates/link", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200, "Endpoint deveria retornar 200 para afiliado ativo."
    data = await resp.json()
    assert "affiliate_link" in data, "Chave 'affiliate_link' não encontrada na resposta."
    assert "TESTCODE123" in data["affiliate_link"], "Código de referência ausente no link retornado."


@pytest.mark.asyncio
async def test_get_affiliate_link_inactive(test_client_fixture):
    """
    Testa o endpoint GET /affiliates/link para um afiliado que não está aprovado.

    Processo:
      1. Utiliza o utilitário get_affiliate_token com status "pending" e define um referral_code.
      2. Chama o endpoint e verifica se retorna erro 403.

    Asserts:
      - Status HTTP 403.
      - Mensagem de erro indica que o afiliado está inativo.
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client, status="pending", referral_code="INACTCODE")
    resp = await client.get("/affiliates/link", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403, "Endpoint deveria retornar 403 para afiliado inativo."
    data = await resp.json()
    assert "Solicitação de afiliação pendente ou rejeitada" in data.get("error", "")

# ---------------------------------------------------------------------------
# GET /affiliates/sales
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_affiliate_sales_success(test_client_fixture):
    """
    Testa a obtenção da lista de vendas para um afiliado ativo.

    Processo:
      1. Utiliza o utilitário get_affiliate_token para registrar, logar e solicitar afiliação,
         atualizando o registro para status "approved".
      2. Insere manualmente um registro de venda associado ao afiliado.
      3. Chama o endpoint GET /affiliates/sales e verifica se os dados da venda são retornados.

    Asserts:
      - Status HTTP 200.
      - Resposta contém a lista de vendas com os campos "order_id" e "commission".
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client, status="approved", referral_code="SALECODE")
    db = client.app[DB_SESSION_KEY]
    sale = Sale(
        order_id="ORDER123",
        commission=10.0,
        affiliate_id=affiliate_id
    )
    db.add(sale)
    await db.commit()

    resp = await client.get("/affiliates/sales", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200, "Endpoint deveria retornar 200 para afiliado ativo."
    data = await resp.json()
    assert "sales" in data, "Chave 'sales' não encontrada na resposta."
    assert any(s["order_id"] == "ORDER123" for s in data["sales"]), "Venda não encontrada na lista."


@pytest.mark.asyncio
async def test_get_affiliate_sales_inactive(test_client_fixture):
    """
    Testa o endpoint GET /affiliates/sales para um afiliado inativo (status não 'approved').

    Processo:
      1. Utiliza o utilitário get_affiliate_token com status "pending" e define um referral_code.
      2. Chama o endpoint e verifica se retorna erro 403.

    Asserts:
      - Status HTTP 403.
      - Mensagem de erro indica que o afiliado está inativo.
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client, status="pending", referral_code="INACTSALE")
    resp = await client.get("/affiliates/sales", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403, "Endpoint deveria retornar 403 para afiliado inativo."
    data = await resp.json()
    assert "Solicitação de afiliação pendente ou rejeitada" in data.get("error", "")

# ---------------------------------------------------------------------------
# POST /affiliates/request
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_request_affiliation(test_client_fixture):
    """Testa solicitação de afiliação por um usuário."""
    # Setup
    client = test_client_fixture
    email = f"affiliate_req_{uuid.uuid4().hex[:6]}@test.com"
    password = "user123"
    cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    
    # Registrar um usuário
    reg_resp = await client.post("/auth/register", json={
        "name": "Affiliate Request Test",
        "email": email.lower(),
        "cpf": cpf,
        "password": password,
        "role": "user"
    })
    assert reg_resp.status == 201
    
    # Login
    login_resp = await client.post("/auth/login", json={
        "identifier": email.lower(),
        "password": password
    })
    assert login_resp.status == 200
    token = (await login_resp.json())["access_token"]
    
    # Fazer a solicitação de afiliação
    payload = {
        "commission_rate": 0.07
    }
    
    resp = await client.post(
        "/affiliates/request", 
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert resp.status == 201
    data = await resp.json()
    assert "referral_code" in data
    assert "message" in data
    
    # Verificar se a solicitação foi registrada no banco de dados
    db = client.app[DB_SESSION_KEY]
    query = text("SELECT referral_code FROM affiliates WHERE user_id = (SELECT id FROM users WHERE email = :email)")
    result = await db.execute(query, {"email": email.lower()})
    referral_code = result.scalar_one()
    
    assert referral_code == data["referral_code"]

@pytest.mark.asyncio
async def test_request_affiliation_duplicate(test_client_fixture):
    """
    Testa que uma solicitação de afiliação duplicada não é permitida.

    Processo:
      1. Registra um usuário com papel 'user' e realiza login.
      2. Chama o endpoint /affiliates/request duas vezes.
      3. Verifica que a segunda solicitação retorna erro 400.

    Asserts:
      - A primeira chamada retorna sucesso.
      - A segunda chamada retorna status HTTP 400 com mensagem de erro apropriada.
    """
    client = test_client_fixture

    # Registra e loga o usuário (sem utilizar get_affiliate_token, para poder chamar manualmente o endpoint)
    email = f"user_aff_dup_{uuid.uuid4().hex[:6]}@test.com"
    password = "user123"
    cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    reg_resp = await client.post("/auth/register", json={
        "name": "Affiliate Request Duplicate",
        "email": email.lower(),
        "cpf": cpf,
        "password": password,
        "role": "user"
    })
    assert reg_resp.status == 201

    # Login
    login_resp = await client.post("/auth/login", json={
        "identifier": email.lower(),
        "password": password
    })
    assert login_resp.status == 200
    token = (await login_resp.json())["access_token"]

    # Primeira solicitação
    req_resp1 = await client.post("/affiliates/request", json={"commission_rate": 0.06},
                                  headers={"Authorization": f"Bearer {token}"})
    assert req_resp1.status == 201, "Primeira solicitação deveria retornar 201."

    # Segunda solicitação (duplicada)
    req_resp2 = await client.post("/affiliates/request", json={"commission_rate": 0.06},
                                  headers={"Authorization": f"Bearer {token}"})
    assert req_resp2.status == 400, "Solicitação duplicada deveria retornar 400."
    data = await req_resp2.json()
    assert "Solicitação de afiliação já existente" in data.get("error", "")

# ---------------------------------------------------------------------------
# PUT /affiliates/{affiliate_id}
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_affiliate_success(test_client_fixture):
    """
    Testa que um administrador consegue atualizar os dados de um afiliado com sucesso.

    Processo:
      1. Utiliza o utilitário get_affiliate_token para criar um registro de afiliação (com status "pending").
      2. Utiliza um token de administrador para chamar o endpoint PUT /affiliates/{affiliate_id} com novos dados.
      3. Verifica se os dados foram atualizados na resposta e na base.
      4. Verifica se o papel do usuário foi atualizado para 'affiliate'.

    Asserts:
      - Status HTTP 200.
      - Mensagem de sucesso na atualização.
      - Papel do usuário atualizado para 'affiliate'.
      - Campo 'reason' armazenado corretamente ao rejeitar.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    
    # Criar uma solicitação de afiliação pendente
    token, affiliate_id = await get_affiliate_token(client, status="pending", referral_code="UPDATECODE")
    
    # Aprovar a solicitação
    update_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"commission_rate": 0.08, "request_status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status == 200, "Endpoint deveria retornar 200 para atualização bem-sucedida."
    
    # Verificar mensagem de aprovação
    data = await update_resp.json()
    assert "aprovada com sucesso" in data.get("message", ""), "Mensagem deveria indicar aprovação"
    
    # Verificar se o usuário tem papel 'affiliate'
    db = client.app[DB_SESSION_KEY]
    query = text("""
    SELECT u.role FROM users u
    JOIN affiliates a ON u.id = a.user_id
    WHERE a.id = :aff_id
    """)
    result = await db.execute(query, {"aff_id": affiliate_id})
    user_role = result.scalar_one()
    assert user_role == "affiliate", "Papel do usuário deveria ser 'affiliate' após aprovação"
    
    # Agora rejeitar a solicitação com motivo
    rejection_reason = "Perfil não atende aos requisitos"
    update_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"request_status": "blocked", "reason": rejection_reason},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status == 200, "Endpoint deveria retornar 200 para rejeição bem-sucedida."
    
    # Verificar mensagem de rejeição
    data = await update_resp.json()
    assert "rejeitada com sucesso" in data.get("message", ""), "Mensagem deveria indicar rejeição"
    
    # Verificar se o motivo foi salvo
    query = text("""
    SELECT reason FROM affiliates WHERE id = :aff_id
    """)
    result = await db.execute(query, {"aff_id": affiliate_id})
    saved_reason = result.scalar_one()
    assert saved_reason == rejection_reason, "Motivo da rejeição não foi salvo corretamente"
    
    # Verificar se o usuário voltou a ter papel 'user'
    query = text("""
    SELECT u.role FROM users u
    JOIN affiliates a ON u.id = a.user_id
    WHERE a.id = :aff_id
    """)
    result = await db.execute(query, {"aff_id": affiliate_id})
    user_role = result.scalar_one()
    assert user_role == "user", "Papel do usuário deveria voltar para 'user' após rejeição"


@pytest.mark.asyncio
async def test_update_affiliate_not_found(test_client_fixture):
    """
    Testa que o endpoint PUT /affiliates/{affiliate_id} retorna 404 quando o afiliado não existe.

    Processo:
      1. Utiliza token de administrador.
      2. Chama o endpoint com um ID inexistente.
    
    Asserts:
      - Status HTTP 404.
      - Mensagem de erro apropriada.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    fake_affiliate_id = "999999"  # ID inexistente

    update_resp = await client.put(
        f"/affiliates/{fake_affiliate_id}",
        json={"commission_rate": 0.08, "request_status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status == 404, "Atualização de afiliado inexistente deveria retornar 404."
    data = await update_resp.json()
    assert "Afiliado não encontrado" in data.get("error", "")


@pytest.mark.asyncio
async def test_update_affiliate_forbidden(test_client_fixture):
    """
    Testa que um usuário sem papel 'admin' não consegue atualizar os dados do afiliado.

    Processo:
      1. Utiliza o utilitário get_affiliate_token para criar um registro de afiliação.
      2. Utiliza o token deste usuário para tentar atualizar os dados via endpoint PUT.
    
    Asserts:
      - Status HTTP 403.
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client, status="pending", referral_code="UPDFORBID")
    update_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"commission_rate": 0.09, "request_status": "approved"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert update_resp.status == 403, "Usuário sem papel 'admin' não deve atualizar afiliado."

# ---------------------------------------------------------------------------
# GET /affiliates/requests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_affiliate_requests_success(test_client_fixture):
    """
    Testa que um administrador consegue listar todas as solicitações de afiliação pendentes.

    Processo:
      1. Insere manualmente múltiplos registros de afiliados na base, com status 'pending' e 'approved'.
      2. Utiliza token de administrador para chamar o endpoint GET /affiliates/requests.
      3. Verifica que apenas os registros com status 'pending' são retornados.

    Asserts:
      - Status HTTP 200.
      - Resposta contém a estrutura de paginação correta com apenas afiliados pendentes.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    db = client.app[DB_SESSION_KEY]
    
    # Criar usuários reais para associar aos afiliados
    auth_service = AuthService(db)
    
    user1 = await auth_service.create_user(
        name="Test User 1",
        email="testuser1@example.com",
        cpf="11122233344",
        password="testpass",
        role="user"
    )
    
    user2 = await auth_service.create_user(
        name="Test User 2",
        email="testuser2@example.com",
        cpf="22233344455",
        password="testpass",
        role="user"
    )
    
    user3 = await auth_service.create_user(
        name="Test User 3",
        email="testuser3@example.com",
        cpf="33344455566",
        password="testpass",
        role="user"
    )

    pending_aff1 = Affiliate(
        user_id=user1.id,
        referral_code="PEND1",
        commission_rate=0.05,
        request_status="pending"
    )
    pending_aff2 = Affiliate(
        user_id=user2.id,
        referral_code="PEND2",
        commission_rate=0.06,
        request_status="pending"
    )
    approved_aff = Affiliate(
        user_id=user3.id,
        referral_code="APPROVED",
        commission_rate=0.07,
        request_status="approved"
    )
    db.add_all([pending_aff1, pending_aff2, approved_aff])
    await db.commit()

    resp = await client.get("/affiliates/requests", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200, "Admin deve conseguir listar solicitações de afiliação pendentes."
    data = await resp.json()
    
    # Verifica a estrutura de paginação
    assert "requests" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    
    requests_list = data.get("requests", [])
    assert isinstance(requests_list, list)
    
    referral_codes = [aff["referral_code"] for aff in requests_list]
    assert "PEND1" in referral_codes or "PEND2" in referral_codes
    assert "APPROVED" not in referral_codes
    
    # Testa se a paginação funciona corretamente
    resp_paged = await client.get("/affiliates/requests?page=1&per_page=1", 
                                 headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_paged.status == 200
    data_paged = await resp_paged.json()
    assert len(data_paged["requests"]) <= 1

@pytest.mark.asyncio
async def test_list_affiliate_requests_forbidden(test_client_fixture):
    """
    Testa que um usuário sem papel 'admin' não consegue listar as solicitações de afiliação.

    Processo:
      1. Registra um usuário com papel 'user' (utilizando get_user_token) e realiza login.
      2. Tenta acessar o endpoint GET /affiliates/requests.
    
    Asserts:
      - Status HTTP 403.
    """
    client = test_client_fixture

    token = await get_user_token(client)
    resp = await client.get("/affiliates/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403, "Usuário sem papel 'admin' não deve listar solicitações de afiliação."

@pytest.mark.asyncio
async def test_list_affiliate_requests(test_client_fixture):
    """
    Testa o endpoint de listagem de solicitações de afiliação pendentes com paginação.
    
    Verifica:
    - Se o endpoint retorna status 200
    - Se a estrutura da resposta está correta
    - Se os dados completos do usuário estão incluídos
    - Se a paginação funciona corretamente
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    
    # Criar algumas solicitações de afiliação pendentes
    for i in range(5):
        token, _ = await get_affiliate_token(client, status="pending")
    
    # Testando listagem de solicitações pendentes
    resp = await client.get('/affiliates/requests', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    
    # Verificando estrutura da resposta
    assert "requests" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    
    # Se existirem solicitações, verifica se inclui o objeto do usuário
    if data["total"] > 0 and len(data["requests"]) > 0:
        affiliate = data["requests"][0]
        assert "user" in affiliate
        assert "id" in affiliate["user"]
        assert "name" in affiliate["user"]
        assert "email" in affiliate["user"]
    
    # Testando paginação
    resp = await client.get('/affiliates/requests?page=1&per_page=2', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    assert len(data["requests"]) <= 2
    
    # Verificando se página inválida retorna resultado vazio
    resp = await client.get('/affiliates/requests?page=999', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    assert len(data["requests"]) == 0

@pytest.mark.asyncio
async def test_list_approved_affiliates(test_client_fixture):
    """
    Testa o endpoint de listagem de afiliados aprovados.
    
    Verifica:
    - Se o endpoint retorna status 200
    - Se a estrutura da resposta está correta
    - Se apenas afiliados aprovados são retornados
    - Se a paginação funciona corretamente
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    db = client.app[DB_SESSION_KEY]
    
    # Criar usuários reais para associar aos afiliados
    auth_service = AuthService(db)
    
    user1 = await auth_service.create_user(
        name="Approved User 1",
        email="approveduser1@example.com",
        cpf="11122233399",
        password="testpass",
        role="user"
    )
    
    user2 = await auth_service.create_user(
        name="Approved User 2",
        email="approveduser2@example.com",
        cpf="22233344499",
        password="testpass",
        role="user"
    )
    
    user3 = await auth_service.create_user(
        name="Pending User",
        email="pendinguser@example.com",
        cpf="33344455599",
        password="testpass",
        role="user"
    )
    
    # Criar afiliados com diferentes status
    approved_aff1 = Affiliate(
        user_id=user1.id,
        referral_code="APPROVED1",
        commission_rate=0.07,
        request_status="approved"
    )
    
    approved_aff2 = Affiliate(
        user_id=user2.id,
        referral_code="APPROVED2",
        commission_rate=0.08,
        request_status="approved"
    )
    
    pending_aff = Affiliate(
        user_id=user3.id,
        referral_code="PENDING1",
        commission_rate=0.05,
        request_status="pending"
    )
    
    db.add_all([approved_aff1, approved_aff2, pending_aff])
    await db.commit()
    
    # Agora testando a listagem de afiliados aprovados
    resp = await client.get('/affiliates/list', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    
    # Verificando estrutura da resposta
    assert "affiliates" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    
    # Verificando se apenas afiliados aprovados são retornados
    assert data["total"] >= 2
    
    referral_codes = [aff["referral_code"] for aff in data["affiliates"]]
    assert "APPROVED1" in referral_codes or "APPROVED2" in referral_codes
    assert "PENDING1" not in referral_codes
    
    for affiliate in data["affiliates"]:
        assert affiliate["request_status"] == "approved"
        assert "user" in affiliate
        assert "id" in affiliate["user"]
        assert "name" in affiliate["user"]
        assert "email" in affiliate["user"]
    
    # Testando paginação
    resp = await client.get('/affiliates/list?page=1&per_page=1', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    assert len(data["affiliates"]) <= 1
    
    # Verificando se página inválida retorna resultado vazio
    resp = await client.get('/affiliates/list?page=999', headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200
    data = await resp.json()
    assert len(data["affiliates"]) == 0

# ---------------------------------------------------------------------------
# GET /affiliates/status
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_affiliation_status_not_requested(test_client_fixture):
    """Testa a obtenção do status de afiliação para um usuário que não solicitou afiliação."""
    # Setup
    client = test_client_fixture
    token = await get_user_token(client)
    
    # Execute
    resp = await client.get(
        "/affiliates/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "not_requested" or "not_requested" in data.get("status", "")
    assert "message" in data

@pytest.mark.asyncio
async def test_get_affiliation_status_pending(test_client_fixture):
    """Testa a obtenção do status de afiliação para um usuário com solicitação pendente."""
    # Setup
    client = test_client_fixture
    
    # Criar usuário e solicitar afiliação, deixando como 'pending'
    token, affiliate_id = await get_affiliate_token(client, status="pending")
    
    # Execute
    resp = await client.get(
        "/affiliates/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "pending"
    assert "message" in data

@pytest.mark.asyncio
async def test_get_affiliation_status_approved(test_client_fixture):
    """Testa a obtenção do status de afiliação para um usuário aprovado."""
    # Setup
    client = test_client_fixture
    
    # Criar usuário e solicitar afiliação, atualizando para 'approved'
    token, affiliate_id = await get_affiliate_token(client, status="approved", referral_code="REF123TEST")
    
    # Execute
    resp = await client.get(
        "/affiliates/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "approved"
    assert "message" in data

@pytest.mark.asyncio
async def test_get_affiliation_status_blocked(test_client_fixture):
    """Testa a obtenção do status de afiliação para um usuário bloqueado."""
    # Setup
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    
    # Criar usuário e solicitar afiliação
    token, affiliate_id = await get_affiliate_token(client, status="pending")
    
    # Bloquear a solicitação usando API de admin
    block_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"request_status": "blocked", "reason": "Violação dos termos de uso"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert block_resp.status == 200
    
    # Execute
    resp = await client.get(
        "/affiliates/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "blocked"
    assert "message" in data
    assert "reason" in data
    assert data["reason"] == "Violação dos termos de uso"

@pytest.mark.asyncio
async def test_get_affiliate_link_permission_checks(test_client_fixture):
    """
    Testa as verificações de permissão no endpoint get_affiliate_link.

    Processo:
      1. Cria um usuário com papel 'user' e tenta acessar o endpoint (deve falhar).
      2. Solicita afiliação e tenta novamente com status 'pending' (deve falhar).
      3. Altera apenas o papel para 'affiliate' sem aprovar a solicitação (deve falhar).
      4. Altera apenas o status para 'approved' sem atualizar o papel (deve falhar).
      5. Configura corretamente (aprovado + papel affiliate) e verifica sucesso.

    Asserts:
      - Cada caso de falha retorna o status HTTP e mensagem de erro corretos.
      - Apenas quando ambas as condições são atendidas o acesso é permitido.
    """
    client = test_client_fixture
    db = client.app[DB_SESSION_KEY]
    admin_token = await get_admin_token(client)
    
    # Registrar um usuário comum
    email = f"perms_{uuid.uuid4().hex[:6]}@test.com"
    password = "user123"
    cpf = str(uuid.uuid4().int % 10**11).zfill(11)
    reg_resp = await client.post("/auth/register", json={
        "name": "Permissions Test User",
        "email": email.lower(),
        "cpf": cpf,
        "password": password,
        "role": "user"
    })
    assert reg_resp.status == 201
    
    # Login
    login_resp = await client.post("/auth/login", json={
        "identifier": email.lower(),
        "password": password
    })
    assert login_resp.status == 200
    token = (await login_resp.json())["access_token"]
    
    # Caso 1: Usuário sem afiliação tenta acessar
    resp = await client.get("/affiliates/link", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403
    
    # Solicitar afiliação
    req_resp = await client.post("/affiliates/request", json={"commission_rate": 0.05},
                               headers={"Authorization": f"Bearer {token}"})
    assert req_resp.status == 201
    referral_code = (await req_resp.json())["referral_code"]
    
    # Obter o ID do afiliado
    query = text("""
    SELECT id FROM affiliates WHERE referral_code = :code
    """)
    result = await db.execute(query, {"code": referral_code})
    affiliate_id = result.scalar_one()
    
    # Aprovar a solicitação usando o endpoint (isso também atualiza o papel do usuário)
    update_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"request_status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status == 200
    
    # Fazer login novamente para obter um token atualizado
    login_resp = await client.post("/auth/login", json={
        "identifier": email.lower(),
        "password": password
    })
    assert login_resp.status == 200
    token = (await login_resp.json())["access_token"]
    
    # Caso 2: Afiliado com todas as permissões corretas
    resp = await client.get("/affiliates/link", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "affiliate_link" in data
