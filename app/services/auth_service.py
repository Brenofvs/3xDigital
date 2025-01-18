# D:\#3xDigital\app\services\auth_service.py

import bcrypt
import jwt
from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import User
from app.config.settings import JWT_SECRET_KEY, TIMEZONE

class AuthService:
    def __init__(self, db_session: AsyncSession):
        """
        Recebe a sessão assíncrona do banco de dados (injeção de dependência).
        """
        self.db_session = db_session

    async def create_user(self, name: str, email: str, password: str, role: str = "affiliate") -> User:
        """
        Cria um novo usuário com hash de senha, de forma assíncrona.
        """
        # Verifica se o email já está registrado
        result = await self.db_session.execute(select(User).where(User.email == email))
        existing_user = result.scalars().first()
        if existing_user:
            raise ValueError("O email já está registrado.")
        
        # Cria o hash da senha
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        # Cria o novo usuário
        new_user = User(
            name=name,
            email=email,
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

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Verifica se existe um usuário com este e-mail e se a senha confere.
        Retorna o objeto User ou None.
        """
        # Trocar 'User.__table__.select()' por 'select(User)'
        result = await self.db_session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalars().first()

        if user and bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return user
        return None

    def generate_jwt_token(self, user: User) -> str:
        """
        Gera um token JWT contendo ID e role do usuário, com expiração de 1 hora.
        """
        expires = TIMEZONE + timedelta(hours=1)
        payload = {
            "sub": str(user.id),  # agora é string
            "role": user.role,
            "exp": expires
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_jwt_token(token: str) -> dict:
        """
        Decodifica o JWT, lançando exceções em caso de erro.
        """
        try:
            decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            return decoded
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expirado.")
        except jwt.InvalidTokenError:
            raise ValueError("Token inválido.")

    @staticmethod
    def check_permissions(role_required: str, user_role: str) -> bool:
        """
        Exemplo simples de checagem de papel do usuário.
        """
        if user_role == "admin":
            return True
        return user_role == role_required
