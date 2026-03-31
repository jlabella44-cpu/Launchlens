"""VideoAgent — generates AI property tour videos from listing photos via Kling.
Ported from Juke Marketing Engine with adaptations for ListingJet pipeline.
"""

import asyncio
import logging
import os
import tempfile
import uuid

logger = logging.getLogger(__name__)

import httpx
from sqlalchemy import select

from listingjet.agents.video_prompts import (
    NEGATIVE_PROMPT,
    SLOT_ORDER,
    get_camera_control,
    get_prompt_for_room,
    get_transition,
)
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.providers.elevenlabs import get_voiceover_provider
from listingjet.providers.kling import KlingProvider
from listingjet.services.endcard import ENDCARD_DURATION, generate_endcard
from listingjet.services.events import emit_event
from listingjet.services.metrics import record_cost
from listingjet.services.storage import StorageService
from listingjet.services.video_stitcher import VideoStitcher

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

                # Generate branded end-card from tenant's BrandKit
                from listingjet.models.brand_kit import BrandKit
                brand_kit = (await session.execute(
                    select(BrandKit).where(BrandKit.tenant_id == listing.tenant_id)
                )).scalar_one_or_none()

                endcard_path = None
                if brand_kit:
                    endcard_png = generate_endcard(
                        brokerage_name=brand_kit.brokerage_name or "",
                        agent_name=brand_kit.agent_name or "",
                        primary_color=brand_kit.primary_color or "#2563EB",
                        logo_bytes=self._try_download_logo(brand_kit.logo_url),
                    )
                    if endcard_png:
                        endcard_path = self._endcard_to_video(endcard_png)
                        if endcard_path:
                            clip_paths.append(endcard_path)

                # Stitch into final video (includes end-card if generated)
                transitions = [get_transition(i, len(successful)) for i in range(len(successful))]
                if endcard_path:
                    transitions.append("fade")  # Fade into end-card
                video_bytes = self._stitcher.stitch(clip_paths, transitions)

                # Generate voiceover narration from listing description
                video_bytes = await self._add_voiceover(video_bytes, listing)

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

        record_cost(self.agent_name, "kling", len(successful))
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
            for url in urls:
                resp = await client.get(url)
                fd, path = tempfile.mkstemp(suffix=".mp4", prefix="listingjet_clip_")
                with os.fdopen(fd, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
        return paths

    async def _add_voiceover(self, video_bytes: bytes, listing) -> bytes:
        """Generate voiceover from listing description and overlay on video.

        Returns original video bytes if voiceover generation fails or is unavailable.
        """
        import subprocess

        voiceover = get_voiceover_provider()
        description = (listing.metadata_ or {}).get("description", "")
        if not description:
            # Try to build a basic description from metadata
            meta = listing.metadata_ or {}
            addr = listing.address or {}
            parts = []
            if addr.get("street"):
                parts.append(f"Welcome to {addr['street']}.")
            if meta.get("beds") and meta.get("baths"):
                parts.append(f"This {meta['beds']} bedroom, {meta['baths']} bathroom home")
            if meta.get("sqft"):
                parts.append(f"offers {meta['sqft']:,} square feet of living space.")
            description = " ".join(parts) if parts else ""

        if not description:
            return video_bytes

        try:
            audio_bytes = await voiceover.synthesize(description)
            if not audio_bytes:
                return video_bytes

            # Write video + audio to temp files, merge with ffmpeg
            video_path = tempfile.mktemp(suffix=".mp4", prefix="listingjet_vo_in_")
            audio_path = tempfile.mktemp(suffix=".mp3", prefix="listingjet_vo_audio_")
            output_path = tempfile.mktemp(suffix=".mp4", prefix="listingjet_vo_out_")

            with open(video_path, "wb") as f:
                f.write(video_bytes)
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            subprocess.run([
                "ffmpeg", "-i", video_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                "-y", output_path,
            ], check=True, capture_output=True)

            with open(output_path, "rb") as f:
                result = f.read()

            for p in (video_path, audio_path, output_path):
                if os.path.exists(p):
                    os.unlink(p)

            return result
        except Exception:
            logger.warning("voiceover_failed listing=%s", listing.id, exc_info=True)
            return video_bytes

    def _try_download_logo(self, logo_url: str | None) -> bytes | None:
        """Download logo from S3. Returns None on failure."""
        if not logo_url:
            return None
        try:
            return self._storage.download(logo_url)
        except Exception:
            return None

    def _endcard_to_video(self, png_bytes: bytes) -> str | None:
        """Convert a PNG end-card to a 5-second MP4 clip via ffmpeg."""
        import subprocess
        try:
            png_path = tempfile.mktemp(suffix=".png", prefix="listingjet_endcard_")
            mp4_path = tempfile.mktemp(suffix=".mp4", prefix="listingjet_endcard_")
            with open(png_path, "wb") as f:
                f.write(png_bytes)
            subprocess.run([
                "ffmpeg", "-loop", "1", "-i", png_path,
                "-c:v", "libx264", "-t", str(ENDCARD_DURATION),
                "-pix_fmt", "yuv420p", "-vf", "scale=1280:720",
                "-y", mp4_path,
            ], check=True, capture_output=True)
            os.unlink(png_path)
            return mp4_path
        except Exception:
            return None
