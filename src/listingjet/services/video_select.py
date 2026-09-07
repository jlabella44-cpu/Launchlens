"""Shared "which video is *the* video for this listing" selection logic.

Both `GET /listings/{id}/video` (and its `/social-cuts` sibling) and
`SocialCutAgent` need to pick one ready `VideoAsset` per listing to act on.
They must agree: prefer the ready `video_type == "tour"` row (the two-tier
pipeline's own output), else fall back to the newest ready row of any type
(e.g. a user-uploaded or professional video) so a listing without a tour
still serves something.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.video_asset import VideoAsset


async def pick_tour_video(session: AsyncSession, listing_id: uuid.UUID) -> VideoAsset | None:
    """Return the listing's tour video: the ready `tour` row if one exists,
    else the newest ready row of any type. `None` if nothing is ready yet."""
    videos = (await session.execute(
        select(VideoAsset)
        .where(VideoAsset.listing_id == listing_id, VideoAsset.status == "ready")
        .order_by(VideoAsset.created_at.desc())
    )).scalars().all()
    if not videos:
        return None
    for video in videos:
        if video.video_type == "tour":
            return video
    return videos[0]
