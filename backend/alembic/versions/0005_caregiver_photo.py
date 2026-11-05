"""Foto de la cuidadora en la Consola (se sincroniza desde el sitio público).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TABLE = "marketplace_caregivers"


def upgrade() -> None:
    # Idempotente: el despliegue puede haber agregado ya la columna (ver app/schema_sync.py).
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    if "photo_url" not in existing:
        op.add_column(TABLE, sa.Column("photo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    if "photo_url" in existing:
        op.drop_column(TABLE, "photo_url")
