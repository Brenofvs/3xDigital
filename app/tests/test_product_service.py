# D:\3xDigital\app\tests\test_product_service.py

"""
test_product_service.py

Este módulo contém os testes unitários para o ProductService, responsável pela lógica
de gerenciamento de produtos, incluindo CRUD, upload de imagens e controle de estoque.

Fixtures:
    async_db_session: Sessão de banco de dados assíncrona fornecida pelo fixture.

Test Functions:
    - test_list_products: Testa a listagem de produtos.
    - test_get_product: Testa a obtenção de detalhes de um produto.
    - test_create_product: Testa a criação de um produto.
    - test_update_product: Testa a atualização de um produto.
    - test_delete_product: Testa a exclusão de um produto.
    - test_update_stock: Testa a atualização de estoque de um produto.
    - test_validate_category: Testa a validação de categorias.
"""

import pytest
import os
import io
from app.services.category_service import CategoryService
from app.services.product_service import ProductService
from app.models.database import Category, Product

@pytest.mark.asyncio
async def test_list_products(async_db_session):
    """
    Testa a listagem de produtos.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a lista de produtos é retornada corretamente.
        - Verifica o filtro por categoria.
        - Verifica se os dados dos produtos estão completos.
    """
    # Criar categorias
    cat1 = Category(name="Categoria 1")
    cat2 = Category(name="Categoria 2")
    async_db_session.add_all([cat1, cat2])
    await async_db_session.commit()
    await async_db_session.refresh(cat1)
    await async_db_session.refresh(cat2)
    
    # Criar produtos
    products = [
        Product(
            name="Produto 1",
            description="Descrição 1",
            price=100.0,
            stock=10,
            category_id=cat1.id
        ),
        Product(
            name="Produto 2",
            description="Descrição 2",
            price=200.0,
            stock=20,
            category_id=cat1.id
        ),
        Product(
            name="Produto 3",
            description="Descrição 3",
            price=300.0,
            stock=30,
            category_id=cat2.id
        )
    ]
    async_db_session.add_all(products)
    await async_db_session.commit()
    
    product_service = ProductService(async_db_session)
    
    # Listar todos os produtos
    result = await product_service.list_products()
    assert result["success"] is True
    assert len(result["data"]) == 3
    
    # Verificar formato dos dados
    for product in result["data"]:
        assert "id" in product
        assert "name" in product
        assert "description" in product
        assert "price" in product
        assert "stock" in product
        assert "category_id" in product
    
    # Listar produtos por categoria
    result = await product_service.list_products(cat1.id)
    assert result["success"] is True
    assert len(result["data"]) == 2
    
    # Verificar que todos os produtos são da categoria correta
    for product in result["data"]:
        assert product["category_id"] == cat1.id

