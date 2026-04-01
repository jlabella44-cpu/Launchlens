import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.assets import (
    AssetResponse,
    CreateAssetsRequest,
    CreateAssetsResponse,
)
from listingjet.api.schemas.listings import (
    ActionResponse,
    BundleMetadata,
    CancelResponse,
    CreateListingRequest,
    ExportMode,
    ExportResponse,
    ListingResponse,
    PipelineStatusResponse,
    RejectRequest,
    ReorderRequest,
    UpdateListingRequest,
    UploadUrlsRequest,
    VideoUploadRequest,
)
from listingjet.database import get_db
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.models.video_asset import VideoAsset
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event
from listingjet.services.metrics import record_review_turnaround
from listingjet.services.plan_limits import check_asset_quota, check_listing_quota, get_limits
from listingjet.services.storage import StorageService
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", status_code=201, response_model=ListingResponse)
async def create_listing(
    body: CreateListingRequest,
    _rl=Depends(rate_limit(20, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    listing = Listing(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        address=body.address,
        metadata_=body.metadata,
        state=ListingState.NEW,
    )

    if tenant.billing_model == "credit":
        # Credit-based billing: deduct credits
        from listingjet.services.credits import CreditService, InsufficientCreditsError
        credit_svc = CreditService()
        cost = tenant.per_listing_credit_cost
        try:
            await credit_svc.deduct_credits(
                db, tenant.id, cost,
                transaction_type="listing_debit",
                reference_type="listing",
                reference_id=str(listing.id),
                description=f"Listing at {body.address.get('street', 'new listing')}",
            )
            listing.credit_cost = cost
        except InsufficientCreditsError:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {cost} credit(s). Purchase more to continue.",
            )
    else:
        # Legacy billing: monthly quota check
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

    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)


@router.get("")
async def list_listings(
    state: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    _rl=Depends(rate_limit(60, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List listings with optional filters and pagination.

    - **state**: filter by listing state (e.g. "approved", "delivered")
    - **search**: search in address fields (street, city)
    - **page**: page number (default 1)
    - **page_size**: items per page (default 50, max 200)
    """
    page_size = min(page_size, 200)
    offset = (max(page, 1) - 1) * page_size

    base_query = select(Listing).where(Listing.tenant_id == current_user.tenant_id)

    if state:
        try:
            validated_state = ListingState(state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid listing state: {state}")
        base_query = base_query.where(Listing.state == validated_state)

    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            Listing.address["street"].astext.ilike(search_pattern)
            | Listing.address["city"].astext.ilike(search_pattern)
        )

    # Count total
    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    # Fetch page
    query = base_query.order_by(Listing.created_at.desc()).limit(page_size).offset(offset)
    result = await db.execute(query)
    listings = result.scalars().all()
    items = [ListingResponse.from_orm_listing(listing) for listing in listings]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }


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
    storage = StorageService()
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


@router.post("/{listing_id}/review", response_model=ActionResponse)
async def start_review(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state != ListingState.AWAITING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot start review: listing is {listing.state.value}")

    listing.state = ListingState.IN_REVIEW
    await emit_event(
        session=db,
        event_type="listing.review_started",
        payload={"user_id": str(current_user.id)},
        tenant_id=str(current_user.tenant_id),
        listing_id=str(listing.id),
    )
    await db.commit()
    await db.refresh(listing)
    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/approve", response_model=ActionResponse)
async def approve_listing(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state != ListingState.IN_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot approve: listing is {listing.state.value}")

    # Record review turnaround time (time since last state change, approx AWAITING_REVIEW)
    if listing.updated_at:
        turnaround = (datetime.now(timezone.utc) - listing.updated_at).total_seconds()
        record_review_turnaround(turnaround)

    listing.state = ListingState.APPROVED
    await db.commit()
    await db.refresh(listing)

    # Signal the waiting workflow to continue post-approval pipeline
    try:
        client = get_temporal_client()
        await client.signal_review_completed(listing_id=str(listing.id))
    except Exception:
        logger.exception("Review signal failed for listing %s", listing.id)

    # Send REVIEW_APPROVED email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        from listingjet.services.notifications import _listing_address_str
        address = _listing_address_str(listing)
        email_svc = get_email_service()
        email_svc.send_notification(
            current_user.email,
            "review_approved",
            name=current_user.name or "there",
            address=address,
        )
    except Exception:
        logger.exception("review_approved email failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/reject", response_model=ActionResponse)
async def reject_listing(
    listing_id: uuid.UUID,
    body: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a listing with a reason code. Transitions state to FAILED."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
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
    if body.reason not in valid_reasons:
        raise HTTPException(status_code=400, detail=f"Invalid reason. Must be one of: {valid_reasons}")

    listing.state = ListingState.FAILED

    # Emit event BEFORE commit — outbox atomicity
    from listingjet.services.events import emit_event
    await emit_event(
        session=db,
        event_type="listing.rejected",
        payload={"reason": body.reason, "detail": body.detail},
        tenant_id=str(current_user.tenant_id),
        listing_id=str(listing.id),
    )

    await db.commit()
    await db.refresh(listing)

    # Send REVIEW_REJECTED email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        from listingjet.services.notifications import _listing_address_str
        address = _listing_address_str(listing)
        email_svc = get_email_service()
        email_svc.send_notification(
            current_user.email,
            "review_rejected",
            name=current_user.name or "there",
            address=address,
            reason=body.reason,
            detail=body.detail or "",
        )
    except Exception:
        logger.exception("review_rejected email failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/retry")
async def retry_pipeline(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a failed listing and re-trigger the pipeline."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    retryable = {ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
    if listing.state not in retryable:
        raise HTTPException(
            status_code=409,
            detail=f"Can only retry failed listings, current state: {listing.state.value}",
        )

    listing.state = ListingState.UPLOADING
    tenant = await db.get(Tenant, current_user.tenant_id)
    await db.commit()

    try:
        client = get_temporal_client()
        await client.start_pipeline(
            listing_id=str(listing.id),
            tenant_id=str(current_user.tenant_id),
            plan=tenant.plan if tenant else "starter",
        )
    except Exception:
        logger.exception("Pipeline retry trigger failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": "uploading"}


@router.post("/{listing_id}/cancel", response_model=CancelResponse)
async def cancel_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a listing and refund credits if using credit billing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    cancellable = {ListingState.NEW, ListingState.UPLOADING, ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
    if listing.state not in cancellable:
        raise HTTPException(409, f"Cannot cancel: listing is {listing.state.value}")

    credits_refunded = 0
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant and tenant.billing_model == "credit" and listing.credit_cost:
        from listingjet.services.credits import CreditService
        credit_svc = CreditService()
        txn = await credit_svc.refund_credits(db, current_user.tenant_id, str(listing_id))
        if txn:
            credits_refunded = txn.amount

    listing.state = ListingState.FAILED  # reuse FAILED state for cancelled
    await db.commit()

    return {"listing_id": str(listing.id), "state": listing.state.value, "credits_refunded": credits_refunded}


@router.get("/{listing_id}/pipeline-status", response_model=PipelineStatusResponse)
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

    from listingjet.models.event import Event

    result = await db.execute(
        select(Event)
        .where(Event.listing_id == listing_id)
        .order_by(Event.created_at)
        .limit(500)
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

    # Engagement prediction + features — only compute for packaged listings (expensive)
    engagement_score = None
    detected_features = []
    packaged_states = {"awaiting_review", "in_review", "approved", "exporting", "delivered"}
    if state_val in packaged_states:
        from listingjet.models.vision_result import VisionResult
        from listingjet.services.engagement_score import predict_engagement
        from listingjet.services.feature_tags import extract_features

        vision_results = (await db.execute(
            select(VisionResult)
            .join(Asset, VisionResult.asset_id == Asset.id)
            .where(Asset.listing_id == listing_id, VisionResult.tier == 1)
        )).scalars().all()

        engagement_score = predict_engagement(vision_results)
        detected_features = extract_features(vision_results)

    return {
        "listing_id": str(listing.id),
        "state": state_val,
        "steps": steps,
        "engagement_score": engagement_score,
        "detected_features": detected_features,
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

    from listingjet.agents.base import AgentContext
    from listingjet.agents.photo_compliance import PhotoComplianceAgent

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
