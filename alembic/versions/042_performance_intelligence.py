"""Add listing_outcomes and performance_insights tables.

Revision ID: 042_performance_intelligence
Revises: 041_health_score
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "042_performance_intelligence"
down_revision = "041_health_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_outcomes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, unique=True, index=True),
        sa.Column("days_on_market", sa.Integer(), nullable=True),
        sa.Column("final_price", sa.Float(), nullable=True),
        sa.Column("original_price", sa.Float(), nullable=True),
        sa.Column("price_change_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("sold_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avg_photo_quality", sa.Float(), nullable=True),
        sa.Column("avg_commercial_score", sa.Float(), nullable=True),
        sa.Column("hero_quality", sa.Float(), nullable=True),
        sa.Column("coverage_pct", sa.Float(), nullable=True),
        sa.Column("photo_count", sa.Integer(), nullable=True),
        sa.Column("room_diversity", sa.Integer(), nullable=True),
        sa.Column("override_rate", sa.Float(), nullable=True),
        sa.Column("health_score_at_delivery", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE listing_outcomes ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON listing_outcomes "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    op.create_table(
        "performance_insights",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_perf_insights_tenant_type", "performance_insights", ["tenant_id", "insight_type"])
    op.execute("ALTER TABLE performance_insights ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON performance_insights "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON performance_insights")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON listing_outcomes")
    op.drop_table("performance_insights")
    op.drop_table("listing_outcomes")
