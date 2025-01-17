# D:\#3xDigital\app\config\settings.py

from dotenv import load_dotenv
import os
from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from zoneinfo import ZoneInfo

# Carrega as variáveis do arquivo .env
load_dotenv()

# Pegamos a chave JWT de variável de ambiente ou usamos um fallback inseguro (apenas para desenvolvimento)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")

# URL do banco de dados assíncrono
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./3x_digital.db")

# Tempo de expiração do JWT (em minutos, por exemplo)
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", 60))

# Outras configurações que venham a ser necessárias

DB_SESSION_KEY = web.AppKey[AsyncSession]("db_session")
TIMEZONE = datetime.now(ZoneInfo("America/Sao_Paulo"))