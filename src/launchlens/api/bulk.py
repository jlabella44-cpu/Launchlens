"""
Bulk operations API — approve and export multiple listings at once.

Endpoints:
  POST /bulk/approve  — approve multiple listings in review
  POST /bulk/export   — get export URLs for multiple delivered listings
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user, get_db
from launchlens.models.listing import Listing, ListingState
from launchlens.models.user import User
from launchlens.services.endpoint_rate_limit import rate_limit
from launchlens.services.storage import StorageService
from launchlens.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


class BulkApproveRequest(BaseModel):
    listing_ids: list[uuid.UUID]


class BulkExportRequest(BaseModel):
    listing_ids: list[uuid.UUID]
    mode: str = "marketing"  # "mls" or "marketing"


@router.post("/approve")
async def bulk_approve(
    body: BulkApproveRequest,
    _rl=Depends(rate_limit(3, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve multiple listings that are in IN_REVIEW state."""
    if len(body.listing_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 listings per bulk approve")

    results = []
    for lid in body.listing_ids:
        listing = (await db.execute(
            select(Listing).where(
                Listing.id == lid,
                Listing.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()

        if not listing:
            results.append({"listing_id": str(lid), "status": "not_found"})
            continue

        if listing.state != ListingState.IN_REVIEW:
            results.append({
                "listing_id": str(lid),
                "status": "skipped",
                "reason": f"state is {listing.state.value}, expected in_review",
            })
            continue

        listing.state = ListingState.APPROVED
        results.append({"listing_id": str(lid), "status": "approved"})

        # Signal Temporal workflow
        try:
            client = get_temporal_client()
            await client.signal_review_completed(listing_id=str(lid))
        except Exception:
            logger.exception("Review signal failed for listing %s", lid)

    await db.commit()

    approved_count = sum(1 for r in results if r["status"] == "approved")
    return {
        "total": len(body.listing_ids),
        "approved": approved_count,
        "results": results,
    }


@router.post("/export")
async def bulk_export(
    body: BulkExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get export download URLs for multiple listings."""
    if len(body.listing_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 listings per bulk export")

    if body.mode not in ("mls", "marketing"):
        raise HTTPException(status_code=400, detail="Mode must be 'mls' or 'marketing'")

    storage = StorageService()
    results = []

    for lid in body.listing_ids:
        listing = (await db.execute(
            select(Listing).where(
                Listing.id == lid,
                Listing.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()

        if not listing:
            results.append({"listing_id": str(lid), "status": "not_found"})
            continue

        bundle_path = listing.mls_bundle_path if body.mode == "mls" else listing.marketing_bundle_path
        if not bundle_path:
            results.append({
                "listing_id": str(lid),
                "status": "no_bundle",
                "reason": f"No {body.mode} bundle available",
            })
            continue

        url = storage.presigned_url(bundle_path, expires_in=3600)
        results.append({
            "listing_id": str(lid),
            "status": "ready",
            "download_url": url,
        })

    ready_count = sum(1 for r in results if r["status"] == "ready")
    return {
        "total": len(body.listing_ids),
        "ready": ready_count,
        "mode": body.mode,
        "results": results,
    }
