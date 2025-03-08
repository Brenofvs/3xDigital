# D:\#3xDigital\app\views\auth_views.py

"""
auth_views.py

Este módulo define as rotas relacionadas à autenticação, como login, registro de usuários,
e verificação de acesso protegido.

Funções:
    protected_route(request: web.Request) -> web.Response:
        Exemplo de rota protegida que exige um token JWT válido.

    register_user(request: web.Request) -> web.Response:
        Rota para registrar um novo usuário no sistema.

    login_user(request: web.Request) -> web.Response:
        Rota para autenticação de usuários e geração de token JWT.

    logout_user(request: web.Request) -> web.Response:
        Rota para logout de usuários.

    admin_only_route(request: web.Request) -> web.Response:
        Rota de exemplo que utiliza o middleware de autorização para permitir acesso somente
        a usuários com papel 'admin'.
"""

from aiohttp import web
from app.services.auth_service import AuthService
from app.middleware.authorization_middleware import require_role
from app.config.settings import DB_SESSION_KEY

routes = web.RouteTableDef()

@routes.get("/auth/protected")
async def protected_route(request: web.Request):
    """
    Exemplo de rota que exige um token válido no cabeçalho Authorization.

    Args:
        request (web.Request): Objeto de requisição contendo os cabeçalhos e informações da requisição.

    Returns:
        web.Response: Resposta JSON informando sucesso ou erro de autenticação.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return web.json_response({"error": "Missing or invalid Authorization header"}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = AuthService.verify_jwt_token(token)
        return web.json_response({"message": f"Access granted. User ID: {payload['sub']}"}, status=200)
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=401)

@routes.get("/admin-only")
@require_role(["admin"])
async def admin_only_route(request: web.Request):
    """
    Rota restrita para usuários com papel 'admin'.

    Args:
        request (web.Request): Objeto de requisição.

    Returns:
        web.Response: Resposta JSON com mensagem de sucesso para admins.
    """
    return web.json_response({"message": "Bem-vindo à rota de admin!"}, status=200)

@routes.post("/auth/register")
async def register_user(request: web.Request):
    """
    Rota POST para registro de usuário.

    JSON de entrada:
        {
          "name": "...",
          "email": "...",
          "cpf": "...",
          "password": "...",
          "role": "affiliate"
        }

    Args:
        request (web.Request): Objeto de requisição contendo o corpo da requisição em JSON.

    Returns:
        web.Response: Resposta JSON informando o status do registro e o ID do usuário criado.
    """
    data = await request.json()
    session = request.app[DB_SESSION_KEY]
    auth_service = AuthService(session)

    try:
        user = await auth_service.create_user(
            name=data["name"],
            email=data["email"],
            cpf=data["cpf"],  # Novo campo para CPF
            password=data["password"],
            role=data.get("role", "affiliate")
        )
        return web.json_response({
            "message": "Usuário criado com sucesso",
            "user_id": user.id
        }, status=201)
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)
    except KeyError as e:
        return web.json_response({"error": f"Campo ausente: {str(e)}"}, status=400)
    except Exception as e:
        return web.json_response({"error": "Erro ao criar usuário"}, status=500)

@routes.post("/auth/login")
async def login_user(request: web.Request):
    """
    Rota POST para login.

    JSON de entrada:
        {
          "identifier": "...",
          "password": "..."
        }

    Args:
        request (web.Request): Objeto de requisição contendo o corpo da requisição em JSON.

    Returns:
        web.Response: Resposta JSON contendo o token de acesso ou erro de autenticação.
    """
    try:
        data = await request.json()
        session = request.app[DB_SESSION_KEY]
        auth_service = AuthService(session)

        identifier = data.get("identifier")  # Pode ser email ou CPF
        password = data.get("password")
        
        user = await auth_service.authenticate_user(identifier, password)
        if not user:
            return web.json_response({"error": "Credenciais inválidas"}, status=401)

        token = auth_service.generate_jwt_token(user)
        return web.json_response({"access_token": token}, status=200)
    except Exception as e:
        return web.json_response({"error": f"Erro interno: {str(e)}"}, status=500)

@routes.post("/auth/logout")
async def logout_user(request: web.Request):
    """
    Rota POST para logout.

    Em sistemas com JWT stateless, o logout é tratado no cliente descartando o token.

    Args:
        request (web.Request): Objeto de requisição.

    Returns:
        web.Response: Resposta JSON indicando sucesso no logout.
    """
    return web.json_response({"message": "Logout efetuado com sucesso"}, status=200)
