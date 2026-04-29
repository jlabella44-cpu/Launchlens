import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas import ErrorResponse
from listingjet.api.schemas.listings import (
    ActionResponse,
    CancelResponse,
    PipelineStatusResponse,
    RejectRequest,
)
from listingjet.database import get_db
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.scoring_event import ScoringEvent
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event
from listingjet.services.metrics import record_review_turnaround
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-process cache for engagement scores (computed once per listing, never changes)
_engagement_cache: dict[str, tuple] = {}


@router.post("/{listing_id}/review", response_model=ActionResponse)
async def start_review(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transition a listing from AWAITING_REVIEW to IN_REVIEW, locking it for editing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state != ListingState.AWAITING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot start review: listing is {listing.state.value}")

    listing.state = ListingState.IN_REVIEW
    await emit_event(
        session=db,
        event_type="listing.review_started",
        payload={"user_id": str(current_user.id)},
        tenant_id=str(current_user.tenant_id),
        listing_id=str(listing.id),
    )
    await db.commit()
    await db.refresh(listing)
    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post(
    "/{listing_id}/approve",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def approve_listing(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a listing that is IN_REVIEW, signalling the workflow to continue post-approval steps."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state != ListingState.IN_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot approve: listing is {listing.state.value}")

    # Record review turnaround time (time since last state change, approx AWAITING_REVIEW)
    if listing.updated_at:
        turnaround = (datetime.now(timezone.utc) - listing.updated_at).total_seconds()
        record_review_turnaround(turnaround)

    listing.state = ListingState.APPROVED

    # Backfill "approval" outcome on all un-labeled ScoringEvent rows for this listing
    await db.execute(
        update(ScoringEvent)
        .where(
            ScoringEvent.listing_id == listing_id,
            ScoringEvent.outcome.is_(None),
        )
        .values(outcome="approval", outcome_at=datetime.now(timezone.utc))
    )

    await db.commit()
    await db.refresh(listing)

    # Signal the waiting workflow to continue post-approval pipeline
    try:
        client = get_temporal_client()
        await client.signal_review_completed(listing_id=str(listing.id))
    except Exception:
        logger.exception("Review signal failed for listing %s", listing.id)

    # Send REVIEW_APPROVED email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        from listingjet.services.notifications import _listing_address_str
        address = _listing_address_str(listing)
        email_svc = get_email_service()
        email_svc.send_notification(
            current_user.email,
            "review_approved",
            name=current_user.name or "there",
            address=address,
        )
    except Exception:
        logger.exception("review_approved email failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post(
    "/{listing_id}/reject",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def reject_listing(
    listing_id: uuid.UUID,
    body: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a listing with a reason code. Transitions state to FAILED."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    rejectable = {ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW}
    if listing.state not in rejectable:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: listing is {listing.state.value}",
        )

    valid_reasons = {"quality", "incomplete", "non_compliant", "other"}
    if body.reason not in valid_reasons:
        raise HTTPException(status_code=400, detail=f"Invalid reason. Must be one of: {valid_reasons}")

    listing.state = ListingState.FAILED

    # Backfill "rejection" outcome on all un-labeled ScoringEvent rows for this listing
    await db.execute(
        update(ScoringEvent)
        .where(
            ScoringEvent.listing_id == listing_id,
            ScoringEvent.outcome.is_(None),
        )
        .values(outcome="rejection", outcome_at=datetime.now(timezone.utc))
    )

    # Emit event BEFORE commit — outbox atomicity
    from listingjet.services.events import emit_event
    await emit_event(
        session=db,
        event_type="listing.rejected",
        payload={"reason": body.reason, "detail": body.detail},
        tenant_id=str(current_user.tenant_id),
        listing_id=str(listing.id),
    )

    await db.commit()
    await db.refresh(listing)

    # Send REVIEW_REJECTED email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        from listingjet.services.notifications import _listing_address_str
        address = _listing_address_str(listing)
        email_svc = get_email_service()
        email_svc.send_notification(
            current_user.email,
            "review_rejected",
            name=current_user.name or "there",
            address=address,
            reason=body.reason,
            detail=body.detail or "",
        )
    except Exception:
        logger.exception("review_rejected email failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post(
    "/{listing_id}/retry",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def retry_pipeline(
    listing_id: uuid.UUID,
    _rl=Depends(rate_limit(3, 3600)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a failed listing and re-trigger the pipeline."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    retryable = {ListingState.FAILED, ListingState.PIPELINE_TIMEOUT, ListingState.UPLOADING, ListingState.ANALYZING}
    if listing.state not in retryable:
        raise HTTPException(
            status_code=409,
            detail=f"Can only retry failed or stuck listings, current state: {listing.state.value}",
        )

    listing.state = ListingState.UPLOADING
    tenant = await db.get(Tenant, current_user.tenant_id)
    await db.commit()

    try:
        client = get_temporal_client()
        await client.start_pipeline(
            listing_id=str(listing.id),
            tenant_id=str(current_user.tenant_id),
            plan=tenant.plan if tenant else "starter",
            terminate_existing=True,
        )
    except Exception:
        logger.exception("Pipeline retry trigger failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": "uploading"}


@router.post(
    "/{listing_id}/cancel",
    response_model=CancelResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def cancel_listing(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a listing and refund credits if using credit billing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    cancellable = {ListingState.DRAFT, ListingState.NEW, ListingState.UPLOADING, ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
    if listing.state not in cancellable:
        raise HTTPException(409, f"Cannot cancel: listing is {listing.state.value}")

    credits_refunded = 0
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant and tenant.billing_model == "credit" and listing.credit_cost:
        from listingjet.services.credits import CreditService
        credit_svc = CreditService()
        txn = await credit_svc.refund_credits(db, current_user.tenant_id, str(listing_id))
        if txn:
            credits_refunded = txn.amount

    listing.state = ListingState.CANCELLED
    await db.commit()

    return {"listing_id": str(listing.id), "state": listing.state.value, "credits_refunded": credits_refunded}


@router.get("/{listing_id}/pipeline-status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return per-step pipeline progress for a listing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    from listingjet.models.event import Event

    result = await db.execute(
        select(Event)
        .where(Event.listing_id == listing_id)
        .order_by(Event.created_at)
        .limit(500)
    )
    events = result.scalars().all()

    # Build step list from known pipeline stages
    pipeline_steps = [
        "ingestion", "vision_tier1", "vision_tier2", "coverage",
        "floorplan", "packaging", "compliance", "review",
        "content", "brand", "social_content", "chapters",
        "social_cuts", "mls_export", "watermark", "distribution",
    ]

    completed_steps = set()
    step_times = {}
    for evt in events:
        et = evt.event_type
        if et.endswith(".completed") or et.endswith(".done"):
            step_name = et.rsplit(".", 1)[0]
            completed_steps.add(step_name)
            step_times[step_name] = evt.created_at.isoformat()

    state_val = listing.state.value if hasattr(listing.state, "value") else listing.state
    steps = []
    for step in pipeline_steps:
        if step in completed_steps:
            status = "completed"
        elif state_val in ("delivered", "failed"):
            status = "skipped"
        else:
            status = "pending"
        steps.append({
            "name": step,
            "status": status,
            "completed_at": step_times.get(step),
            "progress": None,
        })

    # Mark current active step
    for s in steps:
        if s["status"] == "pending":
            if state_val not in ("new", "awaiting_review", "in_review", "delivered", "failed"):
                s["status"] = "in_progress"
            break

    # Engagement prediction + features — cached to avoid recomputation on every poll
    engagement_score = None
    detected_features = []
    packaged_states = {"awaiting_review", "in_review", "approved", "exporting", "delivered"}
    if state_val in packaged_states:
        cache_key = f"engagement:{listing_id}"
        cached = _engagement_cache.get(cache_key)
        if cached:
            engagement_score, detected_features = cached
        else:
            from listingjet.models.vision_result import VisionResult
            from listingjet.services.engagement_score import predict_engagement
            from listingjet.services.feature_tags import extract_features

            vision_results = (await db.execute(
                select(VisionResult)
                .join(Asset, VisionResult.asset_id == Asset.id)
                .where(Asset.listing_id == listing_id, VisionResult.tier == 1)
            )).scalars().all()

            engagement_score = predict_engagement(vision_results)
            detected_features = extract_features(vision_results)
            _engagement_cache[cache_key] = (engagement_score, detected_features)

    return {
        "listing_id": str(listing.id),
        "listing_state": state_val,
        "steps": steps,
        "engagement_score": engagement_score,
        "detected_features": detected_features,
    }


@router.post("/{listing_id}/compliance")
async def run_compliance_scan(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run photo compliance scan on a listing's packaged photos. Returns per-photo report."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    scannable = {
        ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW,
        ListingState.APPROVED, ListingState.EXPORTING, ListingState.DELIVERED,
    }
    if listing.state not in scannable:
        raise HTTPException(
            status_code=409,
            detail=f"Compliance scan requires packaged photos. Current state: {listing.state.value}",
        )

    from listingjet.agents.base import AgentContext
    from listingjet.agents.photo_compliance import PhotoComplianceAgent

    agent = PhotoComplianceAgent()
    ctx = AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id))
    report = await agent.execute(ctx)
    return report
