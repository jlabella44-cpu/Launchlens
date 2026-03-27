# tests/test_workflows/test_listing_pipeline.py
import pytest
from launchlens.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


def test_pipeline_input_dataclass():
    inp = ListingPipelineInput(listing_id="abc-123", tenant_id="tenant-xyz")
    assert inp.listing_id == "abc-123"
    assert inp.tenant_id == "tenant-xyz"


def test_pipeline_workflow_has_required_signals():
    assert hasattr(ListingPipeline, "shadow_review_approved")
    assert hasattr(ListingPipeline, "human_review_completed")


def test_pipeline_init_sets_flags():
    pipeline = ListingPipeline()
    assert pipeline._shadow_approved is False
    assert pipeline._review_completed is False


@pytest.mark.asyncio
async def test_shadow_review_signal_sets_flag():
    pipeline = ListingPipeline()
    await pipeline.shadow_review_approved()
    assert pipeline._shadow_approved is True


@pytest.mark.asyncio
async def test_human_review_signal_sets_flag():
    pipeline = ListingPipeline()
    await pipeline.human_review_completed()
    assert pipeline._review_completed is True


def test_pipeline_imports_activities():
    """Workflow module must reference all pipeline activities."""
    from launchlens.workflows import listing_pipeline
    source = open(listing_pipeline.__file__).read()
    expected_activities = [
        "run_ingestion", "run_vision_tier1", "run_vision_tier2",
        "run_coverage", "run_packaging", "run_content", "run_brand", "run_distribution",
    ]
    for act in expected_activities:
        assert act in source, f"Workflow does not reference activity: {act}"


def test_pipeline_has_retry_policy():
    """Workflow source should contain RetryPolicy configuration."""
    from launchlens.workflows import listing_pipeline
    source = open(listing_pipeline.__file__).read()
    assert "RetryPolicy" in source
    assert "start_to_close_timeout" in source
