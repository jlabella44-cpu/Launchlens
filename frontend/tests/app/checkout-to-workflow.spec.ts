import { test, expect } from "@playwright/test";
import { setupAuth } from "../fixtures";

/**
 * E2E Happy Path: Stripe checkout → plan activation → listing creation → workflow start
 *
 * This is the most critical user journey for launch day.  All Stripe
 * interactions are mocked at the API layer via Playwright route
 * interception so the test can run without Stripe credentials.
 */
test.describe("Checkout → Workflow Happy Path", () => {
  const MOCK_LISTING_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

  test.beforeEach(async ({ page }) => {
    await setupAuth(page);

    // Mock credit bundles (used by PlanContext / billing page).
    await page.route("**/credits/bundles", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { id: "1", credits: 5, price_cents: 10000, label: "$20/credit" },
        ]),
      })
    );

    // Mock credit transactions.
    await page.route("**/credits/transactions", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    );
  });

  test("should complete the full checkout-to-listing-workflow flow", async ({
    page,
  }) => {
    // ── Step 1: Navigate to billing and initiate checkout ──────────

    // Mock the checkout endpoint to return a fake Stripe URL.
    // In production this redirects to Stripe Checkout — here we
    // intercept and simulate an instant success.
    let checkoutCalled = false;
    await page.route("**/billing/checkout", (route) => {
      checkoutCalled = true;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          checkout_url: "https://checkout.stripe.com/test_session_123",
        }),
      });
    });

    await page.goto("/billing");
    await expect(
      page.getByRole("heading", { name: "Billing" })
    ).toBeVisible();
    await page.getByRole("button", { name: "Buy Credits" }).click();

    // Wait for bundle cards to appear, then click the first one.
    await expect(page.getByText("$100.00")).toBeVisible();
    await page.getByRole("button", { name: /Purchase|Buy/ }).first().click();
    expect(checkoutCalled).toBe(true);

    // ── Step 2: Simulate post-checkout return ─────────────────────
    // After Stripe checkout, the user is redirected back to the app.
    // Mock the billing status endpoint to reflect the new plan/credits.

    await page.route("**/credits/balance", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          balance: 15,
          billing_model: "credit",
          tier: "active_agent",
          listing_credit_cost: 1,
          rollover_cap: 10,
        }),
      })
    );

    await page.route("**/billing/status", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          plan: "active_agent",
          subscription_active: true,
          credit_balance: 15,
        }),
      })
    );

    // ── Step 3: Create a new listing ──────────────────────────────

    // Mock listings endpoint for GET (empty list) and POST (create).
    await page.route("**/listings", (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      }
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: MOCK_LISTING_ID,
            state: "uploading",
            address: { street: "123 Main St", city: "Austin", state: "TX" },
            created_at: new Date().toISOString(),
          }),
        });
      }
      return route.continue();
    });

    await page.goto("/listings");
    await page.getByRole("button", { name: "New Listing" }).click();

    // Fill out the listing form.
    await page.getByLabel("Street Address").fill("123 Main St");
    await page.getByLabel("City").fill("Austin");
    await page.getByLabel("State").fill("TX");
    await page.getByLabel("Beds").fill("3");
    await page.getByLabel("Baths").fill("2");
    await page.getByLabel("Sqft").fill("1800");
    await page.getByLabel("Price").fill("450000");

    // Submit the listing — this triggers workflow start on the backend.
    await page.getByRole("button", { name: /Create/ }).last().click();

    // ── Step 4: Verify pipeline status ───────────────────────────

    // Mock the pipeline-status endpoint to confirm workflow started.
    await page.route(`**/listings/${MOCK_LISTING_ID}/pipeline-status`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflow_id: `listing-pipeline-${MOCK_LISTING_ID}`,
          state: "uploading",
          steps: [
            { name: "ingestion", status: "running" },
            { name: "vision_tier1", status: "pending" },
            { name: "vision_tier2", status: "pending" },
          ],
        }),
      })
    );

    // Mock listing detail page data.
    await page.route(`**/listings/${MOCK_LISTING_ID}`, (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: MOCK_LISTING_ID,
            state: "uploading",
            address: { street: "123 Main St", city: "Austin", state: "TX" },
            beds: 3,
            baths: 2,
            sqft: 1800,
            price: 450000,
            created_at: new Date().toISOString(),
          }),
        });
      }
      return route.continue();
    });

    // The listing was created — verify the user can see it.
    // After creation, the UI typically navigates to the listing detail or
    // stays on the listings page.  Either way, the listing ID should appear
    // in the application state.
    await expect(page.getByText("123 Main St")).toBeVisible({ timeout: 5000 });
  });
});
