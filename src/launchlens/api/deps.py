from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from launchlens.database import get_db


async def get_current_tenant(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tenant_id


async def require_admin(request: Request) -> str:
    # Placeholder — full role check in Task 6+
    return await get_current_tenant(request)
