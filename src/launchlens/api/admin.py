from fastapi import APIRouter, Depends

from launchlens.api.deps import require_admin
from launchlens.models.user import User

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
    return {"status": "ok", "detail": "admin"}


@router.get("/health")
async def admin_health(admin_user: User = Depends(require_admin)):
    return {"status": "ok", "role": admin_user.role.value}
