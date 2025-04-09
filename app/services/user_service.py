# D:\3xDigital\app\services\user_service.py
"""
user_service.py

Módulo responsável pela lógica de gerenciamento avançado de usuários,
permitindo que administradores realizem operações de gerenciamento
de contas de usuários no sistema 3xDigital.

Funcionalidades principais:
    - Listagem e busca de usuários com filtros
    - Atualização de papéis (roles) de usuários
    - Bloqueio/desbloqueio de usuários
    - Redefinição de senhas
    - Atualização de dados pessoais pelo próprio usuário
    - Auto-gerenciamento de conta

Regras de Negócio:
    - Apenas administradores podem gerenciar usuários
    - Usuários não podem alterar seus próprios papéis
    - Senhas são sempre armazenadas com hash seguro
    - Logs são gerados para operações sensíveis
    - Usuários podem atualizar seus próprios dados pessoais

Dependências:
    - SQLAlchemy para persistência
    - bcrypt para hash seguro de senhas
    - app.models.database para acesso às entidades
"""

import bcrypt
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import select, func, or_, and_, not_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User, Affiliate, Log, UserAddress


async def list_users(
    session: AsyncSession,
    search_term: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[User], int]:
    """
    Lista usuários do sistema com opções de filtragem.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        search_term (Optional[str]): Termo para busca em nome, email ou CPF
        role (Optional[str]): Filtro por papel (admin, manager, affiliate, user)
        page (int): Página de resultados
        page_size (int): Tamanho da página
        
    Returns:
        Tuple[List[User], int]:
            - Lista de usuários
            - Total de usuários encontrados
    """
    # Constrói a query base
    query = select(User)
    
    # Aplica filtros
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.where(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.cpf.ilike(search_pattern)
            )
        )
    
    if role:
        query = query.where(User.role == role)
    
    # Conta o total
    count_query = select(func.count()).select_from(query.subquery())
    result = await session.execute(count_query)
    total_count = result.scalar_one()
    
    # Aplica paginação
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Executa a query
    result = await session.execute(query)
    users = result.scalars().all()
    
    return users, total_count


