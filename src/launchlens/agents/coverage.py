import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}


class CoverageAgent(BaseAgent):
    agent_name = "coverage"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                # Load Tier 1 VisionResults for this listing
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                        VisionResult.room_label.isnot(None),
                    )
                )
                vision_results = result.scalars().all()

                covered = {vr.room_label for vr in vision_results}
                missing = sorted(REQUIRED_SHOTS - covered)

                if missing:
                    await emit_event(
                        session=session,
                        event_type="coverage.gap",
                        payload={"missing_shots": missing},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return {"missing_shots": missing, "covered_shots": sorted(covered & REQUIRED_SHOTS)}


@activity.defn
async def run_coverage(listing_id: str, tenant_id: str) -> dict:
    agent = CoverageAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
