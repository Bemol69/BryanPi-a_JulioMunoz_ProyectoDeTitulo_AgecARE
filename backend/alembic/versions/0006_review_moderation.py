"""Moderación de reseñas: archivar/restaurar y vínculo con la reseña del sitio público.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLE = "marketplace_caregiver_reviews"
COLUMNS = {
    "external_id": sa.Column("external_id", sa.Uuid(), nullable=True),
    "archived_at": sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    "archived_by_name": sa.Column("archived_by_name", sa.String(120), nullable=True),
}


def upgrade() -> None:
    # Idempotente: el despliegue puede haber agregado ya las columnas (ver app/schema_sync.py).
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for name, col in COLUMNS.items():
        if name not in existing:
            op.add_column(TABLE, col)


def downgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for name in COLUMNS:
        if name in existing:
            op.drop_column(TABLE, name)
