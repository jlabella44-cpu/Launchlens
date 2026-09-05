# Phase 1: Security and Correctness Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the auth, CORS, proxy, encryption, and index gaps the 2026-09-01 review found, so later phases build on a backend that cannot be driven with a refresh token or a spoofed origin.

**Architecture:** Small, independent edits to existing FastAPI modules plus one Alembic migration and one Next.js config change. No new subsystems. Each task is its own commit on branch `fix/security-week1`.

**Tech Stack:** Python 3.12, FastAPI, PyJWT, redis-py (sync client on `app.state.redis`), SQLAlchemy 2 async, Alembic, pytest + pytest-asyncio + httpx ASGI client, Next.js 16.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` (section "Phase 1").

## Global Constraints

- Never push to `main`; work on `fix/security-week1`, open a PR, wait for approval.
- Every Bash call passes an explicit `timeout`. Full pytest takes ~165 s: use `timeout: 400000`.
- Tests need Postgres on `localhost:5433` (`docker compose up -d postgres-test`, timeout 120000). Non-DB tests run without it.
- Run tests with `python -m pytest --tb=short -q <path>`. Ruff with `ruff check src tests`.
- Alembic head is `051_admin_rls_bypass`. The new migration is `052_...` with `down_revision = "051_admin_rls_bypass"`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

## Findings that changed the spec's Phase 1 list

Verified against the code before planning:

- **Upload limits already exist.** `StorageService.presigned_upload_url` (`src/listingjet/services/storage.py:60-89`) issues a presigned POST with `content-length-range` 1–50 MB and a `Content-Type` equality condition, and both upload components in the frontend post a `FormData` with those fields. Task 8 adds a regression test only; no code change.
- **Canva JWT decode is not a vulnerability.** The token decoded at `canva_oauth.py:252` is the access token Canva's own token endpoint just returned over TLS, not user input; only `sub` is read. No change.
- **Tenant indexes partially exist.** `events` has `(tenant_id, event_type, created_at)`. `users`, `outbox`, `audit_logs` have none. Task 7 adds those three.
- **A shared Redis client already exists** on `app.state.redis` (`main.py:66-79`). Task 2 makes `services/auth.py` use a single module-level client instead of one per call.

---

### Task 1: Enforce access-token type in the auth dependency and tenant middleware

**Files:**
- Modify: `src/listingjet/services/auth.py:76-86` (`decode_token`)
- Modify: `src/listingjet/middleware/tenant.py:35-45`
- Modify: `src/listingjet/api/auth.py:375` (refresh endpoint must still accept refresh tokens)
- Test: `tests/test_api/test_auth.py`, `tests/test_middleware/test_tenant.py`

**Interfaces:**
- Produces: `decode_token(token: str, *, expected_type: str = "access") -> dict`. Raises `HTTPException(401)` when `payload["type"] != expected_type`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_refresh_token_rejected_as_bearer(async_client: AsyncClient):
    """A refresh token must not authenticate API requests (review finding: 7-day refresh works as bearer)."""
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "ValidPass1!", "name": "Reg", "company_name": "Reg LLC",
        "plan_tier": "free",
    })
    assert reg.status_code == 200
    refresh = reg.json()["refresh_token"]

    resp = await async_client.get("/listings", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Wrong token type"


def test_decode_token_rejects_wrong_type():
    user = User(id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="t@example.com",
                password_hash="x", role=UserRole.ADMIN)
    from listingjet.services.auth import create_refresh_token
    refresh = create_refresh_token(user)
    with pytest.raises(HTTPException) as exc:
        decode_token(refresh)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Wrong token type"
    # Explicitly asking for a refresh token still works
    assert decode_token(refresh, expected_type="refresh")["type"] == "refresh"
```

Append to `tests/test_middleware/test_tenant.py`:

```python
@pytest.mark.asyncio
async def test_middleware_rejects_refresh_token(async_client: AsyncClient):
    email = f"test-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo",
        "plan_tier": "free",
    })
    refresh = reg.json()["refresh_token"]
    resp = await async_client.get("/listings", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api/test_auth.py::test_refresh_token_rejected_as_bearer tests/test_api/test_auth.py::test_decode_token_rejects_wrong_type tests/test_middleware/test_tenant.py::test_middleware_rejects_refresh_token -q` (timeout 120000)
Expected: FAIL. The bearer test gets 200, `decode_token` does not raise (TypeError on `expected_type` kwarg).

