"""dollhouse scenes

Revision ID: 006
Revises: 005
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dollhouse_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("scene_json", postgresql.JSONB, nullable=False),
        sa.Column("room_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("floorplan_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute("ALTER TABLE dollhouse_scenes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON dollhouse_scenes
        USING (tenant_id = current_setting('app.current_tenant')::uuid)
    """)


def downgrade() -> None:
    op.drop_table("dollhouse_scenes")
