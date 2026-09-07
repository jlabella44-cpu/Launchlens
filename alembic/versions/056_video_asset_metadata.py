"""video_assets.metadata column + ai_generated -> tour rename

Revision ID: 056_video_asset_metadata
Revises: 055_vision_result_analysis
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "056_video_asset_metadata"
down_revision = "055_vision_result_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_assets", sa.Column("metadata", postgresql.JSONB(), nullable=True))
    # Two-tier video (Task 1+) renames the "ai_generated" video_type to "tour";
    # this data migration keeps existing rows consistent with the new naming.
    # Intentionally not reversed in downgrade() — the rename is a one-way
    # cleanup, not tied to the column's existence.
    op.execute("UPDATE video_assets SET video_type='tour' WHERE video_type='ai_generated'")


def downgrade() -> None:
    op.drop_column("video_assets", "metadata")
