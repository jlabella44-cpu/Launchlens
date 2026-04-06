"""Add DRAFT listing state and bundle support.

Revision ID: 039_add_draft_state_and_bundle
Revises: 038_pricing_v3_weighted_credits
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

revision = "039_add_draft_state_and_bundle"
down_revision = "038_pricing_v3_weighted_credits"
branch_labels = None
depends_on = None


def upgrade():
    # Add DRAFT to listing state enum
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'draft' BEFORE 'new'")

    # Add bundle_id to addon_purchases for tracking bundle activations
    op.add_column(
        "addon_purchases",
        sa.Column("bundle_id", sa.String(50), nullable=True),
    )

    # Seed the "all_addons_bundle" into addon_catalog
    op.execute("""
        INSERT INTO addon_catalog (id, slug, name, credit_cost, is_active, metadata)
        VALUES (
            gen_random_uuid(),
            'all_addons_bundle',
            'Premium Bundle (Video + Staging + Floorplan)',
            30,
            true,
            '{"includes": ["ai_video_tour", "virtual_staging", "3d_floorplan"], "savings": 13}'::jsonb
        )
        ON CONFLICT (slug) DO NOTHING
    """)

    # Deactivate addons that are now included in base
    op.execute("""
        UPDATE addon_catalog SET is_active = false
        WHERE slug IN ('social_content_pack', 'social_media_cuts', 'photo_compliance', 'microsite', 'image_editing', 'cma_report')
    """)


def downgrade():
    # Re-activate deactivated addons
    op.execute("""
        UPDATE addon_catalog SET is_active = true
        WHERE slug IN ('social_content_pack', 'social_media_cuts', 'photo_compliance', 'microsite', 'image_editing', 'cma_report')
    """)

    # Remove bundle from catalog
    op.execute("DELETE FROM addon_catalog WHERE slug = 'all_addons_bundle'")

    # Remove bundle_id column
    op.drop_column("addon_purchases", "bundle_id")

    # Note: Cannot remove enum value in PostgreSQL, leave DRAFT in place
