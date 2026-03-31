"""Add rollover_balance and rollover_cap to credit_accounts.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_accounts", sa.Column("rollover_balance", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("credit_accounts", sa.Column("rollover_cap", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("credit_accounts", "rollover_cap")
    op.drop_column("credit_accounts", "rollover_balance")
