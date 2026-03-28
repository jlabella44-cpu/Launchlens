"""Add-on management API — catalog, per-listing activation."""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user
from launchlens.api.schemas.addons import ActivateAddonRequest, AddonPurchaseResponse, AddonResponse
from launchlens.database import get_db
from launchlens.models.addon_catalog import AddonCatalog
from launchlens.models.addon_purchase import AddonPurchase
from launchlens.models.listing import Listing, ListingState
from launchlens.models.user import User
from launchlens.services.credits import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[AddonResponse])
async def list_addons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AddonCatalog).where(AddonCatalog.is_active.is_(True))
    )
    return result.scalars().all()


@router.post("/listings/{listing_id}/addons", response_model=AddonPurchaseResponse)
async def activate_addon(
    listing_id: uuid.UUID,
    body: ActivateAddonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify listing ownership
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Listing not found")

    # Can only add add-ons before pipeline starts generating
    if listing.state not in {ListingState.NEW, ListingState.UPLOADING, ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW}:
        raise HTTPException(409, f"Cannot add add-ons in state: {listing.state.value}")

    # Find the add-on
    addon = (await db.execute(
        select(AddonCatalog).where(AddonCatalog.slug == body.addon_slug, AddonCatalog.is_active.is_(True))
    )).scalar_one_or_none()
    if not addon:
        raise HTTPException(404, f"Add-on not found: {body.addon_slug}")

    # Check for duplicate
    existing = (await db.execute(
        select(AddonPurchase).where(
            AddonPurchase.listing_id == listing_id,
            AddonPurchase.addon_id == addon.id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Add-on already activated for this listing")

    # Deduct credits
    credit_svc = CreditService()
    try:
        txn = await credit_svc.deduct_credits(
            db, current_user.tenant_id, addon.credit_cost,
            transaction_type="addon_debit",
            reference_type="addon",
            reference_id=f"{listing_id}:{addon.slug}",
            description=f"{addon.name} for listing {listing_id}",
        )
    except InsufficientCreditsError:
        raise HTTPException(402, f"Insufficient credits. Need {addon.credit_cost}, check your balance.")

    purchase = AddonPurchase(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        addon_id=addon.id,
        credit_transaction_id=txn.id,
    )
    db.add(purchase)
    await db.commit()

    return AddonPurchaseResponse(
        id=purchase.id,
        addon_id=addon.id,
        addon_slug=addon.slug,
        addon_name=addon.name,
        status=purchase.status,
        created_at=purchase.created_at,
    )


@router.get("/listings/{listing_id}/addons", response_model=list[AddonPurchaseResponse])
async def list_listing_addons(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AddonPurchase, AddonCatalog)
        .join(AddonCatalog, AddonPurchase.addon_id == AddonCatalog.id)
        .where(
            AddonPurchase.listing_id == listing_id,
            AddonPurchase.tenant_id == current_user.tenant_id,
        )
    )
    return [
        AddonPurchaseResponse(
            id=purchase.id,
            addon_id=addon.id,
            addon_slug=addon.slug,
            addon_name=addon.name,
            status=purchase.status,
            created_at=purchase.created_at,
        )
        for purchase, addon in result.all()
    ]


@router.delete("/listings/{listing_id}/addons/{addon_slug}")
async def remove_addon(
    listing_id: uuid.UUID,
    addon_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an add-on and refund credits if pipeline hasn't started."""
    purchase = (await db.execute(
        select(AddonPurchase, AddonCatalog)
        .join(AddonCatalog, AddonPurchase.addon_id == AddonCatalog.id)
        .where(
            AddonPurchase.listing_id == listing_id,
            AddonPurchase.tenant_id == current_user.tenant_id,
            AddonCatalog.slug == addon_slug,
        )
    )).one_or_none()

    if not purchase:
        raise HTTPException(404, "Add-on not found on this listing")

    addon_purchase, addon = purchase

    listing = await db.get(Listing, listing_id)
    if listing and listing.state in {ListingState.NEW, ListingState.UPLOADING, ListingState.AWAITING_REVIEW}:
        # Refund credits
        credit_svc = CreditService()
        await credit_svc.add_credits(
            db, current_user.tenant_id, addon.credit_cost,
            transaction_type="refund",
            reference_type="addon",
            reference_id=f"{listing_id}:{addon_slug}:refund",
            description=f"Refund: {addon.name} removed from listing {listing_id}",
        )
        addon_purchase.status = "refunded"
    else:
        raise HTTPException(409, "Cannot remove add-on after pipeline has started processing")

    await db.commit()
    return {"status": "refunded", "credits_returned": addon.credit_cost}
