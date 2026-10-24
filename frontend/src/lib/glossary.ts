export type GlossaryTerm = {
  id: string;
  term: string;
  tip: string;
};

/** Shared vocabulary — Help page + inline InfoTip tooltips. */
export const GLOSSARY: Record<string, GlossaryTerm> = {
  gci: {
    id: "gci",
    term: "GCI (Guidance Credibility Index)",
    tip: "0–100 score of how reliably management delivers on its quantified guidance, built from evidence rows (guided range, actual, outcome). Not a buy/sell recommendation.",
  },
  tracker: {
    id: "tracker",
    term: "GCI Screener",
    tip: "Screen Sensex companies by GCI level, change in GCI (YoY/QoQ/PoP), data-quality badge, peers and alerts. Open a company for its evidence dossier and charts.",
  },
  desk_sku: {
    id: "desk_sku",
    term: "Analyst Workbench (review & export workspace)",
    tip: "Review workspace for pilot and paid desks: approve extracted guidance, check evidence, export point-in-time data and build reports. Requires a pilot or paid seat.",
  },
  research_terminal: {
    id: "research_terminal",
    term: "Filing Search",
    tip: "Search filings and transcripts for one company or all covered companies, ask cite-only questions, and see a company snapshot of guidance vs reported numbers. Complements GCI. Not a price feed.",
  },
  guidance: {
    id: "guidance",
    term: "Guidance",
    tip: "A forward-looking quantified promise from management for a metric and period (e.g. FY25 revenue growth 8–10%).",
  },
  actual: {
    id: "actual",
    term: "Actual",
    tip: "The reported result for the same metric and period, used to judge whether the guidance was delivered.",
  },
  band: {
    id: "band",
    term: "Band (guided low–high)",
    tip: "The range management guided to. A result inside the range (with a small tolerance) counts as met.",
  },
  evidence: {
    id: "evidence",
    term: "Evidence trail",
    tip: "The audit table for a company: period, metric, guided range, actual, change in actual, outcome, gap to guidance and source. Use hand-labeled companies when citing.",
  },
  thread: {
    id: "thread",
    term: "Promise thread",
    tip: "The history of one guidance commitment: first stated, then raised, cut or reiterated across calls until it resolves as met, missed, exceeded or dropped. Quiet walk-backs show up here.",
  },
  met: {
    id: "met",
    term: "Met",
    tip: "The actual landed inside (or very near) the guided range. Scores about 100 before the confidence adjustment.",
  },
  exceeded: {
    id: "exceeded",
    term: "Exceeded",
    tip: "The actual came in above the range. Under the default scorer (v4), a small beat scores close to 100. A beat far above the range still means the guidance was off, so points fall with distance, but never below 60. A miss the same distance below always scores lower (γ=1.4). Scorer v3 let beats fall toward 0; the older v2 set a floor of 85 for beats.",
  },
  missed: {
    id: "missed",
    term: "Missed",
    tip: "The actual came in below the range. Points fall with the size of the shortfall, and a large miss can score 0.",
  },
  dropped: {
    id: "dropped",
    term: "Dropped",
    tip: "Management stopped reiterating the guidance. The default scorer v4 (like v3) leaves the row out of the average and applies a −15 withdrawal deduction to the company score. The older v2 scored a dropped row at about 35. Not the same as a miss.",
  },
  pending: {
    id: "pending",
    term: "Pending",
    tip: "The period is still open or no actual has been reported. Left out of the company GCI until it closes.",
  },
  basis_mismatch: {
    id: "basis_mismatch",
    term: "Different basis",
    tip: "The actual is on a different reporting basis, unit, or scope from the guidance, so the row stays outside the score.",
  },
  pending_guidance_cite: {
    id: "pending_guidance_cite",
    term: "Pending guidance cite",
    tip: "The reported actual is cited, but the original guidance filing (URL, quote, date) is not yet on the row. Excluded from the company GCI until both sides are cited.",
  },
  confidence: {
    id: "confidence",
    term: "Confidence",
    tip: "How certain the extraction and match are (0.5–1.0). Lower confidence pulls the outcome score toward 50.",
  },
  delta: {
    id: "delta",
    term: "Delta % (vs guide)",
    tip: "The relative gap between the actual and the guided midpoint (or the edge of the range).",
  },
  contribution: {
    id: "contribution",
    term: "Contribution score",
    tip: "That outcome’s 0–100 score after label rules and confidence. Company GCI averages these.",
  },
  peer_rank: {
    id: "peer_rank",
    term: "Peer rank",
    tip: "Rank of this company’s GCI among Sensex peers in the same sector (1 = best).",
  },
  sector_avg: {
    id: "sector_avg",
    term: "Sector avg",
    tip: "Average of company GCI scores in the sector. Each company is scored on its own guidance. The average is not a sector adjustment.",
  },
  trend: {
    id: "trend",
    term: "GCI trend",
    tip: "Company GCI period by period on a line chart, showing whether credibility is improving or eroding. Read the level and the change together.",
  },
  change_trend: {
    id: "change_trend",
    term: "MoM / QoQ / YoY change",
    tip: "Percentage change against the prior comparable period. Desks often read the change before the level.",
  },
  pit: {
    id: "pit",
    term: "PIT history",
    tip: "GCI as it stood on past dates, for backtests with no look-ahead. Shown as a table and a chart, with the change from the prior point.",
  },
  alerts: {
    id: "alerts",
    term: "Alerts",
    tip: "Flagged events such as repeated misses or dropped guidance that need analyst attention.",
  },
  data_quality: {
    id: "data_quality",
    term: "Data quality",
    tip: "Hand-labeled = guidance whose quotes were found on the cited filings; the only rows that carry a GCI. Demo = sample data for walkthroughs, not scored. Listing = NSE/BSE master, not yet scored.",
  },
  listing_master: {
    id: "listing_master",
    term: "NSE / BSE listing",
    tip: "A row from the exchange's equity list. The GCI stays blank until guidance and actuals are labeled; we never invent actuals.",
  },
  nse_bse: {
    id: "nse_bse",
    term: "NSE_ALL / BSE_ALL",
    tip: "Full India equity masters for navigation. Only hand-labeled companies carry a GCI; every other listing shows Not yet scored until both quotes are found on the cited filings.",
  },
  listing_provisional: {
    id: "listing_provisional",
    term: "Not yet scored",
    tip: "Listed company whose guidance quotes are not yet on the cited filings. No GCI is shown until that check passes.",
  },
  source: {
    id: "source",
    term: "Source",
    tip: "Where the guidance came from (transcript, filing or IR material), so every outcome can be audited.",
  },
  source_policy: {
    id: "source_policy",
    term: "Source policy",
    tip: "GCI uses text only: transcripts, filings, IR pages, presentation text, speech-to-text transcripts and reported actuals. Raw audio or video, technicals and shenanigans do not feed the score.",
  },
  review: {
    id: "review",
    term: "Review",
    tip: "Accept keeps the outcome; Reject excludes it and flags it for follow-up.",
  },
  extract: {
    id: "extract",
    term: "Extract",
    tip: "Pulls candidate guidance statements from transcript text into a review queue. Nothing enters the GCI until it is reviewed.",
  },
  sentiment: {
    id: "sentiment",
    term: "Wordmap (context)",
    tip: "Tone themes for a company against its industry, for context only. Not part of the GCI calculation.",
  },
  label: {
    id: "label",
    term: "Label",
    tip: "Outcome class: met, exceeded, missed, dropped, or pending.",
  },
  metric: {
    id: "metric",
    term: "Metric",
    tip: "Catalog name for the guided measure (for example revenue growth). Unknown metrics are rejected on import.",
  },
  gci_parameter: {
    id: "gci_parameter",
    term: "GCI parameter",
    tip: "A catalog metric that management quantified for a period (about 16 core metrics plus sector-specific ones). Only these enter the GCI; see the Parameters tab in the Analyst Workbench.",
  },
  period: {
    id: "period",
    term: "Period",
    tip: "Fiscal window the guidance applies to (e.g. FY24, Q2FY25).",
  },
  alphahunter: {
    id: "alphahunter",
    term: "Facts import",
    tip: "Paste facts JSON that matches the metric catalog and merge it into a company's record. Not a live vendor connector.",
  },
  labeling_queue: {
    id: "labeling_queue",
    term: "Labeling priority queue",
    tip: "Enterprise backlog for priority hand-labeling. Queues a company for analyst labeling; no actuals are invented.",
  },
  one_stop: {
    id: "one_stop",
    term: "Enterprise platform",
    tip: "One contract covering the GCI Screener, evidence, API, facts import, Wordmap, vernacular summaries and customer success. Guidance delivery only; keep your market terminal for prices.",
  },
  csm: {
    id: "csm",
    term: "Customer success",
    tip: "Named customer-success contact and quarterly reviews, included on Enterprise. The Workbench shows your pilot organisation.",
  },
  charts: {
    id: "charts",
    term: "Charts",
    tip: "Line, bar and donut charts for GCI over time, metric changes, parameter usage and Wordmap. Levels stay in tables; charts show change.",
  },
  language_selector: {
    id: "language_selector",
    term: "Language selector",
    tip: "Sets the interface language (Indian and global languages). Saved in this browser, and to your account when you are signed in. Does not change the GCI. The glossary is in English only for now.",
  },
  guest: {
    id: "guest",
    term: "Guest session",
    tip: "A temporary one-click identity that keeps your preferences. Register to sync language, market, index and watchlist across devices. Signing in does not entitle you to investment advice.",
  },
  market: {
    id: "market",
    term: "Market",
    tip: "Exchange region (IN, US, JP, …). Only India is scored in depth; other markets show index constituent lists with data-quality badges.",
  },
  index: {
    id: "index",
    term: "Index",
    tip: "Flagship benchmark within a market (e.g. SENSEX, Nifty 50, S&P 500). Filters the universe table. Full GCI labeling covers India first.",
  },
  tier1: {
    id: "tier1",
    term: "Tier 1 foundation",
    tip: "Ingestion, structure, search and citation: automatic collection of IR documents, each period's transcript, results and IR material, and a citation ID for every citeable item. Without this layer, analytics stay experimental.",
  },
  citability: {
    id: "citability",
    term: "Citeable",
    tip: "A hand-labeled outcome with a source URL and quote (and a linked document). Provisional and demo scores are never citeable, and reports leave them out.",
  },
  granger: {
    id: "granger",
    term: "Granger precedence",
    tip: "LASSO variable selection, then a Granger F-test on point-in-time series of at least 12 quarters. Predictive precedence is not causation, and this is not a forecast or investment advice.",
  },
  corpus_status: {
    id: "corpus_status",
    term: "Corpus status",
    tip: "Citeable: hand-labeled with sources. In corpus: scored, or documents are present. Filings not yet read: an exchange listing whose filings since 2022 have not been read yet.",
  },
  sights: {
    id: "sights",
    term: "Disclosure Explorer",
    tip: "Compare disclosures across Indian companies: search, cite-only Ask, boards, compare grid and desk agents over public IR material and labeled evidence. Complements the GCI; not a price terminal.",
  },
  score_sku: {
    id: "score_sku",
    term: "CiteAlpha Score",
    tip: "GCI 0–100 plus peer delivery comparisons. The core product: what management promised against what it delivered.",
  },
  radar: {
    id: "radar",
    term: "CiteAlpha Radar",
    tip: "A feed of guidance changes, misses, drops and withdrawals for PMs, risk teams and IR watchers. Not a news ticker.",
  },
  ledger: {
    id: "ledger",
    term: "CiteAlpha Ledger",
    tip: "What was committed, by whom and when, and where it stands. For compliance, credit, IR and board packs.",
  },
  data_sku: {
    id: "data_sku",
    term: "CiteAlpha Data",
    tip: "Point-in-time dataset of guidance outcomes, with factor export. The series can be backtested with no look-ahead.",
  },
  rankings: {
    id: "rankings",
    term: "Public Snapshot",
    tip: "A public snapshot of citeable GCI companies, no login needed. Each score links to its evidence. Not recommendations.",
  },
  trust_center: {
    id: "trust_center",
    term: "Trust Center",
    tip: "Security, legal and citation practices for procurement teams, with live configuration status rather than marketing claims.",
  },
};

