"""pricing v2 — addon price_by_tier, free tier support

Revision ID: 014
Revises: 013
Create Date: 2026-03-29
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tier-specific pricing to addon catalog
    op.add_column("addon_catalog", sa.Column("price_by_tier", JSONB(), server_default="{}", nullable=False))

    # Seed price_by_tier for existing addons (cents)
    op.execute("""
        UPDATE addon_catalog SET price_by_tier = '{"free": 3400, "lite": 2400, "active_agent": 2400, "team": 2400}'
        WHERE slug = 'ai_video_tour'
    """)
    op.execute("""
        UPDATE addon_catalog SET price_by_tier = '{"free": 2400, "lite": 1700, "active_agent": 1700, "team": 1700}'
        WHERE slug = '3d_floorplan'
    """)
    op.execute("""
        UPDATE addon_catalog SET price_by_tier = '{"free": 1700, "lite": 1200, "active_agent": 1200, "team": 1200}'
        WHERE slug = 'social_content_pack'
    """)


def downgrade() -> None:
    op.drop_column("addon_catalog", "price_by_tier")
