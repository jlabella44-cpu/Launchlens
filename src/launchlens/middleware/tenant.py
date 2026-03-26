import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Request, HTTPException
from launchlens.config import settings


class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Skip auth for health check
        if request.url.path == "/health":
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")

        token = auth.removeprefix("Bearer ")
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise HTTPException(status_code=401, detail="No tenant in token")
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        request.state.tenant_id = tenant_id
        return await call_next(request)
