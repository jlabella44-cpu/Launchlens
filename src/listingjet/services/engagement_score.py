"""Engagement prediction score — thin wrapper around HealthScoreService.calculate_media_score.

The original heuristic has been moved to health_score.calculate_media_score().
This function is kept for backward compatibility with callers that pass
in-memory VisionResult lists (no async DB session available).
"""

# Required shots — kept in sync with health_score.py
REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}


def predict_engagement(vision_results: list, package_selections: list | None = None) -> int:
    """Return 0-100 engagement prediction score from vision data.

    This is the synchronous in-memory version. For the full async DB-backed
    media score, use ``health_score.calculate_media_score()``.
    """
    if not vision_results:
        return 50

    avg_quality = sum(vr.quality_score or 50 for vr in vision_results) / len(vision_results)
    avg_commercial = sum(vr.commercial_score or 50 for vr in vision_results) / len(vision_results)

    # Hero strength
    hero_results = [vr for vr in vision_results if getattr(vr, "hero_candidate", False)]
    hero_strength = max((vr.commercial_score or 0 for vr in hero_results), default=0) if hero_results else 0

    # Coverage
    covered = {
        getattr(vr, "room_label", None)
        for vr in vision_results
        if getattr(vr, "room_label", None)
    }
    coverage_pct = len(covered & REQUIRED_SHOTS) / len(REQUIRED_SHOTS) * 100

    # Same weights as health_score.calculate_media_score
    score = avg_quality * 0.40 + avg_commercial * 0.30 + hero_strength * 0.15 + coverage_pct * 0.15

    return min(100, max(0, int(score)))
