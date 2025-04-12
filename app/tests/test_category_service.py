# D:\3xDigital\app\tests\test_category_service.py

"""
test_category_service.py

Este módulo contém os testes unitários para o CategoryService, responsável pela lógica
de gerenciamento de categorias de produtos.

Fixtures:
    async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

Test Functions:
    - test_list_categories: Testa a listagem de categorias.
    - test_get_category: Testa a obtenção de detalhes de uma categoria.
    - test_create_category: Testa a criação de uma categoria.
    - test_update_category: Testa a atualização de uma categoria.
    - test_delete_category: Testa a exclusão de uma categoria.
    - test_has_associated_products: Testa a verificação de produtos associados a uma categoria.
    - test_list_categories_with_pagination: Testa a paginação e filtro de busca na listagem de categorias.
"""

import pytest
from app.services.category_service import CategoryService
from app.models.database import Category, Product

@pytest.mark.asyncio
async def test_list_categories(async_db_session):
    """
    Testa a listagem de categorias.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a lista de categorias é retornada corretamente.
        - Verifica se os dados das categorias estão completos.
        - Verifica se os metadados de paginação estão presentes.
    """
    # Criar categorias diretamente no banco
    categories = [
        Category(name="Eletrônicos"),
        Category(name="Roupas"),
        Category(name="Alimentos")
    ]
    async_db_session.add_all(categories)
    await async_db_session.commit()
    
    # Listar categorias
    category_service = CategoryService(async_db_session)
    result = await category_service.list_categories()
    
    # Verificações
    assert result["success"] is True
    assert "categories" in result["data"]
    assert len(result["data"]["categories"]) == 3
    
    # Verificar que todas as categorias criadas estão na lista
    category_names = [c["name"] for c in result["data"]["categories"]]
    assert "Eletrônicos" in category_names
    assert "Roupas" in category_names
    assert "Alimentos" in category_names
    
    # Verificar formato dos dados
    for category in result["data"]["categories"]:
        assert "id" in category
        assert "name" in category
    
    # Verificar metadados de paginação
    assert "meta" in result["data"]
    assert "page" in result["data"]["meta"]
    assert "page_size" in result["data"]["meta"]
    assert "total_count" in result["data"]["meta"]
    assert "total_pages" in result["data"]["meta"]
    assert result["data"]["meta"]["page"] == 1  # Página padrão
    assert result["data"]["meta"]["total_count"] == 3  # Três categorias

@pytest.mark.asyncio
async def test_list_categories_with_pagination(async_db_session):
    """
    Testa a paginação e filtro de busca na listagem de categorias.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a paginação funciona corretamente.
        - Verifica se o filtro de busca por nome funciona.
        - Verifica se os metadados de paginação são calculados corretamente.
    """
    # Criar categorias para testar paginação e busca
    categories = []
    for i in range(1, 11):
        if i <= 5:
            # Primeiras 5 categorias com padrão "Esporte"
            categories.append(Category(name=f"Esporte {i}"))
        else:
            # Últimas 5 categorias com padrão "Tecnologia"
            categories.append(Category(name=f"Tecnologia {i-5}"))
    
    async_db_session.add_all(categories)
    await async_db_session.commit()
    
    category_service = CategoryService(async_db_session)
    
    # Testar primeira página com 3 itens por página
    result = await category_service.list_categories(page=1, page_size=3)
    assert result["success"] is True
    assert len(result["data"]["categories"]) == 3
    assert result["data"]["meta"]["page"] == 1
    assert result["data"]["meta"]["page_size"] == 3
    assert result["data"]["meta"]["total_count"] == 10
    assert result["data"]["meta"]["total_pages"] == 4  # 10 itens / 3 por página = 4 páginas (arredondado para cima)
    
    # Verificar a segunda página
    result2 = await category_service.list_categories(page=2, page_size=3)
    assert result2["success"] is True
    assert len(result2["data"]["categories"]) == 3
    
    # Verificar que não há categorias duplicadas entre páginas
    page1_ids = [c["id"] for c in result["data"]["categories"]]
    page2_ids = [c["id"] for c in result2["data"]["categories"]]
    for cid in page2_ids:
        assert cid not in page1_ids
    
    # Testar última página (deve ter apenas 1 item)
    result4 = await category_service.list_categories(page=4, page_size=3)
    assert result4["success"] is True
    assert len(result4["data"]["categories"]) == 1
    
    # Testar filtro de busca por "Esporte" (deve ter 5 categorias)
    result_esporte = await category_service.list_categories(search="Esporte")
    assert result_esporte["success"] is True
    assert len(result_esporte["data"]["categories"]) == 5
    assert result_esporte["data"]["meta"]["total_count"] == 5
    
    # Verificar que todas as categorias contêm "Esporte" no nome
    for category in result_esporte["data"]["categories"]:
        assert "Esporte" in category["name"]
    
    # Testar filtro de busca por "Tecnologia" (deve ter 5 categorias)
    result_tecnologia = await category_service.list_categories(search="Tecnologia")
    assert result_tecnologia["success"] is True
    assert len(result_tecnologia["data"]["categories"]) == 5
    assert result_tecnologia["data"]["meta"]["total_count"] == 5
    
    # Testar busca com correspondência parcial, por exemplo, "Tec"
    result_tec = await category_service.list_categories(search="Tec")
    assert result_tec["success"] is True
    assert len(result_tec["data"]["categories"]) == 5
    
    # Testar busca por categoria específica, por número
    result_especifica = await category_service.list_categories(search="Esporte 3")
    assert result_especifica["success"] is True
    assert len(result_especifica["data"]["categories"]) == 1

