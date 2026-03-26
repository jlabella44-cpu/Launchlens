import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from launchlens.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


@pytest.mark.asyncio
async def test_pipeline_workflow_registers_without_error():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[ListingPipeline],
            activities=[],
        ):
            # Workflow is registered — basic smoke test
            assert True


@pytest.mark.asyncio
async def test_pipeline_run_returns_complete_string():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[ListingPipeline],
            activities=[],
        ) as worker:
            result = await env.client.execute_workflow(
                ListingPipeline.run,
                ListingPipelineInput(listing_id="test-123", tenant_id="tenant-abc"),
                id="test-pipeline",
                task_queue="test-queue",
            )
            assert result == "pipeline_complete:test-123"
