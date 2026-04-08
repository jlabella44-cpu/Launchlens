"""Social publishing API — OAuth connect, publish now, schedule, status.

Endpoints:
  GET  /social-accounts/{platform}/connect    — initiate OAuth redirect
  GET  /social-accounts/{platform}/callback   — handle OAuth callback (public)
  POST /listings/{id}/social/publish          — publish now
  POST /listings/{id}/social/schedule         — schedule future post
  GET  /listings/{id}/social/posts            — list posts for listing
  PATCH /social/posts/{id}/cancel             — cancel scheduled post
  POST  /social/posts/{id}/retry              — retry failed post
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.social import (
    OAuthRedirectResponse,
    PublishRequest,
    ScheduledPostResponse,
    ScheduleRequest,
)
from listingjet.config import settings
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.scheduled_post import ScheduledPost
from listingjet.models.social_account import SocialAccount
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.social_oauth import SocialOAuthService
from listingjet.services.social_publisher import get_publisher

router = APIRouter()


# ---- Plan gating helpers ----

_PUBLISH_PLANS = {"active_agent", "pro", "team", "enterprise"}
_SCHEDULE_PLANS = {"team", "enterprise"}


def _check_publish_access(tenant: Tenant):
    if tenant.plan not in _PUBLISH_PLANS:
        raise HTTPException(403, "Social publishing requires Active Agent plan or higher")


def _check_schedule_access(tenant: Tenant):
    if tenant.plan not in _SCHEDULE_PLANS:
        raise HTTPException(403, "Post scheduling requires Team plan or higher")


# ---- OAuth Endpoints ----


@router.get("/social-accounts/{platform}/connect")
async def oauth_connect(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthRedirectResponse:
    """Generate OAuth URL for connecting a social account."""
    if platform not in ("instagram", "facebook", "tiktok"):
        raise HTTPException(400, "Unsupported platform")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    _check_publish_access(tenant)

    oauth = SocialOAuthService()
    state = f"{current_user.id}:{current_user.tenant_id}"

    if platform in ("instagram", "facebook"):
        auth_url = oauth.get_meta_auth_url(platform, state)
    else:
        auth_url = oauth.get_tiktok_auth_url(state)

    return OAuthRedirectResponse(auth_url=auth_url)


@router.get("/social-accounts/meta/callback")
async def meta_oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Handle Meta (Instagram/Facebook) OAuth callback."""
    parts = state.split(":")
    if len(parts) < 3:
        raise HTTPException(400, "Invalid OAuth state")

    platform = parts[0]  # "instagram" or "facebook"
    user_id = uuid.UUID(parts[1])
    tenant_id = uuid.UUID(parts[2])

    oauth = SocialOAuthService()
    tokens = await oauth.exchange_meta_code(code)

    # Upsert social account
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        account.access_token_encrypted = tokens.access_token  # TODO: encrypt
        account.token_expires_at = tokens.expires_at
        account.scopes = tokens.scopes
        account.platform_user_id = tokens.platform_user_id
        account.page_id = tokens.page_id
        account.page_name = tokens.page_name
        account.status = "connected"
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            user_id=user_id,
            platform=platform,
            platform_username=tokens.page_name or "",
            platform_user_id=tokens.platform_user_id,
            access_token_encrypted=tokens.access_token,
            token_expires_at=tokens.expires_at,
            scopes=tokens.scopes,
            page_id=tokens.page_id,
            page_name=tokens.page_name,
            status="connected",
        )
        db.add(account)

    await db.commit()
    return RedirectResponse(url=settings.social_publish_frontend_redirect)


