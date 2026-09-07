import pytest

from listingjet.pipeline.definition import (
    PIPELINE,
    STEP_INDEX,
    Step,
    topological_order,
    transitive_requires,
    validate_pipeline,
)


def test_pipeline_is_valid_and_has_expected_steps():
    validate_pipeline(PIPELINE)
    names = [s.name for s in PIPELINE]
    assert names[0] == "ingestion"
    assert "await_review" in names and "distribution" in names
    assert len(names) == len(set(names))
    assert STEP_INDEX["await_review"].gate == "review"
    assert STEP_INDEX["video"].gate == "video"
    assert STEP_INDEX["virtual_staging"].gate == "addon:virtual_staging"
    assert "chapters" not in STEP_INDEX
    assert STEP_INDEX["social_cuts"].requires == ("video", "await_review")
    assert len(names) == 21


def test_photo_analysis_is_the_only_photo_analysis_step():
    """The two vision tiers and the standalone compliance sweep collapsed into
    a single `photo_analysis` step hanging straight off ingestion."""
    assert [n for n in STEP_INDEX if "vision" in n or "complian" in n] == []
    assert STEP_INDEX["photo_analysis"].requires == ("ingestion",)
    assert STEP_INDEX["coverage"].requires == ("photo_analysis",)
    assert STEP_INDEX["distribution"].requires == ("mls_export", "social_content", "social_cuts")


def test_required_steps_are_not_optional():
    for name in ("ingestion", "photo_analysis", "coverage", "floorplan",
                 "packaging", "content", "mls_export", "distribution"):
        assert STEP_INDEX[name].optional is False, name


def test_post_approval_steps_depend_on_review_gate():
    order = topological_order(PIPELINE)
    assert order.index("await_review") < order.index("content")
    assert order.index("content") < order.index("mls_export")
    assert order.index("mls_export") < order.index("distribution")


def test_validate_rejects_unknown_dependency():
    bad = [Step("a"), Step("b", requires=("zzz",))]
    with pytest.raises(ValueError, match="zzz"):
        validate_pipeline(bad)


def test_validate_rejects_cycle():
    bad = [Step("a", requires=("b",)), Step("b", requires=("a",))]
    with pytest.raises(ValueError, match="cycle"):
        validate_pipeline(bad)


def test_transitive_requires_finds_indirect_dependency():
    assert "await_review" in transitive_requires("distribution")


def test_transitive_requires_excludes_unrelated_branch():
    assert "await_review" not in transitive_requires("packaging")
