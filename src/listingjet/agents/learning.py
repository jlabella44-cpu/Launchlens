from datetime import datetime, timezone

from sqlalchemy import select, update

from listingjet.database import AsyncSessionLocal
from listingjet.models.event import Event
from listingjet.models.learning_weight import LearningWeight
from listingjet.models.scoring_event import ScoringEvent
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
        async with self.session_scope(context) as (session, listing_id, tenant_id):
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

                    # Backfill outcome on ScoringEvent rows for XGBoost training data
                    asset_id = event.payload.get("asset_id")
                    now = datetime.now(timezone.utc)
                    if asset_id:
                        await session.execute(
                            update(ScoringEvent)
                            .where(
                                ScoringEvent.listing_id == listing_id,
                                ScoringEvent.asset_id == asset_id,
                                ScoringEvent.outcome.is_(None),
                            )
                            .values(outcome=action, outcome_at=now)
                        )

                    weights_updated += 1

                if weights_updated > 0:
                    await self.emit(session, context, "learning.completed", {"weights_updated": weights_updated})

                # Retrain XGBoost with all labeled events for this tenant
                if weights_updated > 0:
                    labeled_events = (await session.execute(
                        select(ScoringEvent).where(
                            ScoringEvent.tenant_id == tenant_id,
                            ScoringEvent.outcome.isnot(None),
                        )
                    )).scalars().all()
                    WeightManager.train_model([
                        {"features": ev.features, "outcome": ev.outcome}
                        for ev in labeled_events
                    ])

        return {"weights_updated": weights_updated}
