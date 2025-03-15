# D:\3xDigital\app\views\profile_views.py
"""
profile_views.py

Módulo responsável pelos endpoints de gerenciamento de perfil, permitindo que
os usuários visualizem e atualizem seus próprios dados.

Endpoints:
    - GET /profile: Obtém dados do perfil do usuário autenticado
    - PUT /profile: Atualiza dados pessoais do usuário
    - PUT /profile/password: Altera a senha do usuário
    - PUT /profile/email: Atualiza o email do usuário
    - PUT /profile/preferences: Atualiza preferências de notificação
    - POST /profile/deactivate: Desativa temporariamente a conta
    - POST /profile/delete-request: Solicita exclusão permanente da conta

Regras de Negócio:
    - Todos os endpoints exigem autenticação
    - Usuários só podem acessar/modificar seus próprios dados
    - Alterações sensíveis (email, senha) exigem verificação da senha atual
    - Todas as operações são registradas em logs

Dependências:
    - aiohttp para rotas HTTP
    - SQLAlchemy para acesso a dados
    - app.services.user_service para lógica de usuários
    - app.middleware.authorization_middleware para controle de acesso
"""

from aiohttp import web
from sqlalchemy import select
import bcrypt

from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_auth
from app.services.user_service import (
    get_user_details, update_user_profile_data, change_password,
    update_user_email, deactivate_user_account, request_account_deletion,
    update_notification_preferences
)

# Definição das rotas
routes = web.RouteTableDef()


