# Core Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the provider abstraction layer, storage service, rate limiter, and full Outbox-pattern event system that all agents depend on.

**Architecture:** Provider ABCs (`VisionProvider`, `LLMProvider`, `TemplateProvider`) with concrete Google/OpenAI/Claude implementations and a mock layer for tests. A `StorageService` wraps S3. A Redis token-bucket `RateLimiter` protects external API calls. `emit_event()` is upgraded from a stub to the full Outbox Pattern (write event + outbox row in one DB transaction; a background poller marks rows delivered).

**Tech Stack:** httpx (async REST), anthropic SDK, boto3/moto, redis-py, SQLAlchemy 2.0 async, FastAPI lifespan

---

## File Structure

```
src/launchlens/
  providers/
    __init__.py          MODIFY — export factory functions
    base.py              CREATE — VisionProvider, LLMProvider, TemplateProvider ABCs
    mock.py              CREATE — MockVisionProvider, MockLLMProvider, MockTemplateProvider
    factory.py           CREATE — get_vision_provider(), get_llm_provider(), get_template_provider()
    google_vision.py     CREATE — GoogleVisionProvider (httpx REST)
    openai_vision.py     CREATE — OpenAIVisionProvider (GPT-4V, Semaphore(5))
    claude.py            CREATE — ClaudeProvider (anthropic SDK)
  services/
    events.py            MODIFY — replace stub with full Outbox Pattern
    storage.py           CREATE — StorageService (upload, presigned_url, delete)
    rate_limiter.py      CREATE — RateLimiter (Redis token bucket via Lua)
    outbox_poller.py     CREATE — OutboxPoller (FastAPI lifespan background task)
  main.py                MODIFY — wire OutboxPoller into lifespan
  config.py              MODIFY — add OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_VISION_API_KEY, USE_MOCK_PROVIDERS

tests/
  test_providers/
    __init__.py          CREATE
    test_mock_providers.py  CREATE
    test_factory.py      CREATE
  test_services/
    __init__.py          CREATE (already exists? verify)
    test_storage.py      CREATE — moto S3 mocks
    test_rate_limiter.py CREATE — fakeredis
    test_events.py       CREATE — full outbox cycle
    test_outbox_poller.py CREATE
```

---

### Task 1: Provider ABCs + Config Fields

**Files:**
- Create: `src/launchlens/providers/base.py`
- Modify: `src/launchlens/config.py`
- Test: `tests/test_providers/__init__.py` (empty, just creates the package)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers/__init__.py
# (empty)
```

```python
# tests/test_providers/test_mock_providers.py
import pytest
from launchlens.providers.base import VisionLabel, VisionProvider, LLMProvider, TemplateProvider
from launchlens.providers.mock import MockVisionProvider, MockLLMProvider, MockTemplateProvider


def test_vision_label_dataclass():
    label = VisionLabel(name="kitchen", confidence=0.95, category="room")
    assert label.name == "kitchen"
    assert label.confidence == 0.95
    assert label.category == "room"


def test_mock_vision_provider_is_vision_provider():
    provider = MockVisionProvider()
    assert isinstance(provider, VisionProvider)


def test_mock_llm_provider_is_llm_provider():
    provider = MockLLMProvider()
    assert isinstance(provider, LLMProvider)


def test_mock_template_provider_is_template_provider():
    provider = MockTemplateProvider()
    assert isinstance(provider, TemplateProvider)


@pytest.mark.asyncio
async def test_mock_vision_provider_analyze_returns_labels():
    provider = MockVisionProvider()
    labels = await provider.analyze(image_url="https://example.com/photo.jpg")
    assert isinstance(labels, list)
    assert len(labels) > 0
    assert all(isinstance(l, VisionLabel) for l in labels)


@pytest.mark.asyncio
async def test_mock_llm_provider_complete_returns_string():
    provider = MockLLMProvider()
    result = await provider.complete(prompt="Describe this kitchen.", context={})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_mock_template_provider_render_returns_bytes():
    provider = MockTemplateProvider()
    result = await provider.render(template_id="flyer-standard", data={"headline": "Beautiful Home"})
    assert isinstance(result, bytes)
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_mock_providers.py -v 2>&1 | tail -20
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.providers.base'`

- [ ] **Step 3: Create provider ABCs**

```python
# src/launchlens/providers/base.py
"""
Provider ABCs for external service integrations.

VisionProvider  — photo analysis (Google Vision, GPT-4V)
LLMProvider     — text generation (Claude, GPT-4)
TemplateProvider — flyer/social asset rendering (Canva, HTML/Chromium)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VisionLabel:
    name: str
    confidence: float
    category: str  # e.g. "room", "feature", "quality"


class VisionProvider(ABC):
    @abstractmethod
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        """Return labels for the given image URL."""
        ...


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, context: dict) -> str:
        """Return a text completion for the given prompt and context."""
        ...


class TemplateProvider(ABC):
    @abstractmethod
    async def render(self, template_id: str, data: dict) -> bytes:
        """Render a template and return raw bytes (PDF or PNG)."""
        ...
```

