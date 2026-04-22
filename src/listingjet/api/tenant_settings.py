"""
Tenant settings API — non-admin users can manage their own tenant config.

Endpoints:
  GET  /settings              — view current tenant settings
  PATCH /settings             — update webhook URL
  POST /settings/test-webhook — test webhook delivery
  GET  /settings/usage        — current month usage vs plan limits
  POST /settings/api-keys     — create an API key
  GET  /settings/api-keys     — list API keys
  DELETE /settings/api-keys/{id} — revoke an API key
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.listing import Listing
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.plan_limits import get_limits

router = APIRouter()


SUPPORTED_LANGUAGES = {"en", "es", "fr", "de", "pt", "zh", "ja", "ko", "it", "ar"}


class TenantSettingsResponse(BaseModel):
    tenant_id: uuid.UUID
    name: str
    plan: str
    webhook_url: str | None
    preferred_language: str = "en"
    auto_approve_enabled: bool = False
    auto_approve_threshold: float = 85.0

    model_config = {"from_attributes": True}


class UpdateSettingsRequest(BaseModel):
    webhook_url: str | None = None
    preferred_language: str | None = None
    auto_approve_enabled: bool | None = None
    auto_approve_threshold: float | None = None

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language. Choose from: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        if v:
            from urllib.parse import urlparse
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Webhook URL must use http or https")
            if not parsed.hostname:
                raise ValueError("Webhook URL must have a valid hostname")
        return v


@router.get("", response_model=TenantSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current tenant's name, plan, and webhook URL configuration."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantSettingsResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        webhook_url=tenant.webhook_url,
        preferred_language=tenant.preferred_language,
        auto_approve_enabled=tenant.auto_approve_enabled,
        auto_approve_threshold=tenant.auto_approve_threshold,
    )


@router.patch("", response_model=TenantSettingsResponse)
async def update_settings(
    body: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant settings such as the outbound webhook URL."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.webhook_url is not None:
        if body.webhook_url:
            from listingjet.services.webhook_delivery import _is_url_safe
            if not _is_url_safe(body.webhook_url):
                raise HTTPException(status_code=400, detail="Webhook URL must not target private/internal IP ranges")
        tenant.webhook_url = body.webhook_url or None
    if body.preferred_language is not None:
        tenant.preferred_language = body.preferred_language
    if body.auto_approve_enabled is not None:
        tenant.auto_approve_enabled = body.auto_approve_enabled
    if body.auto_approve_threshold is not None:
        if not (50.0 <= body.auto_approve_threshold <= 100.0):
            raise HTTPException(400, "auto_approve_threshold must be between 50 and 100")
        tenant.auto_approve_threshold = body.auto_approve_threshold

    await db.commit()
    await db.refresh(tenant)
    return TenantSettingsResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        webhook_url=tenant.webhook_url,
        preferred_language=tenant.preferred_language,
        auto_approve_enabled=tenant.auto_approve_enabled,
        auto_approve_threshold=tenant.auto_approve_threshold,
    )


@router.post("/test-webhook")
async def test_my_webhook(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test event to your tenant's webhook URL."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL configured. Set one via PATCH /settings first.")

    from listingjet.services.webhook_delivery import deliver_webhook

    success = await deliver_webhook(
        url=tenant.webhook_url,
        event_type="webhook.test",
        payload={"message": "Test webhook from ListingJet", "tenant_name": tenant.name},
        tenant_id=str(tenant.id),
    )

    return {"delivered": success, "webhook_url": tenant.webhook_url}


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current month usage vs plan limits."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    limits = get_limits(tenant.plan, tenant.plan_overrides)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    listing_count = (await db.execute(
        select(func.count(Listing.id)).where(
            Listing.tenant_id == current_user.tenant_id,
            Listing.created_at >= month_start,
            Listing.is_demo.is_(False),
        )
    )).scalar() or 0

    return {
        "plan": tenant.plan,
        "period": month_start.strftime("%Y-%m"),
        "listings": {
            "used": listing_count,
            "limit": limits["max_listings_per_month"],
            "remaining": max(0, limits["max_listings_per_month"] - listing_count),
        },
        "features": {
            "max_assets_per_listing": limits["max_assets_per_listing"],
            "tier2_vision": limits["tier2_vision"],
            "social_content": limits.get("social_content", False),
        },
    }


# --- API Key Management ---

class CreateAPIKeyRequest(BaseModel):
    name: str


@router.post("/api-keys", status_code=201)
async def create_api_key_endpoint(
    body: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The plaintext key is returned ONCE."""
    from listingjet.services.api_keys import create_api_key

    api_key, plaintext = await create_api_key(
        session=db,
        tenant_id=current_user.tenant_id,
        name=body.name,
    )
    await db.commit()

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": plaintext,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "warning": "Save this key now. It cannot be retrieved again.",
    }


@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current tenant (hashes hidden)."""
    from listingjet.models.api_key import APIKey

    result = await db.execute(
        select(APIKey)
        .where(APIKey.tenant_id == current_user.tenant_id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) an API key."""
    from listingjet.models.api_key import APIKey

    api_key = (await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.commit()
    return {"id": str(key_id), "revoked": True}
