import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiClient } from "@/lib/api-client";

const mockFetch = vi.fn();
global.fetch = mockFetch;

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
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await apiClient.getListings();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/listings"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer my-jwt",
        }),
      })
    );
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid token" }),
    });

    await expect(apiClient.login("bad@test.com", "wrong")).rejects.toThrow(
      "Invalid token"
    );
  });

  it("calls login endpoint correctly", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({ access_token: "tok123", token_type: "bearer" }),
    });

    const result = await apiClient.login("test@test.com", "password");

    expect(result.access_token).toBe("tok123");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("calls createListing with correct body", async () => {
    apiClient.setToken("tok");
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "listing-1", state: "new" }),
    });

    await apiClient.createListing({
      address: { street: "123 Main", city: "Austin", state: "TX" },
      metadata: { beds: 3, baths: 2 },
    });

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.address.street).toBe("123 Main");
    expect(body.metadata.beds).toBe(3);
  });
});
