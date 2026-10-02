"""Motor async de SQLAlchemy y sesión por petición."""
import os
from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _engine_options(url: str) -> dict:
    """Opciones del motor según dónde corre: local (pool normal), Vercel (sin pool, cada
    invocación abre su conexión) o pooler transaccional de Supabase (puerto 6543, que no
    admite sentencias preparadas con nombre fijo)."""
    opts: dict = {"pool_pre_ping": True}
    transaction_pooler = ":6543/" in url
    if transaction_pooler or os.getenv("VERCEL"):
        opts["poolclass"] = NullPool
    if transaction_pooler:
        opts["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
    return opts


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, **_engine_options(get_settings().database_url))
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: una sesión por petición, commit al éxito."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
