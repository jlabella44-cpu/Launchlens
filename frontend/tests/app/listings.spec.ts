import { test, expect } from "@playwright/test";
import { setupAuth } from "../fixtures";

test.describe("Listings Page — unauthenticated", () => {
  test("should redirect to /login when not authenticated", async ({ page }) => {
    await page.goto("/listings");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Listings Page — authenticated", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);

    // Mock the listings endpoint with an empty list.
    await page.route("**/listings", (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      }
      return route.continue();
    });

    await page.goto("/listings");
  });

  test("should display the Listings heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Listings" })
    ).toBeVisible();
  });

  test("should display the page description", async ({ page }) => {
    await expect(
      page.getByText("Manage your property listings")
    ).toBeVisible();
  });

  test("should show the New Listing button", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: "New Listing" })
    ).toBeVisible();
  });

  test("should show empty state when no listings exist", async ({ page }) => {
    await expect(
      page.getByText("No listings yet. Create your first one to get started.")
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Create First Listing" })
    ).toBeVisible();
  });
});

test.describe("Listings Page — with data", () => {
  test("should display listing cards when listings exist", async ({ page }) => {
    await setupAuth(page);

    await page.route("**/listings", (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "listing-001",
              address: {
                street: "123 Main St",
                city: "Austin",
                state: "TX",
              },
              metadata: { beds: 3, baths: 2, sqft: 1800, price: 450000 },
              status: "ready",
              created_at: "2026-03-01T00:00:00Z",
            },
            {
              id: "listing-002",
              address: {
                street: "456 Oak Ave",
                city: "Dallas",
                state: "TX",
              },
              metadata: { beds: 4, baths: 3, sqft: 2400, price: 650000 },
              status: "processing",
              created_at: "2026-03-15T00:00:00Z",
            },
          ]),
        });
      }
      return route.continue();
    });

    await page.goto("/listings");

    await expect(page.getByText("123 Main St")).toBeVisible();
    await expect(page.getByText("456 Oak Ave")).toBeVisible();
  });
});
