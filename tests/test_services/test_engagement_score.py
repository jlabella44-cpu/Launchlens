from types import SimpleNamespace

from listingjet.services.engagement_score import predict_engagement


def _vr(quality=50, commercial=50, hero=False, room_label=None):
    return SimpleNamespace(
        quality_score=quality,
        commercial_score=commercial,
        hero_candidate=hero,
        room_label=room_label,
    )


def test_empty_results_returns_default():
    assert predict_engagement([]) == 50


def test_basic_score_calculation():
    results = [_vr(quality=80, commercial=60)]
    # 80*0.4 + 60*0.3 = 32 + 18 = 50
    assert predict_engagement(results) == 50


def test_hero_and_exterior_bonus():
    results = [_vr(quality=80, commercial=80, hero=True, room_label="exterior")]
    # 80*0.4 + 80*0.3 = 32+24 = 56, +10 hero, +10 exterior = 76
    assert predict_engagement(results) == 76


def test_coverage_bonus_five_rooms():
    rooms = ["kitchen", "bedroom", "bathroom", "living room", "exterior"]
    results = [_vr(quality=60, commercial=60, room_label=r) for r in rooms]
    # 60*0.4 + 60*0.3 = 24+18 = 42, +10 exterior, +10 coverage = 62
    assert predict_engagement(results) == 62
