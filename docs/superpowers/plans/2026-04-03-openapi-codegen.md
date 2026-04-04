# OpenAPI Code Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate typed API clients from OpenAPI specs for the TypeScript frontend (from FastAPI) and the Canva Python integration.

**Architecture:** Frontend uses `openapi-typescript` for type generation + `openapi-fetch` for a typed fetch wrapper, with the existing `ApiClient` class preserved as a thin wrapper. Canva uses `openapi-generator-cli` to produce a Python async client replacing the hand-rolled httpx calls.

**Tech Stack:** openapi-typescript, openapi-fetch, @openapitools/openapi-generator-cli, FastAPI (existing), httpx (existing)

---

## File Structure

```
frontend/
  src/lib/
    generated/
      api.d.ts              # CREATE — generated types from FastAPI spec (DO NOT EDIT)
    api-client.ts           # MODIFY — refactor internals to use openapi-fetch
    types.ts                # MODIFY — re-export from generated/ for backwards compat
  package.json              # MODIFY — add deps + generate-api script

scripts/
  generate-canva-client.sh  # CREATE — downloads Canva spec, runs generator

src/listingjet/providers/
  canva_generated/          # CREATE — generated Python client (DO NOT EDIT)
  canva.py                  # MODIFY — use generated client instead of raw httpx
```

---

### Task 1: Install frontend codegen dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install openapi-typescript and openapi-fetch**

```bash
cd C:/Users/Jeff/launchlens/frontend
npm install openapi-fetch
npm install -D openapi-typescript
```

- [ ] **Step 2: Add generate-api script to package.json**

Add to the `"scripts"` section in `frontend/package.json`:

```json
"generate-api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/generated/api.d.ts"
```

- [ ] **Step 3: Create the generated directory**

```bash
mkdir -p C:/Users/Jeff/launchlens/frontend/src/lib/generated
```

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add frontend/package.json frontend/package-lock.json frontend/src/lib/generated/
git commit -m "chore: add openapi-typescript and openapi-fetch dependencies"
```

---

### Task 2: Generate TypeScript types from FastAPI spec

**Files:**
- Create: `frontend/src/lib/generated/api.d.ts`

**Prerequisite:** The FastAPI backend must be running locally on port 8000. If it's not running, start it first. The dev server exposes `/openapi.json` automatically.

- [ ] **Step 1: Verify the backend serves its OpenAPI spec**

```bash
curl -s http://localhost:8000/openapi.json | head -5
```

Expected: JSON starting with `{"openapi":"3.1.0","info":{"title":"ListingJet API"...`

If the backend isn't running, start it:
```bash
cd C:/Users/Jeff/launchlens
python -m uvicorn listingjet.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Run the generator**

```bash
cd C:/Users/Jeff/launchlens/frontend
npm run generate-api
```

Expected: Creates `src/lib/generated/api.d.ts` with `paths` and `components` type exports.

- [ ] **Step 3: Verify the generated file has path types**

```bash
grep -c "paths" C:/Users/Jeff/launchlens/frontend/src/lib/generated/api.d.ts
```

Expected: Multiple matches — the file should contain path definitions for `/listings`, `/auth/login`, `/brand-kit`, etc.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add frontend/src/lib/generated/api.d.ts
git commit -m "chore: generate TypeScript types from FastAPI OpenAPI spec"
```

---

### Task 3: Refactor api-client.ts to use openapi-fetch internally

**Files:**
- Modify: `frontend/src/lib/api-client.ts`

This is the core task. The existing `ApiClient` class keeps its public interface (every method name, every parameter, every return type stays the same). Internally, it switches from raw `fetch()` to `openapi-fetch`'s typed `client.GET()` / `client.POST()` / etc.

**Important:** Read `frontend/AGENTS.md` and check `node_modules/next/dist/docs/` for any relevant Next.js breaking changes before modifying imports.

- [ ] **Step 1: Read the current api-client.ts to confirm it hasn't changed**

```bash
head -20 C:/Users/Jeff/launchlens/frontend/src/lib/api-client.ts
```

Confirm the file starts with the type imports from `./types` and defines `const API_URL = ...`.

- [ ] **Step 2: Replace the import block and add openapi-fetch client creation**

Replace the top of `api-client.ts` (lines 1-46) with:

```typescript
import createClient from "openapi-fetch";
import type { paths } from "./generated/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

// Re-export legacy types from generated spec for backwards compat
export type { PropertyLookupResponse } from "./types-legacy";

const fetchClient = createClient<paths>({ baseUrl: API_URL });
```

**Note:** We do NOT remove any public methods. Every method in the class stays. We only change the internals of the `request<T>()` method and add typed overloads where the generated paths provide type safety.

- [ ] **Step 3: Update the private request method to use openapi-fetch middleware for auth**

The `openapi-fetch` library supports middleware for injecting headers. Update the class:

```typescript
class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    // Update the openapi-fetch client middleware
    fetchClient.use({
      async onRequest({ request }) {
        if (token) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
        request.headers.set("ngrok-skip-browser-warning", "true");
        return request;
      },
    });
  }

  getToken(): string | null {
    return this.token;
  }

  // Keep the raw request method as a fallback for endpoints not yet in the spec
  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      const err = new Error(error.detail || `Request failed: ${response.status}`) as Error & { status: number };
      err.status = response.status;
      throw err;
    }

    return response.json();
  }
