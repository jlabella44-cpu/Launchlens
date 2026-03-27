from temporalio import activity
from launchlens.agents.base import AgentContext


@activity.defn
async def run_ingestion(context: AgentContext) -> dict:
    from launchlens.agents.ingestion import IngestionAgent
    return await IngestionAgent().execute(context)


@activity.defn
async def run_vision_tier1(context: AgentContext) -> int:
    from launchlens.agents.vision import VisionAgent
    return await VisionAgent().run_tier1(context)


@activity.defn
async def run_vision_tier2(context: AgentContext) -> int:
    from launchlens.agents.vision import VisionAgent
    return await VisionAgent().run_tier2(context)


@activity.defn
async def run_coverage(context: AgentContext) -> dict:
    from launchlens.agents.coverage import CoverageAgent
    return await CoverageAgent().execute(context)


@activity.defn
async def run_packaging(context: AgentContext) -> dict:
    from launchlens.agents.packaging import PackagingAgent
    return await PackagingAgent().execute(context)


@activity.defn
async def run_content(context: AgentContext) -> dict:
    from launchlens.agents.content import ContentAgent
    return await ContentAgent().execute(context)


@activity.defn
async def run_brand(context: AgentContext) -> dict:
    from launchlens.agents.brand import BrandAgent
    return await BrandAgent().execute(context)


@activity.defn
async def run_distribution(context: AgentContext) -> dict:
    from launchlens.agents.distribution import DistributionAgent
    return await DistributionAgent().execute(context)


# Collect all activities for worker registration
ALL_ACTIVITIES = [
    run_ingestion, run_vision_tier1, run_vision_tier2,
    run_coverage, run_packaging, run_content, run_brand, run_distribution,
]