```python
# src/launchlens/providers/mock.py
"""Mock provider implementations for tests and local development."""
from .base import VisionLabel, VisionProvider, LLMProvider, TemplateProvider


class MockVisionProvider(VisionProvider):
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        return [
            VisionLabel(name="living room", confidence=0.97, category="room"),
            VisionLabel(name="hardwood floor", confidence=0.91, category="feature"),
            VisionLabel(name="natural light", confidence=0.88, category="quality"),
        ]


class MockLLMProvider(LLMProvider):
    async def complete(self, prompt: str, context: dict) -> str:
        return "Stunning home with modern finishes and abundant natural light."


class MockTemplateProvider(TemplateProvider):
    async def render(self, template_id: str, data: dict) -> bytes:
        return b"%PDF-mock-content"
```

- [ ] **Step 4: Add config fields for API keys + mock flag**

Read `src/launchlens/config.py` first, then add fields:

```python
# Add to Settings class in src/launchlens/config.py:
openai_api_key: str = ""
anthropic_api_key: str = ""
google_vision_api_key: str = ""
use_mock_providers: bool = False
```

- [ ] **Step 5: Create tests/test_providers/__init__.py**

Empty file — just creates the package.

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_mock_providers.py -v 2>&1 | tail -20
```

Expected: 7 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/base.py src/launchlens/providers/mock.py src/launchlens/config.py tests/test_providers/__init__.py tests/test_providers/test_mock_providers.py && git commit -m "feat: add provider ABCs, mock providers, and api key config fields"
```

---

### Task 2: Provider Factory

**Files:**
- Create: `src/launchlens/providers/factory.py`
- Modify: `src/launchlens/providers/__init__.py`
- Test: `tests/test_providers/test_factory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers/test_factory.py
import pytest
from unittest.mock import patch
from launchlens.providers.factory import get_vision_provider, get_llm_provider, get_template_provider
from launchlens.providers.mock import MockVisionProvider, MockLLMProvider, MockTemplateProvider
from launchlens.providers.base import VisionProvider, LLMProvider, TemplateProvider


def test_get_vision_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, MockVisionProvider)


def test_get_llm_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)


def test_get_template_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)


def test_get_vision_provider_returns_vision_provider_interface():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, VisionProvider)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_factory.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.providers.factory'`

- [ ] **Step 3: Write the factory**

```python
# src/launchlens/providers/factory.py
"""
Provider factory.

Returns mock providers when USE_MOCK_PROVIDERS=true (tests, local dev).
Returns real providers otherwise (requires API keys in environment).
"""
from launchlens.config import settings
from .base import VisionProvider, LLMProvider, TemplateProvider


def get_vision_provider() -> VisionProvider:
    if settings.use_mock_providers:
        from .mock import MockVisionProvider
        return MockVisionProvider()
    from .google_vision import GoogleVisionProvider
    return GoogleVisionProvider()


def get_llm_provider() -> LLMProvider:
    if settings.use_mock_providers:
        from .mock import MockLLMProvider
        return MockLLMProvider()
    from .claude import ClaudeProvider
    return ClaudeProvider()


def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    from .mock import MockTemplateProvider  # Canva not yet implemented
    return MockTemplateProvider()
```

```python
# src/launchlens/providers/__init__.py
from .factory import get_vision_provider, get_llm_provider, get_template_provider
from .base import VisionProvider, LLMProvider, TemplateProvider, VisionLabel

__all__ = [
    "get_vision_provider",
    "get_llm_provider",
    "get_template_provider",
    "VisionProvider",
    "LLMProvider",
    "TemplateProvider",
    "VisionLabel",
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/ -v 2>&1 | tail -15
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/factory.py src/launchlens/providers/__init__.py tests/test_providers/test_factory.py && git commit -m "feat: add provider factory with USE_MOCK_PROVIDERS flag"
```

---

### Task 3: S3 Storage Service

**Files:**
- Create: `src/launchlens/services/storage.py`
- Create: `tests/test_services/__init__.py`
- Create: `tests/test_services/test_storage.py`

Note: `moto` is not in dev dependencies. It must be added to `pyproject.toml` before writing this test.

- [ ] **Step 1: Add moto to dev dependencies**

Edit `pyproject.toml` — add `"moto[s3]>=5.0"` to `[project.optional-dependencies] dev`.

- [ ] **Step 2: Install updated deps**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pip install -e ".[dev]" 2>&1 | tail -5
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_services/__init__.py
# (empty)
```

```python
# tests/test_services/test_storage.py
import pytest
import boto3
from moto import mock_aws
from launchlens.services.storage import StorageService


