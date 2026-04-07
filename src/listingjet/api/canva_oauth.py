"""
Canva OAuth2 PKCE flow — per-tenant Canva integration.

Endpoints:
  GET  /auth/canva           — redirect user to Canva authorization (requires auth)
  GET  /auth/canva/callback  — handle Canva redirect, exchange code for tokens (public)
"""
import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config import settings
from listingjet.database import AsyncSessionLocal, get_db
from listingjet.models.brand_kit import BrandKit
from listingjet.models.user import User
from listingjet.services.auth import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# PKCE state store — Redis preferred, in-memory fallback
# ---------------------------------------------------------------------------
_PKCE_TTL_SECONDS = 600

# In-memory fallback: {state: {code_verifier, tenant_id, expires_at}}
_memory_store: dict[str, dict] = {}


def _clean_memory_store() -> None:
    """Evict expired entries from the in-memory store."""
    now = time.time()
    expired = [k for k, v in _memory_store.items() if v["expires_at"] < now]
    for k in expired:
        _memory_store.pop(k, None)


async def _store_pkce(
    request: Request,
    state: str,
    code_verifier: str,
    tenant_id: uuid.UUID,
) -> None:
    """Persist PKCE params keyed by *state*."""
    payload = json.dumps({"code_verifier": code_verifier, "tenant_id": str(tenant_id)})
    redis = getattr(getattr(request, "app", None), "state", None)
    redis = getattr(redis, "redis", None) if redis else None
    if redis:
        try:
            await asyncio.to_thread(redis.setex, f"canva_pkce:{state}", _PKCE_TTL_SECONDS, payload)
            return
        except Exception:
            logger.warning("canva_oauth.redis_store_failed — falling back to memory")
    _clean_memory_store()
    _memory_store[state] = {
        "code_verifier": code_verifier,
        "tenant_id": str(tenant_id),
        "expires_at": time.time() + _PKCE_TTL_SECONDS,
    }


async def _load_pkce(request: Request, state: str) -> dict | None:
    """Retrieve and delete PKCE params by *state*."""
    redis = getattr(getattr(request, "app", None), "state", None)
    redis = getattr(redis, "redis", None) if redis else None
    if redis:
        try:
            raw = await asyncio.to_thread(redis.get, f"canva_pkce:{state}")
            if raw:
                await asyncio.to_thread(redis.delete, f"canva_pkce:{state}")
                return json.loads(raw)
        except Exception:
            logger.warning("canva_oauth.redis_load_failed — falling back to memory")
    entry = _memory_store.pop(state, None)
    if entry and entry["expires_at"] >= time.time():
        return {"code_verifier": entry["code_verifier"], "tenant_id": entry["tenant_id"]}
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_CANVA_SCOPES = (
    "design:content:read design:content:write "
    "asset:read asset:write "
    "brandtemplate:meta:read brandtemplate:content:read brandtemplate:content:write"
)


def _generate_code_verifier() -> str:
    """128-char base64url random string (PKCE code_verifier)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(96)).rstrip(b"=").decode("ascii")


def _generate_code_challenge(verifier: str) -> str:
    """S256 code_challenge from verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _redirect_uri() -> str:
    return getattr(settings, "canva_redirect_uri", None) or "https://api.listingjet.ai/auth/canva/callback"


def _frontend_redirect() -> str:
    return getattr(settings, "canva_frontend_redirect", None) or "https://listingjet.ai/settings/brand-kit"


def _decode_jwt_payload(token: str) -> dict:
    """Decode a JWT payload WITHOUT signature verification (Canva access_token)."""
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload_b64 = parts[1]
    # Add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/canva")
async def canva_authorize(
    request: Request,
    token: str | None = Query(None, description="JWT for browser redirect auth"),
    db: AsyncSession = Depends(get_db),
):
    """Initiate Canva OAuth2 PKCE flow — redirects user to Canva."""
    # Resolve user manually: query param first (browser redirect), then cookie.
    jwt_token: str | None = token
    if not jwt_token:
        jwt_token = request.cookies.get("access_token")
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(jwt_token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    current_user = await db.get(User, user_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    if not settings.canva_client_id:
        raise HTTPException(status_code=503, detail="Canva OAuth not configured")

    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    await _store_pkce(request, state, code_verifier, current_user.tenant_id)

    params = {
        "response_type": "code",
        "client_id": settings.canva_client_id,
        "redirect_uri": _redirect_uri(),
        "scope": _CANVA_SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    from urllib.parse import urlencode
    auth_url = f"https://www.canva.com/api/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/canva/callback")
async def canva_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Canva OAuth2 callback — exchange code for tokens, store in BrandKit."""
    import httpx

    pkce = await _load_pkce(request, state)
    if not pkce:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    code_verifier = pkce["code_verifier"]
    tenant_id = uuid.UUID(pkce["tenant_id"])

    # Exchange authorization code for tokens
    credentials = base64.b64encode(
        f"{settings.canva_client_id}:{settings.canva_client_secret}".encode()
    ).decode()

    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": _redirect_uri(),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.canva.com/rest/v1/oauth/token",
            data=token_payload,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if resp.status_code != 200:
        logger.error(
            "canva_oauth.token_exchange_failed status=%s",
            resp.status_code,
        )
        raise HTTPException(status_code=502, detail="Failed to exchange Canva authorization code")

    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("canva_oauth.token_missing keys=%s", list(token_data.keys()))
        raise HTTPException(status_code=502, detail="Canva token response missing access_token")
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        logger.error("canva_oauth.refresh_token_missing keys=%s", list(token_data.keys()))
        raise HTTPException(status_code=502, detail="Canva token response missing refresh_token")
    expires_in = token_data.get("expires_in")
    if not expires_in:
        logger.error("canva_oauth.expires_in_missing keys=%s", list(token_data.keys()))
        raise HTTPException(status_code=502, detail="Canva token response missing expires_in")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Extract Canva user ID from JWT
    jwt_payload = _decode_jwt_payload(access_token)
    canva_user_id = jwt_payload.get("sub")

    # Upsert BrandKit with Canva tokens (unscoped session — callback is unauthenticated)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1).with_for_update()
        )
        kit = result.scalar_one_or_none()

        if kit is None:
            kit = BrandKit(id=uuid.uuid4(), tenant_id=tenant_id)
            db.add(kit)

        kit.canva_access_token = access_token
        kit.canva_refresh_token = refresh_token
        kit.canva_token_expires_at = expires_at
        kit.canva_user_id = canva_user_id

        await db.commit()

    logger.info("canva_oauth.connected tenant_id=%s canva_user=%s", tenant_id, canva_user_id)

    frontend_url = f"{_frontend_redirect()}?canva=connected"
    return RedirectResponse(url=frontend_url, status_code=302)
