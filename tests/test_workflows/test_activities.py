# tests/test_workflows/test_activities.py


def test_all_activities_are_decorated():
    """All pipeline activity functions must have @activity.defn."""
    from launchlens.activities.pipeline import (
        run_brand,
        run_content,
        run_coverage,
        run_distribution,
        run_ingestion,
        run_packaging,
        run_vision_tier1,
        run_vision_tier2,
    )
    for fn in [
        run_ingestion, run_vision_tier1, run_vision_tier2,
        run_coverage, run_packaging, run_content, run_brand, run_distribution,
    ]:
        assert hasattr(fn, "__temporal_activity_definition"), f"{fn.__name__} missing @activity.defn"


def test_activity_names():
    """Activity names should match expected convention."""
    from launchlens.activities.pipeline import (
        run_brand,
        run_content,
        run_coverage,
        run_distribution,
        run_ingestion,
        run_packaging,
        run_vision_tier1,
        run_vision_tier2,
    )
    expected = [
        "run_ingestion", "run_vision_tier1", "run_vision_tier2",
        "run_coverage", "run_packaging", "run_content", "run_brand", "run_distribution",
    ]
    fns = [run_ingestion, run_vision_tier1, run_vision_tier2,
           run_coverage, run_packaging, run_content, run_brand, run_distribution]
    for fn, name in zip(fns, expected):
        assert fn.__temporal_activity_definition.name == name
