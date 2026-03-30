"""add superadmin to userrole enum

Revision ID: 015
Revises: 014
Create Date: 2026-03-27
"""
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'superadmin' BEFORE 'admin'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; recreating the type
    # would require rewriting the column.  Leaving as-is for downgrade.
    pass
