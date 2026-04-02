import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from listingjet.config.tiers import TIER_DEFAULTS
from listingjet.config.tiers import TIER_TO_PLAN as _TIER_TO_PLAN
from listingjet.database import get_db
from listingjet.models.credit_account import CreditAccount
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password_constant_time,
)
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event

logger = logging.getLogger(__name__)

router = APIRouter()


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
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, _rl=Depends(rate_limit(10, 60)), db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Constant-time comparison: always run bcrypt even if user not found
    password_valid = verify_password_constant_time(
        body.password, user.password_hash if user else None
    )
    if not user or not password_valid:
        import hashlib
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:12]
        logger.warning("auth.login_failed email_hash=%s", email_hash)
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
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit(10, 60))])
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
    )


@router.post("/logout")
async def logout():
    """Logout endpoint. Client should discard tokens.

    Note: Full server-side token revocation requires a Redis-backed
    blocklist. For now, short-lived access tokens (1hr) limit exposure.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Google Sign-In
# ---------------------------------------------------------------------------

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_google_jwks_cache: dict | None = None


async def _get_google_jwks() -> dict:
    """Fetch and cache Google's public JWKS for ID token verification."""
    global _google_jwks_cache
    if _google_jwks_cache is not None:
        return _google_jwks_cache
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GOOGLE_JWKS_URL)
        resp.raise_for_status()
        _google_jwks_cache = resp.json()
    return _google_jwks_cache


def _verify_google_id_token(id_token: str, client_id: str) -> dict:
    """Verify a Google ID token and return the payload (email, name, sub)."""
    import jwt as pyjwt
    from jwt import PyJWKClient

    jwk_client = PyJWKClient(_GOOGLE_JWKS_URL)
    signing_key = jwk_client.get_signing_key_from_jwt(id_token)
    payload = pyjwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=["https://accounts.google.com", "accounts.google.com"],
    )
    if not payload.get("email_verified"):
        raise ValueError("Email not verified by Google")
    return payload


class GoogleLoginRequest(BaseModel):
    id_token: str


@router.post("/google", response_model=TokenResponse)
async def google_login(
    body: GoogleLoginRequest,
    _rl=Depends(rate_limit(10, 60)),
    db: AsyncSession = Depends(get_db),
):
    """Sign in or register with a Google ID token from the Sign In With Google flow."""
    from listingjet.config import settings

    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=501, detail="Google sign-in is not configured")

    try:
        google_payload = _verify_google_id_token(body.id_token, settings.google_oauth_client_id)
    except Exception as exc:
        logger.warning("google_auth_failed error=%s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google ID token")

    email = google_payload["email"].strip().lower()
    name = google_payload.get("name")

    # Check if user already exists
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user:
        # Existing user — log them in
        logger.info("auth.google_login email=%s user=%s", email, user.id)
        return TokenResponse(
            access_token=create_access_token(user),
            refresh_token=create_refresh_token(user),
        )

    # New user — auto-register with default plan
    tenant = Tenant(id=uuid.uuid4(), name=name or email.split("@")[0], plan="starter", billing_model="credit")
    db.add(tenant)
    await db.flush()

    from listingjet.models.credit_account import CreditAccount

    credit_account = CreditAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        balance=0,
        rollover_cap=5,
    )
    db.add(credit_account)

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash="",  # No password for Google-only users
        name=name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await emit_event(
        session=db,
        event_type="user.registered",
        payload={"email": email, "user_id": str(user.id), "provider": "google", "plan": "starter"},
        tenant_id=str(tenant.id),
    )
    await db.commit()
    await db.refresh(user)

    logger.info("auth.google_register email=%s tenant=%s", email, tenant.id)
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
    )
