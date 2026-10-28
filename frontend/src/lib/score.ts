/** Score color band for GCI 0–100 displays. */
export function scoreClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "";
  if (score >= 75) return "good";
  if (score >= 50) return "warn";
  return "bad";
}

export function formatScore(score: number | null | undefined, digits = 1): string {
  if (score === null || score === undefined) return "—";
  return score.toFixed(digits);
}

export const NOT_SCORED_LABEL = "Not yet scored";

const COVERAGE_LABELS: Record<string, string> = {
  scored: "Scored",
  open_period: "Guided year not yet closed",
  filing_in_review: "Filings being checked",
  no_quantified_guidance: "No numeric guidance found",
  listed_only: "Filings not yet read",
};

/** Typed GCI cell when there is no publishable number. */
export function formatCoverageStatus(status?: string | null): string {
  if (!status) return NOT_SCORED_LABEL;
  return COVERAGE_LABELS[status] || NOT_SCORED_LABEL;
}

/** A company's own GCI: a number, or the reason there is none — never an invented score. */
export function formatCompanyScore(
  score: number | null | undefined,
  digits = 1,
  coverageStatus?: string | null,
  coverageReason?: string | null,
): string {
  if (score === null || score === undefined) {
    return coverageReason || formatCoverageStatus(coverageStatus);
  }
  return score.toFixed(digits);
}

/** ``YYYY-MM-DD`` → ``d Mon yyyy`` (UTC), for dossier as-of / reviewed stamps. */
export function formatDossierDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim());
  if (!m) return iso;
  const dt = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return dt.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Catalog display names (mirrors backend/app/data/metric_catalog.py). */
const METRIC_DISPLAY: Record<string, string> = {
  revenue_growth_pct: "Revenue growth %",
  revenue_growth_cc_pct: "Revenue growth (constant currency) %",
  operating_margin_pct: "Operating margin %",
  ebitda_margin_pct: "EBITDA margin %",
  ebitda_growth_pct: "EBITDA growth %",
  pat_margin_pct: "Net / PAT margin %",
  capex: "Capex guidance",
  fcf_guidance: "Free cash flow guidance",
  wc_days: "Working-capital days",
  capacity_util_pct: "Capacity / utilization %",
  nim_pct: "Net interest margin %",
  loan_growth_pct: "Loan / advances growth %",
  underlying_volume_growth_pct: "Underlying volume growth %",
  cigarette_volume_growth_pct: "Cigarette volume growth %",
  wholesale_volume_growth_pct: "Wholesale volume growth %",
  sssg_pct: "Same-store sales growth %",
  arpu_growth_pct: "ARPU growth %",
  jewellery_ebitda_margin_pct: "Jewellery EBITDA margin %",
  rd_spend_pct: "R&D spend % of revenue",
  cost_saves_pct: "Cost savings % of revenue",
  ape_growth_pct: "APE / new business growth %",
  vnb_growth_pct: "VNB growth %",
  vnb_margin_pct: "VNB / new business margin %",
  oev_pct: "Operating return on embedded value %",
  occupancy_pct: "Hospital bed occupancy %",
  arpo_growth_pct: "ARPOB growth %",
  production_volume_mmt: "Production / cargo volume (MMT)",
  vehicle_volume_units: "Vehicle sales volume (units)",
  gross_margin_pct: "Gross margin %",
  revenue_usd_mn: "Revenue (US$ m)",
  eps_diluted_usd: "Diluted EPS (GAAP, US$)",
  eps_adjusted_usd: "Adjusted EPS (non-GAAP, US$)",
  adjusted_ebitda_usd_mn: "Adjusted EBITDA (US$ m)",
  fcf_usd_mn: "Free cash flow (US$ m)",
  capex_usd_mn: "Capex (US$ m)",
};

const METRIC_UNIT: Record<string, string> = {
  revenue_growth_pct: "pct",
  revenue_growth_cc_pct: "pct",
  operating_margin_pct: "pct",
  ebitda_margin_pct: "pct",
  ebitda_growth_pct: "pct",
  pat_margin_pct: "pct",
  nim_pct: "pct",
  loan_growth_pct: "pct",
  underlying_volume_growth_pct: "pct",
  cigarette_volume_growth_pct: "pct",
  wholesale_volume_growth_pct: "pct",
  sssg_pct: "pct",
  arpu_growth_pct: "pct",
  jewellery_ebitda_margin_pct: "pct",
  rd_spend_pct: "pct",
  cost_saves_pct: "pct",
  ape_growth_pct: "pct",
  vnb_growth_pct: "pct",
  vnb_margin_pct: "pct",
  oev_pct: "pct",
  occupancy_pct: "pct",
  arpo_growth_pct: "pct",
  production_volume_mmt: "mmt",
  vehicle_volume_units: "units",
  wc_days: "days",
  gross_margin_pct: "pct",
  revenue_usd_mn: "usd_mn",
  eps_diluted_usd: "usd",
  eps_adjusted_usd: "usd",
  adjusted_ebitda_usd_mn: "usd_mn",
  fcf_usd_mn: "usd_mn",
  capex_usd_mn: "usd_mn",
};

