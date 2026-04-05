import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin, require_superadmin
from listingjet.api.schemas.admin import (
    AdminListingResponse,
    AdminUpdateListingRequest,
)
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.audit import audit_log

router = APIRouter()


@router.get("/listings", response_model=list[AdminListingResponse])
async def admin_list_listings(
    state: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all listings across tenants with filters."""
    query = select(
        Listing, Tenant.name.label("tenant_name")
    ).join(Tenant, Listing.tenant_id == Tenant.id)

    if state:
        try:
            ls = ListingState(state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
        query = query.where(Listing.state == ls)
    if tenant_id:
        query = query.where(Listing.tenant_id == tenant_id)
    if search:
        query = query.where(
            func.cast(Listing.address, String).ilike(f"%{search}%")
        )

    query = query.order_by(Listing.updated_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    # Fetch thumbnails for admin listing rows
    listing_ids = [listing.id for listing, _ in rows]
    thumbnail_map: dict = {}
    if listing_ids:
        try:
            from listingjet.services.storage import get_storage
            storage = get_storage()
            subq = (
                select(Asset.listing_id, func.min(Asset.created_at).label("min_created"))
                .where(Asset.listing_id.in_(listing_ids))
                .group_by(Asset.listing_id)
                .subquery()
            )
            from sqlalchemy import and_
            first_assets = (await db.execute(
                select(Asset.listing_id, Asset.file_path)
                .join(subq, and_(
                    Asset.listing_id == subq.c.listing_id,
                    Asset.created_at == subq.c.min_created,
                ))
            )).all()
            for lid, fpath in first_assets:
                try:
                    thumbnail_map[lid] = storage.presigned_url(fpath, expires_in=3600)
                except Exception:
                    pass
        except Exception:
            pass

    return [
        AdminListingResponse(
            id=listing.id,
            tenant_id=listing.tenant_id,
            tenant_name=tenant_name,
            address=listing.address or {},
            metadata=listing.metadata_ or {},
            state=listing.state.value if hasattr(listing.state, "value") else listing.state,
            analysis_tier=listing.analysis_tier or "standard",
            credit_cost=listing.credit_cost,
            is_demo=listing.is_demo,
            thumbnail_url=thumbnail_map.get(listing.id),
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )
        for listing, tenant_name in rows
    ]


@router.patch("/listings/{listing_id}", response_model=AdminListingResponse)
async def admin_update_listing(
    listing_id: uuid.UUID,
    body: AdminUpdateListingRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Update a listing's address, metadata, or state (for fixing errors)."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    changes = {}
    if body.address is not None:
        changes["address"] = {"old": listing.address, "new": body.address}
        listing.address = body.address
    if body.metadata is not None:
        changes["metadata"] = {"old": listing.metadata_, "new": body.metadata}
        listing.metadata_ = body.metadata
    if body.state is not None:
        try:
            new_state = ListingState(body.state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {body.state}")
        changes["state"] = {"old": listing.state.value, "new": body.state}
        listing.state = new_state

    await audit_log(
        db, admin_user.id, "update", "listing", str(listing_id),
        tenant_id=listing.tenant_id, details=changes,
    )
    await db.commit()
    await db.refresh(listing)

    tenant = await db.get(Tenant, listing.tenant_id)
    return AdminListingResponse(
        id=listing.id,
        tenant_id=listing.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        address=listing.address or {},
        metadata=listing.metadata_ or {},
        state=listing.state.value if hasattr(listing.state, "value") else listing.state,
        analysis_tier=listing.analysis_tier or "standard",
        credit_cost=listing.credit_cost,
        is_demo=listing.is_demo,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


@router.post("/listings/{listing_id}/retry")
async def admin_retry_listing(
    listing_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Admin retry of a failed/timed-out listing (cross-tenant)."""
    import logging

    logger = logging.getLogger(__name__)

    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    retryable = {ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
    if listing.state not in retryable:
        raise HTTPException(
            status_code=409,
            detail=f"Can only retry failed listings, current state: {listing.state.value}",
        )

    previous_state = listing.state.value
    tenant = await db.get(Tenant, listing.tenant_id)

    # Start the workflow BEFORE committing the state change
    try:
        from listingjet.temporal_client import get_temporal_client

        client = get_temporal_client()
        await client.start_pipeline(
            listing_id=str(listing.id),
            tenant_id=str(listing.tenant_id),
            plan=tenant.plan if tenant else "starter",
        )
    except Exception:
        logger.exception("Admin pipeline retry trigger failed for listing %s", listing.id)
        raise HTTPException(
            status_code=502,
            detail="Failed to start pipeline — listing state unchanged",
        )

    # Only update state after workflow is confirmed running
    listing.state = ListingState.UPLOADING
    await audit_log(
        db, admin_user.id, "retry_listing", "listing", str(listing_id),
        tenant_id=listing.tenant_id,
        details={"previous_state": previous_state},
    )
    await db.commit()

    return {"listing_id": str(listing.id), "state": "uploading"}
