"""VirtualStagingAgent — stages empty room photos with AI-generated furniture.

Runs after Vision analysis (which provides room labels) and only if the
virtual_staging addon is active for the listing. Each interior photo is
staged with the selected style, downloaded, and re-uploaded to S3.
"""
import logging
import uuid

import httpx
from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.asset import Asset
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_virtual_staging_provider
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

# Rooms that benefit from staging (skip exteriors, bathrooms, etc.)
_STAGEABLE_ROOMS = {
    "living_room", "bedroom", "master_bedroom", "dining_room",
    "family_room", "office", "den", "guest_room",
}

_DEFAULT_STYLE = "modern"


class VirtualStagingAgent(BaseAgent):
    agent_name = "virtual_staging"
    requires_ai_consent = True

    def __init__(self, staging_provider=None, storage_service=None, session_factory=None):
        self._provider = staging_provider or get_virtual_staging_provider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            # Check if virtual_staging addon is active for this listing
            addon = (await session.execute(
                select(AddonPurchase).where(
                    AddonPurchase.listing_id == listing_id,
                    AddonPurchase.addon_slug == "virtual_staging",
                    AddonPurchase.status == "active",
                )
            )).scalar_one_or_none()

            if not addon:
                return {"skipped": True, "reason": "addon_not_active"}

            # Get interior photos with room labels from Vision T1
            results = (await session.execute(
                select(Asset, VisionResult)
                .join(VisionResult, VisionResult.asset_id == Asset.id)
                .where(
                    Asset.listing_id == listing_id,
                    VisionResult.tier == 1,
                )
            )).all()

            candidates = [
                (asset, vr) for asset, vr in results
                if vr.room_label in _STAGEABLE_ROOMS
            ]

            if not candidates:
                return {"skipped": True, "reason": "no_stageable_rooms"}

            # Stage each candidate (max 8)
            staged_count = 0
            for asset, vr in candidates[:8]:
                try:
                    # Get presigned URL for the source image
                    source_url = self._storage.presigned_url(asset.file_path)

                    # Call staging provider
                    staged_url = await self._provider.stage_image(
                        image_url=source_url,
                        room_type=vr.room_label,
                        style=_DEFAULT_STYLE,
                    )

                    # Download staged image and upload to S3
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.get(staged_url)
                        resp.raise_for_status()
                        staged_bytes = resp.content

                    s3_key = f"listings/{listing_id}/staged/{uuid.uuid4()}.jpg"
                    self._storage.upload(s3_key, staged_bytes, content_type="image/jpeg")

                    # Create a new asset for the staged version
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
                except Exception:
                    logger.warning(
                        "virtual_staging.failed room=%s asset=%s",
                        vr.room_label, asset.id, exc_info=True,
                    )

            await self.emit(session, context, "virtual_staging.completed", {
                "staged_count": staged_count,
                "candidates": len(candidates),
                "style": _DEFAULT_STYLE,
            })

        return {"staged_count": staged_count, "style": _DEFAULT_STYLE}