- [ ] **Step 3: Implement**

`src/listingjet/services/auth.py`, replace `decode_token`:

```python
def decode_token(token: str, *, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Wrong token type")

    # Check Redis blocklist for revoked tokens
    if is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    return payload
```

`src/listingjet/middleware/tenant.py`, inside the `try` after `payload = jwt.decode(...)`:

```python
            if payload.get("type") != "access":
                return JSONResponse(status_code=401, content={"detail": "Wrong token type"})
            tenant_id = payload.get("tenant_id")
```

`src/listingjet/api/auth.py:374-376` (refresh endpoint) currently reads:

```python
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
```

Replace with:

```python
    try:
        payload = decode_token(token, expected_type="refresh")
    except HTTPException as exc:
        if exc.detail == "Wrong token type":
            raise HTTPException(status_code=401, detail="Not a refresh token")
        raise
```

The password-reset endpoint (`api/auth.py:306-311`) uses raw `pyjwt.decode` and its own type check; leave it. Confirm no other callers need a different type: `grep -rn "decode_token(" src/` should show only `api/deps.py` (access, default) and the refresh endpoint.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_api/test_auth.py tests/test_middleware/test_tenant.py -q` (timeout 200000)
Expected: PASS, including the existing refresh and password-reset tests.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/services/auth.py src/listingjet/middleware/tenant.py src/listingjet/api/auth.py tests/test_api/test_auth.py tests/test_middleware/test_tenant.py
git commit -m "fix(auth): reject non-access tokens as bearer credentials"
```

---

### Task 2: Token revocation fails closed and uses one Redis client

**Files:**
- Modify: `src/listingjet/services/auth.py:21-23, 103-111`
- Modify: `tests/conftest.py:58-67` (add a patch so tests never touch Redis)
- Test: `tests/test_services/test_auth_revocation.py` (new)

**Interfaces:**
- Produces: `services.auth.get_redis() -> redis.Redis` (module-level cached sync client). `is_token_revoked(token) -> bool` raises `HTTPException(503, "Auth backend unavailable")` on Redis errors instead of returning False.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_services/test_auth_revocation.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from listingjet.services import auth as auth_svc


def test_is_token_revoked_true_when_key_exists():
    r = MagicMock()
    r.exists.return_value = 1
    with patch.object(auth_svc, "get_redis", return_value=r):
        assert auth_svc.is_token_revoked("tok") is True
    r.exists.assert_called_once_with("token_revoked:tok")


def test_is_token_revoked_fails_closed_when_redis_errors():
    r = MagicMock()
    r.exists.side_effect = ConnectionError("down")
    with patch.object(auth_svc, "get_redis", return_value=r):
        with pytest.raises(HTTPException) as exc:
            auth_svc.is_token_revoked("tok")
    assert exc.value.status_code == 503


def test_get_redis_is_cached():
    auth_svc._redis_client = None
    with patch("redis.from_url") as from_url:
        from_url.return_value = MagicMock()
        a = auth_svc.get_redis()
        b = auth_svc.get_redis()
    assert a is b
    assert from_url.call_count == 1
    auth_svc._redis_client = None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_services/test_auth_revocation.py -q` (timeout 60000)
Expected: FAIL with `AttributeError: module has no attribute 'get_redis'`.

- [ ] **Step 3: Implement**

`src/listingjet/services/auth.py`: replace `_get_redis` and `is_token_revoked`:

```python
_redis_client = None


def get_redis():
    """Process-wide sync Redis client for auth (blocklist + lockout)."""
    global _redis_client
    if _redis_client is None:
        import redis
        _redis_client = redis.from_url(
            settings.redis_url, socket_connect_timeout=2, socket_timeout=2,
        )
    return _redis_client
```

```python
def is_token_revoked(token: str) -> bool:
    """Check the Redis blocklist. Fails closed: Redis errors reject the request."""
    try:
        return get_redis().exists(f"token_revoked:{token}") > 0
    except Exception:
        logger.error("token_revocation_check_failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Auth backend unavailable")
