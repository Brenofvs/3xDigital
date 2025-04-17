# D:\3xDigital\app\views\users_views.py
"""
users_views.py

Módulo responsável pelos endpoints de gerenciamento avançado de usuários
do sistema 3xDigital, permitindo que administradores gerenciem contas.

Endpoints:
    - GET /users: Lista todos os usuários com filtros
    - GET /users/{user_id}: Obtém detalhes de um usuário específico
    - PUT /users/{user_id}/role: Atualiza o papel de um usuário
    - PUT /users/{user_id}/status: Bloqueia ou desbloqueia um usuário
    - PUT /users/{user_id}/reset-password: Redefine a senha de um usuário
    - POST /users: Cria um novo usuário

Regras de Negócio:
    - Apenas administradores podem acessar estes endpoints
    - Usuários não podem alterar seus próprios papéis
    - Todas as operações sensíveis são registradas
    - Senhas são sempre armazenadas com hash seguro

Dependências:
    - aiohttp para rotas HTTP
    - SQLAlchemy para acesso a dados
    - app.services.user_service para lógica de usuários
    - app.middleware.authorization_middleware para controle de acesso
    - app.services.auth_service para autenticação
"""

from aiohttp import web
from sqlalchemy import select

from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.models.database import User
from app.services.user_service import (
    list_users, get_user_details, update_user_role,
    toggle_user_status, reset_user_password
)
from app.services.auth_service import AuthService

# Definição das rotas
routes = web.RouteTableDef()


@routes.get('/users')
@require_role(['admin'])
async def get_users(request: web.Request) -> web.Response:
    """
    Lista usuários do sistema com opções de filtragem.
    Apenas para administradores.
    
    Query params:
        search (str, opcional): Termo de busca (nome, email, CPF)
        role (str, opcional): Filtro por papel (admin, manager, affiliate, user)
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)
    
    Returns:
        web.Response: JSON com lista de usuários e metadados
    """
    # Parâmetros de query
    search = request.query.get('search', '')
    role = request.query.get('role')
    page = int(request.query.get('page', 1))
    page_size = int(request.query.get('page_size', 20))
    
    # Obtém os usuários
    db = request.app[DB_SESSION_KEY]
    users, total_count = await list_users(db, search, role, page, page_size)
    
    # Formata a resposta
    users_data = []
    for user in users:
        users_data.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "cpf": user.cpf,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    
    response_data = {
        "users": users_data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }
    
    return web.json_response(response_data, status=200)


@routes.get('/users/{user_id}')
@require_role(['admin'])
async def get_user(request: web.Request) -> web.Response:
    """
    Obtém detalhes de um usuário específico.
    Apenas para administradores.
    
    Path params:
        user_id (int): ID do usuário
    
    Returns:
        web.Response: JSON com detalhes do usuário
    """
    # Obtém o ID do usuário
    try:
        user_id = int(request.match_info['user_id'])
    except ValueError:
        return web.json_response(
            {"error": "ID de usuário inválido"},
            status=400
        )
    
    # Obtém os detalhes do usuário
    db = request.app[DB_SESSION_KEY]
    user_data = await get_user_details(db, user_id)
    
    if not user_data:
        return web.json_response(
            {"error": "Usuário não encontrado"},
            status=404
        )
    
    return web.json_response(user_data, status=200)


