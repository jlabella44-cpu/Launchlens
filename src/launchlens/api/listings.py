import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user
from launchlens.api.schemas.assets import (
    AssetResponse,
    CreateAssetsRequest,
    CreateAssetsResponse,
)
from launchlens.api.schemas.listings import (
    BundleMetadata,
    CreateListingRequest,
    ExportMode,
    ExportResponse,
    ListingResponse,
    UpdateListingRequest,
    VideoUploadRequest,
)
from launchlens.database import get_db
from launchlens.models.asset import Asset
from launchlens.models.dollhouse_scene import DollhouseScene
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.models.tenant import Tenant
from launchlens.models.user import User
from launchlens.models.video_asset import VideoAsset
from launchlens.services.plan_limits import check_asset_quota, check_listing_quota, get_limits
from launchlens.services.storage import StorageService
from launchlens.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", status_code=201, response_model=ListingResponse)
async def create_listing(
    body: CreateListingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check monthly listing quota
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.tenant_id == current_user.tenant_id,
            Listing.created_at >= month_start,
        )
    )
    current_count = count_result.scalar() or 0

    if not check_listing_quota(tenant.plan, current_count):
        raise HTTPException(
            status_code=403,
            detail=f"Monthly listing limit reached ({current_count}). Upgrade your plan for more.",
        )

    listing = Listing(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        address=body.address,
        metadata_=body.metadata,
        state=ListingState.NEW,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)


