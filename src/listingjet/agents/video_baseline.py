"""VideoBaselineAgent — the free ffmpeg Ken Burns tour every listing gets.

Unlike VideoAgent (AI-generated Kling clips, `requires_ai_consent = True`),
this agent builds a "baseline" tour entirely with local ffmpeg: a pan/zoom
(Ken Burns) clip per packaged photo, crossfaded together, with a branded
(or neutral default) end-card always appended. No third-party AI provider
is involved, so `requires_ai_consent = False` and it can run for every
listing regardless of AI consent.

`upsert_tour_asset` is shared with Task 4 (the AI-upgrade path): both write
to the same `VideoAsset` row, keyed by `video_type in ("tour", "ai_generated")`.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile

from sqlalchemy import select

from listingjet.agents.video_template import VIDEO_EXCLUDED_LABELS
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.services.endcard import ENDCARD_DURATION, endcard_clip, generate_endcard
from listingjet.services.storage import get_storage
from listingjet.services.video_stitcher import VideoStitcher, build_ken_burns_clip, probe_duration

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

# Filename substrings that mark non-photo content (floorplans, etc.) even
# when vision analysis hasn't labeled the asset.
_EXCLUDED_FILENAME_MARKERS = ("floorplan", "blueprint", "site_plan", "diagram")


def select_baseline_photos(rows, max_photos: int = 10) -> list[tuple[Asset, VisionResult | None]]:
    """Pick the photos that go into the baseline tour, in package order.

    `rows` is a sequence of `(PackageSelection, Asset, VisionResult | None)`
    already ordered by `PackageSelection.position`. Skips non-photo assets
    (documents, floorplans, etc.) and caps at `max_photos`.
    """
    selected: list[tuple[Asset, VisionResult | None]] = []
    for _ps, asset, vr in rows:
        if vr is not None and vr.is_photo is False:
            continue
        room = vr.room_label if vr else None
        if room and room.lower() in VIDEO_EXCLUDED_LABELS:
            continue
        fname = (asset.file_path or "").lower()
        if any(marker in fname for marker in _EXCLUDED_FILENAME_MARKERS):
            continue
        selected.append((asset, vr))
        if len(selected) >= max_photos:
            break
    return selected


def build_tour(
    photo_paths_rooms: list[tuple[str, str | None]],
    endcard_png: bytes | None,
    *,
    clip_s: float = 3.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    transition_s: float = 0.5,
    music_path: str | None = None,
    music_db: float = -18.0,
    stitcher: VideoStitcher | None = None,
) -> tuple[bytes, list[dict], list[dict]]:
    """Build the Ken Burns tour video from local image paths. Pure/sync — run under `to_thread`.

    Returns `(video_bytes, chapters, clips)`:
      - `chapters`: `[{"time": int(round(start_s)), "label": room or "photo"}, ...]`
      - `clips`: `[{"room": room, "start_s": start_s, "end_s": end_s, "source": "ken_burns"}, ...]`
        (one entry per photo clip — the end card is not a "clip" in this manifest)

    Clip `i` starts at `i * (clip_s - transition_s)` because that's where the
    crossfade-stitched photo clips actually land once overlaps are applied.
    The end card, if provided, is appended afterward with a hard cut (its
    full duration is added on top, no overlap subtracted).
    """
    if not photo_paths_rooms:
        raise ValueError("No photos to build a tour from")

    stitcher = stitcher or VideoStitcher()
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_clips: list[tuple[str, float]] = []
        clips_manifest: list[dict] = []
        for i, (path, room) in enumerate(photo_paths_rooms):
            out_path = os.path.join(tmpdir, f"clip_{i}.mp4")
            build_ken_burns_clip(path, out_path, duration_s=clip_s, index=i, width=width, height=height, fps=fps)
            start_s = i * (clip_s - transition_s)
            end_s = start_s + clip_s
            photo_clips.append((out_path, clip_s))
            clips_manifest.append({"room": room, "start_s": start_s, "end_s": end_s, "source": "ken_burns"})

        photo_video_bytes = stitcher.stitch_xfade(
            photo_clips, transition_s=transition_s, music_path=music_path, music_db=music_db,
            width=width, height=height, fps=fps,
        )

        final_bytes = photo_video_bytes
        if endcard_png:
            photo_video_path = os.path.join(tmpdir, "photos.mp4")
            with open(photo_video_path, "wb") as f:
                f.write(photo_video_bytes)
            endcard_path = os.path.join(tmpdir, "endcard.mp4")
            endcard_clip(endcard_png, endcard_path, duration_s=ENDCARD_DURATION, width=width, height=height)
            final_bytes = stitcher.stitch([photo_video_path, endcard_path], ["cut"])

        chapters = [
            {"time": int(round(c["start_s"])), "label": c["room"] or "photo"}
            for c in clips_manifest
        ]
        return final_bytes, chapters, clips_manifest


async def upsert_tour_asset(
    session,
    listing: Listing,
    *,
    s3_key: str,
    duration_s: float,
    clip_count: int,
    chapters: list[dict],
    metadata: dict,
) -> VideoAsset:
    """Create or update the listing's tour `VideoAsset` row.

    Shared with Task 4 (the AI-upgrade path): both the free baseline tour
    and the AI-generated upgrade write to the same row, found by
    `video_type in ("tour", "ai_generated")`.
    """
    existing = (await session.execute(
        select(VideoAsset).where(
            VideoAsset.listing_id == listing.id,
            VideoAsset.video_type.in_(("tour", "ai_generated")),
        ).order_by(VideoAsset.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    if existing:
        existing.s3_key = s3_key
        existing.duration_seconds = int(round(duration_s))
        existing.clip_count = clip_count
        existing.chapters = chapters
        existing.metadata_ = metadata
        existing.status = "ready"
        existing.video_type = "tour"
        video_asset = existing
    else:
        video_asset = VideoAsset(
            tenant_id=listing.tenant_id,
            listing_id=listing.id,
            s3_key=s3_key,
            video_type="tour",
            duration_seconds=int(round(duration_s)),
            status="ready",
            clip_count=clip_count,
            chapters=chapters,
            metadata_=metadata,
        )
        session.add(video_asset)

    await session.flush()
    return video_asset


class VideoBaselineAgent(BaseAgent):
    """Free ffmpeg Ken Burns tour — every listing gets one, no AI consent needed."""

    agent_name = "video_baseline"
    requires_ai_consent = False

    def __init__(
        self,
        storage=None,
        stitcher=None,
        session_factory=None,
        max_photos: int = 10,
        clip_s: float = 3.0,
        width: int = 1920,
        height: int = 1080,
    ):
        self._storage = storage or get_storage()
        self._stitcher = stitcher or VideoStitcher()
        self._session_factory = session_factory or AsyncSessionLocal
        self._max_photos = max_photos
        self._clip_s = clip_s
        self._width = width
        self._height = height

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            rows = (await session.execute(
                select(PackageSelection, Asset, VisionResult)
                .join(Asset, PackageSelection.asset_id == Asset.id)
                .outerjoin(VisionResult, (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1))
                .where(PackageSelection.listing_id == listing_id)
                .order_by(PackageSelection.position)
            )).all()

            brand_kit = (await session.execute(
                select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1)
            )).scalar_one_or_none()

            brokerage_name = brand_kit.brokerage_name if brand_kit else None
            agent_name = brand_kit.agent_name if brand_kit else None
            primary_color = brand_kit.primary_color if brand_kit else None

        if not rows:
            return {"skipped": True, "reason": "no_packaged_photos"}

        selected = select_baseline_photos(rows, max_photos=self._max_photos)
        if not selected:
            return {"skipped": True, "reason": "no_packaged_photos"}

        endcard_png = generate_endcard(
            brokerage_name=brokerage_name or "",
            agent_name=agent_name or "",
            primary_color=primary_color or "#2563EB",
        )

        music_path = settings.video_music_path if settings.video_music_enabled else None

        with tempfile.TemporaryDirectory() as tmpdir:
            photo_paths_rooms: list[tuple[str, str | None]] = []
            for asset, vr in selected:
                key = asset.proxy_path or asset.file_path
                data = await asyncio.to_thread(self._storage.download, key)
                ext = os.path.splitext(key)[1] or ".jpg"
                path = os.path.join(tmpdir, f"{asset.id}{ext}")
                with open(path, "wb") as f:
                    f.write(data)
                photo_paths_rooms.append((path, vr.room_label if vr else None))

            video_bytes, chapters, clips = await asyncio.to_thread(
                build_tour,
                photo_paths_rooms,
                endcard_png,
                clip_s=self._clip_s,
                width=self._width,
                height=self._height,
                music_path=music_path,
                stitcher=self._stitcher,
            )

            s3_key = f"videos/{listing_id}/tour.mp4"
            await asyncio.to_thread(self._storage.upload_bytes, video_bytes, s3_key, "video/mp4")

            probe_path = os.path.join(tmpdir, "final_check.mp4")
            with open(probe_path, "wb") as f:
                f.write(video_bytes)
            duration_s = await asyncio.to_thread(probe_duration, probe_path)

        metadata = {
            "tier": "baseline",
            "clips": [
                {
                    "asset_id": str(asset.id),
                    "room": vr.room_label if vr else None,
                    "start_s": c["start_s"],
                    "end_s": c["end_s"],
                    "source": "ken_burns",
                }
                for (asset, vr), c in zip(selected, clips)
            ],
        }

        async with self.session_scope(context) as (session, listing_id, _tenant_id):
            listing = await session.get(Listing, listing_id)
            video_asset = await upsert_tour_asset(
                session,
                listing,
                s3_key=s3_key,
                duration_s=duration_s,
                clip_count=len(selected),
                chapters=chapters,
                metadata=metadata,
            )
            video_asset_id = video_asset.id
            await self.emit(session, context, "video_baseline.completed", {
                "video_asset_id": str(video_asset_id),
                "s3_key": s3_key,
                "clip_count": len(selected),
                "duration_s": duration_s,
            })

        return {
            "status": "ready",
            "video_asset_id": str(video_asset_id),
            "s3_key": s3_key,
            "clip_count": len(selected),
            "duration_s": duration_s,
        }
