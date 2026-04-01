import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin, require_admin, require_superadmin
from listingjet.api.schemas.admin import (
    AdjustCreditsRequest,
    AdminListingResponse,
    AdminUpdateListingRequest,
    AdminUserResponse,
    AuditLogResponse,
    CreditSummaryResponse,
    CreditTransactionResponse,
    InviteUserRequest,
    PlatformStatsResponse,
    RevenueBreakdownResponse,
    SystemEventResponse,
    TenantCreditsResponse,
    TenantDetailResponse,
    TenantResponse,
    UpdateTenantRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from listingjet.models.audit_log import AuditLog
from listingjet.models.credit_transaction import CreditTransaction
from listingjet.models.event import Event
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.audit import audit_log
from listingjet.services.auth import hash_password
from listingjet.services.events import emit_event

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
    """Unauthenticated health check for the admin router."""
    return {"status": "ok", "detail": "admin"}


@router.get("/health")
async def admin_health(admin_user: User = Depends(require_admin)):
    """Authenticated health check that confirms admin role access."""
    return {"status": "ok", "role": admin_user.role.value}


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all tenants ordered by creation date. Requires superadmin role."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return result.scalars().all()


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Return detailed info for a single tenant including user and listing counts. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )).scalar() or 0

    listing_count = (await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == tenant_id)
    )).scalar() or 0

    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        stripe_customer_id=tenant.stripe_customer_id,
        stripe_subscription_id=tenant.stripe_subscription_id,
        webhook_url=tenant.webhook_url,
        credit_balance=tenant.credit_balance,
        created_at=tenant.created_at,
        user_count=user_count,
        listing_count=listing_count,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Update a tenant's name, plan, or webhook URL. Changes are audit-logged. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    changes = {}
    if body.name is not None:
        changes["name"] = {"old": tenant.name, "new": body.name}
        tenant.name = body.name
    if body.plan is not None:
        if body.plan not in ("starter", "pro", "enterprise"):
            raise HTTPException(status_code=400, detail="Invalid plan. Must be: starter, pro, enterprise")
        changes["plan"] = {"old": tenant.plan, "new": body.plan}
        tenant.plan = body.plan
    if body.webhook_url is not None:
        tenant.webhook_url = body.webhook_url or None  # empty string → None
        changes["webhook_url"] = "updated"

    await audit_log(db, admin_user.id, "update", "tenant", str(tenant_id), tenant_id=tenant_id, details=changes)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/tenants/{tenant_id}/test-webhook")
