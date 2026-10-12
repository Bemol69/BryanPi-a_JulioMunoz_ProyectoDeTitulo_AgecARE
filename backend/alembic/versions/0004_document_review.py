"""Revisión de documentos de cuidadoras: estado, cambio pendiente y nota del staff.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TABLE = "marketplace_caregiver_documents"
COLUMNS = [
    sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
    sa.Column("pending_file_url", sa.String(500), nullable=True),
    sa.Column("pending_filename", sa.String(255), nullable=True),
    sa.Column("review_note", sa.Text(), nullable=True),
    sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("reviewed_by_name", sa.String(120), nullable=True),
]


def upgrade() -> None:
    # Idempotente: en producción el despliegue puede haber agregado ya estas columnas
    # (ver app/schema_sync.py); aquí solo se agregan las que falten.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for col in COLUMNS:
        if col.name not in existing:
            op.add_column(TABLE, col.copy())


def downgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for col in reversed(COLUMNS):
        if col.name in existing:
            op.drop_column(TABLE, col.name)
