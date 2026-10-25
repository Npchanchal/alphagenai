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
  | "analyst"
  | "holdings"
  | "ninja"
  | "workflows"
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
    blurb: "Screen Indian listings, hide unscored names when you want, and open a dossier from the row.",
    group: "workbench",
    startRoute: "/tracker",
    steps: [
      {
        selector: ".brand",
        title: "Welcome to CiteAlpha",
        body: "The Guidance Credibility Index (GCI) scores whether management delivered on quantified guidance. Every published score links to the promise and the later actual. Not a recommendation.",
        route: "/tracker",
      },
      {
        selector: '[data-testid="universe-filters"]',
        title: "Index",
        body: "India is the scored market. Sensex is the hand-labeled set. NSE All and BSE All list every name. Unscored names sort last and carry no rank.",
      },
      {
        selector: '[data-testid="entity-search"]',
        title: "Company search",
        body: "Find a company by name or ticker. Scored names are the ones you can cite. A listing without both quotes shows Not scored.",
      },
      {
        selector: '[data-testid="screener-scope"]',
        title: "Scored only",
        body: "Tick Scored only to hide names without a published GCI. When they are shown, they sort after scored names.",
      },
      {
        selector: '[data-testid="company-table"]',
        title: "Universe table",
        body: "GCI, confidence tier, closed results, and the last filing. A change column is an em dash until the series can be cited. Click a row for the evidence.",
      },
      {
        selector: '[data-testid="alerts-panel"]',
        title: "Alerts",
        body: "Misses, dropped guidance, and filings still waiting for review, for the companies on screen.",
        placement: "left",
      },
    ],
  },
  {
    id: "dossier",
    title: "Company dossier",
    blurb: "The delivery record, both filings, and how the score is calculated.",
    group: "workbench",
    startRoute: "/companies/infy",
    steps: [
      {
        selector: '[data-testid="company-name"]',
        title: "Dossier header",
        body: "Company, ticker, and sector. The GCI sits with its confidence tier, the as-of date, and one sentence of the delivery record.",
        route: "/companies/infy",
      },
      {
        selector: '[data-testid="gci-score"]',
        title: "GCI score",
        body: "A 0–100 delivery score from closed guidance outcomes. Week, month, quarter, and year changes appear only when that history can be cited.",
      },
      {
        selector: ".dossier-toc",
        title: "Sections",
        body: "Delivery record, evidence, the revision trail, and how this score is calculated. Period documents, charts, and notes sit with a desk seat.",
      },
      {
        selector: '[data-testid="evidence-table"]',
        title: "Evidence trail",
        body: "Each row is one promise and the later reported figure: period, metric, guided band, actual, outcome, and both sources. Rows start grouped by metric, latest period first. Filter period or metric above the table.",
      },
      {
        selector: '[data-testid="revision-panel"]',
        title: "Revision trail",
        body: "The opening band, later revisions in the year, and the final figure. A walk-back shows up here before the year closes.",
      },
      {
        selector: '[data-testid="dossier-calc"]',
        title: "How this score is calculated",
        body: "The same worked example as the homepage: each metric, the weight, and what was left out because the period is still open.",
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
        selector: '[data-testid="desk-access-gate"], [data-testid="desk-console"]',
        title: "Welcome to the Analyst Workbench",
        body: "Analysts check guidance pulled from filings before it can move a published GCI. Nothing here changes a live score until a reviewer accepts it. A visitor sees how to request the seat.",
        route: "/desk",
        search: "?tab=console",
      },
      {
        selector: '[data-testid="desk-page"] .tab-bar, [data-testid="desk-access-gate"]',
        title: "Your sections",
        body: "Console is the overview. Review is the queue. Corpus is source coverage. Reports builds cited notes. Point-in-time export is the history as of a past date.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="crawl-bar"], [data-testid="desk-access-gate"]',
        title: "New filings",
        body: "New documents wait in the review queue until a reviewer accepts them. A sample batch is badged so it cannot be mistaken for a filing.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="queue-extract"], [data-testid="desk-access-gate"]',
        title: "Try it with a sample",
        body: "On a seat, this pulls guidance from a sample transcript. Those lines are badged “Demo sample”: practice data, not a filing. Accept, edit, or reject each line, then commit.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="queue-paste"], [data-testid="desk-access-gate"]',
        title: "Missing a document?",
        body: "Paste transcript text or an IR link only when that filing is not stored yet. Most days the queue already has it.",
        route: "/desk",
        search: "?tab=review",
      },
      {
        selector: '[data-testid="corpus-panel"], [data-testid="desk-access-gate"]',
        title: "Source coverage",
        body: "Which companies have a transcript, a results release, and an IR page for each year, and how many rows can be cited.",
        route: "/desk",
        search: "?tab=corpus",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="reports-panel"], [data-testid="desk-access-gate"]',
        title: "Cited reports",
        body: "A note that includes only rows with a source, plus the citation list. Rows that cannot be cited are left out.",
        route: "/desk",
        search: "?tab=reports",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="pit-panel"], [data-testid="desk-access-gate"]',
        title: "Scores as of any date",
        body: "Export GCI as it stood on a past date, so a later filing cannot enter the history. Replay this tour from Help.",
        route: "/desk",
        search: "?tab=pit",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "research",
    title: "Filing Search",
    blurb: "Search filings. A research seat adds cite-only chat, a snapshot, and a watchlist.",
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
        body: "Search the text of stored filings and transcripts. Without a research seat, search stays on companies that already have a published GCI, eight times in this browser.",
        route: "/research",
        search: "?tab=search",
      },
      {
        selector: '[data-testid="research-question"], [data-testid="research-access-gate"]',
        title: "Cited chat",
        body: "On a research seat, every answer cites a retrieved passage. A passage that is not in the store is not invented. Visitors see how to request that seat.",
        route: "/research",
        search: "?tab=chat",
        waitMs: 4000,
      },
      {
        selector: '[data-testid="promise-brief"], [data-testid="research-access-gate"]',
        title: "Company snapshot",
        body: "Open promises and the delivery record for the selected company. A period change is shown only when the series can be cited.",
        route: "/research",
        search: "?tab=desk",
        waitMs: 5000,
      },
      {
        selector: '[data-testid="research-watchlist"], [data-testid="research-access-gate"]',
        title: "Watchlist",
        body: "Companies the seat is following, with the published GCI. A change is an em dash until the series can be cited. Open the row for the dossier.",
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
    id: "analyst",
    title: "CiteAlpha Analyst",
    blurb: "A cited note in the desk's format, and a monitor when a new filing is stored.",
    group: "workbench",
    startRoute: "/analyst",
    steps: [
      {
        selector: '[data-testid="analyst-page"], [data-testid="analyst-access-gate"]',
        title: "CiteAlpha Analyst",
        body: "A seat writes a note from stored filings, in the desk's format, with a source on each claim. A visitor sees how to request that seat. The published GCI does not move because a note was exported.",
        route: "/analyst",
      },
      {
        selector: '[data-testid="analyst-page"] .analyst-skills, [data-testid="analyst-access-gate"] h2',
        title: "Skills",
        body: "Coverage, an earnings note, and the other jobs are named as work, not as files. Pick a company or a project, then run. A claim the sources do not support is dropped, and the note says so.",
        route: "/analyst",
      },
      {
        selector: '[data-testid="analyst-feed"], [data-testid="analyst-access-gate"] a[href="/products#plans"]',
        title: "When a filing arrives",
        body: "A Coverage Monitor quotes the new filing, lists guidance that is still open, and restates the delivery record. It does not publish a new score. Export is Excel, PowerPoint, PDF, or Markdown.",
        route: "/analyst",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "holdings",
    title: "Holdings",
    blurb: "The weighted GCI of the part of a book that has a published score, and a named gap list.",
    group: "workbench",
    startRoute: "/holdings",
    steps: [
      {
        selector: '[data-testid="holdings-page"], [data-testid="holdings-gate"]',
        title: "Holdings look-through",
        body: "Paste identifiers and weights. The figure is the weighted GCI of the weight that has a published score. Cash, debt, and names without a score are gaps, not a filled-in number.",
        route: "/holdings",
      },
      {
        selector: '[data-testid="holdings-file"], [data-testid="holdings-gate"] h2',
        title: "The book",
        body: "An identifier, a weight, and a name. Five hundred lines is the limit. The latest file stays with this organisation. Another desk's file is not here.",
        route: "/holdings",
      },
      {
        selector: '[data-testid="holdings-covered-gci"], [data-testid="holdings-gate"] a[href="/products#plans"]',
        title: "Covered weight",
        body: "The result leads with the weighted GCI and the share of the book that entered it. The gap list names every line left out, and why. The figure is not a recommendation.",
        route: "/holdings",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "ninja",
    title: "Financial Ninja",
    blurb: "Valuation worksheets and delivery counts that stay separate from the published GCI.",
    group: "workbench",
    startRoute: "/ninja",
    steps: [
      {
        selector: '[data-testid="ninja-page"], [data-testid="ninja-gate"]',
        title: "Financial Ninja",
        body: "A worksheet beside the delivery record. The result is labeled as the desk's figure. It is not the Guidance Credibility Index, and it is not a recommendation.",
        route: "/ninja",
      },
      {
        selector: '[data-testid="ninja-template"], [data-testid="ninja-gate"] h2',
        title: "The worksheet",
        body: "Discounted cash flow, relative value, residual income, reverse discounted cash flow, and asset value. Each input has a unit. Saving keeps the inputs for this organisation.",
        route: "/ninja",
      },
      {
        selector: '[data-testid="ninja-page"], [data-testid="ninja-gate"]',
        title: "Counts, not a new score",
        body: "Layer notes need a source, and an index waits until three cited observations exist. Delivery tests count met, exceeded, and missed. The count does not rewrite the GCI.",
        route: "/ninja/tests",
        waitMs: 4000,
      },
    ],
  },
  {
    id: "workflows",
    title: "Workflows",
    blurb: "Earnings, delivery, coverage, and a desk note — each one opens a page that already exists.",
    group: "learn",
    startRoute: "/workflows",
    steps: [
      {
        selector: '[data-testid="workflows-page"]',
        title: "Four jobs",
        body: "Workflows is a map, not a second product. Each section names the job and links to the page that does it.",
        route: "/workflows",
      },
      {
        selector: '[data-testid="workflow-earnings-season"]',
        title: "Earnings season",
        body: "Open the dossier for the guided band, the reported figure, and both filings. On a desk seat, a Coverage Monitor prepares the same comparison when the filing is stored.",
        route: "/workflows",
      },
      {
        selector: '[data-testid="workflow-management-delivery"]',
        title: "Management delivery",
        body: "The screener and the evidence table are the delivery record. The methodology page is how a point enters the score.",
        route: "/workflows",
      },
      {
        selector: '[data-testid="workflow-desk-note"]',
        title: "A note in the desk's format",
        body: "CiteAlpha Analyst writes the note. The published GCI on the company page is unchanged when the note is saved.",
        route: "/workflows",
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
        body: "Type citeable, dropped, tier, or reading room. The same words sit behind every ⓘ tip on the screener, the dossier, Filing Search, and Disclosure Explorer.",
        route: "/help",
      },
      {
        selector: '[data-testid="trust-page"]',
        title: "Trust Center",
        body: "Security, data residency, and citation practice for a desk that is evaluating the product.",
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
