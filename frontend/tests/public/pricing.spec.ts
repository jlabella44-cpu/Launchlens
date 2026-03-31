import { test, expect } from "@playwright/test";

test.describe("Pricing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/pricing");
  });

  test("should display the pricing page heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Pay for what you use" })
    ).toBeVisible();
  });

  test("should display all three plan tier cards", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Free" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Lite" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Active Agent" })).toBeVisible();
  });

  test("should show the Most Popular badge on Active Agent tier", async ({ page }) => {
    await expect(page.getByText("Most Popular")).toBeVisible();
  });

  test("should display tier prices", async ({ page }) => {
    await expect(page.getByText("$0")).toBeVisible();
    await expect(page.getByText("$9")).toBeVisible();
    await expect(page.getByText("$29")).toBeVisible();
  });

  test("should have Get Started buttons linking to register", async ({ page }) => {
    const getStartedButtons = page.getByRole("link", { name: "Get Started" });
    await expect(getStartedButtons).toHaveCount(3);
  });

  test("should display the cost calculator slider", async ({ page }) => {
    await expect(page.getByText("I list about")).toBeVisible();
    await expect(page.getByText("properties/month")).toBeVisible();
    await expect(page.getByRole("slider")).toBeVisible();
  });

  test("should display Credit Bundles section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Credit Bundles" })
    ).toBeVisible();
  });

  test("should display Premium Add-Ons section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Premium Add-Ons" })
    ).toBeVisible();
    await expect(page.getByText("AI Video Tour")).toBeVisible();
    await expect(page.getByText("3D Floorplan")).toBeVisible();
    await expect(page.getByText("Social Content Pack")).toBeVisible();
  });

  test("should display the Annual Credit Bank option", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Annual Credit Bank" })
    ).toBeVisible();
    await expect(page.getByText("$349")).toBeVisible();
  });
});
