"""Draft listing endpoints — staging tags and pipeline start."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.draft import (
    StagingTagRequest,
    StagingTagResponse,
    StartPipelineRequest,
    StartPipelineResponse,
)
from listingjet.config.tiers import BUNDLE_PRICING, SERVICE_CREDIT_COSTS
from listingjet.database import get_db
from listingjet.models.addon_catalog import AddonCatalog
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.credits import CreditService, InsufficientCreditsError
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{listing_id}/staging-tags", response_model=StagingTagResponse)
async def set_staging_tags(
    listing_id: uuid.UUID,
    body: StagingTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tag specific photos for virtual staging. Only allowed on DRAFT listings."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.state != ListingState.DRAFT:
        raise HTTPException(status_code=409, detail=f"Staging tags can only be set on DRAFT listings, current: {listing.state.value}")

    # Validate asset IDs belong to this listing
    asset_uuids = [uuid.UUID(aid) for aid in body.asset_ids]
    result = await db.execute(
        select(Asset).where(Asset.listing_id == listing_id, Asset.id.in_(asset_uuids))
    )
    found_assets = result.scalars().all()
    if len(found_assets) != len(asset_uuids):
        raise HTTPException(status_code=400, detail="Some asset IDs not found for this listing")

    # Store staging tags in listing metadata
    current_meta = dict(listing.metadata_) if listing.metadata_ else {}
    current_meta["staging_asset_ids"] = body.asset_ids
    listing.metadata_ = current_meta

    await db.commit()
    return StagingTagResponse(tagged_count=len(body.asset_ids), listing_id=str(listing_id))


@router.post("/{listing_id}/start-pipeline", response_model=StartPipelineResponse)
async def start_pipeline(
    listing_id: uuid.UUID,
    body: StartPipelineRequest,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a DRAFT listing: deduct credits, activate addons, start the pipeline."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.state != ListingState.DRAFT:
        raise HTTPException(status_code=409, detail=f"Can only start pipeline for DRAFT listings, current: {listing.state.value}")

    # Verify listing has assets
    asset_count = (await db.execute(
        select(Asset.id).where(Asset.listing_id == listing_id).limit(1)
    )).scalar_one_or_none()
    if not asset_count:
        raise HTTPException(status_code=400, detail="Upload at least one photo before starting the pipeline")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    credit_svc = CreditService()

    # Calculate total cost
    base_cost = tenant.per_listing_credit_cost
    addon_cost = 0
    is_bundle = "all_addons_bundle" in body.selected_addons
    enabled_addon_slugs: list[str] = []

    if is_bundle:
        bundle = BUNDLE_PRICING["all_addons_bundle"]
        addon_cost = bundle["credit_cost"]
        enabled_addon_slugs = list(bundle["includes"])
    else:
        for slug in body.selected_addons:
            cost = SERVICE_CREDIT_COSTS.get(slug)
            if cost is None:
                raise HTTPException(status_code=400, detail=f"Unknown addon: {slug}")
            addon_cost += cost
            enabled_addon_slugs.append(slug)

    total_cost = base_cost + addon_cost

    # Deduct base listing credits
    try:
        await credit_svc.deduct_credits(
            db, tenant.id, base_cost,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(listing_id),
            description=f"Listing at {listing.address.get('street', 'new listing')}",
        )
    except InsufficientCreditsError:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {total_cost}, purchase more to continue.")

    listing.credit_cost = base_cost

    # Activate addons and deduct addon credits
    bundle_id = "all_addons_bundle" if is_bundle else None
    for slug in enabled_addon_slugs:
        catalog_entry = (await db.execute(
            select(AddonCatalog).where(AddonCatalog.slug == slug)
        )).scalar_one_or_none()
        if not catalog_entry:
            continue

        addon_credit_cost = 0 if is_bundle else catalog_entry.credit_cost
        txn = None
        if addon_credit_cost > 0:
            try:
                txn = await credit_svc.deduct_credits(
                    db, tenant.id, addon_credit_cost,
                    transaction_type="addon_debit",
                    reference_type="addon",
                    reference_id=f"{listing_id}:{slug}",
                    description=f"Addon {slug} for listing {listing.address.get('street', '')}",
                )
            except InsufficientCreditsError:
                raise HTTPException(status_code=402, detail=f"Insufficient credits for addon {slug}.")

        purchase = AddonPurchase(
            tenant_id=tenant.id,
            listing_id=listing_id,
            addon_id=catalog_entry.id,
            credit_transaction_id=txn.id if txn else None,
            bundle_id=bundle_id,
            status="active",
        )
        db.add(purchase)

    # Bundle credit deduction (single charge for all included addons)
    if is_bundle:
        try:
            await credit_svc.deduct_credits(
                db, tenant.id, addon_cost,
                transaction_type="addon_debit",
                reference_type="bundle",
                reference_id=f"{listing_id}:all_addons_bundle",
                description=f"Premium Bundle for listing {listing.address.get('street', '')}",
            )
        except InsufficientCreditsError:
            raise HTTPException(status_code=402, detail=f"Insufficient credits for bundle. Need {addon_cost} more.")

    # Transition to UPLOADING and start pipeline
    listing.state = ListingState.UPLOADING
    await db.commit()

    # Start Temporal workflow
    workflow_id = ""
    try:
        client = get_temporal_client()
        workflow_id = await client.start_pipeline(
            listing_id=str(listing_id),
            tenant_id=str(tenant.id),
            plan=tenant.plan,
            billing_model=tenant.billing_model,
            enabled_addons=enabled_addon_slugs,
        )
    except Exception:
        logger.exception("Pipeline start failed for listing %s", listing_id)
        listing.state = ListingState.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to start processing pipeline")

    return StartPipelineResponse(
        listing_id=str(listing_id),
        state=listing.state.value,
        credits_deducted=total_cost,
        workflow_id=workflow_id,
    )
