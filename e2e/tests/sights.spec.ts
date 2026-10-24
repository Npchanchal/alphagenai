import { expect, test } from "@playwright/test";
import { dismissOverlays } from "../helpers";
import { SIGHTS_ROUTES } from "../routes";

test.describe("Sights — India disclosure research", () => {
  test("hub shows primary nav links", async ({ page }) => {
    await page.goto("/sights");
    await dismissOverlays(page);
    await expect(page.getByTestId("sights-hub")).toBeVisible();
    for (const label of ["Themes", "Compare"]) {
      await expect(page.getByRole("link", { name: label, exact: true }).first()).toBeVisible();
    }
  });

  for (const spec of SIGHTS_ROUTES) {
    test(`${spec.path} renders panel`, async ({ page }) => {
      await page.goto(spec.path);
      await dismissOverlays(page);
      await expect(page.getByTestId("sights-shell")).toBeVisible();
      if (spec.testId) {
        await expect(page.getByTestId(spec.testId)).toBeVisible({ timeout: 15_000 });
      }
    });
  }

  test("retired Disclosure Explorer tools redirect to their merged homes", async ({ page }) => {
    const moved: Array<[string, RegExp]> = [
      ["/sights/search", /\/research\?scope=all$/],
      ["/sights/ask", /\/research\?tab=chat&scope=all$/],
      ["/sights/boards", /\/research\?tab=watch$/],
      ["/sights/agents", /\/analyst$/],
      ["/sights/export", /\/analyst$/],
    ];
    for (const [from, to] of moved) {
      await page.goto(from);
      await expect(page).toHaveURL(to);
    }
  });

  test("Filing Search spans all covered companies with synonym expansion", async ({ page }) => {
    await page.goto("/research?scope=all");
    await dismissOverlays(page);
    await expect(page.getByTestId("research-company")).toHaveValue("");
    await page.getByTestId("research-query").fill("margin guidance");
    await page.getByTestId("research-query").press("Enter");
    await expect(page.getByTestId("research-expanded")).toBeVisible({ timeout: 15_000 });
  });
});
