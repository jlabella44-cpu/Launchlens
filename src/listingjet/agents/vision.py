# src/listingjet/agents/vision.py
import logging
import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_vision_provider
from listingjet.providers.base import VisionLabel
from listingjet.services.metrics import record_cost
from listingjet.services.storage import get_storage

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

ROOM_LABEL_MAP = {
    # Interior rooms
    "living room": "living_room",
    "interior design": "living_room",
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "dining room": "dining_room",
    "garage": "garage",
    "office": "office",
    "laundry room": "basement",
    "basement": "basement",
    # Exterior / outdoor
    "building exterior": "exterior",
    "facade": "exterior",
    "house": "exterior",
    "home": "exterior",
    "residential area": "exterior",
    "property": "exterior",
    "real estate": "exterior",
    "swimming pool": "pool",
    "backyard": "backyard",
    "garden": "backyard",
    "patio": "backyard",
    "yard": "backyard",
    # Non-photo content — mapped so downstream agents can filter them out
    "floor plan": "floorplan",
    "floorplan": "floorplan",
    "blueprint": "blueprint",
    "diagram": "diagram",
    "map": "map",
    "site plan": "site_plan",
    "document": "document",
    "text": "document",
    "screenshot": "screenshot",
}

COMMERCIAL_LABELS = {
    "natural light", "hardwood", "granite", "stainless steel",
    "open plan", "vaulted ceiling", "fireplace", "mountain view",
    "city view", "pool", "renovated",
}

TIER2_CANDIDATE_LIMIT = 20


def _labels_to_vision_result(asset_id: uuid.UUID, labels: list[VisionLabel]) -> VisionResult:
    """Map VisionLabel list → VisionResult row for Tier 1."""
    top_confidence = max((lbl.confidence for lbl in labels), default=0.0)
    quality_score = int(top_confidence * 100)

    room_label = None
    for label in labels:
        mapped = ROOM_LABEL_MAP.get(label.name.lower())
        if mapped:
            room_label = mapped
            break

    commercial_count = sum(1 for lbl in labels if lbl.name.lower() in COMMERCIAL_LABELS)
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
        raw_labels={"labels": [{"name": lbl.name, "confidence": lbl.confidence} for lbl in labels]},
        model_used="google-vision-v1",
    )


class VisionAgent(BaseAgent):
    agent_name = "vision"

    def __init__(self, vision_provider=None, session_factory=None):
        self._vision_provider = vision_provider or get_vision_provider(agent=self.agent_name)
        self._session_factory = session_factory or AsyncSessionLocal

    async def run_tier1(self, context: AgentContext) -> int:
        """Run Google Vision on all ingested assets. Returns count of results written."""
        count = await self._run_tier1_inner(context)
        record_cost(self.agent_name, "google_vision", count)
        return count

    async def _run_tier1_inner(self, context) -> int:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                result = await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state == "ingested",
                    )
                )
                assets = result.scalars().all()

                storage = get_storage()
                count = 0
                for asset in assets:
                    image_url = self._resolve_image_url(asset, storage)
                    logger.info(
                        "Vision T1 [%d/%d] asset=%s proxy=%s",
                        count + 1, len(assets), asset.id,
                        "yes" if asset.proxy_path else "no",
                    )
                    labels = await self._vision_provider.analyze(image_url=image_url)
                    vr = _labels_to_vision_result(asset.id, labels)
                    session.add(vr)
                    count += 1
                    logger.info(
                        "Vision T1 completed asset=%s labels=%d",
                        asset.id, len(labels),
                    )

                if count > 0:
                    await self.emit(session, context, "vision.tier1.completed", {"asset_count": count})

        return count

    @staticmethod
    def _resolve_image_url(asset: Asset, storage) -> str:
        """Return a presigned URL for the proxy image if available, otherwise full-res."""
        key = asset.proxy_path or asset.file_path
        return storage.presigned_url(key)

    async def execute(self, context: AgentContext) -> dict:
        tier1_count = await self.run_tier1(context)
        tier2_count = await self.run_tier2(context)
        return {"tier1_count": tier1_count, "tier2_count": tier2_count}

    async def run_tier2(self, context: AgentContext) -> int:
        """Run GPT-4V on top hero candidates from Tier 1. Returns count of Tier 2 results."""
        count = await self._run_tier2_inner(context)
        record_cost(self.agent_name, "openai_gpt4v", count)
        return count

    async def _run_tier2_inner(self, context) -> int:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                        VisionResult.hero_candidate.is_(True),
                    )
                    .order_by(VisionResult.quality_score.desc())
                    .limit(TIER2_CANDIDATE_LIMIT)
                )
                candidates = result.scalars().all()

                if not candidates:
                    return 0

                storage = get_storage()
                count = 0
                for vr in candidates:
                    asset = await session.get(Asset, vr.asset_id)
                    image_url = self._resolve_image_url(asset, storage)
                    logger.info(
                        "Vision T2 [%d/%d] asset=%s proxy=%s",
                        count + 1, len(candidates), asset.id,
                        "yes" if asset.proxy_path else "no",
                    )
                    labels = await self._vision_provider.analyze(image_url=image_url)

                    quality_labels = [lbl for lbl in labels if lbl.category == "quality"]
                    shot_labels = [lbl for lbl in labels if lbl.category == "shot_type"]

                    quality_score = int(
                        (sum(lbl.confidence for lbl in quality_labels) / len(quality_labels) * 100)
                        if quality_labels else vr.quality_score
                    )
                    hero_explanation = quality_labels[0].name if quality_labels else None
                    room_label = shot_labels[0].name if shot_labels else vr.room_label

                    tier2 = VisionResult(
                        asset_id=vr.asset_id,
                        tier=2,
                        room_label=room_label,
                        is_interior=vr.is_interior,
                        quality_score=quality_score,
                        commercial_score=vr.commercial_score,
                        hero_candidate=True,
                        hero_explanation=hero_explanation,
                        raw_labels={"labels": [{"name": lbl.name, "confidence": lbl.confidence} for lbl in labels]},
                        model_used="gpt-4o",
                    )
                    session.add(tier2)
                    count += 1

                if count > 0:
                    await self.emit(session, context, "vision.tier2.completed", {"candidate_count": count})

        return count
