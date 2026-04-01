"""add missing indexes for asset.listing_id, event.listing_id, address GIN, addon_purchases

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
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_listings_address_gin ON listings USING GIN(address)"
    )
    op.create_index("ix_addon_purchases_listing_id", "addon_purchases", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_addon_purchases_listing_id", table_name="addon_purchases")
    op.execute("DROP INDEX IF EXISTS idx_listings_address_gin")
    op.drop_index("ix_events_listing_id_created_at", table_name="events")
    op.drop_index("ix_assets_listing_id", table_name="assets")
