"""Add listing health scores, health score history, and IDX feed configs tables.

Revision ID: 037_health_score
Revises: 036_support_tickets
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "037_health_score"
down_revision = "036_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- listing_health_scores: latest snapshot per listing --
    op.create_table(
        "listing_health_scores",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, unique=True, index=True),
        sa.Column("overall_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("media_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("velocity_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("syndication_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("market_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weights", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("signals_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS policy
    op.execute(
        "ALTER TABLE listing_health_scores ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY tenant_isolation ON listing_health_scores "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    # -- health_score_history: rolling 90-day append-only --
    op.create_table(
        "health_score_history",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, index=True),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("media_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("velocity_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("syndication_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("market_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_health_history_listing_calc",
        "health_score_history",
        ["listing_id", "calculated_at"],
    )

    # RLS policy
    op.execute(
        "ALTER TABLE health_score_history ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY tenant_isolation ON health_score_history "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    # -- idx_feed_configs: per-tenant RESO connection --
    op.create_table(
        "idx_feed_configs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("api_key_encrypted", sa.String(1000), nullable=False),
        sa.Column("board_id", sa.String(100), nullable=True),
        sa.Column("poll_interval_minutes", sa.Integer(), server_default="60"),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS policy
    op.execute(
        "ALTER TABLE idx_feed_configs ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY tenant_isolation ON idx_feed_configs "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON idx_feed_configs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON health_score_history")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON listing_health_scores")
    op.drop_table("idx_feed_configs")
    op.drop_table("health_score_history")
    op.drop_table("listing_health_scores")
