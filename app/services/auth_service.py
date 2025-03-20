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
from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import User
from app.config.settings import JWT_SECRET_KEY, TIMEZONE, get_current_timezone

class AuthService:
    """
    Serviço de autenticação e autorização.

    Métodos:
        create_user: Cria um novo usuário com hash de senha.
        authenticate_user: Autentica um usuário com base em e-mail e senha.
        generate_jwt_token: Gera um token JWT para um usuário.
        verify_jwt_token: Decodifica e valida um token JWT.
        check_permissions: Verifica se o usuário tem o papel necessário.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Inicializa o AuthService com uma sessão de banco de dados.

        Args:
            db_session (AsyncSession): Sessão assíncrona do banco de dados.
        """
        self.db_session = db_session

    async def create_user(self, name: str, email: str, cpf: str, password: str, role: str = "affiliate") -> User:
        """
        Cria um novo usuário com hash de senha de forma assíncrona.

        Args:
            name (str): Nome do usuário.
            email (str): E-mail do usuário.
            password (str): Senha do usuário.
            role (str, optional): Papel do usuário. Padrão é "affiliate".

        Returns:
            User: Objeto do usuário criado.

        Raises:
            ValueError: Se o e-mail já estiver registrado.
            Exception: Caso ocorra algum erro na criação do usuário.
        """
        result = await self.db_session.execute(select(User).where((User.email == email) | (User.cpf == cpf)))
        existing_user = result.scalars().first()
        if existing_user:
            raise ValueError("E-mail ou CPF já está registrado.")
        
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        new_user = User(
            name=name,
            email=email,
            cpf=cpf,
            password_hash=password_hash,
            role=role
        )
        try:
            self.db_session.add(new_user)
            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            return new_user
        except Exception as e:
            await self.db_session.rollback()
            raise e

    async def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        """
        Autentica um usuário verificando o e-mail e a senha.

        Args:
            email (str): E-mail do usuário.
            password (str): Senha do usuário.

        Returns:
            Optional[User]: Retorna o objeto do usuário autenticado ou None se as credenciais forem inválidas.
        """
        result = await self.db_session.execute(select(User).where((User.email == identifier) | (User.cpf == identifier)))
        user = result.scalars().first()

        if user and bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return user
        return None

    def generate_jwt_token(self, user: User) -> str:
        """
        Gera um token JWT contendo informações do usuário.

        Args:
            user (User): Objeto do usuário para o qual o token será gerado.

        Returns:
            str: Token JWT gerado.
        """
        expires = TIMEZONE() + timedelta(hours=1)
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
