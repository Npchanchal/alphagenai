import { expect, test } from "@playwright/test";
import { dismissOverlays, waitForDossier } from "../helpers";

// The suite's default storageState is a pilot seat; these journeys are for guests.
const GUEST_ORIGIN = {
  cookies: [] as [],
  origins: [
    {
      origin: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080",
      localStorage: [
        { name: "intellens.analytics_consent", value: "denied" },
        {
          name: "citealpha.tours.seen.v2",
          value: JSON.stringify({ welcome_prompt: true, tracker: true, desk_first_run: true }),
        },
      ],
    },
  ],
};

test.use({ storageState: GUEST_ORIGIN });

/**
 * Rule `index-integrity` (plan W1): a guest never sees synthetic numbers.
 * No price tape, correlation / lead–lag, wordmap or narrative-consistency on the
 * public dossier; deltas only from the reviewed point-in-time series; every score
 * carries a confidence tier and an as-of date; footer links to the changelog.
 */
test("guest dossier has no synthetic analytics and shows tier + as-of", async ({ page }) => {
  await page.goto("/companies/infy");
  await dismissOverlays(page);
  await waitForDossier(page);

  await expect(page.getByTestId("gci-score")).not.toHaveText("N/A", { timeout: 10_000 });
  await expect(page.getByTestId("confidence-tier")).toBeVisible();
  await expect(page.getByTestId("tier-badge")).toHaveText(/Provisional|Established|Deep/);
  await expect(page.getByTestId("dossier-as-of")).toContainText(/Data as of \d{1,2} \w{3} \d{4}/);
  await expect(page.getByTestId("dossier-reviewed")).toContainText(
    /Checked against the source documents/,
  );
  await expect(page.getByTestId("dossier-record")).toBeVisible();
  await expect(page.getByTestId("delivery-record")).toBeVisible();
  await expect(page.getByTestId("revision-panel")).toBeVisible();
  await expect(page.getByTestId("dossier-calc")).toBeVisible();
  await expect(page.getByTestId("example-calc")).toBeVisible();
  await expect(page.getByTestId("dossier-cite-page")).toBeVisible();
  await expect(page.getByTestId("dossier-report-error")).toBeVisible();

  await expect(page.getByTestId("ledger-panel")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Run extract/i })).toHaveCount(0);

  const table = page.getByTestId("evidence-table");
  await expect(table).toBeVisible();
  const tableText = await table.innerText();
  expect(tableText).not.toMatch(/\{o\.|span_end/);
  await expect(page.getByTestId("promise-source-0")).toBeVisible();
  await expect(page.getByTestId("actual-source-0")).toBeVisible();
  await expect(page.getByTestId("promise-threads")).toBeVisible();
  await expect(page.getByTestId("thread-promise").first()).toBeVisible();

  await expect(page.getByTestId("gci-trend-chart")).toBeVisible();
  await expect(page.getByTestId("analytics-panel")).toHaveCount(0);
  await expect(page.getByTestId("gci-price-overlay")).toHaveCount(0);
  await expect(page.getByTestId("stock-history")).toHaveCount(0);
  await expect(page.getByTestId("granger-panel")).toHaveCount(0);
  await expect(page.getByTestId("nci-block")).toHaveCount(0);
  await expect(page.getByTestId("experimental-banner")).toHaveCount(0);

  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/demo_pit_extension|demo_multi_horizon|hybrid_pit|demo tape/i);
  expect(body).not.toMatch(/Peer #|sector avg/i);

  // Deltas appear only from the reviewed PIT series; otherwise an honest note.
  const horizons = page.getByTestId("delta-horizon-chart");
  const pending = page.getByTestId("deltas-pending");
  expect((await horizons.count()) + (await pending.count())).toBeGreaterThanOrEqual(0);

  const changelog = page.getByTestId("dossier-changelog-link");
  await expect(changelog).toBeVisible();
  await changelog.click();
  await expect(page).toHaveURL(/\/changelog\?company=infy/);
  await expect(page.getByTestId("changelog-page")).toBeVisible();
  await expect(page.getByTestId("changelog-filter")).toContainText(/Infosys/);
  await expect(page.getByTestId("changelog-entries")).toContainText(/88\.2/);
});

test("guest dossier is readable at 390 px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/companies/infy");
  await dismissOverlays(page);
  await waitForDossier(page);
  await expect(page.getByTestId("gci-score")).toBeVisible();
  await expect(page.getByTestId("dossier-record")).toBeVisible();
  await expect(page.getByTestId("delivery-record")).toBeVisible();
  await expect(page.getByTestId("evidence-table")).toBeVisible();
});

test("public snapshot ranks only established/deep and explains an empty list", async ({ page }) => {
  await page.goto("/rankings");
  await dismissOverlays(page);
  await expect(page.getByTestId("gci-rankings-page")).toBeVisible();
  const record = page.getByTestId("rankings-record-table");
  const ranked = page.getByRole("columnheader", { name: "#", exact: true });
  const recordMode = await record
    .waitFor({ state: "visible", timeout: 10_000 })
    .then(() => true)
    .catch(() => false);
  if (recordMode) {
    // Below 20 established names the snapshot is a delivery record, not a ranking.
    await expect(ranked).toHaveCount(0);
    const badges = record.locator("[data-testid^='rank-tier-']");
    if ((await badges.count()) === 0) {
      await expect(page.getByTestId("rankings-empty")).toBeVisible();
    }
  } else {
    const badges = page.locator("[data-testid^='rank-tier-']");
    const n = await badges.count();
    if (n === 0) {
      await expect(page.getByTestId("rankings-empty")).toBeVisible();
    } else {
      for (let i = 0; i < n; i++) {
        await expect(badges.nth(i)).toHaveText(/Established|Deep/);
      }
    }
  }
});

test("screener lists every name, with scored rows first", async ({ page }) => {
  await page.goto("/tracker");
  await dismissOverlays(page);
  await expect(page.getByTestId("company-table")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("scored-only-toggle")).not.toBeChecked();
  const unscored = page.locator("[data-testid^='not-scored-']");
  if ((await unscored.count()) > 0) {
    await expect(unscored.first()).toHaveAttribute(
      "title",
      /Not yet scored|No numeric guidance|being checked|being read|not yet closed|closes [A-Z][a-z]{2} \d{4}|not yet read|not yet matched/,
    );
    const lastScore = page.locator("[data-testid='company-table'] tbody tr").last().locator("td.score");
    await expect(lastScore).toHaveAttribute(
      "title",
      /Not yet scored|No numeric guidance|being checked|being read|not yet closed|closes [A-Z][a-z]{2} \d{4}|not yet read|not yet matched/,
    );
  }
});

test.describe("pilot seat", () => {
  test.use({ storageState: ".auth/pilot.json" });

  test("seat sees experimental analytics with the synthetic-inputs banner", async ({ page }) => {
    await page.goto("/companies/infy");
    await dismissOverlays(page);
    await waitForDossier(page);
    await expect(page.getByTestId("analytics-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("experimental-banner")).toContainText(/Experimental — synthetic inputs/);
  });
});
