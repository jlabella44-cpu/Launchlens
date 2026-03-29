"""Engagement prediction score — heuristic estimate of listing photo performance.

Uses existing VisionResult quality/commercial scores, hero candidate status,
coverage completeness, and global baseline weights to predict a 0-100
engagement score displayed on the listing dashboard.
"""


def predict_engagement(vision_results: list, package_selections: list | None = None) -> int:
    """Return 0-100 engagement prediction score from vision data.

    Scoring breakdown:
    - 40%: average quality score across all photos
    - 30%: average commercial score (features that attract buyers)
    - 10%: hero candidate bonus (strong lead photo)
    - 10%: exterior/curb appeal bonus
    - 10%: coverage bonus (5+ distinct room types)
    """
    if not vision_results:
        return 50  # Default when no vision data

    avg_quality = sum(vr.quality_score or 50 for vr in vision_results) / len(vision_results)
    avg_commercial = sum(vr.commercial_score or 50 for vr in vision_results) / len(vision_results)

    score = avg_quality * 0.4 + avg_commercial * 0.3

    # Hero candidate bonus
    has_hero = any(getattr(vr, "hero_candidate", False) for vr in vision_results)
    if has_hero:
        score += 10

    # Exterior/curb appeal bonus
    exterior_labels = {"exterior", "drone", "facade", "building exterior"}
    has_exterior = any(
        getattr(vr, "room_label", "") in exterior_labels for vr in vision_results
    )
    if has_exterior:
        score += 10

    # Coverage bonus (diverse room types)
    room_types = {
        getattr(vr, "room_label", None) for vr in vision_results
        if getattr(vr, "room_label", None)
    }
    if len(room_types) >= 5:
        score += 10
    elif len(room_types) >= 3:
        score += 5

    return min(100, max(0, int(score)))
