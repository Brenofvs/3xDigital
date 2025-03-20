# D:\3xDigital\app\middleware\authorization_middleware.py
"""
authorization_middleware.py

Este módulo define decoradores para verificar autorização com base no papel (role) do usuário
armazenado no token JWT. Ele extrai o token do cabeçalho Authorization, decodifica-o e checa
se o usuário possui um dos papéis exigidos para acessar a rota.

Funções:
    validate_token(token: str) -> dict:
        Função auxiliar que valida um token JWT e retorna seu payload.
        
    require_role(allowed_roles: List[str]) -> Callable:
        Decorador que valida o papel do usuário antes de executar a rota. Caso o token seja
        inválido/ausente ou o papel não seja suficiente, retorna o erro apropriado.
        
    require_auth() -> Callable:
        Decorador que apenas verifica se o usuário está autenticado, sem validar papéis específicos.
        Útil para rotas que qualquer usuário autenticado pode acessar.

Exemplo de Uso:
    @routes.get("/admin-dashboard")
    @require_role(["admin"])
    async def admin_dashboard(request: web.Request) -> web.Response:
        \"\"\"
        Exemplo de rota que apenas usuários com papel 'admin' podem acessar.
        \"\"\"
        return web.json_response({"message": "Bem-vindo ao dashboard de administrador!"})
        
    @routes.get("/profile")
    @require_auth
    async def get_profile(request: web.Request) -> web.Response:
        \"\"\"
        Exemplo de rota que qualquer usuário autenticado pode acessar.
        \"\"\"
        return web.json_response({"message": "Bem-vindo ao seu perfil!"})
"""

from typing import Callable, List, Optional
from aiohttp import web
from app.services.auth_service import AuthService

async def validate_token(token: str) -> Optional[dict]:
    """
    Função que valida um token JWT e retorna seu payload.
    
    Args:
        token (str): Token JWT completo com prefixo "Bearer"
        
    Returns:
        Optional[dict]: Payload do token se válido, None caso contrário
        
    Raises:
        ValueError: Se o token for inválido ou expirado
    """
    if not token.startswith("Bearer "):
        return None
        
    token = token.split(" ")[1]
    try:
        return AuthService.verify_jwt_token(token)
    except ValueError:
        return None

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

            try:
                payload = await validate_token(auth_header)
                if not payload:
                    raise ValueError("Token inválido")
            except ValueError as e:
                # Token expirado ou inválido
                raise web.HTTPUnauthorized(
                    text=f'{{"error": "{str(e)}"}}',
                    content_type="application/json"
                )

            user_role = payload.get("role")
            user_id = payload.get("sub")  # Obtém o ID do usuário do payload (sub).

            if user_role not in allowed_roles:
                raise web.HTTPForbidden(
                    text='{"error": "Acesso negado: privilégio insuficiente."}',
                    content_type="application/json"
                )

            # Armazena os dados do usuário no request, para uso nas rotas.
            request["user"] = {
                "id": int(user_id) if user_id is not None else None,
                "role": user_role
            }

            return await handler(request)
        return wrapper
    return decorator


def require_auth(handler: Callable) -> Callable:
    """
    Decorador que verifica apenas se o usuário está autenticado, sem verificar papéis.
    
    Este decorador é aplicado a rotas AIOHTTP que qualquer usuário autenticado pode acessar.
    Ele extrai o token JWT do cabeçalho Authorization, decodifica-o e armazena informações
    do usuário no objeto request.
    
    Args:
        handler (Callable): O handler original da rota.
        
    Returns:
        Callable: Função decoradora que envolve o handler original.
        
    Raises:
        web.HTTPUnauthorized: Se o cabeçalho Authorization estiver ausente ou inválido, 
                              ou se o token for inválido/expirado.
                              
    Exemplo:
        @routes.get("/profile")
        @require_auth
        async def get_profile(request: web.Request) -> web.Response:
            \"\"\"
            Rota que qualquer usuário autenticado pode acessar.
            \"\"\"
            user_id = request["user"]["id"]  # ID do usuário atual
            return web.json_response({"message": f"Bem-vindo ao seu perfil, usuário {user_id}!"})
    """
    async def wrapper(request: web.Request) -> web.Response:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise web.HTTPUnauthorized(
                text='{"error": "Missing or invalid Authorization header"}',
                content_type="application/json"
            )

        try:
            payload = await validate_token(auth_header)
            if not payload:
                raise ValueError("Token inválido")
        except ValueError as e:
            # Token expirado ou inválido
            raise web.HTTPUnauthorized(
                text=f'{{"error": "{str(e)}"}}',
                content_type="application/json"
            )

        user_role = payload.get("role")
        user_id = payload.get("sub")  # Obtém o ID do usuário do payload (sub).

        # Armazena os dados do usuário no request, para uso nas rotas.
        request["user"] = {
            "id": int(user_id) if user_id is not None else None,
            "role": user_role
        }

        return await handler(request)
    return wrapper