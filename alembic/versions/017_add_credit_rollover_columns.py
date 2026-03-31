"""Add rollover_balance to credit_accounts.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # rollover_cap already exists from migration 010 (credit_accounts table creation)
    op.add_column("credit_accounts", sa.Column("rollover_balance", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("credit_accounts", "rollover_balance")
