"""credit transactions table + tenant credit_balance column

Revision ID: 010
Revises: 009
Create Date: 2026-03-28

"""
from alembic import op  # noqa: I001
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_transactions_tenant_created", "credit_transactions", ["tenant_id", "created_at"])

    op.add_column("tenants", sa.Column("credit_balance", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "credit_balance")
    op.drop_index("ix_credit_transactions_tenant_created")
    op.drop_table("credit_transactions")
