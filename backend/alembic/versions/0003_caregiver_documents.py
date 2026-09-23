"""Agrega marketplace_caregiver_documents (documentos de respaldo de cuidadoras).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-22
"""
from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create_all solo crea las tablas que todavía no existen (como 0001), así
    # que es seguro volver a llamarlo: únicamente añade marketplace_caregiver_documents.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.tables["marketplace_caregiver_documents"].drop(bind=op.get_bind())
