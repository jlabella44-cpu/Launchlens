"""
Canva token refresh utility.

Looks up the BrandKit for a tenant, refreshes the Canva access token if
expired (or within 5 min of expiry), and returns a valid access token.
"""
import base64
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config import settings
from listingjet.models.brand_kit import BrandKit

logger = logging.getLogger(__name__)

_REFRESH_BUFFER = timedelta(minutes=5)


async def get_valid_canva_token(db: AsyncSession, tenant_id) -> str | None:
    """Return a valid Canva access token for *tenant_id*, refreshing if needed.

    Returns None if the tenant has no Canva tokens stored.
    """
    result = await db.execute(
        select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1).with_for_update()
    )
    kit = result.scalar_one_or_none()
    if not kit or not kit.canva_access_token:
        return None

    # Check if token is still valid (with buffer)
    now = datetime.now(timezone.utc)
    if kit.canva_token_expires_at and kit.canva_token_expires_at > now + _REFRESH_BUFFER:
        return kit.canva_access_token

    # Token expired or about to expire — refresh it
    if not kit.canva_refresh_token:
        logger.warning("canva_tokens.no_refresh_token tenant_id=%s", tenant_id)
        return None

    new_token_data = await _refresh_token(kit.canva_refresh_token)
    if not new_token_data:
        return None

    kit.canva_access_token = new_token_data["access_token"]
    kit.canva_refresh_token = new_token_data.get("refresh_token", kit.canva_refresh_token)
    expires_in = new_token_data.get("expires_in", 3600)
    kit.canva_token_expires_at = now + timedelta(seconds=expires_in)

    await db.flush()
    logger.info("canva_tokens.refreshed tenant_id=%s", tenant_id)
    return kit.canva_access_token


async def _refresh_token(refresh_token: str) -> dict | None:
    """Exchange a refresh token for new Canva tokens."""
    credentials = base64.b64encode(
        f"{settings.canva_client_id}:{settings.canva_client_secret}".encode()
    ).decode()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.canva.com/rest/v1/oauth/token",
                data=payload,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        if resp.status_code != 200:
            logger.error(
                "canva_tokens.refresh_failed status=%s body=%s",
                resp.status_code,
                resp.text,
            )
            return None
        return resp.json()
    except Exception:
        logger.exception("canva_tokens.refresh_error")
        return None
