"""video assets

Revision ID: 007
Revises: 006
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("video_type", sa.String(50), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="processing"),
        sa.Column("chapters", postgresql.JSONB, nullable=True),
        sa.Column("social_cuts", postgresql.JSONB, nullable=True),
        sa.Column("branded_player_config", postgresql.JSONB, nullable=True),
        sa.Column("thumbnail_s3_key", sa.String(500), nullable=True),
        sa.Column("clip_count", sa.Integer, nullable=True),
    )

    op.execute("ALTER TABLE video_assets ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON video_assets
        USING (tenant_id = current_setting('app.current_tenant')::uuid)
    """)


def downgrade() -> None:
    op.drop_table("video_assets")
