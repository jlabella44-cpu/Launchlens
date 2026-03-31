"""add missing indexes for asset.listing_id and event.listing_id

Revision ID: 020
Revises: 019
Create Date: 2026-03-31

"""
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_assets_listing_id", "assets", ["listing_id"])
    op.create_index("ix_events_listing_id_created_at", "events", ["listing_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_events_listing_id_created_at", table_name="events")
    op.drop_index("ix_assets_listing_id", table_name="assets")
