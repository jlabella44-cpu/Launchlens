# src/launchlens/agents/vision.py
import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.vision_result import VisionResult
from launchlens.models.listing import Listing, ListingState
from launchlens.providers import get_vision_provider
from launchlens.providers.base import VisionLabel
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

ROOM_LABEL_MAP = {
    "living room": "living_room",
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "dining room": "dining_room",
    "building exterior": "exterior",
    "facade": "exterior",
    "garage": "garage",
    "swimming pool": "pool",
    "backyard": "backyard",
    "office": "office",
}

COMMERCIAL_LABELS = {
    "natural light", "hardwood", "granite", "stainless steel",
    "open plan", "vaulted ceiling", "fireplace", "mountain view",
    "city view", "pool", "renovated",
}

TIER2_CANDIDATE_LIMIT = 20


def _labels_to_vision_result(asset_id: uuid.UUID, labels: list[VisionLabel]) -> VisionResult:
    """Map VisionLabel list → VisionResult row for Tier 1."""
    top_confidence = max((l.confidence for l in labels), default=0.0)
    quality_score = int(top_confidence * 100)

    room_label = None
    for label in labels:
        mapped = ROOM_LABEL_MAP.get(label.name.lower())
        if mapped:
            room_label = mapped
            break

    commercial_count = sum(1 for l in labels if l.name.lower() in COMMERCIAL_LABELS)
    commercial_score = min(100, commercial_count * 20)

    is_interior = room_label not in (None, "exterior", "garage", "pool", "backyard")
    hero_candidate = quality_score >= 70 and commercial_score >= 40

    return VisionResult(
        asset_id=asset_id,
        tier=1,
        room_label=room_label,
        is_interior=is_interior,
        quality_score=quality_score,
        commercial_score=commercial_score,
        hero_candidate=hero_candidate,
        raw_labels={"labels": [{"name": l.name, "confidence": l.confidence} for l in labels]},
        model_used="google-vision-v1",
    )


class VisionAgent(BaseAgent):
    agent_name = "vision"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def run_tier1(self, context: AgentContext) -> int:
        """Run Google Vision on all ingested assets. Returns count of results written."""
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                result = await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state == "ingested",
                    )
                )
                assets = result.scalars().all()

                count = 0
                for asset in assets:
                    labels = await self._vision_provider.analyze(image_url=asset.file_path)
                    vr = _labels_to_vision_result(asset.id, labels)
                    session.add(vr)
                    count += 1

                if count > 0:
                    await emit_event(
                        session=session,
                        event_type="vision.tier1.completed",
                        payload={"asset_count": count},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return count

    async def execute(self, context: AgentContext) -> dict:
        tier1_count = await self.run_tier1(context)
        tier2_count = await self.run_tier2(context)
        return {"tier1_count": tier1_count, "tier2_count": tier2_count}

    async def run_tier2(self, context: AgentContext) -> int:
        """GPT-4V re-ranking — implemented in Task 3."""
        return 0


@activity.defn
async def run_vision(listing_id: str, tenant_id: str) -> dict:
    agent = VisionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
