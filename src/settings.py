import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(find_dotenv())

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RUN_TYPE = os.getenv('RUN_TYPE', 'DOCKER')


class EmailProviderSettings(BaseSettings):
    EMAIL_HOST: str = 'smtp.yandex.ru'
    EMAIL_PORT: int = 465
    EMAIL_USE_SSL: bool = True

    EMAIL_HOST_USER: str
    EMAIL_HOST_PASSWORD: str


class AuthSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 120

    FRONTEND_RESET_PASSWORD_CALLBACK_URL: str = 'http://127.0.0.1:8000/reset'
    RESET_PASSWORD_CODE_TTL: int = 3600


class Settings(BaseSettings):
    DEBUG: bool = os.getenv('DEBUG').lower() == 'true'

    PROJECT_NAME: str
    MEDIA_DIR: Path = os.path.join(BASE_DIR, os.getenv('media', 'media'))
    SERVER_URL: str = 'http://127.0.0.1:8000/'

    DEFAULT_ELEMENTS_PER_PAGE: int = 25
    MAX_ELEMENTS_PER_PAGE: int = 100

    DOCS_URL: str = '/api/docs'
    REDOC_URL: str = '/api/redoc'
    OPENAPI_URL: str = '/api/docs/openapi.json'

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int

    REDIS_HOST: str = 'redis'
    REDIS_PORT: int = 6379

    auth: AuthSettings = AuthSettings()
    email: EmailProviderSettings = EmailProviderSettings()

    @property
    def DATABASE_DSN(self) -> str:
        hostname = 'postgres' if RUN_TYPE == 'DOCKER' else 'localhost'
        return (
            f'postgresql+asyncpg://'
            f'{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
            f'@{hostname}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )


settings = Settings()
