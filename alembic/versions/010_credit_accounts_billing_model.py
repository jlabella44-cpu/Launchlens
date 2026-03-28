"""credit accounts and tenant billing_model

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
    # Add billing_model column to tenants
    op.add_column("tenants", sa.Column("billing_model", sa.String(50), server_default="credit", nullable=False))

    # Create credit_accounts table
    op.create_table(
        "credit_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("balance", sa.Float(), server_default="0", nullable=False),
        sa.Column("included_credits", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rollover_cap", sa.Integer(), server_default="5", nullable=False),
        sa.Column("per_listing_credit_cost", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tier", sa.String(50), server_default="lite", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_accounts_tenant_id", "credit_accounts", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_credit_accounts_tenant_id", table_name="credit_accounts")
    op.drop_table("credit_accounts")
    op.drop_column("tenants", "billing_model")
