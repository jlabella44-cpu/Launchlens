"""Activity for appending branded endcard to user-uploaded videos."""
import logging
import os
import tempfile
import uuid

from sqlalchemy import select
from temporalio import activity

from listingjet.agents.base import AgentContext

logger = logging.getLogger(__name__)


@activity.defn
async def run_append_endcard(context: AgentContext, video_asset_id: str) -> dict:
    """Download user video, append branded endcard, re-upload."""
    from listingjet.database import AsyncSessionLocal
    from listingjet.models.brand_kit import BrandKit
    from listingjet.models.video_asset import VideoAsset
    from listingjet.services.endcard import generate_endcard, endcard_png_to_video
    from listingjet.services.storage import StorageService
    from listingjet.services.video_stitcher import VideoStitcher

    storage = StorageService()
    stitcher = VideoStitcher()

    async with AsyncSessionLocal() as session:
        video = await session.get(VideoAsset, uuid.UUID(video_asset_id))
        if not video:
            return {"status": "failed", "reason": "video_asset_not_found"}

        # Get brand kit for endcard
        brand_kit = (await session.execute(
            select(BrandKit).where(BrandKit.tenant_id == video.tenant_id)
        )).scalar_one_or_none()

        brokerage_name = ""
        agent_name = ""
        primary_color = "#2563EB"
        logo_bytes = None

        if brand_kit:
            brokerage_name = brand_kit.brokerage_name or ""
            agent_name = brand_kit.agent_name or ""
            primary_color = brand_kit.primary_color or "#2563EB"
            if brand_kit.logo_s3_key:
                try:
                    logo_bytes = storage.download(brand_kit.logo_s3_key)
                except Exception:
                    pass

        # Generate endcard
        endcard_png = generate_endcard(
            brokerage_name=brokerage_name,
            agent_name=agent_name,
            primary_color=primary_color,
            logo_bytes=logo_bytes,
        )
        if not endcard_png:
            video.status = "ready"
            await session.commit()
            return {"status": "skipped", "reason": "endcard_generation_failed"}

        endcard_mp4_path = endcard_png_to_video(endcard_png)
        if not endcard_mp4_path:
            video.status = "ready"
            await session.commit()
            return {"status": "skipped", "reason": "endcard_to_video_failed"}

        # Download source video
        try:
            source_bytes = storage.download(video.s3_key)
        except Exception:
            video.status = "ready"
            await session.commit()
            return {"status": "skipped", "reason": "source_download_failed"}

        source_fd, source_path = tempfile.mkstemp(suffix=".mp4", prefix="listingjet_src_")
        with os.fdopen(source_fd, "wb") as f:
            f.write(source_bytes)

        # Stitch source + endcard
        try:
            stitched_bytes = stitcher.stitch([source_path, endcard_mp4_path], ["fade"])
        except Exception:
            logger.warning("stitch_failed video=%s", video_asset_id, exc_info=True)
            video.status = "ready"
            await session.commit()
            return {"status": "skipped", "reason": "stitch_failed"}
        finally:
            for p in (source_path, endcard_mp4_path):
                if os.path.exists(p):
                    os.unlink(p)

        # Optionally add voiceover
        listing_meta = {}
        from listingjet.models.listing import Listing
        listing = await session.get(Listing, video.listing_id)
        if listing:
            listing_meta = listing.metadata_ or {}

        voiceover_enabled = listing_meta.get("voiceover_enabled")
        if voiceover_enabled is None and brand_kit:
            voiceover_enabled = (brand_kit.raw_config or {}).get("voiceover_enabled", False)

        if voiceover_enabled:
            try:
                from listingjet.providers.elevenlabs import get_voiceover_provider
                import subprocess
                description = listing_meta.get("description", "") if listing else ""
                if description:
                    voiceover = get_voiceover_provider()
                    audio_bytes = await voiceover.synthesize(description)
                    if audio_bytes:
                        import tempfile
                        vid_fd, vid_path = tempfile.mkstemp(suffix=".mp4", prefix="listingjet_vo_in_")
                        aud_fd, aud_path = tempfile.mkstemp(suffix=".mp3", prefix="listingjet_vo_audio_")
                        out_fd, out_path = tempfile.mkstemp(suffix=".mp4", prefix="listingjet_vo_out_")
                        with os.fdopen(vid_fd, "wb") as f:
                            f.write(stitched_bytes)
                        with os.fdopen(aud_fd, "wb") as f:
                            f.write(audio_bytes)
                        os.close(out_fd)
                        subprocess.run([
                            "ffmpeg", "-i", vid_path, "-i", aud_path,
                            "-c:v", "copy", "-c:a", "aac",
                            "-map", "0:v:0", "-map", "1:a:0",
                            "-shortest", "-y", out_path,
                        ], check=True, capture_output=True)
                        with open(out_path, "rb") as f:
                            stitched_bytes = f.read()
                        for p in (vid_path, aud_path, out_path):
                            if os.path.exists(p):
                                os.unlink(p)
            except Exception:
                logger.warning("voiceover_failed video=%s", video_asset_id, exc_info=True)

        # Upload branded video
        branded_key = f"videos/{video.listing_id}/branded.mp4"
        storage.upload(branded_key, stitched_bytes, content_type="video/mp4")

        video.s3_key = branded_key
        video.status = "ready"
        await session.commit()

        return {"status": "completed", "s3_key": branded_key}
