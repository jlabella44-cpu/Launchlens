import { vi } from "vitest";
import "@testing-library/jest-dom/vitest";

// openapi-fetch builds a Request object before delegating to fetch, so the
// client's base URL has to be absolute under Node. Production keeps its
// relative "/api" default.
process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";

// openapi-fetch captures globalThis.fetch when the api-client module is first
// imported, which happens before any test body runs. Install the double here so
// tests can drive it via vi.mocked(globalThis.fetch).
globalThis.fetch = vi.fn() as unknown as typeof fetch;
