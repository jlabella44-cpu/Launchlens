import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiClient } from "@/lib/api-client";

// Installed by test-setup.ts before api-client is imported, because
// openapi-fetch captures globalThis.fetch at module load.
const mockFetch = vi.mocked(globalThis.fetch);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** openapi-fetch calls fetch(Request), so unpack the first argument. */
function lastRequest(): Request {
  return mockFetch.mock.calls[0][0] as Request;
}

beforeEach(() => {
  mockFetch.mockReset();
  apiClient.setToken(null);
});

describe("ApiClient", () => {
  it("sets and gets token", () => {
    expect(apiClient.getToken()).toBeNull();
    apiClient.setToken("test-token");
    expect(apiClient.getToken()).toBe("test-token");
  });

  it("sends auth header when token is set", async () => {
    apiClient.setToken("my-jwt");
    mockFetch.mockResolvedValue(jsonResponse([]));

    await apiClient.getListings();

    const req = lastRequest();
    expect(req.url).toContain("/listings");
    expect(req.headers.get("Authorization")).toBe("Bearer my-jwt");
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Invalid token" }, 401));

    await expect(apiClient.login("bad@test.com", "wrong")).rejects.toThrow(
      "Invalid token"
    );
  });

  it("calls login endpoint correctly", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ access_token: "tok123", token_type: "bearer" })
    );

    const result = await apiClient.login("test@test.com", "password");

    expect(result.access_token).toBe("tok123");
    const req = lastRequest();
    expect(req.url).toContain("/auth/login");
    expect(req.method).toBe("POST");
  });

  it("calls createListing with correct body", async () => {
    apiClient.setToken("tok");
    mockFetch.mockResolvedValue(jsonResponse({ id: "listing-1", state: "new" }));

    await apiClient.createListing({
      address: { street: "123 Main", city: "Austin", state: "TX" },
      metadata: { beds: 3, baths: 2 },
    });

    const body = await lastRequest().json();
    expect(body.address.street).toBe("123 Main");
    expect(body.metadata.beds).toBe(3);
  });
});
