"""Rentabilidad: cobro de verificación a cuidadoras y patrocinio/comisión en artículos de apoyo.

Las cuidadoras que ya existían quedan "waived" (eximidas): el cobro aplica a las nuevas.
Los artículos con categoría en español se pasan a las claves que usa el sitio público.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

CAREGIVERS = "marketplace_caregivers"
PRODUCTS = "marketplace_products"
CAREGIVER_COLUMNS = [
    sa.Column("verification_fee_status", sa.String(10), nullable=False, server_default="waived"),
    sa.Column("verification_fee_clp", sa.Integer(), nullable=False, server_default="9990"),
    sa.Column("verification_reference", sa.String(20), nullable=True),
    sa.Column("verification_paid_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("verification_marked_by", sa.String(120), nullable=True),
]
PRODUCT_COLUMNS = [
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("is_sponsored", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("conditions", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=True),
    sa.Column("commission_pct", sa.Float(), nullable=True),
]
CATEGORY_KEYS = {"Movilidad": "mobility", "Monitoreo": "monitoring", "Seguridad en el hogar": "home_safety",
                 "Seguridad": "home_safety", "Medicación": "daily_care", "Cuidado diario": "daily_care"}


def _add_missing(table: str, columns: list[sa.Column]) -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    for col in columns:
        if col.name not in existing:
            op.add_column(table, col.copy())


def upgrade() -> None:
    # Idempotente: el despliegue puede haber agregado ya las columnas (ver app/schema_sync.py).
    _add_missing(CAREGIVERS, CAREGIVER_COLUMNS)
    _add_missing(PRODUCTS, PRODUCT_COLUMNS)
    for old, new in CATEGORY_KEYS.items():
        op.execute(sa.text(f"UPDATE {PRODUCTS} SET category = :new WHERE category = :old").bindparams(new=new, old=old))


def downgrade() -> None:
    for table, columns in ((PRODUCTS, PRODUCT_COLUMNS), (CAREGIVERS, CAREGIVER_COLUMNS)):
        existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for col in reversed(columns):
            if col.name in existing:
                op.drop_column(table, col.name)
