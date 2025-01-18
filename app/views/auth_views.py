# D:\#3xDigital\app\views\auth_views.py

from aiohttp import web
from app.services.auth_service import AuthService
from app.models.database import get_session_maker, get_async_engine
from app.config.settings import DATABASE_URL, DB_SESSION_KEY

routes = web.RouteTableDef()

@routes.get("/auth/protected")
async def protected_route(request: web.Request):
    """
    Exemplo de rota que exige um token válido no cabeçalho Authorization.
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

@routes.post("/auth/register")
async def register_user(request: web.Request):
    """
    Rota POST para registro de usuário.
    JSON de entrada: {
      "name": "...",
      "email": "...",
      "password": "...",
      "role": "affiliate"
    }
    """
    data = await request.json()
    session = request.app[DB_SESSION_KEY]
    auth_service = AuthService(session)

    try:
        user = await auth_service.create_user(
            name=data["name"],
            email=data["email"],
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
    JSON de entrada: {
      "email": "...",
      "password": "..."
    }
    """
    data = await request.json()
    session = request.app[DB_SESSION_KEY]
    auth_service = AuthService(session)

    user = await auth_service.authenticate_user(data["email"], data["password"])
    if not user:
        return web.json_response({"error": "Credenciais inválidas"}, status=401)

    token = auth_service.generate_jwt_token(user)
    return web.json_response({"access_token": token}, status=200)

@routes.post("/auth/logout")
async def logout_user(request: web.Request):
    """
    Rota POST para logout.
    Em JWT stateless, normalmente basta descartar token no cliente.
    """
    return web.json_response({"message": "Logout efetuado com sucesso"}, status=200)
