import { test, expect } from "@playwright/test";

test.describe("Login Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
  });

  test("should load the login page with heading and form", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Welcome Back" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
  });

  test("should have a link to the register page", async ({ page }) => {
    const registerLink = page.getByRole("link", { name: "Register" });
    await expect(registerLink).toBeVisible();
    await expect(registerLink).toHaveAttribute("href", "/register");
  });

  test("should have a Google Sign-In button container", async ({ page }) => {
    // The Google Sign-In button is rendered into this div by the GSI script.
    // Without a valid GOOGLE_CLIENT_ID the script won't load in test, so we
    // verify the container element exists and is ready to receive the button.
    const googleContainer = page.locator("#google-signin-btn");
    await expect(googleContainer).toBeAttached();
  });

  test("should toggle password visibility", async ({ page }) => {
    const passwordInput = page.getByLabel("Password");
    const toggleButton = page.getByRole("button", { name: "Show password" });

    await expect(passwordInput).toHaveAttribute("type", "password");
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute("type", "text");

    const hideButton = page.getByRole("button", { name: "Hide password" });
    await hideButton.click();
    await expect(passwordInput).toHaveAttribute("type", "password");
  });

  test("should require email and password fields", async ({ page }) => {
    await expect(page.getByLabel("Email")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Password")).toHaveAttribute("required", "");
  });
});
