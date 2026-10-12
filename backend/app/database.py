"""Motor async de SQLAlchemy y sesión por petición."""
import asyncio
import logging
import os
import time
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


_schema_ready = False
_schema_retry_at = 0.0
_schema_lock: asyncio.Lock | None = None


async def _ensure_schema_once() -> None:
    """Agrega las columnas nuevas que falten, una vez por instancia (ver app/schema_sync.py).
    Si falla no tumba la API: se registra y se reintenta pasado un minuto."""
    global _schema_ready, _schema_retry_at, _schema_lock
    if _schema_ready or time.monotonic() < _schema_retry_at:
        return
    if _schema_lock is None:
        _schema_lock = asyncio.Lock()
    async with _schema_lock:
        if _schema_ready:
            return
        from app.schema_sync import ensure_schema
        try:
            await ensure_schema(get_engine())
            _schema_ready = True
        except Exception:  # noqa: BLE001
            logging.getLogger("agecare.schema").exception("No se pudo sincronizar el esquema")
            _schema_retry_at = time.monotonic() + 60


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: una sesión por petición, commit al éxito."""
    await _ensure_schema_once()
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
