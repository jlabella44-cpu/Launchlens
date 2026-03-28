"""add webhook_url to tenants

Revision ID: 008
Revises: 007
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("webhook_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "webhook_url")
