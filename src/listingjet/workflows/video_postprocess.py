"""Video post-processing workflow for user-uploaded videos.

Appends a branded endcard and generates social cuts for uploaded videos.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from listingjet.activities.video_postprocess import run_append_endcard
    from listingjet.activities.pipeline import run_social_cuts
    from listingjet.agents.base import AgentContext


@dataclass
class VideoPostProcessInput:
    listing_id: str
    tenant_id: str
    video_asset_id: str


@workflow.defn
class VideoPostProcessWorkflow:
    @workflow.run
    async def run(self, input: VideoPostProcessInput) -> str:
        ctx = AgentContext(listing_id=input.listing_id, tenant_id=input.tenant_id)

        await workflow.execute_activity(
            run_append_endcard,
            args=[ctx, input.video_asset_id],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        await workflow.execute_activity(
            run_social_cuts,
            args=[ctx],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return "completed"
