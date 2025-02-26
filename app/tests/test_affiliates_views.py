# D:\#3xDigital\app\tests\test_affiliates_views.py

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
"""

import uuid
import pytest
from app.config.settings import DB_SESSION_KEY
from app.models.database import Affiliate, Sale
from app.tests.utils.auth_utils import get_admin_token, get_user_token, get_affiliate_token

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
    assert "Afiliado inativo" in data.get("error", "")

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
    assert "Afiliado inativo" in data.get("error", "")

# ---------------------------------------------------------------------------
# POST /affiliates/request
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_request_affiliation_success(test_client_fixture):
    """
    Testa a solicitação de afiliação com sucesso por um usuário com papel 'user'.

    Processo:
      1. Utiliza o utilitário get_affiliate_token para registrar, logar e solicitar afiliação.
      2. Verifica se o registro de afiliação foi criado com sucesso (através do token e do ID retornado).

    Asserts:
      - O fluxo retorna um token e um ID de afiliado.
    """
    client = test_client_fixture

    token, affiliate_id = await get_affiliate_token(client)
    # Se o fluxo não lançar exceção, entende-se que a solicitação foi realizada com sucesso.
    assert token is not None, "Token não retornado na solicitação de afiliação."
    assert affiliate_id is not None, "ID do afiliado não retornado na solicitação de afiliação."


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

    Asserts:
      - Status HTTP 200.
      - Mensagem de sucesso na atualização.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)

    token, affiliate_id = await get_affiliate_token(client, status="pending", referral_code="UPDATECODE")
    update_resp = await client.put(
        f"/affiliates/{affiliate_id}",
        json={"commission_rate": 0.08, "request_status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status == 200, "Admin deveria conseguir atualizar os dados do afiliado."
    data = await update_resp.json()
    assert "atualizados com sucesso" in data.get("message", "")

    db = client.app[DB_SESSION_KEY]
    from sqlalchemy import select
    result = await db.execute(select(Affiliate).where(Affiliate.id == affiliate_id))
    updated_affiliate = result.scalar()
    assert updated_affiliate.commission_rate == 0.08
    assert updated_affiliate.request_status == "approved"


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
      - Resposta contém a chave "affiliate_requests" com somente os afiliados pendentes.
    """
    client = test_client_fixture
    admin_token = await get_admin_token(client)
    db = client.app[DB_SESSION_KEY]

    pending_aff1 = Affiliate(
        user_id="user1",
        referral_code="PEND1",
        commission_rate=0.05,
        request_status="pending"
    )
    pending_aff2 = Affiliate(
        user_id="user2",
        referral_code="PEND2",
        commission_rate=0.06,
        request_status="pending"
    )
    approved_aff = Affiliate(
        user_id="user3",
        referral_code="APPROVED",
        commission_rate=0.07,
        request_status="approved"
    )
    db.add_all([pending_aff1, pending_aff2, approved_aff])
    await db.commit()

    resp = await client.get("/affiliates/requests", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status == 200, "Admin deve conseguir listar solicitações de afiliação pendentes."
    data = await resp.json()
    requests_list = data.get("affiliate_requests", [])
    assert isinstance(requests_list, list)
    referral_codes = [aff["referral_code"] for aff in requests_list]
    assert "PEND1" in referral_codes
    assert "PEND2" in referral_codes
    assert "APPROVED" not in referral_codes


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
