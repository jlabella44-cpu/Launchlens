"""add cancelled state to listingstate enum, remove dead states

Revision ID: 024
Revises: 023
Create Date: 2026-04-01

"""
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # Postgres doesn't support removing enum values; no-op
    pass
