"""SocialCutAgent — creates platform-specific video clips from a property tour video."""

import asyncio
import subprocess
import tempfile

from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing
from listingjet.models.video_asset import VideoAsset
from listingjet.services.storage import StorageService
from listingjet.services.video_select import pick_tour_video
from listingjet.services.video_stitcher import ffmpeg_cmd

from .base import AgentContext, BaseAgent

PLATFORM_SPECS: dict[str, dict] = {
    "instagram": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 30,
        "format": "mp4",
    },
    "tiktok": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 60,
        "format": "mp4",
    },
    "facebook": {
        "width": 1920, "height": 1080,  # 16:9 horizontal
        "max_duration": 60,
        "format": "mp4",
    },
    "youtube_short": {
        "width": 1080, "height": 1920,  # 9:16 vertical
        "max_duration": 60,
        "format": "mp4",
    },
}


class VideoCutter:
    """FFmpeg-based video cropper/resizer for social platforms."""

    def create_cut(
        self,
        source_bytes: bytes,
        width: int,
        height: int,
        max_duration: int,
    ) -> bytes:
        """Crop/resize a video for a specific platform using FFmpeg. Returns video bytes."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as src_f,
            tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as dst_f,
        ):
            src_path = src_f.name
            dst_path = dst_f.name
            src_f.write(source_bytes)

        try:
            subprocess.run(
                [
                    ffmpeg_cmd(), "-i", src_path,
                    "-t", str(max_duration),
                    "-vf", (
                        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                    ),
                    "-c:v", "libx264", "-preset", "fast",
                    "-y", dst_path,
                ],
                check=True,
                capture_output=True,
            )
            with open(dst_path, "rb") as f:
                return f.read()
        finally:
            import os
            os.unlink(src_path)
            os.unlink(dst_path)


class SocialCutAgent(BaseAgent):
    agent_name = "social_cuts"

    def __init__(self, storage_service=None, video_cutter=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._cutter = video_cutter or VideoCutter()
        self._session_factory = session_factory or AsyncSessionLocal

    async def _pick_video(self, session, listing_id) -> VideoAsset | None:
        return await pick_tour_video(session, listing_id)

    async def execute(self, context: AgentContext) -> dict:
        # Phase 1: pick the source video and grab just what we need, then
        # close the session before doing any slow IO/CPU work — a DB session
        # (and the connection-pool slot behind it) must never sit open across
        # an ffmpeg subprocess or an S3 round-trip.
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            video = await self._pick_video(session, listing_id)
            if not video:
                return {"skipped": True, "reason": "No ready video found"}

            video_id = video.id
            source_key = video.s3_key

        # Phase 2: no session open. Downloads, ffmpeg cuts, and uploads all
        # run in worker threads so the event loop stays free for other jobs.
        source_bytes = await asyncio.to_thread(self._storage.download, source_key)

        cuts = []
        for platform, spec in PLATFORM_SPECS.items():
            cut_bytes = await asyncio.to_thread(
                self._cutter.create_cut,
                source_bytes=source_bytes,
                width=spec["width"],
                height=spec["height"],
                max_duration=spec["max_duration"],
            )

            s3_key = await asyncio.to_thread(
                self._storage.upload,
                key=f"videos/{listing_id}/social/{platform}.mp4",
                data=cut_bytes,
                content_type="video/mp4",
            )

            cuts.append({
                "platform": platform,
                "s3_key": s3_key,
                "width": spec["width"],
                "height": spec["height"],
                "max_duration": spec["max_duration"],
            })

        # Phase 3: reopen a session to persist results and emit the event.
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            video = await session.get(VideoAsset, video_id)
            video.social_cuts = cuts

            await self.emit(session, context, "social_cuts.completed", {
                "listing_id": str(listing_id),
                "video_asset_id": str(video_id),
                "cut_count": len(cuts),
                "platforms": [c["platform"] for c in cuts],
            })

        return {"cut_count": len(cuts), "video_asset_id": str(video_id)}
