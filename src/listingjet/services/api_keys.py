"""
API key management service.

Keys are generated as `ll_` + 32 random hex chars. Only the SHA-256 hash
is stored; the plaintext is returned once at creation time.
"""
import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.api_key import APIKey

_PREFIX = "ll_"


def generate_key() -> str:
    """Generate a new API key: ll_ + 32 hex chars."""
    return f"{_PREFIX}{secrets.token_hex(16)}"


def hash_key(key: str) -> str:
    """SHA-256 hash of the key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(session: AsyncSession, tenant_id, name: str) -> tuple[APIKey, str]:
    """Create a new API key. Returns (model, plaintext_key)."""
    plaintext = generate_key()
    api_key = APIKey(
        tenant_id=tenant_id,
        key_hash=hash_key(plaintext),
        name=name,
    )
    session.add(api_key)
    await session.flush()
    return api_key, plaintext


async def validate_api_key(session: AsyncSession, key: str) -> APIKey | None:
    """Look up an API key by its plaintext value. Returns None if invalid/inactive."""
    h = hash_key(key)
    result = await session.execute(
        select(APIKey).where(APIKey.key_hash == h, APIKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.last_used_at = datetime.now(timezone.utc)
        await session.flush()
    return api_key
