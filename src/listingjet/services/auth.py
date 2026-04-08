import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from listingjet.config import settings
from listingjet.models.user import User

logger = logging.getLogger(__name__)

# Pre-computed dummy hash for constant-time comparison when user not found.
# Prevents timing-based user enumeration attacks.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode()


def _get_redis():
    import redis as redis_lib
    return redis_lib.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def verify_password_constant_time(plain: str, hashed: str | None) -> bool:
    """Verify password with constant-time behaviour even when user doesn't exist."""
    target = hashed if hashed is not None else _DUMMY_HASH
    return bcrypt.checkpw(plain.encode(), target.encode())


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role.value,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expiry_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Check Redis blocklist for revoked tokens
    if is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    return payload


def revoke_token(token: str) -> None:
    """Add a token to the Redis blocklist. TTL matches the token's remaining lifetime."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                             options={"verify_exp": False})
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 0)
        if ttl <= 0:
            return  # Already expired, no need to blocklist
        r = _get_redis()
        r.set(f"token_revoked:{token}", "1", ex=ttl)
    except Exception:
        logger.warning("token_revoke_failed", exc_info=True)


def is_token_revoked(token: str) -> bool:
    """Check if a token is in the Redis blocklist."""
    try:
        r = _get_redis()
        return r.exists(f"token_revoked:{token}") > 0
    except Exception:
        # Fail open — if Redis is unavailable, allow the token
        return False


def set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> JSONResponse:
    """Attach httpOnly, Secure, SameSite cookies for both tokens."""
    is_prod = settings.app_env != "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_expiry_minutes * 60,
        path="/",
    )
    # Refresh token uses SameSite=strict — it is only ever sent to our own
    # /auth/refresh endpoint, so cross-site POST is not needed.
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        max_age=settings.jwt_refresh_expiry_days * 86400,
        path="/auth/refresh",
    )
    # Add Partitioned attribute (CHIPS) in production for third-party cookie
    # isolation.  Starlette doesn't support the Partitioned flag natively, so
    # we patch the Set-Cookie header directly.
    if is_prod:
        raw_headers = response.raw_headers
        patched: list[tuple[bytes, bytes]] = []
        for name, value in raw_headers:
            if name == b"set-cookie" and b"refresh_token" in value:
                value = value + b"; Partitioned"
            patched.append((name, value))
        response.raw_headers = patched
    return response


def clear_auth_cookies(response: JSONResponse) -> JSONResponse:
    """Remove auth cookies on logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return response
