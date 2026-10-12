"""Sincronización idempotente del esquema (solo PostgreSQL).

Las tablas de la Consola las crea Alembic. Para que un despliegue desde GitHub no requiera
correr migraciones a mano en Supabase, al atender la primera petición de cada instancia se
agregan las columnas nuevas que falten (las mismas que agregan las migraciones, que son
idempotentes). Si ya está al día son solo dos consultas de lectura."""
from sqlalchemy import text

# (tabla, columna, definición). Agregar aquí cada columna nueva de un modelo existente.
COLUMN_PATCHES: list[tuple[str, str, str]] = [
    ("marketplace_caregiver_documents", "status", "VARCHAR(16) NOT NULL DEFAULT 'pending'"),
    ("marketplace_caregiver_documents", "pending_file_url", "VARCHAR(500)"),
    ("marketplace_caregiver_documents", "pending_filename", "VARCHAR(255)"),
    ("marketplace_caregiver_documents", "review_note", "TEXT"),
    ("marketplace_caregiver_documents", "reviewed_at", "TIMESTAMP WITH TIME ZONE"),
    ("marketplace_caregiver_documents", "reviewed_by_name", "VARCHAR(120)"),
]
ADVISORY_LOCK_KEY = 727_502


async def ensure_schema(engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ADVISORY_LOCK_KEY})
        existing_cols = {(r[0], r[1]) for r in (await conn.execute(text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'"))).all()}
        existing_tables = {t for t, _ in existing_cols}
        for table, column, ddl in COLUMN_PATCHES:
            if table in existing_tables and (table, column) not in existing_cols:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))
