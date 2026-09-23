"""Agrega is_engaged a marketplace_caregivers (indica si la cuidadora tiene
un trabajo activo con alguna familia).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 crea las tablas con Base.metadata.create_all() a partir del models.py
    # vigente, así que en una base nueva "is_engaged" ya nace creada junto con la
    # tabla. Solo hace falta el ALTER en una base que exista desde antes de este
    # campo (ya con datos, corriendo 0001 -> 0002 en orden).
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("marketplace_caregivers")]
    if "is_engaged" not in columns:
        op.add_column("marketplace_caregivers",
                      sa.Column("is_engaged", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("marketplace_caregivers", "is_engaged")
