"""Centralized credit tier, service cost, and bundle configuration.

Pricing v3: Weighted credit system where each service costs a proportional
number of credits based on its actual expense. Credits have a tier-locked
dollar value that decreases (= better deal) at higher tiers.
"""

# ---------------------------------------------------------------------------
# Service credit costs (weighted by computational expense)
# ---------------------------------------------------------------------------

SERVICE_CREDIT_COSTS: dict[str, int] = {
    "base_listing": 12,
    "ai_video_tour": 20,
    "virtual_staging": 15,
    "3d_floorplan": 8,
    "image_editing": 6,
    "cma_report": 5,
    "photo_compliance": 3,
    "social_media_cuts": 3,
    "microsite": 2,
    "social_content_pack": 2,
}

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

TIER_DEFAULTS: dict[str, dict] = {
    "free": {
        "included_credits": 0,
        "rollover_cap": 0,
        "per_listing_credit_cost": 12,
        "per_credit_dollar_value": 0.50,
        "monthly_price_cents": 0,
    },
    "lite": {
        "included_credits": 25,
        "rollover_cap": 15,
        "per_listing_credit_cost": 12,
        "per_credit_dollar_value": 0.45,
        "monthly_price_cents": 1900,
    },
    "active_agent": {
        "included_credits": 75,
        "rollover_cap": 50,
        "per_listing_credit_cost": 12,
        "per_credit_dollar_value": 0.40,
        "monthly_price_cents": 4900,
    },
    "team": {
        "included_credits": 250,
        "rollover_cap": 150,
        "per_listing_credit_cost": 12,
        "per_credit_dollar_value": 0.35,
        "monthly_price_cents": 9900,
    },
}

# Maps tier names to internal plan names (for backward compat)
TIER_TO_PLAN: dict[str, str] = {
    "free": "free",
    "lite": "lite",
    "active_agent": "active_agent",
    "team": "team",
}

# Legacy plan name mapping (old -> new)
LEGACY_PLAN_MAP: dict[str, str] = {
    "starter": "free",
    "pro": "active_agent",
    "enterprise": "team",
}

# Per-credit dollar value by tier (what 1 credit is "worth")
TIER_CREDIT_VALUES: dict[str, float] = {
    tier: cfg["per_credit_dollar_value"] for tier, cfg in TIER_DEFAULTS.items()
}

# Daily token limits for the AI help agent (input + output tokens)
HELP_AGENT_TOKEN_LIMITS: dict[str, int] = {
    "free": 200_000,
    "lite": 500_000,
    "active_agent": 1_000_000,
    "team": 5_000_000,
}


def apply_plan_credits(tenant, plan: str) -> None:
    """Set a tenant's plan and credit tier fields from the plan name."""
    # Handle legacy plan names
    resolved = LEGACY_PLAN_MAP.get(plan, plan)
    tier = TIER_DEFAULTS.get(resolved)
    if not tier:
        resolved = "free"
        tier = TIER_DEFAULTS["free"]

    tenant.plan = resolved
    tenant.plan_tier = resolved
    tenant.included_credits = tier["included_credits"]
    tenant.rollover_cap = tier["rollover_cap"]
    tenant.per_listing_credit_cost = tier["per_listing_credit_cost"]


# ---------------------------------------------------------------------------
# Credit bundles — tier-locked pricing
# ---------------------------------------------------------------------------

CREDIT_BUNDLES: dict[str, list[dict]] = {
    "free": [
        {"size": 25, "price_cents": 1199, "per_credit_cents": 48},
        {"size": 50, "price_cents": 2299, "per_credit_cents": 46},
        {"size": 100, "price_cents": 4299, "per_credit_cents": 43},
        {"size": 250, "price_cents": 9999, "per_credit_cents": 40},
    ],
    "lite": [
        {"size": 25, "price_cents": 1099, "per_credit_cents": 44},
        {"size": 50, "price_cents": 2099, "per_credit_cents": 42},
        {"size": 100, "price_cents": 3899, "per_credit_cents": 39},
        {"size": 250, "price_cents": 8999, "per_credit_cents": 36},
    ],
    "active_agent": [
        {"size": 25, "price_cents": 949, "per_credit_cents": 38},
        {"size": 50, "price_cents": 1799, "per_credit_cents": 36},
        {"size": 100, "price_cents": 3399, "per_credit_cents": 34},
        {"size": 250, "price_cents": 7749, "per_credit_cents": 31},
    ],
    "team": [
        {"size": 25, "price_cents": 849, "per_credit_cents": 34},
        {"size": 50, "price_cents": 1599, "per_credit_cents": 32},
        {"size": 100, "price_cents": 2999, "per_credit_cents": 30},
        {"size": 250, "price_cents": 6749, "per_credit_cents": 27},
    ],
}


def get_bundles_for_tier(tier: str) -> list[dict]:
    """Return credit bundles available for the given tier."""
    return CREDIT_BUNDLES.get(tier, CREDIT_BUNDLES["free"])