@pytest.fixture
def s3_service():
    return StorageService(bucket="test-bucket", region="us-east-1")


@mock_aws
def test_upload_bytes_returns_key(s3_service):
    # moto patches boto3 — create bucket first
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    key = s3_service.upload(key="listings/abc/hero.jpg", data=b"fake-image-bytes", content_type="image/jpeg")
    assert key == "listings/abc/hero.jpg"


@mock_aws
def test_presigned_url_returns_string(s3_service):
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    s3_service.upload(key="listings/abc/hero.jpg", data=b"x", content_type="image/jpeg")
    url = s3_service.presigned_url(key="listings/abc/hero.jpg", expires_in=3600)
    assert url.startswith("http")  # moto returns http://, real S3 returns https://


@mock_aws
def test_delete_removes_object(s3_service):
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")
    s3_service.upload(key="listings/abc/hero.jpg", data=b"x", content_type="image/jpeg")
    s3_service.delete(key="listings/abc/hero.jpg")
    objs = client.list_objects_v2(Bucket="test-bucket").get("Contents", [])
    assert len(objs) == 0


@mock_aws
def test_upload_file_like_object(s3_service):
    import io
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    buf = io.BytesIO(b"image-data")
    key = s3_service.upload(key="listings/abc/photo.jpg", data=buf, content_type="image/jpeg")
    assert key == "listings/abc/photo.jpg"
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_storage.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.services.storage'`

- [ ] **Step 5: Implement StorageService**

```python
# src/launchlens/services/storage.py
"""
S3-backed storage service.

All asset uploads use a consistent key scheme:
  listings/{listing_id}/{asset_type}/{filename}

Presigned URLs expire in 1 hour by default.
"""
import io
import boto3
from launchlens.config import settings


class StorageService:
    def __init__(self, bucket: str = None, region: str = None):
        self._bucket = bucket or settings.s3_bucket_name
        self._region = region or settings.aws_region
        self._client = boto3.client("s3", region_name=self._region)

    def upload(self, key: str, data: bytes | io.IOBase, content_type: str) -> str:
        """Upload bytes or file-like object. Returns the S3 key."""
        if isinstance(data, (bytes, bytearray)):
            data = io.BytesIO(data)
        self._client.upload_fileobj(
            data,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, key: str) -> None:
        """Delete an object from S3."""
        self._client.delete_object(Bucket=self._bucket, Key=key)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_storage.py -v 2>&1 | tail -15
```

Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add pyproject.toml src/launchlens/services/storage.py tests/test_services/__init__.py tests/test_services/test_storage.py && git commit -m "feat: add S3 StorageService with moto tests"
```

---

### Task 4: Redis Token Bucket Rate Limiter

**Files:**
- Create: `src/launchlens/services/rate_limiter.py`
- Create: `tests/test_services/test_rate_limiter.py`

Note: `fakeredis` is not in dev dependencies. It must be added to `pyproject.toml`.

- [ ] **Step 1: Add fakeredis to dev dependencies**

Edit `pyproject.toml` — add `"fakeredis>=2.23"` to `[project.optional-dependencies] dev`.

- [ ] **Step 2: Install**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pip install -e ".[dev]" 2>&1 | tail -5
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_services/test_rate_limiter.py
import pytest
import fakeredis
from launchlens.services.rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    client = fakeredis.FakeRedis()
    return RateLimiter(redis_client=client, key_prefix="test")


def test_acquire_within_limit_returns_true(limiter):
    # capacity=10, default; 3 calls should all succeed
    for _ in range(3):
        assert limiter.acquire(key="google_vision", cost=1) is True


def test_acquire_exceeds_capacity_returns_false(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=2,
        refill_rate=0,  # no refill during test
    )
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is False


def test_acquire_cost_greater_than_one(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=5,
        refill_rate=0,
    )
    assert small.acquire(key="gpt4v", cost=3) is True
    assert small.acquire(key="gpt4v", cost=3) is False  # only 2 tokens left


def test_different_keys_are_independent(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=1,
        refill_rate=0,
    )
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is False
    # Different key still has tokens
    assert small.acquire(key="gpt4v", cost=1) is True
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_rate_limiter.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.services.rate_limiter'`

- [ ] **Step 5: Implement RateLimiter**

