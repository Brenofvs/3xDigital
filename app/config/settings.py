# D:\3xDigital\app\config\settings.py

"""
settings.py

Este módulo contém as configurações principais da aplicação, incluindo variáveis
de ambiente, configurações do banco de dados, chave JWT e fuso horário.

Configurações:
    JWT_SECRET_KEY: Chave secreta para assinar tokens JWT.
    DATABASE_URL: URL de conexão com o banco de dados assíncrono.
    JWT_EXPIRATION_MINUTES: Tempo de expiração dos tokens JWT, em minutos.
    DB_SESSION_KEY: Chave para armazenar a sessão do banco de dados na aplicação.
    TIMEZONE: Configuração do fuso horário padrão da aplicação.
"""

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
"""
str: Chave secreta usada para assinar e verificar tokens JWT. 
Carregada de uma variável de ambiente ou definida como um valor padrão para fins de desenvolvimento.
"""

# URL do banco de dados assíncrono
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./3x_digital.db")
"""
str: URL de conexão com o banco de dados assíncrono. 
Carregada de uma variável de ambiente ou definida como SQLite padrão em ambiente de desenvolvimento.
"""

# Tempo de expiração do JWT (em minutos, por exemplo)
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", 60))
"""
int: Tempo de expiração dos tokens JWT, em minutos. 
Padrão é 60 minutos se não for definido na variável de ambiente.
"""

# Tempo de expiração do Refresh Token (em dias)
REFRESH_TOKEN_EXPIRATION_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", 30))
"""
int: Tempo de expiração dos refresh tokens, em dias.
Padrão é 30 dias se não for definido na variável de ambiente.
"""

# Outras configurações que venham a ser necessárias

DB_SESSION_KEY = web.AppKey[AsyncSession]("db_session")
"""
web.AppKey[AsyncSession]: Chave para armazenar e recuperar a sessão de banco de dados na aplicação AIOHTTP.
"""

def get_current_timezone():
    """Retorna o datetime atual no fuso horário de São Paulo"""
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

# Usamos uma função lambda para evitar chamar get_current_timezone() na definição
# e sim apenas quando o SQLAlchemy precisar do valor (lazy evaluation)
TIMEZONE = lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
"""
function: Função que retorna o datetime atual no fuso horário "America/Sao_Paulo".
Usada para valores default e onupdate nos modelos SQLAlchemy.
"""