@pytest.mark.asyncio
async def test_get_product(async_db_session):
    """
    Testa a obtenção de detalhes de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se os detalhes do produto são retornados corretamente.
        - Verifica comportamento com produto inexistente.
    """
    # Criar categoria
    category = Category(name="Teste Get")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Criar produto
    product = Product(
        name="Produto Detalhes",
        description="Descrição detalhada",
        price=150.0,
        stock=15,
        category_id=category.id,
        image_url="/static/test.jpg"
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    product_service = ProductService(async_db_session)
    
    # Obter produto válido
    result = await product_service.get_product(product.id)
    assert result["success"] is True
    assert result["data"]["id"] == product.id
    assert result["data"]["name"] == "Produto Detalhes"
    assert result["data"]["description"] == "Descrição detalhada"
    assert result["data"]["price"] == 150.0
    assert result["data"]["stock"] == 15
    assert result["data"]["category_id"] == category.id
    assert result["data"]["image_url"] == "/static/test.jpg"
    
    # Testar com ID inválido
    result = await product_service.get_product(9999)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_create_product(async_db_session):
    """
    Testa a criação de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o produto é criado com sucesso.
        - Verifica validação de dados (nome, preço, estoque).
        - Verifica validação de categoria.
    """
    # Criar categoria
    category = Category(name="Nova Categoria")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    product_service = ProductService(async_db_session)
    
    # Criar produto válido
    result = await product_service.create_product(
        name="Novo Produto",
        description="Nova descrição",
        price=250.0,
        stock=25,
        category_id=category.id,
        image_url="/static/novo.jpg"
    )
    
    # Verificações
    assert result["success"] is True
    assert result["data"]["name"] == "Novo Produto"
    assert result["data"]["price"] == 250.0
    assert result["data"]["stock"] == 25
    assert result["data"]["category_id"] == category.id
    assert result["data"]["image_url"] == "/static/novo.jpg"
    
    # Testar validações
    
    # Nome vazio
    result = await product_service.create_product(
        name="",
        description="Descrição teste",
        price=100.0,
        stock=10,
        category_id=category.id
    )
    assert result["success"] is False
    assert "vazio" in result["error"]
    
    # Preço negativo
    result = await product_service.create_product(
        name="Produto Preço",
        description="Descrição teste",
        price=-50.0,
        stock=10,
        category_id=category.id
    )
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Estoque negativo
    result = await product_service.create_product(
        name="Produto Estoque",
        description="Descrição teste",
        price=50.0,
        stock=-5,
        category_id=category.id
    )
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Categoria inexistente
    result = await product_service.create_product(
        name="Produto Categoria",
        description="Descrição teste",
        price=50.0,
        stock=5,
        category_id=9999
    )
    assert result["success"] is False
    assert "Categoria não encontrada" in result["error"]

@pytest.mark.asyncio
async def test_update_product(async_db_session):
    """
    Testa a atualização de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o produto é atualizado com sucesso.
        - Verifica validação de dados.
        - Verifica comportamento com produto inexistente.
    """
    # Criar categorias
    cat1 = Category(name="Categoria Update 1")
    cat2 = Category(name="Categoria Update 2")
    async_db_session.add_all([cat1, cat2])
    await async_db_session.commit()
    await async_db_session.refresh(cat1)
    await async_db_session.refresh(cat2)
    
    # Criar produto
    product = Product(
        name="Produto Original",
        description="Descrição original",
        price=100.0,
        stock=10,
        category_id=cat1.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    product_service = ProductService(async_db_session)
    
    # Atualizar produto - todos os campos
    result = await product_service.update_product(
        product.id,
        name="Produto Atualizado",
        description="Descrição atualizada",
        price=200.0,
        stock=20,
        category_id=cat2.id,
        image_url="/static/updated.jpg"
    )
    
    # Verificações
    assert result["success"] is True
    assert result["data"]["name"] == "Produto Atualizado"
    assert result["data"]["description"] == "Descrição atualizada"
    assert result["data"]["price"] == 200.0
    assert result["data"]["stock"] == 20
    assert result["data"]["category_id"] == cat2.id
    assert result["data"]["image_url"] == "/static/updated.jpg"
    
    # Atualizar apenas alguns campos
    result = await product_service.update_product(
        product.id,
        name="Produto Parcial",
        price=150.0
    )
    
    assert result["success"] is True
    assert result["data"]["name"] == "Produto Parcial"
    assert result["data"]["price"] == 150.0
    assert result["data"]["description"] == "Descrição atualizada"  # Não alterado
    
    # Validações
    
    # Preço negativo
    result = await product_service.update_product(
        product.id,
        price=-50.0
    )
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Produto inexistente
    result = await product_service.update_product(
        9999,
        name="Não existe"
    )
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_delete_product(async_db_session):
    """
    Testa a exclusão de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o produto é excluído com sucesso.
        - Verifica comportamento com produto inexistente.
    """
    # Criar categoria
    category = Category(name="Categoria Exclusão")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Criar produto
    product = Product(
        name="Produto para Excluir",
        description="Será excluído",
        price=50.0,
        stock=5,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    product_service = ProductService(async_db_session)
    
    # Excluir produto
    result = await product_service.delete_product(product.id)
    assert result["success"] is True
    assert result["data"]["id"] == product.id
    assert result["data"]["name"] == "Produto para Excluir"
    
    # Verificar que o produto foi excluído
    result = await product_service.get_product(product.id)
    assert result["success"] is False
    
    # Tentar excluir produto inexistente
    result = await product_service.delete_product(9999)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_update_stock(async_db_session):
    """
    Testa a atualização de estoque de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se o estoque é atualizado corretamente.
        - Verifica validação de quantidade negativa.
        - Verifica comportamento com produto inexistente.
    """
    # Criar categoria
    category = Category(name="Categoria Estoque")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Criar produto
    product = Product(
        name="Produto com Estoque",
        description="Para atualizar estoque",
        price=75.0,
        stock=15,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    product_service = ProductService(async_db_session)
    
    # Atualizar estoque
    result = await product_service.update_stock(product.id, 30)
    assert result["success"] is True
    assert result["data"]["stock"] == 30
    
    # Verificar no banco
    await async_db_session.refresh(product)
    assert product.stock == 30
    
    # Tentar atualizar com quantidade negativa
    result = await product_service.update_stock(product.id, -5)
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Tentar atualizar produto inexistente
    result = await product_service.update_stock(9999, 10)
    assert result["success"] is False
    assert "não encontrado" in result["error"]

@pytest.mark.asyncio
async def test_validate_category(async_db_session):
    """
    Testa a validação de categorias.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se categoria válida é identificada.
        - Verifica se categoria inexistente é rejeitada.
    """
    # Criar categoria
    category = Category(name="Categoria Validação")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    product_service = ProductService(async_db_session)
    
    # Validar categoria existente
    is_valid = await product_service.validate_category(category.id)
    assert is_valid is True
    
    # Validar categoria inexistente
    is_valid = await product_service.validate_category(9999)
    assert is_valid is False

@pytest.mark.asyncio
async def test_save_image(async_db_session):
    """
    Testa o salvamento de imagens.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a URL da imagem é gerada corretamente.
        - Verifica padrão de nomenclatura da imagem.
    """
    product_service = ProductService(async_db_session)
    
    # Criar um objeto simulando um arquivo
    test_image = io.BytesIO(b"fake image content")
    test_image.filename = "test_image.jpg"
    
    # Salvar a imagem
    url = await product_service.save_image(test_image)
    
    # Verificar formato da URL
    assert url.startswith("/static/uploads/")
    assert url.endswith("_test_image.jpg")
    
    # Verificar que o diretório foi criado
    assert os.path.exists("static/uploads")
    
    # Limpar arquivos criados após o teste
    image_path = "." + url
    if os.path.exists(image_path):
        os.remove(image_path) 