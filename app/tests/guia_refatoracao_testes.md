# Guia de Refatoração de Testes

Este documento fornece instruções sobre como refatorar os testes de views existentes para utilizarem os novos services, seguindo a arquitetura baseada no princípio da Responsabilidade Única (SRP) do SOLID.

## Princípios da Refatoração

1. **Mantenha os testes existentes funcionando** - O comportamento externo não deve mudar, apenas a implementação interna.
2. **Privilegie o uso de mocks para services** - Em testes de views, o ideal é mockar os services para isolar a camada de visualização.
3. **Teste cada camada independentemente** - Views já têm seus próprios testes e services também têm os deles.

## Passo a Passo para Refatoração

### 1. Importe o Service Correspondente

```python
# Antes
from app.models.database import Affiliate, Sale

# Depois
from app.services.affiliate_service import AffiliateService
```

### 2. Injeção do Service na View

Nas views, o padrão é injetar o service utilizando a sessão do banco de dados:

```python
# No teste atual
db = request.app[DB_SESSION_KEY]
result = await db.execute(select(Affiliate).where(...))

# No teste refatorado
db = request.app[DB_SESSION_KEY]
affiliate_service = AffiliateService(db)
result = await affiliate_service.get_affiliate_by_id(affiliate_id)
```

### 3. Adaptação das Verificações (Asserts)

Os services retornam resultados em formato padronizado:

```python
# Antes
assert response.status == 200
data = await response.json()
assert "affiliate_link" in data

# Depois (mantém-se o mesmo, já que a interface da view não muda)
assert response.status == 200
data = await response.json()
assert "affiliate_link" in data
```

### 4. Exemplo de Refatoração Completa

#### Teste Original:

```python
@pytest.mark.asyncio
async def test_get_affiliate_link_success(test_client_fixture):
    """
    Testa a obtenção do link de afiliado com sucesso.
    """
    client = test_client_fixture
    token, affiliate_id = await get_affiliate_token(client, status="approved")
    
    resp = await client.get("/affiliates/link",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "affiliate_link" in data
    assert "ref=" in data["affiliate_link"]
```

#### Teste Refatorado (via mockup do service):

```python
@pytest.mark.asyncio
async def test_get_affiliate_link_success(test_client_fixture, mocker):
    """
    Testa a obtenção do link de afiliado com sucesso.
    """
    client = test_client_fixture
    token, affiliate_id = await get_affiliate_token(client, status="approved")
    
    # Mock para AffiliateService.get_affiliate_link
    mock_get_link = mocker.patch('app.services.affiliate_service.AffiliateService.get_affiliate_link')
    mock_get_link.return_value = {
        "success": True, 
        "data": "https://example.com/?ref=TESTCODE", 
        "error": None
    }
    
    resp = await client.get("/affiliates/link",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "affiliate_link" in data
    assert "ref=" in data["affiliate_link"]
```

#### Teste Refatorado (mantendo integração):

```python
@pytest.mark.asyncio
async def test_get_affiliate_link_success(test_client_fixture):
    """
    Testa a obtenção do link de afiliado com sucesso.
    """
    client = test_client_fixture
    token, affiliate_id = await get_affiliate_token(client, status="approved")
    
    resp = await client.get("/affiliates/link",
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    data = await resp.json()
    assert "affiliate_link" in data
    assert "ref=" in data["affiliate_link"]
```

## Observações Importantes

1. **Testes de Integração vs. Unitários**:
   - Se o objetivo é testar apenas a view, use mocks para os services.
   - Se o objetivo é testar a integração completa, mantenha a chamada real aos services.

2. **Mantendo a Compatibilidade**:
   - As APIs das views não mudam, apenas a implementação interna.
   - Os testes ainda verificam o mesmo comportamento externo.

3. **Estrutura dos Retornos de Services**:
   - Todos os services retornam objetos com formato padronizado `{"success": bool, "data": Any, "error": str}`.
   - As views tratam esses retornos e enviam as respostas HTTP apropriadas.

## Esquema de Refatoração por Módulo

1. **affiliates_views.py ➔ AffiliateService**:
   - Todas as operações com `Affiliate` e `Sale` vão para o service.
   - A view apenas coordena a autenticação, validação e formatação da resposta.

2. **orders_views.py ➔ OrderService**:
   - Processamento de pedidos, validação de itens e interação com afiliados vão para o service.
   - A view lida com os aspectos HTTP e formatação da resposta.

3. **categories_views.py ➔ CategoryService**:
   - CRUD de categorias vai para o service.
   - Validações mais complexas como produtos associados são tratadas pelo service.

4. **products_views.py ➔ ProductService**:
   - CRUD de produtos e manipulação de imagens vão para o service.
   - A view trata aspectos de formulário, upload e formatação da resposta. 