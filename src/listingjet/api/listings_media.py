import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.assets import (
    AssetResponse,
    CreateAssetsRequest,
    CreateAssetsResponse,
)
from listingjet.api.schemas.listings import (
    BundleMetadata,
    ExportMode,
    ExportResponse,
    ReorderRequest,
    UploadUrlsRequest,
    VideoUploadRequest,
)
from listingjet.database import get_db
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.models.video_asset import VideoAsset
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event
from listingjet.services.plan_limits import check_asset_quota, get_limits
from listingjet.services.storage import get_storage
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{listing_id}/upload-urls")
async def get_upload_urls(
    listing_id: uuid.UUID,
    body: UploadUrlsRequest,
    _rl=Depends(rate_limit(10, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate presigned S3 upload URLs for browser-direct uploads."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Normalize input: accept either filenames list or files list
    raw_files = body.files or (body.filenames or [])
    files = []
    for f in raw_files:
        if isinstance(f, str):
            files.append({"filename": f, "content_type": body.content_type})
        else:
            files.append({"filename": f.filename, "content_type": f.content_type or body.content_type})
    if not files or len(files) > 50:
        raise HTTPException(status_code=400, detail="Provide 1-50 files")

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    storage = get_storage()
    upload_urls = []
    for f in files:
        filename = f.get("filename", "") if isinstance(f, dict) else str(f)
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {filename}. Allowed: {ALLOWED_EXTENSIONS}",
            )
        content_type = f.get("content_type", "image/png" if ext == ".png" else "image/jpeg") if isinstance(f, dict) else ("image/png" if ext == ".png" else "image/jpeg")
        key = f"listings/{listing_id}/uploads/{uuid.uuid4()}/{filename}"
        try:
            presigned = storage.presigned_upload_url(key=key, content_type=content_type)
            upload_urls.append({"filename": filename, "key": key, "upload_url": presigned, "content_type": content_type})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"upload_urls": upload_urls}


@router.post("/{listing_id}/assets", status_code=201, response_model=CreateAssetsResponse)
async def register_assets(
    listing_id: uuid.UUID,
    body: CreateAssetsRequest,
    _rl=Depends(rate_limit(10, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register uploaded S3 assets for a listing and trigger the AI pipeline.

    Advances the listing from NEW → UPLOADING and automatically starts the
    Temporal workflow. Returns 403 if the plan's per-listing asset quota is exceeded.
    """
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Check per-listing asset quota
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing_count_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.listing_id == listing.id)
    )
    existing_count = existing_count_result.scalar() or 0

    if not check_asset_quota(tenant.plan, existing_count, len(body.assets)):
        max_allowed = get_limits(tenant.plan)["max_assets_per_listing"]
        raise HTTPException(
            status_code=403,
            detail=f"Asset limit reached ({existing_count}/{max_allowed}). Upgrade your plan for more.",
        )

    for a in body.assets:
        asset = Asset(
            tenant_id=current_user.tenant_id,
            listing_id=listing.id,
            file_path=a.file_path,
            file_hash=a.file_hash,
            state="uploaded",
        )
        db.add(asset)

    if listing.state == ListingState.NEW:
        listing.state = ListingState.UPLOADING

    await db.commit()

    # Trigger the pipeline if listing just entered UPLOADING
    if listing.state == ListingState.UPLOADING:
        try:
            client = get_temporal_client()
            await client.start_pipeline(
                listing_id=str(listing.id),
                tenant_id=str(current_user.tenant_id),
                plan=tenant.plan,
            )
        except Exception:
            logger.exception("Pipeline trigger failed for listing %s", listing.id)
            listing.state = ListingState.FAILED
            await db.commit()

    return CreateAssetsResponse(
        count=len(body.assets),
        listing_state=listing.state.value,
    )


@router.get("/{listing_id}/assets", response_model=list[AssetResponse])
async def list_assets(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all assets associated with a listing, ordered by upload time."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    result = await db.execute(
        select(Asset).where(Asset.listing_id == listing.id).order_by(Asset.created_at)
    )
    assets = result.scalars().all()

    storage = get_storage()
    response = [AssetResponse.model_validate(a) for a in assets]

    # Batch generate presigned URLs in thread pool (S3 calls are sync/IO-bound)
    def _gen_url(file_path: str) -> str | None:
        try:
            return storage.presigned_url(file_path, expires_in=3600)
        except Exception:
            logger.warning("presigned_url_failed path=%s", file_path, exc_info=True)
            return None

    with ThreadPoolExecutor(max_workers=10) as pool:
        urls = list(pool.map(_gen_url, [a.file_path for a in assets]))

    for data, asset_obj, url in zip(response, assets, urls):
        # Use presigned URL if available, fall back to proxy_path
        data.thumbnail_url = url or asset_obj.proxy_path

    return response


@router.get("/{listing_id}/package")
async def get_package(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the AI-selected photo package for the listing, ordered by position."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    result = await db.execute(
        select(PackageSelection)
        .where(PackageSelection.listing_id == listing.id)
        .order_by(PackageSelection.position)
    )
    selections = result.scalars().all()
    return [
        {
            "asset_id": str(s.asset_id),
            "channel": s.channel,
            "position": s.position,
            "composite_score": s.composite_score,
            "selected_by": s.selected_by,
        }
        for s in selections
    ]


@router.post("/{listing_id}/package/reorder")
async def reorder_package(
    listing_id: uuid.UUID,
    body: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder photos in a package. Body: {"swaps": [{"from_position": 0, "to_position": 3}]}."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    reviewable = {ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW}
    if listing.state not in reviewable:
        raise HTTPException(status_code=409, detail="Listing is not in a reviewable state")

    swaps = body.swaps
    if not swaps:
        raise HTTPException(status_code=422, detail="No swaps provided")

    # Load all selections for this listing
    result = await db.execute(
        select(PackageSelection)
        .where(PackageSelection.listing_id == listing.id)
        .order_by(PackageSelection.position)
    )
    selections = {s.position: s for s in result.scalars().all()}

    # Load vision results for room labels
    from listingjet.models.vision_result import VisionResult
    vr_result = await db.execute(
        select(VisionResult).where(
            VisionResult.asset_id.in_([s.asset_id for s in selections.values()])
        )
    )
    vr_map = {vr.asset_id: vr for vr in vr_result.scalars().all()}

    swapped = 0
    for swap in swaps:
        from_pos = swap.get("from_position")
        to_pos = swap.get("to_position")
        if from_pos is None or to_pos is None:
            continue

        sel_from = selections.get(from_pos)
        sel_to = selections.get(to_pos)
        if not sel_from or not sel_to:
            continue

        # Swap positions
        sel_from.position, sel_to.position = sel_to.position, sel_from.position
        sel_from.selected_by = "human"
        sel_to.selected_by = "human"

        # Emit override events with room_label for learning agent
        from_vr = vr_map.get(sel_from.asset_id)
        to_vr = vr_map.get(sel_to.asset_id)

        await emit_event(
            session=db,
            event_type="package.override.swap_to",
            payload={
                "asset_id": str(sel_from.asset_id),
                "room_label": from_vr.room_label if from_vr else None,
                "from_position": to_pos,
                "to_position": from_pos,
            },
            tenant_id=str(current_user.tenant_id),
            listing_id=str(listing.id),
        )
        await emit_event(
            session=db,
            event_type="package.override.swap_from",
            payload={
                "asset_id": str(sel_to.asset_id),
                "room_label": to_vr.room_label if to_vr else None,
                "from_position": from_pos,
                "to_position": to_pos,
            },
            tenant_id=str(current_user.tenant_id),
            listing_id=str(listing.id),
        )
        swapped += 1

    await db.commit()
    return {"swaps_applied": swapped}


_EXPORTABLE_STATES = {ListingState.APPROVED, ListingState.EXPORTING, ListingState.DELIVERED}


@router.get("/{listing_id}/export", response_model=ExportResponse)
async def export_listing(
    listing_id: uuid.UUID,
    mode: ExportMode = ExportMode.marketing,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state not in _EXPORTABLE_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot export: listing is {listing.state.value}",
        )

    bundle_path = (
        listing.mls_bundle_path if mode == ExportMode.mls else listing.marketing_bundle_path
    )
    if not bundle_path:
        raise HTTPException(status_code=404, detail="Export not yet generated")

    storage = get_storage()
    expires_in = 900  # 15 minutes
    download_url = storage.presigned_url(bundle_path, expires_in=expires_in)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Record performance event for learning loop
    db.add(PerformanceEvent(
        tenant_id=current_user.tenant_id,
        listing_id=listing.id,
        signal_type="export_downloaded",
        value=1.0,
        source="user",
    ))
    await db.commit()

    return ExportResponse(
        listing_id=listing.id,
        mode=mode.value,
        download_url=download_url,
        expires_at=expires_at,
        bundle=BundleMetadata(
            includes_flyer=(mode == ExportMode.marketing),
            includes_social_posts=(mode == ExportMode.marketing),
        ),
    )


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


@router.get("/{listing_id}/activity")
async def listing_activity(
    listing_id: uuid.UUID,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the event audit trail for a listing, newest first."""
    from listingjet.models.event import Event

    # Verify listing belongs to tenant
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    limit = min(limit, 200)
    result = await db.execute(
        select(Event)
        .where(Event.listing_id == listing_id)
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "payload": e.payload,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Link import
# ---------------------------------------------------------------------------


class ImportLinkRequest(BaseModel):
    url: str


class ImportLinkResponse(BaseModel):
    import_id: uuid.UUID
    platform: str
    status: str


class ImportStatusResponse(BaseModel):
    import_id: uuid.UUID
    status: str
    platform: str
    total_files: int
    completed_files: int
    error_message: str | None


async def _run_link_import_background(
    listing_id: str,
    tenant_id: str,
    url: str,
    platform: str,
    import_job_id: str,
) -> None:
    """Background task that runs the link import activity."""
    from listingjet.activities.pipeline import LinkImportParams, run_link_import

    params = LinkImportParams(
        listing_id=listing_id,
        tenant_id=tenant_id,
        url=url,
        platform=platform,
        import_job_id=import_job_id,
    )
    await run_link_import(params)


@router.post("/{listing_id}/import-link", response_model=ImportLinkResponse)
async def import_from_link_endpoint(
    listing_id: uuid.UUID,
    body: ImportLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start importing photos from a third-party delivery link (Google Drive, Show & Tour)."""
    from listingjet.models.import_job import ImportJob
    from listingjet.services.link_import import detect_platform

    # Verify listing belongs to tenant
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    platform = detect_platform(body.url)
    if not platform:
        raise HTTPException(
            status_code=400,
            detail="Unsupported link. Supported platforms: Google Drive, Show & Tour.",
        )

    # Create ImportJob record
    job = ImportJob(
        id=uuid.uuid4(),
        listing_id=listing_id,
        tenant_id=current_user.tenant_id,
        url=body.url,
        platform=platform,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Fire-and-forget background task
    asyncio.create_task(
        _run_link_import_background(
            listing_id=str(listing_id),
            tenant_id=str(current_user.tenant_id),
            url=body.url,
            platform=platform,
            import_job_id=str(job.id),
        )
    )

    return ImportLinkResponse(
        import_id=job.id,
        platform=platform,
        status="started",
    )


@router.get("/{listing_id}/import-status/{import_id}", response_model=ImportStatusResponse)
async def get_import_status(
    listing_id: uuid.UUID,
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of a link-import job."""
    from listingjet.models.import_job import ImportJob

    # Verify listing belongs to tenant
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    job = await db.get(ImportJob, import_id)
    if not job or job.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Import job not found")

    return ImportStatusResponse(
        import_id=job.id,
        status=job.status,
        platform=job.platform,
        total_files=job.total_files or 0,
        completed_files=job.completed_files or 0,
        error_message=job.error_message,
    )


# --- Review Analytics ---


@router.get("/review/analytics")
async def get_review_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review override rate and trust score analytics for the tenant.

    Returns:
      - override_rate: % of photos changed by humans across all reviewed listings
      - override_rate_by_month: monthly trend showing if the AI is improving
      - avg_trust_score: average AI trust score across reviewed listings
      - total_reviewed: number of listings that went through human review
      - total_auto_approved: number of listings auto-approved
    """
    tenant_id = current_user.tenant_id

    # Total selections and human overrides
    total_selections = (await db.execute(
        select(func.count(PackageSelection.id))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            Listing.state.in_([
                ListingState.APPROVED, ListingState.DELIVERED,
                ListingState.EXPORTING,
            ]),
        )
    )).scalar() or 0

    human_overrides = (await db.execute(
        select(func.count(PackageSelection.id))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            PackageSelection.selected_by == "human",
            Listing.state.in_([
                ListingState.APPROVED, ListingState.DELIVERED,
                ListingState.EXPORTING,
            ]),
        )
    )).scalar() or 0

    override_rate = (human_overrides / total_selections * 100) if total_selections > 0 else 0.0

    # Average trust score
    avg_trust = (await db.execute(
        select(func.avg(PackageSelection.composite_score))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            Listing.state.in_([
                ListingState.APPROVED, ListingState.DELIVERED,
                ListingState.EXPORTING,
            ]),
        )
    )).scalar() or 0.0

    # Total reviewed (went through human review) vs auto-approved
    from listingjet.models.event import Event
    total_reviewed = (await db.execute(
        select(func.count(func.distinct(Event.listing_id))).where(
            Event.tenant_id == tenant_id,
            Event.event_type == "listing.review_started",
        )
    )).scalar() or 0

    total_auto_approved = (await db.execute(
        select(func.count(func.distinct(Event.listing_id))).where(
            Event.tenant_id == tenant_id,
            Event.event_type == "packaging.completed",
            func.cast(Event.payload["auto_approved"], sa.Boolean).is_(True),
        )
    )).scalar() or 0

    # Monthly override rate trend (last 6 months)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    monthly_result = await db.execute(
        select(
            extract("year", PackageSelection.created_at).label("year"),
            extract("month", PackageSelection.created_at).label("month"),
            func.count(PackageSelection.id).label("total"),
            func.sum(
                case((PackageSelection.selected_by == "human", 1), else_=0)
            ).label("overrides"),
        )
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            PackageSelection.created_at >= six_months_ago,
            Listing.state.in_([
                ListingState.APPROVED, ListingState.DELIVERED,
                ListingState.EXPORTING,
            ]),
        )
        .group_by("year", "month")
        .order_by("year", "month")
    )

    override_trend = []
    for row in monthly_result:
        month_total = row.total or 0
        month_overrides = row.overrides or 0
        rate = (month_overrides / month_total * 100) if month_total > 0 else 0.0
        override_trend.append({
            "month": f"{int(row.year)}-{int(row.month):02d}",
            "override_rate": round(rate, 1),
            "total_selections": month_total,
            "human_overrides": month_overrides,
        })

    return {
        "override_rate": round(override_rate, 1),
        "avg_trust_score": round(float(avg_trust), 1),
        "total_selections": total_selections,
        "human_overrides": human_overrides,
        "total_reviewed": total_reviewed,
        "total_auto_approved": total_auto_approved,
        "override_trend": override_trend,
    }