```python
# src/launchlens/services/rate_limiter.py
"""
Token bucket rate limiter backed by Redis.

Uses a Lua script for atomic check-and-decrement.
Each provider key (e.g. "google_vision", "gpt4v") has its own bucket.

Usage:
    limiter = RateLimiter(redis_client=redis.from_url(settings.redis_url))
    if not limiter.acquire(key="google_vision", cost=1):
        raise RateLimitExceeded("google_vision")
"""
import time
import redis as redis_lib

# Lua script: atomic token bucket check + consume
# KEYS[1] = bucket key
# ARGV[1] = capacity, ARGV[2] = refill_rate (tokens/sec), ARGV[3] = cost, ARGV[4] = now (float)
_LUA_ACQUIRE = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(data[1]) or capacity
local last_refill = tonumber(data[2]) or now

local elapsed = now - last_refill
local refilled = elapsed * refill_rate
tokens = math.min(capacity, tokens + refilled)

if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 1
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 0
end
"""


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        redis_client=None,
        key_prefix: str = "ratelimit",
        capacity: int = 10,
        refill_rate: float = 1.0,  # tokens per second
    ):
        if redis_client is None:
            from launchlens.config import settings
            redis_client = redis_lib.from_url(settings.redis_url)
        self._redis = redis_client
        self._prefix = key_prefix
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._script = self._redis.register_script(_LUA_ACQUIRE)

    def acquire(self, key: str, cost: int = 1) -> bool:
        """Attempt to consume `cost` tokens. Returns True if allowed."""
        bucket_key = f"{self._prefix}:{key}"
        now = time.time()
        result = self._script(
            keys=[bucket_key],
            args=[self._capacity, self._refill_rate, cost, now],
        )
        return bool(result)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_rate_limiter.py -v 2>&1 | tail -15
```

Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add pyproject.toml src/launchlens/services/rate_limiter.py tests/test_services/test_rate_limiter.py && git commit -m "feat: add Redis token-bucket RateLimiter with Lua script"
```

---

### Task 5: Events Service — Full Outbox Pattern

**Files:**
- Modify: `src/launchlens/services/events.py` (replace stub)
- Create: `tests/test_services/test_events.py`

> **Note on `db_session` fixture:** The `db_session` async fixture is provided by `tests/conftest.py`, created in the scaffold plan (Task 11). It yields an `AsyncSession` bound to the test database with per-test rollback isolation. No new conftest work is needed here.

The Outbox Pattern: `emit_event()` writes an `Event` row AND an `Outbox` row in the **same transaction** as the caller's state change. This ensures events are never lost even if the process crashes before delivery. The Outbox Poller (Task 6) delivers and marks rows.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_services/test_events.py
import pytest
import uuid
from sqlalchemy import select
from launchlens.services.events import emit_event
from launchlens.models.event import Event
from launchlens.models.outbox import Outbox


@pytest.mark.asyncio
async def test_emit_event_writes_event_row(db_session):
    tenant_id = str(uuid.uuid4())
    listing_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="vision.completed",
        payload={"label_count": 5},
        tenant_id=tenant_id,
        listing_id=listing_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Event).where(Event.event_type == "vision.completed")
    )
    event = result.scalar_one()
    assert event.tenant_id == uuid.UUID(tenant_id)
    assert event.listing_id == uuid.UUID(listing_id)
    assert event.payload["label_count"] == 5


@pytest.mark.asyncio
async def test_emit_event_writes_outbox_row(db_session):
    tenant_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="coverage.failed",
        payload={"reason": "no photos"},
        tenant_id=tenant_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Outbox).where(Outbox.event_type == "coverage.failed")
    )
    outbox = result.scalar_one()
    assert outbox.delivered_at is None  # not yet delivered


@pytest.mark.asyncio
async def test_emit_event_without_listing_id(db_session):
    tenant_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="tenant.created",
        payload={"plan": "starter"},
        tenant_id=tenant_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Event).where(Event.event_type == "tenant.created")
    )
    event = result.scalar_one()
    assert event.listing_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_events.py -v 2>&1 | tail -20
```

Expected: FAIL — `TypeError: emit_event() got unexpected keyword argument 'session'` (stub signature mismatch)

- [ ] **Step 3: Replace stub with full Outbox implementation**

```python
# src/launchlens/services/events.py
"""
Event emission service — Outbox Pattern.

USAGE: Always call emit_event() within an existing SQLAlchemy session that
is part of a broader state-change transaction. Do NOT commit inside this
function — the caller commits, which atomically persists both the state
change AND the event.

  async with session.begin():
      listing.status = "vision_complete"
      await emit_event(session, "vision.completed", {...}, tenant_id=...)
      # single commit covers both
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from launchlens.models.event import Event
from launchlens.models.outbox import Outbox


async def emit_event(
    session: AsyncSession,
    event_type: str,
    payload: dict,
    tenant_id: str,
    listing_id: str | None = None,
) -> Event:
    """
    Write an Event row and an Outbox row in the caller's transaction.
    Returns the Event ORM object (not yet flushed — caller controls that).
    """
    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(listing_id) if listing_id else None

    event = Event(
        event_type=event_type,
        payload=payload,
        tenant_id=tid,
        listing_id=lid,
        occurred_at=datetime.now(timezone.utc),
    )
    outbox = Outbox(
        event_type=event_type,
        payload=payload,
        tenant_id=tid,
        listing_id=lid,
        created_at=datetime.now(timezone.utc),
        delivered_at=None,
    )

    session.add(event)
    session.add(outbox)
    return event
```