```

Update `revoke_token` to call `get_redis()` instead of `_get_redis()`. Grep `_get_redis` in `services/auth.py` to be sure none remain.

`tests/conftest.py`: inside the `with (` block at line 58, add:

```python
        patch("listingjet.services.auth.get_redis", return_value=mock_redis),
```

`mock_redis.exists` already returns 0, so tokens are never revoked in tests.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_services/test_auth_revocation.py tests/test_api/test_auth.py -q` (timeout 200000)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/services/auth.py tests/conftest.py tests/test_services/test_auth_revocation.py
git commit -m "fix(auth): revocation check fails closed on a shared Redis client"
```

---

### Task 3: CORS allows only the configured origin list

**Files:**
- Modify: `src/listingjet/main.py:163-171`
- Test: `tests/test_middleware/test_cors.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_middleware/test_cors.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unlisted_vercel_origin_gets_no_cors_headers(async_client: AsyncClient):
    resp = await async_client.options(
        "/health",
        headers={
            "Origin": "https://listingjet-attacker.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.asyncio
async def test_configured_origin_gets_cors_headers(async_client: AsyncClient):
    from listingjet.config import settings
    origin = settings.cors_origins.split(",")[0].strip()
    resp = await async_client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == origin
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_middleware/test_cors.py -q` (timeout 120000)
Expected: first test FAILS (header present because of the regex), second passes.

- [ ] **Step 3: Implement**

`src/listingjet/main.py`: delete the line `allow_origin_regex=r"https://listingjet[a-z0-9-]*\.vercel\.app",`. Preview deployments get added to `CORS_ORIGINS` explicitly when needed.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_middleware/test_cors.py -q` (timeout 120000)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/main.py tests/test_middleware/test_cors.py
git commit -m "fix(cors): drop wildcard vercel origin regex"
```

---

### Task 4: Trusted proxy count comes from settings

**Files:**
- Modify: `src/listingjet/config/__init__.py` (add field near `cors_origins`, line 11)
- Modify: `src/listingjet/middleware/rate_limit.py:25-28, 39-48`
- Modify: `src/listingjet/api/demo.py:48-56`
- Modify: `render.yaml` (env group) and `.env.example`
- Test: `tests/test_middleware/test_rate_limit_ip.py` (new)

**Interfaces:**
- Produces: `settings.trusted_proxy_count: int` (default 1). `middleware.rate_limit.extract_client_ip(request) -> str` shared by the middleware and `api/demo.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_middleware/test_rate_limit_ip.py`:

```python
from unittest.mock import patch

from starlette.requests import Request

from listingjet.middleware.rate_limit import extract_client_ip


def _req(xff: str | None) -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({
        "type": "http", "method": "GET", "path": "/", "headers": headers,
        "query_string": b"", "server": ("testserver", 80), "scheme": "http",
        "client": ("10.0.0.9", 1234),
    })


def test_one_trusted_proxy_uses_last_forwarded_entry():
    with patch("listingjet.middleware.rate_limit.settings.trusted_proxy_count", 1):
        assert extract_client_ip(_req("203.0.113.5, 10.1.1.1")) == "10.1.1.1"


def test_zero_trusted_proxies_ignores_header():
    with patch("listingjet.middleware.rate_limit.settings.trusted_proxy_count", 0):
        assert extract_client_ip(_req("203.0.113.5")) == "10.0.0.9"


def test_default_is_one_proxy():
    from listingjet.config import Settings
    assert Settings.model_fields["trusted_proxy_count"].default == 1
```

Note on semantics: with `trusted_proxy_count = 1` the code picks `parts[len(parts) - 1]`, the entry the single trusted proxy appended. That is the existing algorithm; the test pins it.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_middleware/test_rate_limit_ip.py -q` (timeout 60000)
Expected: FAIL with ImportError on `extract_client_ip`.

- [ ] **Step 3: Implement**

`src/listingjet/config/__init__.py`, after `cors_origins`:

```python
    # Reverse proxies in front of the app (Render = 1). 0 ignores X-Forwarded-For.
    trusted_proxy_count: int = 1
```

`src/listingjet/middleware/rate_limit.py`: delete the `TRUSTED_PROXY_COUNT` constant and its comment; add `from listingjet.config import settings` to imports; rename `_extract_client_ip` to `extract_client_ip` and use `settings.trusted_proxy_count`:

```python
def extract_client_ip(request: Request) -> str:
    """Client IP, trusting X-Forwarded-For only for the configured number of proxies."""
    count = settings.trusted_proxy_count
    if count > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",")]
            idx = max(0, len(parts) - count)
            return parts[idx]
    return request.client.host if request.client else "unknown"
```

Update the one call site in the middleware (`ip = extract_client_ip(request)`).

`src/listingjet/api/demo.py`: replace `_get_client_ip` body with:

```python
def _get_client_ip(request: Request) -> str:
    from listingjet.middleware.rate_limit import extract_client_ip
    return extract_client_ip(request)
```

`render.yaml` env group: add `- key: TRUSTED_PROXY_COUNT` / `value: "1"`. `.env.example`: add `TRUSTED_PROXY_COUNT=0` under the app section with a comment "1 behind Render".

Grep: `grep -rn "TRUSTED_PROXY_COUNT\|_extract_client_ip" src tests` must return nothing except the new setting.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_middleware tests/test_api/test_demo_rate_limit.py -q` (timeout 200000)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/config/__init__.py src/listingjet/middleware/rate_limit.py src/listingjet/api/demo.py render.yaml .env.example tests/test_middleware/test_rate_limit_ip.py
git commit -m "fix(rate-limit): trusted proxy count from settings, default 1 for Render"
```

---

### Task 5: Login lockout errors are logged, not swallowed

**Files:**
- Modify: `src/listingjet/api/auth.py:137-175`
- Test: `tests/test_api/test_auth_lockout_logging.py` (new)

- [ ] **Step 1: Write the failing test**

```python
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_lockout_redis_failure_is_logged(async_client: AsyncClient, caplog):
    broken = MagicMock()
    broken.get.side_effect = ConnectionError("redis down")
    broken.pipeline.side_effect = ConnectionError("redis down")
    with patch("listingjet.api.auth._get_lockout_redis", return_value=broken):
        with caplog.at_level(logging.ERROR, logger="listingjet.api.auth"):
            resp = await async_client.post("/auth/login", json={
                "email": f"nobody-{uuid.uuid4()}@example.com", "password": "Wrong1!",
            })
    assert resp.status_code == 401  # login still fails open on the lockout check
    assert any("auth.lockout_backend_error" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api/test_auth_lockout_logging.py -q` (timeout 120000)
Expected: FAIL, no log record with that message.

- [ ] **Step 3: Implement**

In `src/listingjet/api/auth.py` login handler, replace each of the three `except Exception: pass` blocks:

```python
    except Exception:
        logger.error("auth.lockout_backend_error stage=check", exc_info=True)
```

```python
        except Exception:
            logger.error("auth.lockout_backend_error stage=increment", exc_info=True)
```

```python
    except Exception:
        logger.error("auth.lockout_backend_error stage=clear", exc_info=True)
```

Behaviour stays fail-open for login itself (a Redis outage must not lock every user out), but the outage is now visible in Sentry and logs. Check `logger` exists at module level in `api/auth.py` (`logger = logging.getLogger(__name__)`); add it if missing.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_api/test_auth_lockout_logging.py tests/test_api/test_auth.py -q` (timeout 200000)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/api/auth.py tests/test_api/test_auth_lockout_logging.py
git commit -m "fix(auth): log lockout backend failures instead of swallowing them"
```

---

### Task 6: Field encryption refuses to run unkeyed in production

**Files:**
- Modify: `src/listingjet/services/field_encryption.py`
- Test: `tests/test_services/test_field_encryption.py` (create if absent; extend if present)

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from listingjet.services import field_encryption as fe


def test_roundtrip_with_key():
    key = Fernet.generate_key().decode()
    with patch.object(fe.settings, "field_encryption_key", key):
        assert fe.decrypt(fe.encrypt("secret")) == "secret"


def test_no_key_in_development_passes_through():
    with patch.object(fe.settings, "field_encryption_key", ""), \
         patch.object(fe.settings, "app_env", "development"):
        assert fe.encrypt("x") == "x"
        assert fe.decrypt("x") == "x"


def test_no_key_in_production_raises():
    with patch.object(fe.settings, "field_encryption_key", ""), \
         patch.object(fe.settings, "app_env", "production"):
        with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
            fe.encrypt("x")
        with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
            fe.decrypt("x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_services/test_field_encryption.py -q` (timeout 60000)
Expected: `test_no_key_in_production_raises` FAILS (no exception).

- [ ] **Step 3: Implement**

Replace `_get_fernet`:

```python
def _get_fernet() -> Fernet | None:
    key = settings.field_encryption_key
    if not key:
        if settings.app_env == "production":
            raise RuntimeError(
                "FIELD_ENCRYPTION_KEY is required in production; refusing to store secrets in plaintext"
            )
        return None
    return Fernet(key.encode())
```

`encrypt` and `decrypt` are unchanged; both call `_get_fernet()` first.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_services/test_field_encryption.py -q` (timeout 60000)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/services/field_encryption.py tests/test_services/test_field_encryption.py
git commit -m "fix(security): field encryption raises without a key in production"
```

---

### Task 7: Tenant indexes on users, outbox, audit_logs

**Files:**
- Create: `alembic/versions/052_tenant_indexes.py`
- Modify: `src/listingjet/models/user.py:23`, `src/listingjet/models/outbox.py:16`, `src/listingjet/models/audit_log.py:15` (add `index=True` so `create_all` in tests matches the migration)
- Test: `tests/test_models/test_tenant_indexes.py` (new)

- [ ] **Step 1: Write the failing test**

```python
from listingjet.models.audit_log import AuditLog
from listingjet.models.outbox import Outbox
from listingjet.models.user import User


def _indexed_columns(model) -> set[str]:
    cols = set()
    for idx in model.__table__.indexes:
        cols.update(c.name for c in idx.columns)
    return cols


def test_tenant_id_is_indexed_on_hot_tables():
    for model in (User, Outbox, AuditLog):
        assert "tenant_id" in _indexed_columns(model), model.__tablename__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models/test_tenant_indexes.py -q` (timeout 60000)
Expected: FAIL on `users`.

- [ ] **Step 3: Implement**

Add `index=True` to the three `tenant_id` columns:

```python
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
```
(`AuditLog` keeps `nullable=True`.)

Create `alembic/versions/052_tenant_indexes.py`:

```python
"""tenant_id indexes on users, outbox, audit_logs

Revision ID: 052_tenant_indexes
Revises: 051_admin_rls_bypass
"""
from alembic import op

revision = "052_tenant_indexes"
down_revision = "051_admin_rls_bypass"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_outbox_tenant_id", "outbox", ["tenant_id"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_index("ix_outbox_tenant_id", table_name="outbox")
    op.drop_index("ix_users_tenant_id", table_name="users")
```

Confirm table names with `grep -n "__tablename__" src/listingjet/models/user.py src/listingjet/models/outbox.py src/listingjet/models/audit_log.py` and adjust if `outbox` is named differently.

- [ ] **Step 4: Run tests and the migration**

Run: `python -m pytest tests/test_models/test_tenant_indexes.py -q` (timeout 60000). Expected: PASS.
Run: `alembic heads` (timeout 60000). Expected: exactly one head, `052_tenant_indexes`.
Run against the local dev DB (`docker compose up -d postgres`, then `DATABASE_URL_SYNC=postgresql://listingjet:password@localhost:5432/listingjet alembic upgrade head`, timeout 120000). Expected: applies without error. Then `alembic downgrade -1 && alembic upgrade head` (timeout 120000) to prove the downgrade.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/052_tenant_indexes.py src/listingjet/models/user.py src/listingjet/models/outbox.py src/listingjet/models/audit_log.py tests/test_models/test_tenant_indexes.py
git commit -m "perf(db): index tenant_id on users, outbox, audit_logs"
```

---

### Task 8: Upload limit regression test and ClamAV removal

**Files:**
- Test: `tests/test_services/test_storage.py` (extend)
- Modify: `src/listingjet/config/__init__.py:130-131` (remove `clamav_host`, `clamav_port`)
- Modify: `pyproject.toml` (remove `"clamd>=1.0.2"`)
- Modify: `docker-compose.yml` (remove `clamav` service and `clamav_data` volume)
- Delete: `src/listingjet/services/scanner.py` if nothing imports it

- [ ] **Step 1: Write the regression test**

Append to `tests/test_services/test_storage.py`. It already has an `s3_service` fixture (moto `mock_aws`, bucket `test-bucket`) at line 10; reuse it:

```python
def test_presigned_upload_rejects_disallowed_type(s3_service):
    with pytest.raises(ValueError, match="not allowed"):
        s3_service.presigned_upload_url(key="k", content_type="image/gif")


def test_presigned_upload_enforces_size_and_type(s3_service):
    post = s3_service.presigned_upload_url(key="k", content_type="image/jpeg")
    assert post["fields"]["Content-Type"] == "image/jpeg"
    # The policy is a base64 JSON document; the size range must be in it.
    policy = json.loads(base64.b64decode(post["fields"]["policy"]))
    assert ["content-length-range", 1, s3_service.MAX_UPLOAD_SIZE] in policy["conditions"]
```

Add `import base64` and `import json` to the file's imports (and `import pytest` if absent).

- [ ] **Step 2: Run to verify**

Run: `python -m pytest tests/test_services/test_storage.py -q` (timeout 60000)
Expected: PASS on first run (this pins existing behaviour). If the policy assertion fails, print `policy["conditions"]` and adjust the expected list shape; do not weaken the size check.

- [ ] **Step 3: Remove ClamAV**

- `grep -rn "scanner\|clamd\|clamav" src tests` and delete `src/listingjet/services/scanner.py` plus any test file that only tests it.
- Remove `clamav_host` and `clamav_port` from `Settings`.
- Remove `"clamd>=1.0.2",` from `pyproject.toml`.
- Remove the `clamav:` service block and `clamav_data:` volume from `docker-compose.yml`; remove any `depends_on: clamav` lines.

- [ ] **Step 4: Run the affected tests**

Run: `python -m pytest tests/test_config tests/test_services/test_storage.py -q` (timeout 120000). Expected: PASS.
Run: `ruff check src tests` (timeout 60000). Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add -A tests/test_services/test_storage.py src/listingjet/config/__init__.py pyproject.toml docker-compose.yml src/listingjet/services
git commit -m "chore: pin upload limit behaviour, remove ClamAV remnants"
```

---

### Task 9: Next.js image hosts point at R2

**Files:**
- Modify: `frontend/next.config.ts`
- Modify: `frontend/.env.example` (create if absent) with `NEXT_PUBLIC_MEDIA_HOST=`

- [ ] **Step 1: Implement**

```ts
import type { NextConfig } from "next";

// Public hostname of the media bucket (Cloudflare R2 public bucket domain or a
// custom domain in front of it), e.g. "media.listingjet.ai" or
// "pub-xxxx.r2.dev". Set per environment; without it next/image rejects every
// listing photo.
const mediaHost = process.env.NEXT_PUBLIC_MEDIA_HOST;

const nextConfig: NextConfig = {
  images: {
    formats: ["image/webp"],
    remotePatterns: mediaHost
      ? [{ protocol: "https", hostname: mediaHost }]
      : [],
  },
};

export default nextConfig;
```

Add to `frontend/.env.example`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MEDIA_HOST=
```

- [ ] **Step 2: Verify the build accepts it**

Run in `frontend/`: `npx tsc --noEmit` (timeout 300000). Expected: no errors (or only pre-existing ones; note them in the PR).
Run: `NEXT_PUBLIC_MEDIA_HOST=pub-test.r2.dev npm run build` (timeout 600000). Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/next.config.ts frontend/.env.example
git commit -m "fix(frontend): allow next/image hosts from NEXT_PUBLIC_MEDIA_HOST (R2)"
```

---

### Task 10: Full verification and PR

- [ ] **Step 1: Full backend suite**

Run: `docker compose up -d postgres-test` (timeout 120000), then `python -m pytest --tb=short -q` (timeout 400000).
Expected: 0 failed. Previous baseline: 883 passed, 3 skipped.

- [ ] **Step 2: Lint**

Run: `ruff check src tests` (timeout 60000). Expected: clean.

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin fix/security-week1
gh pr create --title "fix: phase 1 security and correctness fixes" --body "$(cat <<'EOF'
## Summary
Phase 1 of docs/superpowers/specs/2026-09-05-free-tier-rework-design.md.

- Reject refresh/reset tokens as bearer credentials (dependency + middleware)
- Token revocation fails closed on one shared Redis client
- CORS: configured origin list only, wildcard vercel regex removed
- TRUSTED_PROXY_COUNT from settings (default 1 for Render)
- Lockout backend errors logged
- Field encryption raises unkeyed in production
- tenant_id indexes on users, outbox, audit_logs (migration 052)
- Upload limit regression test; ClamAV remnants removed
- next/image hosts from NEXT_PUBLIC_MEDIA_HOST

Not changed after verification: upload size/type limits already enforced by the presigned POST policy; Canva token decode reads Canva's own token, not user input.

## Test plan
- [ ] `python -m pytest -q` green with postgres-test up
- [ ] `alembic upgrade head` then `downgrade -1` on local DB
- [ ] `npm run build` in frontend with NEXT_PUBLIC_MEDIA_HOST set

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
EOF
)"
```

Do not merge. Report the PR URL and the test counts.
