"""add missing credit columns to tenants

Revision ID: 016
Revises: 015
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("credit_balance", sa.Integer(), server_default="0", nullable=False))
    op.add_column("tenants", sa.Column("rollover_cap", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "rollover_cap")
    op.drop_column("tenants", "credit_balance")
