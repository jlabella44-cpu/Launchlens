"""
Security headers middleware.

Adds standard security headers to all responses:
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Referrer-Policy
- Content-Security-Policy
- Permissions-Policy
"""
from fastapi import Request
from starlette.responses import Response


class SecurityHeadersMiddleware:
    async def __call__(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Relaxed CSP for API backend — frontend is served separately by Vercel.
        # Only restrict frame embedding (clickjacking protection).
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"

        return response
