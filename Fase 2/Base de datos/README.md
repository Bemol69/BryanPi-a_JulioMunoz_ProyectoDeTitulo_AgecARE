# Evidencia de base de datos

Las dos aplicaciones de AgeCare usan **PostgreSQL** (alojado en Supabase en producción). Esta carpeta documenta su
estructura, generada directamente desde los modelos del código, por lo que siempre refleja lo que realmente se usa.

| Archivo | Qué contiene |
|---|---|
| [`diagramas/`](diagramas/) | Diagramas entidad-relación en imagen (`.png`) y en texto (`.mmd`, formato Mermaid) |
| [`Diccionario de datos.md`](Diccionario%20de%20datos.md) | Las 38 tablas con su propósito, columnas, tipos y relaciones |
| [`esquema_consola.sql`](esquema_consola.sql) | Script SQL (`CREATE TABLE` e índices) de la Consola de Administración |
| [`esquema_sitio_publico.sql`](esquema_sitio_publico.sql) | Script SQL del sitio público |

## Otras evidencias de datos en el repositorio

- **Migraciones versionadas** de la Consola: `backend/alembic/versions/` (cuatro versiones, de `0001_initial` a
  `0004_document_review`).
- **Sincronización del esquema del sitio público:** `backend-general/app/schema_sync.py`, que agrega las tablas y
  columnas que falten al iniciar.
- **Seguridad por filas (RLS) en Supabase:** `deploy/supabase_seguridad.sql`.
- **Migraciones manuales de la Fase 2:** `deploy/migracion_2026-10-12.sql` y `deploy/migracion_2026-10-12_solicitudes.sql`.
- **Datos de prueba:** `backend/scripts/seed.py` y `backend-general/scripts/seed.py`.
