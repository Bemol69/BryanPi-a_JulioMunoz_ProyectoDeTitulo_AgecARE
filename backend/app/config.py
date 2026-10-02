"""Configuración de la API de administración de AgeCare."""
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
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADMIN_", extra="ignore")

    app_name: str = "AgeCare Admin API"
    environment: str = "dev"  # dev | staging | prod
    database_url: str = "postgresql+asyncpg://agecare:agecare@localhost:5432/agecare_admin"

    # JWT
    jwt_secret: str = "cambia-esto-en-produccion"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_hours: int = 12

    # Login
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    allowed_email_domains: str = "wellq.co.uk,wellq.co"  # separados por coma

    # Negocio
    business_timezone: str = "America/Santiago"

    # Clave compartida para el endpoint de sincronizacion con el sitio publico.
    internal_sync_key: str = "clave-interna-solo-para-desarrollo"

    @field_validator("database_url")
    @classmethod
    def _normalize_url(cls, v: str) -> str:
        return normalize_database_url(v)

    @property
    def allowed_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
