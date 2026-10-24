import { expect, test } from "@playwright/test";
import { dismissOverlays, waitForCompanyTable } from "../helpers";
import { RESEARCH_TABS } from "../routes";

test.describe("Research Terminal — all tabs", () => {
  for (const tab of RESEARCH_TABS) {
    test(`tab ${tab} loads`, async ({ page }) => {
      await page.goto(`/research?tab=${tab}`);
      await dismissOverlays(page);
      await expect(page.getByTestId("research-page")).toBeVisible({ timeout: 25_000 });
      if (tab === "search") {
        await expect(page.getByTestId("research-query")).toBeVisible({ timeout: 15_000 });
      } else if (tab === "chat") {
        await expect(page.getByTestId("research-question")).toBeVisible({ timeout: 15_000 });
      } else if (tab === "watch") {
        await expect(page.getByTestId("research-watchlist")).toBeVisible({ timeout: 15_000 });
      } else {
        await expect(page.locator("h2, h3").first()).toBeVisible();
      }
    });
  }

  test("search tab has query input and search button", async ({ page }) => {
    await page.goto("/research?tab=search");
    await dismissOverlays(page);
    await expect(page.getByTestId("research-query")).toBeVisible({ timeout: 25_000 });
    await expect(page.getByRole("button", { name: "Search", exact: true })).toBeVisible();
    await expect(page.locator(".doc-list")).toBeAttached();
  });
});

test.describe("Marketing & portfolio surfaces", () => {
  test("products page shows SKU cards and desk guides", async ({ page }) => {
    await page.goto("/products");
    await dismissOverlays(page);
    await expect(page.getByTestId("products-page")).toBeVisible();
    await expect(page.getByTestId("by-desk-section")).toBeVisible();
    for (const sku of ["score", "cite", "radar", "ledger", "data"]) {
      await expect(page.getByTestId(`sku-${sku}`)).toBeVisible();
    }
    await expect(page.getByTestId("plans-section")).toBeVisible();
    await expect(page.getByTestId("features-section")).toBeVisible();
    await expect(page.getByTestId("surface-analyst")).toBeVisible();
  });

  test("old package and tier URLs land on Products and plans", async ({ page }) => {
    await page.goto("/package");
    await dismissOverlays(page);
    await expect(page).toHaveURL(/\/products#plans$/);
    for (const plan of ["pilot", "desk", "enterprise"]) {
      await expect(page.getByTestId(`plan-${plan}`)).toBeVisible();
    }
    await page.goto("/about/tiers");
    await expect(page).toHaveURL(/\/products#features$/);
    await expect(page.getByTestId("tier-feature-ask-1")).toBeVisible();
  });

  test("rankings page lists companies", async ({ page }) => {
    await page.goto("/rankings");
    await dismissOverlays(page);
    await expect(page.getByTestId("gci-rankings-page")).toBeVisible();
    await expect(page.locator("table tbody tr").first()).toBeVisible({ timeout: 20_000 });
  });

  test("pilot request page renders form", async ({ page }) => {
    await page.goto("/pilot");
    await dismissOverlays(page);
    await expect(page.getByTestId("pilot-request-page")).toBeVisible();
    await expect(page.locator("form").first()).toBeVisible();
  });

  test("blog index links to posts", async ({ page }) => {
    await page.goto("/blog");
    await dismissOverlays(page);
    await expect(page.getByTestId("blog-index")).toBeVisible();
    const firstPost = page.locator('a[href^="/blog/"]').first();
    await expect(firstPost).toBeVisible();
    await firstPost.click();
    await expect(page.getByTestId("blog-post")).toBeVisible();
  });
});

test.describe("Dossier portfolio panels", () => {
  test("company dossier loads ledger and radar sections", async ({ page }) => {
    await page.goto("/companies/infy");
    await dismissOverlays(page);
    await expect(page.getByTestId("company-name")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("evidence-table")).toBeVisible();
    await expect(page.getByTestId("ledger-panel")).toBeVisible();
    await expect(page.getByTestId("radar-diff-panel")).toBeVisible();
    await expect(page.getByTestId("trend-row")).toBeVisible();
  });
});

test.describe("Tracker universe", () => {
  test("filters and company table interactive", async ({ page }) => {
    await page.goto("/tracker");
    await dismissOverlays(page);
    await waitForCompanyTable(page);
    await expect(page.getByTestId("universe-filters")).toBeVisible();
    await expect(page.getByTestId("alerts-panel")).toBeVisible();
    await page.getByTestId("company-link-infy").click();
    await expect(page).toHaveURL(/\/companies\/infy$/);
  });
});
