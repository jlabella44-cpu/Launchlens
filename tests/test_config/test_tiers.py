from listingjet.config.tiers import SERVICE_CREDIT_COSTS, TIER_DEFAULTS, BUNDLE_PRICING


def test_base_listing_cost_is_15():
    assert SERVICE_CREDIT_COSTS["base_listing"] == 15


def test_removed_addons_not_in_costs():
    """Social content, social cuts, photo compliance, microsite are now in base."""
    for removed in ("social_content_pack", "social_media_cuts", "photo_compliance", "microsite", "image_editing", "cma_report"):
        assert removed not in SERVICE_CREDIT_COSTS, f"{removed} should be removed from SERVICE_CREDIT_COSTS"


def test_remaining_addons():
    assert SERVICE_CREDIT_COSTS["ai_video_tour"] == 20
    assert SERVICE_CREDIT_COSTS["virtual_staging"] == 15
    assert SERVICE_CREDIT_COSTS["3d_floorplan"] == 8


def test_bundle_pricing():
    assert BUNDLE_PRICING["all_addons_bundle"]["credit_cost"] == 30
    assert set(BUNDLE_PRICING["all_addons_bundle"]["includes"]) == {"ai_video_tour", "virtual_staging", "3d_floorplan"}


def test_tier_per_listing_cost_is_15():
    for tier_name, cfg in TIER_DEFAULTS.items():
        assert cfg["per_listing_credit_cost"] == 15, f"{tier_name} should have per_listing_credit_cost=15"