@router.get("/social-accounts/tiktok/callback")
async def tiktok_oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Handle TikTok OAuth callback."""
    parts = state.split(":")
    if len(parts) < 3:
        raise HTTPException(400, "Invalid OAuth state")

    user_id = uuid.UUID(parts[1])
    tenant_id = uuid.UUID(parts[2])

    oauth = SocialOAuthService()
    tokens = await oauth.exchange_tiktok_code(code)

    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == "tiktok",
        )
    )
    account = result.scalar_one_or_none()

    if account:
        account.access_token_encrypted = tokens.access_token
        account.refresh_token_encrypted = tokens.refresh_token
        account.token_expires_at = tokens.expires_at
        account.scopes = tokens.scopes
        account.platform_user_id = tokens.platform_user_id
        account.status = "connected"
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            user_id=user_id,
            platform="tiktok",
            platform_username=tokens.platform_user_id or "",
            platform_user_id=tokens.platform_user_id,
            access_token_encrypted=tokens.access_token,
            refresh_token_encrypted=tokens.refresh_token,
            token_expires_at=tokens.expires_at,
            scopes=tokens.scopes,
            status="connected",
        )
        db.add(account)

    await db.commit()
    return RedirectResponse(url=settings.social_publish_frontend_redirect)


# ---- Publish / Schedule Endpoints ----


@router.post("/listings/{listing_id}/social/publish", status_code=201)
async def publish_now(
    listing_id: uuid.UUID,
    body: PublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPostResponse:
    """Publish a post immediately to a connected platform."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    _check_publish_access(tenant)

    # Find connected account
    acct_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == current_user.tenant_id,
            SocialAccount.platform == body.platform,
            SocialAccount.status == "connected",
        ).limit(1)
    )
    account = acct_result.scalar_one_or_none()
    if not account:
        raise HTTPException(409, f"No connected {body.platform} account. Connect one in Settings first.")

    # Create the post record
    post = ScheduledPost(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        platform=body.platform,
        caption=body.caption,
        hashtags=body.hashtags,
        media_s3_keys=body.media_s3_keys,
        status="publishing",
    )
    db.add(post)
    await db.flush()

    # Publish immediately
    publisher = get_publisher(body.platform)
    result = await publisher.publish(account, post)

    if result.success:
        post.status = "published"
        post.platform_post_id = result.platform_post_id
        post.platform_post_url = result.platform_post_url
        post.published_at = datetime.now(timezone.utc)
    else:
        post.status = "failed"
        post.error_message = result.error

    await db.flush()
    await db.refresh(post)
    return ScheduledPostResponse.model_validate(post)


@router.post("/listings/{listing_id}/social/schedule", status_code=201)
async def schedule_post(
    listing_id: uuid.UUID,
    body: ScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPostResponse:
    """Schedule a post for future publishing."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    _check_schedule_access(tenant)

    if body.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(422, "scheduled_at must be in the future")

    post = ScheduledPost(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        platform=body.platform,
        caption=body.caption,
        hashtags=body.hashtags,
        media_s3_keys=body.media_s3_keys,
        scheduled_at=body.scheduled_at,
        status="scheduled",
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)
    return ScheduledPostResponse.model_validate(post)


@router.get("/listings/{listing_id}/social/posts")
async def list_social_posts(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledPostResponse]:
    """List all social posts (scheduled + published + failed) for a listing."""
    result = await db.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.listing_id == listing_id,
            ScheduledPost.tenant_id == current_user.tenant_id,
        )
        .order_by(ScheduledPost.created_at.desc())
    )
    return [ScheduledPostResponse.model_validate(p) for p in result.scalars().all()]


@router.patch("/social/posts/{post_id}/cancel")
async def cancel_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPostResponse:
    """Cancel a scheduled post."""
    post = await db.get(ScheduledPost, post_id)
    if not post or post.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "Post not found")
    if post.status != "scheduled":
        raise HTTPException(409, f"Cannot cancel post with status '{post.status}'")

    post.status = "cancelled"
    await db.flush()
    await db.refresh(post)
    return ScheduledPostResponse.model_validate(post)


@router.post("/social/posts/{post_id}/retry")
async def retry_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledPostResponse:
    """Retry a failed post."""
    post = await db.get(ScheduledPost, post_id)
    if not post or post.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "Post not found")
    if post.status != "failed":
        raise HTTPException(409, f"Cannot retry post with status '{post.status}'")

    # Find connected account
    acct_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == current_user.tenant_id,
            SocialAccount.platform == post.platform,
            SocialAccount.status == "connected",
        ).limit(1)
    )
    account = acct_result.scalar_one_or_none()
    if not account:
        raise HTTPException(409, f"No connected {post.platform} account")

    post.status = "publishing"
    post.error_message = None
    await db.flush()

    publisher = get_publisher(post.platform)
    result = await publisher.publish(account, post)

    if result.success:
        post.status = "published"
        post.platform_post_id = result.platform_post_id
        post.platform_post_url = result.platform_post_url
        post.published_at = datetime.now(timezone.utc)
    else:
        post.retry_count += 1
        post.status = "failed"
        post.error_message = result.error

    await db.flush()
    await db.refresh(post)
    return ScheduledPostResponse.model_validate(post)
