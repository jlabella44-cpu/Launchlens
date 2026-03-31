import { test, expect } from "@playwright/test";
import { setupAuth } from "../fixtures";

test.describe("Create Listing Dialog", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);

    // Mock the listings endpoint.
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

    // Mock the credit bundles endpoint used by PlanContext.
    await page.route("**/credits/bundles", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    );

    await page.goto("/listings");
  });

  test("should open the dialog when New Listing is clicked", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(
      page.getByRole("heading", { name: "New Listing" })
    ).toBeVisible();
  });

  test("should display the Street Address field", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByLabel("Street Address")).toBeVisible();
  });

  test("should display City and State fields", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByLabel("City")).toBeVisible();
    await expect(page.getByLabel("State")).toBeVisible();
  });

  test("should display property metadata fields", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByLabel("Beds")).toBeVisible();
    await expect(page.getByLabel("Baths")).toBeVisible();
    await expect(page.getByLabel("Sqft")).toBeVisible();
    await expect(page.getByLabel("Price")).toBeVisible();
  });

  test("should have required attribute on all form fields", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByLabel("Street Address")).toHaveAttribute("required", "");
    await expect(page.getByLabel("City")).toHaveAttribute("required", "");
    await expect(page.getByLabel("State")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Beds")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Baths")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Sqft")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Price")).toHaveAttribute("required", "");
  });

  test("should display Cancel and Create buttons", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
    // The create button text varies depending on credit model, so match partial.
    await expect(
      page.getByRole("button", { name: /Create/ }).last()
    ).toBeVisible();
  });

  test("should close the dialog when Cancel is clicked", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByLabel("Street Address")).toBeVisible();

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByLabel("Street Address")).not.toBeVisible();
  });

  test("should display add-on checkboxes for credit billing model", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByText("AI Video Tour")).toBeVisible();
    await expect(page.getByText("3D Floorplan")).toBeVisible();
    await expect(page.getByText("Social Media Pack")).toBeVisible();
  });

  test("should show credit cost preview", async ({ page }) => {
    await page.getByRole("button", { name: "New Listing" }).click();
    await expect(page.getByText(/credit/i)).toBeVisible();
    await expect(page.getByText("Balance:")).toBeVisible();
  });
});
