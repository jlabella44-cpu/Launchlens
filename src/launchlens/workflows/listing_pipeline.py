import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from launchlens.activities.pipeline import (
        run_brand,
        run_chapters,
        run_content,
        run_coverage,
        run_distribution,
        run_floorplan,
        run_ingestion,
        run_mls_export,
        run_packaging,
        run_social_content,
        run_social_cuts,
        run_video,
        run_vision_tier1,
        run_vision_tier2,
    )
    from launchlens.agents.base import AgentContext


@dataclass
class ListingPipelineInput:
    listing_id: str
    tenant_id: str
    plan: str = "starter"
    billing_model: str = "legacy"
    enabled_addons: list[str] | None = None


_DEFAULT_RETRY = RetryPolicy(maximum_attempts=3)
_DEFAULT_TIMEOUT = timedelta(minutes=10)
_VISION_TIER2_TIMEOUT = timedelta(minutes=20)


@workflow.defn
class ListingPipeline:
    """
    LaunchLens listing processing pipeline.

    +---------------------------------------------------------------+
    |  Ingestion -> Vision T1 -> Vision T2 -> Coverage -> Packaging |
    |                                                               |
    |              [wait for human_review_completed]                 |
    |                                                               |
    |  Content -> [Brand + Social (plan-gated)] -> MLS Export       |
    |          -> Distribution                                      |
    +---------------------------------------------------------------+
    """

    def __init__(self) -> None:
        self._shadow_approved = False
        self._review_completed = False

    @workflow.run
    async def run(self, input: ListingPipelineInput) -> str:
        ctx = AgentContext(listing_id=input.listing_id, tenant_id=input.tenant_id)

        # Phase 1: Analysis pipeline
        await workflow.execute_activity(
            run_ingestion, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier1, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier2, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_coverage, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_floorplan, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_packaging, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Start video generation in parallel with human review
        # For credit users, only run if video add-on is enabled
        addons = input.enabled_addons or []
        run_video_step = True
        if input.billing_model == "credit" and "ai_video_tour" not in addons:
            run_video_step = False

        video_task = None
        if run_video_step:
            video_task = workflow.execute_activity(
                run_video, ctx,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_DEFAULT_RETRY,
            )

        # Wait for human review (listing is now AWAITING_REVIEW)
        await workflow.wait_condition(lambda: self._review_completed)

        # Collect video result (may already be done) — don't block pipeline on failure
        if video_task:
            try:
                await video_task
            except Exception:
                pass  # Video is optional; pipeline continues without it

        # Phase 2: Post-approval pipeline
        # Step 1: Content (dual-tone)
        content_result = await workflow.execute_activity(
            run_content, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 2: Brand + Social in parallel (social is plan-gated)
        parallel_tasks = [
            workflow.execute_activity(
                run_brand, ctx,
                start_to_close_timeout=_DEFAULT_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            )
        ]
        # Social content: plan-gated for legacy, addon-gated for credit users
        run_social = (
            (input.billing_model == "credit" and "social_content_pack" in addons)
            or (input.billing_model != "credit" and input.plan in ("pro", "enterprise"))
        )
        if run_social:
            parallel_tasks.append(
                workflow.execute_activity(
                    run_social_content, ctx,
                    start_to_close_timeout=_DEFAULT_TIMEOUT,
                    retry_policy=_DEFAULT_RETRY,
                )
            )
        results = await asyncio.gather(*parallel_tasks)
        brand_result = results[0]
        flyer_key = brand_result.get("flyer_s3_key") if isinstance(brand_result, dict) else None

        # Video post-processing (chapters + social cuts)
        await workflow.execute_activity(
            run_chapters, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_social_cuts, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 3: MLS Export (builds both bundles)
        await workflow.execute_activity(
            run_mls_export, ctx, content_result, flyer_key,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 4: Distribution (marks DELIVERED)
        await workflow.execute_activity(
            run_distribution, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        return f"pipeline_complete:{input.listing_id}"

    @workflow.signal
    async def shadow_review_approved(self) -> None:
        self._shadow_approved = True

    @workflow.signal
    async def human_review_completed(self) -> None:
        self._review_completed = True
