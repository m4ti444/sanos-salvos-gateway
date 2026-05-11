"""
Sanos y Salvos — API Gateway Configuration
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Database (for auth)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "sanosysalvos")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "sanosysalvos2026")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sanosysalvos_db")

    # Service URLs
    PETS_SERVICE_URL: str = os.getenv("PETS_SERVICE_URL", "http://localhost:8001")
    GEO_SERVICE_URL: str = os.getenv("GEO_SERVICE_URL", "http://localhost:8002")
    MATCH_SERVICE_URL: str = os.getenv("MATCH_SERVICE_URL", "http://localhost:8003")
    NOTIFICATIONS_SERVICE_URL: str = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8004")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"


settings = Settings()
