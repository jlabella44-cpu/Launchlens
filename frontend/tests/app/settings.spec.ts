import { test, expect } from "@playwright/test";
import { setupAuth } from "../fixtures";

test.describe("Settings Page — unauthenticated", () => {
  test("should redirect to /login when not authenticated", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Settings Page — Brand Kit", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await page.goto("/settings");
  });

  test("should display the Brand Kit heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Brand Kit" })
    ).toBeVisible();
  });

  test("should display the brand kit description", async ({ page }) => {
    await expect(
      page.getByText("Configure your branding for flyers, watermarks, and exports.")
    ).toBeVisible();
  });

  test("should display the Brokerage Info section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Brokerage Info" })
    ).toBeVisible();
    await expect(page.getByLabel("Brokerage Name")).toBeVisible();
    await expect(page.getByLabel("Agent Name")).toBeVisible();
  });

  test("should display the Brand Colors section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Brand Colors" })
    ).toBeVisible();
    await expect(page.getByText("Primary Color")).toBeVisible();
    await expect(page.getByText("Secondary Color")).toBeVisible();
  });

  test("should display the Typography section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Typography" })
    ).toBeVisible();
    await expect(page.getByLabel("Primary Font")).toBeVisible();
  });

  test("should display the Logo upload section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Logo" })).toBeVisible();
    await expect(
      page.getByText("Drag & drop your logo here, or click to browse")
    ).toBeVisible();
  });

  test("should display the Preview section", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Preview" })
    ).toBeVisible();
  });

  test("should have the Save Brand Kit button", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: "Save Brand Kit" })
    ).toBeVisible();
  });

  test("should pre-populate fields from the mocked brand kit", async ({ page }) => {
    await expect(page.getByLabel("Brokerage Name")).toHaveValue("Test Brokerage");
    await expect(page.getByLabel("Agent Name")).toHaveValue("Test User");
  });
});
