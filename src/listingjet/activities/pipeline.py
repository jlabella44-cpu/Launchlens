from temporalio import activity

from listingjet.agents.base import AgentContext


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


@activity.defn
async def run_mls_export(context: AgentContext, content_result: dict, flyer_s3_key: str | None) -> dict:
    from listingjet.agents.mls_export import MLSExportAgent
    return await MLSExportAgent(content_result=content_result, flyer_s3_key=flyer_s3_key).instrumented_execute(context)


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
async def run_learning(context: AgentContext) -> dict:
    from listingjet.agents.learning import LearningAgent
    return await LearningAgent().instrumented_execute(context)


# Collect all activities for worker registration
ALL_ACTIVITIES = [
    run_ingestion, run_vision_tier1, run_vision_tier2,
    run_coverage, run_floorplan, run_packaging, run_content, run_brand,
    run_social_content, run_photo_compliance, run_mls_export, run_distribution,
    run_video, run_chapters, run_social_cuts, run_learning,
]
