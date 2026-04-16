PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 3,
        "tier2_vision": False,
        "social_content": False,
    },
    "lite": {
        "max_listings_per_month": 25,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 10,
        "tier2_vision": True,
        "social_content": False,
    },
    "active_agent": {
        "max_listings_per_month": 75,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 25,
        "tier2_vision": True,
        "social_content": True,
    },
    "team": {
        "max_listings_per_month": 999999,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 999999,
        "tier2_vision": True,
        "social_content": True,
    },
    # Legacy aliases
    "starter": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 3,
        "tier2_vision": False,
        "social_content": False,
        "health_breakdown": False,
        "health_trend": False,
        "health_alerts": False,
        "idx_feed": False,
        "idx_feed_max": 0,
        "health_custom_weights": False,
        "health_market_signal": False,
    },
    "pro": {
        "max_listings_per_month": 75,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 25,
        "tier2_vision": True,
        "social_content": True,
        "health_breakdown": True,
        "health_trend": True,
        "health_alerts": True,
        "idx_feed": True,
        "idx_feed_max": 1,
        "health_custom_weights": False,
        "health_market_signal": False,
    },
    "enterprise": {
        "max_listings_per_month": 999999,
        "max_assets_per_listing": 100,
        "max_listings_per_day_per_user": 999999,
        "tier2_vision": True,
        "social_content": True,
        "health_breakdown": True,
        "health_trend": True,
        "health_alerts": True,
        "idx_feed": True,
        "idx_feed_max": 999,
        "health_custom_weights": True,
        "health_market_signal": True,
    },
}


def get_limits(plan: str, overrides: dict | None = None) -> dict:
    base = dict(PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]))
    if overrides:
        base.update(overrides)
    return base


def check_listing_quota(plan: str, current_count: int) -> bool:
    return current_count < get_limits(plan)["max_listings_per_month"]


def check_asset_quota(plan: str, existing_count: int, adding_count: int) -> bool:
    return (existing_count + adding_count) <= get_limits(plan)["max_assets_per_listing"]


def check_user_daily_quota(limits: dict, today_count: int) -> bool:
    """Return True if the user is within the daily listing quota."""
    max_per_day = limits.get("max_listings_per_day_per_user", 10)
    return today_count < max_per_day