@router.get("", response_model=list[ListingResponse])
async def list_listings(
    state: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List listings with optional filters.
    - state: filter by listing state (e.g. "approved", "delivered")
    - search: search in address fields (street, city)
    - limit/offset: pagination (default 50, max 200)
    """
    limit = min(limit, 200)
    query = select(Listing).where(Listing.tenant_id == current_user.tenant_id)

    if state:
        query = query.where(Listing.state == state)

    if search:
        # Search in JSONB address field — street or city contains search term
        search_pattern = f"%{search}%"
        query = query.where(
            Listing.address["street"].astext.ilike(search_pattern)
            | Listing.address["city"].astext.ilike(search_pattern)
        )

    query = query.order_by(Listing.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    listings = result.scalars().all()
    return [ListingResponse.from_orm_listing(listing) for listing in listings]


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: uuid.UUID,
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
    return ListingResponse.from_orm_listing(listing)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: uuid.UUID,
    body: UpdateListingRequest,
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

    if body.address is not None:
        listing.address = body.address
    if body.metadata is not None:
        listing.metadata_ = body.metadata

    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)


@router.get("/{listing_id}/dollhouse")
async def get_dollhouse(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    scene = (await db.execute(
        select(DollhouseScene)
        .where(DollhouseScene.listing_id == listing.id)
        .order_by(DollhouseScene.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Dollhouse not ready — upload a floorplan and run the pipeline")

    return {
        "scene_json": scene.scene_json,
        "room_count": scene.room_count,
        "created_at": scene.created_at.isoformat(),
    }


@router.post("/{listing_id}/upload-urls")
async def get_upload_urls(
    listing_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate presigned PUT URLs for direct browser-to-S3 upload."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    filenames = body.get("filenames", [])
    if not filenames or not isinstance(filenames, list):
        raise HTTPException(status_code=400, detail="filenames must be a non-empty list")
    if len(filenames) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch")

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    storage = StorageService()
    urls = []
    for fname in filenames:
        ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {fname}. Allowed: {ALLOWED_EXTENSIONS}",
            )
        content_type = "image/png" if ext == ".png" else "image/jpeg"
        key = f"listings/{listing_id}/photos/{fname}"
        url = storage.presigned_upload_url(key, content_type=content_type)
        urls.append({"filename": fname, "key": key, "upload_url": url, "content_type": content_type})

    return {"urls": urls}


@router.post("/{listing_id}/assets", status_code=201, response_model=CreateAssetsResponse)
async def register_assets(
    listing_id: uuid.UUID,
    body: CreateAssetsRequest,
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
    return result.scalars().all()


@router.get("/{listing_id}/package")
async def get_package(
    listing_id: uuid.UUID,
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


@router.post("/{listing_id}/review")
async def start_review(
    listing_id: uuid.UUID,
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

    if listing.state != ListingState.AWAITING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot start review: listing is {listing.state.value}")

    listing.state = ListingState.IN_REVIEW
    await db.commit()
    await db.refresh(listing)
    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/approve")
async def approve_listing(
    listing_id: uuid.UUID,
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

    if listing.state != ListingState.IN_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot approve: listing is {listing.state.value}")

    listing.state = ListingState.APPROVED
    await db.commit()
    await db.refresh(listing)

    # Signal the waiting workflow to continue post-approval pipeline
    try:
        client = get_temporal_client()
        await client.signal_review_completed(listing_id=str(listing.id))
    except Exception:
        logger.exception("Review signal failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/reject")
async def reject_listing(
    listing_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a listing with a reason code. Transitions state to FAILED."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    rejectable = {ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW}
    if listing.state not in rejectable:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: listing is {listing.state.value}",
        )

    valid_reasons = {"quality", "incomplete", "non_compliant", "other"}
    reason = body.get("reason", "")
    if reason not in valid_reasons:
        raise HTTPException(status_code=400, detail=f"Invalid reason. Must be one of: {valid_reasons}")

    listing.state = ListingState.FAILED
    await db.commit()
    await db.refresh(listing)

    # Emit audit event
    try:
        from launchlens.services.events import emit_event
        await emit_event(
            session=db,
            event_type="listing.rejected",
            payload={"reason": reason, "detail": body.get("detail", "")},
            tenant_id=current_user.tenant_id,
            listing_id=listing.id,
        )
    except Exception:
        logger.exception("Failed to emit rejection event for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.get("/{listing_id}/pipeline-status")
async def get_pipeline_status(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return per-step pipeline progress for a listing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    from launchlens.models.event import Event

    result = await db.execute(
        select(Event)
        .where(Event.listing_id == listing_id)
        .order_by(Event.created_at)
    )
    events = result.scalars().all()

    # Build step list from known pipeline stages
    pipeline_steps = [
        "ingestion", "vision_tier1", "vision_tier2", "coverage",
        "floorplan", "packaging", "compliance", "review",
        "content", "brand", "social_content", "chapters",
        "social_cuts", "mls_export", "watermark", "distribution",
    ]

    completed_steps = set()
    step_times = {}
    for evt in events:
        et = evt.event_type
        if et.endswith(".completed") or et.endswith(".done"):
            step_name = et.rsplit(".", 1)[0]
            completed_steps.add(step_name)
            step_times[step_name] = evt.created_at.isoformat()

    state_val = listing.state.value if hasattr(listing.state, "value") else listing.state
    steps = []
    for step in pipeline_steps:
        if step in completed_steps:
            status = "completed"
        elif state_val in ("delivered", "failed"):
            status = "skipped"
        else:
            status = "pending"
        steps.append({
            "name": step,
            "status": status,
            "completed_at": step_times.get(step),
            "progress": None,
        })

    # Mark current active step
    for s in steps:
        if s["status"] == "pending":
            if state_val not in ("new", "awaiting_review", "in_review", "delivered", "failed"):
                s["status"] = "in_progress"
            break

    return {
        "listing_id": str(listing.id),
        "state": state_val,
        "steps": steps,
    }


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

    storage = StorageService()
    expires_in = 3600
    download_url = storage.presigned_url(bundle_path, expires_in=expires_in)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

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


@router.post("/{listing_id}/compliance")
async def run_compliance_scan(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run photo compliance scan on a listing's packaged photos. Returns per-photo report."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    scannable = {
        ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW,
        ListingState.APPROVED, ListingState.EXPORTING, ListingState.DELIVERED,
    }
    if listing.state not in scannable:
        raise HTTPException(
            status_code=409,
            detail=f"Compliance scan requires packaged photos. Current state: {listing.state.value}",
        )

    from launchlens.agents.base import AgentContext
    from launchlens.agents.photo_compliance import PhotoComplianceAgent

    agent = PhotoComplianceAgent()
    ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id))
    report = await agent.execute(ctx)
    return report


@router.get("/{listing_id}/activity")
async def listing_activity(
    listing_id: uuid.UUID,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the event audit trail for a listing, newest first."""
    from launchlens.models.event import Event

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
