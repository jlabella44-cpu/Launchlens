"""pricing v3 — weighted credit system, dual-pool balances, updated service costs

Revision ID: 037
Revises: 036
Create Date: 2026-04-06
"""
import sqlalchemy as sa

from alembic import op

revision = "037_pricing_v3"
down_revision = "036_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add granted_balance and purchased_balance to credit_accounts
    op.add_column("credit_accounts", sa.Column("granted_balance", sa.Integer(), server_default="0", nullable=False))
    op.add_column("credit_accounts", sa.Column("purchased_balance", sa.Integer(), server_default="0", nullable=False))

    # Migrate existing balance: treat all existing credits as granted
    op.execute("UPDATE credit_accounts SET granted_balance = balance, purchased_balance = 0")

    # 2. Multiply existing balances by 12 to align with new per_listing_credit_cost=12
    #    (old: 1 credit = 1 listing; new: 12 credits = 1 listing)
    op.execute("UPDATE credit_accounts SET balance = balance * 12, granted_balance = granted_balance * 12")

    # 3. Update per_listing_credit_cost on all tenants
    op.execute("UPDATE tenants SET per_listing_credit_cost = 12")

    # 4. Update rollover caps on credit_accounts (based on tenant plan)
    op.execute("""
        UPDATE credit_accounts ca SET rollover_cap = CASE
            WHEN t.plan IN ('free', 'starter') THEN 0
            WHEN t.plan = 'lite' THEN 15
            WHEN t.plan IN ('active_agent', 'pro') THEN 50
            WHEN t.plan IN ('team', 'enterprise') THEN 150
            ELSE 0
        END
        FROM tenants t WHERE ca.tenant_id = t.id
    """)

    # 5. Update addon_catalog credit costs for existing entries
    op.execute("UPDATE addon_catalog SET credit_cost = 15 WHERE slug = 'virtual_staging'")
    op.execute("UPDATE addon_catalog SET credit_cost = 6 WHERE slug = 'image_editing'")
    op.execute("UPDATE addon_catalog SET credit_cost = 5 WHERE slug = 'cma_report'")

    # 6. Upsert new addon catalog entries for weighted services
    op.execute("""
        INSERT INTO addon_catalog (id, slug, name, credit_cost, is_active, metadata, price_by_tier)
        VALUES
            (gen_random_uuid(), 'ai_video_tour', 'AI Video Tour', 20, true, '{}', '{}'),
            (gen_random_uuid(), 'social_media_cuts', 'Social Media Cuts', 3, true, '{}', '{}'),
            (gen_random_uuid(), '3d_floorplan', '3D Floorplan', 8, true, '{}', '{}'),
            (gen_random_uuid(), 'microsite', 'Microsite', 2, true, '{}', '{}'),
            (gen_random_uuid(), 'photo_compliance', 'Photo Compliance', 3, true, '{}', '{}')
        ON CONFLICT (slug) DO UPDATE SET
            credit_cost = EXCLUDED.credit_cost,
            name = EXCLUDED.name
    """)

    # Update social_content_pack credit cost
    op.execute("UPDATE addon_catalog SET credit_cost = 2 WHERE slug = 'social_content_pack'")

    # 7. Clear price_by_tier (everything is credits now, no more dollar pricing per tier)
    op.execute("UPDATE addon_catalog SET price_by_tier = '{}'")


def downgrade() -> None:
    # Reverse credit multiplication
    op.execute("UPDATE credit_accounts SET balance = balance / 12, granted_balance = granted_balance / 12")
    op.execute("UPDATE tenants SET per_listing_credit_cost = 1")

    # Restore old addon costs
    op.execute("UPDATE addon_catalog SET credit_cost = 15 WHERE slug = 'virtual_staging'")
    op.execute("UPDATE addon_catalog SET credit_cost = 5 WHERE slug = 'image_editing'")
    op.execute("UPDATE addon_catalog SET credit_cost = 10 WHERE slug = 'cma_report'")

    # Remove new addon entries
    op.execute("DELETE FROM addon_catalog WHERE slug IN ('ai_video_tour', 'social_media_cuts', '3d_floorplan', 'microsite', 'photo_compliance')")

    op.drop_column("credit_accounts", "purchased_balance")
    op.drop_column("credit_accounts", "granted_balance")
