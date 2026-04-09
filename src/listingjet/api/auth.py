import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
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
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    set_auth_cookies,
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
    plan = _TIER_TO_PLAN.get(tier, "free")

    tenant = Tenant(id=uuid.uuid4(), name=body.company_name, plan=plan, billing_model="credit")
    db.add(tenant)
    await db.flush()

    # Create credit account with initial grant
    credit_account = CreditAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        balance=tier_config["included_credits"],
        granted_balance=tier_config["included_credits"],
        purchased_balance=0,
        rollover_cap=tier_config["rollover_cap"],
    )
    db.add(credit_account)

    from datetime import datetime, timezone
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.ADMIN,
        consent_at=datetime.now(timezone.utc),
        consent_version="2026-04-03",
        ai_consent_at=datetime.now(timezone.utc) if body.ai_consent else None,
        ai_consent_version="1.0" if body.ai_consent else None,
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

    # Send welcome drip email #1 (fire-and-forget)
    # Full drip sequence: welcome_drip_1 (now), _2 (day 1), _3 (day 3), _4 (day 5), _5 (day 10)
    # Subsequent drips are triggered by a scheduled task (see services/drip_scheduler.py)
    try:
        from listingjet.services.email import get_email_service
        email_svc = get_email_service()
        email_svc.send_notification(
            user.email,
            "welcome_drip_1",
            name=user.name or "there",
            upload_url="https://app.listingjet.com/listings",
        )
    except Exception:
        logger.exception("welcome email failed for user=%s", user.id)

    logger.info("auth.register tenant=%s tier=%s", tenant.id, tier)
    access = create_access_token(user)
    refresh = create_refresh_token(user)
    body = TokenResponse(access_token=access, refresh_token=refresh)
    return set_auth_cookies(JSONResponse(content=body.model_dump()), access, refresh)


_LOGIN_LOCKOUT_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_WINDOW = 900  # 15 minutes