@routes.put('/users/{user_id}/role')
@require_role(['admin'])
async def update_user_role_endpoint(request: web.Request) -> web.Response:
    """
    Atualiza o papel (role) de um usuário.
    Apenas para administradores.
    
    Path params:
        user_id (int): ID do usuário a ser atualizado
    
    JSON de entrada:
        {
            "role": "affiliate"  # Novo papel
        }
    
    Returns:
        web.Response: JSON com resultado da operação
    """
    # Obtém o ID do usuário
    try:
        user_id = int(request.match_info['user_id'])
    except ValueError:
        return web.json_response(
            {"error": "ID de usuário inválido"},
            status=400
        )
    
    # Obtém o ID do admin da requisição
    admin_id = request["user"]["id"]
    
    # Obtém os dados da requisição
    try:
        data = await request.json()
        
        # Validação básica
        if 'role' not in data:
            return web.json_response(
                {"error": "Campo 'role' é obrigatório"},
                status=400
            )
        
        # Atualiza o papel do usuário
        success, message = await update_user_role(
            request.app[DB_SESSION_KEY],
            user_id,
            data['role'],
            admin_id
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response(
            {"message": f"Papel do usuário atualizado para '{data['role']}'"},
            status=200
        )
        
    except ValueError as e:
        return web.json_response(
            {"error": f"Dados inválidos: {str(e)}"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao atualizar papel: {str(e)}"},
            status=500
        )


@routes.put('/users/{user_id}/status')
@require_role(['admin'])
async def toggle_user_status_endpoint(request: web.Request) -> web.Response:
    """
    Bloqueia ou desbloqueia um usuário no sistema.
    Apenas para administradores.
    
    Path params:
        user_id (int): ID do usuário a ser bloqueado/desbloqueado
    
    JSON de entrada:
        {
            "blocked": true  # true para bloquear, false para desbloquear
        }
    
    Returns:
        web.Response: JSON com resultado da operação
    """
    # Obtém o ID do usuário
    try:
        user_id = int(request.match_info['user_id'])
    except ValueError:
        return web.json_response(
            {"error": "ID de usuário inválido"},
            status=400
        )
    
    # Obtém o ID do admin da requisição
    admin_id = request["user"]["id"]
    
    # Obtém os dados da requisição
    try:
        data = await request.json()
        
        # Validação básica
        if 'blocked' not in data or not isinstance(data['blocked'], bool):
            return web.json_response(
                {"error": "Campo 'blocked' é obrigatório e deve ser boolean"},
                status=400
            )
        
        # Atualiza o status do usuário
        success, message = await toggle_user_status(
            request.app[DB_SESSION_KEY],
            user_id,
            data['blocked'],
            admin_id
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response(
            {"message": f"Usuário {'bloqueado' if data['blocked'] else 'desbloqueado'} com sucesso"},
            status=200
        )
        
    except ValueError as e:
        return web.json_response(
            {"error": f"Dados inválidos: {str(e)}"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao atualizar status: {str(e)}"},
            status=500
        )


@routes.put('/users/{user_id}/reset-password')
@require_role(['admin'])
async def reset_password_endpoint(request: web.Request) -> web.Response:
    """
    Redefine a senha de um usuário.
    Apenas para administradores.
    
    Path params:
        user_id (int): ID do usuário
    
    JSON de entrada:
        {
            "new_password": "nova_senha"
        }
    
    Returns:
        web.Response: JSON com resultado da operação
    """
    # Obtém o ID do usuário
    try:
        user_id = int(request.match_info['user_id'])
    except ValueError:
        return web.json_response(
            {"error": "ID de usuário inválido"},
            status=400
        )
    
    # Obtém o ID do admin da requisição
    admin_id = request["user"]["id"]
    
    # Obtém os dados da requisição
    try:
        data = await request.json()
        
        # Validação básica
        if 'new_password' not in data or not data['new_password']:
            return web.json_response(
                {"error": "Campo 'new_password' é obrigatório"},
                status=400
            )
        
        # Redefine a senha
        success, message = await reset_user_password(
            request.app[DB_SESSION_KEY],
            user_id,
            data['new_password'],
            admin_id
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response(
            {"message": "Senha redefinida com sucesso"},
            status=200
        )
        
    except ValueError as e:
        return web.json_response(
            {"error": f"Dados inválidos: {str(e)}"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao redefinir senha: {str(e)}"},
            status=500
        )


@routes.post('/users')
@require_role(['admin'])
async def create_user(request: web.Request) -> web.Response:
    """
    Cria um novo usuário no sistema.
    Apenas para administradores.
    
    JSON de entrada:
        {
            "name": "Nome Completo",
            "email": "email@exemplo.com",
            "cpf": "12345678900",
            "password": "senha_segura",
            "role": "user",   # Pode ser: admin, manager, affiliate, user
            "address": {      # Opcional
                "street": "Rua Exemplo",
                "number": "123",
                "complement": "Apto 101",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234567"
            }
        }
    
    Returns:
        web.Response: JSON com detalhes do usuário criado
    """
    try:
        # Obter dados da requisição
        data = await request.json()
        
        # Verificar campos obrigatórios
        required_fields = ['name', 'email', 'cpf', 'password']
        for field in required_fields:
            if field not in data:
                return web.json_response(
                    {"error": f"Campo obrigatório ausente: {field}"},
                    status=400
                )
        
        # Criar o serviço de autenticação
        db = request.app[DB_SESSION_KEY]
        auth_service = AuthService(db)
        
        # Criar o usuário
        try:
            user = await auth_service.create_user(
                name=data['name'],
                email=data['email'],
                cpf=data['cpf'],
                password=data['password'],
                role=data.get('role', 'user'),  # Default para 'user' se não especificado
                address=data.get('address')
            )
            
            # Registrar ação de criação de usuário pelo admin no log de auditoria
            admin_id = request["user"]["id"]
            
            # Criar registro de log
            from datetime import datetime
            from app.models.database import Log
            
            log = Log(
                user_id=admin_id,
                action=f"Criou um novo usuário (ID: {user.id}, Nome: {user.name}, Papel: {user.role})",
                timestamp=datetime.now()
            )
            db.add(log)
            await db.commit()
            
            # Retornar dados do usuário criado (sem a senha)
            return web.json_response({
                "message": f"Usuário criado com sucesso por administrador",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "cpf": user.cpf,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }, status=201)
            
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
            
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao criar usuário: {str(e)}"},
            status=500
        )