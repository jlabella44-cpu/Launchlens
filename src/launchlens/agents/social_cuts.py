"""SocialCutAgent — creates platform-specific video clips from a property tour video."""

import uuid
from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing
from launchlens.models.video_asset import VideoAsset
from launchlens.services.storage import StorageService
from launchlens.services.events import emit_event
from .base import BaseAgent, AgentContext

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
        """Crop/resize a video for a specific platform. Returns video bytes.
        MVP: returns the source bytes truncated (actual FFmpeg cropping in Phase 2).
        """
        return source_bytes


class SocialCutAgent(BaseAgent):
    agent_name = "social_cuts"

    def __init__(self, storage_service=None, video_cutter=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._cutter = video_cutter or VideoCutter()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                if not listing:
                    raise ValueError(f"Listing {listing_id} not found")

                video = (await session.execute(
                    select(VideoAsset)
                    .where(VideoAsset.listing_id == listing_id, VideoAsset.status == "ready")
                    .order_by(VideoAsset.created_at.desc())
                    .limit(1)
                )).scalar_one_or_none()

                if not video:
                    return {"skipped": True, "reason": "No ready video found"}

                # Generate a cut for each platform
                cuts = []
                for platform, spec in PLATFORM_SPECS.items():
                    cut_bytes = self._cutter.create_cut(
                        source_bytes=b"placeholder",  # MVP: actual download in Phase 2
                        width=spec["width"],
                        height=spec["height"],
                        max_duration=spec["max_duration"],
                    )

                    s3_key = self._storage.upload_bytes(
                        data=cut_bytes,
                        key=f"videos/{listing_id}/social/{platform}.mp4",
                        content_type="video/mp4",
                    )

                    cuts.append({
                        "platform": platform,
                        "s3_key": s3_key,
                        "width": spec["width"],
                        "height": spec["height"],
                        "max_duration": spec["max_duration"],
                    })

                video.social_cuts = cuts

                await emit_event(
                    session=session,
                    event_type="social_cuts.completed",
                    payload={
                        "listing_id": str(listing_id),
                        "video_asset_id": str(video.id),
                        "cut_count": len(cuts),
                        "platforms": [c["platform"] for c in cuts],
                    },
                    tenant_id=str(context.tenant_id),
                    listing_id=str(listing_id),
                )

        return {"cut_count": len(cuts), "video_asset_id": str(video.id)}
