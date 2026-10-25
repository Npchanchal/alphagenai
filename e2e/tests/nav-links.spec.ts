import { expect, test } from "@playwright/test";
import { dismissOverlays, ensurePrimaryNav } from "../helpers";

const NAV_TARGETS: { label: RegExp; url: RegExp; menu?: RegExp }[] = [
  { label: /^GCI Screener$/i, url: /\/tracker$/ },
  { label: /^Filing Search$/i, url: /\/research/, menu: /^Research$/i },
  { label: /^Analyst Workbench$/i, url: /\/desk/, menu: /^Workspace$/i },
  { label: /^Overview$/i, url: /\/sights$/, menu: /^Workspace$/i },
  { label: /^Pricing$/i, url: /\/products/ },
];

const FOOTER_TARGETS: { label: RegExp; url: RegExp }[] = [
  { label: /Terms/i, url: /\/terms$/ },
  { label: /Privacy/i, url: /\/privacy$/ },
  { label: /Trust/i, url: /\/trust$/ },
  { label: /Help/i, url: /\/help$/ },
];

test.describe("Navigation & footer links", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/tracker");
    await dismissOverlays(page);
    await ensurePrimaryNav(page);
  });

  for (const target of NAV_TARGETS) {
    test(`primary nav → ${target.menu ?? target.label}`, async ({ page }) => {
      if (target.menu) {
        await page.getByRole("button", { name: target.menu }).first().click();
        await page.getByRole("menuitem", { name: target.label }).first().click();
      } else {
        await page.getByRole("link", { name: target.label }).first().click();
      }
      await expect(page).toHaveURL(target.url);
    });
  }

  test("footer legal and help links", async ({ page }) => {
    for (const target of FOOTER_TARGETS) {
      await page.goto("/tracker");
      await dismissOverlays(page);
      await page.getByRole("contentinfo").getByRole("link", { name: target.label }).click();
      await expect(page).toHaveURL(target.url);
    }
  });

  test("products hash anchor scrolls to desk-buy-side", async ({ page }) => {
    await page.goto("/products#desk-buy-side");
    await dismissOverlays(page);
    await expect(page.getByTestId("desk-guide-buy-side")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Account & billing navigation", () => {
  test("session menu reaches account; billing page loads", async ({ page }) => {
    await page.goto("/tracker");
    await dismissOverlays(page);
    await ensurePrimaryNav(page);
    await page.getByTestId("session-menu").click();
    await expect(page.locator(".session-dropdown")).toBeVisible();
    await page.getByRole("menuitem", { name: /Account/i }).click();
    await expect(page).toHaveURL(/\/account$/);
    await expect(page.getByTestId("account-settings-page")).toBeVisible();

    await page.goto("/billing");
    await dismissOverlays(page);
    await expect(page.getByTestId("billing-page")).toBeVisible();
  });

  test("org settings reachable for pilot owner", async ({ page }) => {
    await page.goto("/org/settings");
    await dismissOverlays(page);
    await expect(page.getByTestId("org-settings-page")).toBeVisible({ timeout: 15_000 });
  });
});
