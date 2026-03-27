import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from launchlens.database import get_db
from launchlens.models.listing import Listing, ListingState
from launchlens.models.user import User
from launchlens.api.deps import get_current_user
from launchlens.api.schemas.listings import (
    CreateListingRequest, UpdateListingRequest, ListingResponse,
)

router = APIRouter()


@router.post("", status_code=201, response_model=ListingResponse)
async def create_listing(
    body: CreateListingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing)
        .where(Listing.tenant_id == current_user.tenant_id)
        .order_by(Listing.created_at.desc())
    )
    listings = result.scalars().all()
    return [ListingResponse.from_orm_listing(l) for l in listings]


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
