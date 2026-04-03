from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from listingjet.config import settings
from listingjet.models.user import User

# Pre-computed dummy hash for constant-time comparison when user not found.
# Prevents timing-based user enumeration attacks.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode()


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
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
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
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> JSONResponse:
    """Attach httpOnly, Secure, SameSite cookies for both tokens."""
    is_prod = settings.app_env != "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_expiry_hours * 3600,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_refresh_expiry_days * 86400,
        path="/auth/refresh",
    )
    return response


def clear_auth_cookies(response: JSONResponse) -> JSONResponse:
    """Remove auth cookies on logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return response
