import { test, expect } from "@playwright/test";

test.describe("Register Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/register");
  });

  test("should display the registration form with all fields", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();
    await expect(page.getByLabel("Full Name")).toBeVisible();
    await expect(page.getByLabel("Company / Brokerage")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Account" })).toBeVisible();
  });

  test("should require all form fields", async ({ page }) => {
    await expect(page.getByLabel("Full Name")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Company / Brokerage")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Email")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Password")).toHaveAttribute("required", "");
  });

  test("should enforce minimum password length of 8 characters", async ({ page }) => {
    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toHaveAttribute("minlength", "8");
  });

  test("should have a link to the login page", async ({ page }) => {
    const loginLink = page.getByRole("link", { name: "Sign In" });
    await expect(loginLink).toBeVisible();
    await expect(loginLink).toHaveAttribute("href", "/login");
  });

  test("should show plan info when plan query param is provided", async ({ page }) => {
    await page.goto("/register?plan=active_agent");
    await expect(page.getByText("Signing up for Active Agent")).toBeVisible();
  });

  test("should show Lite plan info with upgrade prompt", async ({ page }) => {
    await page.goto("/register?plan=lite");
    await expect(page.getByText("Signing up for Lite")).toBeVisible();
    await expect(page.getByRole("link", { name: "Start with Active Agent instead" })).toBeVisible();
  });

  test("should show Team plan info", async ({ page }) => {
    await page.goto("/register?plan=team");
    await expect(page.getByText("Signing up for Team")).toBeVisible();
  });

  test("should show pricing link when no plan is selected", async ({ page }) => {
    await expect(page.getByRole("link", { name: "View pricing plans" })).toBeVisible();
  });

  test("should have email input with correct type", async ({ page }) => {
    await expect(page.getByLabel("Email")).toHaveAttribute("type", "email");
  });

  test("should have password input with password type", async ({ page }) => {
    await expect(page.getByLabel("Password")).toHaveAttribute("type", "password");
  });
});