/** Value with its unit: 12.5% · $8,100m · $1.32. */
export function formatMetricValue(value: number, metricId?: string): string {
  const unit = metricId ? metricUnit(metricId) : "";
  if (unit === "pct") return `${value}%`;
  if (unit === "usd_mn") return `$${value.toLocaleString("en-US", { maximumFractionDigits: 1 })}m`;
  if (unit === "usd") return `$${value.toFixed(2)}`;
  return `${value}`;
}

export function metricDisplayName(metricId: string): string {
  return METRIC_DISPLAY[metricId] || metricId.replace(/_/g, " ");
}

/** A stored title sometimes is a metric id. Show the period and the metric name. */
export function publicDocTitle(title: string | null | undefined, docType?: string | null): string {
  const raw = (title || "").trim();
  const id = raw.match(/[a-z][a-z0-9]*_[a-z0-9_]+/)?.[0];
  if (!id) return raw || "Filing";
  const name = metricDisplayName(id);
  if (name.includes("_")) return docType ? docType.replace(/_/g, " ") : "Filing";
  const period = raw.match(/\bFY\d{2,4}\b/)?.[0];
  return period ? `${period} ${name}` : name;
}

export function metricUnit(metricId: string): string {
  return METRIC_UNIT[metricId] || (metricId.endsWith("_pct") ? "pct" : "");
}

/** Character span on a filing — never interpolate raw `{end}` into the DOM. */
export function formatCharLocator(
  start?: number | null,
  end?: number | null,
): string {
  if (start == null || end == null) return "";
  return `chars ${start}–${end}`;
}

export function formatGuidedBand(o: {
  guided_low?: number | null;
  guided_high?: number | null;
  guided_value: number;
  metric?: string;
}): string {
  const fmt = (v: number) => formatMetricValue(v, o.metric);
  if (o.guided_low != null && o.guided_high != null) {
    if (o.guided_low === o.guided_high) return fmt(o.guided_low);
    return `${fmt(o.guided_low)}–${fmt(o.guided_high)}`;
  }
  return fmt(o.guided_value);
}

export function formatActual(o: {
  actual_value: number | null;
  metric?: string;
}): string {
  if (o.actual_value == null) return "—";
  return formatMetricValue(o.actual_value, o.metric);
}

/** Guided-vs-actual gap in the metric's own units (not YoY of a growth rate). */
export function formatGuideGap(o: {
  actual_value: number | null;
  guided_low?: number | null;
  guided_high?: number | null;
  guided_value: number;
  metric?: string;
}): string {
  if (o.actual_value == null) return "—";
  const mid =
    o.guided_low != null && o.guided_high != null
      ? (o.guided_low + o.guided_high) / 2
      : o.guided_value;
  const gap = o.actual_value - mid;
  const sign = gap > 0 ? "+" : "";
  const n = Number.isInteger(gap) ? String(gap) : gap.toFixed(1);
  const unit = o.metric && metricUnit(o.metric) === "pct" ? " pp" : "";
  return `${sign}${n}${unit}`;
}

const FY_PERIOD = /^FY\s*(\d{2}|\d{4})$/i;
const QFY_PERIOD = /^Q([1-4])\s*FY\s*(\d{2}|\d{4})$/i;
const FYQ_PERIOD = /^FY\s*(\d{2}|\d{4})\s*Q([1-4])$/i;
const YQ_PERIOD = /^(\d{4})-Q([1-4])$/;
const YM_PERIOD = /^(\d{4})-(\d{2})$/;
const ASOF_PERIOD = /^(\d{4})-(\d{2})-(\d{2})/;

function normYear(year: string): number {
  const n = Number(year);
  return n < 100 ? 2000 + n : n;
}

/** Same rank as backend ``period_rank`` / ``parse_period``. Unknown labels return null. */
export function periodRank(period: string | null | undefined): number | null {
  const p = (period || "").trim();
  let m = FY_PERIOD.exec(p);
  if (m) return normYear(m[1]) * 12 + 3;
  m = QFY_PERIOD.exec(p);
  if (m) return normYear(m[2]) * 12 + (Number(m[1]) - 1) * 3;
  m = FYQ_PERIOD.exec(p);
  if (m) return normYear(m[1]) * 12 + (Number(m[2]) - 1) * 3;
  m = YQ_PERIOD.exec(p);
  if (m) return Number(m[1]) * 12 + (Number(m[2]) - 1) * 3;
  m = YM_PERIOD.exec(p);
  if (m) return Number(m[1]) * 12 + (Number(m[2]) - 1);
  m = ASOF_PERIOD.exec(p);
  if (m) return Number(m[1]) * 12 + (Number(m[2]) - 1);
  return null;
}

