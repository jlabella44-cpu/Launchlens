import { test, expect } from "@playwright/test";
import { setupAuth } from "../fixtures";

test.describe("Billing Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);

    // Mock credit transactions.
    await page.route("**/credits/transactions", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "tx-001",
            type: "purchase",
            amount: 5,
            description: "5-credit bundle purchase",
            created_at: "2026-03-20T00:00:00Z",
          },
          {
            id: "tx-002",
            type: "usage",
            amount: 1,
            description: "Listing: 123 Main St",
            created_at: "2026-03-22T00:00:00Z",
          },
        ]),
      })
    );

    // Mock credit bundles.
    await page.route("**/credits/bundles", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "1",
            credits: 3,
            price_cents: 7200,
            label: "$24/credit",
          },
          {
            id: "2",
            credits: 5,
            price_cents: 10000,
            label: "$20/credit",
          },
          {
            id: "3",
            credits: 10,
            price_cents: 17000,
            label: "$17/credit",
          },
        ]),
      })
    );

    await page.goto("/billing");
  });

  test("should display the Billing heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Billing" })
    ).toBeVisible();
  });

  test("should display the credit balance", async ({ page }) => {
    await expect(page.getByText("Credit Balance")).toBeVisible();
    await expect(page.getByText("75")).toBeVisible();
  });

  test("should display the tier label", async ({ page }) => {
    // The mock returns tier "active_agent" which displays as "Active Agent".
    await expect(page.getByText(/Active Agent/)).toBeVisible();
  });

  test("should have the Buy Credits button", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: "Buy Credits" })
    ).toBeVisible();
  });

  test("should display Transaction History section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Transaction History" })
    ).toBeVisible();
  });

  test("should show transaction entries", async ({ page }) => {
    await expect(page.getByText("5-credit bundle purchase")).toBeVisible();
    await expect(page.getByText("Listing: 123 Main St")).toBeVisible();
  });

  test("should show credit bundle cards when Buy Credits is clicked", async ({ page }) => {
    await page.getByRole("button", { name: "Buy Credits" }).click();
    await expect(
      page.getByRole("heading", { name: "Select a Credit Bundle" })
    ).toBeVisible();
    // Verify bundle options are rendered.
    await expect(page.getByText("$72.00")).toBeVisible();
    await expect(page.getByText("$100.00")).toBeVisible();
    await expect(page.getByText("$170.00")).toBeVisible();
  });
});
