# OpenAPI Code Generation Integration

**Date:** 2026-04-03
**Status:** Approved

## Goal

Replace hand-written API types and generate typed clients from OpenAPI specs for:
1. **TypeScript frontend client** — from the FastAPI backend's `/openapi.json`
2. **Python Canva client** — from Canva's published Connect API spec

## Decisions

- **Frontend toolchain:** `openapi-typescript` (type generation) + `openapi-fetch` (typed fetch wrapper)
- **Canva toolchain:** `openapi-generator-cli` via npx/Docker (Python async client)
- **Regeneration trigger:** Manual `npm run generate-api` / `python scripts/generate-canva-client.sh`
- **Migration strategy:** Generate + Wrap — generated client behind existing `apiClient` interface so no page-level changes needed

## 1. TypeScript Frontend Client

### Tools
- `openapi-typescript` — generates TypeScript types from OpenAPI 3.x spec
- `openapi-fetch` — tiny (~2KB) typed fetch client that uses the generated types

### File Structure
```
frontend/
  scripts/
    generate-api.ts          # Fetches /openapi.json, runs openapi-typescript
  src/lib/
    generated/
      api.d.ts               # Generated types (DO NOT EDIT)
    api-client.ts            # Updated: wraps openapi-fetch, preserves existing interface
    types.ts                 # Deprecated: re-exports from generated/ for backwards compat
```

### How It Works

1. `npm run generate-api` fetches `http://localhost:8000/openapi.json`
2. `openapi-typescript` generates `src/lib/generated/api.d.ts` with path types, request/response schemas
3. `api-client.ts` is updated to use `createClient()` from `openapi-fetch` internally
4. The existing `apiClient.createListing()` etc. interface is preserved as a wrapper
5. `types.ts` re-exports generated types so existing imports don't break

### Wrapper Pattern
```typescript
import createClient from "openapi-fetch";
import type { paths } from "./generated/api";

const client = createClient<paths>({ baseUrl: API_URL });

class ApiClient {
  private token: string | null = null;

  setToken(token: string) { this.token = token; }

  private headers() {
    return {
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      "ngrok-skip-browser-warning": "true",
    };
  }

  async getListings() {
    const { data, error } = await client.GET("/listings/", {
      headers: this.headers(),
    });
    if (error) throw error;
    return data;
  }

  // ... other methods delegate similarly
}
```

### npm Scripts
```json
{
  "generate-api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/generated/api.d.ts"
}
```

### Dependencies
- `openapi-typescript` (devDependency)
- `openapi-fetch` (dependency)

## 2. Python Canva Client

### Source Spec
- URL: `https://www.canva.dev/sources/connect/api/latest/api.yml`
- Mirrored: `https://github.com/canva-sdks/canva-connect-api-starter-kit/blob/main/openapi/spec.yml`

### Tools
- `openapi-generator-cli` via npx (generates Python async client using `asyncio` + `httpx`)

### File Structure
```
scripts/
  generate-canva-client.sh   # Downloads spec, runs generator
src/listingjet/providers/
  canva_generated/            # Generated client (DO NOT EDIT)
    __init__.py
    api/
    models/
  canva.py                    # Updated: imports from canva_generated instead of raw httpx
```

### How It Works

1. `scripts/generate-canva-client.sh` downloads the Canva spec
2. Runs `openapi-generator-cli generate -i spec.yml -g python -o src/listingjet/providers/canva_generated/ --additional-properties=asyncio=true,library=asyncio`
3. `canva.py` (the existing `CanvaTemplateProvider`) is updated to import and use the generated client models and API classes
4. Auth (Bearer token) is configured via the generated client's configuration object

### Generation Script
```bash
#!/bin/bash
set -euo pipefail

SPEC_URL="https://www.canva.dev/sources/connect/api/latest/api.yml"
OUTPUT_DIR="src/listingjet/providers/canva_generated"

# Download spec
curl -sL "$SPEC_URL" -o /tmp/canva-spec.yml

# Generate
npx @openapitools/openapi-generator-cli generate \
  -i /tmp/canva-spec.yml \
  -g python \
  -o "$OUTPUT_DIR" \
  --additional-properties=asyncio=true,library=asyncio,packageName=canva_client

# Clean up spec
rm /tmp/canva-spec.yml
```

### Dependencies
- `@openapitools/openapi-generator-cli` (devDependency, npm — used via npx)
- Generated client uses `httpx` and `pydantic` (already in project)

## 3. Migration Plan

### Frontend (zero breaking changes)
1. Install `openapi-typescript` + `openapi-fetch`
2. Add `generate-api` script
3. Generate types
4. Refactor `api-client.ts` internals to use `openapi-fetch` — keep the same public methods
5. Update `types.ts` to re-export from `generated/api.d.ts`
6. Existing page imports continue working unchanged

### Canva (internal refactor)
1. Generate Canva client
2. Update `CanvaTemplateProvider.render()` to use generated API classes
3. Remove hand-rolled `_poll_job`, `_build_autofill_data` helpers (replaced by generated models)
4. Update tests

## 4. What's NOT Changing
- No changes to FastAPI backend (it already produces the spec)
- No changes to authentication flow
- No changes to page components (wrapper preserves interface)
- No changes to the Canva provider's public interface (`TemplateProvider.render()`)

## 5. Generated Code: Committed to Repo

Generated code IS committed to the repo so that:
- Frontend builds don't require a running backend
- CI doesn't need Java/Docker for the Canva generator
- PRs show type diffs when the API changes

The `generate-api` script is run manually when the backend API changes, and the regenerated files are committed alongside the backend change.
