from __future__ import annotations

import dataclasses
import logging

from temporalio import activity

from listingjet.agents.base import AgentContext

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LinkImportParams:
    listing_id: str
    tenant_id: str
    url: str
    platform: str
    import_job_id: str


@activity.defn
async def run_ingestion(context: AgentContext) -> dict:
    from listingjet.agents.ingestion import IngestionAgent
    return await IngestionAgent().instrumented_execute(context)


@activity.defn
async def run_vision_tier1(context: AgentContext) -> int:
    from listingjet.agents.vision import VisionAgent
    return await VisionAgent().run_tier1(context)


@activity.defn
async def run_vision_tier2(context: AgentContext) -> int:
    from listingjet.agents.vision import VisionAgent
    return await VisionAgent().run_tier2(context)


@activity.defn
async def run_coverage(context: AgentContext) -> dict:
    from listingjet.agents.coverage import CoverageAgent
    return await CoverageAgent().instrumented_execute(context)


@activity.defn
async def run_packaging(context: AgentContext) -> dict:
    from listingjet.agents.packaging import PackagingAgent
    return await PackagingAgent().instrumented_execute(context)


@activity.defn
async def run_content(context: AgentContext) -> dict:
    from listingjet.agents.content import ContentAgent
    return await ContentAgent().instrumented_execute(context)


@activity.defn
async def run_brand(context: AgentContext) -> dict:
    from listingjet.agents.brand import BrandAgent
    return await BrandAgent().instrumented_execute(context)


@activity.defn
async def run_distribution(context: AgentContext) -> dict:
    from listingjet.agents.distribution import DistributionAgent
    return await DistributionAgent().instrumented_execute(context)


@activity.defn
async def run_social_content(context: AgentContext) -> dict:
    from listingjet.agents.social_content import SocialContentAgent
    return await SocialContentAgent().instrumented_execute(context)


@dataclasses.dataclass
class MLSExportParams:
    context: AgentContext
    content_result: dict
    flyer_s3_key: str | None = None


@activity.defn
async def run_mls_export(params: MLSExportParams) -> dict:
    from listingjet.agents.mls_export import MLSExportAgent
    return await MLSExportAgent(content_result=params.content_result, flyer_s3_key=params.flyer_s3_key).instrumented_execute(params.context)


@activity.defn
async def run_floorplan(context: AgentContext) -> dict:
    from listingjet.agents.floorplan import FloorplanAgent
    return await FloorplanAgent().instrumented_execute(context)


@activity.defn
async def run_video(context: AgentContext) -> dict:
    from listingjet.agents.video import VideoAgent
    return await VideoAgent().instrumented_execute(context)


@activity.defn
async def run_chapters(context: AgentContext) -> dict:
    from listingjet.agents.chapter import ChapterAgent
    return await ChapterAgent().instrumented_execute(context)


@activity.defn
async def run_social_cuts(context: AgentContext) -> dict:
    from listingjet.agents.social_cuts import SocialCutAgent
    return await SocialCutAgent().instrumented_execute(context)


@activity.defn
async def run_photo_compliance(context: AgentContext) -> dict:
    from listingjet.agents.photo_compliance import PhotoComplianceAgent
    return await PhotoComplianceAgent().instrumented_execute(context)


@activity.defn
async def run_property_verification(context: AgentContext) -> dict:
    from listingjet.agents.property_verification import PropertyVerificationAgent
    return await PropertyVerificationAgent().instrumented_execute(context)


@activity.defn
async def run_learning(context: AgentContext) -> dict:
    from listingjet.agents.learning import LearningAgent
    return await LearningAgent().instrumented_execute(context)


@activity.defn
async def run_link_import(params: LinkImportParams) -> dict:
    """Download photos from a third-party link and create Asset records."""

    from listingjet.database import AsyncSessionLocal
    from listingjet.models.asset import Asset
    from listingjet.models.import_job import ImportJob
    from listingjet.services.events import emit_event
    from listingjet.services.link_import import import_from_link
    from listingjet.services.storage import StorageService

    storage = StorageService()

    async with AsyncSessionLocal() as db:
        # Mark job as running
        job = await db.get(ImportJob, params.import_job_id)
        if job:
            job.status = "running"
            await db.commit()

        try:
            # Track progress via closure
            def _on_progress(completed: int, total: int) -> None:
                # Note: sync callback — we update the DB in bulk after import
                pass

            imported = await import_from_link(
                url=params.url,
                platform=params.platform,
                listing_id=params.listing_id,
                storage=storage,
                on_progress=_on_progress,
            )

            # Create Asset records for each imported file
            for item in imported:
                asset = Asset(
                    tenant_id=params.tenant_id,
                    listing_id=params.listing_id,
                    file_path=item["file_path"],
                    file_hash=item["file_hash"],
                    state="uploaded",
                )
                db.add(asset)

            # Update job status
            if job:
                job.status = "completed"
                job.total_files = len(imported)
                job.completed_files = len(imported)

            await emit_event(
                session=db,
                event_type="import.completed",
                payload={
                    "import_job_id": params.import_job_id,
                    "platform": params.platform,
                    "files_imported": len(imported),
                },
                tenant_id=params.tenant_id,
                listing_id=params.listing_id,
            )
            await db.commit()

            return {
                "import_job_id": params.import_job_id,
                "files_imported": len(imported),
                "status": "completed",
            }

        except Exception as exc:
            logger.exception(
                "Link import failed for job %s", params.import_job_id,
            )
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                await db.commit()
            return {
                "import_job_id": params.import_job_id,
                "files_imported": 0,
                "status": "failed",
                "error": str(exc)[:500],
            }


@activity.defn
async def run_virtual_staging(context: AgentContext) -> dict:
    from listingjet.agents.virtual_staging import VirtualStagingAgent
    return await VirtualStagingAgent().instrumented_execute(context)


@activity.defn
async def run_cma_report(context: AgentContext) -> dict:
    from listingjet.agents.cma_report import CMAReportAgent
    return await CMAReportAgent().instrumented_execute(context)


@activity.defn
async def run_microsite_generator(context: AgentContext) -> dict:
    from listingjet.agents.microsite_generator import MicrositeGeneratorAgent
    return await MicrositeGeneratorAgent().instrumented_execute(context)


# Collect all activities for worker registration
ALL_ACTIVITIES = [
    run_ingestion, run_vision_tier1, run_vision_tier2,
    run_coverage, run_floorplan, run_packaging, run_content, run_brand,
    run_social_content, run_photo_compliance, run_mls_export, run_distribution,
    run_video, run_chapters, run_social_cuts, run_learning,
    run_link_import, run_property_verification,
    run_virtual_staging, run_cma_report, run_microsite_generator,
]
