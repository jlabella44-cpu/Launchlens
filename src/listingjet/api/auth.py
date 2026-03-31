import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.auth import GoogleLoginRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from listingjet.database import get_db
from listingjet.models.credit_account import CreditAccount
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.auth import (
    create_access_token,
    hash_password,
    verify_google_id_token,
    verify_password_constant_time,
)
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event

logger = logging.getLogger(__name__)

router = APIRouter()

TIER_DEFAULTS = {
    "lite": {"included_credits": 0, "rollover_cap": 5, "per_listing_credit_cost": 1},
    "active_agent": {"included_credits": 1, "rollover_cap": 3, "per_listing_credit_cost": 1},
    "team": {"included_credits": 5, "rollover_cap": 10, "per_listing_credit_cost": 1},
}

# Map tier names to plan names for plan_limits compatibility
_TIER_TO_PLAN = {
    "lite": "starter",
    "active_agent": "pro",
    "team": "enterprise",
}


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, request: Request, _rl=Depends(rate_limit(5, 60)), db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tier = body.plan_tier or "lite"
    if tier not in TIER_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {tier}. Must be one of: {', '.join(TIER_DEFAULTS)}")

    tier_config = TIER_DEFAULTS[tier]
    plan = _TIER_TO_PLAN.get(tier, "starter")

    tenant = Tenant(id=uuid.uuid4(), name=body.company_name, plan=plan, billing_model="credit")
    db.add(tenant)
    await db.flush()

    # Create credit account with initial grant
    credit_account = CreditAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        balance=tier_config["included_credits"],
        rollover_cap=tier_config["rollover_cap"],
    )
    db.add(credit_account)

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await emit_event(
        session=db,
        event_type="user.registered",
        payload={"email": email, "user_id": str(user.id), "tier": tier, "plan": plan},
        tenant_id=str(tenant.id),
    )
    await db.commit()
    await db.refresh(user)

    # Send welcome email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        email_svc = get_email_service()
        await email_svc.send_template(user.email, "welcome", {
            "name": user.name or "there",
            "plan": tier,
            "app_url": "https://app.listingjet.com",
        })
    except Exception:
        logger.exception("welcome email failed for %s", email)

    logger.info("auth.register email=%s tenant=%s tier=%s", email, tenant.id, tier)
    return TokenResponse(access_token=create_access_token(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, _rl=Depends(rate_limit(10, 60)), db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Constant-time comparison: always run bcrypt even if user not found
    password_valid = verify_password_constant_time(
        body.password, user.password_hash if user else None
    )
    if not user or not password_valid:
        logger.warning("auth.login_failed email=%s", email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ip = request.client.host if request.client else "unknown"
    await emit_event(
        session=db,
        event_type="user.login",
        payload={"email": email, "user_id": str(user.id), "ip": ip},
        tenant_id=str(user.tenant_id),
    )
    await db.commit()

    logger.info("auth.login_success email=%s user=%s", email, user.id)
    return TokenResponse(access_token=create_access_token(user))


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleLoginRequest, request: Request, _rl=Depends(rate_limit(10, 60)), db: AsyncSession = Depends(get_db)):
    google_user = await verify_google_id_token(body.id_token)
    email = google_user["email"]

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user:
        # Existing user — log them in
        ip = request.client.host if request.client else "unknown"
        await emit_event(
            session=db,
            event_type="user.login",
            payload={"email": email, "user_id": str(user.id), "ip": ip, "method": "google"},
            tenant_id=str(user.tenant_id),
        )
        await db.commit()
        logger.info("auth.google_login email=%s user=%s", email, user.id)
        return TokenResponse(access_token=create_access_token(user))

    # New user — auto-register with lite tier
    tier = "lite"
    tier_config = TIER_DEFAULTS[tier]
    plan = _TIER_TO_PLAN.get(tier, "starter")

    company_name = google_user["name"] or email.split("@")[0]
    tenant = Tenant(id=uuid.uuid4(), name=company_name, plan=plan, billing_model="credit")
    db.add(tenant)
    await db.flush()

    credit_account = CreditAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        balance=tier_config["included_credits"],
        rollover_cap=tier_config["rollover_cap"],
    )
    db.add(credit_account)

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash="",  # No password for Google-only users
        name=google_user["name"],
        role=UserRole.ADMIN,
    )
    db.add(user)
    await emit_event(
        session=db,
        event_type="user.registered",
        payload={"email": email, "user_id": str(user.id), "tier": tier, "plan": plan, "method": "google"},
        tenant_id=str(tenant.id),
    )
    await db.commit()
    await db.refresh(user)

    try:
        from listingjet.services.email import get_email_service
        email_svc = get_email_service()
        await email_svc.send_template(user.email, "welcome", {
            "name": user.name or "there",
            "plan": tier,
            "app_url": "https://app.listingjet.com",
        })
    except Exception:
        logger.exception("welcome email failed for %s", email)

    logger.info("auth.google_register email=%s tenant=%s", email, tenant.id)
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
