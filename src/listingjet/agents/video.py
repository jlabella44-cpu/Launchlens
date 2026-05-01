"""VideoAgent — generates AI property tour videos from listing photos via Kling 2.5 Turbo."""

import asyncio
import logging
import os
import tempfile

import httpx
from sqlalchemy import select

from listingjet.agents.video_template import (
    DRONE_ROOMS,
    EXTERIOR_ROOMS,
    NEGATIVE_PROMPT,
    STANDARD_60S,
    VIDEO_EXCLUDED_LABELS,
    WALKTHROUGH_ORDER,
    VideoTemplate,
    get_prompt_for_room,
)
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.providers.kling import KlingProvider
from listingjet.services.endcard import ENDCARD_DURATION, generate_endcard
from listingjet.services.metrics import record_cost
from listingjet.services.storage import StorageService
from listingjet.services.video_stitcher import VideoStitcher

from .base import AgentContext, BaseAgent, heartbeat_during

logger = logging.getLogger(__name__)


class VideoAgent(BaseAgent):
    agent_name = "video"
    requires_ai_consent = True

    def __init__(
        self,
        kling_provider=None,
        storage_service=None,
        video_stitcher=None,
        session_factory=None,
        template: VideoTemplate = STANDARD_60S,
    ):
        self._kling = kling_provider or KlingProvider()
        self._storage = storage_service or StorageService()
        self._stitcher = video_stitcher or VideoStitcher()
        self._session_factory = session_factory or AsyncSessionLocal
        self._template = template
        self._score_floor = settings.video_score_floor
        self._semaphore = asyncio.Semaphore(3)  # max 3 concurrent Kling calls

    async def execute(self, context: AgentContext) -> dict:
        async with (
            heartbeat_during(interval=60, detail="video"),
            self.session_scope(context) as (session, listing_id, tenant_id),
        ):
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

                # Select 12 photos using template slot algorithm
                selected = self._select_photos(selections)
                if not selected:
                    return {"skipped": True, "reason": "No photos above score floor"}

                # Generate clips via Kling
                clip_results = await self._generate_clips(selected, listing.metadata_)

                # Filter out failed clips (poll_task returns dict or None)
                successful = [(s, r) for s, r in zip(selected, clip_results) if r]
                if not successful:
                    return {"status": "failed", "reason": "All clips failed to generate"}

                total_credits = sum(
                    float(r.get("credits") or 0) for _, r in successful
                )
                logger.info(
                    "video_clips_generated listing=%s clips=%d/%d credits=%.1f",
                    listing_id, len(successful), self._template.clip_count, total_credits,
                )

                if len(successful) < self._template.clip_count:
                    logger.warning(
                        "video_clip_count_short listing=%s expected=%d actual=%d",
                        listing_id, self._template.clip_count, len(successful),
                    )

                # Download clips to temp files
                clip_paths = await self._download_clips([r["url"] for _, r in successful])

                # Generate branded end-card from tenant's BrandKit
                from listingjet.models.brand_kit import BrandKit
                brand_kit = (await session.execute(
                    select(BrandKit).where(BrandKit.tenant_id == listing.tenant_id)
                    .limit(1)
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

                # Stitch into final video with hard cuts (silent MP4)
                transitions = [self._template.transition] * len(clip_paths)
                video_bytes = self._stitcher.stitch(clip_paths, transitions)

                # Upload to S3
                s3_key = self._storage.upload_bytes(
                    data=video_bytes,
                    key=f"videos/{listing_id}/tour.mp4",
                    content_type="video/mp4",
                )

                # Upsert VideoAsset — replace any previous ai_generated record
                existing = (await session.execute(
                    select(VideoAsset).where(
                        VideoAsset.listing_id == listing_id,
                        VideoAsset.video_type == "ai_generated",
                    ).order_by(VideoAsset.created_at.desc()).limit(1)
                )).scalar_one_or_none()

                if existing:
                    existing.s3_key = s3_key
                    existing.duration_seconds = len(successful) * self._template.clip_duration_s
                    existing.status = "ready"
                    existing.clip_count = len(successful)
                    video_asset = existing
                    logger.info("video_asset_updated listing=%s asset=%s", listing_id, existing.id)
                else:
                    video_asset = VideoAsset(
                        tenant_id=listing.tenant_id,
                        listing_id=listing_id,
                        s3_key=s3_key,
                        video_type="ai_generated",
                        duration_seconds=len(successful) * self._template.clip_duration_s,
                        status="ready",
                        clip_count=len(successful),
                    )
                    session.add(video_asset)

                await self.emit(session, context, "video.completed", {
                    "listing_id": str(listing_id),
                    "video_type": "ai_generated",
                    "clip_count": len(successful),
                    "total_credits": total_credits,
                    "s3_key": s3_key,
                })

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
        """Fill exactly template.clip_count positions.

        Position layout:
          1      = front exterior (best)
          2      = drone OR second-best exterior
          3..N-1 = interiors, score-descending (best up front, lowest in back half)
          N      = drone OR exterior_rear OR repeat exterior

        If the package has fewer unique photos than clip_count, pad by repeating
        the highest-scored photos.
        """
        total = self._template.clip_count

        # Deduplicate by asset_id — keep highest-scored entry per photo
        seen: dict[str, tuple] = {}
        for ps, asset, vr in selections:
            aid = str(asset.id)
            score = vr.quality_score / 100.0 if vr else 0.0
            room = vr.room_label if vr else None

            # Skip non-photo content (floorplans, diagrams, documents, etc.)
            if room and room.lower() in VIDEO_EXCLUDED_LABELS:
                logger.info("video_skip_excluded room=%s asset=%s", room, aid)
                continue

            # Skip assets with filenames that indicate non-photo content
            fname = (asset.file_path or "").lower()
            if any(kw in fname for kw in ("floorplan", "floor_plan", "diagram", "blueprint", "sitemap", "site_plan")):
                logger.info("video_skip_filename asset=%s path=%s", aid, fname)
                continue

            # Skip very low quality photos (below 30% threshold)
            if score < 0.30:
                logger.info("video_skip_low_quality score=%.2f asset=%s", score, aid)
                continue

            if aid not in seen or score > seen[aid][3]:
                # Detect drones/exteriors from filename when room label is missing
                if not room:
                    if "dji" in fname or "drone" in fname:
                        room = "drone"
                    elif not (vr and vr.is_interior):
                        room = "exterior"
                    else:
                        room = "unknown"
                seen[aid] = (ps, asset, vr, score, room)

        # Bucket photos by room category
        drones: list[tuple] = []
        exteriors: list[tuple] = []
        interiors: list[tuple] = []
        for aid, (ps, asset, vr, score, room) in seen.items():
            entry = (ps, asset, vr, score, room)
            if room in DRONE_ROOMS:
                drones.append(entry)
            elif room in EXTERIOR_ROOMS:
                exteriors.append(entry)
            else:
                interiors.append(entry)

        drones.sort(key=lambda e: e[3], reverse=True)
        exteriors.sort(key=lambda e: e[3], reverse=True)

        # Sort interiors by walkthrough order (spatial flow), score as tiebreaker.
        # Rooms not in WALKTHROUGH_ORDER go to the end, sorted by score.
        walk_index = {room: i for i, room in enumerate(WALKTHROUGH_ORDER)}
        max_walk = len(WALKTHROUGH_ORDER)
        interiors.sort(key=lambda e: (walk_index.get(e[4], max_walk), -e[3]))

        # All photos pooled and score-sorted — used as the padding reservoir
        all_photos = sorted(
            drones + exteriors + interiors,
            key=lambda e: e[3],
            reverse=True,
        )
        if not all_photos:
            return []

        def pop_or_pad(bucket: list, fallback: list) -> tuple:
            if bucket:
                return bucket.pop(0)
            if fallback:
                return fallback[0]  # peek — don't consume the reservoir
            return all_photos[0]

        positions: list[tuple] = [None] * total  # type: ignore

        # Position 1: best exterior (fallback: best photo overall)
        positions[0] = pop_or_pad(exteriors, all_photos)

        # Position N (last): best drone, else next exterior, else repeat exterior
        if drones:
            positions[total - 1] = drones.pop(0)
        elif exteriors:
            positions[total - 1] = exteriors.pop(0)
        else:
            positions[total - 1] = positions[0]

        # Position 2: next drone, else next exterior, else best interior
        if drones:
            positions[1] = drones.pop(0)
        elif exteriors:
            positions[1] = exteriors.pop(0)
        elif interiors:
            positions[1] = interiors[0]
        else:
            positions[1] = positions[0]

        # Positions 3..N-1 (interior slots in walkthrough order)
        interior_slots = total - 3  # positions[2] .. positions[total-2]
        interior_pool = list(interiors)  # already walkthrough-sorted
        for i in range(interior_slots):
            slot_idx = 2 + i
            if interior_pool:
                positions[slot_idx] = interior_pool.pop(0)
            else:
                # Pad with first interior if we have any; else best photo
                if interiors:
                    positions[slot_idx] = interiors[0]
                else:
                    # No interiors at all — pad from all_photos, avoiding adjacent duplicates
                    positions[slot_idx] = self._pad_pick(all_photos, positions, slot_idx)

        # Strip score/room extras for downstream compatibility → (ps, asset, vr)
        return [(e[0], e[1], e[2]) for e in positions]

    def _pad_pick(self, pool: list, positions: list, slot_idx: int) -> tuple:
        """Pick a padding photo from pool, avoiding exact duplicate of neighbor if possible."""
        prev = positions[slot_idx - 1] if slot_idx > 0 else None
        prev_asset_id = prev[1].id if prev else None
        for entry in pool:
            if entry[1].id != prev_asset_id:
                return entry
        return pool[0]

    async def _generate_clips(self, selected, metadata) -> list[dict | None]:
        """Generate Kling clips concurrently with rate limiting.

        Returns list of dicts {url, duration, credits} or None for failed clips.
        """
        async def generate_one(index, ps, asset, vr):
            room = vr.room_label if vr else "living_room"
            prompt = get_prompt_for_room(room, metadata)

            # Convert S3 key to presigned URL for Kling API
            image_url = self._storage.presigned_url(asset.file_path)

            logger.info(
                "video_clip_start slot=%d/%d room=%s asset=%s prompt_len=%d",
                index + 1, len(selected), room, asset.file_path, len(prompt),
            )

            async with self._semaphore:
                if index > 0:
                    await asyncio.sleep(3)  # Stagger to avoid rate limits
                try:
                    task_id = await self._kling.generate_clip(
                        image_url=image_url,
                        prompt=prompt,
                        negative_prompt=NEGATIVE_PROMPT,
                        duration=self._template.clip_duration_s,
                        mode=self._template.kling_mode,
                        model_name=self._template.kling_model,
                    )
                    result = await self._kling.poll_task(task_id)
                    if result:
                        logger.info(
                            "video_clip_done slot=%d room=%s credits=%s",
                            index + 1, room, result.get("credits"),
                        )
                    return result
                except Exception as exc:
                    logger.warning(
                        "video_clip_failed room=%s asset=%s error=%s",
                        room, asset.file_path, exc,
                    )
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

    def _try_download_logo(self, logo_url: str | None) -> bytes | None:
        """Download logo from S3. Returns None on failure or invalid key."""
        if not logo_url:
            return None
        # Reject keys that look like URLs or contain path traversal
        if logo_url.startswith(("http://", "https://")) or ".." in logo_url:
            logger.warning("logo_url_rejected key=%s", logo_url)
            return None
        try:
            return self._storage.download(logo_url)
        except Exception:
            return None

    def _endcard_to_video(self, png_bytes: bytes) -> str | None:
        """Convert a PNG end-card to a 5-second MP4 clip via ffmpeg."""
        import subprocess
        try:
            png_fd = tempfile.NamedTemporaryFile(suffix=".png", prefix="listingjet_endcard_", delete=False)
            mp4_fd = tempfile.NamedTemporaryFile(suffix=".mp4", prefix="listingjet_endcard_", delete=False)
            png_path = png_fd.name
            png_fd.close()
            mp4_path = mp4_fd.name
            mp4_fd.close()
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
