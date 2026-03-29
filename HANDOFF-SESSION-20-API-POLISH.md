# Session 20: API Polish — OpenAPI Docs, Response Models, Pagination, Versioning

## Context
The API uses default FastAPI/Swagger with no customization. Many endpoints return raw dicts without response models, there's no pagination standard, no rate limit headers in responses, and no API versioning. For a platform that agents and integrations will consume, this needs work.

## Task 1: OpenAPI Documentation
**File:** `src/launchlens/main.py`

Add metadata to FastAPI app:
```python
app = FastAPI(
    title="LaunchLens API",
    version="1.0.0",
    description="AI-powered real estate listing media automation. Upload property photos, get marketing-ready assets.",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

Add `tags_metadata` with descriptions for each router group.

## Task 2: Response Models for All Endpoints
Several endpoints return raw dicts. Add Pydantic models:

**`src/launchlens/api/schemas/listings.py`** — add:
```python
class ActionResponse(BaseModel):
    listing_id: str
    state: str

class CancelResponse(BaseModel):
    listing_id: str
    state: str
    credits_refunded: int

class PipelineStatusResponse(BaseModel):
    listing_id: str
    listing_state: str
    steps: list[dict]
```

Apply `response_model=` to: retry, cancel, approve, reject, pipeline-status endpoints.

## Task 3: Standardize Pagination
**New file:** `src/launchlens/api/schemas/pagination.py`

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
```

Apply to: `GET /listings`, `GET /credits/transactions`, `GET /admin/tenants`. Accept `?page=1&page_size=20` query params.

## Task 4: Rate Limit Headers
**File:** `src/launchlens/middleware/rate_limit.py`

After rate limit check, add headers to response:
```python
response.headers["X-RateLimit-Limit"] = str(limit)
response.headers["X-RateLimit-Remaining"] = str(remaining)
response.headers["X-RateLimit-Reset"] = str(reset_timestamp)
```

## Task 5: API Versioning (Optional)
Add `/api/v1/` prefix to all routes. Keep `/health` at root. This is optional but recommended for future backward compatibility.

## Verification
- `/docs` shows organized API with tag descriptions
- All endpoints have response models visible in Swagger
- `GET /listings?page=1&page_size=10` returns paginated response
- Response headers include `X-RateLimit-*`
