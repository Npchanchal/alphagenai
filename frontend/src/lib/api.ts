export type CompanySummary = {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  gci_score: number | null;
  data_quality?: string;
  peer_rank_in_sector?: number | null;
  sector_avg_gci?: number | null;
  gci_change_pct?: number | null;
  gci_change_horizon?: string | null;
  wow_pct?: number | null;
  mom_pct?: number | null;
  qoq_pct?: number | null;
  yoy_pct?: number | null;
  market_id?: string | null;
  index_ids?: string[] | null;
  /** provisional | established | deep — null when not scored (W1.3). */
  confidence_tier?: ConfidenceTier | null;
  closed_periods?: number;
  metrics_scored?: number;
  as_of?: string | null;
  algorithm_id?: string | null;
  coverage_status?: CoverageStatus | null;
  /** Plain sentence shown instead of a number, e.g. "First guided year (FY27) closes Mar 2027". */
  coverage_reason?: string | null;
};

export type CoverageStatus =
  | "scored"
  | "open_period"
  | "filing_in_review"
  | "no_quantified_guidance"
  | "listed_only";

export type ConfidenceTier = "provisional" | "established" | "deep";

export type GuidanceRevision = {
  as_of: string;
  guided_low: number;
  guided_high: number;
  source_url?: string | null;
  source_ref?: string | null;
  quote?: string | null;
};

export type OutcomeView = {
  period: string;
  metric: string;
  /** Stored-row position. Review writes use this, not the on-screen order. */
  outcome_index?: number | null;
  guided_value: number;
  guided_low?: number | null;
  guided_high?: number | null;
  actual_value: number | null;
  delta_pct: number | null;
  guided_text: string;
  confidence: number;
  speaker: string;
  contribution_score: number | null;
  label: string;
  thread_id?: string | null;
  source_url?: string | null;
  source_ref?: string | null;
  quote_span?: string | null;
  as_of?: string | null;
  guidance_source_url?: string | null;
  guidance_source_ref?: string | null;
  guidance_quote?: string | null;
  guidance_as_of?: string | null;
  revisions?: GuidanceRevision[];
  revision_direction?: "raised" | "cut" | "unchanged" | null;
  final_guided_low?: number | null;
  final_guided_high?: number | null;
  final_label?: string | null;
  dropped?: boolean;
  actual_change_pct?: number | null;
  actual_change_horizon?: string | null;
  guided_change_pct?: number | null;
  guided_change_horizon?: string | null;
  citation_id?: string | null;
  doc_id?: string | null;
  citeable?: boolean;
  cite_reason?: string | null;
  span_start?: number | null;
  span_end?: number | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  reporting_basis?: string | null;
  actual_reporting_basis?: string | null;
  unit?: string | null;
  actual_unit?: string | null;
  scope?: string | null;
  actual_scope?: string | null;
};

export type CompanyGCIDetail = {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  gci_score: number | null;
  status: string;
  data_quality: string;
  /** Metrics in the composite. */
  by_metric: Record<string, number>;
  /** Metrics with < 2 closed periods — shown as context, not in the composite. */
  context_metrics?: Record<string, number>;
  periods_by_metric?: Record<string, number>;
  composite_weights?: Record<string, number>;
  label_counts: Record<string, number>;
  outcomes: OutcomeView[];
  trend: {
    period: string;
    gci_score: number | null;
    change_pct?: number | null;
    change_horizon?: string | null;
    prior_value?: number | null;
  }[];
  peer_rank_in_sector?: number | null;
  sector_avg_gci?: number | null;
  threads: Record<string, OutcomeView[]>;
  confidence_tier?: ConfidenceTier | null;
  closed_periods?: number;
  metrics_scored?: number;
  as_of?: string | null;
  reviewed_at?: string | null;
  algorithm_id?: string | null;
  coverage_status?: CoverageStatus | null;
  coverage_reason?: string | null;
  gci_change_pct?: number | null;
  gci_change_horizon?: string | null;
  by_metric_changes?: Record<
    string,
    {
      value?: number | null;
      mom_pct?: number | null;
      qoq_pct?: number | null;
      yoy_pct?: number | null;
      pop_pct?: number | null;
    }
  >;
  audit_flags?: string[];
  audit_deduction?: number;
  audit_badges?: Array<{
    flag: string;
    label: string;
    points: number;
    severity: string;
    set_by?: string;
    source_url?: string;
    set_at?: string;
    note?: string;
  }>;
  red_alerts?: Array<{
    company_id: string;
    ticker: string;
    kind: string;
    message: string;
    severity: string;
    period?: string;
    metric?: string;
    source_url?: string | null;
  }>;
  revision_timeline?: Array<{
    as_of?: string;
    period?: string;
    metric?: string;
    kind?: string;
    label?: string;
    detail?: string;
    severity?: string;
    source_url?: string | null;
  }>;
  revision_summaries?: Array<{
    period: string;
    metric: string;
    count: number;
    direction: "raised" | "cut" | "unchanged" | string;
    average_abs_move: number;
  }>;
  guidance_profile?: GuidanceProfile | null;
  audit_note?: string | null;
};

export type GuidanceProfilePart = {
  label: string | null;
  label_text: string | null;
  sentence: string;
};

/** Descriptive record next to the GCI. Labels appear from `min_for_label` closed figures. */
export type GuidanceProfile = {
  closed_figures: number;
  min_for_label: number;
  results_vs_range: GuidanceProfilePart & {
    above: number;
    inside: number;
    below: number;
    bias_index: number | null;
  };
  in_year_revisions: GuidanceProfilePart & {
    revised: number;
    toward_weaker: number;
    toward_stronger: number;
  };
  divergences: Array<{
    period: string;
    kind: "revenue_above_margin_below" | "margin_above_revenue_below" | string;
    metrics: string[];
    sentence: string;
    sources: string[];
  }>;
  note: string;
};

export type AlertItem = {
  company_id: string;
  ticker: string;
  kind: string;
  message: string;
  severity: string;
  period?: string | null;
  metric?: string | null;
  source_url?: string | null;
  audit_flag?: string | null;
  deduction_pts?: number | null;
};

export type ResearchDoc = {
  id?: string;
  company_id: string;
  ticker: string;
  name?: string;
  doc_type: string;
  title: string;
  date: string;
  source?: string;
  url?: string | null;
  snippet: string;
  body?: string;
  score?: number;
};

export type CitationRecord = {
  citation_id?: string | null;
  kind?: string;
  n?: number | null;
  company_id?: string | null;
  ticker?: string | null;
  name?: string | null;
  title?: string | null;
  date?: string | null;
  source_url?: string | null;
  url?: string | null;
  quote?: string | null;
  quote_span?: string | null;
  snippet?: string | null;
  speaker?: string | null;
  doc_id?: string | null;
  doc_type?: string | null;
  period?: string | null;
  metric?: string | null;
  span_start?: number | null;
  span_end?: number | null;
  locator?: string | null;
  citeable?: boolean;
  cite_reason?: string | null;
  bibliographic?: string;
  markdown?: string;
  ic_footnote?: string;
  permalink?: string | null;
  retrieved_at?: string | null;
  document_text?: string | null;
  document_title?: string | null;
  highlight_url?: string | null;
  excerpt_only?: boolean;
  indexed_excerpt?: boolean;
};

export type ResearchSnapshot = {
  company_id: string;
  name: string;
  ticker: string;
  sector: string;
  market: {
    last: number;
    change_pct: number;
    mom_pct?: number | null;
    qoq_pct?: number | null;
    yoy_pct?: number | null;
    mkt_cap_cr: number;
    volume: number;
    note: string;
  };
  gci: {
    score: number | null;
    change_pct?: number | null;
    change_horizon?: string | null;
    label_counts: Record<string, number>;
    peer_rank_in_sector?: number | null;
    sector_avg_gci?: number | null;
    data_quality: string;
    trend?: {
      period: string;
      gci_score: number | null;
      change_pct?: number | null;
      change_horizon?: string | null;
    }[];
  };
  fundamentals_demo: Record<
    string,
    | number
    | {
        value?: number | null;
        mom_pct?: number | null;
        qoq_pct?: number | null;
        yoy_pct?: number | null;
        pop_pct?: number | null;
        pop_horizon?: string | null;
        history?: { period?: string; value?: number | null }[];
      }
  >;
};

export type ResearchEstimateRow = {
  period: string;
  metric: string;
  street_consensus: number | null;
  street_source?: string;
  management_guidance: number;
  guided_band: (number | null)[];
  actual: number | null;
  gci_label: string;
  vs_street_pct: number | null;
  actual_change_pct?: number | null;
  actual_change_horizon?: string | null;
  management_guidance_change_pct?: number | null;
  management_guidance_change_horizon?: string | null;
  street_consensus_change_pct?: number | null;
  street_consensus_change_horizon?: string | null;
};

