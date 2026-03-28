from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException

from launchlens.config import settings
from launchlens.models.user import User

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
