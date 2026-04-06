import { test as base, expect } from "@playwright/test";

/**
 * Fake user returned by the mocked /auth/me endpoint.
 */
const FAKE_USER = {
  id: "test-user-001",
  email: "test@listingjet.com",
  name: "Test User",
  company_name: "Test Brokerage",
  plan_tier: "active_agent",
  onboarding_complete: true,
  created_at: "2026-01-01T00:00:00Z",
};

/**
 * Extends the base Playwright test with an authenticated page fixture.
 *
 * - Sets the `listingjet_token` in localStorage before every navigation.
 * - Intercepts GET /auth/me to return a fake user so ProtectedRoute passes.
 * - Intercepts common API calls with safe default responses.
 */
export const test = base.extend<{ authedPage: typeof base extends { extend: (f: infer T) => unknown } ? never : never }>({
  /**
   * Use `authedPage` in any test that needs a logged-in session.
   * It is just `page` with auth pre-configured.
   */
  page: async ({ page }, use) => {
    // No-op — the default page fixture is unmodified.
    // Protected-page tests should use the `authedPage` helper below.
    await use(page);
  },
});

/**
 * Helper: set up auth state and API mocks on a page before navigating.
 *
 * Usage in a test:
 *   await setupAuth(page);
 *   await page.goto("/listings");
 */
export async function setupAuth(page: import("@playwright/test").Page) {
  // Set the JWT token in localStorage before any navigation triggers the auth check.
  await page.addInitScript(() => {
    window.localStorage.setItem("listingjet_token", "fake-jwt-token-for-testing");
  });

  // Mock the /auth/me endpoint so the AuthProvider resolves with a user.
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user-001",
        email: "test@listingjet.com",
        name: "Test User",
        company_name: "Test Brokerage",
        plan_tier: "active_agent",
        onboarding_complete: true,
        created_at: "2026-01-01T00:00:00Z",
      }),
    })
  );

  // Mock the brand kit endpoint (used by listings page).
  await page.route("**/brand-kit", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          brokerage_name: "Test Brokerage",
          agent_name: "Test User",
          primary_color: "#0F1B2D",
          secondary_color: "#FF6B2C",
          font_primary: "Montserrat",
          logo_url: null,
        }),
      });
    }
    return route.continue();
  });

  // Mock the plan/credits endpoint used by PlanContext.
  await page.route("**/credits/balance", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        balance: 75,
        granted_balance: 50,
        purchased_balance: 25,
        billing_model: "credit",
        tier: "active_agent",
        listing_credit_cost: 12,
        rollover_cap: 50,
      }),
    })
  );
}

export { expect };