- [ ] **Step 4: Verify Event and Outbox models have the needed columns**

Read `src/launchlens/models/event.py` and `src/launchlens/models/outbox.py`. If any columns are missing (e.g., `occurred_at`, `delivered_at`), add them.

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -c "from launchlens.models.event import Event; from launchlens.models.outbox import Outbox; print('OK')" 2>&1
```

- [ ] **Step 5: Fix BaseAgent to pass session to emit_event**

The scaffold's `BaseAgent.handle_failure()` calls `emit_event(event_type, payload, ...)` with the old stub signature. The new signature requires a `session`. Update `base.py`:

```python
# In src/launchlens/agents/base.py — update handle_failure signature
async def handle_failure(self, error: Exception, context: "AgentContext", session=None) -> None:
    """
    Emit a failure event and re-raise so Temporal retries the activity.
    session is optional — if None, failure is logged but not persisted.
    """
    if session is not None:
        from launchlens.services.events import emit_event
        await emit_event(
            session=session,
            event_type=f"{self.agent_name}.failed",
            payload={"error": str(error), "error_type": type(error).__name__},
            tenant_id=str(context.tenant_id),
            listing_id=str(context.listing_id) if context.listing_id else None,
        )
    raise error
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_events.py -v 2>&1 | tail -20
```

Expected: 3 tests PASS

- [ ] **Step 7: Run full test suite to check no regressions**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short 2>&1 | tail -20
```

Expected: All previous tests still PASS

- [ ] **Step 8: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/services/events.py src/launchlens/agents/base.py tests/test_services/test_events.py && git commit -m "feat: implement Outbox Pattern in events service, update BaseAgent handle_failure"
```

---

### Task 6: Outbox Poller

**Files:**
- Create: `src/launchlens/services/outbox_poller.py`
- Modify: `src/launchlens/main.py`
- Create: `tests/test_services/test_outbox_poller.py`

> **Note on `db_session` fixture:** Same as Task 5 — provided by `tests/conftest.py` from the scaffold plan.

The poller runs as a FastAPI lifespan background task. Every 5 seconds it fetches undelivered Outbox rows, processes them (logs for now — real delivery to webhooks/queues is out of scope), and marks them delivered.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_services/test_outbox_poller.py
import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from launchlens.services.outbox_poller import OutboxPoller
from launchlens.models.outbox import Outbox


@pytest.mark.asyncio
async def test_poller_marks_rows_delivered(db_session):
    tenant_id = uuid.uuid4()
    outbox = Outbox(
        event_type="test.event",
        payload={"x": 1},
        tenant_id=tenant_id,
        listing_id=None,
        created_at=datetime.now(timezone.utc),
        delivered_at=None,
    )
    db_session.add(outbox)
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)  # inject session directly
    await poller._process_batch(db_session)

    await db_session.refresh(outbox)
    assert outbox.delivered_at is not None


@pytest.mark.asyncio
async def test_poller_skips_already_delivered_rows(db_session):
    tenant_id = uuid.uuid4()
    already_delivered = datetime.now(timezone.utc)
    outbox = Outbox(
        event_type="test.event",
        payload={"x": 2},
        tenant_id=tenant_id,
        listing_id=None,
        created_at=already_delivered,
        delivered_at=already_delivered,  # already delivered
    )
    db_session.add(outbox)
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)
    count = await poller._process_batch(db_session)
    assert count == 0  # no rows processed


@pytest.mark.asyncio
async def test_poller_processes_multiple_rows(db_session):
    tenant_id = uuid.uuid4()
    for i in range(3):
        db_session.add(Outbox(
            event_type=f"test.event.{i}",
            payload={"i": i},
            tenant_id=tenant_id,
            listing_id=None,
            created_at=datetime.now(timezone.utc),
            delivered_at=None,
        ))
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)
    count = await poller._process_batch(db_session)
    assert count == 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_outbox_poller.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.services.outbox_poller'`

- [ ] **Step 3: Implement OutboxPoller**

```python
# src/launchlens/services/outbox_poller.py
"""
Outbox Poller — background task for the Outbox Pattern.

Runs every POLL_INTERVAL seconds. Fetches undelivered Outbox rows,
delivers them (logs + future: pushes to webhook/queue), marks delivered.

Wired into FastAPI lifespan in main.py.
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.outbox import Outbox

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds
BATCH_SIZE = 100


class OutboxPoller:
    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False

    async def _process_batch(self, session: AsyncSession) -> int:
        """Fetch undelivered rows, deliver, mark done. Returns count processed."""
        result = await session.execute(
            select(Outbox)
            .where(Outbox.delivered_at.is_(None))
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        rows = result.scalars().all()
        now = datetime.now(timezone.utc)
        for row in rows:
            # Delivery: log now; extend here for webhooks/queues later
            logger.info(
                "outbox.deliver event_type=%s tenant_id=%s",
                row.event_type,
                row.tenant_id,
            )
            row.delivered_at = now
        return len(rows)

    async def run(self):
        """Long-running poll loop. Call from FastAPI lifespan."""
        self._running = True
        while self._running:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        await self._process_batch(session)
            except Exception:
                logger.exception("outbox_poller: error during batch")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        self._running = False
```

