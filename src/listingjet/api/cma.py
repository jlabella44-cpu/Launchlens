"""CMA Report API — generate and retrieve Comparative Market Analysis reports."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db, require_superadmin
from listingjet.models.cma_report import CMAReport
from listingjet.models.listing import Listing
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter()


class CMAReportResponse(BaseModel):
    listing_id: uuid.UUID
    generated_at: str
    download_url: str
    comparables_count: int
    analysis_summary: str | None


@router.post("/{listing_id}/cma-report", status_code=202)
async def generate_cma_report(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Generate a CMA report for a listing.

    Superadmin-gated while Repliers is on the synthetic/fallback path — the
    feature will open to tenant users once we move off the synthetic comparables
    and start paying for real MLS data.
    """
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    from listingjet.agents.base import AgentContext
    from listingjet.agents.cma_report import CMAReportAgent

    agent = CMAReportAgent()
    ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id))
    result = await agent.execute(ctx)

    return {"listing_id": str(listing_id), "status": "completed", **result}


@router.get("/{listing_id}/cma-report")
async def get_cma_report(
    listing_id: uuid.UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the most recent CMA report for a listing. Superadmin-only (see POST)."""
    report = (await db.execute(
        select(CMAReport).where(
            CMAReport.listing_id == listing_id,
            CMAReport.tenant_id == current_user.tenant_id,
        ).order_by(CMAReport.generated_at.desc()).limit(1)
    )).scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="No CMA report found. Generate one first.")

    storage = get_storage()
    download_url = storage.presigned_url(report.pdf_s3_key, expires_in=86400)

    return CMAReportResponse(
        listing_id=report.listing_id,
        generated_at=report.generated_at.isoformat(),
        download_url=download_url,
        comparables_count=report.comparables_count,
        analysis_summary=report.analysis_summary,
    )