async def get_user_details(
    session: AsyncSession,
    user_id: int
) -> Optional[Dict]:
    """
    Obtém detalhes completos de um usuário, incluindo informações de afiliado se aplicável.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        
    Returns:
        Optional[Dict]: Dados detalhados do usuário ou None se não encontrado
    """
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    # Busca o endereço principal do usuário
    result = await session.execute(
        select(UserAddress).where(UserAddress.user_id == user_id)
    )
    address = result.scalar_one_or_none()
    
    # Prepara dados básicos
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "cpf": user.cpf,
        "role": user.role,
        "phone": user.phone,
        "address": {
            "street": address.street if address else None,
            "number": address.number if address else None,
            "complement": address.complement if address else None,
            "neighborhood": address.neighborhood if address else None,
            "city": address.city if address else None,
            "state": address.state if address else None,
            "zip_code": address.zip_code if address else None
        } if address else None,
        "active": user.active,
        "deactivation_reason": user.deactivation_reason,
        "deletion_requested": user.deletion_requested,
        "deletion_request_date": user.deletion_request_date.isoformat() if user.deletion_request_date else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "is_affiliate": False
    }
    
    # Busca dados de afiliado, se for o caso
    if user.role == 'affiliate':
        result = await session.execute(
            select(Affiliate).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if affiliate:
            user_data["is_affiliate"] = True
            user_data["affiliate"] = {
                "id": affiliate.id,
                "referral_code": affiliate.referral_code,
                "commission_rate": affiliate.commission_rate,
                "request_status": affiliate.request_status
            }
    
    return user_data


async def update_user_role(
    session: AsyncSession,
    user_id: int,
    new_role: str,
    admin_id: int
) -> Tuple[bool, Optional[str]]:
    """
    Atualiza o papel (role) de um usuário.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário a ser atualizado
        new_role (str): Novo papel (admin, manager, affiliate, user)
        admin_id (int): ID do administrador realizando a alteração
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    # Validação básica
    valid_roles = ['admin', 'manager', 'affiliate', 'user']
    if new_role not in valid_roles:
        return False, f"Papel inválido. Use um dos seguintes: {', '.join(valid_roles)}"
    
    # Verifica se o admin não está alterando seu próprio papel
    if user_id == admin_id:
        return False, "Não é possível alterar seu próprio papel"
    
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False, "Usuário não encontrado"
    
    # Salva o papel anterior para logging
    old_role = user.role
    
    # Atualiza o papel
    user.role = new_role
    
    # Cria um log da alteração
    log = Log(
        user_id=admin_id,
        action=f"Alterou papel do usuário {user.id} de '{old_role}' para '{new_role}'",
        timestamp=datetime.now()
    )
    
    # Salva as alterações
    session.add(user)
    session.add(log)
    await session.commit()
    
    return True, None


async def toggle_user_status(
    session: AsyncSession,
    user_id: int,
    block: bool,
    admin_id: int
) -> Tuple[bool, Optional[str]]:
    """
    Bloqueia ou desbloqueia um usuário no sistema.
    
    Em nosso modelo atual, utilizamos o status do afiliado como forma de bloqueio.
    Para usuários não afiliados, precisaremos adicionar um campo de status na tabela Users.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário a ser bloqueado/desbloqueado
        block (bool): True para bloquear, False para desbloquear
        admin_id (int): ID do administrador realizando a operação
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    # Verifica se o admin não está bloqueando a si mesmo
    if user_id == admin_id:
        return False, "Não é possível bloquear seu próprio usuário"
    
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False, "Usuário não encontrado"
    
    # Para usuários afiliados, utilizamos o status do afiliado
    if user.role == 'affiliate':
        result = await session.execute(
            select(Affiliate).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if affiliate:
            # Atualiza o status
            affiliate.request_status = 'blocked' if block else 'approved'
            session.add(affiliate)
    
    # TODO: Para usuários não afiliados, precisaremos adicionar um campo is_active na tabela Users
    # e atualizá-lo aqui
    
    # Cria um log da alteração
    action = f"{'Bloqueou' if block else 'Desbloqueou'} o usuário {user_id}"
    log = Log(
        user_id=admin_id,
        action=action,
        timestamp=datetime.now()
    )
    
    # Salva as alterações
    session.add(log)
    await session.commit()
    
    return True, None


async def reset_user_password(
    session: AsyncSession,
    user_id: int,
    new_password: str,
    admin_id: int
) -> Tuple[bool, Optional[str]]:
    """
    Redefine a senha de um usuário (apenas administradores).
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        new_password (str): Nova senha
        admin_id (int): ID do administrador realizando a operação
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    # Validação básica
    if not new_password or len(new_password) < 6:
        return False, "Senha inválida. Deve ter pelo menos 6 caracteres"
    
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False, "Usuário não encontrado"
    
    # Gera o hash da nova senha
    password_hash = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Atualiza a senha
    user.password_hash = password_hash
    
    # Cria um log da alteração
    log = Log(
        user_id=admin_id,
        action=f"Redefiniu senha do usuário {user_id}",
        timestamp=datetime.now()
    )
    
    # Salva as alterações
    session.add(user)
    session.add(log)
    await session.commit()
    
    return True, None


async def update_user_profile_data(
    session: AsyncSession,
    user_id: int,
    profile_data: Dict[str, Any]
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Atualiza os dados do perfil de um usuário.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        profile_data (Dict[str, Any]): Dados do perfil a serem atualizados
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
            - Dados atualizados do usuário (se sucesso)
    """
    try:
        # Busca o usuário
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "Usuário não encontrado", None
        
        # Atualiza dados básicos do usuário
        if "name" in profile_data:
            user.name = profile_data["name"]
        if "phone" in profile_data:
            user.phone = profile_data["phone"]
            
        # Atualiza ou cria endereço
        if "address" in profile_data:
            address_data = profile_data["address"]
            
            # Busca endereço existente
            result = await session.execute(
                select(UserAddress).where(UserAddress.user_id == user_id)
            )
            address = result.scalar_one_or_none()
            
            if address:
                # Atualiza endereço existente
                for key, value in address_data.items():
                    setattr(address, key, value)
            else:
                # Cria novo endereço
                address = UserAddress(
                    user_id=user_id,
                    **address_data
                )
                session.add(address)
        
        await session.commit()
        
        # Retorna os dados atualizados do usuário
        updated_data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "address": profile_data.get("address")
        }
        
        return True, None, updated_data
        
    except Exception as e:
        await session.rollback()
        return False, f"Erro ao atualizar perfil: {str(e)}", None


async def change_password(
    session: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str
) -> Tuple[bool, Optional[str]]:
    """
    Permite que um usuário altere sua própria senha, exigindo a senha atual.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        current_password (str): Senha atual para verificação
        new_password (str): Nova senha desejada
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    # Validação básica
    if not new_password or len(new_password) < 6:
        return False, "Nova senha inválida. Deve ter pelo menos 6 caracteres"
    
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False, "Usuário não encontrado"
    
    # Verifica a senha atual
    if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return False, "Senha atual incorreta"
    
    # Gera o hash da nova senha
    password_hash = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Atualiza a senha
    user.password_hash = password_hash
    
    # Cria um log da alteração
    log = Log(
        user_id=user_id,
        action="Alterou a própria senha",
        timestamp=datetime.now()
    )
    
    # Salva as alterações
    session.add(user)
    session.add(log)
    await session.commit()
    
    return True, None


async def update_user_email(
    session: AsyncSession,
    user_id: int,
    password: str,
    new_email: str
) -> Tuple[bool, Optional[str]]:
    """
    Permite que um usuário atualize seu endereço de email.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        password (str): Senha atual para verificação
        new_email (str): Novo endereço de email
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    try:
        # Validação básica de formato de email
        if not new_email or '@' not in new_email:
            return False, "Endereço de email inválido"
        
        # Busca o usuário
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "Usuário não encontrado"
        
        # Verifica se o usuário está ativo
        if not user.active:
            return False, "Conta de usuário desativada"
        
        # Verifica a senha
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return False, "Senha incorreta"
        
        # Verifica se o novo email é igual ao atual
        if user.email == new_email:
            return False, "O novo email é igual ao atual"
        
        # Verifica se o email já está em uso
        result = await session.execute(
            select(User).where(User.email == new_email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user and existing_user.id != user_id:
            return False, "Este email já está em uso por outro usuário"
        
        # Salva o email anterior para o log
        old_email = user.email
        
        # Atualiza o email
        user.email = new_email
        
        # Cria um log da alteração
        log = Log(
            user_id=user_id,
            action=f"Alterou email de '{old_email}' para '{new_email}'",
            timestamp=datetime.now()
        )
        
        # Salva as alterações
        session.add(user)
        session.add(log)
        await session.commit()
        
        return True, None
    except Exception as e:
        await session.rollback()
        return False, f"Erro ao atualizar email: {str(e)}"


async def deactivate_user_account(
    session: AsyncSession,
    user_id: int,
    password: str,
    reason: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Permite que um usuário desative temporariamente sua própria conta.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        password (str): Senha para verificação
        reason (Optional[str]): Motivo da desativação (opcional)
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    try:
        # Busca o usuário
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "Usuário não encontrado"
        
        # Verifica se a conta já está desativada
        if not user.active:
            return False, "Conta já está desativada"
        
        # Verifica a senha
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return False, "Senha incorreta"
        
        # Define o motivo de desativação se fornecido
        if reason:
            user.deactivation_reason = reason
        # Se não foi fornecido um motivo e não há motivo existente, usa o padrão
        elif not user.deactivation_reason:
            user.deactivation_reason = "Conta desativada pelo usuário"
        
        # Desativa a conta
        user.active = False
        
        # Cria um log da alteração
        log = Log(
            user_id=user_id,
            action="Desativou a própria conta",
            timestamp=datetime.now()
        )
        
        # Salva as alterações
        session.add(user)
        session.add(log)
        await session.commit()
        
        return True, None
    except Exception as e:
        await session.rollback()
        return False, f"Erro ao desativar conta: {str(e)}"


async def request_account_deletion(
    session: AsyncSession,
    user_id: int,
    password: str,
    reason: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Permite que um usuário solicite a exclusão definitiva de sua conta.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        password (str): Senha para verificação
        reason (Optional[str]): Motivo da solicitação de exclusão
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    try:
        # Busca o usuário
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "Usuário não encontrado"
        
        # Verifica se já existe uma solicitação de exclusão
        if user.deletion_requested:
            return False, "Já existe uma solicitação de exclusão para esta conta"
        
        # Verifica a senha
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return False, "Senha incorreta"
        
        # Marca a conta para exclusão
        user.deletion_requested = True
        user.deletion_request_date = datetime.now()
        
        # Cria um log da solicitação
        log_message = "Solicitou exclusão de conta"
        if reason:
            log_message += f": {reason}"
        
        log = Log(
            user_id=user_id,
            action=log_message,
            timestamp=datetime.now()
        )
        
        # Salva as alterações
        session.add(user)
        session.add(log)
        await session.commit()
        
        return True, None
    except Exception as e:
        await session.rollback()
        return False, f"Erro ao solicitar exclusão de conta: {str(e)}"


async def update_notification_preferences(
    session: AsyncSession,
    user_id: int,
    preferences: Dict[str, bool]
) -> Tuple[bool, Optional[str]]:
    """
    Atualiza as preferências de notificação do usuário.
    
    Args:
        session (AsyncSession): Sessão do banco de dados
        user_id (int): ID do usuário
        preferences (Dict[str, bool]): Preferências de notificação
            Exemplo: {'email_marketing': True, 'order_updates': True, 'promotions': False}
        
    Returns:
        Tuple[bool, Optional[str]]:
            - Sucesso da operação
            - Mensagem de erro (se houver)
    """
    # Busca o usuário
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False, "Usuário não encontrado"
    
    # Atualiza as preferências
    current_preferences = user.notification_preferences or {}
    
    # Mescla as preferências existentes com as novas
    updated_preferences = {**current_preferences, **preferences}
    
    user.notification_preferences = updated_preferences
    
    # Cria um log da alteração
    log = Log(
        user_id=user_id,
        action="Atualizou preferências de notificação",
        timestamp=datetime.now()
    )
    
    # Salva as alterações
    session.add(user)
    session.add(log)
    await session.commit()
    
    return True, None