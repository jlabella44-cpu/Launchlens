"""
Launch-specific API endpoints for the ListingJet product launch.

Endpoints:
  POST /analytics/events     — Ingest client-side analytics events
  GET  /founding/remaining    — Return remaining Founding 200 spots
  GET  /referral/code         — Return or create the current user's referral code
"""

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.tenant import Tenant
from listingjet.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

FOUNDING_TOTAL = 200


# ── Analytics Event Ingestion ──


class AnalyticsEventRequest(BaseModel):
    event: str
    properties: dict = {}


@router.post("/analytics/events", status_code=204)
async def ingest_analytics_event(body: AnalyticsEventRequest, request: Request):
    """Best-effort analytics event ingestion. Always returns 204."""
    logger.info(
        "analytics_event event=%s props=%s ip=%s",
        body.event,
        body.properties,
        request.client.host if request.client else "unknown",
    )
    # In production, write to a queue (SQS, Kafka) or analytics DB.
    # For now, logging is sufficient for launch tracking.
    return None


# ── Founding 200 Counter ──


@router.get("/founding/remaining")
async def founding_remaining(db: AsyncSession = Depends(get_db)):
    """Return how many Founding 200 spots are left."""
    result = await db.execute(select(func.count(Tenant.id)))
    total_tenants = result.scalar() or 0
    remaining = max(0, FOUNDING_TOTAL - total_tenants)
    return {"remaining": remaining, "total": FOUNDING_TOTAL}


# ── Referral Code ──


@router.get("/referral/code")
async def get_referral_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's referral code. Generates one if missing."""
    # Use a deterministic code derived from user ID for simplicity
    # Format: first 4 chars of name (uppercase) + last 4 of user ID
    name_part = (current_user.name or "USER").replace(" ", "")[:4].upper()
    id_part = str(current_user.id).replace("-", "")[-4:].upper()
    code = f"{name_part}{id_part}"

    return {
        "code": code,
        "url": f"https://app.listingjet.com/register?ref={code}",
    }
