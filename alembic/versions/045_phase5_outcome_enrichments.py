"""Phase 5: Add outcome enrichments to listing_outcomes + photo_outcome_correlations table.

Revision ID: 045_phase5_enrichments
Revises: 044_force_rls
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "045_phase5_enrichments"
down_revision = "044_force_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Phase 5 enrichment columns to listing_outcomes (created in 042)
    op.add_column("listing_outcomes", sa.Column("sale_price", sa.Float(), nullable=True))
    op.add_column("listing_outcomes", sa.Column("price_ratio", sa.Float(), nullable=True))
    op.add_column("listing_outcomes", sa.Column("days_to_contract", sa.Integer(), nullable=True))
    op.add_column("listing_outcomes", sa.Column("hero_room_label", sa.String(100), nullable=True))
    op.add_column("listing_outcomes", sa.Column("outcome_grade", sa.String(1), nullable=True))
    op.add_column("listing_outcomes", sa.Column("idx_source", sa.String(100), nullable=True))
    op.add_column("listing_outcomes", sa.Column("raw_idx_data", postgresql.JSONB(), nullable=True))

    # Create photo_outcome_correlations table
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
    op.drop_column("listing_outcomes", "raw_idx_data")
    op.drop_column("listing_outcomes", "idx_source")
    op.drop_column("listing_outcomes", "outcome_grade")
    op.drop_column("listing_outcomes", "hero_room_label")
    op.drop_column("listing_outcomes", "days_to_contract")
    op.drop_column("listing_outcomes", "price_ratio")
    op.drop_column("listing_outcomes", "sale_price")
