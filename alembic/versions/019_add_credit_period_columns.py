"""Add period_start and period_end to credit_accounts.

Revision ID: 019
Revises: 018
"""

import sqlalchemy as sa

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credit_accounts",
        sa.Column("period_start", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "credit_accounts",
        sa.Column("period_end", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_column("credit_accounts", "period_end")
    op.drop_column("credit_accounts", "period_start")
