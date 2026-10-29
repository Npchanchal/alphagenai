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
    tip: "0–100 score of whether management delivered on quantified guidance, built from evidence rows (guided range, reported figure, outcome). Not a recommendation.",
  },
  tracker: {
    id: "tracker",
    term: "GCI Screener",
    tip: "Screen listed companies by GCI, confidence tier, and delivery record. Tick Scored only to hide names without a published score. A change in GCI appears only when the series can be cited. Open a company for the evidence.",
  },
  desk_sku: {
    id: "desk_sku",
    term: "Analyst Workbench (review & export workspace)",
    tip: "Review workspace for a pilot or paid desk: accept extracted guidance, check source coverage, export point-in-time history, and build cited reports. A guest can read the screener without this seat.",
  },
  research_terminal: {
    id: "research_terminal",
    term: "Filing Search",
    tip: "Search stored filings and transcripts. A research seat can search the covered set, ask cite-only questions, and keep a snapshot and a watchlist. Without that seat, search is limited to companies with a published GCI, eight searches in this browser.",
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
    tip: "The reported figure landed inside the guided range, with a small tolerance. That outcome scores about 100 before the match-confidence adjustment.",
  },
  exceeded: {
    id: "exceeded",
    term: "Exceeded",
    tip: "The reported figure came in above the guided range. A small beat scores close to 100. A beat far above the range means the guidance was off, so points fall with the distance and never go below 60. A miss the same distance below scores lower.",
  },
  missed: {
    id: "missed",
    term: "Missed",
    tip: "The actual came in below the range. Points fall with the size of the shortfall, and a large miss can score 0.",
  },
  dropped: {
    id: "dropped",
    term: "Dropped",
    tip: "Management stopped reiterating the guidance. The row stays out of the average, and the company score takes a 15-point withdrawal deduction. Not the same as a miss.",
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
    term: "Match confidence",
    tip: "How sure the match is between the guidance sentence and the later reported figure, from 0.5 to 1.0. A weaker match pulls that outcome toward 50. This is not the Provisional, Established, or Deep tier.",
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
    tip: "The screener does not rank a company against its sector. A public ordering is the Public Snapshot, and only for Established and Deep names, once enough companies qualify.",
  },
  sector_avg: {
    id: "sector_avg",
    term: "Sector avg",
    tip: "Average GCI of scored companies in a sector, on the India sector view. Each company is scored on its own guidance. The average is not a sector adjustment.",
  },
  trend: {
    id: "trend",
    term: "GCI trend",
    tip: "Company GCI over time, on a desk seat. Read the level with the change, and only when that series can be cited.",
  },
  change_trend: {
    id: "change_trend",
    term: "MoM / QoQ / YoY change",
    tip: "Change in GCI, or in a reported figure, against the prior comparable period. A GCI change is shown only when the point-in-time series can be cited. Otherwise the cell is an em dash.",
  },
  pit: {
    id: "pit",
    term: "PIT history",
    tip: "GCI as it stood on a past date, so a later filing cannot leak into the history. Exported from the Analyst Workbench. A change beside the level uses this series only when it can be cited.",
  },
  alerts: {
    id: "alerts",
    term: "Alerts",
    tip: "Flagged events such as repeated misses or dropped guidance that need analyst attention.",
  },
  data_quality: {
    id: "data_quality",
    term: "Data quality",
    tip: "Hand-labeled means the guidance quote and the later actual were both found on the cited filings. Those rows can carry a GCI. Sample data is for a walkthrough and is not scored. A listing is an exchange name that is not scored yet.",
  },
  listing_master: {
    id: "listing_master",
    term: "NSE / BSE listing",
    tip: "A row from the exchange's equity list. The GCI stays blank until guidance and actuals are labeled; we never invent actuals.",
  },
  nse_bse: {
    id: "nse_bse",
    term: "NSE_ALL / BSE_ALL",
    tip: "The full NSE and BSE equity lists. Names with a published GCI sort ahead of listings that are not scored. Not scored means both quotes are not yet on the cited filings.",
  },
  listing_provisional: {
    id: "listing_provisional",
    term: "Not yet scored",
    tip: "The guidance quote and the later actual are not both on the cited filings, so no GCI is shown. Not a fourth confidence tier.",
  },
  source: {
    id: "source",
    term: "Source",
    tip: "Where the guidance came from (transcript, filing or IR material), so every outcome can be audited.",
  },
  source_policy: {
    id: "source_policy",
    term: "Source policy",
    tip: "GCI uses text: transcripts, filings, IR pages, presentation text, speech-to-text transcripts, and reported actuals. Raw audio or video, technical charts, and tone do not feed the score.",
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
    tip: "A word map of tone, on a desk seat, for context beside the record. It is not an input to the GCI.",
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
    tip: "One contract for the screener, the workbench, Filing Search, CiteAlpha Analyst, Holdings, Financial Ninja, and the API. Guidance delivery only.",
  },
  csm: {
    id: "csm",
    term: "Customer success",
    tip: "A named contact and a quarterly review on Enterprise. The workbench shows the organisation on the evaluation.",
  },
  charts: {
    id: "charts",
    term: "Charts",
    tip: "Charts of GCI over time sit with a desk seat. The public dossier keeps the level, the tier, the delivery record, and the evidence table.",
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
    tip: "Exchange region, chosen once for the whole site. India has the deepest scored record. Other markets list the published index membership; a company there shows a GCI only after both quotes are checked in its filings.",
  },
  index: {
    id: "index",
    term: "Index",
    tip: "Flagship benchmark within a market (e.g. SENSEX, Nifty 50, S&P 500). Filters the universe table. Full GCI labeling covers India first.",
  },
  tier1: {
    id: "tier1",
    term: "Tier 1 foundation",
    tip: "The base layer: filings collected, each period's transcript, results and IR material, and a citation on every citeable row.",
  },
  citability: {
    id: "citability",
    term: "Citeable",
    tip: "Both the guidance quote and the later reported quote are on the cited filings. Sample rows are left out of a cited report.",
  },
  granger: {
    id: "granger",
    term: "Granger precedence",
    tip: "An experimental check, on a desk seat, of whether one series moves before another. It is not part of the GCI and it is not a forecast.",
  },
  corpus_status: {
    id: "corpus_status",
    term: "Corpus status",
    tip: "Citeable: both quotes are on the cited filings. In corpus: documents are stored. Not scored: an exchange listing whose guidance is not yet tied to a later actual.",
  },
  sights: {
    id: "sights",
    term: "Disclosure Explorer",
    tip: "Compare disclosures across Indian companies: delivery themes, street context, field evidence, a compare grid, and a deep dive. Search and cite-only questions are in Filing Search. Cited workflows are in CiteAlpha Analyst.",
  },
  analyst: {
    id: "analyst",
    term: "CiteAlpha Analyst",
    tip: "Cited workflows for a desk seat: a note in the desk's format, a monitor when a new filing is stored, and export to Excel, PowerPoint, or PDF. A monitor does not publish a new GCI.",
  },
  holdings: {
    id: "holdings",
    term: "Holdings",
    tip: "Paste a book and read the weighted GCI of the weight that has a published score. Cash, debt, indirect holdings, and names without a published score are listed as gaps. The figure is not a recommendation.",
  },
  financial_ninja: {
    id: "financial_ninja",
    term: "Financial Ninja",
    tip: "A desk worksheet for valuation, cited notes, and counts of the published delivery record. The worksheet figure belongs to the desk. It is not the GCI and it is not a recommendation.",
  },
  workflows: {
    id: "workflows",
    term: "Workflows",
    tip: "Four jobs a desk already does: earnings season, management delivery, coverage, and a note in the desk's format. Each one opens the page that does the work.",
  },
  reading_room: {
    id: "reading_room",
    term: "Reading room",
    tip: "Filing Search without a research seat. Search is limited to companies with a published GCI, eight searches in this browser. Cite-only chat, the snapshot, and the watchlist stay with the seat.",
  },
  confidence_tier: {
    id: "confidence_tier",
    term: "Confidence tier",
    tip: "Provisional, Established, or Deep, from how many closed periods and metrics are on the record. A public rank uses Established and Deep only. Not scored is not a tier.",
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
      "reading_room",
      "sights",
      "analyst",
      "holdings",
      "financial_ninja",
      "workflows",
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
    ids: ["confidence_tier", "confidence", "delta", "contribution", "metric", "period"],
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
