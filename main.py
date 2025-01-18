# D:\#3xDigital\main.py

import asyncio
from aiohttp import web
from app.models.database import create_database, get_session_maker, get_async_engine
from app.views.auth_views import routes
from app.config.settings import DATABASE_URL, DB_SESSION_KEY

async def init_app():
    """
    Inicializa a aplicação, criando as tabelas do banco de dados e configurando rotas.
    """
    # Configuração do banco de dados
    engine = get_async_engine(DATABASE_URL)
    session_maker = get_session_maker(engine)

    # Cria as tabelas do banco de dados
    await create_database(DATABASE_URL)

    # Configuração da aplicação AIOHTTP
    app = web.Application()
    app[DB_SESSION_KEY] = session_maker()

    # Registra as rotas
    app.add_routes(routes)

    return app

def main():
    """
    Executa a aplicação.
    """
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
