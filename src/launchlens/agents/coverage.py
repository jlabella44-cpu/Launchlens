from temporalio import activity
from .base import BaseAgent, AgentContext


class CoverageAgent(BaseAgent):
    agent_name = "coverage"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("CoverageAgent not yet implemented")


@activity.defn
async def run_coverage(listing_id: str, tenant_id: str) -> str:
    agent = CoverageAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
