"""Microsite API — generate and retrieve single-property landing pages."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.listing import Listing
from listingjet.models.listing_microsite import ListingMicrosite
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter()


class MicrositeResponse(BaseModel):
    listing_id: uuid.UUID
    microsite_url: str
    qr_code_url: str | None
    status: str
    generated_at: str


@router.post("/{listing_id}/microsite", status_code=202)
async def generate_microsite(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(3, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a single-property microsite with photo gallery, details, video, and QR code."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    from listingjet.agents.base import AgentContext
    from listingjet.agents.microsite_generator import MicrositeGeneratorAgent

    agent = MicrositeGeneratorAgent()
    ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id))
    result = await agent.execute(ctx)

    return {"listing_id": str(listing_id), "status": "ready", **result}


@router.get("/{listing_id}/microsite")
async def get_microsite(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the microsite URL and QR code for a listing."""
    microsite = (await db.execute(
        select(ListingMicrosite).where(
            ListingMicrosite.listing_id == listing_id,
            ListingMicrosite.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()

    if not microsite:
        raise HTTPException(status_code=404, detail="No microsite found. Generate one first.")

    storage = get_storage()
    return MicrositeResponse(
        listing_id=microsite.listing_id,
        microsite_url=storage.presigned_url(microsite.s3_key, expires_in=604800),
        qr_code_url=storage.presigned_url(microsite.qr_code_s3_key, expires_in=604800) if microsite.qr_code_s3_key else None,
        status=microsite.status,
        generated_at=microsite.generated_at.isoformat(),
    )


@router.delete("/{listing_id}/microsite")
async def delete_microsite(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a listing's microsite."""
    microsite = (await db.execute(
        select(ListingMicrosite).where(
            ListingMicrosite.listing_id == listing_id,
            ListingMicrosite.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()

    if not microsite:
        raise HTTPException(status_code=404, detail="No microsite found")

    await db.delete(microsite)
    await db.commit()
    return {"listing_id": str(listing_id), "deleted": True}
