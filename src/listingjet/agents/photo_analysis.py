"""PhotoAnalysisAgent — one Claude vision call per photo.

Replaces the old two-tier vision pass (Google Vision labels + a GPT-4o
re-scoring of hero candidates) *and* the separate GPT-4o compliance sweep
with a single structured call per image. Everything downstream still reads
`VisionResult` tier-1 rows, so the room/quality/hero columns keep their
meaning; the compliance verdict now rides along on the same row instead of
being recomputed on demand.

Unlike the agent it replaces, this one does not swallow failures: if more
than half the photos fail to analyse the step raises so the runner retries
instead of letting a half-blind pipeline run to delivery.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_claude
from listingjet.services.compliance import compliance_report
from listingjet.services.storage import get_storage

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

HERO_THRESHOLD = 70


class RoomLabel(str, Enum):
    exterior = "exterior"
    drone = "drone"
    entryway = "entryway"
    living_room = "living_room"
    kitchen = "kitchen"
    dining_room = "dining_room"
    bedroom = "bedroom"
    primary_bedroom = "primary_bedroom"
    bathroom = "bathroom"
    primary_bathroom = "primary_bathroom"
    office = "office"
    garage = "garage"
    basement = "basement"
    laundry = "laundry"
    backyard = "backyard"
    pool = "pool"
    patio = "patio"
    hallway = "hallway"
    closet = "closet"
    other = "other"
    floorplan = "floorplan"
    document = "document"
    screenshot = "screenshot"


class Compliance(BaseModel):
    people: bool
    signage: bool
    branding: bool
    text_overlay: bool


class PhotoAnalysis(BaseModel):
    room: RoomLabel
    is_interior: bool
    is_photo: bool
    quality: int = Field(ge=0, le=100)
    hero_score: int = Field(ge=0, le=100)
    features: list[str] = []
    is_empty_room: bool
    compliance: Compliance
    notes: str = ""


PROMPT = """\
You are analysing one photo from a residential real estate listing. Return the
structured analysis described by the schema, judging only what is visible.

- room: the best-fitting room or shot type.
- is_interior: true only for shots taken inside the home.
- is_photo: false for floorplans, blueprints, documents, screenshots, or any
  other non-photographic image; true for real photographs.
- quality: photographic quality 0-100 (exposure, focus, framing, lighting).
- hero_score: 0-100 for how well this image would work as the lead listing
  photo. Reserve 70+ for images genuinely good enough to lead with.
- features: a few short selling points visible in the shot (e.g. "hardwood
  floors", "granite counters"). Empty list if nothing stands out.
- is_empty_room: true only for an unfurnished interior room.
- compliance, each true only when clearly visible:
  people (any person or identifiable face), signage (for-sale, open-house or
  agent yard signs), branding (brokerage logos, watermarks, agent marks),
  text_overlay (text, captions or contact details added onto the image).
- notes: one short sentence explaining the hero_score.
"""


class PhotoAnalysisAgent(BaseAgent):
    agent_name = "photo_analysis"
    requires_ai_consent = True

    def __init__(
        self,
        claude=None,
        storage=None,
        session_factory=None,
        concurrency: int = 8,
        per_image_timeout_s: float = 30.0,
    ):
        self._claude = claude or get_claude(agent=self.agent_name)
        self._storage = storage
        self._session_factory = session_factory or AsyncSessionLocal
        self._concurrency = concurrency
        self._per_image_timeout_s = per_image_timeout_s

    # -- load ---------------------------------------------------------------

    async def _load_targets(self, listing_id: uuid.UUID) -> list[tuple[uuid.UUID, str]]:
        """(asset_id, storage key) for every ingested asset, oldest first."""
        async with self._session_factory() as session:
            rows = (await session.execute(
                select(Asset)
                .where(Asset.listing_id == listing_id, Asset.state == "ingested")
                .order_by(Asset.created_at, Asset.id)
            )).scalars().all()
            return [(a.id, a.proxy_path or a.file_path) for a in rows]

    # -- call ---------------------------------------------------------------

    async def _analyze_one(self, image_url: str) -> PhotoAnalysis:
        return await asyncio.wait_for(
            self._claude.analyze_images(
                [image_url],
                PROMPT,
                PhotoAnalysis,
                model=settings.claude_fast_model,
                agent=self.agent_name,
            ),
            timeout=self._per_image_timeout_s,
        )

    async def _analyze_all(
        self, targets: list[tuple[uuid.UUID, str]], storage
    ) -> list[tuple[uuid.UUID, PhotoAnalysis | None]]:
        semaphore = asyncio.Semaphore(self._concurrency)

        async def run(asset_id: uuid.UUID, key: str):
            async with semaphore:
                try:
                    return asset_id, await self._analyze_one(storage.presigned_url(key))
                except asyncio.TimeoutError:
                    logger.warning(
                        "photo_analysis timeout asset=%s after %ss",
                        asset_id, self._per_image_timeout_s,
                    )
                except Exception:
                    logger.exception("photo_analysis failed asset=%s", asset_id)
                return asset_id, None

        return list(await asyncio.gather(*(run(aid, key) for aid, key in targets)))

    # -- save ---------------------------------------------------------------

    @staticmethod
    def _to_row(asset_id: uuid.UUID, analysis: PhotoAnalysis) -> VisionResult:
        return VisionResult(
            asset_id=asset_id,
            tier=1,
            room_label=analysis.room.value,
            is_interior=analysis.is_interior,
            quality_score=analysis.quality,
            commercial_score=analysis.hero_score,
            hero_candidate=analysis.hero_score >= HERO_THRESHOLD,
            hero_explanation=analysis.notes,
            raw_labels=analysis.model_dump(mode="json"),
            model_used=settings.claude_fast_model,
            hero_score=analysis.hero_score,
            is_photo=analysis.is_photo,
            is_empty_room=analysis.is_empty_room,
            features=analysis.features,
            compliance=analysis.compliance.model_dump(),
        )

    async def execute(self, context: AgentContext) -> dict:
        listing_id, _tenant_id = self.parse_ids(context)

        targets = await self._load_targets(listing_id)
        if not targets:
            return {"analyzed": 0, "failed": 0, "flagged": 0}

        storage = self._storage or get_storage()
        results = await self._analyze_all(targets, storage)

        successes = [(aid, a) for aid, a in results if a is not None]
        failed = len(results) - len(successes)
        flagged = sum(
            1 for _, a in successes if any(a.compliance.model_dump().values())
        )
        counts = {"analyzed": len(successes), "failed": failed, "flagged": flagged}

        async with self.session_scope(context) as (session, lid, _tid):
            # One analysis per asset replaces whatever was there before,
            # including stale tier-2 rows from the old two-tier pass.
            await session.execute(
                delete(VisionResult).where(
                    VisionResult.asset_id.in_([aid for aid, _ in successes])
                )
            )
            session.add_all([self._to_row(aid, a) for aid, a in successes])
            await session.flush()

            if successes:
                # Kept for backwards compatibility: the SSE stream and the
                # legacy event-derived progress list still key off this name.
                await self.emit(session, context, "vision.tier1.completed",
                                {"asset_count": len(successes)})
            await self.emit(session, context, "photo_analysis.completed", counts)
            report = await compliance_report(session, lid)
            await self.emit(session, context, "photo_compliance.completed", report)

        if failed and (failed == len(results) or failed * 2 > len(results)):
            raise RuntimeError(
                f"photo_analysis: {failed} of {len(results)} photos failed"
            )

        return counts
