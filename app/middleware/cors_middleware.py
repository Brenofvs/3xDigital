"""
cors_middleware.py

Este módulo define o middleware CORS para permitir requisições cross-origin.
Essencial para permitir que frontends em diferentes origens (como localhost) possam
se comunicar com esta API.

Classes:
    Nenhuma.

Functions:
    setup_cors(app) -> None:
        Configura o CORS para a aplicação AIOHTTP.
"""

import aiohttp_cors


def setup_cors(app):
    """
    Configura o CORS para a aplicação AIOHTTP.
    
    Permite requisições de origens específicas, incluindo localhost em diferentes portas
    tipicamente usadas em desenvolvimento frontend.
    
    Args:
        app (web.Application): A aplicação AIOHTTP onde o CORS será configurado.
    
    Returns:
        None
    """
    # Criar uma instância de configuração CORS
    cors = aiohttp_cors.setup(app, defaults={
        # Configuração para localhost em diferentes portas
        "http://localhost:3000": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        ),
        "http://localhost:8080": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        ),
        "http://127.0.0.1:3000": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        ),
        "http://127.0.0.1:8080": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        ),
        # Adicionar aqui outras origens se necessário
    })

    # Aplicar CORS a todas as rotas existentes na aplicação
    for route in list(app.router.routes()):
        cors.add(route) 