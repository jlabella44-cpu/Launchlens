import jwt
from fastapi import Request
from jwt.exceptions import InvalidTokenError
from starlette.responses import JSONResponse

from listingjet.config import settings

_PUBLIC_PATHS = {"/health", "/health/deep", "/auth/register", "/auth/login", "/billing/webhook", "/demo/upload"}


class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Skip CORS preflight (OPTIONS) — let CORSMiddleware handle it
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path in _PUBLIC_PATHS or (path.startswith("/demo/") and request.method == "GET"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing token"})

        token = auth.removeprefix("Bearer ")
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                return JSONResponse(status_code=401, content={"detail": "No tenant in token"})
        except InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        request.state.tenant_id = tenant_id
        return await call_next(request)