@routes.get('/profile')
@require_auth
async def get_profile(request: web.Request) -> web.Response:
    """
    Obtém os dados do perfil do usuário autenticado.
    
    Returns:
        web.Response: JSON com os dados do perfil do usuário.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Busca os detalhes do perfil
        session = request.app[DB_SESSION_KEY]
        user_data = await get_user_details(session, user_id)
        
        if not user_data:
            return web.json_response(
                {"error": "Perfil não encontrado"},
                status=404
            )
        
        # Remove informações sensíveis
        if "password_hash" in user_data:
            del user_data["password_hash"]
        
        return web.json_response(user_data, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao obter perfil: {str(e)}"},
            status=500
        )


@routes.put('/profile')
@require_auth
async def update_profile(request: web.Request) -> web.Response:
    """
    Atualiza os dados pessoais do usuário autenticado.
    
    JSON de entrada:
        {
            "name": "Novo Nome",
            "phone": "11987654321",
            "address": {
                "street": "Rua Exemplo",
                "number": "123",
                "complement": "Apto 45",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234-567"
            },
            "profile_picture": "https://url-da-imagem.com/foto.jpg"
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso e dados atualizados.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Obtém os dados da requisição
        data = await request.json()
        
        if not data:
            return web.json_response(
                {"error": "Nenhum dado fornecido para atualização"},
                status=400
            )
        
        # Atualiza os dados do perfil
        session = request.app[DB_SESSION_KEY]
        success, message, updated_user = await update_user_profile_data(
            session,
            user_id,
            data
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response({
            "message": "Perfil atualizado com sucesso",
            "user": updated_user
        }, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao atualizar perfil: {str(e)}"},
            status=500
        )


@routes.put('/profile/password')
@require_auth
async def update_password(request: web.Request) -> web.Response:
    """
    Altera a senha do usuário autenticado.
    
    JSON de entrada:
        {
            "current_password": "senha_atual",
            "new_password": "nova_senha",
            "confirm_password": "nova_senha"
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Obtém os dados da requisição
        data = await request.json()
        
        # Validações básicas
        required_fields = ["current_password", "new_password", "confirm_password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return web.json_response(
                    {"error": f"Campo obrigatório: {field}"},
                    status=400
                )
        
        if data["new_password"] != data["confirm_password"]:
            return web.json_response(
                {"error": "Nova senha e confirmação não coincidem"},
                status=400
            )
        
        # Altera a senha
        session = request.app[DB_SESSION_KEY]
        success, message = await change_password(
            session,
            user_id,
            data["current_password"],
            data["new_password"]
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response({
            "message": "Senha alterada com sucesso"
        }, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao alterar senha: {str(e)}"},
            status=500
        )


@routes.put('/profile/email')
@require_auth
async def update_email(request: web.Request) -> web.Response:
    """
    Atualiza o endereço de email do usuário autenticado.
    
    JSON de entrada:
        {
            "new_email": "novo_email@exemplo.com",
            "password": "senha_atual"
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Obtém os dados da requisição
        data = await request.json()
        
        # Validações básicas
        required_fields = ["new_email", "password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return web.json_response(
                    {"error": f"Campo obrigatório: {field}"},
                    status=400
                )
        
        # Atualiza o email
        session = request.app[DB_SESSION_KEY]
        success, message = await update_user_email(
            session,
            user_id,
            data["password"],
            data["new_email"]
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response({
            "message": "Email atualizado com sucesso"
        }, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao atualizar email: {str(e)}"},
            status=500
        )


@routes.put('/profile/preferences')
@require_auth
async def update_preferences(request: web.Request) -> web.Response:
    """
    Atualiza as preferências de notificação do usuário.
    
    JSON de entrada:
        {
            "email_marketing": true,
            "order_updates": true,
            "promotions": false
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Obtém os dados da requisição
        data = await request.json()
        
        if not data:
            return web.json_response(
                {"error": "Nenhuma preferência fornecida"},
                status=400
            )
        
        # Atualiza as preferências
        session = request.app[DB_SESSION_KEY]
        success, message = await update_notification_preferences(
            session,
            user_id,
            data
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response({
            "message": "Preferências atualizadas com sucesso"
        }, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao atualizar preferências: {str(e)}"},
            status=500
        )


@routes.post('/profile/deactivate')
@require_auth
async def deactivate_account(request: web.Request) -> web.Response:
    """
    Desativa temporariamente a conta do usuário.
    
    JSON de entrada:
        {
            "password": "senha_atual",
            "reason": "Motivo da desativação" (opcional)
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        print(f"TESTE: Iniciando desativação para usuário ID={user_id}")
        
        # Obtém os dados da requisição
        data = await request.json()
        
        # Validação básica
        if "password" not in data or not data["password"]:
            return web.json_response(
                {"error": "Senha é obrigatória para desativar a conta"},
                status=400
            )
        
        # Desativa a conta
        session = request.app[DB_SESSION_KEY]
        
        # Registra a razão da desativação se fornecida
        reason = data.get("reason")
        print(f"TESTE: Motivo de desativação fornecido: {reason}")
        
        # Verificar se é um motivo válido
        if reason is not None and not isinstance(reason, str):
            return web.json_response(
                {"error": "O motivo de desativação deve ser um texto"},
                status=400
            )
        
        # Verifica se o usuário existe
        from app.models.database import User
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            print(f"TESTE: Usuário com ID {user_id} não encontrado no banco")
            return web.json_response(
                {"error": "Usuário não encontrado"},
                status=404
            )
        
        print(f"TESTE: Usuário encontrado: ID={user.id}, Email={user.email}, Status={user.active}")
        
        # Verificar a senha antes de continuar
        if not bcrypt.checkpw(data["password"].encode('utf-8'), user.password_hash.encode('utf-8')):
            return web.json_response(
                {"error": "Senha incorreta"},
                status=400
            )
        
        # Definir o motivo diretamente
        old_reason = user.deactivation_reason
        if reason:
            user.deactivation_reason = reason
            print(f"TESTE: Definindo motivo: '{user.deactivation_reason}'")
            
        # Desativar a conta
        old_status = user.active
        user.active = 0  # Usar 0 em vez de False para garantir compatibilidade
        print(f"TESTE: Status alterado: {old_status} -> {user.active}")
        
        # Cria um log da alteração
        from app.models.database import Log
        from datetime import datetime
        log = Log(
            user_id=user_id,
            action=f"Desativou a própria conta. Motivo: {user.deactivation_reason}",
            timestamp=datetime.now()
        )
        
        # Salva as alterações
        session.add(user)
        session.add(log)
        await session.commit()
        print(f"TESTE: Alterações salvas no banco - Usuário {user_id} desativado")
        
        # Verificar diretamente se a conta foi desativada
        verify_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        verify_user = verify_result.scalar_one_or_none()
        if verify_user:
            print(f"TESTE: Verificação pós-desativação: active={verify_user.active}, reason={verify_user.deactivation_reason}")
        else:
            print(f"TESTE: ERRO - Usuário não encontrado após desativação!")
        
        return web.json_response({
            "message": "Conta desativada com sucesso"
        }, status=200)
        
    except Exception as e:
        import traceback
        print(f"TESTE: ERRO ao desativar conta: {str(e)}")
        traceback.print_exc()
        return web.json_response(
            {"error": f"Erro ao desativar conta: {str(e)}"},
            status=500
        )


@routes.post('/profile/delete-request')
@require_auth
async def request_deletion(request: web.Request) -> web.Response:
    """
    Solicita a exclusão permanente da conta do usuário.
    
    JSON de entrada:
        {
            "password": "senha_atual",
            "reason": "Motivo da exclusão" (opcional)
        }
    
    Returns:
        web.Response: JSON com mensagem de sucesso.
    """
    try:
        # Obtém o ID do usuário autenticado
        user_id = request["user"]["id"]
        
        # Obtém os dados da requisição
        data = await request.json()
        
        # Validação básica
        if "password" not in data or not data["password"]:
            return web.json_response(
                {"error": "Senha é obrigatória para solicitar exclusão da conta"},
                status=400
            )
        
        # Solicita a exclusão
        session = request.app[DB_SESSION_KEY]
        success, message = await request_account_deletion(
            session,
            user_id,
            data["password"],
            data.get("reason")
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        return web.json_response({
            "message": "Solicitação de exclusão de conta recebida com sucesso. Sua conta será excluída em 30 dias."
        }, status=200)
        
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao solicitar exclusão: {str(e)}"},
            status=500
        ) 