"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenants ──────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("role", sa.Enum("admin", "operator", "agent", "viewer", name="userrole"), nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── listings ──────────────────────────────────────────────────────────
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("address", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "state",
            sa.Enum(
                "new", "uploading", "analyzing", "shadow_review", "awaiting_review",
                "in_review", "approved", "generating", "delivering", "delivered",
                "tracking", "pipeline_timeout", "failed",
                name="listingstate",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column("analysis_tier", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("lock_owner_id", postgresql.UUID(as_uuid=True)),
        sa.Column("lock_expires_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── assets ────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True)),        # nullable — Phase 2 API
        sa.Column("api_request_id", postgresql.UUID(as_uuid=True)),    # nullable
        sa.Column("file_path", sa.String, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),         # SHA-256
        sa.Column("required_for_mls", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("state", sa.String(50), nullable=False, server_default="uploaded"),
        sa.CheckConstraint(
            "listing_id IS NOT NULL OR api_request_id IS NOT NULL",
            name="asset_must_have_context",
        ),
    )

    # ── vision_results ────────────────────────────────────────────────────
    op.create_table(
        "vision_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("tier", sa.Integer, nullable=False),
        sa.Column("room_label", sa.String(100)),
        sa.Column("is_interior", sa.Boolean),
        sa.Column("quality_score", sa.Integer),
        sa.Column("commercial_score", sa.Integer),
        sa.Column("hero_candidate", sa.Boolean),
        sa.Column("hero_explanation", sa.String),
        sa.Column("raw_labels", postgresql.JSONB),
        sa.Column("model_used", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── package_selections ────────────────────────────────────────────────
    op.create_table(
        "package_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("position", sa.Integer),
        sa.Column("selected_by", sa.String(20), nullable=False, server_default="ai"),
        sa.Column("composite_score", sa.Float),
    )

    # ── events ────────────────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── outbox ────────────────────────────────────────────────────────────
    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("published", sa.Boolean, nullable=False, server_default="false", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── label_mappings ────────────────────────────────────────────────────
    op.create_table(
        "label_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("required_labels", postgresql.JSONB, nullable=False),
        sa.Column("optional_labels", postgresql.JSONB, nullable=False),
        sa.Column("room_type", sa.String(100), nullable=False, unique=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── performance_events ────────────────────────────────────────────────
    op.create_table(
        "performance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("signal_type", sa.String(100), nullable=False),
        sa.Column("value", sa.Float),
        sa.Column("source", sa.String(100)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── learning_weights ──────────────────────────────────────────────────
    op.create_table(
        "learning_weights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_label", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("labeled_listing_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "room_label", name="uq_learning_weights_tenant_room"),
    )

    # ── global_baseline_weights ───────────────────────────────────────────
    op.create_table(
        "global_baseline_weights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_label", sa.String(100), nullable=False, unique=True),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── brand_kits ────────────────────────────────────────────────────────
    op.create_table(
        "brand_kits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("logo_url", sa.String),
        sa.Column("primary_color", sa.String(7)),
        sa.Column("secondary_color", sa.String(7)),
        sa.Column("font_primary", sa.String),
        sa.Column("agent_name", sa.String),
        sa.Column("brokerage_name", sa.String),
        sa.Column("raw_config", postgresql.JSONB, nullable=False, server_default="{}"),
    )

    # ── compliance_events ─────────────────────────────────────────────────
    op.create_table(
        "compliance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── prompt_versions ───────────────────────────────────────────────────
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("prompt_text", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("eval_score", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── PostgreSQL RLS — tenant isolation ─────────────────────────────────
    # vision_results excluded: no direct tenant_id column (linked via asset_id)
    for table in ("listings", "assets", "package_selections", "events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)

    # ── Event store indexes ───────────────────────────────────────────────
    op.execute(
        "CREATE INDEX events_tenant_type_time ON events (tenant_id, event_type, created_at)"
    )
    op.execute("""
        CREATE INDEX events_human_overrides ON events (tenant_id, listing_id)
        WHERE event_type IN ('human.photo_swapped', 'human.photo_rejected', 'human.photo_approved')
    """)

    # ── Seed global_baseline_weights ──────────────────────────────────────
    room_types = [
        "exterior_front", "exterior_other", "entry", "living_room", "dining_room",
        "kitchen", "master_bedroom", "master_bathroom", "bedroom", "bathroom",
        "office", "basement", "garage", "outdoor", "aerial",
    ]
    for room in room_types:
        op.execute(f"""
            INSERT INTO global_baseline_weights (id, room_label, weight, updated_at)
            VALUES (gen_random_uuid(), '{room}', 1.0, NOW())
            ON CONFLICT (room_label) DO NOTHING
        """)


def downgrade() -> None:
    # Drop RLS policies first
    for table in ("listings", "assets", "package_selections", "events"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS events_tenant_type_time")
    op.execute("DROP INDEX IF EXISTS events_human_overrides")

    # Drop tables in reverse dependency order
    for table in (
        "prompt_versions", "compliance_events", "brand_kits", "global_baseline_weights",
        "learning_weights", "performance_events", "label_mappings", "outbox", "events",
        "package_selections", "vision_results", "assets", "listings", "users", "tenants",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS listingstate")
    op.execute("DROP TYPE IF EXISTS userrole")
