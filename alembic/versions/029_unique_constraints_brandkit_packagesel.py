"""add unique constraints to brand_kits and package_selections

Deduplicates existing rows before adding constraints to prevent failures.

Revision ID: 029
Revises: 028
Create Date: 2026-04-03

"""
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dedupe brand_kits: keep newest row per tenant_id
    op.execute("""
        DELETE FROM brand_kits
        WHERE id NOT IN (
            SELECT DISTINCT ON (tenant_id) id
            FROM brand_kits
            ORDER BY tenant_id, created_at DESC
        )
    """)
    op.create_unique_constraint("uq_brand_kits_tenant_id", "brand_kits", ["tenant_id"])

    # Dedupe package_selections: keep newest row per (listing_id, channel, position)
    op.execute("""
        DELETE FROM package_selections
        WHERE id NOT IN (
            SELECT DISTINCT ON (listing_id, channel, position) id
            FROM package_selections
            ORDER BY listing_id, channel, position, created_at DESC
        )
    """)
    op.create_unique_constraint(
        "uq_package_selections_listing_channel_position",
        "package_selections",
        ["listing_id", "channel", "position"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_package_selections_listing_channel_position", "package_selections")
    op.drop_constraint("uq_brand_kits_tenant_id", "brand_kits")
