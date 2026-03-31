import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.event import Event
from listingjet.models.learning_weight import LearningWeight
from listingjet.services.events import emit_event
from listingjet.services.weight_manager import WeightManager

from .base import AgentContext, BaseAgent

OVERRIDE_ACTION_MAP = {
    "package.override.approved": "approval",
    "package.override.rejected": "rejection",
    "package.override.swap_to": "swap_to",
    "package.override.swap_from": "swap_from",
}


class LearningAgent(BaseAgent):
    agent_name = "learning"

    def __init__(self, session_factory=None, weight_manager=None):
        self._session_factory = session_factory or AsyncSessionLocal
        self._wm = weight_manager or WeightManager()

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        tenant_id = uuid.UUID(context.tenant_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                result = await session.execute(
                    select(Event).where(
                        Event.listing_id == listing_id,
                        Event.event_type.in_(list(OVERRIDE_ACTION_MAP.keys())),
                    )
                )
                events = result.scalars().all()

                weights_updated = 0
                for event in events:
                    room_label = event.payload.get("room_label")
                    if not room_label:
                        continue

                    action = OVERRIDE_ACTION_MAP[event.event_type]

                    existing = (await session.execute(
                        select(LearningWeight).where(
                            LearningWeight.tenant_id == tenant_id,
                            LearningWeight.room_label == room_label,
                        )
                    )).scalar_one_or_none()

                    current_weight = existing.weight if existing else 1.0
                    new_weight = self._wm.apply_update(current_weight, action)

                    if existing:
                        existing.weight = new_weight
                        existing.labeled_listing_count += 1
                    else:
                        session.add(LearningWeight(
                            tenant_id=tenant_id,
                            room_label=room_label,
                            weight=new_weight,
                            labeled_listing_count=1,
                        ))

                    weights_updated += 1

                if weights_updated > 0:
                    await emit_event(
                        session=session,
                        event_type="learning.completed",
                        payload={"weights_updated": weights_updated},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return {"weights_updated": weights_updated}
