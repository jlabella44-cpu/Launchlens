"""
Tenant settings API — non-admin users can manage their own tenant config.

Endpoints:
  GET  /settings         — view current tenant settings
  PATCH /settings        — update webhook URL, brand kit URL
  POST /settings/test-webhook — test webhook delivery
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user, get_db
from launchlens.models.tenant import Tenant
from launchlens.models.user import User

router = APIRouter()


class TenantSettingsResponse(BaseModel):
    tenant_id: uuid.UUID
    name: str
    plan: str
    webhook_url: str | None

    model_config = {"from_attributes": True}


class UpdateSettingsRequest(BaseModel):
    webhook_url: str | None = None


@router.get("", response_model=TenantSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantSettingsResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        webhook_url=tenant.webhook_url,
    )


@router.patch("", response_model=TenantSettingsResponse)
async def update_settings(
    body: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.webhook_url is not None:
        tenant.webhook_url = body.webhook_url or None

    await db.commit()
    await db.refresh(tenant)
    return TenantSettingsResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        webhook_url=tenant.webhook_url,
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

    from launchlens.services.webhook_delivery import deliver_webhook

    success = await deliver_webhook(
        url=tenant.webhook_url,
        event_type="webhook.test",
        payload={"message": "Test webhook from LaunchLens", "tenant_name": tenant.name},
        tenant_id=str(tenant.id),
    )

    return {"delivered": success, "webhook_url": tenant.webhook_url}
