"""add preferred_language to tenants

Revision ID: 031
Revises: 030
Create Date: 2026-04-04

"""
import sqlalchemy as sa

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("preferred_language", sa.String(10), server_default="en", nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "preferred_language")
