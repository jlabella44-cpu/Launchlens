"""credit system — tenant credit fields + credit_transactions table

Revision ID: 010
Revises: 009
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add credit columns to tenants
    op.add_column("tenants", sa.Column("credit_balance", sa.Integer(), server_default="0", nullable=False))
    op.add_column("tenants", sa.Column("included_credits", sa.Integer(), server_default="0", nullable=False))
    op.add_column("tenants", sa.Column("rollover_cap", sa.Integer(), server_default="0", nullable=False))

    # Create credit_transactions table
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True, index=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("credit_transactions")
    op.drop_column("tenants", "rollover_cap")
    op.drop_column("tenants", "included_credits")
    op.drop_column("tenants", "credit_balance")
