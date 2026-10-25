import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export type RouteSpec = {
  path: string;
  testId?: string;
  heading?: RegExp;
  /** Authenticated non-guest users may redirect (e.g. `/` → `/tracker`). */
  mayRedirect?: boolean;
  redirectTo?: RegExp;
  timeout?: number;
};

/** Blog slugs — keep in sync with `frontend/src/lib/blogPosts.ts`. */
export const BLOG_SLUGS = [
  "what-is-guidance-credibility-index",
  "sentiment-vs-guidance-delivery",
  "reading-guidance-vs-actuals-india",
  "sensex-pilot-evidence-trail",
  "gci-outcome-labels-explained",
  "point-in-time-gci-history",
  "hand-labeled-vs-demo-data",
  "buy-side-gci-workflow",
  "sell-side-citing-guidance-delivery",
  "concall-guidance-extraction-checklist",
  "nse-bse-ir-disclosure-formats",
  "vernacular-research-notes-factual",
  "peer-rank-sector-average-gci",
  "alerts-when-credibility-shifts",
  "api-first-gci-for-quant-desks",
  "sebi-oriented-product-design",
  "sensex-to-nifty-coverage-expansion",
  "why-india-needs-local-guidance-tracker",
  "desk-console-review-queue-hitl",
  "trust-center-checklist-institutional-buyers",
] as const;

export const SIGHTS_ROUTES: RouteSpec[] = [
  { path: "/sights", testId: "sights-hub" },
  { path: "/sights/themes", testId: "sights-themes" },
  { path: "/sights/grid", testId: "sights-grid" },
];

export const SIGHTS_ADVANCED_ROUTES: RouteSpec[] = [
  { path: "/sights/street", testId: "sights-street" },
  { path: "/sights/field", testId: "sights-field" },
  { path: "/sights/deep-dive", testId: "sights-deep-dive" },
  { path: "/sights/fundamentals", testId: "sights-fundamentals" },
  { path: "/sights/settings", testId: "sights-settings" },
];

export const CORE_ROUTES: RouteSpec[] = [
  { path: "/", testId: "landing-page", mayRedirect: true, redirectTo: /\/tracker$/ },
  { path: "/tracker", heading: /GCI Screener/i },
  { path: "/companies/infy", testId: "company-name" },
  { path: "/desk", testId: "desk-page" },
  { path: "/research", testId: "research-page" },
  { path: "/products", testId: "products-page" },
  { path: "/developers", testId: "developers-page" },
  { path: "/status", testId: "status-page" },
  { path: "/pilot", testId: "pilot-request-page" },
  { path: "/rankings", testId: "gci-rankings-page" },
  { path: "/about", testId: "about-page" },
  { path: "/workflows", testId: "workflows-page" },
  { path: "/blog", testId: "blog-index" },
  { path: "/help", testId: "help-page" },
  { path: "/trust", testId: "trust-page" },
  { path: "/terms", testId: "legal-terms-page" },
  { path: "/privacy", testId: "legal-privacy-page" },
  { path: "/login", testId: "login-page" },
  { path: "/register", testId: "register-page" },
  { path: "/forgot-password", testId: "forgot-password-page" },
  { path: "/reset-password", testId: "reset-password-page" },
  { path: "/verify-email", testId: "verify-email-page" },
  { path: "/accept-invite", testId: "accept-invite-page" },
  { path: "/billing", testId: "billing-page" },
  { path: "/account", testId: "account-settings-page" },
  { path: "/org/settings", testId: "org-settings-page" },
  { path: "/admin", testId: "admin-access-denied", timeout: 35_000 },
];

export const RESEARCH_TABS = ["search", "chat", "desk", "news", "watch"] as const;

export const DESK_TABS = [
  { id: "console", testId: "desk-console" },
  { id: "review", testId: "review-queue-panel" },
  { id: "corpus", testId: "corpus-panel" },
  { id: "reports", testId: "reports-panel" },
  { id: "pit", testId: "pit-panel" },
] as const;

export function loadSeoPaths(): string[] {
  const raw = fs.readFileSync(
    path.join(ROOT, "frontend/src/lib/seoRoutes.json"),
    "utf8",
  );
  return (JSON.parse(raw) as { path: string }[]).map((r) => r.path);
}

export function allCrawlRoutes(): RouteSpec[] {
  const seo = loadSeoPaths().filter((p) => p !== "/404").map((p) => {
    const hit = CORE_ROUTES.find((r) => r.path === p);
    return hit ?? { path: p };
  });
  const blog = BLOG_SLUGS.map((slug) => ({
    path: `/blog/${slug}`,
    testId: "blog-post",
  }));
  const extra = CORE_ROUTES.filter((r) => !seo.some((s) => s.path === r.path));
  const sights = SIGHTS_ROUTES.filter((s) => !seo.some((x) => x.path === s.path));
  return [...seo, ...extra, ...sights, ...blog];
}
