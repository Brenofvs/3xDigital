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
            category_id=cat1.id,
            has_custom_commission=True,
            commission_type="percentage",
            commission_value=5.0
        ),
        Product(
            name="Produto 3",
            description="Descrição 3",
            price=300.0,
            stock=30,
            category_id=cat2.id,
            has_custom_commission=True,
            commission_type="fixed",
            commission_value=10.0
        )
    ]
    async_db_session.add_all(products)
    await async_db_session.commit()
    
    product_service = ProductService(async_db_session)
    
    # Listar todos os produtos
    result = await product_service.list_products()
    assert result["success"] is True
    assert "products" in result["data"]
    assert len(result["data"]["products"]) == 3
    
    # Verificar formato dos dados
    for product in result["data"]["products"]:
        assert "id" in product
        assert "name" in product
        assert "description" in product
        assert "price" in product
        assert "stock" in product
        assert "category_id" in product
        assert "has_custom_commission" in product
        assert "commission_type" in product
        assert "commission_value" in product
    
    # Verificar detalhes de comissão
    products_list = {p["name"]: p for p in result["data"]["products"]}
    
    assert products_list["Produto 1"]["has_custom_commission"] is False
    assert products_list["Produto 1"]["commission_type"] is None
    assert products_list["Produto 1"]["commission_value"] is None
    
    assert products_list["Produto 2"]["has_custom_commission"] is True
    assert products_list["Produto 2"]["commission_type"] == "percentage"
    assert products_list["Produto 2"]["commission_value"] == 5.0
    
    assert products_list["Produto 3"]["has_custom_commission"] is True
    assert products_list["Produto 3"]["commission_type"] == "fixed"
    assert products_list["Produto 3"]["commission_value"] == 10.0
    
    # Listar produtos por categoria
    result = await product_service.list_products(cat1.id)
    assert result["success"] is True
    assert len(result["data"]["products"]) == 2
    
    # Verificar que todos os produtos são da categoria correta
    for product in result["data"]["products"]:
        assert product["category_id"] == cat1.id
    
    # Verificar metadados de paginação
    assert "meta" in result["data"]
    assert "page" in result["data"]["meta"]
    assert "page_size" in result["data"]["meta"]
    assert "total_count" in result["data"]["meta"]
    assert "total_pages" in result["data"]["meta"]
    assert result["data"]["meta"]["page"] == 1  # Página padrão
    assert result["data"]["meta"]["total_count"] == 2  # Dois produtos na categoria 1

