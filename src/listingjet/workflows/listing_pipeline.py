import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from listingjet.activities.pipeline import (
        run_brand,
        run_chapters,
        run_content,
        run_coverage,
        run_distribution,
        run_floorplan,
        run_ingestion,
        run_learning,
        run_microsite_generator,
        run_mls_export,
        run_packaging,
        run_property_verification,
        run_social_content,
        run_social_cuts,
        run_video,
        run_virtual_staging,
        run_vision_tier1,
        run_vision_tier2,
    )
    from listingjet.agents.base import AgentContext


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
    ListingJet listing processing pipeline.

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
        addons = input.enabled_addons or []

        # Phase 1: Analysis pipeline
        await workflow.execute_activity(
            run_ingestion, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await asyncio.gather(
            workflow.execute_activity(
                run_vision_tier1, ctx,
                start_to_close_timeout=_DEFAULT_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            ),
            workflow.execute_activity(
                run_property_verification, ctx,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_DEFAULT_RETRY,
            ),
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

        # Virtual staging (addon-gated): stage empty rooms before packaging
        if "virtual_staging" in addons:
            try:
                await workflow.execute_activity(
                    run_virtual_staging, ctx,
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=_DEFAULT_RETRY,
                )
            except Exception as exc:
                workflow.logger.warning("virtual_staging_failed listing=%s error=%s", input.listing_id, exc)

        await workflow.execute_activity(
            run_floorplan, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        packaging_result = await workflow.execute_activity(
            run_packaging, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Start video generation in parallel with human review
        # For credit users, only run if video add-on is enabled
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

        # Skip review wait if auto-approved by packaging agent
        auto_approved = (
            isinstance(packaging_result, dict)
            and packaging_result.get("auto_approved") is True
        )
        if not auto_approved:
            # Wait for human review (listing is now AWAITING_REVIEW)
            await workflow.wait_condition(lambda: self._review_completed)

        # Collect video result (may already be done) — don't block pipeline on failure
        if video_task:
            try:
                await video_task
            except Exception as exc:
                workflow.logger.warning("video_task_failed listing=%s error=%s", input.listing_id, exc)

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
        results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
        brand_result = results[0]
        if isinstance(brand_result, BaseException):
            workflow.logger.warning("brand_failed listing=%s error=%s", input.listing_id, brand_result)
            brand_result = {}
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
        from listingjet.activities.pipeline import MLSExportParams
        await workflow.execute_activity(
            run_mls_export, MLSExportParams(ctx, content_result, flyer_key),
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 4: Distribution (marks DELIVERED)
        await workflow.execute_activity(
            run_distribution, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 5: Auto-generate property microsite (non-blocking)
        try:
            await workflow.execute_activity(
                run_microsite_generator, ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_DEFAULT_RETRY,
            )
        except Exception as exc:
            workflow.logger.warning("microsite_failed listing=%s error=%s", input.listing_id, exc)

        # Step 6: Learn from human overrides for this listing
        await workflow.execute_activity(
            run_learning, ctx,
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