```

**Key decision:** Keep the raw `request<T>()` method as a private fallback. Migrate methods to typed `fetchClient` calls incrementally. This avoids a big-bang rewrite — methods can be migrated one-by-one in future PRs.

- [ ] **Step 4: Migrate a few key methods to typed openapi-fetch calls as examples**

Update these methods to use the typed client (showing the pattern for future migration):

```typescript
  // Auth — typed
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data, error } = await fetchClient.POST("/auth/login", {
      body: { email, password },
    });
    if (error) {
      const err = new Error((error as any).detail || "Login failed") as Error & { status: number };
      err.status = (error as any).status || 400;
      throw err;
    }
    return data as TokenResponse;
  }

  async me(): Promise<UserResponse> {
    const { data, error } = await fetchClient.GET("/auth/me");
    if (error) {
      const err = new Error((error as any).detail || "Failed to fetch user") as Error & { status: number };
      err.status = (error as any).status || 401;
      throw err;
    }
    return data as UserResponse;
  }
```

Leave all other methods using the existing `this.request<T>()` for now — they still work and can be migrated later.

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd C:/Users/Jeff/launchlens/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: No errors (or only pre-existing ones unrelated to api-client).

- [ ] **Step 6: Run the dev server to verify nothing is broken**

```bash
cd C:/Users/Jeff/launchlens/frontend
npm run build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add frontend/src/lib/api-client.ts
git commit -m "feat: wire openapi-fetch into ApiClient with typed auth methods"
```

---

### Task 4: Update types.ts to re-export from generated types

**Files:**
- Modify: `frontend/src/lib/types.ts`

For backwards compatibility, keep `types.ts` exporting all the same interfaces. Add a comment pointing to the generated source. Existing page imports (`from "./types"`) continue working.

- [ ] **Step 1: Add re-export comment at the top of types.ts**

Add this comment to the top of `frontend/src/lib/types.ts`:

```typescript
// NOTE: These types are manually maintained for backwards compatibility.
// The canonical types are generated in ./generated/api.d.ts from the FastAPI OpenAPI spec.
// Run `npm run generate-api` to regenerate. Over time, imports should migrate to ./generated/api.
```

Leave all existing interfaces in place — they still work and match the backend.

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add frontend/src/lib/types.ts
git commit -m "docs: add generated types migration note to types.ts"
```

---

### Task 5: Create Canva client generation script

**Files:**
- Create: `scripts/generate-canva-client.sh`

- [ ] **Step 1: Install openapi-generator-cli globally via npm**

```bash
npm install -g @openapitools/openapi-generator-cli
```

- [ ] **Step 2: Create the generation script**

Create `C:/Users/Jeff/launchlens/scripts/generate-canva-client.sh`:

```bash
#!/bin/bash
set -euo pipefail

SPEC_URL="https://www.canva.dev/sources/connect/api/latest/api.yml"
OUTPUT_DIR="src/listingjet/providers/canva_generated"
TEMP_SPEC="/tmp/canva-openapi-spec.yml"

echo "Downloading Canva Connect API spec..."
curl -sL "$SPEC_URL" -o "$TEMP_SPEC"

echo "Generating Python client..."
openapi-generator-cli generate \
  -i "$TEMP_SPEC" \
  -g python \
  -o "$OUTPUT_DIR" \
  --additional-properties=packageName=canva_client,asyncio=true,library=asyncio \
  --global-property=models,apis,supportingFiles

echo "Cleaning up..."
rm -f "$TEMP_SPEC"

echo "Done! Generated client in $OUTPUT_DIR"
```

- [ ] **Step 3: Make it executable**

