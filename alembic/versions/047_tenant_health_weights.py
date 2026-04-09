"""Persist custom health score weights per tenant.

Revision ID: 047_tenant_health_weights
Revises: 046_drop_credit_balance
"""

import sqlalchemy as sa

from alembic import op

revision = "047_tenant_health_weights"
down_revision = "046_drop_credit_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_health_weights",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("media", sa.Float(), nullable=False, server_default="0.30"),
        sa.Column("content", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("velocity", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("syndication", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("market", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_thw_tenant_id", "tenant_health_weights", ["tenant_id"])
    op.create_unique_constraint("uq_thw_tenant", "tenant_health_weights", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("tenant_health_weights")
