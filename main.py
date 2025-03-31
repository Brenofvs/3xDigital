# D:\3xDigital\main.py

"""
main.py

Este módulo inicializa e executa a aplicação AIOHTTP. Ele configura o banco de dados,
registra as rotas e inicia o servidor web.

Classes:
    Nenhuma.

Functions:
    init_app() -> web.Application:
        Inicializa a aplicação, configurando o banco de dados e as rotas.

    main() -> None:
        Executa a aplicação e inicia o servidor.
"""

import asyncio
from aiohttp import web
from app.models.database import create_database, get_session_maker, get_async_engine
from app.views.auth_views import routes as auth_routes
from app.views.categories_views import routes as categories_routes
from app.views.products_views import routes as products_routes
from app.views.orders_views import routes as orders_routes
from app.views.affiliates_views import routes as affiliates_routes
from app.views.finance_views import routes as finance_routes
from app.views.users_views import routes as users_routes
from app.views.payment_views import routes as payment_routes
from app.views.profile_views import routes as profile_routes
from app.views.dashboard_views import routes as dashboard_routes
from app.config.settings import DATABASE_URL, DB_SESSION_KEY
from app.middleware.cors_middleware import setup_cors

async def init_app():
    """
    Inicializa a aplicação, criando as tabelas do banco de dados e configurando rotas.

    Configura o motor assíncrono do banco de dados e a sessão. Registra as rotas
    definidas nos módulos de autenticação, categorias e produtos.

    Returns:
        web.Application: Instância configurada da aplicação AIOHTTP.
    """
    # Configuração do banco de dados
    engine = get_async_engine(DATABASE_URL)
    session_maker = get_session_maker(engine)

    # Cria as tabelas do banco de dados
    await create_database(DATABASE_URL)

    # Configuração da aplicação AIOHTTP
    app = web.Application()
    app[DB_SESSION_KEY] = session_maker()

    # Registra as rotas de autenticação, categorias e produtos
    app.add_routes(auth_routes)
    app.add_routes(categories_routes)
    app.add_routes(products_routes)
    app.add_routes(orders_routes)
    app.add_routes(affiliates_routes)
    app.add_routes(finance_routes)
    app.add_routes(users_routes)
    app.add_routes(payment_routes)
    app.add_routes(profile_routes)
    app.add_routes(dashboard_routes)

    # Configuração do CORS
    setup_cors(app)

    return app

async def main():
    """
    Executa a aplicação.

    Inicializa a aplicação e inicia o servidor web na porta 8000.
    """
    app = await init_app()
    return app

if __name__ == "__main__":
    web.run_app(asyncio.run(main()), host="0.0.0.0", port=8000)
