"""VideoAIAgent — the paid AI tour: up to six Runway-generated shots, stitched.

This is the upgrade tier over `VideoBaselineAgent`'s free ffmpeg Ken Burns
tour. It picks a handful of hero photos, submits one Runway image-to-video
task per photo, polls them concurrently, and crossfades the results into a
single tour with a branded end card.

Two properties matter operationally:

* **Resume.** Runway task ids are written back to the tour `VideoAsset`
  row's ``metadata_["runway_tasks"]`` *before* polling starts, so a crash
  mid-render never orphans (and never re-pays for) work already submitted.
  A re-run polls the ids it finds instead of resubmitting.
* **Graceful degradation.** Any Runway failure or timeout for a single shot
  falls back to a local Ken Burns clip of the same photo, so the tour is
  always complete even when the provider is not.

Both tiers write the same row (`upsert_tour_asset`); `metadata_["tier"]`
says which one produced the current video.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass

from sqlalchemy import select

from listingjet.agents.video_baseline import select_baseline_photos, upsert_tour_asset
from listingjet.agents.video_template import (
    DRONE_ROOMS,
    EXTERIOR_ROOMS,
    WALKTHROUGH_ORDER,
    get_prompt_for_room,
)
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.providers.factory import get_runway
from listingjet.providers.runway import RunwayError
from listingjet.services.endcard import ENDCARD_DURATION, endcard_clip, generate_endcard
from listingjet.services.metrics import record_video_seconds
from listingjet.services.storage import get_storage
from listingjet.services.video_stitcher import VideoStitcher, build_ken_burns_clip, probe_duration

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

TRANSITION_S = 0.5
FALLBACK_CLIP_S = 5.0
PRESIGN_EXPIRY_S = 3600  # Runway fetches the image during the job, not at submit time
POLL_TIMEOUT_S = 600.0

_WALKTHROUGH_INDEX = {room: i for i, room in enumerate(WALKTHROUGH_ORDER)}


@dataclass
class Shot:
    """One photo destined for one generated clip."""

    asset: Asset
    room: str | None
    kind: str  # "exterior" | "drone" | "interior"


def _kind_for(room: str | None) -> str:
    if room in DRONE_ROOMS:
        return "drone"
    if room in EXTERIOR_ROOMS:
        return "exterior"
    return "interior"


def _score(vr: VisionResult | None) -> float:
    if vr is None:
        return -1.0
    for value in (vr.hero_score, vr.quality_score):
        if value is not None:
            return float(value)
    return -1.0


class VideoAIAgent(BaseAgent):
    """AI property tour built from Runway clips, with a Ken Burns safety net."""

    agent_name = "video_ai"
    requires_ai_consent = True

    def __init__(
        self,
        runway=None,
        storage=None,
        stitcher=None,
        session_factory=None,
        concurrency: int = 3,
        max_shots: int = 6,
        width: int = 1920,
        height: int = 1080,
    ):
        self._owns_runway = runway is None
        self._runway = runway or get_runway()
        self._storage = storage or get_storage()
        self._stitcher = stitcher or VideoStitcher()
        self._session_factory = session_factory or AsyncSessionLocal
        self._concurrency = concurrency
        self._max_shots = max_shots
        self._width = width
        self._height = height

    # ------------------------------------------------------------------ #
    # Selection / routing
    # ------------------------------------------------------------------ #

    def select_shots(self, rows) -> list[Shot]:
        """Pick up to `max_shots` photos: hero exterior, drone, then interiors.

        `rows` is a sequence of `(PackageSelection, Asset, VisionResult | None)`
        in package order. Non-photo assets are filtered out by the same rules
        the baseline tour uses. Interiors run in `WALKTHROUGH_ORDER`; leftover
        exteriors (then leftover drones) backfill any remaining slots.
        """
        base = select_baseline_photos(rows, max_photos=len(rows) or 1)

        exteriors: list[tuple[Asset, VisionResult | None, str]] = []
        drones: list[tuple[Asset, VisionResult | None, str]] = []
        interiors: list[tuple[Asset, VisionResult | None, str]] = []
        for asset, vr in base:
            room = vr.room_label if vr else None
            kind = _kind_for(room)
            bucket = {"exterior": exteriors, "drone": drones}.get(kind, interiors)
            bucket.append((asset, vr, room))

        exteriors.sort(key=lambda e: _score(e[1]), reverse=True)
        drones.sort(key=lambda e: _score(e[1]), reverse=True)
        interiors.sort(key=lambda e: _WALKTHROUGH_INDEX.get(e[2], len(WALKTHROUGH_ORDER)))

        ordered = (
            exteriors[:1] + drones[:1] + interiors + exteriors[1:] + drones[1:]
        )[: self._max_shots]
        return [Shot(asset=a, room=room, kind=_kind_for(room)) for a, _vr, room in ordered]

    def model_for(self, kind: str) -> tuple[str, int, bool | None]:
        """Return `(model, duration_s, audio)` for a shot kind."""
        if kind in ("exterior", "drone"):
            return (settings.runway_exterior_model, 6, False)
        return (settings.runway_interior_model, 5, None)

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    async def execute(self, context: AgentContext) -> dict:
        try:
            return await self._execute(context)
        finally:
            if self._owns_runway and hasattr(self._runway, "aclose"):
                await self._runway.aclose()

    async def _execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")
            listing_metadata = dict(listing.metadata_ or {})

            rows = (await session.execute(
                select(PackageSelection, Asset, VisionResult)
                .join(Asset, PackageSelection.asset_id == Asset.id)
                .outerjoin(VisionResult, (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1))
                .where(PackageSelection.listing_id == listing_id)
                .order_by(PackageSelection.position)
            )).all()

            existing = await self._existing_tour(session, listing_id)
            known_tasks: dict[str, str] = dict((existing.metadata_ or {}).get("runway_tasks") or {}) if existing else {}

            brand_kit = (await session.execute(
                select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1)
            )).scalar_one_or_none()
            brand = {
                "brokerage_name": (brand_kit.brokerage_name if brand_kit else None) or "",
                "agent_name": (brand_kit.agent_name if brand_kit else None) or "",
                "primary_color": (brand_kit.primary_color if brand_kit else None) or "#2563EB",
            }

        shots = self.select_shots(rows) if rows else []
        if not shots:
            return {"skipped": True, "reason": "no_shots"}

        s3_key = f"videos/{listing_id}/tour.mp4"

        # --- submit anything we don't already have a task id for -------- #
        tasks: dict[str, str] = {}
        resumed_asset_ids: set[str] = set()
        submitted_new = False
        for shot in shots:
            asset_id = str(shot.asset.id)
            resumed = known_tasks.get(asset_id)
            if resumed:
                tasks[asset_id] = resumed
                resumed_asset_ids.add(asset_id)
                continue
            model, duration, audio = self.model_for(shot.kind)
            key = shot.asset.proxy_path or shot.asset.file_path
            image_url = await asyncio.to_thread(
                self._storage.presigned_url, key, PRESIGN_EXPIRY_S
            )
            prompt = get_prompt_for_room(shot.room or "living_room", listing_metadata)
            tasks[asset_id] = await self._runway.image_to_video(
                image_url, prompt, model=model, duration=duration, audio=audio,
            )
            submitted_new = True

        # Persist task ids in their own short transaction BEFORE polling, so a
        # crash mid-render leaves the ids behind for the next run to resume.
        if submitted_new:
            async with self.session_scope(context) as (session, listing_id, tenant_id):
                await self._persist_task_ids(
                    session, listing_id, tenant_id, tasks,
                    s3_key=s3_key, clip_count=len(shots),
                )

        # --- render every shot (Runway, or Ken Burns on failure) -------- #
        semaphore = asyncio.Semaphore(self._concurrency)
        with tempfile.TemporaryDirectory() as tmpdir:
            # return_exceptions so one shot blowing up cannot tear this temp
            # directory down while its siblings are still writing into it.
            # _render_shot swallows the failures it can degrade (see below), so
            # anything that comes back here is genuinely unhandled — re-raise it.
            rendered = await asyncio.gather(*[
                self._render_shot(shot, tasks[str(shot.asset.id)], semaphore, tmpdir, i)
                for i, shot in enumerate(shots)
            ], return_exceptions=True)
            for outcome in rendered:
                if isinstance(outcome, BaseException):
                    raise outcome

            cost_usd = 0.0
            for shot, clip in zip(shots, rendered):
                if clip["source"] == "runway" and str(shot.asset.id) not in resumed_asset_ids:
                    cost_usd += record_video_seconds(
                        clip["model"], clip["billed_s"], self.agent_name,
                    )

            video_bytes = await asyncio.to_thread(self._stitch, rendered, tmpdir, brand)
            await asyncio.to_thread(self._storage.upload_bytes, video_bytes, s3_key, "video/mp4")

            probe_path = os.path.join(tmpdir, "final_check.mp4")
            with open(probe_path, "wb") as f:
                f.write(video_bytes)
            duration_s = await asyncio.to_thread(probe_duration, probe_path)

        clips_manifest, chapters = self._manifest(shots, rendered)
        runway_clips = sum(1 for c in rendered if c["source"] == "runway")
        fallback_clips = len(rendered) - runway_clips

        metadata = {
            "tier": "ai",
            "clips": clips_manifest,
            "runway_tasks": tasks,
        }

        async with self.session_scope(context) as (session, listing_id, _tenant_id):
            listing = await session.get(Listing, listing_id)
            video_asset = await upsert_tour_asset(
                session,
                listing,
                s3_key=s3_key,
                duration_s=duration_s,
                clip_count=len(shots),
                chapters=chapters,
                metadata=metadata,
            )
            video_asset_id = str(video_asset.id)
            await self.emit(session, context, "video_ai.completed", {
                "video_asset_id": video_asset_id,
                "s3_key": s3_key,
                "runway_clips": runway_clips,
                "fallback_clips": fallback_clips,
                "cost_usd": round(cost_usd, 4),
            })

        return {
            "status": "ready",
            "video_asset_id": video_asset_id,
            "s3_key": s3_key,
            "runway_clips": runway_clips,
            "fallback_clips": fallback_clips,
            "cost_usd": round(cost_usd, 4),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _existing_tour(self, session, listing_id) -> VideoAsset | None:
        return (await session.execute(
            select(VideoAsset)
            .where(
                VideoAsset.listing_id == listing_id,
                VideoAsset.video_type.in_(("tour", "ai_generated")),
            )
            .order_by(VideoAsset.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

    async def _persist_task_ids(
        self, session, listing_id, tenant_id, tasks: dict[str, str], *, s3_key: str, clip_count: int,
    ) -> None:
        """Write `runway_tasks` onto the tour row, creating a pending row if needed.

        Deliberately narrow: it must not clobber a baseline tour's s3_key,
        duration or chapters, which stay serving until this run finishes.
        """
        existing = await self._existing_tour(session, listing_id)
        if existing:
            metadata = dict(existing.metadata_ or {})
            metadata["runway_tasks"] = dict(tasks)
            existing.metadata_ = metadata
        else:
            session.add(VideoAsset(
                tenant_id=tenant_id,
                listing_id=listing_id,
                s3_key=s3_key,
                video_type="tour",
                duration_seconds=0,
                status="processing",
                clip_count=clip_count,
                chapters=[],
                metadata_={"tier": "ai", "clips": [], "runway_tasks": dict(tasks)},
            ))
        await session.flush()

    async def _render_shot(self, shot: Shot, task_id: str, semaphore, tmpdir: str, index: int) -> dict:
        """Poll one Runway task and download it; fall back to Ken Burns on failure."""
        model, duration, _audio = self.model_for(shot.kind)
        out_path = os.path.join(tmpdir, f"shot_{index}.mp4")

        # The semaphore bounds real work — the transfer and the ffmpeg fallback.
        # Polling is idle HTTP against an already-submitted job, so holding a
        # slot across it would cap us at `concurrency` renders in flight for no
        # reason (and stall a finished shot behind a slow one).
        try:
            urls = await self._runway.wait(task_id, timeout_s=POLL_TIMEOUT_S)
            if not urls:
                raise RunwayError(f"Runway task {task_id} succeeded with no output")
            async with semaphore:
                data = await self._runway.download(urls[0])
                with open(out_path, "wb") as f:
                    f.write(data)
                actual_s = await asyncio.to_thread(probe_duration, out_path)
            return {
                "path": out_path, "duration_s": actual_s, "billed_s": float(duration),
                "source": "runway", "model": model,
            }
        except (RunwayError, asyncio.TimeoutError, subprocess.CalledProcessError, RuntimeError, OSError) as exc:
            logger.warning(
                "Runway shot failed for asset %s (task %s): %s — falling back to Ken Burns",
                shot.asset.id, task_id, exc,
            )

        async with semaphore:
            key = shot.asset.proxy_path or shot.asset.file_path
            photo = await asyncio.to_thread(self._storage.download, key)
            ext = os.path.splitext(key)[1] or ".jpg"
            photo_path = os.path.join(tmpdir, f"src_{index}{ext}")
            with open(photo_path, "wb") as f:
                f.write(photo)
            await asyncio.to_thread(
                build_ken_burns_clip, photo_path, out_path,
                duration_s=FALLBACK_CLIP_S, index=index,
                width=self._width, height=self._height,
            )
            actual_s = await asyncio.to_thread(probe_duration, out_path)
            return {
                "path": out_path, "duration_s": actual_s, "billed_s": 0.0,
                "source": "ken_burns", "model": None,
            }

    def _stitch(self, rendered: list[dict], tmpdir: str, brand: dict) -> bytes:
        """Crossfade the shots together and append the end card. Sync — run in a thread."""
        music_path = settings.video_music_path if settings.video_music_enabled else None
        shots_bytes = self._stitcher.stitch_xfade(
            [(c["path"], c["duration_s"]) for c in rendered],
            transition_s=TRANSITION_S,
            music_path=music_path,
            width=self._width,
            height=self._height,
        )

        png = generate_endcard(**brand)
        if not png:
            return shots_bytes

        shots_path = os.path.join(tmpdir, "shots.mp4")
        with open(shots_path, "wb") as f:
            f.write(shots_bytes)
        endcard_path = os.path.join(tmpdir, "endcard.mp4")
        endcard_clip(
            png, endcard_path,
            duration_s=ENDCARD_DURATION, width=self._width, height=self._height,
        )
        return self._stitcher.stitch(
            [shots_path, endcard_path], ["cut"],
            output_width=self._width, output_height=self._height,
        )

    def _manifest(self, shots: list[Shot], rendered: list[dict]) -> tuple[list[dict], list[dict]]:
        """Build the clip manifest and chapter marks from the *actual* durations."""
        clips: list[dict] = []
        chapters: list[dict] = []
        start_s = 0.0
        for shot, clip in zip(shots, rendered):
            end_s = start_s + clip["duration_s"]
            clips.append({
                "asset_id": str(shot.asset.id),
                "room": shot.room,
                "kind": shot.kind,
                "start_s": start_s,
                "end_s": end_s,
                "source": clip["source"],
                "model": clip["model"],
            })
            chapters.append({"time": int(round(start_s)), "label": shot.room or "photo"})
            start_s = end_s - TRANSITION_S
        return clips, chapters
