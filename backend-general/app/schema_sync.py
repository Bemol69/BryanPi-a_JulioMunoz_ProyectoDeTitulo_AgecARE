"""Sincronización idempotente del esquema de la base de datos (solo PostgreSQL).

El sitio público crea sus tablas con `create_all`, que NO agrega columnas a tablas que ya
existen. Para que los despliegues desde GitHub no requieran pasos manuales en Supabase, al
atender la primera petición de cada instancia se revisa el esquema y se aplica lo que falte:
tablas nuevas, columnas nuevas y seguridad por filas (RLS) en las tablas nuevas. Todo es
idempotente: si ya está al día, son solo dos consultas de lectura.
"""
import logging

import httpx
from sqlalchemy import text

from app.config import get_settings
from app.database import Base

log = logging.getLogger("agecare.schema")

# (tabla, columna, definición). Agregar aquí cada columna nueva de un modelo existente.
COLUMN_PATCHES: list[tuple[str, str, str]] = [
    ("caregiver_profiles", "admin_status", "VARCHAR(12) NOT NULL DEFAULT 'pending'"),
    ("caregiver_documents", "status", "VARCHAR(16) NOT NULL DEFAULT 'pending'"),
    ("caregiver_documents", "pending_file_url", "VARCHAR(500)"),
    ("caregiver_documents", "pending_filename", "VARCHAR(255)"),
    ("caregiver_documents", "review_note", "TEXT"),
    ("caregiver_documents", "reviewed_at", "TIMESTAMP WITH TIME ZONE"),
    ("caregiver_engagements", "review_id", "UUID"),
]
# Tablas que Supabase expondría por su API pública: se les activa RLS sin políticas.
RLS_TABLES = ["chat_conversations", "chat_messages", "hire_requests"]
ADVISORY_LOCK_KEY = 727_501  # evita que dos instancias nuevas apliquen el esquema a la vez


async def ensure_schema(engine) -> None:
    if engine.dialect.name != "postgresql":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    table_names = sorted(Base.metadata.tables.keys())
    admin_status_added = False
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ADVISORY_LOCK_KEY})
        existing_tables = {r[0] for r in (await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))).all()}
        missing_tables = [t for t in table_names if t not in existing_tables]
        if missing_tables:
            log.warning("Creando tablas nuevas: %s", ", ".join(missing_tables))
            await conn.run_sync(Base.metadata.create_all)

        existing_cols = {(r[0], r[1]) for r in (await conn.execute(text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'"))).all()}
        for table, column, ddl in COLUMN_PATCHES:
            if (table, column) in existing_cols or table not in existing_tables:
                continue
            log.warning("Agregando columna %s.%s", table, column)
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))
            if (table, column) == ("caregiver_profiles", "admin_status"):
                admin_status_added = True

        if admin_status_added:
            # Las cuidadoras que ya eran visibles siguen visibles; el estado real se trae de la Consola.
            await conn.execute(text("UPDATE caregiver_profiles SET admin_status = 'approved'"))
        for table in RLS_TABLES:
            if table in existing_tables or table in missing_tables:
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

    if admin_status_added:
        await _backfill_statuses_from_admin(engine)


async def _backfill_statuses_from_admin(engine) -> None:
    """Primera vez que existe admin_status: copia el estado real (aprobada / pendiente /
    suspendida) desde la Consola. Si la Consola no responde, queda 'approved' y el staff lo
    corrige con su próxima acción sobre el perfil."""
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{s.admin_sync_url}/marketplace/caregivers/statuses",
                                   headers={"X-Internal-Key": s.admin_sync_key})
        res.raise_for_status()
        items = res.json().get("items", [])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("No se pudo traer el estado de las cuidadoras desde la Consola: %s", exc)
        return
    async with engine.begin() as conn:
        for item in items:
            await conn.execute(text(
                "UPDATE caregiver_profiles SET admin_status = :st WHERE user_id IN "
                "(SELECT id FROM users WHERE lower(email) = lower(:email))"),
                {"st": item["status"], "email": item["email"]})
