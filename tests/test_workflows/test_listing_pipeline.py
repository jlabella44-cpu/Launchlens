import pytest
from launchlens.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


def test_pipeline_input_dataclass():
    inp = ListingPipelineInput(listing_id="abc-123", tenant_id="tenant-xyz")
    assert inp.listing_id == "abc-123"
    assert inp.tenant_id == "tenant-xyz"


def test_pipeline_workflow_has_required_signals():
    # Verify signal handlers are defined on the class
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
