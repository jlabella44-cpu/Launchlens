PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 25,
        "tier2_vision": False,
        "social_content": False,
    },
    "lite": {
        "max_listings_per_month": 25,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
        "social_content": False,
    },
    "active_agent": {
        "max_listings_per_month": 75,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
        "social_content": True,
    },
    "team": {
        "max_listings_per_month": 999999,
        "max_assets_per_listing": 100,
        "tier2_vision": True,
        "social_content": True,
    },
    # Legacy aliases
    "starter": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 25,
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
        "max_assets_per_listing": 50,
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


def get_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def check_listing_quota(plan: str, current_count: int) -> bool:
    return current_count < get_limits(plan)["max_listings_per_month"]


def check_asset_quota(plan: str, existing_count: int, adding_count: int) -> bool:
    return (existing_count + adding_count) <= get_limits(plan)["max_assets_per_listing"]
