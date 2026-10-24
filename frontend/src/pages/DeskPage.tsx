import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import ChangeChip from "../components/ChangeChip";
import {
  BarChart,
  CompareBars,
  DonutChart,
  FAMILY_COLORS,
  LineChart,
} from "../components/Charts";
import CompanyPicker from "../components/CompanyPicker";
import DeskConsole from "../components/DeskConsole";
import Disclaimer from "../components/Disclaimer";
import InfoTip from "../components/InfoTip";
import PilotChecklistPanel from "../components/PilotChecklistPanel";
import LabelWorkbench from "../components/LabelWorkbench";
import FeedbackInbox from "../components/FeedbackInbox";
import TabBar from "../components/TabBar";
import Toast from "../components/Toast";
import PlanAccessGate from "../components/PlanAccessGate";
import {
  apiDocsUrl,
  demoApiKey,
  fetchBadge,
  fetchCompanies,
  fetchCompanyGci,
  fetchExtractPending,
  fetchHistory,
  fetchOrg,
  fetchMetrics,
  fetchReviews,
  fetchVernacular,
  fetchWordmap,
  postAlphaHunterImport,
  fetchAlphaHunterStatus,
  postAlphaHunterLive,
  fetchNiftyMilestones,
  postNiftyEnqueueLabeling,
  fetchCsmDashboard,
  postCsmTicket,
  postExtract,
  postExtractCommit,
  postIngestPaste,
  postIngestUrl,
  postIngestRefresh,
  fetchCrawlStatus,
  fetchDocuments,
  postDocumentReview,
  fetchCorpusCoverage,
  fetchPendingDepth,
  postPendingDepthBootstrap,
  postIngestCrawl,
  postConsensusImport,
  fetchConsensusStats,
  fetchSsoStatus,
  fetchReportTemplates,
  postGenerateReport,
  downloadIcAuditPdf,
  fetchOpsThroughput,
  fetchPitContract,
  fetchPitHistoryV1,
  postEnsureCitations,
  postTierFoundation,
  fetchLabelingQueue,
  postLabelingQueue,
  patchLabelingQueue,
  fetchEmFactorCsvUrl,
  type BadgePayload,
  type CompanyGCIDetail,
  type CompanySummary,
  type MetricCatalogRow,
  type OrgPayload,
  type PendingExtractBatch,
  type ReviewRecord,
  type VernacularPayload,
  type WordmapPayload,
  type LabelingQueueItem,
} from "../lib/api";
import { formatScore, formatCompanyScore, metricDisplayName } from "../lib/score";
import { tipText } from "../lib/glossary";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";
import { useI18n } from "../i18n";

const TABS = [
  { id: "console", labelKey: "ui.DeskPage.tab.console", titleKey: "ui.DeskPage.tab.consoleTitle" },
  { id: "review", labelKey: "ui.DeskPage.tab.review", title: tipText("extract") },
  { id: "corpus", labelKey: "ui.DeskPage.tab.corpus", title: tipText("tier1") },
  { id: "reports", labelKey: "ui.DeskPage.tab.reports", title: tipText("citability") },
  { id: "pit", labelKey: "ui.DeskPage.tab.pit", title: tipText("pit") },
  { id: "import", labelKey: "ui.DeskPage.tab.import", title: tipText("alphahunter") },
  { id: "parameters", labelKey: "ui.DeskPage.tab.parameters", title: tipText("gci_parameter") },
  { id: "wordmap", labelKey: "ui.DeskPage.tab.wordmap", title: tipText("sentiment") },
  { id: "vernacular", labelKey: "ui.DeskPage.tab.vernacular", title: tipText("gci") },
  { id: "labeling", labelKey: "ui.DeskPage.tab.labeling", title: tipText("labeling_queue") },
  { id: "feedback", labelKey: "ui.DeskPage.tab.feedback", titleKey: "ui.DeskPage.tab.feedbackTitle" },
  { id: "csm", labelKey: "ui.DeskPage.tab.csm", title: tipText("csm") },
] as const;

type TabId = (typeof TABS)[number]["id"];

const PRIMARY_TABS = TABS.filter((t) =>
  ["console", "review", "corpus", "reports", "pit"].includes(t.id),
);
const MORE_TAB_IDS = new Set(["import", "parameters", "wordmap", "vernacular", "labeling", "feedback", "csm"]);

const DEFAULT_FACTS = `[
  {
    "period": "FY25",
    "metric": "revenue_growth_pct",
    "guided_low": 5,
    "guided_high": 8,
    "actual_value": 7.1,
    "guidance_change": "Imported guidance fact",
    "source_ref": "alphahunter-demo"
  }
]`;

type StatementDecision = {
  action: "accept" | "reject";
  editing: boolean;
  period: string;
  low: string;
  high: string;
};

