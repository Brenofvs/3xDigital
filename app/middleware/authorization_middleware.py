# D:\#3xDigital\app\middleware\authorization_middleware.py
"""
authorization_middleware.py

Este módulo define um decorador para verificar autorização com base no papel (role) do usuário
armazenado no token JWT. Ele extrai o token do cabeçalho Authorization, decodifica-o e checa
se o usuário possui um dos papéis exigidos para acessar a rota.

Funções:
    require_role(allowed_roles: List[str]) -> Callable:
        Decorador que valida o papel do usuário antes de executar a rota. Caso o token seja
        inválido/ausente ou o papel não seja suficiente, retorna o erro apropriado.

Exemplo de Uso:
    @routes.get("/admin-dashboard")
    @require_role(["admin"])
    async def admin_dashboard(request: web.Request) -> web.Response:
        \"\"\"
        Exemplo de rota que apenas usuários com papel 'admin' podem acessar.
        \"\"\"
        return web.json_response({"message": "Bem-vindo ao dashboard de administrador!"})
"""

from typing import Callable, List
from aiohttp import web
from app.services.auth_service import AuthService

def require_role(allowed_roles: List[str]) -> Callable:
    """
    Decorador que verifica se o usuário possui um dos papéis especificados.

    Este decorador é aplicado a rotas AIOHTTP. Ele extrai o token JWT do cabeçalho
    Authorization (esperado no formato "Bearer <token>"), decodifica o token e
    verifica se o papel do usuário está contido em allowed_roles.

    Args:
        allowed_roles (List[str]): Lista de papéis que podem acessar a rota (ex.: ["admin", "manager"]).

    Returns:
        Callable: Função decoradora que envolve o handler original.

    Raises:
        web.HTTPUnauthorized: Se o cabeçalho Authorization estiver ausente ou inválido, ou se o token for inválido.
        web.HTTPForbidden: Se o papel do usuário não estiver em allowed_roles.

    Exemplo:
        @routes.get("/manager-area")
        @require_role(["manager", "admin"])
        async def manager_area(request: web.Request) -> web.Response:
            \"\"\"
            Rota restrita a usuários com papéis 'manager' ou 'admin'.
            \"\"\"
            return web.json_response({"message": "Bem-vindo à área de gerente!"})
    """
    def decorator(handler: Callable) -> Callable:
        async def wrapper(request: web.Request) -> web.Response:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                raise web.HTTPUnauthorized(
                    text='{"error": "Missing or invalid Authorization header"}',
                    content_type="application/json"
                )

            token = auth_header.split(" ")[1]
            try:
                payload = AuthService.verify_jwt_token(token)
            except ValueError as e:
                # Token expirado ou inválido
                raise web.HTTPUnauthorized(
                    text=f'{{"error": "{str(e)}"}}',
                    content_type="application/json"
                )

            user_role = payload.get("role")
            if user_role not in allowed_roles:
                raise web.HTTPForbidden(
                    text='{"error": "Acesso negado: privilégio insuficiente."}',
                    content_type="application/json"
                )

            return await handler(request)
        return wrapper
    return decorator
