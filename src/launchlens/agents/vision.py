from temporalio import activity
from .base import BaseAgent, AgentContext


class VisionAgent(BaseAgent):
    agent_name = "vision"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("VisionAgent not yet implemented")


@activity.defn
async def run_vision(listing_id: str, tenant_id: str) -> str:
    agent = VisionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
