/** Guided product tours — step catalogs keyed by surface. */

export type TourStep = {
  /** CSS selector; prefers [data-testid=…] */
  selector: string;
  title: string;
  body: string;
  /** Optional route to navigate before highlighting */
  route?: string;
  /** Optional query string including leading ? */
  search?: string;
  /** Wait for selector up to N ms (default 2500) */
  waitMs?: number;
  placement?: "auto" | "top" | "bottom" | "left" | "right";
};

export type TourId =
  | "tracker"
  | "dossier"
  | "desk"
  | "research"
  | "sights"
  | "about_help";

export type TourGroup = "workbench" | "learn";

export type TourDef = {
  id: TourId;
  title: string;
  blurb: string;
  group: TourGroup;
  /** Prefer this route when launching from Help hub */
  startRoute: string;
  steps: TourStep[];
};

export const TOURS: TourDef[] = [
  {
    id: "tracker",
    title: "GCI Screener",
    blurb: "Screen Sensex and other Indian companies, find citeable ones and open a dossier.",
    group: "workbench",
    startRoute: "/tracker",
    steps: [
      {
        selector: ".brand",
        title: "Welcome to CiteAlpha",
        body: "The Guidance Credibility Index (GCI) scores whether management delivered on its quantified guidance. Every score links to its evidence. No Buy/Hold calls.",
        route: "/tracker",
      },
      {
        selector: '[data-testid="universe-filters"]',
        title: "Market & index",
        body: "Choose India, then SENSEX, for hand-labeled GCI scores. NSE_ALL and BSE_ALL list every listed company; those without hand-labeled evidence show Not yet scored.",
      },
      {
        selector: '[data-testid="entity-search"]',
        title: "Company search",
        body: "Search any NSE/BSE listing. Filter by exchange, data quality and document status, and pick “citeable” for anything you will quote externally.",
      },
      {
        selector: '[data-testid="company-table"]',
        title: "Universe table",
        body: "GCI, change, data-quality badge and peer rank. Click a row to open the evidence dossier.",
      },
      {
        selector: '[data-testid="alerts-panel"]',
        title: "Alerts",
        body: "Guidance drift, pending documents and delivery alerts for the companies on screen, with a link straight to review.",
        placement: "left",
      },
    ],
  },
  {
    id: "dossier",
    title: "Company dossier",
    blurb: "Evidence, period documents and descriptive analytics.",
    group: "workbench",
    startRoute: "/companies/infy",
    steps: [
      {
        selector: '[data-testid="company-name"]',
        title: "Dossier header",
        body: "Company name, GCI score and data-quality badge. Hand-labeled companies are safe to cite.",
        route: "/companies/infy",
      },
      {
        selector: '[data-testid="gci-score"]',
        title: "GCI score",
        body: "A 0–100 delivery score built from closed guidance outcomes. The change appears next to the level once point-in-time history exists.",
      },
      {
        selector: ".dossier-toc",
        title: "Sections",
        body: "Jump between Evidence, Docs, Trend, Analytics, Notes and Reports.",
      },
      {
        selector: '[data-testid="evidence-table"]',
        title: "Evidence trail",
        body: "Each row shows the period, metric, guided range, actual, outcome, quote, URL and citation ID. Rows that cannot be cited are badged.",
      },
      {
        selector: '[data-testid="period-docs"]',
        title: "Period documents",
        body: "Transcript, results release and IR material for each fiscal year. The coverage check passes when all three are present and at least 95% of outcomes are citeable.",
      },
      {
        selector: '[data-testid="analytics-panel"]',
        title: "Analytics",
        body: "The Granger panel shows statistical precedence once the sample reaches 12. The impact map keeps only FDR-controlled links. Neither shows causation, and neither is advice.",
      },
    ],
  },
  {
    id: "desk",
    title: "Analyst Workbench",
    blurb: "First run: check extracted guidance, see new filings, export cited reports.",
    group: "workbench",
    startRoute: "/desk?tab=console",
    steps: [
      {
        selector: '[data-testid="desk-console"]',
        title: "Welcome to the Analyst Workbench",
        body: "This is where analysts check guidance we pulled from filings before it counts toward a GCI score. Nothing here changes a live score until you accept it. Takes about a minute.",
        route: "/desk",
        search: "?tab=console",
      },
      {
        selector: '[data-testid="desk-page"] .tab-bar',
        title: "Your sections",
        body: "Console is the overview. Review is the queue of statements to check. Corpus shows source coverage. Reports builds cited notes. PIT exports history.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="crawl-bar"]',
        title: "New filings arrive on their own",
        body: "We check company IR pages every 6 hours. New documents wait here until someone reviews them.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="queue-extract"]',
        title: "Try it with a demo sample",
        body: "Click this to pull guidance from a demo transcript. Those items are badged “Demo sample”: practice data, not a real filing. Accept, edit or reject each line, then commit.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="queue-paste"]',
        title: "Missing a document?",
        body: "Paste transcript text or an IR link here only when a filing isn't in the corpus yet. Most days you won't need this.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="corpus-panel"]',
        title: "Source coverage",
        body: "See which companies have a transcript, results release, and IR page for each year, and how many rows can be cited.",
        route: "/desk",
        search: "?tab=corpus",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="reports-panel"]',
        title: "Cited reports",
        body: "Build a note that includes only rows with a source, plus a citation list at the end. Unverified rows are left out.",
        route: "/desk",
        search: "?tab=reports",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="pit-panel"]',
        title: "Scores as of any date",
        body: "Export GCI as it stood on a past date, so backtests never see later data. Replay this tour any time from Help.",
        route: "/desk",
        search: "?tab=pit",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "research",
    title: "Filing Search",
    blurb: "Cited search and chat, a company snapshot and a watchlist with MoM/QoQ/YoY.",
    group: "workbench",
    startRoute: "/research?tab=search",
    steps: [
      {
        selector: '[data-testid="research-page"]',
        title: "Filing Search",
        body: "Search and cited chat over filings and transcripts. It complements the GCI and is not a price terminal.",
        route: "/research",
        search: "?tab=search",
      },
      {
        selector: '[data-testid="research-query"]',
        title: "Primary-source search",
        body: "Search the text of IR material, transcripts and filings. Use hand-labeled companies for any claim about guidance delivery.",
        route: "/research",
        search: "?tab=search",
      },
      {
        selector: '[data-testid="research-question"]',
        title: "Cited chat",
        body: "Every answer cites a retrieved passage. Quotes are never invented, and unscored placeholders are left out.",
        route: "/research",
        search: "?tab=chat",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="promise-brief"]',
        title: "Desk snapshot",
        body: "GCI over time, open promises and MoM/QoQ/YoY context for the selected company.",
        route: "/research",
        search: "?tab=desk",
        waitMs: 5000,
      },
      {
        selector: '[data-testid="research-watchlist"]',
        title: "Watchlist",
        body: "Last price, period changes and GCI change for each company. Click through for the full dossier.",
        route: "/research",
        search: "?tab=watch",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "sights",
    title: "Disclosure Explorer",
    blurb: "Compare disclosures across companies: themes, street context, field evidence, grid and deep dive.",
    group: "workbench",
    startRoute: "/sights",
    steps: [
      {
        selector: '[data-testid="sights-hub"]',
        title: "Disclosure Explorer overview",
        body: "Research disclosures across companies with themes, the grid and deep dives. Search and Ask are in Filing Search; skills and exports are in CiteAlpha Analyst.",
        route: "/sights",
      },
      {
        selector: '[data-testid="sights-themes"]',
        title: "Delivery themes",
        body: "Recurring topics across management commentary, grouped by sector, each linked to its source filing.",
        route: "/sights/themes",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="sights-grid"]',
        title: "Compare grid",
        body: "Put several companies side by side on the same disclosure questions. For search across companies, use Filing Search with All covered companies.",
        route: "/sights/grid",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "about_help",
    title: "About, Help & Trust",
    blurb: "What the product does, the glossary, and the Trust Center for procurement.",
    group: "learn",
    startRoute: "/about",
    steps: [
      {
        selector: '[data-testid="about-page"]',
        title: "About CiteAlpha",
        body: "What GCI is, why desks use it, how a score is built from filings, and who uses which tool. Product lines are listed on Products.",
        route: "/about",
      },
      {
        selector: '[data-testid="help-page"]',
        title: "Help hub",
        body: "Where to start, guided tours, the source policy, and the glossary behind every ⓘ tip.",
        route: "/help",
      },
      {
        selector: '[data-testid="help-search"]',
        title: "Find a term",
        body: "Type citeable, dropped, PIT, or Granger to jump to definitions used across the GCI Screener, Analyst Workbench, Filing Search, and Disclosure Explorer.",
        route: "/help",
      },
      {
        selector: '[data-testid="trust-page"]',
        title: "Trust Center",
        body: "Security, data residency, counsel status and citation practice for procurement teams. Live status, not marketing claims.",
        route: "/trust",
        waitMs: 4000,
      },
    ],
  },
];

export function getTour(id: TourId): TourDef | undefined {
  return TOURS.find((t) => t.id === id);
}

export const TOUR_GROUPS: { id: TourGroup; label: string }[] = [
  { id: "workbench", label: "Workbench" },
  { id: "learn", label: "Learn" },
];

export const TOUR_STORAGE_KEY = "citealpha.tours.seen.v2";

export type TourSeenMap = Partial<Record<TourId | "welcome_prompt" | "desk_first_run", boolean>>;

export function loadTourSeen(): TourSeenMap {
  try {
    const raw = localStorage.getItem(TOUR_STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as TourSeenMap;
  } catch {
    return {};
  }
}

export function saveTourSeen(map: TourSeenMap): void {
  try {
    localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* ignore quota */
  }
}
