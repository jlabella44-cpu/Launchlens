"""VideoAgent — generates AI property tour videos from listing photos via Kling.
Ported from Juke Marketing Engine with adaptations for LaunchLens pipeline.
"""

import asyncio
import os
import tempfile
import uuid

import httpx
from sqlalchemy import select

from launchlens.agents.video_prompts import (
    NEGATIVE_PROMPT,
    SLOT_ORDER,
    get_camera_control,
    get_prompt_for_room,
    get_transition,
)
from launchlens.config import settings
from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.models.video_asset import VideoAsset
from launchlens.models.vision_result import VisionResult
from launchlens.providers.kling import KlingProvider
from launchlens.services.events import emit_event
from launchlens.services.storage import StorageService
from launchlens.services.video_stitcher import VideoStitcher

from .base import AgentContext, BaseAgent


class VideoAgent(BaseAgent):
    agent_name = "video"

    def __init__(
        self,
        kling_provider=None,
        storage_service=None,
        video_stitcher=None,
        session_factory=None,
    ):
        self._kling = kling_provider or KlingProvider()
        self._storage = storage_service or StorageService()
        self._stitcher = video_stitcher or VideoStitcher()
        self._session_factory = session_factory or AsyncSessionLocal
        self._max_photos = settings.video_max_photos
        self._score_floor = settings.video_score_floor
        self._semaphore = asyncio.Semaphore(3)  # max 3 concurrent Kling calls

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                # Get package selections with asset + vision data
                selections = (await session.execute(
                    select(PackageSelection, Asset, VisionResult)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .outerjoin(VisionResult, (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1))
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )).all()

                if not selections:
                    return {"skipped": True, "reason": "No package selections"}

                # Select photos for video using slot priority
                selected = self._select_photos(selections)
                if not selected:
                    return {"skipped": True, "reason": "No photos above score floor"}

                # Generate clips via Kling
                clip_urls = await self._generate_clips(selected, listing.metadata_)

                # Filter out failed clips
                successful = [(s, url) for s, url in zip(selected, clip_urls) if url]
                if not successful:
                    return {"status": "failed", "reason": "All clips failed to generate"}

                # Download clips to temp files
                clip_paths = await self._download_clips([url for _, url in successful])

                # Stitch into final video
                transitions = [get_transition(i, len(successful)) for i in range(len(successful))]
                video_bytes = self._stitcher.stitch(clip_paths, transitions)

                # Upload to S3
                s3_key = self._storage.upload_bytes(
                    data=video_bytes,
                    key=f"videos/{listing_id}/tour.mp4",
                    content_type="video/mp4",
                )

                # Create VideoAsset record
                video_asset = VideoAsset(
                    tenant_id=listing.tenant_id,
                    listing_id=listing_id,
                    s3_key=s3_key,
                    video_type="ai_generated",
                    duration_seconds=len(successful) * settings.video_clip_duration,
                    status="ready",
                    clip_count=len(successful),
                )
                session.add(video_asset)

                await emit_event(
                    session=session,
                    event_type="video.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_type": "ai_generated",
                        "clip_count": len(successful),
                        "s3_key": s3_key,
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

                # Clean up temp files
                for p in clip_paths:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

        return {
            "status": "ready",
            "clip_count": len(successful),
            "video_asset_id": str(video_asset.id),
            "s3_key": s3_key,
        }

    def _select_photos(self, selections) -> list[tuple]:
        """Select up to max_photos using slot priority order."""
        # Build lookup: room_label → best (selection, asset, vision_result)
        by_room: dict[str, tuple] = {}
        for ps, asset, vr in selections:
            room = vr.room_label if vr else "unknown"
            score = vr.quality_score / 100.0 if vr else 0
            # Keep highest-scored per room
            if room not in by_room or score > (by_room[room][2].quality_score / 100.0 if by_room[room][2] else 0):
                by_room[room] = (ps, asset, vr)

        # Select in slot order
        selected = []
        for room in SLOT_ORDER:
            if room in by_room and len(selected) < self._max_photos:
                _, asset, vr = by_room[room]
                score = vr.quality_score / 100.0 if vr else 0
                # Drone and exterior bypass score floor
                if room in ("drone", "exterior") or score >= self._score_floor:
                    selected.append(by_room[room])
        return selected

    async def _generate_clips(self, selected, metadata) -> list[str | None]:
        """Generate Kling clips concurrently with rate limiting."""
        async def generate_one(index, ps, asset, vr):
            room = vr.room_label if vr else "living_room"
            prompt = get_prompt_for_room(room, metadata)
            camera = get_camera_control(room)

            async with self._semaphore:
                if index > 0:
                    await asyncio.sleep(3)  # Stagger to avoid rate limits
                try:
                    task_id = await self._kling.generate_clip(
                        image_url=asset.file_path,
                        prompt=prompt,
                        negative_prompt=NEGATIVE_PROMPT,
                        camera_control=camera,
                    )
                    url = await self._kling.poll_task(task_id)
                    return url
                except Exception:
                    return None

        tasks = [generate_one(i, ps, asset, vr) for i, (ps, asset, vr) in enumerate(selected)]
        return await asyncio.gather(*tasks)

    async def _download_clips(self, urls: list[str]) -> list[str]:
        """Download clip URLs to temporary files."""
        paths = []
        async with httpx.AsyncClient(timeout=60) as client:
            for i, url in enumerate(urls):
                resp = await client.get(url)
                path = os.path.join(tempfile.gettempdir(), f"launchlens_clip_{i}.mp4")
                with open(path, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
        return paths
