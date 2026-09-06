"""VirtualStagingAgent — stages empty room photos with AI-generated furniture.

Runs after Vision analysis (which provides room labels and the empty-room
flag) and only if the virtual_staging addon is active for the listing (the
pipeline gate — STEP_INDEX["virtual_staging"].gate == "addon:virtual_staging"
— enforces that before this agent ever runs). Only rooms Vision tier-1
marked as actually empty are staged; a furnished living room is left alone.

Each candidate photo is staged with the selected style, downloaded, and
re-uploaded to S3. The OpenAI call happens with no DB transaction open —
candidates are read in one session, staged assets are written in another.
"""
import logging
import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_virtual_staging_provider
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

# Rooms that benefit from staging (skip exteriors, bathrooms, etc.), mapped
# to agents.photo_analysis.RoomLabel values.
_STAGEABLE_ROOMS = {
    "living_room", "bedroom", "primary_bedroom", "dining_room", "office",
}

_DEFAULT_STYLE = "modern"
_MAX_CANDIDATES = 8


class VirtualStagingAgent(BaseAgent):
    agent_name = "virtual_staging"
    requires_ai_consent = True

    def __init__(self, staging_provider=None, storage_service=None, session_factory=None):
        self._provider = staging_provider or get_virtual_staging_provider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def _load_candidates(self, listing_id: uuid.UUID) -> list[tuple[Asset, VisionResult]]:
        """Interior photos Vision tier-1 marked as empty, in a stageable room."""
        async with self._session_factory() as session:
            results = (await session.execute(
                select(Asset, VisionResult)
                .join(VisionResult, VisionResult.asset_id == Asset.id)
                .where(
                    Asset.listing_id == listing_id,
                    VisionResult.tier == 1,
                )
            )).all()

        return [
            (asset, vr) for asset, vr in results
            if vr.is_empty_room is True and vr.room_label in _STAGEABLE_ROOMS
        ]

    async def execute(self, context: AgentContext) -> dict:
        listing_id, tenant_id = self.parse_ids(context)

        candidates = await self._load_candidates(listing_id)
        if not candidates:
            return {"skipped": True, "reason": "no_empty_rooms"}

        # Stage each candidate (max 8). No DB session is held open across
        # the provider call — each staged asset is written right after.
        staged_count = 0
        for asset, vr in candidates[:_MAX_CANDIDATES]:
            try:
                source_url = self._storage.presigned_url(asset.file_path)
                staged_bytes = await self._provider.stage_image(
                    image_url=source_url,
                    room_type=vr.room_label,
                    style=_DEFAULT_STYLE,
                )
            except Exception:
                logger.warning(
                    "virtual_staging.failed room=%s asset=%s",
                    vr.room_label, asset.id, exc_info=True,
                )
                continue

            s3_key = f"listings/{listing_id}/staged/{uuid.uuid4()}.png"
            self._storage.upload(s3_key, staged_bytes, content_type="image/png")

            async with self.session_scope(context) as (session, _lid, _tid):
                staged_asset = Asset(
                    tenant_id=tenant_id,
                    listing_id=listing_id,
                    file_path=s3_key,
                    file_hash=f"staged-{asset.file_hash[:16]}",
                    state="staged",
                )
                session.add(staged_asset)

            staged_count += 1
            logger.info(
                "virtual_staging.staged room=%s style=%s asset=%s",
                vr.room_label, _DEFAULT_STYLE, asset.id,
            )

        async with self.session_scope(context) as (session, _lid, _tid):
            await self.emit(session, context, "virtual_staging.completed", {
                "staged_count": staged_count,
                "candidates": len(candidates),
                "style": _DEFAULT_STYLE,
            })

        return {"staged_count": staged_count, "style": _DEFAULT_STYLE}