export default function DeskPage() {
  const { preferences } = useAuth();
  const { has } = useEntitlements();
  const { t, lang: uiLang } = useI18n();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab: TabId = TABS.some((x) => x.id === tabParam)
    ? (tabParam as TabId)
    : "console";
  const setTab = useCallback(
    (id: TabId) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("tab", id);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );
  const dismissToast = useCallback(() => setMsg(null), []);
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [companyId, setCompanyId] = useState("infy");
  const [detail, setDetail] = useState<CompanyGCIDetail | null>(null);
  const [history, setHistory] = useState<
    {
      as_of: string;
      gci_score: number | null;
      change_pct?: number | null;
      change_horizon?: string | null;
    }[]
  >([]);
  const [wordmap, setWordmap] = useState<WordmapPayload | null>(null);
  const [vernacular, setVernacular] = useState<VernacularPayload | null>(null);
  const [lang, setLang] = useState<string>(uiLang);

  useEffect(() => {
    setLang(uiLang);
  }, [uiLang]);
  const [badge, setBadge] = useState<BadgePayload | null>(null);
  const [org, setOrg] = useState<OrgPayload | null>(null);
  const [labelQueue, setLabelQueue] = useState<LabelingQueueItem[]>([]);
  const [factsJson, setFactsJson] = useState(DEFAULT_FACTS);
  const [ahStatus, setAhStatus] = useState<{
    configured: boolean;
    note: string;
    url_host: string | null;
  } | null>(null);
  const [niftyMs, setNiftyMs] = useState<{
    milestones: Array<{ id: string; title: string; target: string; status: string }>;
    counts: Record<string, number>;
    nifty_extra_ids?: string[];
    note: string;
    progress: { done: number; total: number };
  } | null>(null);
  const [csmDash, setCsmDash] = useState<Awaited<ReturnType<typeof fetchCsmDashboard>> | null>(
    null,
  );
  const [ticketSubject, setTicketSubject] = useState("");
  const [catalog, setCatalog] = useState<MetricCatalogRow[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [apiOut, setApiOut] = useState<string>("");

  // Review queue state
  const [pasteText, setPasteText] = useState("");
  const [ingestUrlValue, setIngestUrlValue] = useState("");
  const [extractPeriod, setExtractPeriod] = useState("FY26");
  const [pendingBatches, setPendingBatches] = useState<PendingExtractBatch[]>([]);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [decisions, setDecisions] = useState<
    Record<string, Record<number, StatementDecision>>
  >({});
  const [queueBusy, setQueueBusy] = useState(false);
  const [crawlBusy, setCrawlBusy] = useState(false);
  const [pendingDocs, setPendingDocs] = useState(0);
  const [lastCrawl, setLastCrawl] = useState<string | null>(null);
  const [foundationBusy, setFoundationBusy] = useState(false);
  const [reportTemplates, setReportTemplates] = useState<
    Array<{ id: string; name: string; role: string; industry: string }>
  >([]);
  const [reportTpl, setReportTpl] = useState("ic_audit");
  const [reportMd, setReportMd] = useState<string | null>(null);
  const [reportJson, setReportJson] = useState<string | null>(null);
  const [throughput, setThroughput] = useState<Record<string, unknown> | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [corpusCov, setCorpusCov] = useState<Record<string, unknown> | null>(null);
  const [pendingDepth, setPendingDepth] = useState<Record<string, unknown> | null>(null);
  const [pendingDocRows, setPendingDocRows] = useState<Record<string, unknown>[]>([]);
  const [consensusJson, setConsensusJson] = useState("");
  const [consensusStats, setConsensusStats] = useState<{
    row_count: number;
    company_count: number;
  } | null>(null);
  const [ssoStatus, setSsoStatus] = useState<{
    enabled?: boolean;
    configured?: boolean;
    production_ready?: boolean;
    ready?: boolean;
    note?: string;
    checklist?: Record<string, boolean>;
  } | null>(null);
  const [labelNiftyOnly, setLabelNiftyOnly] = useState(false);

  const market = preferences?.default_market ?? "IN";
  const index = preferences?.default_index ?? "SENSEX";

  const selected = useMemo(
    () => companies.find((c) => c.id === companyId) ?? null,
    [companies, companyId]
  );

  useEffect(() => {
    fetchCompanies({ market, index, limit: 200 })
      .then((rows) => {
        setCompanies(rows);
        if (!rows.find((r) => r.id === companyId) && rows[0]) {
          setCompanyId(rows[0].id);
        }
      })
      .catch((e: Error) => setError(e.message));
    fetchOrg("demo")
      .then(setOrg)
      .catch(() => setOrg(null));
    fetchLabelingQueue()
      .then((r) => setLabelQueue(r.items || []))
      .catch(() => setLabelQueue([]));
    fetchAlphaHunterStatus()
      .then(setAhStatus)
      .catch(() => setAhStatus(null));
    fetchNiftyMilestones()
      .then((r) =>
        setNiftyMs({
          milestones: r.milestones,
          counts: r.counts as Record<string, number>,
          nifty_extra_ids: r.nifty_extra_ids,
          note: r.note,
          progress: r.progress,
        }),
      )
      .catch(() => setNiftyMs(null));
    fetchCsmDashboard("demo")
      .then(setCsmDash)
      .catch(() => setCsmDash(null));
    fetchMetrics()
      .then((r) => setCatalog(r.metrics))
      .catch(() => setCatalog([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market, index]);

  useEffect(() => {
    if (!companyId) return;
    const row = companies.find((c) => c.id === companyId);
    if (row?.data_quality === "market_scaffold" || (row && row.gci_score == null && row.market_id && row.market_id !== "IN")) {
      setDetail(null);
      setHistory([]);
      setWordmap(null);
      setVernacular(null);
      setBadge(null);
      setError(null);
      setMsg(t("desk.scaffold"));
      return;
    }
    setError(null);
    setMsg(null);
    Promise.all([
      fetchCompanyGci(companyId),
      fetchHistory(companyId),
      fetchWordmap(companyId),
      fetchVernacular(companyId, lang),
    ])
      .then(([d, h, w, v]) => {
        setDetail(d);
        setHistory(h);
        setWordmap(w);
        setVernacular(v);
        return fetchBadge(d.ticker).catch(() => null);
      })
      .then(setBadge)
      .catch((e: Error) => setError(e.message));
  }, [companyId, lang, companies]);

  const loadQueue = (cid: string) => {
    fetchExtractPending(cid)
      .then((r) => setPendingBatches(r.batches.filter((b) => b.status === "pending")))
      .catch(() => setPendingBatches([]));
    fetchReviews()
      .then((r) => setReviews(r.reviews.slice(-10).reverse()))
      .catch(() => setReviews([]));
  };

  useEffect(() => {
    if (tab === "review" && companyId) loadQueue(companyId);
    if (tab === "review" || tab === "corpus") {
      fetchCrawlStatus()
        .then((s) => {
          setPendingDocs(s.pending_total);
          setLastCrawl(
            s.last && typeof s.last.as_of === "string" ? String(s.last.as_of) : null
          );
        })
        .catch(() => {
          setPendingDocs(0);
          setLastCrawl(null);
        });
      fetchDocuments({ review_status: "pending" })
        .then((r) => {
          setPendingDocs(r.count);
          setPendingDocRows(r.documents || []);
        })
        .catch(() => undefined);
    }
    if (tab === "corpus") {
      fetchCorpusCoverage()
        .then((c) => setCorpusCov(c as Record<string, unknown>))
        .catch(() => setCorpusCov(null));
      fetchPendingDepth()
        .then((d) => setPendingDepth(d))
        .catch(() => setPendingDepth(null));
    }
    if (tab === "import") {
      fetchConsensusStats()
        .then(setConsensusStats)
        .catch(() => setConsensusStats(null));
    }
    if (tab === "csm" || tab === "console") {
      fetchSsoStatus()
        .then((s) => setSsoStatus(s))
        .catch(() => setSsoStatus(null));
    }
    if (tab === "reports") {
      fetchReportTemplates()
        .then((r) => {
          setReportTemplates(r.templates || []);
          if (r.templates?.[0] && !r.templates.find((t) => t.id === reportTpl)) {
            setReportTpl(r.templates[0].id);
          }
        })
        .catch(() => setReportTemplates([]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, companyId]);

  const decisionFor = (batchId: string, idx: number): StatementDecision =>
    decisions[batchId]?.[idx] ?? {
      action: "accept",
      editing: false,
      period: "",
      low: "",
      high: "",
    };

  const setDecision = (batchId: string, idx: number, patch: Partial<StatementDecision>) => {
    setDecisions((prev) => ({
      ...prev,
      [batchId]: {
        ...(prev[batchId] ?? {}),
        [idx]: { ...decisionFor(batchId, idx), ...patch },
      },
    }));
  };

  const commitBatch = async (batch: PendingExtractBatch) => {
    setQueueBusy(true);
    try {
      const accepted: number[] = [];
      const edits: Record<number, Record<string, unknown>> = {};
      batch.statements.forEach((_, i) => {
        const d = decisionFor(batch.id, i);
        if (d.action === "reject") return;
        accepted.push(i);
        const e: Record<string, unknown> = {};
        if (d.period.trim()) e.period = d.period.trim();
        if (d.low.trim() !== "") e.guided_low = Number(d.low);
        if (d.high.trim() !== "") e.guided_high = Number(d.high);
        if (d.low.trim() !== "" && d.high.trim() !== "") {
          e.guided_value = (Number(d.low) + Number(d.high)) / 2;
        }
        if (Object.keys(e).length > 0) edits[i] = e;
      });
      const res = await postExtractCommit({
        extract_id: batch.id,
        accepted_indices: accepted,
        edits: Object.keys(edits).length > 0 ? edits : undefined,
      });
      setMsg(
        t("ui.DeskPage.review.committed", { n: res.committed }) +
          (res.edited ? t("ui.DeskPage.review.committedEdited", { n: res.edited }) : "") +
          t("ui.DeskPage.review.committedRejected", {
            n: batch.statements.length - accepted.length,
          })
      );
      loadQueue(companyId);
      const d = await fetchCompanyGci(companyId);
      setDetail(d);
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setQueueBusy(false);
    }
  };

  const picker = (
    <div className="desk-picker-row">
      <CompanyPicker
        companies={companies}
        value={companyId}
        onChange={setCompanyId}
      />
      {detail && (
        <span className="muted" style={{ fontSize: 13 }}>
          GCI {formatCompanyScore(detail.gci_score)} ·{" "}
          <Link to={`/companies/${companyId}`}>{t("ui.DeskPage.picker.dossier")}</Link>
          {" · "}
          <Link to="/tracker">{t("ui.DeskPage.picker.universe")}</Link>
        </span>
      )}
    </div>
  );

  const moreTabs = TABS.filter((t) => {
    if (!MORE_TAB_IDS.has(t.id)) return false;
    if (t.id === "labeling") return has("labeling") || has("desk");
    if (t.id === "feedback") return has("feedback");
    if (t.id === "import") return has("desk_write");
    if (t.id === "wordmap") return has("wordmap") || has("desk");
    return true;
  });

  const primaryTabs = PRIMARY_TABS.filter((t) => {
    if (t.id === "review" || t.id === "corpus") return has("desk_write") || has("desk");
    if (t.id === "reports" || t.id === "pit") return has("ic_export") || has("desk");
    return true;
  });

  const tabItem = (x: (typeof TABS)[number]) => ({
    id: x.id,
    label: t(x.labelKey),
    title: "titleKey" in x ? t(x.titleKey) : x.title,
  });

  return (
    <PlanAccessGate
      feature="desk"
      title={t("desk.title")}
      kicker={t("desk.kicker")}
      description={t("ui.DeskPage.gate.description")}
      returnTo="/desk"
      testId="desk-access-gate"
    >
    <section className="desk-page" data-testid="desk-page">
      <Toast message={msg} onDismiss={dismissToast} />
      <p className="page-kicker">{t("desk.kicker")}</p>
      <h1>
        {t("desk.title")} <InfoTip termId="desk_sku" />
      </h1>
      <p className="muted lede">{t("desk.lede")}</p>

      <div className="desk-sticky">
        {picker}
        <TabBar
          tabs={[
            ...primaryTabs.map(tabItem),
            { id: "more", label: t("ui.DeskPage.tab.more"), title: t("ui.DeskPage.tab.moreTitle") },
          ]}
          active={MORE_TAB_IDS.has(tab) ? "more" : tab}
          onChange={(id) => {
            if (id === "more") setTab("import");
            else if (TABS.some((x) => x.id === id)) setTab(id as TabId);
          }}
          ariaLabel={t("ui.DeskPage.tab.ariaSections")}
        />
        {MORE_TAB_IDS.has(tab) && (
          <div className="desk-more-tabs" role="tablist" aria-label={t("ui.DeskPage.tab.ariaMore")}>
            {moreTabs.map((tb) => (
              <button
                key={tb.id}
                type="button"
                className={`tab-bar-btn ${tab === tb.id ? "active" : ""}`}
                onClick={() => setTab(tb.id)}
              >
                {t(tb.labelKey)}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {tab === "console" && (
        <DeskConsole
          companyId={companyId}
          onSelectCompany={setCompanyId}
          onJumpTab={(id) => {
            if (id === "tracker") navigate("/tracker");
            else if (id === "sectors") navigate("/tracker?tab=sectors");
            else if (id === "evidence") navigate(`/companies/${companyId}`);
            else if (TABS.some((x) => x.id === id)) setTab(id as TabId);
          }}
        />
      )}

      {tab === "review" && (
        <div className="panel desk-panel" data-testid="review-queue-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.review.title")} <InfoTip termId="extract" />
          </h2>
          <p className="muted">{t("ui.DeskPage.review.lede")}</p>

          <div className="crawl-bar" data-testid="crawl-bar">
            <div>
              <strong>{t("ui.DeskPage.review.liveRefresh")}</strong>
              <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                {t("ui.DeskPage.review.scheduler.before")}{" "}
                <strong>{t("ui.DeskPage.review.scheduler.hours")}</strong> {t("ui.DeskPage.review.scheduler.service")}{" "}
                <code className="inline-code">scheduler</code> {t("ui.DeskPage.review.scheduler.or")}{" "}
                <code className="inline-code">scripts/gci-refresh-loop.sh</code>
                {t("ui.DeskPage.review.scheduler.after")}
                {pendingDocs > 0
                  ? t("ui.DeskPage.review.docsAwaiting", { n: pendingDocs })
                  : t("ui.DeskPage.review.noPendingDocs")}
                {lastCrawl ? t("ui.DeskPage.common.lastCrawl", { when: lastCrawl }) : ""}
              </p>
            </div>
            <button
              type="button"
              className="btn"
              disabled={crawlBusy || queueBusy}
              data-testid="run-ir-crawl"
              onClick={async () => {
                setCrawlBusy(true);
                try {
                  const r = await postIngestRefresh({ limit: 30, live: true });
                  const c = r.crawl || {};
                  const ex = r.extract || {};
                  setMsg(
                    t("ui.DeskPage.review.liveRefreshToast", {
                      newDocs: String(c.pending_new ?? 0),
                      batches: String(ex.batches ?? 0),
                      pending: String(c.pending_total ?? 0),
                    })
                  );
                  setPendingDocs(Number(c.pending_total ?? pendingDocs));
                  setLastCrawl(String(c.as_of ?? new Date().toISOString()));
                  loadQueue(companyId);
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setCrawlBusy(false);
                }
              }}
            >
              {crawlBusy ? t("ui.DeskPage.review.refreshing") : t("ui.DeskPage.review.runLiveRefresh")}
            </button>
          </div>

          <div className="queue-ingest">
            <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
              {t("ui.DeskPage.review.primaryPath.before")} <strong>{t("ui.DeskPage.review.primaryPath.exception")}</strong> {t("ui.DeskPage.review.primaryPath.after")}
            </p>
            <label className="desk-field">
              <span className="field-label">{t("ui.DeskPage.review.pasteLabel")}</span>
              <textarea
                rows={6}
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={t("ui.DeskPage.review.pastePlaceholder")}
                spellCheck={false}
                data-testid="queue-paste"
              />
            </label>
            <div className="queue-ingest-row">
              <input
                value={ingestUrlValue}
                onChange={(e) => setIngestUrlValue(e.target.value)}
                placeholder={t("ui.DeskPage.review.urlPlaceholder")}
                data-testid="queue-url"
              />
              <input
                value={extractPeriod}
                onChange={(e) => setExtractPeriod(e.target.value)}
                style={{ maxWidth: 90 }}
                aria-label={t("ui.DeskPage.review.periodAria")}
              />
              <button
                type="button"
                className="btn ghost"
                disabled={queueBusy || (!pasteText.trim() && !ingestUrlValue.trim())}
                onClick={async () => {
                  setQueueBusy(true);
                  try {
                    if (pasteText.trim()) {
                      const r = await postIngestPaste({
                        company_id: companyId,
                        text: pasteText,
                      });
                      const n = r.extract?.statements?.length ?? 0;
                      setMsg(
                        n > 0
                          ? t("ui.DeskPage.review.ingestedPasteExtracted", { doc: r.document.doc_id, n })
                          : t("ui.DeskPage.review.ingestedPasteNone", { doc: r.document.doc_id })
                      );
                      if (n > 0) loadQueue(companyId);
                    } else {
                      const r = await postIngestUrl({
                        company_id: companyId,
                        url: ingestUrlValue.trim(),
                      });
                      const n = r.extract?.statements?.length ?? 0;
                      setMsg(
                        n > 0
                          ? t("ui.DeskPage.review.ingestedUrlExtracted", { doc: r.document.doc_id, n })
                          : t("ui.DeskPage.review.ingestedUrl", { doc: r.document.doc_id })
                      );
                      if (n > 0) loadQueue(companyId);
                    }
                  } catch (e) {
                    setMsg((e as Error).message);
                  } finally {
                    setQueueBusy(false);
                  }
                }}
              >
                {t("ui.DeskPage.review.ingestBtn")}
              </button>
              <button
                type="button"
                className="btn"
                disabled={queueBusy}
                data-testid="queue-extract"
                onClick={async () => {
                  setQueueBusy(true);
                  try {
                    const res = await postExtract(companyId, {
                      text: pasteText.trim() || undefined,
                      period: extractPeriod,
                      sourceRef: pasteText.trim() ? "desk-paste" : "seed-transcript",
                    });
                    setMsg(
                      res.count > 0
                        ? t("ui.DeskPage.review.extracted", { n: res.count })
                        : t("ui.DeskPage.review.extractedNone")
                    );
                    loadQueue(companyId);
                  } catch (e) {
                    setMsg((e as Error).message);
                  } finally {
                    setQueueBusy(false);
                  }
                }}
              >
                {pasteText.trim() ? t("ui.DeskPage.review.runExtract") : t("ui.DeskPage.review.runExtractDemo")}
              </button>
            </div>
          </div>

          <h3 style={{ marginBottom: 4 }}>{t("ui.DeskPage.review.pendingTitle")}</h3>
          {pendingBatches.length === 0 && (
            <p className="muted" data-testid="queue-empty">
              {t("ui.DeskPage.review.queueEmpty")}
            </p>
          )}
          {pendingBatches.map((batch) => (
            <div className="queue-batch" key={batch.id} data-testid={`batch-${batch.id}`}>
              <div className="queue-batch-head">
                <span className="muted" style={{ fontSize: 12 }}>
                  {batch.sample ? (
                    <span className="quality-badge demo" data-testid={`batch-demo-${batch.id}`}>
                      {t("ui.DeskPage.review.demoSample")}
                    </span>
                  ) : null}{" "}
                  {t("ui.DeskPage.review.batch")} <code className="inline-code">{batch.id.slice(0, 8)}</code> ·{" "}
                  {t("ui.DeskPage.review.statementCount", { n: batch.statements.length })}
                </span>
                <button
                  type="button"
                  className="btn small"
                  disabled={queueBusy}
                  data-testid={`commit-${batch.id}`}
                  onClick={() => commitBatch(batch)}
                >
                  {t("ui.DeskPage.review.commit")}
                </button>
              </div>
              {batch.statements.map((s, i) => {
                const d = decisionFor(batch.id, i);
                return (
                  <div
                    className={`queue-stmt ${d.action}`}
                    key={`${batch.id}-${i}`}
                    data-testid={`stmt-${batch.id}-${i}`}
                  >
                    <div className="queue-stmt-main">
                      <div className="queue-stmt-meta">
                        <strong>{s.metric.replaceAll("_", " ")}</strong>
                        <span className="muted">{s.period}</span>
                        <span className="queue-band">
                          {s.guided_low != null && s.guided_high != null
                            ? `${s.guided_low}–${s.guided_high}`
                            : s.guided_value}
                        </span>
                        <span className="muted">{t("ui.DeskPage.review.conf", { n: s.confidence })}</span>
                        <span className="muted">{s.speaker}</span>
                      </div>
                      <p className="muted queue-quote">“{s.guided_text}”</p>
                      {d.editing && (
                        <div className="edit-form">
                          <label>
                            <span className="field-label">{t("ui.DeskPage.review.period")}</span>
                            <input
                              value={d.period || s.period}
                              onChange={(e) =>
                                setDecision(batch.id, i, { period: e.target.value })
                              }
                            />
                          </label>
                          <label>
                            <span className="field-label">{t("ui.DeskPage.review.guidedLow")}</span>
                            <input
                              type="number"
                              value={d.low}
                              placeholder={String(s.guided_low ?? "")}
                              onChange={(e) =>
                                setDecision(batch.id, i, { low: e.target.value })
                              }
                            />
                          </label>
                          <label>
                            <span className="field-label">{t("ui.DeskPage.review.guidedHigh")}</span>
                            <input
                              type="number"
                              value={d.high}
                              placeholder={String(s.guided_high ?? "")}
                              onChange={(e) =>
                                setDecision(batch.id, i, { high: e.target.value })
                              }
                            />
                          </label>
                        </div>
                      )}
                    </div>
                    <div className="review-actions">
                      <button
                        type="button"
                        className={`btn ghost small ${d.action === "accept" && !d.editing ? "active-lang" : ""}`}
                        onClick={() =>
                          setDecision(batch.id, i, { action: "accept", editing: false })
                        }
                      >
                        {t("ui.DeskPage.common.accept")}
                      </button>
                      <button
                        type="button"
                        className={`btn ghost small ${d.editing ? "active-lang" : ""}`}
                        onClick={() =>
                          setDecision(batch.id, i, { action: "accept", editing: !d.editing })
                        }
                      >
                        {t("ui.DeskPage.review.edit")}
                      </button>
                      <button
                        type="button"
                        className={`btn ghost small ${d.action === "reject" ? "active-lang" : ""}`}
                        onClick={() =>
                          setDecision(batch.id, i, { action: "reject", editing: false })
                        }
                      >
                        {t("ui.DeskPage.common.reject")}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}

          <h3 style={{ marginBottom: 4 }}>{t("ui.DeskPage.review.historyTitle")}</h3>
          {reviews.length === 0 ? (
            <p className="muted">{t("ui.DeskPage.review.historyEmpty")}</p>
          ) : (
            <div className="table-scroll">
              <table className="table" data-testid="review-history">
                <thead>
                  <tr>
                    <th>{t("ui.DeskPage.review.colWhen")}</th>
                    <th>{t("ui.DeskPage.common.company")}</th>
                    <th>{t("ui.DeskPage.review.colAction")}</th>
                    <th>{t("ui.DeskPage.review.colSource")}</th>
                    <th>{t("ui.DeskPage.review.colEdits")}</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((r, i) => (
                    <tr key={`${r.at}-${i}`}>
                      <td>{r.at ? r.at.slice(0, 16).replace("T", " ") : "—"}</td>
                      <td>{r.company_id}</td>
                      <td>
                        <span className={`pill ${r.action === "reject" ? "missed" : "met"}`}>
                          {r.action}
                        </span>
                      </td>
                      <td>{r.source ?? "dossier"}</td>
                      <td className="evidence-text">
                        {r.edits && Object.keys(r.edits).length > 0
                          ? Object.entries(r.edits)
                              .map(([k, v]) => `${k}=${String(v)}`)
                              .join(", ")
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Disclaimer compact />
        </div>
      )}

      {tab === "corpus" && (
        <div className="panel desk-panel" data-testid="corpus-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.corpus.title")} <InfoTip termId="tier1" />
          </h2>
          <p className="muted">{t("ui.DeskPage.corpus.lede")}</p>
          <div className="metrics" data-testid="corpus-coverage">
            <div className="metric">
              <div className="label">{t("ui.DeskPage.corpus.tier1Pass")}</div>
              <div className="value" style={{ fontSize: 20 }}>
                {String(corpusCov?.tier1_gate_pass ?? corpusCov?.tier1_pass ?? "—")} /{" "}
                {String(
                  corpusCov?.hand_labeled_sensex ??
                    (Array.isArray(corpusCov?.companies)
                      ? (corpusCov.companies as unknown[]).length
                      : corpusCov?.companies) ??
                    "—",
                )}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.corpus.tier1Rate")}</div>
              <div className="value" style={{ fontSize: 20 }}>
                {corpusCov?.tier1_gate_rate != null || corpusCov?.tier1_rate_pct != null
                  ? `${Number(corpusCov?.tier1_gate_rate ?? corpusCov?.tier1_rate_pct).toFixed(1)}%`
                  : "—"}
              </div>
            </div>
          </div>
          {pendingDepth && (
            <p className="muted" style={{ fontSize: 13 }} data-testid="pending-depth-summary">
              {t("ui.DeskPage.corpus.depthLlm")}{" "}
              {String(
                (pendingDepth.flags as Record<string, unknown> | undefined)?.LLM_CONFIGURED ??
                  pendingDepth.llm_configured ??
                  "—",
              )}{" "}
              · SSO{" "}
              {String(
                ((pendingDepth.sso as Record<string, unknown> | undefined)?.production_ready ??
                  "—") as string,
              )}
            </p>
          )}
          <div className="crawl-bar">
            <div>
              <strong>{t("ui.DeskPage.corpus.ingestLag")}</strong>
              <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                {t("ui.DeskPage.corpus.refreshEvery")}
                {pendingDocs > 0
                  ? t("ui.DeskPage.corpus.docsPending", { n: pendingDocs })
                  : t("ui.DeskPage.corpus.queueClear")}
                {lastCrawl ? t("ui.DeskPage.common.lastCrawl", { when: lastCrawl }) : ""}
              </p>
            </div>
            <button
              type="button"
              className="btn"
              disabled={foundationBusy}
              data-testid="run-tier-foundation"
              onClick={async () => {
                setFoundationBusy(true);
                try {
                  const r = await postTierFoundation();
                  const cites = (r.citations || {}) as { companies?: number; linked?: number };
                  const pit = (r.pit_warehouse || {}) as {
                    companies?: number;
                    min_n?: number;
                  };
                  setMsg(
                    t("ui.DeskPage.corpus.foundationToast", {
                      n: cites.companies ?? 0,
                      minN: pit.min_n ?? "—",
                    })
                  );
                  const c = await fetchCorpusCoverage();
                  setCorpusCov(c as Record<string, unknown>);
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setFoundationBusy(false);
                }
              }}
            >
              {foundationBusy ? t("ui.DeskPage.corpus.building") : t("ui.DeskPage.corpus.buildFoundation")}
            </button>
          </div>
          <div className="queue-ingest-row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn ghost"
              disabled={crawlBusy}
              data-testid="corpus-crawl-dry"
              onClick={async () => {
                setCrawlBusy(true);
                try {
                  const r = await postIngestCrawl({ limit: 30, dry_run: true, live: false });
                  setMsg(
                    t("ui.DeskPage.corpus.crawlDryToast", {
                      newDocs: r.pending_new,
                      total: r.pending_total,
                    }),
                  );
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setCrawlBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.corpus.crawlDry")}
            </button>
            <button
              type="button"
              className="btn ghost"
              disabled={crawlBusy}
              data-testid="corpus-crawl-live"
              onClick={async () => {
                setCrawlBusy(true);
                try {
                  const r = await postIngestCrawl({ limit: 30, dry_run: false, live: true });
                  setMsg(
                    t("ui.DeskPage.corpus.crawlLiveToast", {
                      newDocs: r.pending_new,
                      total: r.pending_total,
                    }),
                  );
                  const docs = await fetchDocuments({ review_status: "pending" });
                  setPendingDocs(docs.count);
                  setPendingDocRows(docs.documents || []);
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setCrawlBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.corpus.crawlLive")}
            </button>
            <button
              type="button"
              className="btn ghost"
              disabled={foundationBusy}
              data-testid="pending-depth-bootstrap"
              onClick={async () => {
                setFoundationBusy(true);
                try {
                  const r = await postPendingDepthBootstrap();
                  setMsg(t("ui.DeskPage.corpus.bootstrapToast", { json: JSON.stringify(r).slice(0, 120) }));
                  setPendingDepth(await fetchPendingDepth());
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setFoundationBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.corpus.bootstrap")}
            </button>
          </div>
          <div className="queue-ingest-row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn ghost"
              disabled={!companyId || foundationBusy}
              data-testid="ensure-citations-company"
              onClick={async () => {
                if (!companyId) return;
                setFoundationBusy(true);
                try {
                  const r = await postEnsureCitations({ company_id: companyId });
                  setMsg(
                    t("ui.DeskPage.corpus.boundToast", { n: String(r.linked ?? 0), company: companyId }) +
                      (r.pit ? t("ui.DeskPage.corpus.boundPit", { n: String((r.pit as { n?: number }).n) }) : "")
                  );
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setFoundationBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.corpus.bindCitations", { ticker: selected?.ticker || companyId })}
            </button>
            <button
              type="button"
              className="btn ghost"
              data-testid="ops-throughput"
              onClick={async () => {
                try {
                  const tput = await fetchOpsThroughput();
                  setThroughput(tput as unknown as Record<string, unknown>);
                  const u = tput.universe || {};
                  setMsg(
                    t("ui.DeskPage.corpus.throughputToast", {
                      citeable: String(u.citeable_outcomes),
                      total: String(u.outcomes_total_hand_labeled),
                      pending: tput.backlog?.pending_docs_review ?? 0,
                    }),
                  );
                } catch (e) {
                  setMsg((e as Error).message);
                }
              }}
            >
              {t("ui.DeskPage.corpus.throughput")}
            </button>
          </div>
          {throughput && (
            <pre
              className="api-out"
              data-testid="ops-throughput-out"
              style={{ whiteSpace: "pre-wrap", maxHeight: 180, overflow: "auto" }}
            >
              {JSON.stringify(throughput, null, 2)}
            </pre>
          )}
          <h3 style={{ marginTop: 20 }}>{t("ui.DeskPage.corpus.pendingDocsTitle")}</h3>
          <div className="table-scroll">
            <table className="table" data-testid="pending-docs-table">
              <thead>
                <tr>
                  <th>{t("ui.DeskPage.common.company")}</th>
                  <th>{t("ui.DeskPage.corpus.colType")}</th>
                  <th>{t("ui.DeskPage.corpus.colTitle")}</th>
                  <th>{t("ui.DeskPage.corpus.colActions")}</th>
                </tr>
              </thead>
              <tbody>
                {pendingDocRows.slice(0, 40).map((d) => {
                  const id = String(d.id || "");
                  return (
                    <tr key={id}>
                      <td>{String(d.ticker || d.company_id || "—")}</td>
                      <td>{String(d.doc_type || "—")}</td>
                      <td>{String(d.title || d.url || id).slice(0, 60)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn ghost"
                          style={{ marginRight: 6 }}
                          onClick={async () => {
                            try {
                              await postDocumentReview({ doc_id: id, action: "accept" });
                              const docs = await fetchDocuments({ review_status: "pending" });
                              setPendingDocs(docs.count);
                              setPendingDocRows(docs.documents || []);
                              setMsg(t("ui.DeskPage.corpus.acceptedToast", { id }));
                            } catch (e) {
                              setMsg((e as Error).message);
                            }
                          }}
                        >
                          {t("ui.DeskPage.common.accept")}
                        </button>
                        <button
                          type="button"
                          className="btn ghost"
                          onClick={async () => {
                            try {
                              await postDocumentReview({ doc_id: id, action: "reject" });
                              const docs = await fetchDocuments({ review_status: "pending" });
                              setPendingDocs(docs.count);
                              setPendingDocRows(docs.documents || []);
                              setMsg(t("ui.DeskPage.corpus.rejectedToast", { id }));
                            } catch (e) {
                              setMsg((e as Error).message);
                            }
                          }}
                        >
                          {t("ui.DeskPage.common.reject")}
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {pendingDocRows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                      {t("ui.DeskPage.corpus.noPendingDocs")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 16 }}>
            {t("ui.DeskPage.corpus.gateNote")}
          </p>
          {msg && <p className="toast-inline">{msg}</p>}
          <Disclaimer compact />
        </div>
      )}

      {tab === "reports" && (
        <div className="panel desk-panel" data-testid="reports-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.reports.title")} <InfoTip termId="citability" />
          </h2>
          <p className="muted">
            {t("ui.DeskPage.reports.lede.before")} <strong>{t("ui.DeskPage.reports.lede.strong")}</strong> {t("ui.DeskPage.reports.lede.after")}
          </p>
          <div className="queue-ingest-row">
            <select
              value={reportTpl}
              onChange={(e) => setReportTpl(e.target.value)}
              data-testid="report-template"
            >
              {(reportTemplates.length
                ? reportTemplates
                : [{ id: "ic_audit", name: t("ui.DeskPage.reports.icAudit"), role: "", industry: "" }]
              ).map((tpl) => (
                <option key={tpl.id} value={tpl.id}>
                  {tpl.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn"
              disabled={!companyId || reportBusy}
              data-testid="generate-report"
              onClick={async () => {
                if (!companyId) return;
                setReportBusy(true);
                try {
                  const r = await postGenerateReport({
                    company_id: companyId,
                    template_id: reportTpl,
                    format: "markdown",
                  });
                  setReportMd(r.markdown || "");
                  setReportJson(null);
                  setMsg(t("ui.DeskPage.reports.generatedToast", { name: String(r.template_name) }));
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setReportBusy(false);
                }
              }}
            >
              {reportBusy
                ? t("ui.DeskPage.reports.generating")
                : t("ui.DeskPage.reports.markdownBtn", { ticker: selected?.ticker || "—" })}
            </button>
            <button
              type="button"
              className="btn ghost"
              disabled={!companyId || reportBusy}
              data-testid="generate-report-json"
              onClick={async () => {
                if (!companyId) return;
                setReportBusy(true);
                try {
                  const r = await postGenerateReport({
                    company_id: companyId,
                    template_id: "ic_audit",
                    format: "json",
                  });
                  setReportJson(JSON.stringify(r.dossier || r, null, 2));
                  setReportMd(r.markdown || null);
                  setMsg(t("ui.DeskPage.reports.icJsonToast", { n: r.citeable_count ?? "—" }));
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setReportBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.reports.icJson")}
            </button>
            <button
              type="button"
              className="btn ghost"
              disabled={!companyId || reportBusy}
              data-testid="generate-report-pdf"
              onClick={async () => {
                if (!companyId) return;
                setReportBusy(true);
                try {
                  const blob = await downloadIcAuditPdf(companyId);
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `ic-audit-${selected?.ticker || companyId}.pdf`;
                  a.click();
                  URL.revokeObjectURL(url);
                  setMsg(t("ui.DeskPage.reports.icPdfToast"));
                } catch (e) {
                  setMsg((e as Error).message);
                } finally {
                  setReportBusy(false);
                }
              }}
            >
              {t("ui.DeskPage.reports.icPdf")}
            </button>
          </div>
          {reportJson && (
            <pre
              className="api-out"
              data-testid="report-json"
              style={{ whiteSpace: "pre-wrap", maxHeight: 320, overflow: "auto" }}
            >
              {reportJson}
            </pre>
          )}
          {reportMd && (
            <pre
              className="api-out"
              data-testid="report-markdown"
              style={{ whiteSpace: "pre-wrap", maxHeight: 420, overflow: "auto" }}
            >
              {reportMd}
            </pre>
          )}
          <Disclaimer compact />
        </div>
      )}

      {tab === "pit" && (
        <div className="panel desk-panel" data-testid="pit-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.pit.title")} <InfoTip termId="pit" />
          </h2>
          <p className="muted">
            {t("ui.DeskPage.pit.lede.before")} <code className="inline-code">as_of</code> {t("ui.DeskPage.pit.lede.after")}{" "}
            <code className="inline-code">{demoApiKey()}</code>
          </p>
          {history.length >= 2 && (
            <div className="chart-block">
              <h3 className="chart-title">{t("ui.DeskPage.pit.chartTitle")}</h3>
              <LineChart
                points={history.map((h) => ({
                  label: h.as_of.slice(0, 7),
                  value: h.gci_score,
                }))}
                yDomain={[0, 100]}
                ariaLabel={t("ui.DeskPage.pit.chartAria")}
              />
            </div>
          )}
          <div className="table-scroll" style={{ marginTop: 12 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>as_of</th>
                  <th>GCI</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.as_of}>
                    <td>{h.as_of}</td>
                    <td>{formatScore(h.gci_score)}</td>
                    <td>
                      <ChangeChip value={h.change_pct} horizon={h.change_horizon} />
                    </td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr>
                    <td colSpan={3} className="muted">
                      {t("ui.DeskPage.pit.empty")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="desk-api-actions">
            <button
              type="button"
              className="btn"
              onClick={async () => {
                const rows = await fetchHistory(companyId);
                setApiOut(JSON.stringify(rows, null, 2));
                setMsg(t("ui.DeskPage.pit.fetchedToast"));
              }}
            >
              {t("ui.DeskPage.pit.tryApi")}
            </button>
            <button
              type="button"
              className="btn ghost"
              onClick={async () => {
                const [contract, hist] = await Promise.all([
                  fetchPitContract(),
                  fetchPitHistoryV1(companyId),
                ]);
                setApiOut(
                  JSON.stringify({ contract, history_v1: hist }, null, 2),
                );
                setMsg(
                  `Point-in-time contract · ${hist.series_kind === "citeable_pit" ? "citeable" : "not citeable"}`,
                );
              }}
            >
              {t("ui.DeskPage.pit.v1Contract")}
            </button>
            <a className="btn ghost" href={apiDocsUrl()} target="_blank" rel="noreferrer">
              OpenAPI /docs
            </a>
            <a
              className="btn ghost"
              href={fetchEmFactorCsvUrl(companyId)}
              target="_blank"
              rel="noreferrer"
            >
              {t("ui.DeskPage.pit.emFactorCsv")}
            </a>
          </div>
          {apiOut && <pre className="desk-pre">{apiOut}</pre>}
        </div>
      )}

      {tab === "import" && (
        <div className="panel desk-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.import.title")} <InfoTip termId="alphahunter" />
          </h2>
          <p className="muted">
            {ahStatus?.configured
              ? t("ui.DeskPage.import.configured", {
                  host: ahStatus.url_host || t("ui.DeskPage.import.vendor"),
                })
              : t("ui.DeskPage.import.notConfigured")}
          </p>
          {ahStatus && <p className="muted">{ahStatus.note}</p>}
          <button
            type="button"
            className="btn"
            disabled={!ahStatus?.configured}
            style={{ marginBottom: 12 }}
            onClick={async () => {
              try {
                const res = await postAlphaHunterLive({ company_id: companyId, merge: true });
                setMsg(
                  t("ui.DeskPage.import.livePullToast", {
                    facts: res.fact_count ?? 0,
                    merged: res.merged ?? 0,
                  }),
                );
                setApiOut(JSON.stringify(res, null, 2));
                const d = await fetchCompanyGci(companyId);
                setDetail(d);
              } catch (e) {
                setMsg((e as Error).message);
              }
            }}
          >
            {t("ui.DeskPage.import.pullLive")}
          </button>
          <label className="desk-field">
            <span className="field-label">{t("ui.DeskPage.import.factsLabel")}</span>
            <textarea
              rows={12}
              value={factsJson}
              onChange={(e) => setFactsJson(e.target.value)}
              spellCheck={false}
            />
          </label>
          <button
            type="button"
            className="btn"
            style={{ marginTop: 12 }}
            onClick={async () => {
              try {
                const facts = JSON.parse(factsJson) as Record<string, unknown>[];
                const res = await postAlphaHunterImport({
                  facts,
                  merge_into_company: companyId,
                });
                setMsg(t("ui.DeskPage.import.importToast", { n: res.merged ?? 0 }));
                setApiOut(JSON.stringify(res, null, 2));
                const d = await fetchCompanyGci(companyId);
                setDetail(d);
              } catch (e) {
                setMsg((e as Error).message);
              }
            }}
          >
            {t("ui.DeskPage.import.importMerge")}
          </button>
          {apiOut && <pre className="desk-pre">{apiOut}</pre>}

          <h3 style={{ marginTop: 28 }}>{t("ui.DeskPage.import.consensusTitle")}</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            {t("ui.DeskPage.import.consensus.upsert")} <code>POST /api/consensus/import</code>{t("ui.DeskPage.import.consensus.sampleRows")}{" "}
            <code>source: sample_import</code> {t("ui.DeskPage.import.consensus.require")} <code>?demo=true</code>{t("ui.DeskPage.import.consensus.after")}
          </p>
          {consensusStats && (
            <p className="muted" data-testid="consensus-stats">
              {t("ui.DeskPage.import.consensusStats", {
                rows: consensusStats.row_count,
                companies: consensusStats.company_count,
              })}
            </p>
          )}
          <label className="desk-field">
            <span className="field-label">{t("ui.DeskPage.import.consensusLabel")}</span>
            <textarea
              rows={8}
              value={consensusJson}
              onChange={(e) => setConsensusJson(e.target.value)}
              spellCheck={false}
              placeholder='[{"company_id":"infy","period":"FY26","metric":"revenue_growth_pct","street_consensus":6.5,"source":"vendor"}]'
            />
          </label>
          <div className="queue-ingest-row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn"
              data-testid="consensus-import"
              onClick={async () => {
                try {
                  const rows = JSON.parse(consensusJson || "[]") as Record<string, unknown>[];
                  const demo = rows.some((r) => String(r.source || "").includes("sample"));
                  const res = await postConsensusImport(rows, { demo });
                  setMsg(
                    t("ui.DeskPage.import.consensusToast", { n: res.imported }) +
                      (res.demo ? t("ui.DeskPage.import.demoSuffix") : ""),
                  );
                  setConsensusStats(await fetchConsensusStats());
                } catch (e) {
                  setMsg((e as Error).message);
                }
              }}
            >
              {t("ui.DeskPage.import.importConsensus")}
            </button>
            <button
              type="button"
              className="btn ghost"
              data-testid="consensus-load-sample"
              onClick={async () => {
                try {
                  const r = await fetch("/api/consensus/sample", {
                    headers: { "X-API-Key": demoApiKey() },
                  });
                  if (!r.ok) throw new Error(t("ui.DeskPage.import.sampleUnavailable"));
                  const body = await r.json();
                  setConsensusJson(JSON.stringify(body.rows || body, null, 2));
                  setMsg(t("ui.DeskPage.import.sampleLoaded"));
                } catch {
                  setConsensusJson(
                    JSON.stringify(
                      [
                        {
                          company_id: "infy",
                          period: "FY26",
                          metric: "revenue_growth_pct",
                          street_consensus: 6.5,
                          as_of: "sample",
                          source: "sample_import",
                        },
                      ],
                      null,
                      2,
                    ),
                  );
                  setMsg(t("ui.DeskPage.import.inlineSampleLoaded"));
                }
              }}
            >
              {t("ui.DeskPage.import.loadSample")}
            </button>
          </div>
        </div>
      )}

      {tab === "parameters" && (
        <div className="panel desk-panel" data-testid="gci-parameters-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.params.title")} <InfoTip termId="gci_parameter" />
          </h2>
          <p className="muted lede">{t("ui.DeskPage.params.lede")}</p>

          <div className="viz-grid">
            <div className="chart-block">
              <h3 className="chart-title">{t("ui.DeskPage.params.byFamily")}</h3>
              <DonutChart
                centerLabel={`${catalog.length}`}
                slices={Object.entries(
                  catalog.reduce<Record<string, number>>((acc, m) => {
                    acc[m.family] = (acc[m.family] || 0) + 1;
                    return acc;
                  }, {})
                ).map(([label, value]) => ({
                  label,
                  value,
                  color: FAMILY_COLORS[label] || "var(--accent)",
                }))}
                ariaLabel={t("ui.DeskPage.params.donutAria")}
              />
            </div>
            <div className="chart-block">
              <h3 className="chart-title">{t("ui.DeskPage.params.coverageTitle")}</h3>
              <BarChart
                rows={[...catalog]
                  .sort((a, b) => (b.outcome_count || 0) - (a.outcome_count || 0))
                  .slice(0, 8)
                  .map((m) => ({
                    label: m.display_name.replace(/ %$/, ""),
                    value: m.outcome_count || 0,
                    color: FAMILY_COLORS[m.family] || "var(--accent)",
                  }))}
                ariaLabel={t("ui.DeskPage.params.barAria")}
              />
            </div>
          </div>

          <div className="source-viz" aria-label={t("ui.DeskPage.params.sourceAria")}>
            <h3 className="chart-title">{t("ui.DeskPage.params.feedsTitle")}</h3>
            <div className="source-pills">
              {[
                { ok: true, key: "ui.DeskPage.params.source.transcripts" },
                { ok: true, key: "ui.DeskPage.params.source.filings" },
                { ok: true, key: "ui.DeskPage.params.source.irHtml" },
                { ok: true, key: "ui.DeskPage.params.source.ppt" },
                { ok: true, key: "ui.DeskPage.params.source.asr" },
                { ok: true, key: "ui.DeskPage.params.source.actuals" },
                { ok: false, key: "ui.DeskPage.params.source.rawAv" },
                { ok: false, key: "ui.DeskPage.params.source.technicals" },
                { ok: false, key: "ui.DeskPage.params.source.shenanigans" },
                { ok: false, key: "ui.DeskPage.params.source.sentimentOnly" },
              ].map((s) => (
                <span key={s.key} className={`source-pill ${s.ok ? "in" : "out"}`}>
                  {s.ok ? "✓" : "✕"} {t(s.key)}
                </span>
              ))}
            </div>
          </div>

          <div className="table-scroll" style={{ marginTop: 20 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>{t("ui.DeskPage.params.colParameter")}</th>
                  <th>{t("ui.DeskPage.params.colFamily")}</th>
                  <th>{t("ui.DeskPage.params.colUnit")}</th>
                  <th>{t("ui.DeskPage.params.colTier")}</th>
                  <th>{t("ui.DeskPage.params.colUsage")}</th>
                </tr>
              </thead>
              <tbody>
                {catalog.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <strong>{m.display_name}</strong>
                      <div className="muted" style={{ fontSize: 12 }}>
                        <code className="inline-code">{m.id}</code>
                      </div>
                    </td>
                    <td>
                      <span
                        className="family-chip"
                        style={{
                          borderColor: FAMILY_COLORS[m.family] || "var(--line)",
                          color: FAMILY_COLORS[m.family] || "var(--ink)",
                        }}
                      >
                        {m.family}
                      </span>
                    </td>
                    <td>{m.unit}</td>
                    <td>{m.tier}</td>
                    <td style={{ minWidth: 120 }}>
                      <div className="mini-bar-track">
                        <div
                          className="mini-bar-fill"
                          style={{
                            width: `${Math.min(
                              100,
                              ((m.outcome_count || 0) /
                                Math.max(
                                  1,
                                  ...catalog.map((x) => x.outcome_count || 0)
                                )) *
                                100
                            )}%`,
                            background: FAMILY_COLORS[m.family] || "var(--accent)",
                          }}
                        />
                      </div>
                      <span className="muted" style={{ fontSize: 12 }}>
                        {t("ui.DeskPage.params.outcomes", { n: m.outcome_count ?? 0 })}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "wordmap" && (
        <div className="panel desk-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.wordmap.title")} <InfoTip termId="sentiment" />
          </h2>
          <p className="muted">
            {t("ui.DeskPage.wordmap.lede")}
            {wordmap?.source ? (
              <>
                {" "}
                {t("ui.DeskPage.wordmap.source")} <strong>{wordmap.source}</strong>
                {wordmap.citeable
                  ? t("ui.DeskPage.wordmap.citeable")
                  : t("ui.DeskPage.wordmap.nonCiteable")}
              </>
            ) : null}
          </p>
          {wordmap && (
            <div className="chart-block" style={{ marginTop: 16 }}>
              <CompareBars
                rows={Object.keys(wordmap.entity).map((k) => ({
                  label: k,
                  left: wordmap.entity[k],
                  right: wordmap.industry[k],
                }))}
                ariaLabel={t("ui.DeskPage.wordmap.chartAria")}
              />
            </div>
          )}
          <p className="muted" style={{ marginTop: 8 }}>
            {t("ui.DeskPage.wordmap.peers", { n: wordmap?.peer_count ?? "—" })}
          </p>
        </div>
      )}

      {tab === "vernacular" && (
        <div className="panel desk-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.DeskPage.vernacular.title")}</h2>
          <p className="muted">{t("ui.DeskPage.vernacular.lede")}</p>
          <div className="desk-lang-row">
            {(vernacular?.supported_langs ?? ["en", "hi", "ta", "gu", "mr", "ja"]).map(
              (l) => (
                <button
                  key={l}
                  type="button"
                  className={`btn ghost small ${lang === l ? "active-lang" : ""}`}
                  onClick={() => setLang(l)}
                >
                  {l}
                </button>
              )
            )}
          </div>
          {vernacular && (
            <blockquote className="desk-blurb" data-testid="vernacular-blurb">
              {vernacular.text}
            </blockquote>
          )}
          <Disclaimer compact />
          {badge && (
            <div className="desk-badge-box">
              <div className="field-label">{badge.label}</div>
              <div className="value score" style={{ fontFamily: "var(--serif)", fontSize: 28 }}>
                {badge.gci_score ?? t("ui.DeskPage.common.na")}
              </div>
              <p className="muted">{badge.disclaimer}</p>
              <code className="inline-code">{badge.embed}</code>
              <p style={{ marginTop: 8 }}>
                <a href={badge.svg_url} target="_blank" rel="noreferrer">
                  {t("ui.DeskPage.vernacular.previewBadge")}
                </a>
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "labeling" && (
        <>
          {has("labeling") && <LabelWorkbench companyId={companyId} />}
        <div className="panel desk-panel" data-testid="labeling-queue-panel">
          <h2 style={{ marginTop: 0 }}>
            {t("ui.DeskPage.labeling.title")} <InfoTip termId="labeling_queue" />
          </h2>
          <p className="muted">
            {t("ui.DeskPage.labeling.lede.before")}{" "}
            <code>docs/LABELING_PLAYBOOK.md</code> {t("ui.DeskPage.labeling.lede.after")}
          </p>
          <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
            <input
              type="checkbox"
              checked={labelNiftyOnly}
              onChange={(e) => setLabelNiftyOnly(e.target.checked)}
              data-testid="label-nifty-filter"
            />
            <span className="muted">{t("ui.DeskPage.labeling.niftyOnly")}</span>
          </label>
          {niftyMs && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ marginTop: 0 }}>{t("ui.DeskPage.labeling.milestonesTitle")}</h3>
              <p className="muted">{niftyMs.note}</p>
              <p className="muted">
                {t("ui.DeskPage.labeling.progress", {
                  done: niftyMs.progress.done,
                  total: niftyMs.progress.total,
                  sensex: niftyMs.counts.sensex_hand_labeled ?? "—",
                  nifty: niftyMs.counts.nifty_hand_labeled ?? 0,
                  queued: niftyMs.counts.nifty_queued ?? 0,
                })}
              </p>
              <ul className="package-steps">
                {niftyMs.milestones.map((m) => (
                  <li key={m.id}>
                    <strong>{m.id}</strong> · {m.title} · {m.status} — {m.target}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="btn"
                style={{ marginTop: 8 }}
                onClick={async () => {
                  try {
                    const res = await postNiftyEnqueueLabeling();
                    setMsg(t("ui.DeskPage.labeling.enqueuedToast", { n: res.enqueued }));
                    const q = await fetchLabelingQueue();
                    setLabelQueue(q.items || []);
                    const ms = await fetchNiftyMilestones();
                    setNiftyMs({
                      milestones: ms.milestones,
                      counts: ms.counts as Record<string, number>,
                      nifty_extra_ids: ms.nifty_extra_ids,
                      note: ms.note,
                      progress: ms.progress,
                    });
                  } catch (e) {
                    setMsg((e as Error).message);
                  }
                }}
              >
                {t("ui.DeskPage.labeling.enqueueNifty")}
              </button>
            </div>
          )}
          <button
            type="button"
            className="btn"
            onClick={async () => {
              try {
                await postLabelingQueue({
                  company_id: companyId,
                  priority: "high",
                  note: "Desk request",
                });
                const q = await fetchLabelingQueue();
                setLabelQueue(q.items || []);
                setMsg(t("ui.DeskPage.labeling.queuedToast"));
              } catch (e) {
                setMsg((e as Error).message);
              }
            }}
          >
            {t("ui.DeskPage.labeling.queueBtn", { company: companyId })}
          </button>
          <ul className="package-steps" style={{ marginTop: 16 }}>
            {(labelQueue || [])
              .filter((item) => {
                if (!labelNiftyOnly) return true;
                const ids = new Set(niftyMs?.nifty_extra_ids || []);
                if (ids.size && item.company_id && ids.has(String(item.company_id))) return true;
                const note = `${item.note || ""}`.toLowerCase();
                return note.includes("nifty");
              })
              .slice(0, 20)
              .map((item) => {
                const kindLabel =
                  item.kind === "match_conflict"
                    ? t("ui.DeskPage.labeling.conflict")
                    : item.kind === "guidance_drop_suggestion"
                      ? t("ui.DeskPage.labeling.drop")
                      : "";
                return (
              <li key={item.id} data-testid={`queue-item-${item.id}`}>
                <strong>{item.company_name || item.company_id}</strong>
                {item.period ? ` · ${item.period}` : ""}
                {item.metric ? ` · ${metricDisplayName(item.metric)}` : ""}
                {kindLabel ? ` · ${kindLabel}` : ""}
                {" · "}
                {item.priority} · {item.status}
                {item.note ? <p className="muted queue-quote">{item.note}</p> : null}
                {item.status === "queued" || item.status === "in_progress" ? (
                  <span style={{ display: "inline-flex", gap: 8, marginLeft: 8 }}>
                    <button
                      type="button"
                      className="btn ghost small"
                      data-testid={`queue-done-${item.id}`}
                      onClick={async () => {
                        try {
                          await patchLabelingQueue(item.id, "done");
                          setLabelQueue((await fetchLabelingQueue()).items || []);
                        } catch (e) {
                          setMsg((e as Error).message);
                        }
                      }}
                    >
                      {t("ui.DeskPage.labeling.markDone")}
                    </button>
                    <button
                      type="button"
                      className="btn ghost small"
                      data-testid={`queue-dismiss-${item.id}`}
                      onClick={async () => {
                        try {
                          await patchLabelingQueue(item.id, "cancelled");
                          setLabelQueue((await fetchLabelingQueue()).items || []);
                        } catch (e) {
                          setMsg((e as Error).message);
                        }
                      }}
                    >
                      {t("ui.DeskPage.labeling.dismiss")}
                    </button>
                  </span>
                ) : null}
              </li>
                );
              })}
            {!labelQueue?.length && <li className="muted">{t("ui.DeskPage.labeling.empty")}</li>}
          </ul>
          <p className="muted" style={{ fontSize: 12 }}>
            {t("ui.DeskPage.labeling.m3m4Note")}
          </p>
        </div>
        </>
      )}

      {tab === "feedback" && <FeedbackInbox />}

      {tab === "csm" && (
        <div className="panel desk-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.DeskPage.csm.title")}</h2>
          <p className="muted">
            {csmDash?.note || t("ui.DeskPage.csm.lede")}
          </p>
          {ssoStatus && (
            <div className="panel" style={{ marginBottom: 16 }} data-testid="sso-readiness">
              <h3 style={{ marginTop: 0 }}>{t("ui.DeskPage.csm.ssoTitle")}</h3>
              <p className="muted" style={{ fontSize: 13 }}>
                {t("ui.DeskPage.csm.ssoStatus", {
                  enabled: ssoStatus.enabled ? t("ui.DeskPage.common.yes") : t("ui.DeskPage.common.no"),
                  configured: ssoStatus.configured ? t("ui.DeskPage.common.yes") : t("ui.DeskPage.common.no"),
                  ready:
                    ssoStatus.production_ready || ssoStatus.ready
                      ? t("ui.DeskPage.common.yes")
                      : t("ui.DeskPage.csm.notYet"),
                })}
              </p>
              {ssoStatus.note && <p className="muted">{ssoStatus.note}</p>}
              {ssoStatus.checklist && (
                <ul className="package-steps">
                  {Object.entries(ssoStatus.checklist).map(([k, v]) => (
                    <li key={k}>
                      {k}: {v ? t("ui.DeskPage.csm.ok") : t("ui.DeskPage.csm.missing")}
                    </li>
                  ))}
                </ul>
              )}
              <p className="muted" style={{ fontSize: 12 }}>
                {t("ui.DeskPage.csm.ssoSteps.register")} <code>SSO=true</code> + <code>OIDC_*</code> {t("ui.DeskPage.csm.ssoSteps.redirect")}{" "}
                <code>https://citealpha.com/api/auth/sso/callback</code>{t("ui.DeskPage.csm.ssoSteps.see")}{" "}
                <Link to="/trust">{t("ui.DeskPage.csm.ssoSteps.trust")}</Link>.
              </p>
            </div>
          )}
          <div className="metrics">
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.org")}</div>
              <div className="value" style={{ fontSize: 20 }}>
                {String(csmDash?.org?.name ?? org?.name ?? org?.id ?? "demo")}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.plan")}</div>
              <div className="value" style={{ fontSize: 20 }}>
                {String(csmDash?.org?.plan ?? org?.plan ?? "pilot")}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.seats")}</div>
              <div className="value">
                {String(csmDash?.org?.seats_used ?? org?.seats_used ?? 0)} /{" "}
                {String(csmDash?.org?.seats ?? org?.seats ?? "—")}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.namedCsm")}</div>
              <div className="value" style={{ fontSize: 18 }}>
                {String(csmDash?.csm?.named ?? org?.csm ?? t("ui.DeskPage.csm.assignedAtConvert"))}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.slaTarget")}</div>
              <div className="value" style={{ fontSize: 18 }}>
                {csmDash?.sla?.targets?.uptime_pct != null
                  ? `${csmDash.sla.targets.uptime_pct}%`
                  : "—"}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.DeskPage.csm.observedUptime")}</div>
              <div className="value" style={{ fontSize: 18 }}>
                {csmDash?.sla?.observed?.uptime_pct != null
                  ? `${csmDash.sla.observed.uptime_pct}%`
                  : t("ui.DeskPage.csm.naYet")}
              </div>
            </div>
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            {t("ui.DeskPage.csm.vpc", {
              status: csmDash?.vpc?.status ?? "msa_scoped",
              template: csmDash?.vpc?.private_subnet_example ?? "deploy/aws/vpc-private.example.tf",
            })}
          </p>
          <ul className="package-steps" style={{ marginTop: 16 }}>
            <li>{t("ui.DeskPage.csm.cadence.weekly")}</li>
            <li>{t("ui.DeskPage.csm.cadence.monthly")}</li>
            <li>{t("ui.DeskPage.csm.cadence.quarterly")}</li>
            <li>
              {t("ui.DeskPage.csm.openItems", {
                labeling: csmDash?.labeling_open ?? "—",
                tickets: csmDash?.tickets_open ?? 0,
              })}
            </li>
          </ul>
          {csmDash?.labeling_audit && csmDash.labeling_audit.length > 0 ? (
            <div data-testid="csm-labeling-audit" style={{ marginTop: 12 }}>
              <p className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
                {t("ui.DeskPage.csm.auditTitle")}
              </p>
              <ul className="package-steps">
                {csmDash.labeling_audit.slice(0, 8).map((row) => (
                  <li key={row.id || `${row.company_id}-${row.updated_at}`}>
                    {row.company_id} · {row.status}
                    {row.submitter_id
                      ? t("ui.DeskPage.csm.labeledBy", { id: row.submitter_id })
                      : ""}
                    {row.reviewer_id ? t("ui.DeskPage.csm.reviewedBy", { id: row.reviewer_id }) : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <label className="desk-field" style={{ marginTop: 12 }}>
            <span className="field-label">{t("ui.DeskPage.csm.ticketLabel")}</span>
            <input
              value={ticketSubject}
              onChange={(e) => setTicketSubject(e.target.value)}
              placeholder={t("ui.DeskPage.csm.ticketPlaceholder")}
            />
          </label>
          <button
            type="button"
            className="btn"
            style={{ marginTop: 8 }}
            onClick={async () => {
              try {
                await postCsmTicket("demo", { subject: ticketSubject, severity: "3" });
                setTicketSubject("");
                setCsmDash(await fetchCsmDashboard("demo"));
                setMsg(t("ui.DeskPage.csm.ticketToast"));
              } catch (e) {
                setMsg((e as Error).message);
              }
            }}
          >
            {t("ui.DeskPage.csm.fileTicket")}
          </button>
          <p className="cta-line">
            {t("ui.DeskPage.csm.contact")} <strong>{csmDash?.csm?.email ?? "csm@citealpha.com"}</strong> {t("ui.DeskPage.csm.sales")}{" "}
            <strong>sales@citealpha.com</strong>
          </p>
          <Link className="btn" to="/products#plans" style={{ marginTop: 12 }}>
            {t("ui.DeskPage.csm.viewPackage")}
          </Link>
          <div className="panel" style={{ marginTop: 24 }} data-testid="org-settings-cta">
            <h3 style={{ marginTop: 0 }}>{t("ui.DeskPage.csm.teamTitle")}</h3>
            <p className="muted">
              {t("ui.DeskPage.csm.teamLede")}
            </p>
            <Link to="/org/settings" className="btn-primary">
              {t("ui.DeskPage.csm.openOrgSettings")}
            </Link>
          </div>
          <PilotChecklistPanel orgId={String(org?.id || "demo")} />
        </div>
      )}
    </section>
    </PlanAccessGate>
  );
}
