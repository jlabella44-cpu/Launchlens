import pytest

import listingjet.services.weight_manager as wm_module
from listingjet.services.weight_manager import MIN_TRAIN_SAMPLES, WeightManager


@pytest.fixture(autouse=True)
def _reset_xgb_model():
    wm_module._xgb_model = None
    yield
    wm_module._xgb_model = None

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


# ---- XGBoost Phase 2 tests ----


def _make_events(n: int, outcome: str = "approval") -> list[dict]:
    return [
        {
            "features": {"quality_score": 70, "commercial_score": 60, "hero_candidate": False, "room_weight": 1.0},
            "outcome": outcome,
        }
        for _ in range(n)
    ]


def test_train_model_skipped_below_min_samples():
    events = _make_events(MIN_TRAIN_SAMPLES - 1)
    result = WeightManager.train_model(events)
    assert result is False
    assert wm_module._xgb_model is None


def test_train_model_succeeds_with_sufficient_samples():
    positives = _make_events(MIN_TRAIN_SAMPLES // 2, "approval")
    negatives = _make_events(MIN_TRAIN_SAMPLES // 2, "rejection")
    result = WeightManager.train_model(positives + negatives)
    assert result is True
    assert wm_module._xgb_model is not None


def test_score_uses_rule_based_when_no_model():
    wm = WeightManager()
    features = {"quality_score": 80, "commercial_score": 60, "hero_candidate": False, "room_weight": 1.0}
    assert wm_module._xgb_model is None
    rule_score = WeightManager._rule_based_score(features)
    assert wm.score(features) == pytest.approx(rule_score)


def test_score_uses_xgb_when_model_trained():
    positives = _make_events(MIN_TRAIN_SAMPLES // 2, "approval")
    negatives = _make_events(MIN_TRAIN_SAMPLES // 2, "rejection")
    WeightManager.train_model(positives + negatives)
    assert wm_module._xgb_model is not None

    wm = WeightManager()
    score = wm.score({"quality_score": 90, "commercial_score": 85, "hero_candidate": True, "room_weight": 1.2})
    assert 0.0 <= score <= 1.0


def test_train_model_ignores_unlabeled_events():
    # Mix of labeled and unlabeled — only labeled count toward the threshold
    labeled = _make_events(MIN_TRAIN_SAMPLES // 2, "approval") + _make_events(MIN_TRAIN_SAMPLES // 2, "rejection")
    unlabeled = [{"features": {}, "outcome": None}] * 100
    result = WeightManager.train_model(labeled + unlabeled)
    assert result is True


def test_to_feature_vector_defaults():
    fv = WeightManager._to_feature_vector({})
    assert fv == [0.5, 0.5, 0.0, 1.0]


def test_to_feature_vector_hero():
    fv = WeightManager._to_feature_vector({"quality_score": 100, "commercial_score": 0, "hero_candidate": True, "room_weight": 1.5})
    assert fv == [1.0, 0.0, 1.0, 1.5]
