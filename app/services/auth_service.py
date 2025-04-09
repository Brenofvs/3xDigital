# D:\3xDigital\app\services\auth_service.py

"""
auth_service.py

Este módulo contém a classe AuthService, responsável por lidar com a autenticação e
autorização de usuários, incluindo criação de usuários, autenticação, geração e verificação
de tokens JWT, e checagem de permissões.

Classes:
    AuthService: Provedor de serviços de autenticação e autorização para usuários.
"""

import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.database import User, RefreshToken, UserAddress
from app.config.settings import (
    JWT_SECRET_KEY, TIMEZONE, get_current_timezone, 
    JWT_EXPIRATION_MINUTES, REFRESH_TOKEN_EXPIRATION_DAYS
)

class AuthService:
    """
    Serviço de autenticação e autorização.

    Métodos:
        create_user: Cria um novo usuário com hash de senha e endereço.
        authenticate_user: Autentica um usuário com base em e-mail e senha.
        generate_jwt_token: Gera um token JWT para um usuário.
        verify_jwt_token: Decodifica e valida um token JWT.
        check_permissions: Verifica se o usuário tem o papel necessário.
        generate_refresh_token: Gera um novo refresh token para um usuário.
        verify_refresh_token: Verifica se um refresh token é válido.
        refresh_access_token: Gera um novo access token a partir de um refresh token.
        revoke_refresh_token: Revoga um refresh token.
        revoke_all_refresh_tokens: Revoga todos os refresh tokens de um usuário.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o AuthService com uma sessão de banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do banco de dados.
        """
        self.db_session = db_session

    async def create_user(
            self, 
            name: str, 
            email: str, 
            cpf: str, 
            password: str, 
            role: str = "affiliate",
            address: Optional[Dict[str, str]] = None
        ) -> User:
        """
        Cria um novo usuário com hash de senha e endereço de forma assíncrona.

        Args:
            name (str): Nome do usuário.
            email (str): E-mail do usuário.
            cpf (str): CPF do usuário.
            password (str): Senha do usuário.
            role (str, optional): Papel do usuário. Padrão é "affiliate".
            address (Optional[Dict[str, str]], optional): Dicionário contendo dados do endereço:
                - street: Nome da rua
                - number: Número
                - complement: Complemento (opcional)
                - neighborhood: Bairro
                - city: Cidade
                - state: Estado
                - zip_code: CEP

        Returns:
            User: Objeto do usuário criado.

        Raises:
            ValueError: Se o e-mail já estiver registrado ou se os dados forem inválidos.
        """
        # Validações básicas
        if not name or not email or not cpf or not password:
            raise ValueError("Todos os campos são obrigatórios")

        if len(password) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres")

        # Validação do papel
        valid_roles = ["admin", "manager", "affiliate", "user"]
        if role not in valid_roles:
            role = "affiliate"  # Define o papel padrão se inválido

        # Verifica se já existe usuário com mesmo email ou CPF
        result = await self.db_session.execute(
            select(User).where((User.email == email) | (User.cpf == cpf))
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.email == email:
                raise ValueError("Email já está registrado")
            else:
                raise ValueError("CPF já está registrado")
        
        # Gera o hash da senha
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        # Cria o novo usuário
        new_user = User(
            name=name,
            email=email,
            cpf=cpf,
            password_hash=password_hash,
            role=role,
            active=True
        )

        try:
            self.db_session.add(new_user)
            await self.db_session.flush()  # Necessário para obter o ID do usuário

            # Se houver dados de endereço, cria o endereço do usuário
            if address:
                required_fields = ['street', 'number', 'neighborhood', 'city', 'state', 'zip_code']
                if not all(field in address for field in required_fields):
                    raise ValueError("Campos obrigatórios de endereço faltando")

                new_address = UserAddress(
                    user_id=new_user.id,
                    street=address['street'],
                    number=address['number'],
                    complement=address.get('complement', ''),  # Campo opcional
                    neighborhood=address['neighborhood'],
                    city=address['city'],
                    state=address['state'],
                    zip_code=address['zip_code']
                )
                self.db_session.add(new_address)

            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            return new_user
        except Exception as e:
            await self.db_session.rollback()
            raise ValueError(f"Erro ao criar usuário: {str(e)}")

    async def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        """
        Autentica um usuário usando email/CPF e senha.

        Args:
            identifier (str): Email ou CPF do usuário.
            password (str): Senha do usuário.

        Returns:
            Optional[User]: Objeto do usuário se autenticado, None caso contrário.
        """
        try:
            # Busca usuário por email ou CPF
            result = await self.db_session.execute(
                select(User).where(
                    or_(User.email == identifier, User.cpf == identifier)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                return None

            if not user.active:
                return None

            # Verifica a senha
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return None

            return user

        except Exception as e:
            logging.error(f"Erro na autenticação: {str(e)}")
            return None

    def generate_jwt_token(self, user: User) -> str:
        """
        Gera um token JWT contendo informações do usuário.

        Args:
            user (User): Objeto do usuário para o qual o token será gerado.

        Returns:
            str: Token JWT gerado.
        """
        expires = TIMEZONE() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        payload = {
            "sub": str(user.id),
            "role": user.role,
            "exp": expires
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_jwt_token(token: str) -> dict:
        """
        Decodifica e valida um token JWT.

        Args:
            token (str): Token JWT a ser validado.

        Returns:
            dict: Payload decodificado do token.

        Raises:
            ValueError: Se o token for inválido ou expirado.
        """
        try:
            # Configuramos o algoritmo e verificamos a expiração
            return jwt.decode(
                token, 
                JWT_SECRET_KEY, 
                algorithms=["HS256"],
                options={"verify_exp": True}
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expirado.")
        except jwt.InvalidTokenError:
            raise ValueError("Token inválido.")

    @staticmethod
    def check_permissions(role_required: str, user_role: str) -> bool:
        """
        Verifica se o usuário possui o papel necessário para executar uma ação.

        Args:
            role_required (str): Papel necessário para acessar o recurso.
            user_role (str): Papel do usuário atual.

        Returns:
            bool: True se o usuário tiver permissão, False caso contrário.
        """
        if user_role == "admin":
            return True
        return user_role == role_required
        
    async def generate_refresh_token(self, user: User) -> str:
        """
        Gera um novo refresh token para um usuário.
        
        Args:
            user (User): Usuário para o qual o token será gerado.
            
        Returns:
            str: Token de atualização gerado.
        """
        # Gerar um token único
        token_value = str(uuid.uuid4())
        
        # Calcular a data de expiração
        expires_at = TIMEZONE() + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
        
        # Criar o novo token
        refresh_token = RefreshToken(
            token=token_value,
            user_id=user.id,
            expires_at=expires_at
        )
        
        # Salvar no banco de dados
        try:
            self.db_session.add(refresh_token)
            await self.db_session.commit()
            return token_value
        except Exception as e:
            await self.db_session.rollback()
            raise e
    
    async def verify_refresh_token(self, token: str) -> Tuple[bool, Optional[User]]:
        """
        Verifica se um refresh token é válido.
        
        Args:
            token (str): Token de atualização a ser verificado.
            
        Returns:
            Tuple[bool, Optional[User]]: Uma tupla contendo um booleano indicando
                                         se o token é válido e o usuário associado
                                         ao token (se for válido).
        """
        # Buscar o token no banco de dados
        result = await self.db_session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token == token,
                    RefreshToken.is_revoked == False
                )
            )
        )
        refresh_token = result.scalars().first()
        
        # Verificar se o token existe e é válido
        if not refresh_token or refresh_token.is_expired:
            return False, None
        
        # Buscar o usuário associado ao token
        user_result = await self.db_session.execute(
            select(User).where(User.id == refresh_token.user_id)
        )
        user = user_result.scalars().first()
        
        if not user or not user.is_active:
            return False, None
            
        return True, user
    
    async def refresh_access_token(self, refresh_token: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Gera um novo access token a partir de um refresh token.
        
        Args:
            refresh_token (str): Token de atualização a ser usado.
            
        Returns:
            Tuple[bool, str, dict]: Uma tupla contendo:
                                    - Um booleano indicando sucesso ou falha
                                    - Uma mensagem de sucesso ou erro
                                    - Um dicionário com os tokens (se sucesso)
        """
        # Verificar o refresh token
        is_valid, user = await self.verify_refresh_token(refresh_token)
        
        if not is_valid or not user:
            return False, "Refresh token inválido ou expirado", {}
        
        # Gerar um novo access token
        access_token = self.generate_jwt_token(user)
        
        return True, "Token atualizado com sucesso", {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": JWT_EXPIRATION_MINUTES * 60  # em segundos
        }
    
    async def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoga um refresh token específico.
        
        Args:
            token (str): Token a ser revogado.
            
        Returns:
            bool: True se o token foi revogado com sucesso, False caso contrário.
        """
        try:
            # Buscar o token
            result = await self.db_session.execute(
                select(RefreshToken).where(RefreshToken.token == token)
            )
            refresh_token = result.scalars().first()
            
            if not refresh_token:
                return False
            
            # Revogar o token
            refresh_token.is_revoked = True
            await self.db_session.commit()
            return True
        except Exception:
            await self.db_session.rollback()
            return False
    
    async def revoke_all_refresh_tokens(self, user_id: int) -> bool:
        """
        Revoga todos os refresh tokens de um usuário.
        
        Args:
            user_id (int): ID do usuário.
            
        Returns:
            bool: True se os tokens foram revogados com sucesso, False caso contrário.
        """
        try:
            # Buscar todos os tokens não revogados do usuário
            result = await self.db_session.execute(
                select(RefreshToken).where(
                    and_(
                        RefreshToken.user_id == user_id,
                        RefreshToken.is_revoked == False
                    )
                )
            )
            refresh_tokens = result.scalars().all()
            
            # Revogar todos os tokens
            for token in refresh_tokens:
                token.is_revoked = True
            
            await self.db_session.commit()
            return True
        except Exception:
            await self.db_session.rollback()
            return False
