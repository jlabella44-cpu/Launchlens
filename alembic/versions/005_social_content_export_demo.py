"""social content, export bundles, demo listings

Revision ID: 005
Revises: 004
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("mls_bundle_path", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("marketing_bundle_path", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("listings", sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'exporting'")
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'demo'")

    op.create_table(
        "social_contents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, index=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", JSONB, nullable=True),
        sa.Column("cta", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("ALTER TABLE social_contents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON social_contents "
        "USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON social_contents")
    op.drop_table("social_contents")
    op.drop_column("listings", "demo_expires_at")
    op.drop_column("listings", "is_demo")
    op.drop_column("listings", "marketing_bundle_path")
    op.drop_column("listings", "mls_bundle_path")
