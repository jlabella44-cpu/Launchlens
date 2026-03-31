import { test, expect } from "@playwright/test";

test.describe("Demo Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/demo");
  });

  test("should display the demo page heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "See AI Results in Minutes" })
    ).toBeVisible();
  });

  test("should display the description text", async ({ page }) => {
    await expect(
      page.getByText("Paste your listing photo S3 paths below")
    ).toBeVisible();
  });

  test("should have a textarea for photo paths", async ({ page }) => {
    const textarea = page.getByRole("textbox");
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute(
      "placeholder",
      /listings\/demo\/exterior\.jpg/
    );
  });

  test("should have the Process Photos submit button", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: "Process Photos" })
    ).toBeVisible();
  });

  test("should not require authentication to access", async ({ page }) => {
    // Verify no redirect happened — we should still be on /demo.
    await expect(page).toHaveURL(/\/demo$/);
    await expect(
      page.getByRole("heading", { name: "See AI Results in Minutes" })
    ).toBeVisible();
  });
});
