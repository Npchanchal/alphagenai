import { expect, test } from "@playwright/test";
import { dismissOverlays, showEvidenceRows, waitForCompanyTable, waitForDossier } from "../helpers";

test("US-001/002/003: list companies, open detail, see evidence", async ({ page }) => {
  await page.goto("/tracker");
  await dismissOverlays(page);
  await expect(page.getByRole("heading", { level: 1, name: "GCI Screener" })).toBeVisible();
  await waitForCompanyTable(page);
  await expect(page.getByTestId("alerts-panel")).toBeVisible();

  await page.getByTestId("company-link-infy").click();
  await waitForDossier(page);
  await expect(page.getByTestId("company-name")).toContainText("Infosys");
  await expect(page.getByTestId("gci-score")).not.toHaveText("N/A");
  await showEvidenceRows(page);
  await expect(page.getByTestId("trend-row")).toBeVisible();
  await expect(page.getByTestId("evidence-table").locator("tbody tr").first()).toBeVisible();
});

test("labels and sources visible on detail", async ({ page }) => {
  await page.goto("/companies/infy");
  await dismissOverlays(page);
  await waitForDossier(page);
  await expect(page.getByTestId("gci-score")).not.toHaveText("N/A", { timeout: 10_000 });
  await showEvidenceRows(page);
  const table = page.getByTestId("evidence-table");
  await expect(table.locator(".pill").first()).toBeVisible();
  await expect(table).toContainText(/exceeded|met|missed|pending|dropped/i);
  const text = await table.innerText();
  expect(
    /concall|guidance-vs-actuals|INFY|Infosys|exceeded|met/i.test(text),
  ).toBeTruthy();
});
