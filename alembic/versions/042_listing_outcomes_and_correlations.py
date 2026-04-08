"""Add listing_outcomes and photo_outcome_correlations tables for Phase 5 Performance Intelligence.

Revision ID: 042_perf_intelligence
Revises: 041_health_score
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "042_perf_intelligence"
down_revision = "041_health_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_outcomes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("list_price", sa.Float(), nullable=True),
        sa.Column("sale_price", sa.Float(), nullable=True),
        sa.Column("price_ratio", sa.Float(), nullable=True),
        sa.Column("days_on_market", sa.Integer(), nullable=True),
        sa.Column("days_to_contract", sa.Integer(), nullable=True),
        sa.Column("price_changes", sa.Integer(), server_default="0"),
        sa.Column("total_photos_mls", sa.Integer(), nullable=True),
        sa.Column("hero_room_label", sa.String(100), nullable=True),
        sa.Column("avg_photo_score", sa.Float(), nullable=True),
        sa.Column("outcome_grade", sa.String(1), nullable=True),
        sa.Column("idx_source", sa.String(100), nullable=True),
        sa.Column("raw_idx_data", postgresql.JSONB(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_listing_outcomes_listing_id", "listing_outcomes", ["listing_id"])
    op.create_index("ix_listing_outcomes_tenant_id", "listing_outcomes", ["tenant_id"])
    op.create_index("ix_listing_outcomes_status", "listing_outcomes", ["status"])

    op.create_table(
        "photo_outcome_correlations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("dimension_value", sa.String(100), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_dom", sa.Float(), nullable=True),
        sa.Column("avg_price_ratio", sa.Float(), nullable=True),
        sa.Column("avg_outcome_grade", sa.Float(), nullable=True),
        sa.Column("outcome_boost", sa.Float(), server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_poc_tenant_id", "photo_outcome_correlations", ["tenant_id"])
    op.create_unique_constraint(
        "uq_poc_tenant_dim_val",
        "photo_outcome_correlations",
        ["tenant_id", "dimension", "dimension_value"],
    )


def downgrade() -> None:
    op.drop_table("photo_outcome_correlations")
    op.drop_table("listing_outcomes")
