"""Centralized credit tier and bundle configuration."""

TIER_DEFAULTS = {
    "lite": {"included_credits": 0, "rollover_cap": 5, "per_listing_credit_cost": 1},
    "active_agent": {"included_credits": 1, "rollover_cap": 3, "per_listing_credit_cost": 1},
    "team": {"included_credits": 5, "rollover_cap": 10, "per_listing_credit_cost": 1},
}

TIER_TO_PLAN = {
    "lite": "starter",
    "active_agent": "pro",
    "team": "enterprise",
}

# (included_credits_per_month, rollover_cap)
TIER_CREDITS: dict[str, tuple[int, int]] = {
    "starter": (5, 0),
    "pro": (50, 25),
    "enterprise": (500, 100),
}

# Daily token limits for the AI help agent (input + output tokens)
HELP_AGENT_TOKEN_LIMITS: dict[str, int] = {
    "starter": 200_000,
    "pro": 1_000_000,
    "enterprise": 5_000_000,
}

def apply_plan_credits(tenant, plan: str) -> None:
    """Set a tenant's plan and credit tier fields from the plan name."""
    tenant.plan = plan
    included, cap = TIER_CREDITS.get(plan, (0, 0))
    tenant.included_credits = included
    tenant.rollover_cap = cap


CREDIT_BUNDLES = [
    {"size": 5, "price_cents": 9500, "per_credit_cents": 1900},
    {"size": 10, "price_cents": 14000, "per_credit_cents": 1400},
    {"size": 25, "price_cents": 30000, "per_credit_cents": 1200},
    {"size": 50, "price_cents": 50000, "per_credit_cents": 1000},
]
