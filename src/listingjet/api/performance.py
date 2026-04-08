"""Performance Intelligence API — insights, correlations, and marketing claims.

Endpoints:
  GET /analytics/performance              — tenant overview
  GET /analytics/performance/listing/{id} — per-listing insight card
  GET /analytics/performance/correlations — photo trait → outcome correlations
  GET /admin/performance/claims           — platform-wide marketing claims
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, require_admin
from listingjet.database import get_db
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.performance_insight import PerformanceInsight
from listingjet.models.user import User
from listingjet.services import performance_intelligence as pi

router = APIRouter()


@router.get("/analytics/performance")
async def get_performance_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant-level performance overview with cached insights."""
    # Check for cached insights
    result = await db.execute(
        select(PerformanceInsight).where(
            PerformanceInsight.tenant_id == current_user.tenant_id
        ).order_by(PerformanceInsight.calculated_at.desc())
    )
    cached = result.scalars().all()

    # Count outcomes
    count_result = await db.execute(
        select(ListingOutcome).where(
            ListingOutcome.tenant_id == current_user.tenant_id
        )
    )
    outcomes = count_result.scalars().all()

    if not cached and len(outcomes) >= pi.MIN_SAMPLE_SIZE:
        # Compute fresh insights
        insights = await pi.compute_tenant_insights(db, current_user.tenant_id)
    else:
        insights = [
            {"type": i.insight_type, "data": i.data, "sample_size": i.sample_size}
            for i in cached
        ]

    return {
        "tenant_id": str(current_user.tenant_id),
        "total_outcomes": len(outcomes),
        "insights": insights,
        "sufficient_data": len(outcomes) >= pi.MIN_SAMPLE_SIZE,
    }


@router.get("/analytics/performance/listing/{listing_id}")
async def get_listing_performance(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-listing performance insight card."""
    insight = await pi.get_listing_insight(db, listing_id, current_user.tenant_id)
    if not insight:
        raise HTTPException(404, "No outcome data for this listing")
    return insight


@router.get("/analytics/performance/correlations")
async def get_correlations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Photo trait → outcome correlation data for the tenant."""
    insights = await pi.compute_tenant_insights(db, current_user.tenant_id)
    # Filter to correlation-type insights
    correlations = [
        i for i in insights
        if i["type"] in ("quality_dom_correlation", "hero_impact", "coverage_impact", "override_impact")
    ]
    return {
        "correlations": correlations,
        "sufficient_data": len(correlations) > 0,
    }


@router.get("/admin/performance/claims")
async def get_platform_claims(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide marketing claims (admin only). Uses admin session."""
    from listingjet.database import AsyncSessionLocal

    async with AsyncSessionLocal() as admin_db:
        return await pi.compute_platform_claims(admin_db)
