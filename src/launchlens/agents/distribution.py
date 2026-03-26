from temporalio import activity
from .base import BaseAgent, AgentContext


class DistributionAgent(BaseAgent):
    agent_name = "distribution"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("DistributionAgent not yet implemented")


@activity.defn
async def run_distribution(listing_id: str, tenant_id: str) -> str:
    agent = DistributionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