export const HELP_SECTIONS: { title: string; ids: string[] }[] = [
  {
    title: "Where to work",
    ids: [
      "tracker",
      "desk_sku",
      "research_terminal",
      "sights",
      "score_sku",
      "radar",
      "ledger",
      "data_sku",
      "rankings",
      "one_stop",
      "trust_center",
      "tier1",
    ],
  },
  {
    title: "Language, identity & markets",
    ids: ["language_selector", "guest", "market", "index"],
  },
  {
    title: "Core ideas",
    ids: [
      "gci",
      "guidance",
      "actual",
      "band",
      "evidence",
      "citability",
      "corpus_status",
      "thread",
      "gci_parameter",
      "source_policy",
    ],
  },
  {
    title: "Outcome labels",
    ids: ["met", "exceeded", "missed", "dropped", "pending", "pending_guidance_cite", "basis_mismatch"],
  },
  {
    title: "How the score is built",
    ids: ["confidence", "delta", "contribution", "metric", "period"],
  },
  {
    title: "Change trends & history",
    ids: ["change_trend", "trend", "pit", "charts", "granger"],
  },
  {
    title: "Workbench fields",
    ids: [
      "peer_rank",
      "sector_avg",
      "alerts",
      "data_quality",
      "listing_master",
      "nse_bse",
      "source",
      "review",
      "extract",
      "sentiment",
      "alphahunter",
      "labeling_queue",
      "csm",
      "label",
    ],
  },
];

export function tipForLabel(label: string): string {
  const key = label.toLowerCase();
  return GLOSSARY[key]?.tip ?? GLOSSARY.label.tip;
}

export function formatOutcomeLabel(label: string): string {
  const key = label.toLowerCase();
  return GLOSSARY[key]?.term ?? label.replace(/_/g, " ");
}

export function tipText(termId: string): string {
  return GLOSSARY[termId]?.tip ?? "";
}
