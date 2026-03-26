from temporalio import activity
from .base import BaseAgent, AgentContext


class LearningAgent(BaseAgent):
    agent_name = "learning"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("LearningAgent not yet implemented")


@activity.defn
async def run_learning(listing_id: str, tenant_id: str) -> str:
    agent = LearningAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
