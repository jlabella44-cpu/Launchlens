import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin, require_admin, require_superadmin
from listingjet.api.schemas.admin import (
    AuditLogResponse,
    CreditSummaryResponse,
    PlatformStatsResponse,
    RevenueBreakdownResponse,
    SystemEventResponse,
)
from listingjet.models.audit_log import AuditLog
from listingjet.models.credit_transaction import CreditTransaction
from listingjet.models.event import Event
from listingjet.models.listing import Listing
from listingjet.models.tenant import Tenant
from listingjet.models.user import User

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
    """Unauthenticated health check for the admin router."""
    return {"status": "ok", "detail": "admin"}


@router.get("/health")
async def admin_health(admin_user: User = Depends(require_admin)):
    """Authenticated health check that confirms admin role access."""
    return {"status": "ok", "role": admin_user.role.value}


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Return platform-wide counts: tenants, users, listings, and listings grouped by state. Requires superadmin."""
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_listings = (await db.execute(select(func.count(Listing.id)))).scalar() or 0

    state_rows = (await db.execute(
        select(Listing.state, func.count(Listing.id)).group_by(Listing.state)
    )).all()
    listings_by_state = {
        row[0].value if hasattr(row[0], 'value') else row[0]: row[1]
        for row in state_rows
    }

    return PlatformStatsResponse(
        total_tenants=total_tenants,
        total_users=total_users,
        total_listings=total_listings,
        listings_by_state=listings_by_state,
    )


# ── Credit Summary ────────────────────────────────────────────────────


@router.get("/credits/summary", response_model=CreditSummaryResponse)
async def credits_summary(
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Platform-wide credit statistics."""
    from listingjet.models.credit_account import CreditAccount

    # Total credits outstanding (from CreditAccount — source of truth)
    total_outstanding = (await db.execute(
        select(func.coalesce(func.sum(CreditAccount.balance), 0))
    )).scalar()

    # Tenants with credits
    tenant_count = (await db.execute(
        select(func.count(CreditAccount.tenant_id)).where(CreditAccount.balance > 0)
    )).scalar() or 0

    # This month's transactions
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    purchased = (await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.transaction_type == "purchase",
            CreditTransaction.created_at >= month_start,
        )
    )).scalar()

    used = (await db.execute(
        select(func.coalesce(func.sum(func.abs(CreditTransaction.amount)), 0)).where(
            CreditTransaction.transaction_type == "usage",
            CreditTransaction.created_at >= month_start,
        )
    )).scalar()

    adjusted = (await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.transaction_type == "admin_adjustment",
            CreditTransaction.created_at >= month_start,
        )
    )).scalar()

    return CreditSummaryResponse(
        total_credits_outstanding=total_outstanding,
        credits_purchased_this_month=purchased,
        credits_used_this_month=used,
        credits_adjusted_this_month=adjusted,
        tenant_count_with_credits=tenant_count,
    )


@router.get("/analytics/revenue", response_model=RevenueBreakdownResponse)
async def revenue_breakdown(
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Revenue breakdown — subscriptions vs credit purchases."""
    # Subscription tenants (non-starter with stripe sub)
    sub_count = (await db.execute(
        select(func.count(Tenant.id)).where(
            Tenant.stripe_subscription_id.isnot(None),
            Tenant.plan != "starter",
        )
    )).scalar() or 0

    # Credit purchases (all time)
    purchase_rows = await db.execute(
        select(
            func.count(CreditTransaction.id),
            func.coalesce(func.sum(CreditTransaction.amount), 0),
        ).where(CreditTransaction.transaction_type == "purchase")
    )
    purchase_row = purchase_rows.one()
    credit_purchase_count = purchase_row[0]
    total_credits_purchased = purchase_row[1]

    # Top 10 tenants by credit usage
    usage_rows = (await db.execute(
        select(
            CreditTransaction.tenant_id,
            Tenant.name,
            func.sum(func.abs(CreditTransaction.amount)).label("total_used"),
        )
        .join(Tenant, CreditTransaction.tenant_id == Tenant.id)
        .where(CreditTransaction.transaction_type == "usage")
        .group_by(CreditTransaction.tenant_id, Tenant.name)
        .order_by(func.sum(func.abs(CreditTransaction.amount)).desc())
        .limit(10)
    )).all()
    top_tenants = [
        {"tenant_id": str(row[0]), "credits_used": int(row[2])}
        for row in usage_rows
    ]

    # Average credits per listing (usage transactions / total listings)
    total_usage = (await db.execute(
        select(func.coalesce(func.sum(func.abs(CreditTransaction.amount)), 0)).where(
            CreditTransaction.transaction_type == "usage"
        )
    )).scalar()
    total_listings = (await db.execute(select(func.count(Listing.id)))).scalar() or 0
    avg_per_listing = round(total_usage / total_listings, 2) if total_listings > 0 else None

    return RevenueBreakdownResponse(
        subscription_tenant_count=sub_count,
        credit_purchase_count=credit_purchase_count,
        total_credits_purchased=total_credits_purchased,
        top_tenants_by_usage=top_tenants,
        avg_credits_per_listing=avg_per_listing,
    )


# ── Audit Log ────────────────────────────────────────────────────────


@router.get("/audit-log", response_model=list[AuditLogResponse])
async def admin_audit_log(
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Paginated audit log viewer."""
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)

    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return rows


# ── Recent Events ────────────────────────────────────────────────────


@router.get("/events/recent", response_model=list[SystemEventResponse])
async def admin_recent_events(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Recent system events for health monitoring."""
    query = select(Event)
    if event_type:
        query = query.where(Event.event_type == event_type)
    query = query.order_by(Event.created_at.desc()).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return rows
