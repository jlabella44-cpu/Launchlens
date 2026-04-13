"""White-label branding API — public branding endpoint + admin config.

Endpoints:
  GET   /branding                  — public, returns theme for current domain/tenant
  GET   /settings/white-label      — current white-label config (Team+)
  PATCH /settings/white-label      — update white-label settings (Team+)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.database import get_db
from listingjet.models.brand_kit import BrandKit
from listingjet.models.tenant import Tenant
from listingjet.models.user import User

router = APIRouter()

_WHITE_LABEL_PLANS = {"team", "enterprise"}

# Default ListingJet branding (fallback when no white-label configured)
_DEFAULT_BRANDING = {
    "app_name": "ListingJet",
    "tagline": "From raw listing media to launch-ready marketing in minutes",
    "logo_url": None,
    "favicon_url": None,
    "primary_color": "#2563EB",
    "secondary_color": "#F97316",
    "font_primary": None,
    "brokerage_name": None,
    "powered_by_visible": False,
    "white_label_enabled": False,
}


class BrandingResponse(BaseModel):
    app_name: str
    tagline: str
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str
    secondary_color: str
    font_primary: str | None = None
    brokerage_name: str | None = None
    powered_by_visible: bool = False
    white_label_enabled: bool = False


class WhiteLabelUpdateRequest(BaseModel):
    custom_domain: str | None = Field(None, max_length=255)
    white_label_enabled: bool | None = None
    app_name: str | None = Field(None, max_length=100)
    tagline: str | None = Field(None, max_length=255)
    favicon_url: str | None = Field(None, max_length=500)
    login_bg_url: str | None = Field(None, max_length=500)
    email_header_color: str | None = Field(None, max_length=7)
    email_footer_text: str | None = Field(None, max_length=500)
    powered_by_visible: bool | None = None


class WhiteLabelConfigResponse(BaseModel):
    custom_domain: str | None = None
    domain_verified: bool = False
    white_label_enabled: bool = False
    app_name: str | None = None
    tagline: str | None = None
    favicon_url: str | None = None
    login_bg_url: str | None = None
    email_header_color: str | None = None
    email_footer_text: str | None = None
    powered_by_visible: bool = True
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    brokerage_name: str | None = None


@router.get("/branding")
async def get_branding(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BrandingResponse:
    """Public endpoint — returns branding config for the current domain or tenant.

    Checks Host header for custom domain mapping. Falls back to authenticated
    tenant's brand kit, or default ListingJet branding.
    """
    host = request.headers.get("host", "")
    brand_kit = None

    # Try custom domain lookup (strips port for local dev)
    domain = host.split(":")[0] if host else ""
    if domain and domain not in ("localhost", "listingjet.ai", "api.listingjet.ai"):
        from listingjet.database import AsyncSessionLocal
        async with AsyncSessionLocal() as admin_db:
            result = await admin_db.execute(
                select(BrandKit).where(
                    BrandKit.custom_domain == domain,
                    BrandKit.white_label_enabled.is_(True),
                )
            )
            brand_kit = result.scalar_one_or_none()

    # Fall back to authenticated tenant's brand kit
    if not brand_kit:
        tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
        if tenant_id:
            result = await db.execute(
                select(BrandKit).where(BrandKit.tenant_id == tenant_id)
            )
            brand_kit = result.scalar_one_or_none()

    if not brand_kit:
        return BrandingResponse(**_DEFAULT_BRANDING)

    return BrandingResponse(
        app_name=brand_kit.app_name or brand_kit.brokerage_name or "ListingJet",
        tagline=brand_kit.tagline or _DEFAULT_BRANDING["tagline"],
        logo_url=brand_kit.logo_url,
        favicon_url=brand_kit.favicon_url,
        primary_color=brand_kit.primary_color or _DEFAULT_BRANDING["primary_color"],
        secondary_color=brand_kit.secondary_color or _DEFAULT_BRANDING["secondary_color"],
        font_primary=brand_kit.font_primary,
        brokerage_name=brand_kit.brokerage_name,
        powered_by_visible=brand_kit.powered_by_visible if brand_kit.white_label_enabled else False,
        white_label_enabled=brand_kit.white_label_enabled,
    )


@router.get("/settings/white-label")
async def get_white_label_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WhiteLabelConfigResponse:
    """Get current white-label configuration (Team+ only)."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant or tenant.plan not in _WHITE_LABEL_PLANS:
        raise HTTPException(403, "White-label requires Team or Enterprise plan")

    result = await db.execute(
        select(BrandKit).where(BrandKit.tenant_id == current_user.tenant_id)
    )
    kit = result.scalar_one_or_none()

    if not kit:
        return WhiteLabelConfigResponse()

    return WhiteLabelConfigResponse(
        custom_domain=kit.custom_domain,
        domain_verified=kit.domain_verified,
        white_label_enabled=kit.white_label_enabled,
        app_name=kit.app_name,
        tagline=kit.tagline,
        favicon_url=kit.favicon_url,
        login_bg_url=kit.login_bg_url,
        email_header_color=kit.email_header_color,
        email_footer_text=kit.email_footer_text,
        powered_by_visible=kit.powered_by_visible,
        logo_url=kit.logo_url,
        primary_color=kit.primary_color,
        secondary_color=kit.secondary_color,
        brokerage_name=kit.brokerage_name,
    )


@router.patch("/settings/white-label")
async def update_white_label(
    body: WhiteLabelUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WhiteLabelConfigResponse:
    """Update white-label settings (Team+ only)."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant or tenant.plan not in _WHITE_LABEL_PLANS:
        raise HTTPException(403, "White-label requires Team or Enterprise plan")

    result = await db.execute(
        select(BrandKit).where(BrandKit.tenant_id == current_user.tenant_id)
    )
    kit = result.scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Set up your Brand Kit first before configuring white-label")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(kit, field, value)

    # Reset domain verification when domain changes
    if body.custom_domain is not None:
        kit.domain_verified = False

    await db.flush()
    await db.refresh(kit)
    return await get_white_label_config(current_user, db)
