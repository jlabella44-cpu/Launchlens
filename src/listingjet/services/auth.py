import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
from fastapi import HTTPException

from listingjet.config import settings
from listingjet.models.user import User

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"

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
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google ID token and return the user's email, name, and sub."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": id_token})
    if resp.status_code != 200:
        logger.warning("google token verification failed: %s", resp.text)
        raise HTTPException(status_code=401, detail="Invalid Google token")

    payload = resp.json()

    # Verify the token was issued for our app
    if payload.get("aud") != settings.google_oauth_client_id:
        logger.warning("google token audience mismatch: %s", payload.get("aud"))
        raise HTTPException(status_code=401, detail="Invalid Google token audience")

    if payload.get("email_verified") != "true":
        raise HTTPException(status_code=401, detail="Google email not verified")

    return {
        "email": payload["email"].strip().lower(),
        "name": payload.get("name"),
        "google_sub": payload["sub"],
    }
