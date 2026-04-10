import pytest

from listingjet.services.weight_manager import WeightManager

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


# ---- Phase 5: Outcome boost tests ----


def test_outcome_boost_no_effect_below_min_samples():
    wm = WeightManager()
    base = 0.8
    result = wm.apply_outcome_boost(base, outcome_boost=1.2, sample_count=2)
    assert result == base  # no effect, below minimum


def test_outcome_boost_positive_with_enough_samples():
    wm = WeightManager()
    result = wm.apply_outcome_boost(0.8, outcome_boost=1.2, sample_count=10)
    assert result > 0.8  # boost should increase score


def test_outcome_boost_negative_with_enough_samples():
    wm = WeightManager()
    result = wm.apply_outcome_boost(0.8, outcome_boost=0.8, sample_count=10)
    assert result < 0.8  # poor performance should decrease score


def test_outcome_boost_neutral():
    wm = WeightManager()
    result = wm.apply_outcome_boost(0.8, outcome_boost=1.0, sample_count=100)
    assert result == 0.8  # no change from neutral boost


def test_outcome_boost_clamped_to_bounds():
    wm = WeightManager()
    # Very high boost shouldn't exceed 1.0
    result = wm.apply_outcome_boost(0.95, outcome_boost=1.5, sample_count=100)
    assert result <= 1.0
    # Very low boost shouldn't go below 0.0
    result = wm.apply_outcome_boost(0.1, outcome_boost=0.5, sample_count=100)
    assert result >= 0.0


def test_score_with_outcome_boost():
    wm = WeightManager()
    base_score = wm.score({
        "quality_score": 80,
        "commercial_score": 70,
        "hero_candidate": False,
        "room_weight": 1.0,
    })
    boosted_score = wm.score({
        "quality_score": 80,
        "commercial_score": 70,
        "hero_candidate": False,
        "room_weight": 1.0,
        "outcome_boost": 1.2,
        "outcome_samples": 10,
    })
    assert boosted_score > base_score


def test_score_ignores_outcome_boost_below_min():
    wm = WeightManager()
    base_score = wm.score({
        "quality_score": 80,
        "commercial_score": 70,
        "hero_candidate": False,
        "room_weight": 1.0,
    })
    same_score = wm.score({
        "quality_score": 80,
        "commercial_score": 70,
        "hero_candidate": False,
        "room_weight": 1.0,
        "outcome_boost": 1.5,
        "outcome_samples": 1,  # below MIN_SAMPLES
    })
    assert same_score == base_score
