"""Add scheduled_posts table and extend social_accounts with OAuth fields.

Revision ID: 042_scheduled_posts
Revises: 041_health_score
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "042_scheduled_posts"
down_revision = "041_health_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- scheduled_posts table --
    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_event_id", sa.UUID(), nullable=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("media_s3_keys", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("platform_post_id", sa.String(255), nullable=True),
        sa.Column("platform_post_url", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scheduled_posts_status_scheduled", "scheduled_posts", ["status", "scheduled_at"])

    op.execute("ALTER TABLE scheduled_posts ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON scheduled_posts "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    # -- extend social_accounts --
    op.add_column("social_accounts", sa.Column("refresh_token_encrypted", sa.String(500), nullable=True))
    op.add_column("social_accounts", sa.Column("scopes", postgresql.JSONB(), nullable=True))
    op.add_column("social_accounts", sa.Column("page_id", sa.String(255), nullable=True))
    op.add_column("social_accounts", sa.Column("page_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("social_accounts", "page_name")
    op.drop_column("social_accounts", "page_id")
    op.drop_column("social_accounts", "scopes")
    op.drop_column("social_accounts", "refresh_token_encrypted")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON scheduled_posts")
    op.drop_table("scheduled_posts")
