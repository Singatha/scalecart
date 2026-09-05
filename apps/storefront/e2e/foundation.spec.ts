import { expect, test } from "@playwright/test"

test("serves the storefront through the gateway", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: /useful things/i })).toBeVisible()
  await expect(page.getByRole("status")).toContainText("database are ready")
})