```bash
chmod +x C:/Users/Jeff/launchlens/scripts/generate-canva-client.sh
```

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add scripts/generate-canva-client.sh
git commit -m "chore: add Canva API client generation script"
```

---

### Task 6: Generate the Canva Python client

**Files:**
- Create: `src/listingjet/providers/canva_generated/` (entire directory)

- [ ] **Step 1: Run the generation script**

```bash
cd C:/Users/Jeff/launchlens
bash scripts/generate-canva-client.sh
```

Expected: Creates `src/listingjet/providers/canva_generated/` with `api/`, `models/`, and supporting files.

- [ ] **Step 2: Verify the generated client has the key APIs**

```bash
ls C:/Users/Jeff/launchlens/src/listingjet/providers/canva_generated/api/
```

Expected: Files for autofill, export, asset upload, brand template APIs.

- [ ] **Step 3: Add an `__init__.py` if missing**

```bash
touch C:/Users/Jeff/launchlens/src/listingjet/providers/canva_generated/__init__.py
```

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/canva_generated/
git commit -m "chore: generate Canva Connect API Python client from OpenAPI spec"
```

---

### Task 7: Refactor canva.py to use generated client

**Files:**
- Modify: `src/listingjet/providers/canva.py`
- Test: `tests/test_providers/test_canva.py`

This task replaces the hand-rolled httpx calls in `canva.py` with the generated client. The public interface (`CanvaTemplateProvider.render(template_id, data) -> bytes`) stays the same.

- [ ] **Step 1: Read the generated client structure to understand its API**

```bash
ls C:/Users/Jeff/launchlens/src/listingjet/providers/canva_generated/api/
grep -r "class.*Api" C:/Users/Jeff/launchlens/src/listingjet/providers/canva_generated/api/ | head -10
```

Identify the API classes for autofill, export, and asset upload.

- [ ] **Step 2: Read the existing canva.py test**

```bash
cat C:/Users/Jeff/launchlens/tests/test_providers/test_canva.py
```

Understand what the existing tests cover so you preserve coverage.

- [ ] **Step 3: Update canva.py to import from the generated client**

Rewrite `canva.py` to use the generated API classes instead of raw httpx. The key changes:
- Replace `httpx.AsyncClient` with the generated client's configuration + API instances
- Replace manual `_poll_job` with the generated client's built-in polling (if available) or keep a simplified version
- Replace `_build_autofill_data` with the generated model classes
- Keep `_format_address`, `_format_price`, `_format_sqft` helpers — they format display data

