"""Configuración de la API general de AgeCare (usuarios, pacientes, marketplace)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Acepta la cadena de conexión tal como la entrega Supabase (postgresql://...) y la
    convierte al formato de SQLAlchemy asíncrono. Si el host es de Supabase exige SSL."""
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break
    base = url.split("?", 1)[0]  # asyncpg no entiende sslmode/pgbouncer en la URL
    if "supabase." in base:
        base += "?ssl=require"
    return base


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

    # Supabase Storage para fotos y documentos (en Vercel el disco es de solo lectura).
    # Si no se configuran, los archivos se guardan en la carpeta local uploads/.
    supabase_url: str = ""
    supabase_service_key: str = ""
    storage_bucket: str = "agecare-uploads"

    @field_validator("database_url")
    @classmethod
    def _normalize_url(cls, v: str) -> str:
        return normalize_database_url(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
