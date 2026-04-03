"""add performance indexes on listings, assets, events, property_data

Revision ID: 027
Revises: 026
Create Date: 2026-04-03

"""
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Listing: state, created_at, and composite for filtered list queries
    op.create_index("ix_listings_state", "listings", ["state"])
    op.create_index("ix_listings_created_at", "listings", ["created_at"])
    op.create_index(
        "ix_listings_tenant_state_created",
        "listings",
        ["tenant_id", "state", "created_at"],
    )

    # Asset: listing_id — already created in migration 020, skip if exists
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_assets_listing_id ON assets (listing_id)"
    )

    # Event: listing_id partial index (only non-null)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_listing_id ON events (listing_id) "
        "WHERE listing_id IS NOT NULL"
    )

    # PropertyData: composite for tenant-scoped address lookups
    op.create_index(
        "ix_property_data_tenant_address",
        "property_data",
        ["listing_id", "address_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_property_data_tenant_address", table_name="property_data")
    op.execute("DROP INDEX IF EXISTS ix_events_listing_id")
    op.drop_index("ix_assets_listing_id", table_name="assets")
    op.drop_index("ix_listings_tenant_state_created", table_name="listings")
    op.drop_index("ix_listings_created_at", table_name="listings")
    op.drop_index("ix_listings_state", table_name="listings")
