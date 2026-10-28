import { expect, test } from "@playwright/test";
import { dismissOverlays } from "../helpers";

test.describe("Terminal pass", () => {
  test("palette finds a company and opens its dossier", async ({ page }) => {
    await page.goto("/tracker");
    await dismissOverlays(page);
    await page.getByTestId("palette-hint").click();
    const input = page.getByTestId("command-palette-input");
    await expect(input).toBeFocused();
    await input.fill("infosys");
    await expect(page.getByTestId("palette-company-infy")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("palette-company-infy").click();
    await expect(page).toHaveURL(/\/companies\/infy/);
  });

  test("palette closes on Escape", async ({ page }) => {
    await page.goto("/tracker");
    await dismissOverlays(page);
    await page.getByTestId("palette-hint").click();
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
  });

  test("marketing route keeps the full header", async ({ page }) => {
    await page.goto("/methodology");
    await dismissOverlays(page);
    await expect(page.locator("header.topbar")).toHaveAttribute("data-frame", "full");
    await expect(page.getByTestId("palette-hint")).toHaveCount(0);
  });

  test("screener filter survives a dossier round trip", async ({ page }) => {
    await page.goto("/tracker?scored=0");
    await dismissOverlays(page);
    await expect(page).toHaveURL(/scored=0/);
    await page.goto("/companies/infy");
    await page.goBack();
    await expect(page).toHaveURL(/scored=0/);
  });
});