def _get_lockout_redis(request: Request | None = None):
    """Get Redis client — prefer shared pool from app.state, fall back to new connection."""
    if request is not None:
        pool = getattr(getattr(request, "app", None), "state", None)
        r = getattr(pool, "redis", None)
        if r is not None:
            return r
    import redis as redis_lib  # noqa: I001

    from listingjet.config import settings as _settings

    return redis_lib.from_url(_settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, _rl=Depends(rate_limit(10, 60)), db: AsyncSession = Depends(get_db)):
    import hashlib
    email = body.email.strip().lower()
    email_hash = hashlib.sha256(email.encode()).hexdigest()[:12]

    # Account lockout: check if too many failed attempts
    lockout_key = f"login_failures:{email_hash}"
    try:
        r = _get_lockout_redis(request)
        attempts = int(r.get(lockout_key) or 0)
        if attempts >= _LOGIN_LOCKOUT_MAX_ATTEMPTS:
            ttl = r.ttl(lockout_key)
            logger.warning("auth.login_locked email_hash=%s attempts=%d", email_hash, attempts)
            raise HTTPException(
                status_code=429,
                detail=f"Account temporarily locked due to too many failed attempts. Try again in {max(ttl, 60)} seconds.",
                headers={"Retry-After": str(max(ttl, 60))},
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down — fail open, don't block logins

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Constant-time comparison: always run bcrypt even if user not found
    password_valid = verify_password_constant_time(
        body.password, user.password_hash if user else None
    )
    if not user or not password_valid:
        # Increment failure counter in Redis
        try:
            r = _get_lockout_redis(request)
            pipe = r.pipeline()
            pipe.incr(lockout_key)
            pipe.expire(lockout_key, _LOGIN_LOCKOUT_WINDOW)
            pipe.execute()
        except Exception:
            pass  # Redis down — fail open
        logger.warning("auth.login_failed email_hash=%s", email_hash)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Successful login — clear failure counter
    try:
        r = _get_lockout_redis(request)
        r.delete(lockout_key)
    except Exception:
        pass

    ip = request.client.host if request.client else "unknown"
    await emit_event(
        session=db,
        event_type="user.login",
        payload={"user_id": str(user.id), "ip": ip},
        tenant_id=str(user.tenant_id),
    )
    await db.commit()

    logger.info("auth.login_success email_hash=%s user=%s", email_hash, user.id)
    access = create_access_token(user)
    refresh = create_refresh_token(user)
    body = TokenResponse(access_token=access, refresh_token=refresh)
    return set_auth_cookies(JSONResponse(content=body.model_dump()), access, refresh)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


class AiConsentRequest(BaseModel):
    consent: bool


@router.post("/ai-consent")
async def update_ai_consent(
    body: AiConsentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record or revoke AI processing consent for the current user."""
    from datetime import datetime, timezone
    user = await db.get(User, current_user.id)
    if body.consent:
        user.ai_consent_at = datetime.now(timezone.utc)
        user.ai_consent_version = "1.0"
    else:
        user.ai_consent_at = None
        user.ai_consent_version = None
    await db.commit()
    return {"ai_consent": body.consent, "ai_consent_at": str(user.ai_consent_at) if user.ai_consent_at else None}


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", dependencies=[Depends(rate_limit(3, 60))])
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password reset email. Always returns 200 to prevent user enumeration."""
    from datetime import datetime, timedelta, timezone

    import jwt as pyjwt

    from listingjet.config import settings

    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user:
        reset_token = pyjwt.encode(
            {
                "sub": str(user.id),
                "type": "password_reset",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        try:
            from listingjet.services.email import get_email_service
            email_svc = get_email_service()
            email_svc.send(
                to=email,
                subject="Reset your ListingJet password",
                html_body=(
                    f"<p>You requested a password reset.</p>"
                    f"<p><a href='https://app.listingjet.com/reset-password?token={reset_token}'>"
                    f"Click here to reset your password</a></p>"
                    f"<p>This link expires in 15 minutes.</p>"
                    f"<p>If you didn't request this, you can safely ignore this email.</p>"
                ),
            )
        except Exception:
            logger.exception("password_reset_email_failed for user=%s", user.id)

    # Always return 200 to prevent user enumeration
    return {"status": "ok", "message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password", dependencies=[Depends(rate_limit(5, 60))])
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a token from the forgot-password email."""
    import jwt as pyjwt

    from listingjet.config import settings

    try:
        payload = pyjwt.decode(body.token, settings.jwt_secret, algorithms=["HS256"])
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Validate new password
    from listingjet.api.schemas.auth import RegisterRequest
    try:
        RegisterRequest.password_complexity(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    logger.info("auth.password_reset user=%s", user.id)
    return {"status": "ok", "message": "Password has been reset. You can now log in."}


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit(10, 60))])
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    # Try cookie first, then Authorization header (backward compat)
    token = request.cookies.get("refresh_token")
    if not token:
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

    access = create_access_token(user)
    refresh = create_refresh_token(user)
    body = TokenResponse(access_token=access, refresh_token=refresh)
    return set_auth_cookies(JSONResponse(content=body.model_dump()), access, refresh)


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint. Revokes tokens server-side and clears httpOnly cookies."""
    from listingjet.services.auth import revoke_token

    # Revoke access token (from header or cookie)
    access_token = request.cookies.get("access_token")
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
    if access_token:
        revoke_token(access_token)

    # Revoke refresh token
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        revoke_token(refresh_token)

    return clear_auth_cookies(JSONResponse(content={"status": "ok"}))


# ---------------------------------------------------------------------------
# Account Deletion (GDPR/CCPA — "right to be forgotten")
# ---------------------------------------------------------------------------


class DeleteAccountRequest(BaseModel):
    confirmation: str  # Must be "DELETE" to confirm


@router.post("/delete-account")
async def delete_account(
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete account and all associated tenant data (GDPR/CCPA right-to-erasure).

    Performs a cascading delete of all tenant-scoped data, then removes the
    tenant and user records. Irreversible.
    """
    if body.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail='Confirmation must be the string "DELETE"')

    tenant_id = current_user.tenant_id
    tenant = await db.get(Tenant, tenant_id)
    tenant_name = tenant.name if tenant else "unknown"

    # Emit audit event before deletion
    await emit_event(
        session=db,
        event_type="account.deleted",
        payload={
            "user_id": str(current_user.id),
            "tenant_id": str(tenant_id),
            "tenant_name": tenant_name,
        },
        tenant_id=str(tenant_id),
    )

    # Cascade delete all tenant-scoped data
    from listingjet.services.account_lifecycle import delete_tenant_data
    await delete_tenant_data(db, tenant_id)

    await db.commit()

    logger.info("account.deleted user=%s tenant=%s", current_user.id, tenant_id)
    resp = JSONResponse(content={
        "status": "deleted",
        "message": "Your account and all associated data have been permanently deleted.",
    })
    return clear_auth_cookies(resp)


@router.get("/export-data")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all personal data for the current user's tenant (GDPR data portability)."""
    from listingjet.services.account_lifecycle import export_tenant_data
    data = await export_tenant_data(db, current_user.tenant_id, current_user.id)
    return data


# ---------------------------------------------------------------------------
# Google Sign-In
# ---------------------------------------------------------------------------

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_google_jwks_cache: dict | None = None
_google_jwks_fetched_at: float = 0
_GOOGLE_JWKS_TTL = 43200  # 12 hours


async def _get_google_jwks() -> dict:
    """Fetch and cache Google's public JWKS for ID token verification (12h TTL)."""
    global _google_jwks_cache, _google_jwks_fetched_at
    import time
    now = time.time()
    if _google_jwks_cache is not None and (now - _google_jwks_fetched_at) < _GOOGLE_JWKS_TTL:
        return _google_jwks_cache
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GOOGLE_JWKS_URL)
        resp.raise_for_status()
        _google_jwks_cache = resp.json()
        _google_jwks_fetched_at = now
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
        logger.info("auth.google_login user=%s", user.id)
        access = create_access_token(user)
        refresh = create_refresh_token(user)
        body = TokenResponse(access_token=access, refresh_token=refresh)
        return set_auth_cookies(JSONResponse(content=body.model_dump()), access, refresh)

    # New user — auto-register with default plan
    tenant = Tenant(id=uuid.uuid4(), name=name or email.split("@")[0], plan="free", billing_model="credit")
    db.add(tenant)
    await db.flush()

    from listingjet.models.credit_account import CreditAccount

    credit_account = CreditAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        balance=0,
        granted_balance=0,
        purchased_balance=0,
        rollover_cap=0,
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
        payload={"email": email, "user_id": str(user.id), "provider": "google", "plan": "free"},
        tenant_id=str(tenant.id),
    )
    await db.commit()
    await db.refresh(user)

    logger.info("auth.google_register tenant=%s", tenant.id)
    access = create_access_token(user)
    refresh = create_refresh_token(user)
    body = TokenResponse(access_token=access, refresh_token=refresh)
    return set_auth_cookies(JSONResponse(content=body.model_dump()), access, refresh)
