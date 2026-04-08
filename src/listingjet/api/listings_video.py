"""Listing video endpoints — get video, social cuts, upload video."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.listings import VideoUploadRequest
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.user import User
from listingjet.models.video_asset import VideoAsset

router = APIRouter()


@router.get("/{listing_id}/video")
async def get_video(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    video = (await db.execute(
        select(VideoAsset)
        .where(VideoAsset.listing_id == listing.id, VideoAsset.status == "ready")
        .order_by(VideoAsset.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="No video available")

    return {
        "s3_key": video.s3_key,
        "video_type": video.video_type,
        "duration_seconds": video.duration_seconds,
        "status": video.status,
        "chapters": video.chapters,
        "social_cuts": video.social_cuts,
        "thumbnail_s3_key": video.thumbnail_s3_key,
        "clip_count": video.clip_count,
        "created_at": video.created_at.isoformat(),
    }


@router.get("/{listing_id}/video/social-cuts")
async def get_video_social_cuts(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    video = (await db.execute(
        select(VideoAsset)
        .where(VideoAsset.listing_id == listing.id, VideoAsset.status == "ready")
        .order_by(VideoAsset.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not video or not video.social_cuts:
        return []
    return video.social_cuts


@router.post("/{listing_id}/video/upload", status_code=201)
async def upload_video(
    listing_id: uuid.UUID,
    body: VideoUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a user-submitted or professional video."""
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if body.video_type not in ("user_raw", "professional"):
        raise HTTPException(status_code=400, detail="video_type must be 'user_raw' or 'professional'")

    # Validate S3 key is scoped to this tenant's namespace
    tenant_prefix = f"videos/{listing_id}/"
    if not body.s3_key.startswith(tenant_prefix):
        raise HTTPException(status_code=400, detail=f"s3_key must start with {tenant_prefix}")

    video = VideoAsset(
        tenant_id=current_user.tenant_id,
        listing_id=listing.id,
        s3_key=body.s3_key,
        video_type=body.video_type,
        duration_seconds=body.duration_seconds,
        status="ready",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "id": str(video.id),
        "s3_key": video.s3_key,
        "video_type": video.video_type,
        "status": video.status,
    }
