"""Add deactivated_at, bypass_limits, plan_overrides to tenants.

Revision ID: 050_tenant_admin_controls
Revises: 049_team_invite_tokens
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "050_tenant_admin_controls"
down_revision = "049_team_invite_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("bypass_limits", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("tenants", sa.Column("plan_overrides", JSONB(), nullable=True))
    op.create_index("ix_tenants_deactivated_at", "tenants", ["deactivated_at"])


def downgrade() -> None:
    op.drop_index("ix_tenants_deactivated_at", table_name="tenants")
    op.drop_column("tenants", "plan_overrides")
    op.drop_column("tenants", "bypass_limits")
    op.drop_column("tenants", "deactivated_at")
