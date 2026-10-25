import { expect, type Page } from "@playwright/test";

/** Dismiss analytics consent and one-time welcome tour if shown. */
export async function dismissOverlays(page: Page): Promise<void> {
  const consent = page.getByRole("dialog", { name: "Analytics cookies" });
  if (await consent.isVisible({ timeout: 1200 }).catch(() => false)) {
    await page.getByRole("button", { name: "Decline" }).click();
    await expect(consent).toBeHidden({ timeout: 3000 });
  }

  const welcome = page.getByTestId("tour-welcome");
  if (await welcome.isVisible({ timeout: 1500 }).catch(() => false)) {
    await page.getByTestId("tour-welcome-dismiss").click();
    await expect(welcome).toBeHidden({ timeout: 3000 });
  }
}

function abuseAnswer(prompt: string): string {
  const m = /What is (\d+) \+ (\d+)\?/.exec(prompt);
  if (!m) throw new Error(`Unexpected abuse prompt: ${prompt}`);
  return String(Number(m[1]) + Number(m[2]));
}

const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";

/** Seed a guest session via API (avoids web-proxy rate limits on abuse challenge). */
export async function seedGuestSession(page: Page): Promise<void> {
  const challengeRes = await fetch(`${API_URL}/api/auth/abuse-challenge`);
  if (!challengeRes.ok) throw new Error(`Guest abuse challenge failed (${challengeRes.status})`);
  const challenge = (await challengeRes.json()) as { challenge_id: string; prompt: string };
  const guestRes = await fetch(`${API_URL}/api/auth/guest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      accept_terms: true,
      challenge_id: challenge.challenge_id,
      challenge_answer: abuseAnswer(challenge.prompt),
    }),
  });
  if (!guestRes.ok) throw new Error(`Guest auth failed (${guestRes.status})`);
  const { token } = (await guestRes.json()) as { token: string };
  await page.goto("/");
  await page.evaluate((tkn) => {
    localStorage.setItem("intellens.auth.token", tkn);
    localStorage.setItem("intellens.analytics_consent", "denied");
    localStorage.setItem(
      "citealpha.tours.seen.v2",
      JSON.stringify({ welcome_prompt: true, tracker: true, desk_first_run: true }),
    );
  }, token);
  await page.goto("/tracker");
  await dismissOverlays(page);
}

/** Register a B2B user via API and return its credentials. */
export async function registerViaApi(): Promise<{ email: string; password: string }> {
  const challengeRes = await fetch(`${API_URL}/api/auth/abuse-challenge`);
  if (!challengeRes.ok) throw new Error(`Abuse challenge failed (${challengeRes.status})`);
  const challenge = (await challengeRes.json()) as { challenge_id: string; prompt: string };
  const email = `e2e-login-${Date.now()}@ocotillo.test`;
  const password = "secret99pass!";
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      name: "E2E Login",
      accept_terms: true,
      account_type: "b2b",
      org_name: "E2E Login Desk",
      challenge_id: challenge.challenge_id,
      challenge_answer: abuseAnswer(challenge.prompt),
    }),
  });
  if (!res.ok) throw new Error(`Register failed (${res.status})`);
  return { email, password };
}

/** Complete guest login from `/login` UI (terms + abuse challenge). */
export async function continueAsGuestFromLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await dismissOverlays(page);
  await expect(page.getByTestId("login-page")).toBeVisible();
  await page.locator("#guest-accept-terms").check();
  const challengeInput = page.getByTestId("guest-abuse-challenge");
  await expect(challengeInput).toBeVisible({ timeout: 15_000 });
  const labelText = await page.locator('label[for="guest-abuse-challenge"]').innerText();
  await challengeInput.fill(abuseAnswer(labelText));
  await page.getByTestId("guest-continue").click();
  await expect(page).toHaveURL(/\/tracker$/, { timeout: 15_000 });
}

/** Ensure primary nav is expanded (mobile toggle). */
export async function ensurePrimaryNav(page: Page): Promise<void> {
  const toggle = page.getByTestId("nav-toggle");
  if (await toggle.isVisible().catch(() => false)) {
    const nav = page.locator("#primary-nav");
    const open = await nav.evaluate((el) => el.classList.contains("open"));
    if (!open) await toggle.click();
  }
}

/** Open a header nav dropdown by `nav-dropdown-{id}`. */
export async function openNavDropdown(
  page: Page,
  id: "research" | "workspace" | "learn",
): Promise<void> {
  await ensurePrimaryNav(page);
  const root = page.getByTestId(`nav-dropdown-${id}`);
  await root.getByRole("button").click();
  await expect(root.locator(".nav-submenu")).toBeVisible({ timeout: 10_000 });
}

/** Click a submenu item inside an open nav dropdown. */
export async function clickNavDropdownItem(
  page: Page,
  id: "research" | "workspace" | "learn",
  name: RegExp | string,
): Promise<void> {
  await openNavDropdown(page, id);
  await page
    .getByTestId(`nav-dropdown-${id}`)
    .getByRole("menuitem", { name })
    .first()
    .click();
}

/** Wait for tracker universe table after parallel API calls settle. */
export async function waitForCompanyTable(page: Page): Promise<void> {
  await expect(page.getByTestId("company-table")).toBeVisible({ timeout: 20_000 });
}

/** Wait for company dossier GCI + evidence to finish loading. */
export async function waitForDossier(page: Page): Promise<void> {
  await expect(page.getByTestId("company-name")).toBeVisible({ timeout: 25_000 });
  await expect(page.getByTestId("evidence-table")).toBeVisible({ timeout: 25_000 });
}

/** Visit a route and assert it loads (no 404 shell). */
export async function assertRouteLoads(
  page: Page,
  spec: {
    path: string;
    testId?: string;
    heading?: RegExp;
    mayRedirect?: boolean;
    redirectTo?: RegExp;
    timeout?: number;
  },
): Promise<void> {
  const timeout = spec.timeout ?? 15_000;
  await page.goto(spec.path);
  await dismissOverlays(page);

  if (spec.mayRedirect && spec.redirectTo) {
    await expect(page).toHaveURL(spec.redirectTo, { timeout: 10_000 });
    return;
  }

  await expect(page.getByRole("heading", { name: "Page not found" })).toHaveCount(0);
  if (spec.testId) {
    await expect(page.getByTestId(spec.testId).first()).toBeVisible({ timeout });
  } else if (spec.heading) {
    await expect(page.getByRole("heading", { name: spec.heading }).first()).toBeVisible({
      timeout,
    });
  } else {
    await expect(page.locator("h1").first()).toBeVisible({ timeout });
  }
}