/** Year-view columns: the company's periods, newest first. Unknown labels last. */
export function evidenceYearColumns(periods: (string | null | undefined)[]): string[] {
  const unique = [...new Set(periods.filter((p): p is string => !!p))];
  return unique.sort((a, b) => {
    const ka = periodRank(a);
    const kb = periodRank(b);
    if (ka == null && kb == null) return b.localeCompare(a);
    if (ka == null) return 1;
    if (kb == null) return -1;
    return kb - ka;
  });
}

const CLOSED_OUTCOMES = new Set(["met", "exceeded", "missed", "dropped"]);

/** Track column: closed outcome labels oldest to newest, given cells newest first. */
export function evidenceTrack(labelsNewestFirst: (string | null | undefined)[]): string[] {
  return [...labelsNewestFirst]
    .reverse()
    .filter((label): label is string => !!label && CLOSED_OUTCOMES.has(label.toLowerCase()));
}

function chronoText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Latest period, then latest result date, then metric name. Unknown periods last. */
export function compareEvidenceLatestFirst(
  a: { period?: unknown; as_of?: unknown; metric?: unknown },
  b: { period?: unknown; as_of?: unknown; metric?: unknown },
): number {
  const byPeriod = periodOrder(a, b, true);
  if (byPeriod !== 0) return byPeriod;
  return chronoText(a.metric).localeCompare(chronoText(b.metric));
}

export type EvidenceSortKey = "metric" | "period";
export type EvidenceSortDir = "asc" | "desc";
export type EvidenceSort = { key: EvidenceSortKey; dir: EvidenceSortDir };

/** Every evidence listing opens on the latest period. */
export const DEFAULT_EVIDENCE_SORT: EvidenceSort = { key: "period", dir: "desc" };

/**
 * Evidence table order. Metric sort keeps latest period as the tie-break.
 * Period sort keeps metric name as the tie-break. Unknown periods stay last.
 */
export function compareEvidence(
  a: { period?: unknown; as_of?: unknown; metric?: unknown },
  b: { period?: unknown; as_of?: unknown; metric?: unknown },
  sort: EvidenceSort = DEFAULT_EVIDENCE_SORT,
): number {
  const byMetric = metricDisplayName(chronoText(a.metric)).localeCompare(
    metricDisplayName(chronoText(b.metric)),
  );
  if (sort.key === "metric") {
    const primary = sort.dir === "desc" ? -byMetric : byMetric;
    if (primary !== 0) return primary;
    return periodOrder(a, b, true);
  }
  const byPeriod = periodOrder(a, b, sort.dir !== "asc");
  if (byPeriod !== 0) return byPeriod;
  return byMetric;
}

export function listEvidenceRows<T extends { period?: unknown; metric?: unknown; as_of?: unknown }>(
  rows: readonly T[],
  opts?: { period?: string; metric?: string; sort?: EvidenceSort },
): T[] {
  const period = opts?.period ?? "";
  const metric = opts?.metric ?? "";
  const sort = opts?.sort ?? DEFAULT_EVIDENCE_SORT;
  return rows
    .filter((row) => (period ? chronoText(row.period) === period : true))
    .filter((row) => (metric ? chronoText(row.metric) === metric : true))
    .sort((a, b) => compareEvidence(a, b, sort));
}

/** 1 = low end of the thread range, 5 = high end. A flat range is the middle shade. */
export function heatLevel(value: number, min: number, max: number): 1 | 2 | 3 | 4 | 5 {
  if (!Number.isFinite(value) || !Number.isFinite(min) || !Number.isFinite(max) || max === min) {
    return 3;
  }
  const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
  return (Math.floor(t * 4) + 1) as 1 | 2 | 3 | 4 | 5;
}

export type InYearDirection = "none" | "raised" | "cut" | "unchanged" | "mixed";
export type InYearStep = "raised" | "cut" | "unchanged";

