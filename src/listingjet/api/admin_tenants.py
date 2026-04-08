import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin, require_superadmin
from listingjet.api.schemas.admin import (
    AdjustCreditsRequest,
    CreditTransactionResponse,
    TenantCreditsResponse,
    TenantDetailResponse,
    TenantResponse,
    UpdateTenantRequest,
)
from listingjet.models.credit_transaction import CreditTransaction
from listingjet.models.learning_weight import LearningWeight
from listingjet.models.listing import Listing
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.audit import audit_log
from listingjet.services.events import emit_event
from listingjet.services.weight_manager import WeightManager

router = APIRouter()


@router.get("/tenants")
async def list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all tenants with pagination. Requires superadmin role."""
    total = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(page_size)
    )
    tenants = result.scalars().all()
    return {
        "items": [TenantResponse.model_validate(t) for t in tenants],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }


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

    from listingjet.models.credit_account import CreditAccount

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )).scalar() or 0

    listing_count = (await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == tenant_id)
    )).scalar() or 0

    credit_acct = (await db.execute(
        select(CreditAccount).where(CreditAccount.tenant_id == tenant_id)
    )).scalar_one_or_none()
    balance = credit_acct.balance if credit_acct else 0

    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        stripe_customer_id=tenant.stripe_customer_id,
        stripe_subscription_id=tenant.stripe_subscription_id,
        webhook_url=tenant.webhook_url,
        credit_balance=balance,
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
        valid_admin_plans = ("free", "lite", "active_agent", "team", "starter", "pro", "enterprise")
        if body.plan not in valid_admin_plans:
            raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {', '.join(valid_admin_plans)}")
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


# ── Credit Management ──────────────────────────────────────────────


@router.get("/tenants/{tenant_id}/credits", response_model=TenantCreditsResponse)
async def get_tenant_credits(
    tenant_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Credit balance + recent transactions for a tenant."""
    from listingjet.models.credit_account import CreditAccount

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    credit_acct = (await db.execute(
        select(CreditAccount).where(CreditAccount.tenant_id == tenant_id)
    )).scalar_one_or_none()
    balance = credit_acct.balance if credit_acct else 0

    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.tenant_id == tenant_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
    )
    txns = result.scalars().all()

    return TenantCreditsResponse(
        tenant_id=tenant_id,
        credit_balance=balance,
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

    from listingjet.services.credits import CreditService

    credit_svc = CreditService()
    credit_acct = await credit_svc.ensure_account(db, tenant_id, rollover_cap=tenant.rollover_cap)

    new_balance = credit_acct.balance + body.amount
    if new_balance < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Adjustment would result in negative balance ({new_balance}). Current: {credit_acct.balance}",
        )

    credit_acct.balance = new_balance
    tenant.credit_balance = new_balance  # keep in sync for backward compat

    account_id = credit_acct.id
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


# ── Weight Health Monitoring ──────────────────────────────────────


@router.get("/tenants/{tenant_id}/weight-health")
async def get_weight_health(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Return learning-weight health stats for a tenant (cold-start detection, boundary alerts)."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(LearningWeight).where(LearningWeight.tenant_id == tenant_id)
    )
    rows = result.scalars().all()

    weights = [
        {
            "room_label": w.room_label,
            "weight": w.weight,
            "labeled_listing_count": w.labeled_listing_count,
        }
        for w in rows
    ]

    wm = WeightManager()
    health = wm.check_health(weights)
    health["weights"] = weights
    return health


@router.post("/tenants/{tenant_id}/weights/reset")
async def reset_weight(
    tenant_id: uuid.UUID,
    room_label: str = Query(..., description="Room label to reset"),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Reset a cold-start weight to baseline 1.0.

    Only allows reset if the weight has fewer than COLD_START_THRESHOLD
    labeled listings, preventing accidental erasure of mature weights.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(LearningWeight).where(
            LearningWeight.tenant_id == tenant_id,
            LearningWeight.room_label == room_label,
        )
    )
    weight = result.scalar_one_or_none()
    if not weight:
        raise HTTPException(status_code=404, detail=f"No weight found for room '{room_label}'")

    wm = WeightManager()
    if not wm.should_reset_cold_start(weight.labeled_listing_count):
        raise HTTPException(
            status_code=400,
            detail=f"Weight has {weight.labeled_listing_count} labeled listings — "
            f"exceeds cold-start threshold. Manual reset not recommended.",
        )

    old_weight = weight.weight
    weight.weight = 1.0
    weight.labeled_listing_count = 0

    await audit_log(
        db, admin_user.id, "reset_weight", "learning_weight",
        str(weight.id), tenant_id=tenant_id,
        details={"room_label": room_label, "old_weight": old_weight, "new_weight": 1.0},
    )
    await db.commit()
    return {"room_label": room_label, "old_weight": old_weight, "new_weight": 1.0, "reset": True}
