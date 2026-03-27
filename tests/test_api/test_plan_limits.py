# tests/test_api/test_plan_limits.py
import pytest
from launchlens.services.plan_limits import PLAN_LIMITS, get_limits


def test_plan_limits_has_all_tiers():
    assert "starter" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS
    assert "enterprise" in PLAN_LIMITS


def test_starter_limits():
    limits = get_limits("starter")
    assert limits["max_listings_per_month"] == 5
    assert limits["max_assets_per_listing"] == 25
    assert limits["tier2_vision"] is False


def test_pro_limits():
    limits = get_limits("pro")
    assert limits["max_listings_per_month"] == 50
    assert limits["max_assets_per_listing"] == 50
    assert limits["tier2_vision"] is True


def test_enterprise_limits():
    limits = get_limits("enterprise")
    assert limits["max_listings_per_month"] == 500
    assert limits["tier2_vision"] is True


def test_unknown_plan_returns_starter():
    limits = get_limits("unknown")
    assert limits["max_listings_per_month"] == 5


def test_check_listing_quota_under_limit():
    from launchlens.services.plan_limits import check_listing_quota
    assert check_listing_quota("starter", current_count=3) is True


def test_check_listing_quota_at_limit():
    from launchlens.services.plan_limits import check_listing_quota
    assert check_listing_quota("starter", current_count=5) is False


def test_check_asset_quota_under_limit():
    from launchlens.services.plan_limits import check_asset_quota
    assert check_asset_quota("starter", existing_count=10, adding_count=10) is True


def test_check_asset_quota_over_limit():
    from launchlens.services.plan_limits import check_asset_quota
    assert check_asset_quota("starter", existing_count=10, adding_count=20) is False
