"""OAuth service for social platform connections (Meta, TikTok).

Handles authorization URL generation, token exchange, and refresh.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from listingjet.config import settings

logger = logging.getLogger(__name__)

_META_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
_META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
_META_LONG_LIVED_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
_TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize"
_TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

META_SCOPES_INSTAGRAM = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
META_SCOPES_FACEBOOK = "pages_manage_posts,pages_read_engagement,pages_show_list"
TIKTOK_SCOPES = "user.info.basic,video.publish"


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]
    platform_user_id: str | None = None
    page_id: str | None = None
    page_name: str | None = None


class SocialOAuthService:
    """Generate auth URLs and exchange codes for tokens."""

    def get_meta_auth_url(self, platform: str, state: str) -> str:
        """Generate Meta OAuth URL for Instagram or Facebook."""
        scopes = META_SCOPES_INSTAGRAM if platform == "instagram" else META_SCOPES_FACEBOOK
        params = {
            "client_id": settings.meta_app_id,
            "redirect_uri": settings.meta_redirect_uri,
            "scope": scopes,
            "response_type": "code",
            "state": f"{platform}:{state}",
        }
        return f"{_META_AUTH_URL}?{urlencode(params)}"

    def get_tiktok_auth_url(self, state: str) -> str:
        """Generate TikTok OAuth URL."""
        params = {
            "client_key": settings.tiktok_client_key,
            "redirect_uri": settings.tiktok_redirect_uri,
            "scope": TIKTOK_SCOPES,
            "response_type": "code",
            "state": f"tiktok:{state}",
        }
        return f"{_TIKTOK_AUTH_URL}?{urlencode(params)}"

    async def exchange_meta_code(self, code: str) -> OAuthTokens:
        """Exchange Meta auth code for short-lived token, then upgrade to long-lived."""
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for short-lived token
            resp = await client.get(
                _META_TOKEN_URL,
                params={
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "redirect_uri": settings.meta_redirect_uri,
                    "code": code,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            short_token = data["access_token"]

            # Step 2: Exchange for long-lived token (~60 days)
            resp2 = await client.get(
                _META_LONG_LIVED_URL,
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "fb_exchange_token": short_token,
                },
            )
            resp2.raise_for_status()
            long_data = resp2.json()
            access_token = long_data["access_token"]
            expires_in = long_data.get("expires_in", 5184000)  # ~60 days

            # Step 3: Get user info and pages
            me_resp = await client.get(
                "https://graph.facebook.com/v21.0/me",
                params={"access_token": access_token, "fields": "id,name"},
            )
            me_resp.raise_for_status()
            me = me_resp.json()

            # Get pages for page-level posting
            pages_resp = await client.get(
                f"https://graph.facebook.com/v21.0/{me['id']}/accounts",
                params={"access_token": access_token},
            )
            pages_resp.raise_for_status()
            pages = pages_resp.json().get("data", [])
            page = pages[0] if pages else None

            return OAuthTokens(
                access_token=page["access_token"] if page else access_token,
                refresh_token=None,  # Meta uses long-lived tokens, no refresh
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                scopes=long_data.get("scope", "").split(",") if isinstance(long_data.get("scope"), str) else [],
                platform_user_id=me["id"],
                page_id=page["id"] if page else None,
                page_name=page["name"] if page else me.get("name"),
            )

    async def exchange_tiktok_code(self, code: str) -> OAuthTokens:
        """Exchange TikTok auth code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TIKTOK_TOKEN_URL,
                json={
                    "client_key": settings.tiktok_client_key,
                    "client_secret": settings.tiktok_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.tiktok_redirect_uri,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token_data = data.get("data", data)

            return OAuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 86400)),
                scopes=token_data.get("scope", "").split(",") if isinstance(token_data.get("scope"), str) else [],
                platform_user_id=token_data.get("open_id"),
            )

    async def refresh_tiktok_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired TikTok access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TIKTOK_TOKEN_URL,
                json={
                    "client_key": settings.tiktok_client_key,
                    "client_secret": settings.tiktok_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", resp.json())
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 86400)),
                scopes=[],
            )
