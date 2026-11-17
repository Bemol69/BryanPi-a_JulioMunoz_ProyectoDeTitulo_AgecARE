"""Exención de la verificación con motivo y vencimiento, y datos del pago (método y comprobante).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TABLE = "marketplace_caregivers"
COLUMNS = [
    sa.Column("verification_waiver_reason", sa.String(24), nullable=True),
    sa.Column("verification_waiver_note", sa.String(300), nullable=True),
    sa.Column("verification_waiver_until", sa.DateTime(timezone=True), nullable=True),
    sa.Column("verification_payment_method", sa.String(16), nullable=True),
    sa.Column("verification_receipt", sa.String(60), nullable=True),
]


def upgrade() -> None:
    # Idempotente: el despliegue puede haber agregado ya las columnas (ver app/schema_sync.py).
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for col in COLUMNS:
        if col.name not in existing:
            op.add_column(TABLE, col.copy())


def downgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}
    for col in reversed(COLUMNS):
        if col.name in existing:
            op.drop_column(TABLE, col.name)
