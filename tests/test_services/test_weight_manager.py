import pytest
from launchlens.services.weight_manager import WeightManager

TENANT = "tenant-abc"
ROOM = "kitchen"


def test_new_tenant_uses_global_baseline():
    wm = WeightManager()
    # labeled_listing_count = 0 → pure global baseline (1.0 uniform)
    weight = wm.blend(TENANT, ROOM, labeled_listing_count=0, tenant_weight=1.5)
    assert weight == pytest.approx(1.0)


def test_10_listings_uses_pure_tenant_weight():
    wm = WeightManager()
    weight = wm.blend(TENANT, ROOM, labeled_listing_count=10, tenant_weight=1.5)
    assert weight == pytest.approx(1.5)


def test_5_listings_blends_50_50():
    wm = WeightManager()
    weight = wm.blend(TENANT, ROOM, labeled_listing_count=5, tenant_weight=1.5)
    # 0.5 * 1.5 + 0.5 * 1.0 = 1.25
    assert weight == pytest.approx(1.25)


def test_weight_clamped_at_upper_bound():
    wm = WeightManager()
    result = wm.apply_update(current_weight=1.98, action="approval")
    assert result <= 2.0


def test_weight_clamped_at_lower_bound():
    wm = WeightManager()
    result = wm.apply_update(current_weight=0.12, action="rejection")
    assert result >= 0.1


def test_regression_to_mean_pull():
    wm = WeightManager()
    # Weight above 1.0: update should include 0.01 pull toward 1.0
    result = wm.apply_update(current_weight=1.5, action="approval")
    # +0.05 approval, -0.01 pull = net +0.04
    assert result == pytest.approx(1.54)


def test_labeled_listing_count_not_override_event_count():
    # 10 events from 1 listing should NOT reach full tenant weight
    wm = WeightManager()
    weight = wm.blend(TENANT, ROOM, labeled_listing_count=1, tenant_weight=1.5)
    assert weight < 1.5  # still blended, not pure tenant