```python
# src/listingjet/providers/canva.py
"""Canva Connect API template provider using generated client."""
import asyncio
import logging

from .base import TemplateProvider

logger = logging.getLogger(__name__)


class CanvaTemplateProvider(TemplateProvider):
    """Renders listing flyers via the Canva Connect API."""

    def __init__(self, api_key: str, llm_provider=None):
        self._api_key = api_key
        self._llm = llm_provider

    def _get_config(self):
        from canva_generated import Configuration
        config = Configuration()
        config.access_token = self._api_key
        return config

    async def render(self, template_id: str, data: dict) -> bytes:
        """
        Autofill a Canva brand template with listing + brand data, export as PDF.
        """
        from canva_generated import ApiClient
        from canva_generated.api import AutofillApi, ExportApi, AssetApi

        config = self._get_config()
        async with ApiClient(config) as client:
            # 1. Upload hero photo if provided
            hero_asset_id = None
            if data.get("hero_image_url"):
                hero_asset_id = await self._upload_hero(client, data["hero_image_url"])

            # 2. Autofill template
            autofill_api = AutofillApi(client)
            autofill_fields = self._build_autofill_data(data, hero_asset_id)
            autofill_job = await autofill_api.create_design_autofill_job({
                "brand_template_id": template_id,
                "data": autofill_fields,
            })
            design_id = await self._poll_until_done(
                lambda: autofill_api.get_design_autofill_job(autofill_job.job.id),
                result_key="design_id",
            )

            # 3. Export as PDF
            export_api = ExportApi(client)
            export_job = await export_api.create_export({
                "design_id": design_id,
                "format": "pdf",
            })
            pdf_url = await self._poll_until_done(
                lambda: export_api.get_export(export_job.job.id),
                result_key="url",
            )

            # 4. Download PDF
            import httpx
            async with httpx.AsyncClient(timeout=60) as http:
                pdf_resp = await http.get(pdf_url)
                pdf_resp.raise_for_status()
                return pdf_resp.content

    async def _upload_hero(self, client, image_url: str) -> str | None:
        """Upload hero photo as Canva asset."""
        try:
            from canva_generated.api import AssetApi
            asset_api = AssetApi(client)
            job = await asset_api.create_asset_upload_job({"url": image_url})
            asset_id = await self._poll_until_done(
                lambda: asset_api.get_asset_upload_job(job.job.id),
                result_key="asset_id",
                max_attempts=10,
                delay_s=1.5,
            )
            return asset_id
        except Exception:
            logger.warning("canva.hero_upload_failed url=%s", image_url, exc_info=True)
            return None

    async def _poll_until_done(self, get_fn, result_key: str, max_attempts=20, delay_s=2.0) -> str:
        """Poll a Canva async job until success."""
        for _ in range(max_attempts):
            result = await get_fn()
            status = result.job.status
            if status == "success":
                return getattr(result.job.result, result_key)
            if status == "failed":
                raise RuntimeError(f"Canva job failed: {result.job}")
            await asyncio.sleep(delay_s)
        raise TimeoutError("Canva job did not complete in time")

    @staticmethod
    def _build_autofill_data(data: dict, hero_asset_id: str | None = None) -> list[dict]:
        """Convert listing + brand data into Canva autofill field objects."""
        fields = []

        def add_text(name, value):
            if value:
                fields.append({"name": name, "value": {"type": "text", "text": str(value)}})

        # Property fields
        addr = data.get("address", {})
        parts = [addr.get("street", "")]
        city_state = ", ".join(filter(None, [addr.get("city"), addr.get("state")]))
        if city_state:
            parts.append(city_state)
        if addr.get("zip"):
            parts.append(addr["zip"])
        add_text("property_address", " ".join(filter(None, parts)))

        meta = data.get("metadata", {})
        price = meta.get("price")
        if price:
            add_text("listing_price", f"${price:,.0f}" if isinstance(price, (int, float)) else str(price))
        add_text("bedrooms", str(meta.get("beds", "")))
        add_text("bathrooms", str(meta.get("baths", "")))
        sqft = meta.get("sqft")
        if sqft:
            add_text("square_footage", f"{sqft:,}" if isinstance(sqft, (int, float)) else str(sqft))
        add_text("property_description", data.get("description", ""))

        # Brand fields
        add_text("agent_name", data.get("agent_name", ""))
        add_text("brokerage_name", data.get("brokerage_name", ""))
        add_text("primary_color", data.get("primary_color", ""))

        # Hero image
        if hero_asset_id:
            fields.append({"name": "hero_image", "value": {"type": "image", "asset_id": hero_asset_id}})
        elif data.get("hero_image_url"):
            add_text("hero_image_url", data["hero_image_url"])

        if data.get("logo_url"):
            add_text("logo_url", data["logo_url"])

        return fields
```

**Note:** The exact import paths (`canva_generated.api.AutofillApi`, etc.) depend on what the generator produces. Read the generated code in Step 1 and adjust the imports accordingly.

- [ ] **Step 4: Update the existing test to work with the new implementation**

The test should mock the generated API classes instead of raw httpx. Read the existing test first, then update it to mock the generated client's API methods.

- [ ] **Step 5: Run the canva tests**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/test_providers/test_canva.py -v
```

Expected: All tests pass.

- [ ] **Step 6: Run the full test suite**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -15
```

Expected: No new failures.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/canva.py tests/test_providers/test_canva.py
git commit -m "feat: replace hand-rolled Canva httpx calls with generated API client"
```

---

### Task 8: Add CANVA_DEFAULT_TEMPLATE_ID to .env examples

**Files:**
- Modify: `.env.example` (or `.env.production.example` if it exists)

- [ ] **Step 1: Find the env example file**

```bash
ls C:/Users/Jeff/launchlens/.env*
```

- [ ] **Step 2: Add the Canva env vars**

Add these lines to the env example file(s):

```bash
# Canva Connect API
CANVA_API_KEY=
CANVA_DEFAULT_TEMPLATE_ID=
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add .env*
git commit -m "docs: add CANVA_API_KEY and CANVA_DEFAULT_TEMPLATE_ID to env examples"
```

---

## Summary of Commands

| Action | Command |
|--------|---------|
| Generate TS types | `cd frontend && npm run generate-api` |
| Generate Canva client | `bash scripts/generate-canva-client.sh` |
| Verify TS compiles | `cd frontend && npx tsc --noEmit` |
| Run Python tests | `python -m pytest tests/ -x -q` |
| Build frontend | `cd frontend && npm run build` |
