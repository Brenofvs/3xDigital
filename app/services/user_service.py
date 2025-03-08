# D:\#3xDigital\app\services\user_service.py
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

Regras de Negócio:
    - Apenas administradores podem gerenciar usuários
    - Usuários não podem alterar seus próprios papéis
    - Senhas são sempre armazenadas com hash seguro
    - Logs são gerados para operações sensíveis

Dependências:
    - SQLAlchemy para persistência
    - bcrypt para hash seguro de senhas
    - app.models.database para acesso às entidades
"""

import bcrypt
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, func, or_, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User, Affiliate, Log


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
    
    # Prepara dados básicos
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "cpf": user.cpf,
        "role": user.role,
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