export type WatchlistItem = {
  company_id: string;
  ticker: string;
  name: string;
  sector: string;
  gci_score: number | null;
  gci_change_pct?: number | null;
  gci_change_horizon?: string | null;
  last: number;
  change_pct: number;
  mom_pct?: number | null;
  qoq_pct?: number | null;
  yoy_pct?: number | null;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const API_KEY = import.meta.env.VITE_API_KEY ?? "intellens-demo";

export class ApiError extends Error {
  status: number;
  code?: string;
  retail_marketing_allowed?: boolean;
  detail?: unknown;

  constructor(
    message: string,
    opts: {
      status: number;
      code?: string;
      retail_marketing_allowed?: boolean;
      detail?: unknown;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.retail_marketing_allowed = opts.retail_marketing_allowed;
    this.detail = opts.detail;
  }
}

function throwFromResponse(status: number, body: unknown): never {
  if (status === 429) {
    const wait = Number((body as { retry_after_sec?: unknown } | null)?.retry_after_sec);
    const secs = Number.isFinite(wait) && wait > 0 ? Math.ceil(wait) : 60;
    throw new ApiError(
      `Too many requests right now — please wait about ${secs} seconds and try again.`,
      { status, code: "rate_limited", detail: body },
    );
  }
  const raw = (body as { detail?: unknown } | null)?.detail;
  if (typeof raw === "string") {
    throw new ApiError(raw, { status, detail: raw });
  }
  if (raw && typeof raw === "object") {
    const d = raw as { message?: string; code?: string; retail_marketing_allowed?: boolean };
    throw new ApiError(d.message || `Request failed: ${status}`, {
      status,
      code: d.code,
      retail_marketing_allowed: d.retail_marketing_allowed,
      detail: raw,
    });
  }
  throw new ApiError(`Request failed: ${status}`, { status, detail: body });
}

/** Seconds to wait before retrying, when `e` is a 429 from the API; otherwise null. */
export function rateLimitRetrySeconds(e: unknown): number | null {
  if (!(e instanceof ApiError) || e.status !== 429) return null;
  const wait = Number((e.detail as { retry_after_sec?: unknown } | null)?.retry_after_sec);
  return Number.isFinite(wait) && wait > 0 ? Math.ceil(wait) : 60;
}

/** Retry once after the server's Retry-After when rate-limited. */
export async function withRateLimitRetry<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    const secs = rateLimitRetrySeconds(e);
    if (secs == null) throw e;
    await new Promise((resolve) => window.setTimeout(resolve, secs * 1000));
    return fn();
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  try {
    const tkn = localStorage.getItem("intellens.auth.token");
    if (tkn && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${tkn}`);
    }
  } catch {
    /* ignore */
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    throwFromResponse(res.status, body);
  }
  return res.json() as Promise<T>;
}

export function recordCiteCopy(companyId?: string): void {
  void getJson("/api/activity/cite-copy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId || null }),
  }).catch(() => undefined);
}

export function fetchCompanies(opts?: {
  market?: string;
  index?: string;
  limit?: number;
  offset?: number;
  scored?: boolean;
}): Promise<CompanySummary[]> {
  const params = new URLSearchParams();
  if (opts?.market) params.set("market", opts.market);
  if (opts?.index) params.set("index", opts.index);
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  if (opts?.scored) params.set("scored", "true");
  const qs = params.toString();
  return getJson(`/api/companies${qs ? `?${qs}` : ""}`);
}

export function fetchCompaniesCount(opts?: {
  market?: string;
  index?: string;
}): Promise<{ count: number; market?: string; index?: string }> {
  const params = new URLSearchParams();
  if (opts?.market) params.set("market", opts.market);
  if (opts?.index) params.set("index", opts.index);
  const qs = params.toString();
  return getJson(`/api/companies/count${qs ? `?${qs}` : ""}`);
}

export function fetchCompanyGci(id: string): Promise<CompanyGCIDetail> {
  return getJson(`/api/companies/${id}/gci`);
}

export function searchCompanies(
  q: string,
  limit = 20,
  facets?: {
    exchange?: string;
    sector?: string;
    data_quality?: string;
    corpus_status?: string;
  }
): Promise<{
  q: string;
  count: number;
  facets?: Record<string, string | null | undefined>;
  results: Array<{
    id: string;
    name: string;
    ticker: string;
    sector: string;
    gci_score: number | null;
    data_quality?: string;
    exchange?: string;
    doc_count?: number;
    citeable_outcomes?: number;
    corpus_status?: string;
  }>;
}> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (facets?.exchange) params.set("exchange", facets.exchange);
  if (facets?.sector) params.set("sector", facets.sector);
  if (facets?.data_quality) params.set("data_quality", facets.data_quality);
  if (facets?.corpus_status) params.set("corpus_status", facets.corpus_status);
  return getJson(`/api/companies/search?${params}`);
}

export function fetchSectorLeaderboard(opts?: {
  market?: string;
  index?: string;
  limit?: number;
}): Promise<{
  market?: string;
  index?: string;
  count: number;
  published_count?: number;
  min_names?: number;
  sectors: Array<{
    sector: string;
    avg: number | null;
    count: number;
    min_names?: number;
    best: { id: string; ticker: string; name: string; gci_score: number | null } | null;
    names?: Array<{ id: string; ticker: string; name: string; confidence_tier?: string | null }>;
  }>;
}> {
  const params = new URLSearchParams();
  if (opts?.market) params.set("market", opts.market);
  if (opts?.index) params.set("index", opts.index);
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return getJson(`/api/sectors/leaderboard${qs ? `?${qs}` : ""}`);
}

export function fetchCompanyChanges(id: string): Promise<{
  company_id: string;
  wow_pct?: number | null;
  mom_pct?: number | null;
  qoq_pct?: number | null;
  yoy_pct?: number | null;
  pop_pct?: number | null;
  pop_horizon?: string | null;
  /** citeable_pit | citeable_pit_short | insufficient_history | not_yet_scored */
  series_kind?: string | null;
  series_n?: number | null;
  citeable?: boolean;
  note?: string | null;
}> {
  return getJson(`/api/companies/${id}/changes`);
}

export function fetchCompanyAnalytics(id: string): Promise<{
  company_id: string;
  dependent?: string;
  independents?: string[];
  gci_price_corr?: number | null;
  lead_lag_gci_vs_price?: {
    best?: { lag: number; corr: number | null } | null;
    lags: Array<{ lag: number; corr: number | null }>;
  };
  correlation_matrix?: {
    variables: string[];
    matrix: Record<string, Record<string, number | null>>;
  };
  impact_factors?: Array<{
    factor: string;
    score: number;
    impact_vs_gci: number;
  }>;
  sample_n?: number;
  window_label?: string;
  experimental?: boolean;
  show_experimental_ui?: boolean;
  methodology?: string;
  note?: string;
  series_kind?: string;
  citeable?: boolean;
  pit_as_of?: string[];
  granger?: {
    enabled?: boolean;
    disclaimer?: string;
    sample_n?: number;
    var_ready?: boolean;
    lasso_selected?: Array<{ factor: string; coef?: number; corr?: number | null }>;
    granger_tests?: Array<{
      factor?: string;
      ok?: boolean;
      reason?: string;
      f_stat?: number;
      p_value?: number;
      significant_0_05?: boolean;
      best?: { lag?: number; corr?: number | null };
      method?: string;
    }>;
    impact_map?: Array<{
      from?: string;
      to?: string;
      weight?: number;
      p_value?: number;
      lag?: number;
    }>;
  };
}> {
  return getJson(`/api/companies/${id}/analytics`);
}

export function fetchCompanyDocs(
  id: string,
  period?: string
): Promise<{
  company_id: string;
  count: number;
  documents: Array<Record<string, unknown>>;
  completeness?: {
    periods: Array<{
      period: string;
      status: string;
      doc_count: number;
      expected_types?: string[];
      types_complete?: boolean;
      type_coverage?: Record<string, boolean>;
      documents?: Array<Record<string, unknown>>;
    }>;
    summary?: {
      accepted_periods: number;
      total_periods: number;
      complete: boolean;
      citeable_bound_outcomes?: number;
      citeable_pct?: number;
      types_complete_periods?: number;
      tier1_gate?: boolean;
    };
    note?: string;
  };
}> {
  const params = new URLSearchParams();
  if (period) params.set("period", period);
  const qs = params.toString();
  return getJson(`/api/companies/${id}/docs${qs ? `?${qs}` : ""}`);
}

export function fetchNotes(companyId?: string): Promise<{
  notes: Array<{ id: string; title: string; body: string; company_id: string }>;
}> {
  const params = new URLSearchParams();
  if (companyId) params.set("company_id", companyId);
  const qs = params.toString();
  return getJson(`/api/notes${qs ? `?${qs}` : ""}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postNote(body: {
  company_id: string;
  title?: string;
  body: string;
  id?: string;
}): Promise<unknown> {
  return getJson("/api/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

export function fetchReportTemplates(): Promise<{
  templates: Array<{ id: string; name: string; role: string; industry: string }>;
}> {
  return getJson("/api/reports/templates");
}

export function postGenerateReport(body: {
  company_id: string;
  template_id: string;
  format?: "markdown" | "json" | "pdf";
}): Promise<{
  markdown?: string;
  template_name: string;
  format?: string;
  dossier?: Record<string, unknown>;
  citeable_count?: number;
  pdf_base64?: string;
}> {
  return getJson("/api/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

/** Download IC audit PDF (binary response). */
export async function downloadIcAuditPdf(companyId: string): Promise<Blob> {
  const res = await fetch("/api/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({
      company_id: companyId,
      template_id: "ic_audit",
      format: "pdf",
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `PDF export failed (${res.status})`);
  }
  return res.blob();
}

export function fetchOpsThroughput(): Promise<{
  universe: Record<string, number>;
  backlog: Record<string, number>;
  throughput_hints: { next_actions: string[]; bottlenecks: string[] };
  note?: string;
}> {
  return getJson("/api/ops/throughput", { headers: { "X-API-Key": API_KEY } });
}

export function fetchPilotChecklist(orgId: string): Promise<{
  org_id: string;
  progress: { done: number; total: number; pct: number };
  items: Array<{ id: string; phase: string; label: string; done: boolean }>;
  convert_intent: string | null;
  target_sku: string | null;
  conversion_ready: boolean;
  next_step: string;
  success_metrics: Record<string, string | number>;
  notes?: string;
  activity?: {
    feedback_logged?: number;
    quality_feedback?: number;
    convert_intent?: number;
    citations_in_notes?: number;
    citations_copied?: number;
    dossier_opens?: number;
  };
}> {
  return getJson(`/api/orgs/${encodeURIComponent(orgId)}/pilot-checklist`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function patchPilotChecklist(
  orgId: string,
  body: {
    item_id?: string;
    done?: boolean;
    notes?: string;
    convert_intent?: string;
    target_sku?: string;
  },
): Promise<Record<string, unknown>> {
  return getJson(`/api/orgs/${encodeURIComponent(orgId)}/pilot-checklist`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

export function postProvisionPilot(body: {
  name: string;
  owner_email?: string;
  seats?: number;
}): Promise<{ org: { id: string; name: string; plan: string }; checklist: unknown }> {
  return getJson("/api/orgs/pilot", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

export type PublicRankingRow = {
  rank: number;
  ticker: string;
  name: string;
  sector: string;
  gci_score: number;
  citeable_outcomes: number;
  company_id: string;
  confidence_tier?: ConfidenceTier | null;
  closed_periods?: number;
  metrics_scored?: number;
  as_of?: string | null;
  algorithm_id?: string | null;
};

export type SnapshotRecordRow = {
  company_id: string;
  ticker: string;
  name: string;
  confidence_tier?: ConfidenceTier | null;
  gci_score?: number | null;
  met: number;
  exceeded: number;
  missed: number;
  as_of?: string | null;
  closed_periods?: number;
};

export function fetchPublicGciRankings(opts?: {
  limit?: number;
  format?: "json" | "markdown";
  index?: string;
}): Promise<{
  title: string;
  as_of: string;
  index?: string;
  universe_n: number;
  mode?: "ranked" | "record";
  ranked_threshold?: number;
  records?: SnapshotRecordRow[];
  tiers_ranked?: string[];
  top: PublicRankingRow[];
  bottom: PublicRankingRow[];
  methodology: string;
  legal: string;
  markdown?: string;
}> {
  const params = new URLSearchParams();
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.format) params.set("format", opts.format);
  if (opts?.index) params.set("index", opts.index);
  const qs = params.toString();
  return getJson(`/api/public/gci-rankings${qs ? `?${qs}` : ""}`);
}

// --- Index integrity: score ledger + public changelog (W1.6 / W1.7) ---

export type ScoreLedgerRow = {
  company_id: string;
  as_of: string;
  algorithm_id: string;
  dataset_version: string;
  gci: number | null;
  prior_gci: number | null;
  confidence_tier: ConfidenceTier | null;
  reason: string;
  note: string;
  by: string;
};

export function fetchScoreLedger(
  companyId?: string,
  limit = 200,
): Promise<{ company_id: string | null; count: number; rows: ScoreLedgerRow[]; note: string }> {
  const params = new URLSearchParams();
  if (companyId) params.set("company_id", companyId);
  params.set("limit", String(limit));
  return getJson(`/api/v1/index/ledger?${params.toString()}`);
}

export type ChangelogEntry = {
  date: string;
  reason: string;
  companies: string[];
  change: string;
};

export function fetchScoreChangelog(
  companyId?: string,
): Promise<{ company_id: string | null; count: number; entries: ChangelogEntry[] }> {
  const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
  return getJson(`/api/v1/index/changelog${qs}`);
}

export function fetchPitContract(): Promise<Record<string, unknown>> {
  return getJson("/api/v1/pit/contract");
}

export function fetchPitHistoryV1(companyId: string): Promise<{
  contract_version: string;
  series_kind: string;
  citeable: boolean;
  points: Array<{ as_of: string; gci_score: number | null }>;
  note?: string;
}> {
  return getJson(`/api/v1/pit/companies/${encodeURIComponent(companyId)}/history`);
}

export function postEnsureCitations(opts?: {
  company_id?: string;
  limit?: number;
}): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (opts?.company_id) params.set("company_id", opts.company_id);
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return getJson(`/api/ingest/ensure-citations${qs ? `?${qs}` : ""}`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });
}

export function postTierFoundation(limit?: number): Promise<{
  ok: boolean;
  citations?: Record<string, unknown>;
  pit_warehouse?: Record<string, unknown>;
}> {
  const qs = limit != null ? `?limit=${limit}` : "";
  return getJson(`/api/ingest/tier-foundation${qs}`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });
}

export function fetchSectorBenchmark(sector: string): Promise<{
  sector: string;
  company_count: number;
  avg_gci: number | null;
  companies: CompanySummary[];
}> {
  return getJson(`/api/sectors/${encodeURIComponent(sector)}/benchmark`);
}

export function fetchAlerts(): Promise<AlertItem[]> {
  return getJson("/api/alerts");
}

export type PortfolioProduct = {
  id: string;
  name: string;
  job: string;
  status: string;
  buyer: string;
  endpoints: string[];
  ui: string[];
  docs: string;
};

export function fetchProductsCatalog(): Promise<{
  product: string;
  entity: string;
  note: string;
  disclaimer: string;
  catalog_doc: string;
  roadmap_doc: string;
  products: PortfolioProduct[];
}> {
  return getJson("/api/products");
}

export type SightsMeta = {
  product: string;
  sku_id: string;
  enabled: boolean;
  job: string;
  flags: Record<string, boolean>;
  brand_map: Record<string, string>;
  refuse: string[];
  enterprise: Record<string, string>;
  stretch: Record<string, string>;
  disclaimer: string;
};

export function fetchSightsMeta(): Promise<SightsMeta> {
  return getJson("/api/sights/meta");
}

export function fetchSightsThemes(opts?: {
  companyId?: string;
  sector?: string;
  limit?: number;
}): Promise<{
  product: string;
  themes: { theme: string; count: number; kind: string; note: string }[];
  metric_themes: { metric: string; labels: Record<string, number>; dominant: string | null }[];
  sample_rows: Record<string, unknown>[];
  disclaimer?: string;
}> {
  const params = new URLSearchParams();
  if (opts?.companyId) params.set("company_id", opts.companyId);
  if (opts?.sector) params.set("sector", opts.sector);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return getJson(`/api/sights/themes${qs ? `?${qs}` : ""}`);
}

export function fetchSightsStreet(companyId: string): Promise<{
  product: string;
  company_id: string;
  note: string;
  estimates: unknown;
  public_filing_snippets: {
    id?: string;
    title?: string;
    date?: string;
    snippet?: string;
    url?: string;
    doc_type?: string;
  }[];
  disclaimer?: string;
}> {
  return getJson(`/api/sights/street/${encodeURIComponent(companyId)}`);
}

export function fetchSightsField(companyId: string): Promise<{
  product: string;
  company_id: string;
  ticker: string;
  name: string;
  data_quality: string;
  gci_score: number | null;
  outcomes: Record<string, unknown>[];
  citations: CitationRecord[];
  empty_demo?: boolean;
  note: string;
  disclaimer?: string;
}> {
  return getJson(`/api/sights/field/${encodeURIComponent(companyId)}`);
}

export function postSightsGrid(body: {
  prompts: string[];
  company_ids?: string[];
}): Promise<{
  product: string;
  company_ids: string[];
  rows: {
    prompt: string;
    cells: {
      company_id: string;
      answer?: string;
      refused: boolean;
      citations: CitationRecord[];
    }[];
  }[];
  refused?: boolean;
  message?: string;
  disclaimer?: string;
}> {
  return getJson("/api/sights/grid", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postSightsDeepDive(body: {
  topic: string;
  company_id?: string;
}): Promise<{
  product: string;
  topic?: string;
  refused: boolean;
  message?: string;
  steps: { step: number; query: string; refused: boolean; answer?: string; citations: CitationRecord[] }[];
  report?: string | null;
  citations?: CitationRecord[];
  disclaimer?: string;
}> {
  return getJson("/api/sights/deep-dive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchSightsFundamentals(companyId: string): Promise<{
  product: string;
  company_id: string;
  snapshot: ResearchSnapshot;
  note: string;
  disclaimer?: string;
}> {
  return getJson(`/api/sights/fundamentals/${encodeURIComponent(companyId)}`);
}

// ── CiteAlpha Analyst (cited research agent) ─────────────────────────────────

export type AnalystSkill = {
  id: string;
  version: string;
  title: string;
  audience?: string;
  description?: string;
  inputs?: string[];
  requires_project?: boolean;
};

export type AnalystClaim = {
  text: string;
  cites: number[];
  kind: "quoted" | "computed" | "record";
};

export type AnalystSection = {
  id: string;
  title: string;
  claims: AnalystClaim[];
  empty?: string | null;
};

export type AnalystCitation = {
  n: number;
  kind?: string;
  title?: string | null;
  quote?: string | null;
  source_url?: string | null;
  date?: string | null;
  period?: string | null;
  permalink?: string | null;
};

export type AnalystRun = {
  run_id: string;
  engine: string;
  skill: { id: string; version: string; title: string; description?: string };
  company_id: string;
  company_name: string;
  ticker: string;
  as_of: string;
  generated_at: string;
  headline?: string | null;
  sections: AnalystSection[];
  not_found: string[];
  citations: AnalystCitation[];
  refused: boolean;
  verifier: { kept: number; removed: number };
  llm: { used: boolean; model?: string };
  includes_unreviewed: boolean;
  trigger?: { doc_id: string; title?: string | null; date?: string | null; url?: string | null } | null;
  project?: { project_id: string; name: string; memory_items: number } | null;
  disclaimer: string;
  markdown: string;
  evidence_receipt: Record<string, unknown>;
};

export type AnalystRunSummary = {
  run_id: string;
  skill_id: string;
  skill_title: string;
  company_id: string;
  company_name: string;
  generated_at: string;
  claims_kept: number;
  claims_removed: number;
  monitor_id?: string | null;
  trigger?: { doc_id: string; title?: string | null; date?: string | null; doc_type?: string | null } | null;
};

export type AnalystMonitorScope = "company" | "watchlist" | "project";

export type AnalystMonitor = {
  monitor_id: string;
  scope?: AnalystMonitorScope;
  company_id?: string | null;
  project_id?: string | null;
  user_id?: string | null;
  skill_id: string;
  email?: string | null;
  created_at: string;
  last_run_id?: string | null;
  last_triggered_at?: string | null;
};

export type AnalystUpload = {
  upload_id: string;
  filename: string;
  kind: string;
  bytes: number;
  passages: number;
  uploaded_at: string;
};

export type AnalystProject = {
  project_id: string;
  name: string;
  company_ids: string[];
  memory: { id: string; text: string; created_at: string }[];
  models?: { model_id: string; name: string; figure: number; unit: string; as_of: string; statement: string }[];
  uploads: AnalystUpload[];
  created_at: string;
};

const analystHeaders = () => ({ "Content-Type": "application/json", "X-API-Key": API_KEY });

export function fetchAnalystProjects(): Promise<{ projects: AnalystProject[] }> {
  return getJson("/api/analyst/projects", { headers: { "X-API-Key": API_KEY } });
}

export function postAnalystProject(body: { name: string; company_ids: string[] }): Promise<AnalystProject> {
  return getJson("/api/analyst/projects", { method: "POST", headers: analystHeaders(), body: JSON.stringify(body) });
}

export function deleteAnalystProject(projectId: string): Promise<{ deleted: string }> {
  return getJson(`/api/analyst/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
    headers: { "X-API-Key": API_KEY },
  });
}

export function postAnalystMemory(projectId: string, text: string): Promise<{ id: string }> {
  return getJson(`/api/analyst/projects/${encodeURIComponent(projectId)}/memory`, {
    method: "POST",
    headers: analystHeaders(),
    body: JSON.stringify({ text }),
  });
}

export function deleteAnalystMemory(projectId: string, memoryId: string): Promise<{ deleted: string }> {
  return getJson(
    `/api/analyst/projects/${encodeURIComponent(projectId)}/memory/${encodeURIComponent(memoryId)}`,
    { method: "DELETE", headers: { "X-API-Key": API_KEY } },
  );
}

export function postAnalystUpload(
  projectId: string,
  body: { filename: string; content_base64: string },
): Promise<AnalystUpload> {
  return getJson(`/api/analyst/projects/${encodeURIComponent(projectId)}/uploads`, {
    method: "POST",
    headers: analystHeaders(),
    body: JSON.stringify(body),
  });
}

export function deleteAnalystUpload(projectId: string, uploadId: string): Promise<{ deleted: string }> {
  return getJson(
    `/api/analyst/projects/${encodeURIComponent(projectId)}/uploads/${encodeURIComponent(uploadId)}`,
    { method: "DELETE", headers: { "X-API-Key": API_KEY } },
  );
}

export function fetchAnalystMonitors(): Promise<{ monitors: AnalystMonitor[]; limit: number }> {
  return getJson("/api/analyst/monitors", { headers: { "X-API-Key": API_KEY } });
}

export function postAnalystMonitor(body: {
  skill_id: string;
  scope?: AnalystMonitorScope;
  company_id?: string;
  project_id?: string;
  email?: string;
}): Promise<AnalystMonitor> {
  return getJson("/api/analyst/monitors", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

export function deleteAnalystMonitor(monitorId: string): Promise<{ deleted: string }> {
  return getJson(`/api/analyst/monitors/${encodeURIComponent(monitorId)}`, {
    method: "DELETE",
    headers: { "X-API-Key": API_KEY },
  });
}

export function fetchAnalystFeed(): Promise<{ runs: AnalystRunSummary[] }> {
  return getJson("/api/analyst/feed", { headers: { "X-API-Key": API_KEY } });
}

export function fetchAnalystSkills(): Promise<{ product: string; skills: AnalystSkill[] }> {
  return getJson("/api/analyst/skills", { headers: { "X-API-Key": API_KEY } });
}

export function postAnalystRun(body: {
  skill_id: string;
  company_id: string;
  include_unreviewed?: boolean;
  project_id?: string;
}): Promise<AnalystRun> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  try {
    const tkn = localStorage.getItem("intellens.auth.token");
    if (tkn) headers.Authorization = `Bearer ${tkn}`;
    else headers["X-API-Key"] = API_KEY;
  } catch {
    headers["X-API-Key"] = API_KEY;
  }
  return getJson("/api/analyst/run", {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}

export function fetchAnalystRuns(companyId?: string): Promise<{ runs: AnalystRunSummary[] }> {
  const q = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
  return getJson(`/api/analyst/runs${q}`, { headers: { "X-API-Key": API_KEY } });
}

export type AnalystExportFormat = "xlsx" | "pptx" | "pdf" | "md";

async function downloadAnalystFile(path: string, fallbackName: string): Promise<void> {
  const headers: Record<string, string> = { "X-API-Key": API_KEY };
  try {
    const tkn = localStorage.getItem("intellens.auth.token");
    if (tkn) headers.Authorization = `Bearer ${tkn}`;
  } catch {
    /* ignore */
  }
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) throw new Error((await res.text()) || `Download failed (${res.status})`);
  const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") || "")?.[1] || fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadAnalystExport(runId: string, format: AnalystExportFormat): Promise<void> {
  return downloadAnalystFile(
    `/api/analyst/runs/${encodeURIComponent(runId)}/export?format=${format}`,
    `citealpha-${runId}.${format}`
  );
}

export function downloadHouseStylePreview(): Promise<void> {
  return downloadAnalystFile("/api/analyst/house-style/preview", "citealpha-house-style-preview.pptx");
}

// ── Analyst settings: digest, org API keys, destinations, house style ───────

export type AnalystDigestSettings = { enabled: boolean; emails: string[]; last_sent_at?: string | null };

export function fetchAnalystDigest(): Promise<{ settings: AnalystDigestSettings; text: string }> {
  return getJson("/api/analyst/digest", { headers: { "X-API-Key": API_KEY } });
}

export function putAnalystDigest(body: { enabled: boolean; emails: string[] }): Promise<AnalystDigestSettings> {
  return getJson("/api/analyst/digest", {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
}

export type AnalystOrgKey = {
  key_id: string;
  label: string;
  role: "analyst" | "viewer";
  prefix: string;
  created_at: string;
  created_by?: string;
  last_used_at?: string | null;
};

export function fetchAnalystKeys(): Promise<{ keys: AnalystOrgKey[]; limit: number }> {
  return getJson("/api/analyst/keys");
}

export function postAnalystKey(body: { label: string; role: "analyst" | "viewer" }): Promise<AnalystOrgKey & { key: string; note: string }> {
  return getJson("/api/analyst/keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteAnalystKey(keyId: string): Promise<{ revoked: string }> {
  return getJson(`/api/analyst/keys/${encodeURIComponent(keyId)}`, { method: "DELETE" });
}

export type AnalystDestinationKind = "webhook" | "slack" | "teams";

export type AnalystDestination = {
  destination_id: string;
  kind: AnalystDestinationKind;
  label: string;
  url: string;
  events: string[];
  created_at: string;
  last_status?: number | null;
  last_delivered_at?: string | null;
  secret?: string;
};

export type AnalystDeliveryLogRow = {
  at: string;
  destination_id: string;
  kind: AnalystDestinationKind;
  event: string;
  status: number;
  ok: boolean;
  error?: string | null;
};

export function fetchAnalystDestinations(): Promise<{
  destinations: AnalystDestination[];
  log: AnalystDeliveryLogRow[];
  events: string[];
  kinds: AnalystDestinationKind[];
}> {
  return getJson("/api/analyst/destinations");
}

export function postAnalystDestination(body: {
  kind: AnalystDestinationKind;
  url: string;
  events: string[];
  label?: string;
}): Promise<AnalystDestination> {
  return getJson("/api/analyst/destinations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteAnalystDestination(destinationId: string): Promise<{ deleted: string }> {
  return getJson(`/api/analyst/destinations/${encodeURIComponent(destinationId)}`, { method: "DELETE" });
}

export function testAnalystDestination(destinationId: string): Promise<{ result: AnalystDeliveryLogRow | null }> {
  return getJson(`/api/analyst/destinations/${encodeURIComponent(destinationId)}/test`, { method: "POST" });
}

export type AnalystHouseStyle = {
  firm_name: string;
  primary_color: string;
  accent_color: string;
  font: string;
  footer: string;
  classification: string;
  has_logo: boolean;
  has_template: boolean;
  configured: boolean;
  fonts: string[];
};

export function fetchAnalystHouseStyle(): Promise<AnalystHouseStyle> {
  return getJson("/api/analyst/house-style", { headers: { "X-API-Key": API_KEY } });
}

export function putAnalystHouseStyle(
  body: Omit<AnalystHouseStyle, "has_logo" | "has_template" | "configured" | "fonts"> & { logo_base64?: string }
): Promise<AnalystHouseStyle> {
  return getJson("/api/analyst/house-style", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function resetAnalystHouseStyle(): Promise<AnalystHouseStyle> {
  return getJson("/api/analyst/house-style", { method: "DELETE" });
}

export function postAnalystHouseTemplate(body: { filename: string; content_base64: string }): Promise<AnalystHouseStyle> {
  return getJson("/api/analyst/house-style/template", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function clearAnalystHouseAsset(asset: "template" | "logo"): Promise<AnalystHouseStyle> {
  return getJson(`/api/analyst/house-style/${asset}`, { method: "DELETE" });
}

export function fetchAnalystRun(runId: string): Promise<AnalystRun> {
  return getJson(`/api/analyst/runs/${encodeURIComponent(runId)}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

// ── Commitment Record ────────────────────────────────────────────────────────

export type Commitment = {
  id: string;
  company_id: string;
  type: string;
  type_label: string;
  subject: string;
  outcome: string;
  due_period: string;
  due_date: string | null;
  quote: string;
  source_url: string;
  as_of: string;
  state: string;
  state_label: string;
  review_status: "unreviewed" | "accepted" | "rejected";
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  proof?: { quote?: string; source_url?: string; as_of?: string } | null;
};

export type CommitmentView = {
  company_id: string;
  as_of: string;
  summary: {
    due: number;
    delivered: number;
    awaiting_proof: number;
    open_not_yet_due: number;
    sentence: string;
  };
  commitments: Commitment[];
  includes_unreviewed: boolean;
  note: string;
};

export function fetchCompanyCommitments(
  companyId: string,
  opts?: { includeUnreviewed?: boolean },
): Promise<CommitmentView> {
  const q = opts?.includeUnreviewed ? "?include_unreviewed=true" : "";
  return getJson(`/api/companies/${encodeURIComponent(companyId)}/commitments${q}`);
}

export function fetchSightsEnterprise(): Promise<{
  product: string;
  links: Record<string, string>;
  sso_configured_flag: boolean;
  note: string;
  disclaimer?: string;
}> {
  return getJson("/api/sights/enterprise");
}

export type RadarFeedItem = {
  source: string;
  company_id: string;
  ticker: string;
  kind: string;
  message: string;
  severity: string;
  period?: string | null;
  metric?: string | null;
  source_url?: string | null;
  audit_flag?: string | null;
  deduction_pts?: number | null;
  as_of?: string | null;
};

export function fetchRadarFeed(opts?: {
  companyId?: string;
  limit?: number;
  includeRevisions?: boolean;
}): Promise<{
  product: string;
  company_id?: string | null;
  count: number;
  items: RadarFeedItem[];
  note: string;
  disclaimer: string;
}> {
  const q = new URLSearchParams();
  if (opts?.companyId) q.set("company_id", opts.companyId);
  if (opts?.limit != null) q.set("limit", String(opts.limit));
  if (opts?.includeRevisions === false) q.set("include_revisions", "false");
  const qs = q.toString();
  return getJson(`/api/radar/feed${qs ? `?${qs}` : ""}`);
}

export function fetchCompanyLedger(
  companyId: string,
  opts?: { creditOnly?: boolean; mirror?: boolean },
): Promise<{
  product: string;
  company_id: string;
  name: string;
  ticker: string;
  sector: string;
  data_quality?: string;
  gci_score?: number | null;
  filter?: string;
  mode?: string;
  summary: {
    closed_count: number;
    open_promise_count: number;
    by_status: Record<string, number>;
  };
  closed_promises: Record<string, unknown>[];
  open_promises: Record<string, unknown>[];
  note: string;
  disclaimer: string;
}> {
  const q = new URLSearchParams();
  if (opts?.creditOnly) q.set("credit_only", "true");
  if (opts?.mirror) q.set("mirror", "true");
  const qs = q.toString();
  return getJson(`/api/ledger/${encodeURIComponent(companyId)}${qs ? `?${qs}` : ""}`);
}

export function fetchDataCatalog(): Promise<{
  product: string;
  note: string;
  disclaimer: string;
  exports: { id: string; path: string; format: string; description: string }[];
  roadmap: string[];
  docs: string;
}> {
  return getJson("/api/data/catalog");
}

export function fetchRadarDiffBrief(companyId: string): Promise<{
  feature: string;
  company_id: string;
  ticker: string;
  count: number;
  diffs: {
    metric?: string;
    prior_period?: string;
    current_period?: string;
    band_delta?: number | null;
    kind: string;
    detail?: string;
    severity?: string;
  }[];
}> {
  return getJson(`/api/radar/diff/${encodeURIComponent(companyId)}`);
}

export function fetchRadarCalendar(limit = 15): Promise<{
  feature: string;
  count: number;
  windows: {
    company_id: string;
    ticker: string;
    open_promise_count: number;
    periods: string[];
  }[];
}> {
  return getJson(`/api/radar/calendar?limit=${limit}`);
}

export function fetchCiteTiers(): Promise<{
  tiers: { id: string; name: string; rpm: number; note: string }[];
}> {
  return getJson("/api/cite/tiers");
}

export function fetchVernacularDigest(
  companyId: string,
  lang = "hi",
): Promise<{ text: string; text_en: string; text_hi: string; sources: { url?: string }[] }> {
  return getJson(`/api/digest/vernacular/${encodeURIComponent(companyId)}?lang=${lang}`);
}

export function fetchNarrativeConsistency(companyId: string): Promise<{
  nci_score: number;
  conflicts: { kind: string; detail?: string }[];
  status: string;
  gate?: string;
  disclaimer?: string;
}> {
  return getJson(`/api/score/narrative-consistency/${encodeURIComponent(companyId)}`);
}

export async function downloadLedgerPdf(
  companyId: string,
  opts?: { creditOnly?: boolean },
): Promise<Blob> {
  const q = opts?.creditOnly ? "?credit_only=true" : "";
  const res = await fetch(`/api/ledger/${encodeURIComponent(companyId)}/pdf${q}`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Ledger PDF failed (${res.status})`);
  }
  return res.blob();
}

export function fetchLedgerMirror(companyId: string): Promise<{
  product: string;
  mode?: string;
  mirror_note?: string;
  ticker: string;
  summary: {
    closed_count: number;
    open_promise_count: number;
    by_status: Record<string, number>;
  };
  peer_context?: {
    sector?: string;
    sector_avg_gci?: number | null;
    peer_rank_in_sector?: number | null;
  };
  closed_promises: Record<string, unknown>[];
  open_promises: Record<string, unknown>[];
  disclaimer: string;
}> {
  return getJson(`/api/ledger/mirror/${encodeURIComponent(companyId)}`);
}

export function fetchCiteUsage(): Promise<{
  tier: string;
  citations_served_session: number;
  tier_detail?: { name: string; rpm: number; note: string };
  tiers: { id: string; name: string; rpm: number; note: string }[];
}> {
  return getJson("/api/cite/usage", { headers: { "X-API-Key": API_KEY } });
}

export async function downloadOutcomesExport(
  format: "json" | "csv" | "parquet" = "csv",
  limit = 200,
): Promise<Blob> {
  const headers: Record<string, string> = { "X-API-Key": API_KEY };
  try {
    const tkn = localStorage.getItem("intellens.auth.token");
    if (tkn) headers.Authorization = `Bearer ${tkn}`;
  } catch {
    /* ignore */
  }
  const res = await fetch(`${API_BASE}/api/data/export/outcomes?format=${format}&limit=${limit}`, {
    headers,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Export failed (${res.status})`);
  }
  return res.blob();
}

export function fetchKpiDictionary(sector?: string): Promise<{
  metric_count: number;
  families: Record<string, string[]>;
  metrics: { id: string; display_name: string; family: string }[];
}> {
  const qs = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return getJson(`/api/data/kpi-dictionary${qs}`);
}

export function fetchWorkbenchExtraction(): Promise<{
  product: string;
  status: string;
  pending_extract_batches: number;
  throughput: {
    backlog?: Record<string, number>;
    throughput_hints?: { bottlenecks?: string[]; next_actions?: string[] };
  };
  gate?: string;
}> {
  return getJson("/api/workbench/extraction", { headers: { "X-API-Key": API_KEY } });
}

export type FilingToScoreSla = {
  target_business_days: number;
  instrumentation_date?: string;
  unit?: string;
  scored_rows: number;
  observed_median_business_days: number | null;
  sample?: string;
  policy?: string;
  live?: {
    n: number;
    median_business_days: number | null;
    note?: string;
  };
  backfill?: {
    n: number;
    median_business_days: number | null;
    reviewed_on?: string;
    note?: string;
  };
};

export type ProductMeta = {
  version: string;
  published_gci_count?: number;
  published_ranked_count?: number;
  company_count: number;
  hand_labeled_count: number;
  demo_structured_count: number;
  gci_scored_count: number;
  gci_listing_scored_count: number;
  gci_listing_unscored_count?: number;
  sensex_scored_count?: number;
  sensex_count?: number;
  gci_algorithm: string;
  gci_listing_as_of?: string | null;
  feature_flags?: Record<string, boolean | string>;
  filing_to_score?: FilingToScoreSla;
};

export function fetchTrustBadgeChannel(ticker: string): Promise<{
  ticker: string;
  gci_score: number | null;
  embed_path: string;
  svg_path: string;
  gate?: string;
  disclaimer: string;
}> {
  return getJson(`/api/channel/trust-badge/${encodeURIComponent(ticker)}`);
}

export function fetchMetaFlags(): Promise<ProductMeta> {
  return fetchProductMeta();
}

export function fetchProductMeta(): Promise<ProductMeta> {
  return getJson("/api/meta");
}

export function fetchHistory(
  id: string
): Promise<
  {
    as_of: string;
    gci_score: number | null;
    prior_gci?: number | null;
    change_pct?: number | null;
    change_horizon?: string | null;
  }[]
> {
  return getJson(`/api/companies/${id}/gci/history`);
}

export function postReview(body: {
  company_id: string;
  outcome_index: number;
  action: "accept" | "edit" | "reject";
  comment?: string;
  edits?: Record<string, unknown>;
}): Promise<unknown> {
  return getJson("/api/review", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export type PendingStatement = {
  company_id: string;
  period: string;
  metric: string;
  guided_value: number;
  guided_low?: number | null;
  guided_high?: number | null;
  actual_value?: number | null;
  guided_text: string;
  confidence: number;
  speaker: string;
  thread_id?: string | null;
  source_ref?: string | null;
  quote_span?: string | null;
  review_status?: string;
  needs_review?: boolean;
};

export type PendingExtractBatch = {
  id: string;
  company_id: string;
  statements: PendingStatement[];
  status: string;
  accepted_count?: number;
  /** Extracted from the seeded demo transcript, not a real filing. */
  sample?: boolean;
};

export function postExtract(
  companyId: string,
  opts?: { text?: string; period?: string; sourceRef?: string }
): Promise<{ statements: PendingStatement[]; count: number; extract_id?: string }> {
  const body: Record<string, unknown> = { company_id: companyId };
  if (opts?.text) body.text = opts.text;
  if (opts?.period) body.period = opts.period;
  if (opts?.sourceRef) body.source_ref = opts.sourceRef;
  return getJson("/api/extract", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export function fetchExtractPending(
  companyId?: string
): Promise<{ count: number; batches: PendingExtractBatch[] }> {
  const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
  return getJson(`/api/extract/pending${qs}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postExtractCommit(body: {
  extract_id: string;
  accepted_indices: number[];
  edits?: Record<number, Record<string, unknown>>;
}): Promise<{ ok: boolean; committed: number; edited?: number; company_id: string }> {
  return getJson("/api/extract/commit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export type ReviewRecord = {
  company_id: string;
  action: string;
  reviewer?: string;
  source?: string;
  at?: string;
  comment?: string | null;
  edits?: Record<string, unknown>;
  outcome_index?: number;
  statement_index?: number;
};

export function fetchReviews(): Promise<{ reviews: ReviewRecord[] }> {
  return getJson("/api/reviews", {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postIngestPaste(body: {
  company_id: string;
  text: string;
  title?: string;
  doc_type?: string;
}): Promise<{
  ok: boolean;
  document: { doc_id: string; title: string };
  extract?: { id?: string; statements?: unknown[] } | null;
  note?: string;
}> {
  return getJson("/api/ingest/paste", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export function postIngestUrl(body: {
  company_id: string;
  url: string;
  title?: string;
}): Promise<{
  ok: boolean;
  document: { doc_id: string; title: string };
  extract?: { id?: string; statements?: unknown[] } | null;
}> {
  return getJson("/api/ingest/url", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export type CrawlReport = {
  ok: boolean;
  as_of: string;
  dry_run: boolean;
  live: boolean;
  targets: number;
  fetched: number;
  catalog: number;
  skipped_dedupe: number;
  failed: number;
  pending_new: number;
  pending_total: number;
  pending_by_company: Record<string, number>;
  note?: string;
};

export function postIngestCrawl(body?: {
  limit?: number;
  dry_run?: boolean;
  live?: boolean;
  company_ids?: string[];
}): Promise<CrawlReport> {
  return getJson("/api/ingest/crawl", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body ?? { limit: 30, dry_run: false, live: true }),
  });
}

export type RefreshReport = {
  ok: boolean;
  live: boolean;
  interval_hours: number;
  crawl: Record<string, unknown>;
  extract: Record<string, unknown>;
  fmp: Record<string, unknown>;
  note?: string;
};

export function postIngestRefresh(body?: {
  limit?: number;
  live?: boolean;
  auto_extract?: boolean;
  warm_fmp?: boolean;
}): Promise<RefreshReport> {
  return getJson("/api/ingest/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body ?? { limit: 30, live: true }),
  });
}

export function fetchCrawlStatus(): Promise<{
  last: Record<string, unknown> | null;
  runs: Record<string, unknown>[];
  pending_total: number;
  pending_by_company: Record<string, number>;
}> {
  return getJson("/api/ingest/crawl/status", {
    headers: { "X-API-Key": API_KEY },
  });
}

export function fetchDocuments(params?: {
  company_id?: string;
  review_status?: string;
}): Promise<{ count: number; documents: Record<string, unknown>[] }> {
  const q = new URLSearchParams();
  if (params?.company_id) q.set("company_id", params.company_id);
  if (params?.review_status) q.set("review_status", params.review_status);
  const qs = q.toString() ? `?${q}` : "";
  return getJson(`/api/documents${qs}`);
}

export function fetchDocumentByUrl(url: string): Promise<{
  count: number;
  documents: Array<{
    doc_id?: string;
    company_id?: string | null;
    title?: string;
    text?: string;
    url?: string | null;
  }>;
}> {
  return getJson(`/api/documents?url=${encodeURIComponent(url)}`);
}

export function fetchDocument(docId: string): Promise<{
  doc_id: string;
  company_id?: string | null;
  doc_type?: string | null;
  title: string;
  text: string;
  url?: string | null;
  date?: string | null;
  source?: string | null;
  period?: string | null;
  review_status?: string | null;
}> {
  return getJson(`/api/documents/${encodeURIComponent(docId)}`);
}

export function postDocumentReview(body: {
  doc_id: string;
  action: "accept" | "reject";
}): Promise<{ ok: boolean; document: Record<string, unknown> }> {
  return getJson("/api/documents/review", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
}

export function fetchCorpusCoverage(): Promise<{
  companies?: number;
  tier1_pass?: number;
  tier1_rate_pct?: number;
  note?: string;
  [key: string]: unknown;
}> {
  return getJson("/api/ops/corpus-coverage", {
    headers: { "X-API-Key": API_KEY },
  });
}

export function fetchPendingDepth(bootstrap = false): Promise<Record<string, unknown>> {
  const qs = bootstrap ? "?bootstrap=true" : "";
  return getJson(`/api/ops/pending-depth${qs}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postPendingDepthBootstrap(): Promise<Record<string, unknown>> {
  return getJson("/api/ops/pending-depth/bootstrap", {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });
}

export function postConsensusImport(
  rows: Record<string, unknown>[],
  opts?: { demo?: boolean },
): Promise<{ ok: boolean; imported: number; demo?: boolean }> {
  const qs = opts?.demo ? "?demo=true" : "";
  return getJson(`/api/consensus/import${qs}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ rows }),
  });
}

export function fetchConsensusStats(): Promise<{
  row_count: number;
  company_count: number;
}> {
  return getJson("/api/consensus/stats", {
    headers: { "X-API-Key": API_KEY },
  });
}

export type RecentFiling = {
  doc_id: string;
  company_id?: string | null;
  name?: string | null;
  ticker?: string | null;
  doc_type?: string | null;
  title?: string | null;
  url?: string | null;
  date?: string | null;
  source_type?: string | null;
};

export function fetchRecentFilings(limit = 8): Promise<{ count: number; filings: RecentFiling[] }> {
  return getJson(`/api/filings/recent?limit=${limit}`);
}

export function fetchReadingRoom(): Promise<{
  limited: boolean;
  cap: number;
  used?: number;
  remaining?: number | null;
  blocked?: boolean;
}> {
  return getJson("/api/research/reading-room");
}

export function fetchResearchSearch(
  q: string,
  companyId?: string,
  opts: { expand?: boolean; readingRoom?: boolean } = {}
): Promise<{
  results: ResearchDoc[];
  count: number;
  original_query?: string;
  expanded_query?: string;
  reading_room?: { cap?: number; used?: number; remaining?: number | null };
}> {
  const params = new URLSearchParams({ q });
  if (companyId) params.set("company_id", companyId);
  if (opts.expand) params.set("expand", "true");
  if (opts.readingRoom) params.set("reading_room", "true");
  return getJson(`/api/research/search?${params}`);
}

export function fetchResearchChat(
  question: string,
  companyId?: string,
  opts: { expand?: boolean } = {}
): Promise<{ answer: string; citations: CitationRecord[]; refused?: boolean }> {
  return getJson("/api/research/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, company_id: companyId, expand: !!opts.expand }),
  });
}

export function fetchCitation(citationId: string): Promise<CitationRecord> {
  return getJson(`/api/citations/${encodeURIComponent(citationId)}`);
}

export function fetchCompanyCitations(
  companyId: string,
  citeableOnly = true
): Promise<{ count: number; citations: CitationRecord[] }> {
  const q = new URLSearchParams({
    company_id: companyId,
    citeable_only: citeableOnly ? "true" : "false",
  });
  return getJson(`/api/citations?${q}`);
}

export function fetchResearchSnapshot(id: string): Promise<ResearchSnapshot> {
  return getJson(`/api/research/snapshot/${id}`);
}

export function fetchResearchEstimates(
  id: string
): Promise<{ estimates: ResearchEstimateRow[] }> {
  return getJson(`/api/research/estimates/${id}`);
}

export type PromiseBriefItem = {
  period: string;
  metric: string;
  guided_value: number;
  guided_band: (number | null)[];
  guided_text: string;
  speaker: string;
  confidence: number;
  source_url?: string | null;
  source_ref?: string | null;
  street_consensus: number;
  street_source: string;
  history: {
    closed: number;
    met: number;
    exceeded: number;
    missed: number;
    dropped: number;
    kept: number;
    hit_rate_pct: number | null;
  };
};

export type PromiseBrief = {
  company_id: string;
  name: string;
  ticker: string;
  sector: string;
  gci_score: number | null;
  gci_change_pct?: number | null;
  gci_change_horizon?: string | null;
  data_quality: string;
  open_promise_count: number;
  promises: PromiseBriefItem[];
  note: string;
  disclaimer: string;
};

export function fetchResearchBrief(companyId: string): Promise<PromiseBrief> {
  return getJson(`/api/research/brief/${encodeURIComponent(companyId)}`);
}

export function fetchResearchNews(
  companyId?: string
): Promise<{ items: ResearchDoc[] }> {
  const params = new URLSearchParams();
  if (companyId) params.set("company_id", companyId);
  const qs = params.toString();
  return getJson(`/api/research/news${qs ? `?${qs}` : ""}`);
}

export function fetchResearchWatchlist(opts?: {
  companyIds?: string[];
  token?: string | null;
}): Promise<{ items: WatchlistItem[]; source?: string; count?: number }> {
  const params = new URLSearchParams();
  if (opts?.companyIds?.length) {
    params.set("ids", opts.companyIds.join(","));
  }
  const qs = params.toString();
  const headers: Record<string, string> = {};
  if (opts?.token) headers.Authorization = `Bearer ${opts.token}`;
  return getJson(`/api/research/watchlist${qs ? `?${qs}` : ""}`, {
    headers: Object.keys(headers).length ? headers : undefined,
  });
}

export type TrustCenterPayload = {
  product: string;
  legal_entity: string;
  domain: string;
  copyright?: {
    counsel_status?: string;
    counsel_note?: string;
    terms_version?: string;
    privacy_version?: string;
    contact_email?: string;
    line?: string;
  };
  security: {
    force_https: boolean;
    hsts: boolean;
    headers: string[];
    auth_modes: string[];
    csp?: string;
    backups?: string;
  };
  sso: {
    enabled?: boolean;
    configured?: boolean;
    production_ready?: boolean;
    note?: string;
  };
  citations: {
    model: string;
    endpoints: string[];
    research_chat: string;
  };
  compliance: {
    posture: string;
    sebi: string;
    terms_version?: string;
    privacy_version?: string;
    counsel_status?: string;
    counsel_note?: string;
    contact_email?: string;
    privacy_email?: string;
    link_out_policy?: string;
    prices_on_public?: boolean;
    links: Record<string, string>;
  };
  data: {
    beachhead: string;
    gci: string;
    invent_actuals: boolean;
    quality_badges?: string;
  };
  residency?: {
    region: string;
    provider: string;
    note: string;
  };
  tenancy?: {
    model: string;
    auth: string;
  };
  subprocessors?: { name: string; role: string; optional: boolean }[];
  incident?: { contact: string; note: string };
  llm?: { configured: boolean; note: string };
  labeling_governance?: {
    two_person_review?: boolean;
    drafts?: number;
    submitted?: number;
    accepted?: number;
    note?: string;
    recent?: Array<{
      id?: string;
      company_id?: string;
      period?: string;
      metric?: string;
      status?: string;
      submitter_id?: string;
      reviewer_id?: string;
      updated_at?: string;
    }>;
  };
  source_verification?: {
    as_of?: string | null;
    checked?: number;
    verified?: number;
    failed?: number;
    fetch_failed?: number;
    note?: string;
  };
  filing_to_score?: FilingToScoreSla;
  feature_flags_public?: Record<string, unknown>;
};

export function fetchTrustCenter(): Promise<TrustCenterPayload> {
  return getJson("/api/trust");
}

export function fetchResearchTranscripts(
  companyId?: string
): Promise<{ transcripts: ResearchDoc[] }> {
  const params = new URLSearchParams();
  if (companyId) params.set("company_id", companyId);
  const qs = params.toString();
  return getJson(`/api/research/transcripts${qs ? `?${qs}` : ""}`);
}

export type WordmapPayload = {
  company_id: string;
  entity: Record<string, number>;
  industry: Record<string, number | null>;
  sector: string;
  peer_count: number;
  source?: string;
  citeable?: boolean;
  note?: string;
};

export type LabelingQueueItem = {
  id: string;
  company_id: string;
  company_name?: string;
  data_quality?: string;
  priority?: string;
  status?: string;
  note?: string;
  kind?: string;
  flag?: string | null;
  period?: string | null;
  metric?: string | null;
  requested_by?: string;
};

export type VernacularPayload = {
  company_id: string;
  lang: string;
  text: string;
  supported_langs: string[];
  status: string;
};

export type BadgePayload = {
  ticker: string;
  name?: string | null;
  gci_score: number | null;
  confidence_tier?: string | null;
  as_of?: string | null;
  algorithm_id?: string | null;
  label: string;
  embed: string;
  svg_url: string;
  status: string;
  disclaimer: string;
  data_quality?: string | null;
};

export type OwnerInviteResult = {
  status?: string;
  org_id?: string;
  email?: string;
  mail_status?: string;
  role?: string;
  detail?: string;
  sent_at?: string;
  dev_token?: string;
  dev_link?: string;
};

export type OrgSeat = {
  id: string;
  email?: string | null;
  name?: string;
  role?: string;
  active?: boolean;
  protected?: boolean;
  platform_admin_role?: string | null;
};

export type OrgPayload = {
  id: string;
  name?: string;
  seats?: number;
  seats_used?: number;
  seats_available?: number;
  plan?: string;
  csm?: string;
  features?: string[];
  owner_email?: string | null;
  owner_invite?: OwnerInviteResult | null;
  protected?: boolean;
  members?: OrgSeat[];
  deletable?: boolean;
  delete_block?: string | null;
  [key: string]: unknown;
};

function authHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  };
  try {
    const tkn = localStorage.getItem("intellens.auth.token");
    if (tkn) headers.Authorization = `Bearer ${tkn}`;
  } catch {
    /* ignore */
  }
  return headers;
}

export function fetchWordmap(id: string): Promise<WordmapPayload> {
  return getJson(`/api/companies/${id}/wordmap`);
}

export function fetchVernacular(id: string, lang = "hi"): Promise<VernacularPayload> {
  return getJson(`/api/vernacular/${id}?lang=${encodeURIComponent(lang)}`);
}

export function fetchBadge(ticker: string): Promise<BadgePayload> {
  return getJson(`/api/badge/${encodeURIComponent(ticker)}`);
}

export function fetchOrg(orgId = "demo"): Promise<OrgPayload> {
  return getJson(`/api/orgs/${orgId}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postAlphaHunterImport(body: {
  facts: Record<string, unknown>[];
  merge_into_company?: string;
}): Promise<{ actuals: unknown[]; merged?: number }> {
  return getJson("/api/import/alphahunter", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export function fetchAlphaHunterStatus(): Promise<{
  configured: boolean;
  api_key_set: boolean;
  url_host: string | null;
  note: string;
}> {
  return getJson("/api/import/alphahunter/status");
}

export function postAlphaHunterLive(opts: {
  company_id: string;
  merge?: boolean;
}): Promise<{
  ok?: boolean;
  source?: string;
  fact_count?: number;
  merged?: number;
  note?: string;
}> {
  const qs = new URLSearchParams({
    company_id: opts.company_id,
    merge: opts.merge === false ? "false" : "true",
  });
  return getJson(`/api/import/alphahunter/live?${qs}`, {
    method: "POST",
    headers: authHeaders(),
  });
}

export function fetchNiftyMilestones(): Promise<{
  milestones: Array<{
    id: string;
    title: string;
    target: string;
    status: string;
  }>;
  counts: Record<string, number | string[]>;
  nifty_extra_ids?: string[];
  progress: { done: number; total: number };
  note: string;
  day1_claim: boolean;
}> {
  return getJson("/api/universe/nifty/milestones");
}

export function postNiftyEnqueueLabeling(): Promise<{
  ok: boolean;
  enqueued: number;
  milestones: {
    milestones: Array<{ id: string; title: string; status: string }>;
  };
}> {
  return getJson("/api/universe/nifty/enqueue-labeling", {
    method: "POST",
    headers: authHeaders(),
  });
}

export function fetchCsmDashboard(orgId = "demo"): Promise<{
  org: OrgPayload;
  csm: { named: string; email: string; qbr_cadence: string; next_qbr_hint: string };
  sla: {
    plan: string;
    targets: { uptime_pct: number; sev1_hours: number; channel: string };
    observed: { uptime_pct: number | null; checks: number; note?: string };
    within_target: boolean | null;
  };
  labeling_open: number;
  labeling_audit?: Array<{
    id?: string;
    company_id?: string;
    period?: string;
    metric?: string;
    status?: string;
    submitter_id?: string;
    reviewer_id?: string;
    updated_at?: string;
  }>;
  tickets_open: number;
  tickets: Array<{ id: string; subject: string; severity: string; status: string }>;
  vpc: { status: string; private_subnet_example: string; note: string };
  note: string;
}> {
  return getJson(`/api/csm/${encodeURIComponent(orgId)}`, {
    headers: { "X-API-Key": API_KEY },
  });
}

export function postCsmTicket(
  orgId: string,
  body: { subject: string; severity?: string; body?: string },
): Promise<{ ok: boolean; ticket: { id: string } }> {
  return getJson(`/api/csm/${encodeURIComponent(orgId)}/tickets`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export function fetchSsoStatus(): Promise<{
  enabled: boolean;
  configured: boolean;
  ready?: boolean;
  production_ready?: boolean;
  coming_soon?: boolean;
  note?: string;
  login_url?: string | null;
  checklist?: Record<string, boolean>;
}> {
  return getJson("/api/auth/sso/status");
}

export function fetchSsoLogin(): Promise<{
  status: string;
  authorize_url: string | null;
  message?: string;
}> {
  return getJson("/api/auth/sso/login");
}

export function fetchLabelingQueue(orgId?: string): Promise<{
  items: LabelingQueueItem[];
  count: number;
}> {
  const qs = orgId ? `?org_id=${encodeURIComponent(orgId)}` : "";
  return getJson(`/api/labeling/queue${qs}`, { headers: authHeaders() });
}

export function postLabelingQueue(body: {
  company_id: string;
  priority?: string;
  note?: string;
  org_id?: string;
}): Promise<{ ok: boolean; item: LabelingQueueItem }> {
  return getJson("/api/labeling/queue", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export function patchLabelingQueue(
  itemId: string,
  status: "done" | "cancelled" | "in_progress" | "queued",
): Promise<{ ok: boolean; item: LabelingQueueItem }> {
  return getJson(`/api/labeling/queue/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  });
}

export function postCompanyAuditFlag(
  companyId: string,
  body: { flag: string; source_url: string; note?: string },
): Promise<{ ok: boolean; flag: Record<string, unknown> }> {
  return getJson(`/api/companies/${encodeURIComponent(companyId)}/audit-flags`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export function deleteCompanyAuditFlag(
  companyId: string,
  flag: string,
): Promise<{ ok: boolean }> {
  return getJson(
    `/api/companies/${encodeURIComponent(companyId)}/audit-flags/${encodeURIComponent(flag)}`,
    { method: "DELETE", headers: authHeaders() },
  );
}

export function fetchEmFactorCsvUrl(companyId: string): string {
  return `${API_BASE || ""}/api/export/em-factor/${encodeURIComponent(companyId)}?format=csv`;
}

export type MetricCatalogRow = {
  id: string;
  display_name: string;
  unit: string;
  family: string;
  sectors: string[];
  aliases: string[];
  tier: string;
  bands_preferred: boolean;
  outcome_count?: number;
};

export function fetchMetrics(sector?: string): Promise<{ count: number; metrics: MetricCatalogRow[] }> {
  const qs = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return getJson(`/api/metrics${qs}`);
}

export function apiDocsUrl(): string {
  return `${API_BASE || ""}/docs`;
}

export function demoApiKey(): string {
  return API_KEY;
}

export type UserPreferences = {
  language: string;
  default_market: string;
  default_index: string;
  watchlist: string[];
  show_demo_tape: boolean;
  density?: "comfortable" | "compact";
  saved_queries?: string[];
  analytics_consent?: boolean | null;
  dossier_opens?: number;
};

export type Entitlements = {
  plan: string;
  role: string;
  kind?: string;
  org_id?: string | null;
  features: string[];
  skus?: string[];
  limits?: Record<string, number>;
  labeling_granted?: boolean;
  design_partner?: boolean;
  source?: string;
};

export function fetchEntitlementsMe(): Promise<Entitlements> {
  return getJson("/api/entitlements/me");
}

export type AdminPortalSection = { id: string; label: string };

export type AdminPortalMe = {
  platform_admin_role: string;
  permissions: string[];
  source?: string;
  email?: string | null;
  name?: string | null;
  sections: AdminPortalSection[];
};

export type AdminPortalUser = {
  id: string;
  email?: string | null;
  name?: string;
  kind?: string;
  account_type?: string;
  org_id?: string | null;
  role?: string;
  platform_admin_role?: string | null;
  email_verified?: boolean;
  active?: boolean;
  protected?: boolean;
  created_at?: string;
};

export function fetchAdminPortalMe(token?: string | null): Promise<AdminPortalMe> {
  return authJson("/api/admin/portal/me", undefined, token);
}

export function fetchAdminPortalOrgs(token?: string | null): Promise<{ orgs: OrgPayload[] }> {
  return authJson("/api/admin/portal/orgs", undefined, token);
}

export function fetchAdminPortalUsers(token?: string | null): Promise<{ users: AdminPortalUser[] }> {
  return authJson("/api/admin/portal/users", undefined, token);
}

export function deleteAdminPortalOrg(
  orgId: string,
  token?: string | null,
): Promise<{ deleted: string; name?: string }> {
  return authJson(`/api/admin/portal/orgs/${encodeURIComponent(orgId)}`, { method: "DELETE" }, token);
}

export function deleteAdminPortalUser(
  userId: string,
  token?: string | null,
): Promise<{ deleted: string; email?: string | null; org_id?: string | null }> {
  return authJson(`/api/admin/portal/users/${encodeURIComponent(userId)}`, { method: "DELETE" }, token);
}

export function patchAdminPortalUserRole(
  userId: string,
  platformAdminRole: string | null,
  token?: string | null,
): Promise<{ id: string; email?: string; platform_admin_role?: string }> {
  return authJson(
    `/api/admin/portal/users/${encodeURIComponent(userId)}/platform-role`,
    {
      method: "PATCH",
      body: JSON.stringify({ platform_admin_role: platformAdminRole }),
    },
    token,
  );
}

export function fetchAdminPortalFeedback(
  token?: string | null,
  status?: string,
): Promise<{ items: FeedbackItem[] }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return authJson(`/api/admin/portal/feedback${q}`, undefined, token);
}

export function patchAdminPortalFeedback(
  itemId: string,
  status: string,
  token?: string | null,
): Promise<FeedbackItem> {
  return authJson(
    `/api/admin/portal/feedback/${encodeURIComponent(itemId)}`,
    { method: "PATCH", body: JSON.stringify({ status }) },
    token,
  );
}

export function fetchAdminPortalLegal(token?: string | null): Promise<Record<string, unknown>> {
  return authJson("/api/admin/portal/legal", undefined, token);
}

export function postAdminPortalLegalAttest(
  body: { kind: string; attested_by: string; note?: string },
  token?: string | null,
): Promise<Record<string, unknown>> {
  return authJson(
    "/api/admin/portal/legal/attest",
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
}

export function fetchAdminPortalBilling(
  token?: string | null,
): Promise<{ invoices: Record<string, unknown>[] }> {
  return authJson("/api/admin/portal/billing", undefined, token);
}

export function fetchAdminPortalAudit(token?: string | null): Promise<Record<string, number>> {
  return authJson("/api/admin/portal/audit", undefined, token);
}

export type AdminBoardRow = {
  id: string;
  label: string;
  count: number;
  section: string;
  running?: boolean;
};

export function fetchAdminPortalBoard(token?: string | null): Promise<{ as_of: string; rows: AdminBoardRow[] }> {
  return authJson("/api/admin/portal/board", undefined, token);
}

export type AdminLabelingItem = {
  id: string;
  company_id?: string;
  company_name?: string;
  org_id?: string;
  kind?: string;
  status?: string;
  priority?: string;
  created_at?: string;
  age_days?: number | null;
};

export type AdminLabelingView = {
  as_of: string;
  items: AdminLabelingItem[];
  extracts: { id: string; company_id?: string; status?: string; statements: number }[];
  source_checks: {
    as_of?: string | null;
    checked: number;
    verified: number;
    failed: number;
    fetch_failed: number;
    note?: string;
    failures: { company_id?: string; period?: string; metric?: string; kind?: string }[];
  };
  note: string;
};

export function fetchAdminPortalLabeling(token?: string | null): Promise<AdminLabelingView> {
  return authJson("/api/admin/portal/labeling", undefined, token);
}

export type AdminCommitmentItem = {
  id: string;
  company_id?: string;
  type?: string;
  subject?: string;
  due_period?: string;
  proposed_at?: string;
  quote?: string;
};

export function fetchAdminPortalCommitments(
  token?: string | null,
): Promise<{ as_of: string; items: AdminCommitmentItem[]; note: string }> {
  return authJson("/api/admin/portal/commitments", undefined, token);
}

export type AdminFlag = { id: string; label: string; on: boolean };

export type AdminSystemStatus = {
  as_of: string;
  guidance_review: { ran: boolean; market_id?: string | null; date?: string | null; at?: string | null; bound_rows?: number | null };
  monitors: { monitors: number; orgs: number; last_triggered_at?: string | null; seen_documents: number; baselined_at?: string | null };
  india_coverage: Record<string, unknown>;
  us_coverage: Record<string, unknown>;
  source_verification: { as_of?: string | null; checked: number; verified: number; failed: number; fetch_failed: number; note?: string };
  flags: AdminFlag[];
  note: string;
};

export function fetchAdminPortalSystem(token?: string | null): Promise<AdminSystemStatus> {
  return authJson("/api/admin/portal/system", undefined, token);
}

export function postAdminPortalCleanup(
  dryRun: boolean,
  token?: string | null,
): Promise<{ dry_run: boolean; users_removed: string[]; orgs_removed: string[]; users_kept: number; orgs_kept: number }> {
  return authJson(
    "/api/admin/portal/cleanup-test-tenants",
    { method: "POST", body: JSON.stringify({ dry_run: dryRun }) },
    token,
  );
}

export function postAdminPortalInvoice(
  body: { org_id: string; plan: string; seats: number; amount_inr?: number; po_number?: string; signer_email?: string },
  token?: string | null,
): Promise<Record<string, unknown>> {
  return authJson("/api/admin/portal/billing/invoices", { method: "POST", body: JSON.stringify(body) }, token);
}

export type AdminReportMeta = { id: string; label: string; permission: string };

export function fetchAdminPortalReportCatalog(
  token?: string | null,
): Promise<{ reports: AdminReportMeta[] }> {
  return authJson("/api/admin/portal/reports", undefined, token);
}

export function fetchAdminPortalReport(
  reportId: string,
  token?: string | null,
): Promise<Record<string, unknown>> {
  return authJson(`/api/admin/portal/reports/${encodeURIComponent(reportId)}`, undefined, token);
}

export function postAdminPortalPilot(
  name: string,
  termDays: 30 | 45 | 60,
  token?: string | null,
): Promise<Record<string, unknown>> {
  return authJson(
    "/api/admin/portal/pilot",
    { method: "POST", body: JSON.stringify({ name, term_days: termDays }) },
    token,
  );
}

export type PilotRequestItem = {
  id: string;
  name: string;
  email: string;
  firm: string;
  role?: string;
  team_size?: string;
  message?: string;
  status: "pending" | "approved" | "rejected";
  org_id?: string | null;
  admin_note?: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at?: string;
  owner_invite?: OwnerInviteResult | null;
};

export function fetchAdminPortalPilotRequests(
  status?: string,
  token?: string | null,
): Promise<{ items: PilotRequestItem[] }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return authJson(`/api/admin/portal/pilot-requests${q}`, undefined, token);
}

export function deleteAdminPortalPilotRequest(
  requestId: string,
  token?: string | null,
): Promise<{ deleted: string; org_id?: string | null }> {
  return authJson(
    `/api/admin/portal/pilot-requests/${encodeURIComponent(requestId)}`,
    { method: "DELETE" },
    token,
  );
}

export type HoldingsLine = {
  isin?: string;
  weight: number;
  residual?: string;
  name?: string;
  company_id?: string;
  ticker?: string | null;
  gci_score?: number | null;
  confidence_tier?: string | null;
  reason?: string;
  kind?: string;
  open_commitments?: number | null;
};

export type HoldingsReport = {
  product: string;
  as_of: string;
  covered_gci: number | null;
  covered_weight_pct: number;
  unscored_weight_pct: number;
  residual_weight_pct: number;
  statement: string;
  note: string;
  scored: HoldingsLine[];
  gaps: HoldingsLine[];
  residual: HoldingsLine[];
  manager?: {
    equal_weight_gci: number | null;
    delivery_tilt: number | null;
    universe_gci: number | null;
    versus_universe: number | null;
    statement: string;
  };
  scheme?: {
    available: boolean;
    change_pct: number | null;
    statement: string;
    points?: { as_of: string; value: number }[];
  };
  lines?: { isin?: string; weight: number; residual?: string; name?: string }[];
  diff?: {
    prior_as_of?: string;
    prior_covered_gci?: number | null;
    covered_gci_change?: number | null;
    entered?: HoldingsLine[];
    exited?: HoldingsLine[];
    weight_changes?: { name?: string; prior_weight?: number; weight?: number; prior_gci?: number | null; gci_score?: number | null }[];
  } | null;
  last_opened_at?: string | null;
  since_last_open?: {
    company_id: string;
    name: string;
    kind: "filing" | "open_guidance" | "missed";
    title?: string | null;
    at?: string | null;
    count?: number;
    period?: string;
    metric?: string;
  }[];
};

export function postHoldingsLookthrough(
  body: {
    as_of: string;
    lines: { isin?: string; weight: number; residual?: string; name?: string }[];
    scheme?: { as_of: string; value: number }[];
  },
  token?: string | null,
): Promise<HoldingsReport> {
  return authJson(
    "/api/holdings/lookthrough",
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
}

export function fetchHoldingsLatest(token?: string | null): Promise<HoldingsReport> {
  return authJson("/api/holdings/latest", { method: "GET" }, token);
}

export type NinjaWorksheet = {
  template: string;
  figure: number;
  unit: string;
  statement: string;
  saved?: boolean;
  saved_at?: string;
  company_id?: string;
  published_gci?: number | null;
  sensitivity?: { label: string; figure: number }[];
  inputs?: Record<string, unknown>;
  id?: string;
};

export type NinjaWorksheetRecord = {
  company_id: string;
  template: string | null;
  latest: (NinjaWorksheet & { inputs: Record<string, unknown>; saved_at?: string }) | null;
  history: (NinjaWorksheet & { inputs: Record<string, unknown>; saved_at?: string })[];
  statement: string;
};

export type NinjaProfile = {
  company_id: string;
  note: string;
  layers: Record<string, { quote: string; source_url: string; as_of: string; stance: string }[]>;
  notes?: {
    skill_id: string;
    title: string;
    generated_at?: string;
    claims: { text?: string; quote: string; source_url: string; as_of?: string }[];
  }[];
  sector?: string | null;
};

export function postNinjaWorksheet(
  template: string,
  body: Record<string, unknown>,
  token?: string | null,
): Promise<NinjaWorksheet> {
  return authJson(`/api/ninja/worksheets/${encodeURIComponent(template)}`, { method: "POST", body: JSON.stringify(body) }, token);
}

export function fetchNinjaWorksheets(
  companyId: string,
  template: string,
  token?: string | null,
): Promise<NinjaWorksheetRecord> {
  const params = new URLSearchParams({ company_id: companyId });
  if (template) params.set("template", template);
  return authJson(`/api/ninja/worksheets?${params}`, { method: "GET" }, token);
}

export type NinjaChronology = {
  statement: string;
  events: {
    date: string;
    kind: "guidance" | "revision" | "actual";
    period: string;
    metric: string;
    metric_name: string;
    text: string;
    quote: string | null;
    source_url: string | null;
  }[];
};

export type NinjaCalculation = {
  company_id: string;
  name: string;
  sector: string | null;
  sector_rule: string | null;
  scale_floor: number | null;
  decay: number | null;
  published_gci: number | null;
  delivery: number;
  floor: number;
  ceiling: number;
  years_above_ceiling: number;
  rubrics_on_file: boolean;
  years: {
    period: string;
    metric: string;
    metric_name: string;
    as_of: string | null;
    band_low: number;
    band_high: number;
    actual: number;
    delivery: number;
    published_year: number;
    floor: number;
    ceiling: number;
    rubric_needed: number;
    reachable: boolean;
    in_composite: boolean;
  }[];
  path: {
    as_of: string;
    published: number | null;
    delivery: number;
    floor: number;
    ceiling: number;
  }[];
  heatmap: {
    columns: { key: string; period: string; metric_name: string; in_composite: boolean }[];
    rows: { id: string; label: string; values: number[] }[];
  };
  chronology: NinjaChronology;
  statement: string;
};

export type NinjaListingRow = {
  company_id: string;
  ticker: string;
  name: string;
  sector: string;
  data_quality?: string;
  has_worksheet: boolean;
  published_gci: number | null;
};

export function fetchNinjaCalculations(
  token?: string | null,
): Promise<{ statement: string; listing: NinjaListingRow[]; companies: NinjaCalculation[] }> {
  return authJson("/api/ninja/indices", { method: "GET" }, token);
}

export type NinjaObservation = {
  id?: string;
  layer: string;
  stance: string;
  quote: string;
  source_url: string;
  as_of: string;
};

export type NinjaQuestion = {
  id: string;
  prompt: string;
  score: number | null;
  quote: string;
  source_url: string;
  as_of: string;
  period: string;
};

export type NinjaSheetLayer = {
  layer: string;
  cited: number;
  needed: number;
  complete: boolean;
  level: number | null;
  questions: NinjaQuestion[];
};

export type NinjaSheet = {
  period: string;
  periods: string[];
  scale: string;
  layers: NinjaSheetLayer[];
  statement: string;
  desk_blend: {
    period: string | null;
    available: boolean;
    level: number | null;
    delivery: number | null;
    statement: string;
  };
};

export type NinjaIndex = {
  statement: string;
  min_observations: number;
  layers: {
    layer: string;
    level: number | null;
    supported: number;
    contradicted: number;
    count: number;
    needed: number;
    published: boolean;
  }[];
  observations: NinjaObservation[];
  sheet: NinjaSheet;
  calculation: NinjaCalculation | null;
  chronology: NinjaChronology;
};

export function fetchNinjaIndex(
  companyId: string,
  token?: string | null,
  period?: string,
): Promise<NinjaIndex> {
  const params = new URLSearchParams();
  if (period) params.set("period", period);
  const qs = params.toString();
  return authJson(`/api/ninja/indices/${encodeURIComponent(companyId)}${qs ? `?${qs}` : ""}`, { method: "GET" }, token);
}

export function postNinjaObservation(
  body: { company_id: string; layer: string; stance: string; quote: string; source_url: string; as_of: string },
  token?: string | null,
): Promise<NinjaObservation> {
  return authJson("/api/ninja/observations", { method: "POST", body: JSON.stringify(body) }, token);
}

export function deleteNinjaObservation(obsId: string, token?: string | null): Promise<{ deleted: string }> {
  return authJson(`/api/ninja/observations/${encodeURIComponent(obsId)}`, { method: "DELETE" }, token);
}

export function postNinjaRating(
  body: {
    company_id: string;
    layer: string;
    question: string;
    period: string;
    score: number;
    quote: string;
    source_url: string;
    as_of: string;
  },
  token?: string | null,
): Promise<Record<string, unknown>> {
  return authJson("/api/ninja/ratings", { method: "POST", body: JSON.stringify(body) }, token);
}

export type NinjaTestRow = {
  company_id: string;
  ticker: string;
  name: string;
  sector: string;
  period: string;
  metric_name: string;
  outcome: string;
  downward: boolean;
};

export type NinjaOutcomeCount = {
  company_id?: string;
  ticker?: string;
  name?: string;
  sector: string;
  met: number;
  exceeded: number;
  missed: number;
};

export function fetchNinjaTests(token?: string | null): Promise<{
  statement: string;
  rows: NinjaTestRow[];
  by_company: NinjaOutcomeCount[];
  by_sector: NinjaOutcomeCount[];
  flags: {
    guidance_withdrawal: { n: number; rows: { company_id: string; ticker: string; name: string; source_url?: string; set_at?: string }[] };
    definition_shift: { n: number; rows: { company_id: string; ticker: string; name: string; source_url?: string; set_at?: string }[] };
  };
  downward_revision: {
    sufficient: boolean;
    statement: string;
    with_revision: { n: number; miss_share_pct: number | null };
    without_revision: { n: number; miss_share_pct: number | null };
  };
  persistence: {
    sufficient: boolean;
    statement: string;
    companies: number;
    both_missed_share_pct: number | null;
    rows: {
      company_id: string;
      ticker: string;
      name: string;
      prior_period: string;
      latest_period: string;
      both_missed: boolean;
    }[];
  };
}> {
  return authJson("/api/ninja/tests", { method: "GET" }, token);
}

export function fetchNinjaProfile(companyId: string, token?: string | null): Promise<NinjaProfile> {
  return authJson(`/api/ninja/profile/${encodeURIComponent(companyId)}`, { method: "GET" }, token);
}

export function fetchNinjaTaxonomy(token?: string | null): Promise<{
  note: string;
  sectors: { sector: string; companies: number }[];
}> {
  return authJson("/api/ninja/taxonomy", { method: "GET" }, token);
}

export function postAnalystModel(
  projectId: string,
  body: {
    company_id: string;
    name: string;
    figure: number;
    unit: string;
    as_of: string;
    assumptions: string;
    sources: string;
    not_found: string;
  },
): Promise<{ model_id: string; statement: string; figure: number; unit: string; name: string }> {
  return getJson(`/api/analyst/projects/${encodeURIComponent(projectId)}/models`, {
    method: "POST",
    headers: analystHeaders(),
    body: JSON.stringify(body),
  });
}

export function patchAdminPortalPilotRequest(
  requestId: string,
  body: { action: "approve" | "reject"; note?: string; term_days?: 30 | 45 | 60 },
  token?: string | null,
): Promise<{ ok: boolean; request: PilotRequestItem; owner_invite?: OwnerInviteResult }> {
  return authJson(
    `/api/admin/portal/pilot-requests/${encodeURIComponent(requestId)}`,
    { method: "PATCH", body: JSON.stringify(body) },
    token,
  );
}

export function postAdminPortalOwnerInvite(
  orgId: string,
  token?: string | null,
): Promise<OwnerInviteResult> {
  return authJson(
    `/api/admin/portal/orgs/${encodeURIComponent(orgId)}/owner-invite`,
    { method: "POST" },
    token,
  );
}

export type AuthUser = {
  id: string;
  email: string | null;
  name: string;
  kind: "registered" | "guest";
  account_type?: "retail" | "b2b" | "guest";
  org_id?: string | null;
  role?: string;
  company_scope?: string[];
  platform_admin_role?: string;
  email_verified?: boolean;
  active?: boolean;
  protected?: boolean;
  terms_version?: string;
  terms_accepted_at?: string;
  privacy_version?: string;
  preferences: UserPreferences;
  created_at?: string;
  mfa_enabled?: boolean;
};

export type AuthSession = {
  token: string;
  user: AuthUser;
};

export type LegalSection = { id: string; heading: string; body: string };

export type LegalDocument = {
  version: string;
  title: string;
  legal_entity: string;
  effective_date: string;
  counsel_status?: string;
  contact_email?: string;
  sections: LegalSection[];
  copyright: string;
};

export type LegalMeta = {
  legal_entity: string;
  product: string;
  year: string;
  line: string;
  terms_version: string;
  privacy_version: string;
  counsel_status?: string;
  counsel_note?: string;
  contact_email?: string;
  domain?: string;
  retail_marketing_allowed?: boolean;
  sebi_retail_status?: string;
  retail_marketing_note?: string;
};

export type Market = {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  primary_index?: string;
  universe_size?: number;
  /** Rows come from a published listing, not constituent placeholders. */
  listed?: boolean;
};

export type MarketIndex = {
  id: string;
  market_id: string;
  name: string;
  ticker: string;
  constituent_count?: number;
  /** Every member comes from a published listing. */
  listed?: boolean;
};

async function authJson<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    throwFromResponse(res.status, body);
  }
  return res.json() as Promise<T>;
}

export function postRegister(body: {
  email: string;
  password: string;
  name: string;
  guest_token?: string;
  preferences?: Partial<UserPreferences>;
  accept_terms?: boolean;
  account_type?: "retail" | "b2b";
  org_name?: string;
  org_id?: string;
  challenge_id?: string;
  challenge_answer?: string;
}): Promise<AuthSession> {
  return authJson("/api/auth/register", { method: "POST", body: JSON.stringify(body) });
}

export function postLogin(
  email: string,
  password: string,
  totpCode?: string,
): Promise<AuthSession> {
  return authJson("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, totp_code: totpCode || undefined }),
  });
}

export function postMfaEnroll(token?: string | null): Promise<{
  secret: string;
  otpauth_uri: string;
  mfa_enabled: boolean;
}> {
  return authJson("/api/auth/mfa/enroll", { method: "POST" }, token);
}

export function postMfaConfirm(code: string, token?: string | null): Promise<{
  mfa_enabled: boolean;
  user: AuthUser;
}> {
  return authJson("/api/auth/mfa/confirm", { method: "POST", body: JSON.stringify({ code }) }, token);
}

export function postMfaDisable(code: string, token?: string | null): Promise<{
  mfa_enabled: boolean;
  user: AuthUser;
}> {
  return authJson("/api/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) }, token);
}

export function postGuest(body?: {
  accept_terms?: boolean;
  challenge_id?: string;
  challenge_answer?: string;
}): Promise<AuthSession> {
  return authJson("/api/auth/guest", {
    method: "POST",
    body: JSON.stringify({
      accept_terms: body?.accept_terms ?? false,
      challenge_id: body?.challenge_id,
      challenge_answer: body?.challenge_answer,
    }),
  });
}

export function fetchLegalMeta(): Promise<LegalMeta> {
  return authJson("/api/legal/meta");
}

export function fetchLegalTerms(): Promise<LegalDocument> {
  return authJson("/api/legal/terms");
}

export function fetchLegalPrivacy(): Promise<LegalDocument> {
  return authJson("/api/legal/privacy");
}

export function postVerifyEmailRequest(email: string): Promise<{ status: string; dev_token?: string }> {
  return authJson("/api/auth/verify-email/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function postVerifyEmailConfirm(token: string): Promise<{ status: string; user: AuthUser }> {
  return authJson("/api/auth/verify-email/confirm", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function postPasswordResetRequest(email: string): Promise<{ status: string; dev_token?: string }> {
  return authJson("/api/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function postPasswordResetConfirm(
  token: string,
  password: string,
): Promise<{ status: string }> {
  return authJson("/api/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export function postAcceptInvite(body: {
  token: string;
  password: string;
  name?: string;
  accept_terms: boolean;
}): Promise<AuthSession> {
  return authJson("/api/auth/accept-invite", { method: "POST", body: JSON.stringify(body) });
}

export function fetchOrgMembers(
  orgId: string,
  token: string,
): Promise<{ org_id: string; members: AuthUser[] }> {
  return authJson(`/api/orgs/${encodeURIComponent(orgId)}/members`, undefined, token);
}

export function fetchMyOrg(token: string): Promise<OrgPayload> {
  return authJson("/api/orgs/me", undefined, token);
}

export function postOrgInvite(
  orgId: string,
  token: string,
  email: string,
  role = "viewer",
): Promise<{ status: string; dev_token?: string; mail_status?: string }> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/invites`,
    { method: "POST", body: JSON.stringify({ email, role }) },
    token,
  );
}

export function postPartnerInvite(
  orgId: string,
  token: string,
  email: string,
): Promise<{ status: string; dev_token?: string; expires_at?: string }> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/partner-invite`,
    { method: "POST", body: JSON.stringify({ email }) },
    token,
  );
}

export function postMemberRole(
  orgId: string,
  token: string,
  userId: string,
  role: string,
  companyScope?: string[],
): Promise<{ ok: boolean; user: AuthUser }> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}/role`,
    {
      method: "POST",
      body: JSON.stringify({
        role,
        ...(companyScope ? { company_scope: companyScope } : {}),
      }),
    },
    token,
  );
}

export function postOrgRevoke(
  orgId: string,
  token: string,
  userId: string,
): Promise<{ status: string }> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/revoke`,
    { method: "POST", body: JSON.stringify({ user_id: userId }) },
    token,
  );
}

export function postOrgApiKey(
  orgId: string,
  token: string,
): Promise<{ api_key: string; org_id: string }> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/api-keys`,
    { method: "POST", body: "{}" },
    token,
  );
}

export function putOrgOidc(
  orgId: string,
  token: string,
  body: { oidc_issuer?: string; oidc_client_id?: string; email_domain?: string },
): Promise<OrgPayload> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/oidc`,
    { method: "PUT", body: JSON.stringify(body) },
    token,
  );
}

export type OrgAuditEvent = {
  ts?: string;
  action?: string;
  org?: string;
  actor?: string;
  role?: string;
  detail?: Record<string, unknown>;
};

export function fetchOrgAudit(token: string): Promise<{ count: number; events: OrgAuditEvent[] }> {
  return authJson("/api/audit", undefined, token);
}

export type OrgInvoice = {
  id?: string;
  amount_inr?: number;
  status?: string;
  esign_status?: string;
  plan?: string;
  created_at?: string;
  org_id?: string;
};

export function fetchOrgInvoices(
  token: string,
): Promise<{ invoices: OrgInvoice[]; subscription: Record<string, unknown> | null }> {
  return authJson("/api/billing/invoices", undefined, token);
}

export function postSignOrgInvoice(
  invoiceId: string,
  token: string,
  signerEmail: string,
): Promise<{ id?: string; status?: string; esign_status?: string }> {
  return authJson(
    `/api/billing/msa/${encodeURIComponent(invoiceId)}/sign`,
    { method: "POST", body: JSON.stringify({ signer_email: signerEmail }) },
    token,
  );
}

export function fetchOrgPilotChecklist(orgId: string, token: string): Promise<{
  org_id: string;
  progress: { done: number; total: number; pct: number };
  items: Array<{ id: string; phase: string; label: string; done: boolean }>;
  notes?: string;
}> {
  return authJson(`/api/orgs/${encodeURIComponent(orgId)}/pilot-checklist`, undefined, token);
}

export function patchOrgPilotChecklist(
  orgId: string,
  token: string,
  body: { item_id?: string; done?: boolean; notes?: string },
): Promise<{
  progress: { done: number; total: number; pct: number };
  items: Array<{ id: string; phase: string; label: string; done: boolean }>;
  notes?: string;
}> {
  return authJson(
    `/api/orgs/${encodeURIComponent(orgId)}/pilot-checklist`,
    { method: "PATCH", body: JSON.stringify(body) },
    token,
  );
}

export function postLogout(token: string): Promise<{ status: string }> {
  return authJson("/api/auth/logout", { method: "POST" }, token);
}

export function fetchAuthMe(token: string): Promise<{ user: AuthUser }> {
  return authJson("/api/auth/me", undefined, token);
}

export function fetchPreferences(token: string): Promise<{ preferences: UserPreferences }> {
  return authJson("/api/auth/preferences", undefined, token);
}

export function putPreferences(
  token: string,
  patch: Partial<UserPreferences>,
): Promise<{ preferences: UserPreferences }> {
  return authJson(
    "/api/auth/preferences",
    { method: "PUT", body: JSON.stringify(patch) },
    token,
  );
}

export function fetchMarkets(): Promise<{
  count: number;
  markets: Market[];
  gci_deep_markets: string[];
  listed_markets?: string[];
  note: string;
}> {
  return getJson("/api/markets");
}

export function fetchMarketIndexes(marketId: string): Promise<{
  market_id: string;
  count: number;
  indexes: MarketIndex[];
  gci_deep: boolean;
}> {
  return getJson(`/api/markets/${encodeURIComponent(marketId)}/indexes`);
}

export function fetchIndexConstituents(indexId: string): Promise<{
  index: MarketIndex;
  count: number;
  constituents: unknown[];
  gci_deep: boolean;
}> {
  return getJson(`/api/indexes/${encodeURIComponent(indexId)}/constituents`);
}

export type HistoryPoint = {
  date: string;
  close: number;
  volume?: number;
};

export type IndexHistory = {
  index_id: string;
  market_id: string;
  name: string;
  ticker: string;
  years: number;
  points: HistoryPoint[];
  point_count: number;
  last: number;
  change_pct: number | null;
  data_quality: string;
  kind: string;
  note: string;
};

export type StockHistory = {
  stock_id: string;
  name: string;
  ticker: string;
  market_id?: string;
  years: number;
  points: HistoryPoint[];
  point_count: number;
  last: number;
  change_pct: number | null;
  fundamentals: {
    fiscal_year: string;
    revenue_growth_pct?: number;
    operating_margin_pct?: number;
  }[];
  data_quality: string;
  kind: string;
  note: string;
};

export function fetchMarketHistory(
  marketId: string,
  opts?: { index?: string; years?: number },
): Promise<{
  market_id: string;
  market_name: string;
  currency: string;
  index: IndexHistory;
  kind: string;
  note: string;
}> {
  const params = new URLSearchParams();
  if (opts?.index) params.set("index", opts.index);
  if (opts?.years) params.set("years", String(opts.years));
  const qs = params.toString();
  return getJson(
    `/api/markets/${encodeURIComponent(marketId)}/history${qs ? `?${qs}` : ""}`,
  );
}

export function fetchStockHistory(
  stockId: string,
  years = 5,
): Promise<StockHistory> {
  return getJson(
    `/api/stocks/${encodeURIComponent(stockId)}/history?years=${years}`,
  );
}

export type LabelDraft = {
  id: string;
  status: string;
  company_id: string;
  period: string;
  metric: string;
  guided_low?: number | null;
  guided_high?: number | null;
  guided_value?: number | null;
  actual_value?: number | null;
  guided_text?: string;
  quote_span?: string | null;
  source_url?: string | null;
  source_ref?: string | null;
  submitter_id?: string;
  reviewer_id?: string | null;
};

export function fetchLabelCompanies(): Promise<{
  count: number;
  companies: {
    company_id: string;
    ticker: string;
    name: string;
    data_quality: string;
    gci_score: number | null;
  }[];
}> {
  return getJson("/api/labeling/companies", { headers: authHeaders() });
}

export function fetchLabelDrafts(opts?: {
  companyId?: string;
  status?: string;
}): Promise<{ count: number; drafts: LabelDraft[] }> {
  const params = new URLSearchParams();
  if (opts?.companyId) params.set("company_id", opts.companyId);
  if (opts?.status) params.set("status", opts.status);
  const qs = params.toString();
  return getJson(`/api/labeling/drafts${qs ? `?${qs}` : ""}`, {
    headers: authHeaders(),
  });
}

export function postLabelDraft(body: Record<string, unknown>): Promise<{
  ok: boolean;
  draft: LabelDraft;
}> {
  return getJson("/api/labeling/drafts", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export function postLabelDraftAction(
  draftId: string,
  action: "submit" | "accept" | "reject",
  comment?: string,
): Promise<{ ok: boolean; draft: LabelDraft }> {
  return getJson(`/api/labeling/drafts/${encodeURIComponent(draftId)}/${action}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(action === "reject" ? { comment: comment || "" } : {}),
  });
}

export function postLabelImportCsv(csv: string): Promise<{
  ok: boolean;
  created: number;
  errors: { line: number; detail: string }[];
}> {
  return getJson("/api/labeling/import", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ csv }),
  });
}

export type FeedbackItem = {
  id: string;
  company_id?: string | null;
  org_id?: string | null;
  period?: string | null;
  metric?: string | null;
  kind: string;
  comment: string;
  status: string;
  nps?: number | null;
  created_at?: string;
};

export function fetchFeedback(status?: string): Promise<{
  count: number;
  items: FeedbackItem[];
}> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return getJson(`/api/feedback${qs}`, { headers: authHeaders() });
}

export function postFeedback(body: {
  company_id?: string;
  period?: string;
  metric?: string;
  kind: string;
  comment?: string;
  nps?: number;
}): Promise<{ ok: boolean; item: FeedbackItem }> {
  return getJson("/api/feedback", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
}

export type AbuseChallenge = {
  challenge_id: string;
  prompt: string;
  expires_in_sec: number;
};

export function fetchAbuseChallenge(): Promise<AbuseChallenge> {
  return getJson("/api/auth/abuse-challenge");
}

export function postPilotRequest(body: {
  name: string;
  email: string;
  firm: string;
  role?: string;
  team_size?: string;
  message?: string;
  challenge_id?: string;
  challenge_answer?: string;
}): Promise<{ ok: boolean; request_id: string; status: string; submitted_at: string }> {
  return getJson("/api/pilot-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function patchFeedback(
  itemId: string,
  status: string,
): Promise<{ ok: boolean; item: FeedbackItem }> {
  return getJson(`/api/feedback/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  });
}
