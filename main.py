# D:\#3xDigital\main.py

import asyncio
from aiohttp import web

from app.models.database import create_database
from app.views.auth_views import routes

async def init_app():
    # Cria as tabelas no banco caso não existam
    await create_database()  # Usa o default "sqlite+aiosqlite:///./3x_digital.db"

    # Cria a instância do AIOHTTP
    app = web.Application()

    # Registra as rotas de autenticação
    app.add_routes(routes)

    return app

def main():
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
