"""Add scoring_events table for XGBoost training data.

Revision ID: 037_scoring_events
Revises: 036_support_tickets
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "037_scoring_events"
down_revision = "036_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scoring_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("asset_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("room_label", sa.String(100)),
        sa.Column("features", postgresql.JSONB, nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("position", sa.Integer),
        sa.Column("outcome", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("outcome_at", sa.DateTime(timezone=True)),
    )
    # Index for training data export: find all labeled rows
    op.create_index(
        "ix_scoring_events_outcome_not_null",
        "scoring_events",
        ["tenant_id", "created_at"],
        postgresql_where=sa.text("outcome IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_scoring_events_outcome_not_null", table_name="scoring_events")
    op.drop_table("scoring_events")
