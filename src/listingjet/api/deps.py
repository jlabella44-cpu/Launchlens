import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.database import AsyncSessionLocal, get_db
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.auth import decode_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Prefer explicit Authorization header, fall back to httpOnly cookie.
    # This ordering is critical: httpx and browsers may persist cookies
    # across requests, so an explicit Bearer header must take priority
    # to avoid using a stale cookie from a different user/session.
    token: str | None = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Soft-delete gate: even with a valid JWT, users of a deactivated
    # tenant must be denied. Mirrors the TenantMiddleware check so this
    # holds when the middleware is bypassed (ASGI transport in tests).
    tenant = await db.get(Tenant, user.tenant_id)
    if tenant is None or tenant.deactivated_at is not None:
        raise HTTPException(status_code=401, detail="Tenant deactivated")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Tenant admin — manages own tenant."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """Platform superadmin — can manage all tenants."""
    if user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return user


async def get_db_admin():
    """DB session with explicit admin RLS scope for cross-tenant queries.

    `SET LOCAL` is transaction-scoped and would be cleared by any mid-request
    `db.commit()`. Admin handlers commonly commit and then re-read, so we hook
    `after_begin` to re-set the flag on every transaction the session opens.
    """
    async with AsyncSessionLocal() as session:
        @event.listens_for(session.sync_session, "after_begin")
        def _set_admin_flag(_session, _transaction, connection):
            connection.execute(text("SET LOCAL app.is_admin = 'true'"))

        try:
            yield session
        finally:
            event.remove(session.sync_session, "after_begin", _set_admin_flag)


async def get_current_tenant(request: Request) -> str:
    """Backward-compat: reads tenant_id set by TenantMiddleware."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tenant_id


async def get_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant or tenant.deactivated_at is not None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