@pytest.mark.asyncio
async def test_list_products_with_pagination(async_db_session):
    """
    Testa a paginação na listagem de produtos.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se a paginação funciona corretamente.
        - Verifica se os metadados de paginação são calculados corretamente.
        - Verifica se offset e limit estão sendo aplicados corretamente.
    """
    # Criar categoria
    category = Category(name="Categoria Paginação")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    # Criar 10 produtos para testar paginação
    products = []
    for i in range(1, 11):
        products.append(
            Product(
                name=f"Produto Paginação {i}",
                description=f"Descrição {i}",
                price=100.0 * i,
                stock=10 * i,
                category_id=category.id
            )
        )
    async_db_session.add_all(products)
    await async_db_session.commit()
    
    product_service = ProductService(async_db_session)
    
    # Testar primeira página com 3 itens por página
    result = await product_service.list_products(None, page=1, page_size=3)
    assert result["success"] is True
    assert len(result["data"]["products"]) == 3
    assert result["data"]["meta"]["page"] == 1
    assert result["data"]["meta"]["page_size"] == 3
    assert result["data"]["meta"]["total_count"] == 10
    assert result["data"]["meta"]["total_pages"] == 4  # 10 itens / 3 por página = 4 páginas (arredondado para cima)
    
    # Verificar a segunda página
    result2 = await product_service.list_products(None, page=2, page_size=3)
    assert result2["success"] is True
    assert len(result2["data"]["products"]) == 3
    
    # Verificar que não há itens duplicados entre páginas
    page1_ids = [p["id"] for p in result["data"]["products"]]
    page2_ids = [p["id"] for p in result2["data"]["products"]]
    for pid in page2_ids:
        assert pid not in page1_ids
    
    # Testar última página (deve ter apenas 1 item)
    result4 = await product_service.list_products(None, page=4, page_size=3)
    assert result4["success"] is True
    assert len(result4["data"]["products"]) == 1
    
    # Testar categoria específica com paginação
    result_cat = await product_service.list_products(category.id, page=1, page_size=5)
    assert result_cat["success"] is True
    assert len(result_cat["data"]["products"]) == 5
    assert result_cat["data"]["meta"]["total_count"] == 10
    assert result_cat["data"]["meta"]["total_pages"] == 2
    
    # Verificar que todos os produtos são da categoria correta
    for product in result_cat["data"]["products"]:
        assert product["category_id"] == category.id

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
        image_url="/static/test.jpg",
        has_custom_commission=True,
        commission_type="percentage",
        commission_value=7.5
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
    assert result["data"]["has_custom_commission"] is True
    assert result["data"]["commission_type"] == "percentage"
    assert result["data"]["commission_value"] == 7.5
    
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
        - Verifica criação com comissão personalizada.
    """
    # Criar categoria
    category = Category(name="Nova Categoria")
    async_db_session.add(category)
    await async_db_session.commit()
    await async_db_session.refresh(category)
    
    product_service = ProductService(async_db_session)
    
    # Teste 1: Criar produto básico, sem comissão personalizada
    result = await product_service.create_product(
        name="Produto Básico",
        description="Descrição básica",
        price=99.90,
        stock=30,
        category_id=category.id
    )
    assert result["success"] is True
    assert result["data"]["name"] == "Produto Básico"
    assert result["data"]["price"] == 99.90
    assert result["data"]["stock"] == 30
    assert result["data"]["category_id"] == category.id
    assert result["data"]["has_custom_commission"] is False
    assert result["data"]["commission_type"] is None
    assert result["data"]["commission_value"] is None
    
    # Teste 2: Criar produto com comissão percentual
    result = await product_service.create_product(
        name="Produto Comissão Percentual",
        description="Descrição com comissão",
        price=150.0,
        stock=20,
        category_id=category.id,
        has_custom_commission=True,
        commission_type="percentage",
        commission_value=5.0
    )
    assert result["success"] is True
    assert result["data"]["name"] == "Produto Comissão Percentual"
    assert result["data"]["has_custom_commission"] is True
    assert result["data"]["commission_type"] == "percentage"
    assert result["data"]["commission_value"] == 5.0
    
    # Teste 3: Criar produto com comissão fixa
    result = await product_service.create_product(
        name="Produto Comissão Fixa",
        description="Descrição com comissão fixa",
        price=299.0,
        stock=10,
        category_id=category.id,
        has_custom_commission=True,
        commission_type="fixed",
        commission_value=15.0
    )
    assert result["success"] is True
    assert result["data"]["has_custom_commission"] is True
    assert result["data"]["commission_type"] == "fixed"
    assert result["data"]["commission_value"] == 15.0
    
    # Teste 4: Validar comissão percentual acima de 100%
    result = await product_service.create_product(
        name="Produto Comissão Inválida",
        description="Comissão percentual acima de 100%",
        price=100.0,
        stock=5,
        category_id=category.id,
        has_custom_commission=True,
        commission_type="percentage",
        commission_value=120.0
    )
    assert result["success"] is False
    assert "não pode ser maior que 100%" in result["error"]
    
    # Teste 5: Validar tipo de comissão inválido
    result = await product_service.create_product(
        name="Produto Tipo Inválido",
        description="Tipo de comissão inválido",
        price=100.0,
        stock=5,
        category_id=category.id,
        has_custom_commission=True,
        commission_type="invalid_type",
        commission_value=10.0
    )
    assert result["success"] is False
    assert "deve ser 'percentage' ou 'fixed'" in result["error"]

@pytest.mark.asyncio
async def test_update_product(async_db_session):
    """
    Testa a atualização de um produto.

    Args:
        async_db_session: Sessão de banco de dados assíncrona.
        
    Asserts:
        - Verifica se os dados do produto são atualizados corretamente.
        - Verifica validação de dados (preço, estoque).
        - Verifica validação de categoria.
        - Verifica atualização de comissão personalizada.
    """
    # Criar categoria
    category = Category(name="Categoria Update")
    category2 = Category(name="Categoria Update 2")
    async_db_session.add_all([category, category2])
    await async_db_session.commit()
    await async_db_session.refresh(category)
    await async_db_session.refresh(category2)
    
    # Criar produto para atualização
    product = Product(
        name="Produto para Atualizar",
        description="Descrição inicial",
        price=120.0,
        stock=10,
        category_id=category.id
    )
    async_db_session.add(product)
    await async_db_session.commit()
    await async_db_session.refresh(product)
    
    product_service = ProductService(async_db_session)
    
    # Teste 1: Atualizar campos básicos
    result = await product_service.update_product(
        product.id,
        name="Produto Atualizado",
        description="Descrição atualizada",
        price=150.0,
        stock=15,
        category_id=category2.id
    )
    assert result["success"] is True
    assert result["data"]["name"] == "Produto Atualizado"
    assert result["data"]["description"] == "Descrição atualizada"
    assert result["data"]["price"] == 150.0
    assert result["data"]["stock"] == 15
    assert result["data"]["category_id"] == category2.id
    
    # Teste 2: Ativar comissão personalizada (percentual)
    result = await product_service.update_product(
        product.id,
        has_custom_commission=True,
        commission_type="percentage",
        commission_value=8.5
    )
    assert result["success"] is True
    assert result["data"]["has_custom_commission"] is True
    assert result["data"]["commission_type"] == "percentage"
    assert result["data"]["commission_value"] == 8.5
    
    # Teste 3: Alterar para comissão fixa
    result = await product_service.update_product(
        product.id,
        commission_type="fixed",
        commission_value=12.0
    )
    assert result["success"] is True
    assert result["data"]["has_custom_commission"] is True
    assert result["data"]["commission_type"] == "fixed"
    assert result["data"]["commission_value"] == 12.0
    
    # Teste 4: Desativar comissão personalizada
    result = await product_service.update_product(
        product.id,
        has_custom_commission=False
    )
    assert result["success"] is True
    assert result["data"]["has_custom_commission"] is False
    assert result["data"]["commission_type"] is None
    assert result["data"]["commission_value"] is None
    
    # Teste 5: Validação de percentual acima de 100%
    result = await product_service.update_product(
        product.id,
        has_custom_commission=True,
        commission_type="percentage",
        commission_value=150.0
    )
    assert result["success"] is False
    assert "não pode ser maior que 100%" in result["error"]
    
    # Teste 6: Tipo de comissão inválido
    result = await product_service.update_product(
        product.id,
        has_custom_commission=True,
        commission_type="invalid_type",
        commission_value=10.0
    )
    assert result["success"] is False
    assert "deve ser 'percentage' ou 'fixed'" in result["error"]
    
    # Testes de validação de dados básicos
    
    # Preço negativo
    result = await product_service.update_product(product.id, price=-10.0)
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Estoque negativo
    result = await product_service.update_product(product.id, stock=-1)
    assert result["success"] is False
    assert "negativo" in result["error"]
    
    # Categoria inexistente
    result = await product_service.update_product(product.id, category_id=9999)
    assert result["success"] is False
    assert "Categoria não encontrada" in result["error"]
    
    # Produto inexistente
    result = await product_service.update_product(9999, name="Inexistente")
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
        - Verifica se o caminho e a URL da imagem são gerados corretamente.
        - Verifica padrão de nomenclatura da imagem.
    """
    product_service = ProductService(async_db_session)

    # Criar um objeto simulando um arquivo
    test_image = io.BytesIO(b"fake image content")
    test_image.filename = "test_image.jpg"

    # Salvar a imagem
    image_path, image_url = await product_service.save_image(test_image)

    # Verificar formato do caminho e da URL
    assert image_path.startswith("uploads/")
    assert image_url.startswith("/static/uploads/")
    
    # Verificar se o nome do arquivo está no caminho e na URL
    assert "test_image.jpg" in image_path
    assert "test_image.jpg" in image_url 