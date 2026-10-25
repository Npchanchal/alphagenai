/**
 * Capture Tier 1–3 feature screenshots from a live CiteAlpha URL.
 * Writes to docs/screenshots/tiers and frontend/public/screenshots/tiers (served by /about/tiers).
 *
 * Usage (from repo root or e2e — needs Playwright deps from e2e/):
 *   cd e2e && NODE_PATH=./node_modules BASE_URL=https://citealpha.com \
 *     node ../scripts/capture-tier-screenshots.mjs
 * Desk (Analyst Workbench) panels require a Pilot/Desk session: set AUTH_TOKEN to a bearer token.
 */
import { createRequire } from "module";
import { copyFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const requireFromE2e = createRequire(join(__dirname, "../e2e/package.json"));
const { chromium } = requireFromE2e("@playwright/test");

const OUT = join(__dirname, "../docs/screenshots/tiers");
const PUBLIC_OUT = join(__dirname, "../frontend/public/screenshots/tiers");
const BASE = process.env.BASE_URL || process.env.E2E_BASE_URL || "http://127.0.0.1:8080";

mkdirSync(OUT, { recursive: true });
mkdirSync(PUBLIC_OUT, { recursive: true });

async function shot(page, name, locator, pad = 8) {
  const saved = await capture(page, name, locator, pad);
  if (saved) copyFileSync(join(OUT, `${name}.png`), join(PUBLIC_OUT, `${name}.png`));
}

async function capture(page, name, locator, pad) {
  const path = join(OUT, `${name}.png`);
  if (locator) {
    const el = typeof locator === "string" ? page.locator(locator).first() : locator;
    const found = await el
      .waitFor({ state: "visible", timeout: 8000 })
      .then(() => true)
      .catch(() => false);
    if (!found) {
      console.log("skip", name, "—", locator, "not on the page");
      return false;
    }
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(350);
    const box = await el.evaluate((node) => {
      const r = node.getBoundingClientRect();
      return { x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height };
    });
    if (box && box.width > 0 && box.height > 0) {
      await el.evaluate((target) => {
        for (const n of document.querySelectorAll("body *")) {
          if (target.contains(n) || n.contains(target)) continue;
          const pos = getComputedStyle(n).position;
          if (pos === "sticky" || pos === "fixed") n.setAttribute("data-shot-hidden", n.style.visibility || "-");
        }
        for (const n of document.querySelectorAll("[data-shot-hidden]")) n.style.visibility = "hidden";
      });
      await page.screenshot({
        path,
        fullPage: true,
        clip: {
          x: Math.max(0, box.x - pad),
          y: Math.max(0, box.y - pad),
          width: Math.min(1400, box.width + pad * 2),
          height: Math.min(900, Math.max(box.height + pad * 2, 200)),
        },
      });
      await page.evaluate(() => {
        for (const n of document.querySelectorAll("[data-shot-hidden]")) {
          const prev = n.getAttribute("data-shot-hidden");
          n.style.visibility = prev === "-" ? "" : prev;
          n.removeAttribute("data-shot-hidden");
        }
      });
      console.log("saved", name);
      return true;
    }
    console.log("skip", name, "— empty box");
    return false;
  }
  await page.screenshot({ path });
  console.log("saved", name, "(full viewport)");
  return true;
}

async function dismissTours(page) {
  const consent = page.locator('[data-testid="consent-banner"] button', { hasText: "Decline" }).first();
  const bannerShown = await consent
    .waitFor({ state: "visible", timeout: 5000 })
    .then(() => true)
    .catch(() => false);
  if (bannerShown) {
    await consent.click().catch(() => {});
    await page.waitForTimeout(300);
  }
  if (await page.locator('[data-testid="tour-welcome-dismiss"]').count()) {
    await page.locator('[data-testid="tour-welcome-dismiss"]').click();
  }
  if (await page.locator('[data-testid="tour-skip"]').count()) {
    await page.locator('[data-testid="tour-skip"]').click();
  }
}

async function main() {
  console.log("BASE_URL=", BASE);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  if (process.env.AUTH_TOKEN) {
    await page.addInitScript((tkn) => {
      localStorage.setItem("intellens.auth.token", tkn);
    }, process.env.AUTH_TOKEN);
  }

  await page.goto(`${BASE}/tracker`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(2000);
  await dismissTours(page);
  await shot(page, "00-tracker-overview");

  await page.locator('[data-testid="universe-search"]').fill("INFY");
  await page.waitForTimeout(1500);
  await shot(page, "01-entity-search");

  await page.goto(`${BASE}/companies/infy`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(2000);
  await dismissTours(page);

  await shot(page, "06-citability-evidence", '[data-testid="evidence-table"]');
  await shot(page, "12-delivery-record", '[data-testid="delivery-record"]');
  await shot(page, "04-period-documents", '[data-testid="period-docs"]');
  await shot(page, "10-private-notes", '[data-testid="private-notes"]');
  await shot(page, "11-report-templates-dossier", '[data-testid="report-panel"]');

  await page.goto(`${BASE}/desk?tab=review`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(1200);
  await dismissTours(page);
  await shot(page, "05-auto-ingest-crawl", '[data-testid="crawl-bar"]', 40);

  await page.goto(`${BASE}/desk?tab=corpus`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(1200);
  await dismissTours(page);
  await shot(page, "05b-corpus-foundation", '[data-testid="corpus-panel"]');

  await page.goto(`${BASE}/desk?tab=reports`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(1200);
  await dismissTours(page);
  try {
    await page.locator('[data-testid="generate-report"]').first().click({ timeout: 4000 });
    await page.waitForTimeout(2000);
  } catch {
    /* optional */
  }
  await shot(page, "11-report-templates-desk", '.panel:has([data-testid="generate-report"])');

  await page.goto(`${BASE}/about`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(600);
  await dismissTours(page);
  await shot(page, "00-about-tiers", "#layers");

  await browser.close();
  console.log("done →", OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
