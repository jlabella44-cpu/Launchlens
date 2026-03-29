PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "max_listings_per_month": 100,  # No monthly cap — pay per listing via credits
        "max_assets_per_listing": 25,
        "tier2_vision": False,
        "social_content": False,
        "asset_hosting_days": 30,       # 30-day expiry for free tier
        "watermark": "launchlens",      # LaunchLens watermark
        "queue_priority": "standard",
    },
    "starter": {
        "max_listings_per_month": 100,
        "max_assets_per_listing": 25,
        "tier2_vision": True,
        "social_content": False,
        "asset_hosting_days": 0,        # Permanent
        "watermark": "custom",          # Agent's branding
        "queue_priority": "priority",
    },
    "pro": {
        "max_listings_per_month": 100,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
        "social_content": True,
        "asset_hosting_days": 0,
        "watermark": "none",            # White-label
        "queue_priority": "top",
    },
    "enterprise": {
        "max_listings_per_month": 500,
        "max_assets_per_listing": 100,
        "tier2_vision": True,
        "social_content": True,
        "asset_hosting_days": 0,
        "watermark": "none",
        "queue_priority": "top",
    },
}


def get_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


def check_listing_quota(plan: str, current_count: int) -> bool:
    return current_count < get_limits(plan)["max_listings_per_month"]


def check_asset_quota(plan: str, existing_count: int, adding_count: int) -> bool:
    return (existing_count + adding_count) <= get_limits(plan)["max_assets_per_listing"]