- [ ] **Step 4: Wire poller into FastAPI lifespan**

Read `src/launchlens/main.py`, then add lifespan:

```python
# In src/launchlens/main.py — add lifespan context manager
from contextlib import asynccontextmanager
from launchlens.database import AsyncSessionLocal
from launchlens.services.outbox_poller import OutboxPoller
import asyncio

@asynccontextmanager
async def lifespan(app):
    poller = OutboxPoller(session_factory=AsyncSessionLocal)
    task = asyncio.create_task(poller.run())
    yield
    poller.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

# Pass to FastAPI constructor:
# app = FastAPI(lifespan=lifespan, ...)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_services/test_outbox_poller.py -v 2>&1 | tail -15
```

Expected: 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short 2>&1 | tail -10
```

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/services/outbox_poller.py src/launchlens/main.py tests/test_services/test_outbox_poller.py && git commit -m "feat: add OutboxPoller background task, wire into FastAPI lifespan"
```

---

### Task 7: Google Vision Provider

**Files:**
- Create: `src/launchlens/providers/google_vision.py`
- Create: `tests/test_providers/test_google_vision.py`

Uses httpx to call the Google Cloud Vision REST API. No `google-cloud-vision` SDK — keeps the dependency footprint small.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers/test_google_vision.py
import pytest
import httpx
from pytest_httpx import HTTPXMock
from launchlens.providers.google_vision import GoogleVisionProvider
from launchlens.providers.base import VisionLabel

FAKE_RESPONSE = {
    "responses": [{
        "labelAnnotations": [
            {"description": "Living room", "score": 0.97, "mid": "/m/01234"},
            {"description": "Interior design", "score": 0.89, "mid": "/m/05678"},
            {"description": "Hardwood", "score": 0.82, "mid": "/m/09abc"},
        ]
    }]
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_RESPONSE)
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert len(labels) == 3
    assert all(isinstance(l, VisionLabel) for l in labels)
    assert labels[0].name == "Living room"
    assert labels[0].confidence == pytest.approx(0.97)


@pytest.mark.asyncio
async def test_analyze_maps_category_from_score(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_RESPONSE)
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    # All labels come from labelAnnotations — category is "general"
    assert all(l.category == "general" for l in labels)


@pytest.mark.asyncio
async def test_analyze_empty_annotations_returns_empty_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"responses": [{}]})
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert labels == []


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=403)
    provider = GoogleVisionProvider(api_key="bad-key")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_google_vision.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.providers.google_vision'`

- [ ] **Step 3: Implement GoogleVisionProvider**

```python
# src/launchlens/providers/google_vision.py
"""
Google Cloud Vision provider.

Uses the REST API directly (not the google-cloud-vision SDK) to keep
the dependency footprint minimal.

Endpoint: POST https://vision.googleapis.com/v1/images:annotate
"""
import httpx
from launchlens.config import settings
from .base import VisionLabel, VisionProvider

_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionProvider(VisionProvider):
    def __init__(self, api_key: str = None):
        self._api_key = api_key or settings.google_vision_api_key

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "requests": [{
                "image": {"source": {"imageUri": image_url}},
                "features": [{"type": "LABEL_DETECTION", "maxResults": 20}],
            }]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _ENDPOINT,
                params={"key": self._api_key},
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

        data = response.json()
        annotations = (
            data.get("responses", [{}])[0].get("labelAnnotations", [])
        )
        return [
            VisionLabel(
                name=ann["description"],
                confidence=ann["score"],
                category="general",
            )
            for ann in annotations
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_google_vision.py -v 2>&1 | tail -15
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/google_vision.py tests/test_providers/test_google_vision.py && git commit -m "feat: add GoogleVisionProvider using httpx REST"
```

---

### Task 8: OpenAI Vision Provider (GPT-4V)

**Files:**
- Create: `src/launchlens/providers/openai_vision.py`
- Create: `tests/test_providers/test_openai_vision.py`

GPT-4V is used for Tier 2 (top-N candidate re-ranking). Uses httpx. Semaphore(5) caps concurrent calls to avoid hitting OpenAI rate limits.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers/test_openai_vision.py
import pytest
import asyncio
import httpx
from pytest_httpx import HTTPXMock
from launchlens.providers.openai_vision import OpenAIVisionProvider
from launchlens.providers.base import VisionLabel

