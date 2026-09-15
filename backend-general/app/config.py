"""Configuración de la API general de AgeCare (usuarios, pacientes, marketplace)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GENERAL_", extra="ignore")

    app_name: str = "AgeCare General API"
    environment: str = "dev"
    database_url: str = "postgresql+asyncpg://agecare:agecare@localhost:5433/agecare_general"

    jwt_secret: str = "cambia-esto-en-produccion"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30

    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # Sincroniza el perfil publicado hacia la Consola de Administración
    # (falla silenciosamente si el otro servicio no responde).
    admin_sync_url: str = "http://host.docker.internal:8000/api/v1/admin"
    admin_sync_key: str = "clave-interna-solo-para-desarrollo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
