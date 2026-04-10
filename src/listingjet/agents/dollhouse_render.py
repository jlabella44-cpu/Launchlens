"""DollhouseRenderAgent — bakes a DollhouseScene v2 JSON into a PNG.

Uses an image-to-image model (OpenAI gpt-image-1.5 by default) to transform
the listing's floorplan plus a handful of room reference photos into a
photorealistic isometric 3D dollhouse render. Stores the resulting PNG in S3
and writes the key back into scene_json["render_key"] so the API can presign
it on the way out.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing
from listingjet.providers.openai_dollhouse import (
    DOLLHOUSE_PROMPT,
    DollhouseRenderError,
    OpenAIDollhouseProvider,
)
from listingjet.services.storage import get_storage

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

_MAX_ROOM_PHOTOS = 4  # gpt-image-1.5 gives high-fidelity to first 5 images (1 floorplan + 4 rooms)


class DollhouseRenderAgent(BaseAgent):
    agent_name = "dollhouse_render"

    def __init__(
        self,
        session_factory=None,
        storage=None,
        provider: OpenAIDollhouseProvider | None = None,
        render_fn=None,
    ):
        self._session_factory = session_factory or AsyncSessionLocal
        self._storage = storage
        self._provider = provider
        # render_fn lets tests substitute a pure function; signature is
        # (floorplan_url: str, room_photo_urls: list[str]) -> bytes.
        self._render_fn = render_fn

    def _get_storage(self):
        return self._storage or get_storage()

    def _get_provider(self) -> OpenAIDollhouseProvider:
        if self._provider is None:
            self._provider = OpenAIDollhouseProvider()
        return self._provider

    async def _collect_image_urls(
        self,
        session,
        scene: DollhouseScene,
        storage,
    ) -> tuple[str | None, list[str]]:
        """Return (floorplan_url, room_photo_urls) based on scene_json + Asset lookups."""
        scene_json = scene.scene_json or {}
        floors = scene_json.get("floors") or []

        floorplan_asset_id = None
        photo_asset_ids: list[uuid.UUID] = []

        for floor in floors:
            fa = floor.get("source_floorplan_asset_id")
            if fa and not floorplan_asset_id:
                try:
                    floorplan_asset_id = uuid.UUID(str(fa))
                except (ValueError, TypeError):
                    pass
            for room in floor.get("rooms", []):
                photo_id = room.get("best_photo_asset_id")
                if photo_id:
                    try:
                        pid = uuid.UUID(str(photo_id))
                    except (ValueError, TypeError):
                        continue
                    if pid not in photo_asset_ids:
                        photo_asset_ids.append(pid)

        # Fall back to the scene's own floorplan_asset_id column if scene_json
        # was written by an older run.
        if not floorplan_asset_id and scene.floorplan_asset_id:
            floorplan_asset_id = scene.floorplan_asset_id

        if not floorplan_asset_id:
            return None, []

        ids_to_fetch = [floorplan_asset_id] + photo_asset_ids[:_MAX_ROOM_PHOTOS]
        assets = (
            await session.execute(
                select(Asset).where(Asset.id.in_(ids_to_fetch))
            )
        ).scalars().all()
        asset_by_id = {a.id: a for a in assets}

        floorplan_asset = asset_by_id.get(floorplan_asset_id)
        if not floorplan_asset:
            return None, []

        floorplan_url = storage.presigned_url(floorplan_asset.file_path)
        room_urls: list[str] = []
        for pid in photo_asset_ids[:_MAX_ROOM_PHOTOS]:
            asset = asset_by_id.get(pid)
            if asset:
                room_urls.append(storage.presigned_url(asset.file_path))

        return floorplan_url, room_urls

    async def execute(self, context: AgentContext) -> dict:
        render_key: str | None = None
        async with self.session_scope(context) as (session, listing_id, _tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            scene = (
                await session.execute(
                    select(DollhouseScene)
                    .where(DollhouseScene.listing_id == listing_id)
                    .order_by(DollhouseScene.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if not scene:
                return {
                    "skipped": True,
                    "reason": "No dollhouse scene to render",
                }

            storage = self._get_storage()
            floorplan_url, room_photo_urls = await self._collect_image_urls(
                session, scene, storage
            )
            if not floorplan_url:
                return {
                    "skipped": True,
                    "reason": "No floorplan asset to send to the render provider",
                }

            try:
                if self._render_fn is not None:
                    png_bytes = await _maybe_await(
                        self._render_fn(floorplan_url, room_photo_urls)
                    )
                else:
                    provider = self._get_provider()
                    png_bytes = await provider.generate(
                        floorplan_url=floorplan_url,
                        room_photo_urls=room_photo_urls,
                        prompt=DOLLHOUSE_PROMPT,
                    )
            except DollhouseRenderError as exc:
                logger.warning(
                    "dollhouse render provider failed listing=%s: %s",
                    listing_id, exc,
                )
                return {"skipped": True, "reason": f"Provider error: {exc}"}
            except Exception as exc:
                logger.exception(
                    "dollhouse render crashed listing=%s", listing_id
                )
                return {"skipped": True, "reason": f"Render failed: {exc}"}

            if not png_bytes:
                return {"skipped": True, "reason": "Render returned empty bytes"}

            render_key = f"listings/{listing_id}/dollhouse.png"
            storage.upload(key=render_key, data=png_bytes, content_type="image/png")

            new_scene_json = dict(scene.scene_json or {})
            new_scene_json["render_key"] = render_key
            scene.scene_json = new_scene_json

            await self.emit(
                session,
                context,
                "dollhouse.rendered",
                {
                    "listing_id": str(listing_id),
                    "render_key": render_key,
                    "byte_size": len(png_bytes),
                    "input_image_count": 1 + len(room_photo_urls),
                },
            )

        return {"render_key": render_key}


async def _maybe_await(value):
    """Allow render_fn to be either sync or async."""
    if hasattr(value, "__await__"):
        return await value
    return value
