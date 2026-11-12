"""Hash de contraseñas (Argon2id) y JWT — mismo patrón que agecare-admin-api."""
import asyncio
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

# Argon2id con la configuración mínima que recomienda OWASP (19 MiB, 2 pasadas, 1 hilo). Antes se usaban los
# valores por defecto de la librería (64 MiB, 3 pasadas, 4 hilos): cada hash costaba el doble y ocupaba 4 núcleos,
# así que el servidor aguantaba ~14 inicios de sesión por segundo contra ~60 ahora. Los hashes ya guardados
# siguen siendo válidos: cada uno lleva sus propios parámetros.
_ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# Argon2 usa 64 MB y varios hilos por cada hash: si se calculan muchos a la vez, la máquina se satura y todo
# se pone lento. Un grupo pequeño de hilos hace que se turnen (los demás esperan sin bloquear el servidor).
_HASH_POOL = ThreadPoolExecutor(max_workers=int(os.getenv("HASH_WORKERS", str(min(4, os.cpu_count() or 2)))), thread_name_prefix="argon2")


async def ahash_password(password: str) -> str:
    """Argon2 gasta ~150 ms de CPU a propósito. Se calcula fuera del hilo principal para no frenar a los demás."""
    return await asyncio.get_running_loop().run_in_executor(_HASH_POOL, hash_password, password)


async def averify_password(password: str, password_hash: str) -> bool:
    return await asyncio.get_running_loop().run_in_executor(_HASH_POOL, verify_password, password, password_hash)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def create_access_token(user_id: UUID) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now_utc().timestamp()),
        "exp": now_utc() + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                      options={"require": ["exp", "sub"]})


def new_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    return token, hash_refresh(token), now_utc() + timedelta(days=get_settings().refresh_token_days)


def hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
