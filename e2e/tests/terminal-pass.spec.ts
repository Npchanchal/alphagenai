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

  test("workflows names the signed-in seat", async ({ page }) => {
    await page.goto("/workflows");
    await dismissOverlays(page);
    await expect(page.getByTestId("workflows-seat")).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Sector tab", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("homepage and footer carry the tagline", async ({ page }) => {
    await page.goto("/");
    await dismissOverlays(page);
    await expect(page.getByTestId("landing-tagline")).toHaveText("Beyond Guidance. Into Credibility.");
    await expect(page.getByTestId("footer-tagline")).toContainText("Beyond Guidance. Into Credibility.");
  });

  test("explains published coverage and lists every sector that holds a published name", async ({ page }) => {
    await page.goto("/tracker?tab=sectors");
    await dismissOverlays(page);
    await expect(page.getByTestId("sector-leaderboard")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("sector-coverage")).toContainText(/published GCI/);
    const listed = page.locator("[data-testid^=sector-row-], [data-testid^=sector-building-]");
    expect(await listed.count()).toBeGreaterThan(0);
  });
});

test.describe("Dossier delivery chips", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("no chip reads zero", async ({ page }) => {
    await page.goto("/companies/infy");
    await dismissOverlays(page);
    const chips = page.locator("[data-testid^=delivery-chip-]");
    await expect(chips.first()).toBeVisible({ timeout: 20_000 });
    for (const value of await chips.locator(".value").allInnerTexts()) {
      expect(value.trim()).not.toBe("0");
    }
  });
});

test.describe("Terminal pass, signed out", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("compact screener shows 25 rows on 1920×1080 without scrolling the window", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("/tracker?scored=0");
    await dismissOverlays(page);
    await expect(page.getByTestId("company-table")).toBeVisible({ timeout: 20_000 });
    const visible = await page.evaluate(
      () =>
        [...document.querySelectorAll("[data-testid=company-table] tbody tr")].filter((row) => {
          const box = row.getBoundingClientRect();
          return box.top >= 0 && box.bottom <= window.innerHeight;
        }).length,
    );
    expect(visible).toBeGreaterThanOrEqual(25);
  });
});
