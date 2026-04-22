"""Tenant admin controls: soft-delete, limit bypass, plan overrides.

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
    # Soft-delete marker. Deactivated tenants fail auth with 401, are
    # hidden from default admin list responses, and cannot issue new
    # access tokens. Historical rows (listings, credits, audit log) are
    # retained — this is a soft delete, not a cascade.
    op.add_column(
        "tenants",
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # When true, requests for this tenant skip the API rate limiter and
    # plan quota checks (monthly listing quota, per-listing asset quota).
    op.add_column(
        "tenants",
        sa.Column(
            "bypass_limits",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Per-tenant overrides merged on top of the plan-tier defaults from
    # listingjet.services.plan_limits.PLAN_LIMITS. Keys that appear here
    # override the base value; other keys fall through to the plan tier.
    op.add_column(
        "tenants",
        sa.Column("plan_overrides", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "plan_overrides")
    op.drop_column("tenants", "bypass_limits")
    op.drop_column("tenants", "deactivated_at")
