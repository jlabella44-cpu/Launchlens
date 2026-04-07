import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.listings import (
    CreateListingRequest,
    ListingResponse,
    UpdateListingRequest,
)
from listingjet.database import get_db
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.asset import Asset
from listingjet.models.cma_report import CMAReport
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.event import Event
from listingjet.models.health_score_history import HealthScoreHistory
from listingjet.models.import_job import ImportJob
from listingjet.models.listing import Listing, ListingState
from listingjet.models.listing_event import ListingEvent
from listingjet.models.listing_health_score import ListingHealthScore
from listingjet.models.listing_microsite import ListingMicrosite
from listingjet.models.outbox import Outbox
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.property_data import PropertyData
from listingjet.models.scoring_event import ScoringEvent
from listingjet.models.social_content import SocialContent
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.models.video_asset import VideoAsset
from listingjet.services.endpoint_rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", status_code=201, response_model=ListingResponse)
async def create_listing(
    body: CreateListingRequest,
    _rl=Depends(rate_limit(20, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new listing. Deducts one credit for credit-billed tenants (402 if insufficient).

    For legacy tenants, enforces the monthly listing quota for the current plan.
    Accepts an optional Idempotency-Key header to prevent duplicate creation.
    """
    from listingjet.services.credits import InsufficientCreditsError
    from listingjet.services.listing_creation import ListingCreationService, ListingQuotaExceededError

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    svc = ListingCreationService()
    try:
        listing = await svc.create(
            session=db,
            tenant=tenant,
            tenant_id=current_user.tenant_id,
            address=body.address.model_dump(exclude_none=True),
            metadata=body.metadata.model_dump(exclude_none=True) if body.metadata else {},
            idempotency_key=body.idempotency_key,
        )
    except InsufficientCreditsError:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {tenant.per_listing_credit_cost} credit(s). Purchase more to continue.",
        )
    except ListingQuotaExceededError as e:
        raise HTTPException(
            status_code=403,
            detail=f"Monthly listing limit reached ({e.current_count}). Upgrade your plan for more.",
        )

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
    - **page_size**: items per page (default 50, max 50)
    """
    page_size = min(page_size, 50)
    offset = (max(page, 1) - 1) * page_size

    base_query = select(Listing).where(Listing.tenant_id == current_user.tenant_id)

    # Hide cancelled listings unless explicitly requested
    if state != "cancelled":
        base_query = base_query.where(Listing.state != ListingState.CANCELLED)

    # Hide draft listings unless explicitly requested
    if state != "draft":
        base_query = base_query.where(Listing.state != ListingState.DRAFT)

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

    # Fetch thumbnails: hero photo (PackageSelection pos 0) or first uploaded asset
    listing_ids = [item.id for item in listings]
    thumbnail_map: dict[uuid.UUID, str | None] = {}
    if listing_ids:
        try:
            from sqlalchemy import and_

            from listingjet.services.storage import get_storage
            storage = get_storage()

            # Hero photos from PackageSelection
            hero_rows = (await db.execute(
                select(PackageSelection.listing_id, Asset.file_path)
                .join(Asset, PackageSelection.asset_id == Asset.id)
                .where(PackageSelection.listing_id.in_(listing_ids), PackageSelection.position == 0)
            )).all()
            for lid, fpath in hero_rows:
                try:
                    thumbnail_map[lid] = storage.presigned_url(fpath, expires_in=3600)
                except Exception:
                    pass

            # Fallback: first asset for listings without hero
            missing = [lid for lid in listing_ids if lid not in thumbnail_map]
            if missing:
                subq = (
                    select(Asset.listing_id, func.min(Asset.created_at).label("min_created"))
                    .where(Asset.listing_id.in_(missing))
                    .group_by(Asset.listing_id)
                    .subquery()
                )
                first_assets = (await db.execute(
                    select(Asset.listing_id, Asset.file_path)
                    .join(subq, and_(Asset.listing_id == subq.c.listing_id, Asset.created_at == subq.c.min_created))
                )).all()
                for lid, fpath in first_assets:
                    if lid not in thumbnail_map:
                        try:
                            thumbnail_map[lid] = storage.presigned_url(fpath, expires_in=3600)
                        except Exception:
                            pass
        except Exception:
            logger.exception("thumbnail_fetch_failed")

    items = [
        ListingResponse.from_orm_listing(listing, thumbnail_url=thumbnail_map.get(listing.id))
        for listing in listings
    ]

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
    """Return a single listing by ID. Returns 404 if not found or not owned by the current tenant."""
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
    """Update a listing's address or metadata fields. Only provided fields are changed."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if body.address is not None:
        listing.address = body.address.model_dump(exclude_none=True)

    # Capture old price before overwriting metadata
    old_price = (listing.metadata_ or {}).get("price") if body.metadata is not None else None

    if body.metadata is not None:
        listing.metadata_ = body.metadata.model_dump(exclude_none=True)

    # Auto-detect price change for social reminders
    if body.metadata is not None:
        new_meta = body.metadata.model_dump(exclude_none=True)
        new_price = new_meta.get("price")
        if new_price is not None and old_price is not None and new_price != old_price:
            price_event = ListingEvent(
                tenant_id=current_user.tenant_id,
                listing_id=listing_id,
                event_type="price_change",
                event_data={"old_price": old_price, "new_price": new_price},
            )
            db.add(price_event)

    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)


@router.delete("/{listing_id}", status_code=200)
async def delete_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a listing and its associated assets.

    Credits are refunded only if the pipeline hasn't done significant work
    (states: NEW, UPLOADING, ANALYZING, FAILED). Once a listing reaches
    AWAITING_REVIEW or beyond, no refund is issued.
    """
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Refund credits only if no significant pipeline work was done
    credits_refunded = 0
    refundable_states = {ListingState.DRAFT, ListingState.NEW, ListingState.UPLOADING, ListingState.ANALYZING, ListingState.FAILED}
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant and tenant.billing_model == "credit" and listing.credit_cost and listing.state in refundable_states:
        from listingjet.services.credits import CreditService
        credit_svc = CreditService()
        txn = await credit_svc.refund_credits(db, current_user.tenant_id, str(listing_id))
        if txn:
            credits_refunded = txn.amount

    # Delete all related records
    for model in (
        VideoAsset,
        SocialContent,
        ListingEvent,
        Event,
        HealthScoreHistory,
        ListingHealthScore,
        ScoringEvent,
        PerformanceEvent,
        ListingMicrosite,
        PropertyData,
        CMAReport,
        DollhouseScene,
        ImportJob,
        AddonPurchase,
        Outbox,
        PackageSelection,
        Asset,
    ):
        await db.execute(sa_delete(model).where(model.listing_id == listing_id))
    await db.delete(listing)
    await db.commit()

    return {"listing_id": str(listing_id), "deleted": True, "credits_refunded": credits_refunded}


@router.get("/{listing_id}/dollhouse")
async def get_dollhouse(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the 3-D dollhouse scene JSON generated from the listing's floorplan asset."""
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
