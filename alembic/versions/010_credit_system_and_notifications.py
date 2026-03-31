"""credit system, addons, and notification preferences

Revision ID: 010
Revises: 009
Create Date: 2026-03-28
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Credit accounts ---
    op.create_table(
        "credit_accounts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("included_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rollover_cap", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("per_listing_credit_cost", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tier", sa.String(50), nullable=False, server_default="lite"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_accounts_tenant_id", "credit_accounts", ["tenant_id"])

    # --- Credit transactions ---
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_transactions_tenant_id", "credit_transactions", ["tenant_id"])
    op.create_index("ix_credit_transactions_ref", "credit_transactions", ["reference_type", "reference_id"])

    # --- Addon catalog ---
    op.create_table(
        "addon_catalog",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credit_cost", sa.Integer(), nullable=False),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("metadata", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Addon purchases ---
    op.create_table(
        "addon_purchases",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("addon_id", sa.UUID(), nullable=False),
        sa.Column("credit_transaction_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("listing_id", "addon_id"),
    )
    op.create_index("ix_addon_purchases_tenant_id", "addon_purchases", ["tenant_id"])

    # --- Notification preferences ---
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("email_on_complete", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("email_on_failure", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("email_on_review_ready", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Tenant billing columns ---
    op.add_column("tenants", sa.Column("plan_tier", sa.String(50), server_default="lite"))
    op.add_column("tenants", sa.Column("billing_model", sa.String(50), server_default="credit"))
    op.add_column("tenants", sa.Column("included_credits", sa.Integer(), server_default="0"))
    op.add_column("tenants", sa.Column("per_listing_credit_cost", sa.Integer(), server_default="1"))

    # --- Listing credit cost ---
    op.add_column("listings", sa.Column("credit_cost", sa.Integer(), nullable=True))

    # --- Seed addon catalog ---
    op.execute("""
        INSERT INTO addon_catalog (id, slug, name, credit_cost, metadata) VALUES
        (gen_random_uuid(), 'ai_video_tour', 'AI Video Tour', 1, '{"description": "AI-generated property tour video"}'),
        (gen_random_uuid(), '3d_floorplan', '3D Floorplan', 1, '{"description": "Interactive 3D floorplan visualization"}'),
        (gen_random_uuid(), 'social_content_pack', 'Social Content Pack', 1, '{"description": "Platform-specific social media captions and hashtags"}')
    """)

    # --- Set existing tenants to legacy billing ---
    op.execute("UPDATE tenants SET billing_model = 'legacy', plan_tier = plan")


def downgrade() -> None:
    op.drop_column("listings", "credit_cost")
    op.drop_column("tenants", "per_listing_credit_cost")
    op.drop_column("tenants", "included_credits")
    op.drop_column("tenants", "billing_model")
    op.drop_column("tenants", "plan_tier")
    op.drop_table("notification_preferences")
    op.drop_table("addon_purchases")
    op.drop_table("addon_catalog")
    op.drop_table("credit_transactions")
    op.drop_table("credit_accounts")
