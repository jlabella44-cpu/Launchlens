"""allow explicit admin context through tenant RLS policies

Revision ID: 051_admin_rls_bypass
Revises: 050_tenant_admin_controls
Create Date: 2026-04-26
"""

from alembic import op

revision = "051_admin_rls_bypass"
down_revision = "050_tenant_admin_controls"
branch_labels = None
depends_on = None

_RLS_TABLES = [
    "listings",
    "assets",
    "package_selections",
    "events",
    "social_contents",
    "dollhouse_scenes",
    "video_assets",
    "listing_health_scores",
    "health_score_history",
    "idx_feed_configs",
    "listing_outcomes",
    "performance_insights",
]

_ADMIN_AWARE_POLICY = """
    CREATE POLICY tenant_isolation ON {table}
    USING (
        current_setting('app.is_admin', true) = 'true'
        OR tenant_id = current_setting('app.current_tenant', true)::uuid
    )
"""

_TENANT_ONLY_POLICY = """
    CREATE POLICY tenant_isolation ON {table}
    USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
"""


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(_ADMIN_AWARE_POLICY.format(table=table))


def downgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(_TENANT_ONLY_POLICY.format(table=table))