FAKE_GPT_RESPONSE = {
    "choices": [{
        "message": {
            "content": '{"labels": [{"name": "primary exterior", "confidence": 0.95, "category": "shot_type"}, {"name": "golden hour", "confidence": 0.88, "category": "quality"}]}'
        }
    }]
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_GPT_RESPONSE)
    provider = OpenAIVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert len(labels) == 2
    assert all(isinstance(l, VisionLabel) for l in labels)
    assert labels[0].name == "primary exterior"
    assert labels[0].category == "shot_type"


@pytest.mark.asyncio
async def test_analyze_raises_on_malformed_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "choices": [{"message": {"content": "not valid json"}}]
    })
    provider = OpenAIVisionProvider(api_key="test-key")
    with pytest.raises(ValueError, match="GPT-4V returned unparseable JSON"):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=429)
    provider = OpenAIVisionProvider(api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    # Verify the semaphore is initialized with the correct value
    provider = OpenAIVisionProvider(api_key="test-key", max_concurrent=5)
    assert provider._semaphore._value == 5
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_openai_vision.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.providers.openai_vision'`

- [ ] **Step 3: Implement OpenAIVisionProvider**

```python
# src/launchlens/providers/openai_vision.py
"""
OpenAI GPT-4V provider — used for Tier 2 aesthetic re-ranking.

Sends the image URL in the messages array (vision feature).
Expects the model to return a JSON object with a "labels" array.

Concurrency: Semaphore(max_concurrent) prevents more than N simultaneous
calls to avoid OpenAI rate limits. Default is 5.
"""
import asyncio
import json
import httpx
from launchlens.config import settings
from .base import VisionLabel, VisionProvider

_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_SYSTEM_PROMPT = (
    "You are a real estate photography analyst. "
    "Analyze the image and return a JSON object with a single key 'labels' "
    "containing an array of objects, each with 'name', 'confidence' (0.0-1.0), "
    "and 'category' (one of: shot_type, quality, feature, room) fields. "
    "Return only valid JSON, no markdown."
)


class OpenAIVisionProvider(VisionProvider):
    def __init__(self, api_key: str = None, max_concurrent: int = 5):
        self._api_key = api_key or settings.openai_api_key
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "Analyze this real estate photo."},
                    ],
                },
            ],
            "max_tokens": 500,
        }
        async with self._semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"GPT-4V returned unparseable JSON: {content!r}") from e

        return [
            VisionLabel(
                name=item["name"],
                confidence=item["confidence"],
                category=item.get("category", "general"),
            )
            for item in data.get("labels", [])
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_openai_vision.py -v 2>&1 | tail -15
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/openai_vision.py tests/test_providers/test_openai_vision.py && git commit -m "feat: add OpenAIVisionProvider (GPT-4V) with Semaphore concurrency cap"
```

---

### Task 9: Claude Provider (Content Generation)

**Files:**
- Create: `src/launchlens/providers/claude.py`
- Create: `tests/test_providers/test_claude.py`

Used by the Content Agent to generate listing copy. Uses the `anthropic` SDK (already a transitive dep via the PRD — add it explicitly).

- [ ] **Step 1: Add anthropic to project dependencies**

Edit `pyproject.toml` — add `"anthropic>=0.28"` to `[project.dependencies]`.

- [ ] **Step 2: Install**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pip install -e ".[dev]" 2>&1 | tail -5
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_providers/test_claude.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from launchlens.providers.claude import ClaudeProvider
from launchlens.providers.base import LLMProvider


def test_claude_provider_is_llm_provider():
    with patch("launchlens.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
        assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_complete_returns_string():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="A beautiful sun-drenched kitchen.")]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("launchlens.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        provider = ClaudeProvider(api_key="test-key")
        result = await provider.complete(
            prompt="Write a description for this kitchen.",
            context={"listing_id": "abc-123", "beds": 3},
        )

    assert result == "A beautiful sun-drenched kitchen."


@pytest.mark.asyncio
async def test_complete_includes_context_in_prompt():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Lovely home.")]

    mock_client = MagicMock()
    captured_kwargs = {}

    async def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    mock_client.messages.create = capture

    with patch("launchlens.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        provider = ClaudeProvider(api_key="test-key")
        await provider.complete(
            prompt="Write listing copy.",
            context={"beds": 4, "baths": 2},
        )

    # Context should appear in the messages sent to Claude
    messages = captured_kwargs.get("messages", [])
    all_content = " ".join(str(m) for m in messages)
    assert "beds" in all_content or "4" in all_content
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_claude.py -v 2>&1 | tail -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.providers.claude'`

- [ ] **Step 5: Implement ClaudeProvider**

```python
# src/launchlens/providers/claude.py
"""
Anthropic Claude provider — used for listing copy generation.

Model: claude-sonnet-4-6 (latest capable model per environment config).
Context is serialized into the user message so Claude has full listing metadata.
"""
import json
import anthropic
from launchlens.config import settings
from .base import LLMProvider

_MODEL = "claude-sonnet-4-6"
_SYSTEM_PROMPT = (
    "You are an expert real estate copywriter. "
    "Write compelling, accurate, and legally compliant listing descriptions. "
    "Avoid Fair Housing Act violations. Be specific about features, never generic."
)


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str = None):
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    async def complete(self, prompt: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2) if context else ""
        user_content = f"{prompt}\n\nContext:\n{context_str}" if context_str else prompt

        message = await self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return message.content[0].text
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_claude.py -v 2>&1 | tail -15
```

Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add pyproject.toml src/launchlens/providers/claude.py tests/test_providers/test_claude.py && git commit -m "feat: add ClaudeProvider for listing copy generation"
```

---

### Task 10: Update Factory for Real Providers + Full Provider Suite Test

**Files:**
- Modify: `src/launchlens/providers/factory.py` (verify google_vision + claude routes work)
- Create: `tests/test_providers/test_factory_real.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers/test_factory_real.py
"""
Verify that factory returns the correct concrete class for each provider type.
Tests use USE_MOCK_PROVIDERS=True to avoid real API calls.
"""
import pytest
from unittest.mock import patch
from launchlens.providers.factory import get_vision_provider, get_llm_provider, get_template_provider
from launchlens.providers.mock import MockVisionProvider, MockLLMProvider, MockTemplateProvider
from launchlens.providers.google_vision import GoogleVisionProvider
from launchlens.providers.claude import ClaudeProvider


def test_factory_returns_google_vision_when_mock_disabled():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.google_vision_api_key = "test"
        provider = get_vision_provider()
        assert isinstance(provider, GoogleVisionProvider)


def test_factory_returns_claude_when_mock_disabled():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.anthropic_api_key = "test"
        provider = get_llm_provider()
        assert isinstance(provider, ClaudeProvider)


def test_factory_returns_mock_template_always():
    # TemplateProvider real impl (Canva) not yet built — always mock
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/test_factory_real.py -v 2>&1 | tail -15
```

Expected: FAIL with `AssertionError` — `test_factory_returns_google_vision_when_mock_disabled` fails because the factory currently returns `MockVisionProvider` (imports are deferred and `use_mock_providers=False` path returns `GoogleVisionProvider`, but the `google_vision` module may not yet be importable). `test_factory_returns_claude_when_mock_disabled` fails similarly. At minimum one `AssertionError: assert isinstance(...)` should appear.

- [ ] **Step 3: Verify factory imports work, fix if needed**

Run:
```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -c "from launchlens.providers.factory import get_vision_provider, get_llm_provider; print('OK')" 2>&1
```

If any ImportError, fix the factory's deferred imports.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_providers/ -v 2>&1 | tail -20
```

Expected: All provider tests PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/providers/factory.py tests/test_providers/test_factory_real.py && git commit -m "feat: verify provider factory routes for all concrete providers"
```

---

### Task 11: Final Integration + Full Suite

**Files:**
- No new files — wire up and verify everything runs together.

- [ ] **Step 1: Run the complete test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -30
```

Expected: All tests PASS. Note the count.

- [ ] **Step 2: Verify no import errors in the full package**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -c "
import launchlens.providers
import launchlens.services.storage
import launchlens.services.rate_limiter
import launchlens.services.events
import launchlens.services.outbox_poller
print('All imports OK')
" 2>&1
```

Expected: `All imports OK`

- [ ] **Step 3: Tag the milestone**

```bash
cd /c/Users/Jeff/launchlens && git tag v0.2.0-core-services && echo "Tagged v0.2.0-core-services"
```

- [ ] **Step 4: Final commit (if any last fixes)**

```bash
cd /c/Users/Jeff/launchlens && git status
```

If clean, no commit needed. If dirty, commit with descriptive message.

---

## NOT in scope

- Canva API integration (TemplateProvider real impl) — placeholder mock used; will be a separate plan
- Webhook delivery in OutboxPoller — logs only; real delivery (HTTP webhooks, SQS) deferred
- OpenAI Tier 2 concurrent batch processing orchestration — that belongs in the Vision Agent plan
- Redis connection pooling tuning — defaults are fine for MVP
- S3 multipart upload for large files — not needed until video assets
- Retry logic with exponential backoff for provider HTTP errors — deferred to Agent Pipeline plan

## What already exists

- `src/launchlens/services/events.py` — stub that this plan replaces with full Outbox Pattern
- `src/launchlens/providers/__init__.py` — empty file; this plan fills it with factory exports
- `src/launchlens/agents/base.py` — `handle_failure()` stub calls old `emit_event` signature; Task 5 updates it
- `src/launchlens/config.py` — Settings class exists; Task 1 adds the new API key fields
- `moto` and `fakeredis` — not yet in dependencies; Tasks 3 and 4 add them