@pytest.mark.asyncio
async def test_get_category(async_db_session):
    """
    Testa a obtenção de detalhes de uma categoria.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se os detalhes da categoria são retornados corretamente.
        - Verifica comportamento com categoria inexistente.
    """
    # Criar categoria
    category = Category(name="Livros")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Obter categoria
    category_service = CategoryService(async_db_session)
    result = await category_service.get_category(category.id)
    
    # Verificações
    assert result["success"] is True
    assert result["data"]["id"] == category.id
    assert result["data"]["name"] == "Livros"
    
    # Testar com ID inexistente
    result = await category_service.get_category(9999)
    assert result["success"] is False
    assert "não encontrada" in result["error"]

@pytest.mark.asyncio
async def test_create_category(async_db_session):
    """
    Testa a criação de uma categoria.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a categoria é criada com sucesso.
        - Verifica validação de nome vazio.
        - Verifica validação de nome duplicado.
    """
    category_service = CategoryService(async_db_session)
    
    # Criar categoria válida
    result = await category_service.create_category("Móveis")
    assert result["success"] is True
    assert result["data"]["name"] == "Móveis"
    assert "id" in result["data"]
    
    # Tentar criar com nome vazio
    result = await category_service.create_category("")
    assert result["success"] is False
    assert "não pode ser vazio" in result["error"]
    
    # Tentar criar com nome duplicado
    result = await category_service.create_category("Móveis")
    assert result["success"] is False
    assert "já existe" in result["error"]

@pytest.mark.asyncio
async def test_update_category(async_db_session):
    """
    Testa a atualização de uma categoria.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a categoria é atualizada com sucesso.
        - Verifica validação de nome vazio.
        - Verifica validação de nome duplicado.
        - Verifica comportamento com categoria inexistente.
    """
    # Criar categorias
    category1 = Category(name="Jogos")
    category2 = Category(name="Acessórios")
    async_db_session.add_all([category1, category2])
    await async_db_session.commit()
    await async_db_session.refresh(category1)
    await async_db_session.refresh(category2)
    
    category_service = CategoryService(async_db_session)
    
    # Atualizar categoria - nome válido
    result = await category_service.update_category(category1.id, "Videogames")
    assert result["success"] is True
    assert result["data"]["name"] == "Videogames"
    
    # Tentar atualizar com nome vazio
    result = await category_service.update_category(category1.id, "")
    assert result["success"] is False
    assert "não pode ser vazio" in result["error"]
    
    # Tentar atualizar com nome duplicado
    result = await category_service.update_category(category1.id, "Acessórios")
    assert result["success"] is False
    assert "já existe" in result["error"]
    
    # Tentar atualizar categoria inexistente
    result = await category_service.update_category(9999, "Nova Categoria")
    assert result["success"] is False
    assert "não encontrada" in result["error"]

@pytest.mark.asyncio
async def test_delete_category(async_db_session):
    """
    Testa a exclusão de uma categoria.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a categoria é excluída com sucesso.
        - Verifica comportamento com categoria inexistente.
        - Verifica comportamento quando a categoria possui produtos.
    """
    # Criar categoria
    category = Category(name="Para Deletar")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    category_service = CategoryService(async_db_session)
    
    # Excluir categoria
    result = await category_service.delete_category(category.id)
    assert result["success"] is True
    assert result["data"]["id"] == category.id
    assert result["data"]["name"] == "Para Deletar"
    
    # Verificar que a categoria foi excluída
    get_result = await category_service.get_category(category.id)
    assert get_result["success"] is False
    
    # Tentar excluir categoria inexistente
    result = await category_service.delete_category(9999)
    assert result["success"] is False
    assert "não encontrada" in result["error"]
    
    # Criar categoria com produto associado
    category2 = Category(name="Com Produto")
    async_db_session.add(category2)
    await async_db_session.commit()
    await async_db_session.refresh(category2)
    
    # Adicionar produto à categoria
    product = Product(
        name="Produto Teste",
        description="Produto para testar exclusão",
        price=10.0,
        stock=5,
        category_id=category2.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    
    # Tentar excluir categoria com produto
    result = await category_service.delete_category(category2.id)
    assert result["success"] is False
    assert "produtos associados" in result["error"]

@pytest.mark.asyncio
async def test_has_associated_products(async_db_session):
    """
    Testa a verificação de produtos associados a uma categoria.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica detecção correta de produtos associados.
        - Verifica comportamento quando não há produtos associados.
    """
    # Criar categorias
    category1 = Category(name="Com Produtos")
    category2 = Category(name="Sem Produtos")
    async_db_session.add_all([category1, category2])
    await async_db_session.commit()
    await async_db_session.refresh(category1)
    await async_db_session.refresh(category2)
    
    # Adicionar produto à primeira categoria
    product = Product(
        name="Produto de Teste",
        description="Para testar associação",
        price=20.0,
        stock=10,
        category_id=category1.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    
    category_service = CategoryService(async_db_session)
    
    # Verificar categoria com produto
    has_products = await category_service.has_associated_products(category1.id)
    assert has_products is True
    
    # Verificar categoria sem produto
    has_products = await category_service.has_associated_products(category2.id)
    assert has_products is False
    
    # Verificar categoria inexistente
    has_products = await category_service.has_associated_products(9999)
    assert has_products is False 