async def test_webhook(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Send a test event to the tenant's webhook URL."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL configured for this tenant")

    from listingjet.services.webhook_delivery import deliver_webhook

    success = await deliver_webhook(
        url=tenant.webhook_url,
        event_type="webhook.test",
        payload={"message": "This is a test webhook from ListingJet", "tenant_name": tenant.name},
        tenant_id=str(tenant_id),
    )

    return {
        "delivered": success,
        "webhook_url": tenant.webhook_url,
        "event_type": "webhook.test",
    }


VALID_ROLES = {r.value for r in UserRole}


@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all users belonging to a tenant. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    return [UserResponse.from_orm_user(u) for u in result.scalars().all()]


@router.post("/tenants/{tenant_id}/users", status_code=201, response_model=UserResponse)
async def invite_user(
    tenant_id: uuid.UUID,
    body: InviteUserRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Create a new user under the given tenant. Returns 409 if email is already registered. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole(body.role),
    )
    db.add(user)
    await audit_log(
        db, admin_user.id, "invite_user", "user", str(user.id),
        tenant_id=tenant_id,
        details={"email": body.email, "role": body.role},
    )
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    body: UpdateUserRoleRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Change a user's role (e.g. viewer → admin). Requires superadmin."""
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(body.role)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


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


# ── Credit Management ──────────────────────────────────────────────


@router.get("/tenants/{tenant_id}/credits", response_model=TenantCreditsResponse)
async def get_tenant_credits(
    tenant_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Credit balance + recent transactions for a tenant."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.tenant_id == tenant_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
    )
    txns = result.scalars().all()

    return TenantCreditsResponse(
        tenant_id=tenant_id,
        credit_balance=tenant.credit_balance,
        transactions=[CreditTransactionResponse.model_validate(t) for t in txns],
    )


@router.post("/tenants/{tenant_id}/credits/adjust", response_model=CreditTransactionResponse)
async def adjust_credits(
    tenant_id: uuid.UUID,
    body: AdjustCreditsRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Manually add or remove credits for a tenant with audit trail."""
    if body.amount == 0:
        raise HTTPException(status_code=400, detail="Amount must be non-zero")

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    new_balance = tenant.credit_balance + body.amount
    if new_balance < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Adjustment would result in negative balance ({new_balance}). Current: {tenant.credit_balance}",
        )

    tenant.credit_balance = new_balance

    # Sync CreditAccount (source of truth) with Tenant.credit_balance
    from listingjet.models.credit_account import CreditAccount
    credit_acct = (await db.execute(
        select(CreditAccount).where(CreditAccount.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if credit_acct:
        credit_acct.balance = new_balance

    account_id = credit_acct.id if credit_acct else uuid.uuid4()
    txn = CreditTransaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        account_id=account_id,
        amount=body.amount,
        balance_after=new_balance,
        transaction_type="admin_adjustment",
        description=body.reason,
        metadata_={"admin_user_id": str(admin_user.id)},
    )
    db.add(txn)
    await audit_log(
        db, admin_user.id, "adjust_credits", "tenant", str(tenant_id),
        tenant_id=tenant_id,
        details={"amount": body.amount, "new_balance": new_balance, "reason": body.reason},
    )

    await emit_event(
        session=db,
        event_type="credits.admin_adjustment",
        payload={
            "amount": body.amount,
            "balance_after": new_balance,
            "reason": body.reason,
            "admin_user_id": str(admin_user.id),
        },
        tenant_id=str(tenant_id),
    )

    await db.commit()
    await db.refresh(txn)
    return txn


@router.get("/credits/summary", response_model=CreditSummaryResponse)
async def credits_summary(
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Platform-wide credit statistics."""
    # Total credits outstanding
    total_outstanding = (await db.execute(
        select(func.coalesce(func.sum(Tenant.credit_balance), 0))
    )).scalar()

    # Tenants with credits
    tenant_count = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.credit_balance > 0)
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


# ── Listings Management ──────────────────────────────────────────────


@router.get("/listings", response_model=list[AdminListingResponse])
async def admin_list_listings(
    state: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all listings across tenants with filters."""
    query = select(
        Listing, Tenant.name.label("tenant_name")
    ).join(Tenant, Listing.tenant_id == Tenant.id)

    if state:
        try:
            ls = ListingState(state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
        query = query.where(Listing.state == ls)
    if tenant_id:
        query = query.where(Listing.tenant_id == tenant_id)
    if search:
        query = query.where(
            func.cast(Listing.address, String).ilike(f"%{search}%")
        )

    query = query.order_by(Listing.updated_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    return [
        AdminListingResponse(
            id=listing.id,
            tenant_id=listing.tenant_id,
            tenant_name=tenant_name,
            address=listing.address or {},
            metadata=listing.metadata_ or {},
            state=listing.state.value if hasattr(listing.state, "value") else listing.state,
            analysis_tier=listing.analysis_tier or "standard",
            credit_cost=listing.credit_cost,
            is_demo=listing.is_demo,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )
        for listing, tenant_name in rows
    ]


@router.patch("/listings/{listing_id}", response_model=AdminListingResponse)
async def admin_update_listing(
    listing_id: uuid.UUID,
    body: AdminUpdateListingRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Update a listing's address, metadata, or state (for fixing errors)."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    changes = {}
    if body.address is not None:
        changes["address"] = {"old": listing.address, "new": body.address}
        listing.address = body.address
    if body.metadata is not None:
        changes["metadata"] = {"old": listing.metadata_, "new": body.metadata}
        listing.metadata_ = body.metadata
    if body.state is not None:
        try:
            new_state = ListingState(body.state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {body.state}")
        changes["state"] = {"old": listing.state.value, "new": body.state}
        listing.state = new_state

    await audit_log(
        db, admin_user.id, "update", "listing", str(listing_id),
        tenant_id=listing.tenant_id, details=changes,
    )
    await db.commit()
    await db.refresh(listing)

    tenant = await db.get(Tenant, listing.tenant_id)
    return AdminListingResponse(
        id=listing.id,
        tenant_id=listing.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        address=listing.address or {},
        metadata=listing.metadata_ or {},
        state=listing.state.value if hasattr(listing.state, "value") else listing.state,
        analysis_tier=listing.analysis_tier or "standard",
        credit_cost=listing.credit_cost,
        is_demo=listing.is_demo,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


@router.post("/listings/{listing_id}/retry")
async def admin_retry_listing(
    listing_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Admin retry of a failed/timed-out listing (cross-tenant)."""
    import logging

    logger = logging.getLogger(__name__)

    listing = (await db.execute(
        select(Listing).where(Listing.id == listing_id).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    retryable = {ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
    if listing.state not in retryable:
        raise HTTPException(
            status_code=409,
            detail=f"Can only retry failed listings, current state: {listing.state.value}",
        )

    listing.state = ListingState.UPLOADING
    tenant = await db.get(Tenant, listing.tenant_id)

    await audit_log(
        db, admin_user.id, "retry_listing", "listing", str(listing_id),
        tenant_id=listing.tenant_id,
        details={"previous_state": listing.state.value},
    )
    await db.commit()

    try:
        from listingjet.temporal_client import get_temporal_client

        client = get_temporal_client()
        await client.start_pipeline(
            listing_id=str(listing.id),
            tenant_id=str(listing.tenant_id),
            plan=tenant.plan if tenant else "starter",
        )
    except Exception:
        logger.exception("Admin pipeline retry trigger failed for listing %s", listing.id)

    return {"listing_id": str(listing.id), "state": "uploading"}


# ── Users (cross-tenant) ─────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserResponse])
async def admin_list_all_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all users across tenants with filters."""
    query = select(
        User, Tenant.name.label("tenant_name")
    ).join(Tenant, User.tenant_id == Tenant.id)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )
    if role:
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        query = query.where(User.role == UserRole(role))
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    return [
        AdminUserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            tenant_name=tenant_name,
            email=user.email,
            name=user.name,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            created_at=user.created_at,
        )
        for user, tenant_name in rows
    ]


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
