"""Listing events router — create events, list events, mark platforms as posted."""
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import CreateListingEventRequest, ListingEventResponse, MarkPostedRequest
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.listing_event import ListingEvent
from listingjet.models.user import User
from listingjet.services.social_reminder import SocialReminderService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/{listing_id}/events", status_code=201, response_model=ListingEventResponse)
async def create_listing_event(
    listing_id: uuid.UUID, body: CreateListingEventRequest,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    event = ListingEvent(
        tenant_id=current_user.tenant_id, listing_id=listing_id,
        event_type=body.event_type, event_data=body.event_data,
    )
    db.add(event)
    await db.flush()

    address = listing.address.get("street", "your listing")
    svc = SocialReminderService()
    svc.create_notification(
        session=db, user_id=current_user.id, tenant_id=current_user.tenant_id,
        listing_id=listing_id, event_type=body.event_type, address=address,
    )
    event.notified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(event)

    try:
        await svc.send_email_reminder(
            to_email=current_user.email, listing_id=listing_id, event_id=event.id,
            event_type=body.event_type, address=address,
        )
    except Exception:
        logger.exception("social reminder email failed for event %s", event.id)

    return ListingEventResponse.model_validate(event)

@router.get("/{listing_id}/events", response_model=list[ListingEventResponse])
async def list_listing_events(
    listing_id: uuid.UUID, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    result = await db.execute(
        select(ListingEvent).where(ListingEvent.listing_id == listing_id).order_by(ListingEvent.created_at.desc())
    )
    return [ListingEventResponse.model_validate(e) for e in result.scalars().all()]

@router.patch("/{listing_id}/events/{event_id}/posted", response_model=ListingEventResponse)
async def mark_posted(
    listing_id: uuid.UUID, event_id: uuid.UUID, body: MarkPostedRequest,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    event = (await db.execute(
        select(ListingEvent).where(
            ListingEvent.id == event_id, ListingEvent.listing_id == listing_id,
            ListingEvent.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    platforms = list(event.posted_platforms)
    if body.platform not in platforms:
        platforms.append(body.platform)
        event.posted_platforms = platforms
    await db.commit()
    await db.refresh(event)
    return ListingEventResponse.model_validate(event)
