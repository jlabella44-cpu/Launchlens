PLAN_LIMITS: dict[str, dict] = {
    "starter": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 25,
        "tier2_vision": False,
    },
    "pro": {
        "max_listings_per_month": 50,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
    },
    "enterprise": {
        "max_listings_per_month": 500,
        "max_assets_per_listing": 100,
        "tier2_vision": True,
    },
}


def get_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


def check_listing_quota(plan: str, current_count: int) -> bool:
    return current_count < get_limits(plan)["max_listings_per_month"]


def check_asset_quota(plan: str, existing_count: int, adding_count: int) -> bool:
    return (existing_count + adding_count) <= get_limits(plan)["max_assets_per_listing"]