export function readInYearRevision(o: {
  guided_low?: number | null;
  guided_high?: number | null;
  guided_value: number;
  metric?: string;
  revisions?: Array<{ guided_low: number; guided_high: number }> | null;
}): { direction: InYearDirection; steps: InYearStep[]; finalBand: string; path: string } {
  const opening = formatGuidedBand(o);
  const revisions = o.revisions ?? [];
  if (revisions.length === 0) {
    return { direction: "none", steps: [], finalBand: opening, path: opening };
  }
  let prev = bandMid(o.guided_low, o.guided_high, o.guided_value);
  const steps: InYearStep[] = [];
  const bands = [opening];
  for (const rev of revisions) {
    const mid = (rev.guided_low + rev.guided_high) / 2;
    steps.push(mid > prev + 1e-9 ? "raised" : mid < prev - 1e-9 ? "cut" : "unchanged");
    prev = mid;
    bands.push(
      formatGuidedBand({
        guided_low: rev.guided_low,
        guided_high: rev.guided_high,
        guided_value: mid,
        metric: o.metric,
      }),
    );
  }
  const raised = steps.some((step) => step === "raised");
  const cut = steps.some((step) => step === "cut");
  const direction: InYearDirection = raised && cut ? "mixed" : raised ? "raised" : cut ? "cut" : "unchanged";
  return {
    direction,
    steps,
    finalBand: bands[bands.length - 1] ?? opening,
    path: bands.join(" → "),
  };
}

export type RevisionCandle = {
  low: number;
  high: number;
  open: number;
  close: number;
  ticks: number[];
  direction: "raised" | "cut" | "unchanged";
};

/** Opening band through each in-year revision, for a vertical range at the period. */
export function revisionCandle(o: {
  guided_low?: number | null;
  guided_high?: number | null;
  guided_value: number;
  revisions?: Array<{ guided_low: number; guided_high: number }> | null;
}): RevisionCandle | null {
  const revisions = o.revisions ?? [];
  if (revisions.length === 0) return null;
  const open = bandMid(o.guided_low, o.guided_high, o.guided_value);
  const lows: number[] = [];
  const highs: number[] = [];
  if (o.guided_low != null && o.guided_high != null) {
    lows.push(o.guided_low);
    highs.push(o.guided_high);
  } else {
    lows.push(open);
    highs.push(open);
  }
  const ticks = [open];
  for (const rev of revisions) {
    lows.push(rev.guided_low);
    highs.push(rev.guided_high);
    ticks.push((rev.guided_low + rev.guided_high) / 2);
  }
  const close = ticks[ticks.length - 1] ?? open;
  const direction: RevisionCandle["direction"] =
    close > open + 1e-9 ? "raised" : close < open - 1e-9 ? "cut" : "unchanged";
  return {
    low: Math.min(...lows),
    high: Math.max(...highs),
    open,
    close,
    ticks,
    direction,
  };
}

function bandMid(low?: number | null, high?: number | null, value?: number): number {
  if (low != null && high != null) return (low + high) / 2;
  return value ?? 0;
}

/** Period rank, then result date. Unknown labels sort last in either direction. */
function periodOrder(
  a: { period?: unknown; as_of?: unknown },
  b: { period?: unknown; as_of?: unknown },
  latestFirst: boolean,
): number {
  const ka = periodRank(chronoText(a.period));
  const kb = periodRank(chronoText(b.period));
  if (ka == null && kb == null) {
    const byLabel = chronoText(b.period).localeCompare(chronoText(a.period));
    if (byLabel !== 0) return byLabel;
  } else if (ka == null || kb == null) {
    return ka == null ? 1 : -1;
  } else if (ka !== kb) {
    return latestFirst ? kb - ka : ka - kb;
  }
  const byAsOf = chronoText(a.as_of).localeCompare(chronoText(b.as_of));
  if (byAsOf !== 0) return latestFirst ? -byAsOf : byAsOf;
  return 0;
}

const CLOSED_LABELS = new Set(["met", "exceeded", "missed"]);

export type RecordParts = {
  metOrBeat: number;
  closed: number;
  missedClause: string;
  metricLabel: string;
};

export function buildRecordParts(
  outcomes: Array<{
    metric: string;
    period: string;
    label: string;
    actual_value: number | null;
  }>,
): RecordParts {
  const closedRows = outcomes.filter(
    (o) => o.actual_value != null && CLOSED_LABELS.has(o.label),
  );
  const revenue = closedRows.filter((o) => o.metric.includes("revenue"));
  const focus = revenue.length ? revenue : closedRows;
  const missed = focus
    .filter((o) => o.label === "missed")
    .map((o) => o.period)
    .sort();
  const metOrBeat = focus.filter((o) => o.label === "met" || o.label === "exceeded").length;
  const metricId = focus[0]?.metric || "";
  return {
    metOrBeat,
    closed: focus.length,
    missedClause: missed.length ? `; missed ${missed.join(", ")}` : "",
    metricLabel: metricId ? metricDisplayName(metricId) : "guidance",
  };
}

/** English record sentence for SEO / OG (locale-independent). */
export function englishRecordSentence(parts: RecordParts): string {
  if (parts.closed === 0) return "No closed, dual-cited results yet.";
  return `Met or beat ${parts.metricLabel} guidance in ${parts.metOrBeat} of ${parts.closed} closed years${parts.missedClause}.`;
}
