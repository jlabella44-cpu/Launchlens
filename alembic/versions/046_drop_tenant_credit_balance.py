"""Drop legacy credit_balance column from tenants table.

CreditAccount is the single source of truth for credit balances.
Tenant.credit_balance was a legacy duplicate that could drift out of sync.

Revision ID: 046_drop_credit_balance
Revises: 045_phase5_enrichments
"""

import sqlalchemy as sa

from alembic import op

revision = "046_drop_credit_balance"
down_revision = "045_phase5_enrichments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("tenants", "credit_balance")


def downgrade() -> None:
    op.add_column("tenants", sa.Column("credit_balance", sa.Integer(), server_default="0", nullable=False))
