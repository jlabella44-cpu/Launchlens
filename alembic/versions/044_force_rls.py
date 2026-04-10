"""force row level security on all tenant-isolated tables

Revision ID: 044_force_rls
Revises: 043_white_label
Create Date: 2026-04-08

PostgreSQL table owners bypass RLS by default.  Since the application
connects as the table owner (the same role that runs migrations), the
SET LOCAL app.current_tenant guard has no effect unless we explicitly
force RLS.  This migration adds FORCE ROW LEVEL SECURITY to every
table that already has ENABLE ROW LEVEL SECURITY.
"""

from alembic import op

revision = "044_force_rls"
down_revision = "043_white_label"
branch_labels = None
depends_on = None

# Every table that has ENABLE ROW LEVEL SECURITY across migrations 001-042.
_RLS_TABLES = [
    # 001_initial_schema
    "listings",
    "assets",
    "package_selections",
    "events",
    # 005_social_content_export_demo
    "social_contents",
    # 006_dollhouse_scenes
    "dollhouse_scenes",
    # 007_video_assets
    "video_assets",
    # 041_health_score_and_idx_feed
    "listing_health_scores",
    "health_score_history",
    "idx_feed_configs",
    # 042_performance_intelligence
    "listing_outcomes",
    "performance_insights",
]


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
