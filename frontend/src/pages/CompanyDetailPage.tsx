import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ChangeChip, { ChangeTriple } from "../components/ChangeChip";
import AuditBadges from "../components/AuditBadges";
import { BarChart, CompareBars, DualLineChart, LineChart } from "../components/Charts";
import Disclaimer from "../components/Disclaimer";
import EvidenceTable from "../components/EvidenceTable";
import InfoTip from "../components/InfoTip";
import QualityBadge from "../components/QualityBadge";
import RecordSentence from "../components/RecordSentence";
import ScoreCalcPanel from "../components/ScoreCalcPanel";
import TierBadge from "../components/TierBadge";
import RevisionTimeline from "../components/RevisionTimeline";
import ScoreReveal from "../components/ScoreReveal";
import Skeleton from "../components/Skeleton";
import ThreadTimeline from "../components/ThreadTimeline";
import Toast from "../components/Toast";
import WatchlistToggle from "../components/WatchlistToggle";
import GuestPaywallModal from "../components/GuestPaywallModal";
import GuidanceProfileNote from "../components/GuidanceProfileNote";
import { useSourceViewer } from "../lib/SourceViewerContext";
import { withTextHighlight } from "../lib/sourceHighlight";
import {
  downloadIcAuditPdf,
  downloadLedgerPdf,
  fetchCompanyAnalytics,
  fetchCompanyChanges,
  fetchCompanyCommitments,
  fetchNinjaProfile,
  fetchCompanyDocs,
  fetchCompanyGci,
  fetchCompanyLedger,
  fetchHistory,
  fetchLedgerMirror,
  fetchNarrativeConsistency,
  fetchNotes,
  fetchRadarDiffBrief,
  fetchReportTemplates,
  fetchStockHistory,
  fetchVernacular,
  fetchVernacularDigest,
  fetchWordmap,
  type CommitmentView,
  postExtract,
  postFeedback,
  postGenerateReport,
  postNote,
  postReview,
  recordCiteCopy,
  ApiError,
  type CompanyGCIDetail,
  type StockHistory,
  type VernacularPayload,
  type WordmapPayload,
} from "../lib/api";
import { formatOutcomeLabel, tipForLabel } from "../lib/glossary";
import { formatDossierDate, formatScore, metricDisplayName, scoreClass, buildRecordParts, englishRecordSentence } from "../lib/score";
import { dossierSeo } from "../lib/seo";
import { setSeoOverride } from "../lib/seoOverride";
import { severityLabel } from "../lib/severity";
import { CONTACT_EMAIL } from "../lib/legal";
import { useI18n } from "../i18n";
import { useEntitlements } from "../lib/entitlements";
import { useAuth } from "../lib/auth";
import { isPlatformSuper } from "../lib/platformRole";
import { trackEvent } from "../lib/analytics";

const TOC_PUBLIC = [
  { id: "record", labelKey: "ui.CompanyDetailPage.toc.record" },
  { id: "evidence", labelKey: "ui.CompanyDetailPage.toc.evidence" },
  { id: "revisions", labelKey: "ui.CompanyDetailPage.toc.revisions" },
  { id: "calc", labelKey: "ui.CompanyDetailPage.toc.calc" },
] as const;

const TOC_PRIMARY = [
  { id: "ledger", labelKey: "ui.CompanyDetailPage.toc.ledger" },
  { id: "docs", labelKey: "ui.CompanyDetailPage.toc.docs" },
  { id: "trend", labelKey: "ui.CompanyDetailPage.toc.trend" },
  { id: "report", labelKey: "ui.CompanyDetailPage.toc.report" },
] as const;

const TOC_MORE = [
  { id: "radar-diff", labelKey: "ui.CompanyDetailPage.toc.radar_diff" },
  { id: "revisions", labelKey: "ui.CompanyDetailPage.toc.revisions" },
  { id: "analytics", labelKey: "ui.CompanyDetailPage.toc.analytics" },
  { id: "threads", labelKey: "ui.CompanyDetailPage.toc.threads" },
  { id: "metrics", labelKey: "ui.CompanyDetailPage.toc.metrics" },
  { id: "notes", labelKey: "ui.CompanyDetailPage.toc.notes" },
  { id: "pit", labelKey: "ui.CompanyDetailPage.toc.pit" },
  { id: "context", labelKey: "ui.CompanyDetailPage.toc.context" },
] as const;

export default function CompanyDetailPage() {
  const { id } = useParams();
  const { t, lang: uiLang } = useI18n();
  const { has, entitlements } = useEntitlements();
  const { token, user } = useAuth();
  const { openSource } = useSourceViewer();
  const [detail, setDetail] = useState<CompanyGCIDetail | null>(null);
  const [commitments, setCommitments] = useState<CommitmentView | null>(null);
  const [history, setHistory] = useState<
    {
      as_of: string;
      gci_score: number | null;
      change_pct?: number | null;
      change_horizon?: string | null;
    }[]
  >([]);
  const [priceHistory, setPriceHistory] = useState<StockHistory | null>(null);
  const [wordmap, setWordmap] = useState<WordmapPayload | null>(null);
  const [vernacular, setVernacular] = useState<VernacularPayload | null>(null);
  const [lang, setLang] = useState<string>(uiLang);

  useEffect(() => {
    setLang(uiLang);
  }, [uiLang]);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [changes, setChanges] = useState<{
    wow_pct?: number | null;
    mom_pct?: number | null;
    qoq_pct?: number | null;
    yoy_pct?: number | null;
    pop_pct?: number | null;
    pop_horizon?: string | null;
    series_kind?: string | null;
    series_n?: number | null;
    citeable?: boolean;
    note?: string | null;
  } | null>(null);
  const [analytics, setAnalytics] = useState<Awaited<
    ReturnType<typeof fetchCompanyAnalytics>
  > | null>(null);
  const [docs, setDocs] = useState<Array<Record<string, unknown>>>([]);
  const [completeness, setCompleteness] = useState<{
    periods: Array<{
      period: string;
      status: string;
      doc_count: number;
      expected_types?: string[];
      types_complete?: boolean;
      type_coverage?: Record<string, boolean>;
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
  } | null>(null);
  const [notes, setNotes] = useState<
    Array<{ id: string; title: string; body: string }>
  >([]);
  const [noteDraft, setNoteDraft] = useState("");
  const [templates, setTemplates] = useState<
    Array<{ id: string; name: string }>
  >([]);
  const [reportMd, setReportMd] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState("ic_audit");
  const [radarDiffs, setRadarDiffs] = useState<
    Awaited<ReturnType<typeof fetchRadarDiffBrief>>["diffs"]
  >([]);
  const [creditOnly, setCreditOnly] = useState(false);
  const [ledgerSummary, setLedgerSummary] = useState<{
    closed_count: number;
    open_promise_count: number;
    by_status: Record<string, number>;
    filter?: string;
  } | null>(null);
  const [ledgerRows, setLedgerRows] = useState<
    { period?: string; metric?: string; status?: string; source_url?: string | null }[]
  >([]);
  const [mirrorNote, setMirrorNote] = useState<string | null>(null);
  const [vernacularDigest, setVernacularDigest] = useState<{
    text: string;
    sources: { url?: string }[];
  } | null>(null);
  const [nci, setNci] = useState<{
    nci_score: number;
    conflicts: { kind: string; detail?: string }[];
    status: string;
  } | null>(null);
  const [paywall, setPaywall] = useState<ApiError | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);

  // W1.2 (rule index-integrity): price tape, correlation / lead–lag, wordmap and
  // narrative-consistency use synthetic inputs. Workbench seats only; never guests.
  const showGciGraphs = isPlatformSuper(user);
  const canAnalytics = has("analytics_experimental") && showGciGraphs;
  const canWordmap = has("wordmap");
  const canNinja = has("ninja");
  const canNotes = canNinja || has("analyst_agent");
  const canVernacular = has("vernacular");
  const showWorkbench = has("desk");
  const [layerNotes, setLayerNotes] = useState<Awaited<ReturnType<typeof fetchNinjaProfile>> | null>(null);
  const isGuest = entitlements.plan === "guest" || entitlements.kind === "guest";
  const [citeCopied, setCiteCopied] = useState(false);

  const reload = useCallback(() => {
    if (!id) return;
    setError(null);
    setPaywall(null);
    const nothing = <T,>(): Promise<T | null> => Promise.resolve(null);
    Promise.all([
      fetchCompanyGci(id),
      fetchHistory(id).catch(() => []),
      canWordmap ? fetchWordmap(id).catch(() => null) : nothing<WordmapPayload>(),
      canVernacular ? fetchVernacular(id, lang).catch(() => null) : nothing<VernacularPayload>(),
      canAnalytics ? fetchStockHistory(id, 5).catch(() => null) : nothing<StockHistory>(),
      fetchCompanyChanges(id).catch(() => null),
      canAnalytics
        ? fetchCompanyAnalytics(id).catch(() => null)
        : nothing<Awaited<ReturnType<typeof fetchCompanyAnalytics>>>(),
      fetchCompanyDocs(id).catch(() => ({
        documents: [] as Array<Record<string, unknown>>,
        completeness: undefined as
          | {
              periods: Array<{
                period: string;
                status: string;
                doc_count: number;
                expected_types?: string[];
                types_complete?: boolean;
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
            }
          | undefined,
      })),
      canNotes ? fetchNotes(id).catch(() => ({ notes: [] })) : Promise.resolve({ notes: [] as { id: string; title: string; body: string }[] }),
      fetchReportTemplates().catch(() => ({ templates: [] })),
      fetchRadarDiffBrief(id).catch(() => ({ diffs: [] })),
      fetchCompanyLedger(id, { creditOnly }).catch(() => null),
      canVernacular
        ? fetchVernacularDigest(id, lang === "hi" ? "hi" : "en").catch(() => null)
        : nothing<Awaited<ReturnType<typeof fetchVernacularDigest>>>(),
      canAnalytics
        ? fetchNarrativeConsistency(id).catch(() => null)
        : nothing<Awaited<ReturnType<typeof fetchNarrativeConsistency>>>(),
    ])
      .then(([d, h, w, v, ph, ch, an, dc, nt, tpl, diff, led, vdig, nciRow]) => {
        setDetail(d);
        trackEvent("open_dossier");
        setHistory(h || []);
        setWordmap(w);
        setVernacular(v);
        setPriceHistory(ph);
        setChanges(ch);
        setAnalytics(an);
        setDocs(dc.documents || []);
        setCompleteness(dc.completeness || null);
        setNotes(nt.notes || []);
        setTemplates(tpl.templates || []);
        setRadarDiffs(diff.diffs || []);
        if (led) {
          setLedgerSummary({
            closed_count: led.summary.closed_count,
            open_promise_count: led.summary.open_promise_count,
            by_status: led.summary.by_status,
            filter: led.filter,
          });
          setLedgerRows(
            (led.closed_promises as { period?: string; metric?: string; status?: string; source_url?: string | null }[]).slice(
              0,
              12,
            ),
          );
        } else {
          setLedgerSummary(null);
          setLedgerRows([]);
        }
        setVernacularDigest(
          vdig ? { text: vdig.text, sources: vdig.sources || [] } : null,
        );
        setNci(nciRow);
        setError(null);
      })
      .catch((e: Error) => {
        if (e instanceof ApiError && e.code === "guest_dossier_cap") {
          setPaywall(e);
          setError(null);
          return;
        }
        setError(e.message);
      });
  }, [id, lang, creditOnly, canAnalytics, canWordmap, canNotes, canVernacular]);

  useEffect(() => {
    if (!id || !canNotes || !token) {
      setLayerNotes(null);
      return;
    }
    let cancelled = false;
    fetchNinjaProfile(id, token)
      .then((view) => {
        if (!cancelled) setLayerNotes(view);
      })
      .catch(() => {
        if (!cancelled) setLayerNotes(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id, canNotes, token]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    fetchCompanyCommitments(id)
      .then((view) => {
        if (!cancelled) setCommitments(view);
      })
      .catch(() => {
        if (!cancelled) setCommitments(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    setDetail(null);
    setCommitments(null);
    reload();
  }, [reload]);

  useEffect(() => {
    if (!detail || !id) {
      setSeoOverride(null);
      return;
    }
    const next = dossierSeo({
      id: detail.id,
      name: detail.name,
      gci: detail.gci_score,
      asOf: detail.as_of,
      dataQuality: detail.data_quality,
      recordSentence: englishRecordSentence(buildRecordParts(detail.outcomes)),
    });
    setSeoOverride(next);
    return () => setSeoOverride(null);
  }, [detail, id]);

  if (paywall) {
    return (
      <section>
        <Link className="back" to="/tracker">
          {t("common.back")}
        </Link>
        <GuestPaywallModal error={paywall} cap={15} />
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <Link className="back" to="/tracker">
          {t("common.back")}
        </Link>
        <p className="error">{error}</p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section>
        <Link className="back" to="/tracker">
          {t("common.back")}
        </Link>
        <p className="page-kicker">{t("company.kicker")}</p>
        <h1 className="muted">{t("ui.CompanyDetailPage.loading")}</h1>
        <Skeleton rows={10} className="panel" />
      </section>
    );
  }

  const hasThreads = detail.threads && Object.keys(detail.threads).length > 0;
  const hasMetricChanges =
    detail.by_metric_changes && Object.keys(detail.by_metric_changes).length > 0;
  // Score deltas are shown only from the reviewed point-in-time series (≥ 4 dates).
  const hasCiteableDeltas = !!changes && changes.series_kind === "citeable_pit";

  return (
    <section className="dossier-page">
      <Toast message={toast} onDismiss={dismissToast} tone="info" />

      <Link className="back" to="/tracker">
        {t("common.back")}
      </Link>

      <div className="dossier-hero">
        <div>
          <p className="page-kicker">{t("company.kicker")}</p>
          <h1 data-testid="company-name">{detail.name}</h1>
          <div className="dossier-meta">
            <span>
              <strong>{detail.ticker}</strong> · {detail.sector}
            </span>
            <QualityBadge quality={detail.data_quality} />
            {detail.confidence_tier && (
              <span data-testid="confidence-tier">
                <TierBadge tier={detail.confidence_tier} />
                {" · "}
                {t("tier.depth", {
                  periods: detail.closed_periods ?? 0,
                  metrics: detail.metrics_scored ?? 0,
                })}
              </span>
            )}
            {detail.as_of && (
              <span data-testid="dossier-as-of">
                {t("dossier.asOf", { date: formatDossierDate(detail.as_of) })}
              </span>
            )}
            {detail.reviewed_at && (
              <span data-testid="dossier-reviewed">
                {t("dossier.reviewed", { date: formatDossierDate(detail.reviewed_at) })}
              </span>
            )}
          </div>
        </div>
        <div className="dossier-score-block">
          {!isGuest ? (
            <div className="dossier-watch-row">
              <WatchlistToggle companyId={detail.id} />
            </div>
          ) : null}
          <span className="field-label">
            GCI <InfoTip termId="gci" />
          </span>
          <ScoreReveal
            score={detail.gci_score}
            coverageStatus={detail.coverage_status}
            coverageReason={detail.coverage_reason}
            testId="gci-score"
          />
          <AuditBadges
            badges={detail.audit_badges}
            deduction={detail.audit_deduction}
            note={detail.audit_note}
          />
          <RecordSentence outcomes={detail.outcomes} coverageReason={detail.coverage_reason} />
          <div style={{ marginTop: 6 }}>
            {hasCiteableDeltas ? (
              <ChangeTriple
                wow={changes!.wow_pct}
                mom={changes!.mom_pct}
                qoq={changes!.qoq_pct}
                yoy={changes!.yoy_pct}
                pop={changes!.pop_pct}
                popHorizon={changes!.pop_horizon}
              />
            ) : (
              <span className="muted" style={{ fontSize: 12 }} data-testid="deltas-pending">
                {t("dossier.deltasPending", { n: changes?.series_n ?? 0 })}
              </span>
            )}
          </div>
        </div>
      </div>

      {(showWorkbench || (commitments?.commitments.length ?? 0) > 0) && commitments ? (
        <section className="panel" id="commitments" data-testid="commitment-record">
          <div className="panel-head">
            <h2>{t("dossier.commitment.title")}</h2>
          </div>
          <p className="muted">{commitments.note}</p>
          {commitments.commitments.length === 0 ? (
            <p>{t("dossier.commitment.empty")}</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t("analyst.commitments.subject")}</th>
                  <th>{t("analyst.commitments.due")}</th>
                  <th>{t("analyst.commitments.status")}</th>
                </tr>
              </thead>
              <tbody>
                {commitments.commitments.slice(0, 8).map((row) => (
                  <tr key={row.id}>
                    <td>{row.subject}</td>
                    <td>{row.due_date || row.due_period || "—"}</td>
                    <td>{row.state_label || row.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : null}

      {(canNinja || (layerNotes?.notes || []).some((note) => note.claims.length > 0)) && layerNotes ? (
        <section className="panel" id="layer-notes" data-testid="dossier-layers">
          <div className="panel-head">
            <h2>{t("dossier.layers.title")}</h2>
          </div>
          <p className="muted">{layerNotes.note}</p>
          {layerNotes.sector ? (
            <p data-testid="dossier-sector">{t("dossier.layers.sector", { sector: layerNotes.sector })}</p>
          ) : null}
          {canNinja
            ? (["accounting", "causality", "conduct", "execution"] as const).map((layer) => {
                const rows = layerNotes.layers[layer] || [];
                return (
                  <div key={layer}>
                    <h3>{t(`ninja.layer.${layer}`)}</h3>
                    {rows.length === 0 ? (
                      <p>{t("dossier.layers.empty")}</p>
                    ) : (
                      <ul>
                        {rows.map((row) => (
                          <li key={`${layer}-${row.as_of}-${row.quote}`}>
                            {row.quote}{" "}
                            <a href={row.source_url} target="_blank" rel="noreferrer">
                              {row.as_of}
                            </a>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })
            : null}
          <div data-testid="dossier-analyst-notes">
            <h3>{t("dossier.layers.notes")}</h3>
            {(layerNotes.notes || []).filter((note) => note.claims.length > 0).length === 0 ? (
              <p>{t("dossier.layers.notesEmpty")}</p>
            ) : (
              (layerNotes.notes || [])
                .filter((note) => note.claims.length > 0)
                .map((note) => (
                  <div key={note.skill_id}>
                    <h4>{note.title}</h4>
                    <ul>
                      {note.claims.map((claim) => (
                        <li key={`${note.skill_id}-${claim.source_url}-${claim.quote}`}>
                          {claim.text || claim.quote}{" "}
                          <a href={claim.source_url} target="_blank" rel="noreferrer">
                            {claim.as_of || claim.quote}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
            )}
          </div>
        </section>
      ) : null}

      <Disclaimer compact />

      {showWorkbench && (detail.red_alerts?.length ?? 0) > 0 && (
        <details className="panel dossier-red-alerts" data-testid="dossier-red-alerts">
          <summary className="panel-head">
            <h2>{t("ui.CompanyDetailPage.redAlerts", { n: detail.red_alerts!.length })}</h2>
          </summary>
          <ul className="alert-list">
            {detail.red_alerts!.map((a) => (
              <li key={`${a.kind}-${a.message}`}>
                <strong>{a.kind.replace(/_/g, " ")}</strong> — {a.message}
                <span className={`pill ${a.severity}`}>{severityLabel(a.severity)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <nav className="dossier-toc" aria-label={t("ui.CompanyDetailPage.tocAria")}>
        {TOC_PUBLIC.map((s) => (
          <a key={s.id} href={`#${s.id}`} className="dossier-toc-link">
            {t(s.labelKey)}
          </a>
        ))}
        {showWorkbench ? (
          <>
            {TOC_PRIMARY.map((s) => (
              <a key={s.id} href={`#${s.id}`} className="dossier-toc-link">
                {t(s.labelKey)}
              </a>
            ))}
            <details className="dossier-toc-more">
              <summary>{t("ui.CompanyDetailPage.tocMore")}</summary>
              {TOC_MORE.filter((s) => {
                if (s.id === "threads") return hasThreads;
                if (s.id === "metrics") return hasMetricChanges;
                if (s.id === "analytics") return canAnalytics;
                if (s.id === "notes") return canNotes;
                if (s.id === "context") return canWordmap || canVernacular;
                if (s.id === "revisions") return false;
                return true;
              }).map((s) => (
                <a key={s.id} href={`#${s.id}`} className="dossier-toc-link">
                  {t(s.labelKey)}
                </a>
              ))}
            </details>
          </>
        ) : null}
      </nav>

      {showWorkbench ? (
        <p className="muted" data-testid="dossier-workbench-link">
          <Link to={`/desk?tab=review&company=${encodeURIComponent(detail.id)}`} className="inline-link">
            {t("dossier.workbench")}
          </Link>
        </p>
      ) : null}

      <div className="panel" id="record" data-testid="delivery-record">
        <div className="panel-head">
          <h2>{t("dossier.delivery.title")}</h2>
        </div>
        <div className="metrics">
          {Object.entries(detail.label_counts).map(([label, n]) => (
            <div className="metric" key={label}>
              <div className="label">
                {formatOutcomeLabel(label)}{" "}
                <InfoTip termId={label.toLowerCase()} text={tipForLabel(label)} />
              </div>
              <div className="value">{n}</div>
            </div>
          ))}
        </div>
        <ul className="about-list" data-testid="delivery-metrics">
          {Object.entries(detail.by_metric).map(([m, s]) => (
            <li key={m}>
              {metricDisplayName(m)} · {detail.periods_by_metric?.[m] ?? 0} closed · {formatScore(s)}
            </li>
          ))}
          {Object.entries(detail.context_metrics ?? {}).map(([m, s]) => (
            <li key={m} className="muted">
              {metricDisplayName(m)} · {detail.periods_by_metric?.[m] ?? 0} closed · {formatScore(s)}{" "}
              ({t("dossier.delivery.context")})
            </li>
          ))}
        </ul>
        <GuidanceProfileNote profile={detail.guidance_profile} />
      </div>

      <div className="panel" id="evidence">
        <div className="panel-head">
          <h2>
            {t("ui.CompanyDetailPage.evidence.title")} <InfoTip termId="evidence" />
          </h2>
          {showWorkbench ? (
            <button
              type="button"
              className="btn ghost small"
              onClick={async () => {
                try {
                  const res = await postExtract(detail.id);
                  setToast(
                    t("ui.CompanyDetailPage.evidence.extracted", { count: res.count })
                  );
                } catch (e) {
                  setToast((e as Error).message);
                }
              }}
            >
              {t("ui.CompanyDetailPage.evidence.runExtract")}
            </button>
          ) : null}
        </div>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.evidence.lede")}
          {showWorkbench ? (
            <>
              {" "}
              <Link to="/desk?tab=review" className="inline-link">
                {t("ui.CompanyDetailPage.evidence.openQueue")}
              </Link>
            </>
          ) : null}
        </p>
        {detail.status === "not_yet_scored" && detail.outcomes.length === 0 ? (
          <div className="empty" data-testid="empty-state">
            {t("ui.CompanyDetailPage.evidence.notScored")}
          </div>
        ) : detail.status === "insufficient_data" || detail.outcomes.length === 0 ? (
          <div className="empty" data-testid="empty-state">
            {t("ui.CompanyDetailPage.evidence.insufficient")}
          </div>
        ) : (
          <EvidenceTable
            outcomes={detail.outcomes}
            companyId={detail.id}
            testId="evidence-table"
            onReview={
              showWorkbench && has("desk_write")
                ? async (outcomeIndex, action) => {
                    await postReview({
                      company_id: detail.id,
                      outcome_index: outcomeIndex,
                      action,
                      comment: action === "reject" ? "reject from UI" : undefined,
                    });
                    setToast(
                      action === "accept"
                        ? t("ui.CompanyDetailPage.toast.accepted", { n: outcomeIndex })
                        : t("ui.CompanyDetailPage.toast.rejected", { n: outcomeIndex }),
                    );
                    reload();
                  }
                : undefined
            }
            onEdit={
              showWorkbench && has("desk_write")
                ? async (outcomeIndex, edits) => {
                    await postReview({
                      company_id: detail.id,
                      outcome_index: outcomeIndex,
                      action: "edit",
                      comment: "edit from UI",
                      edits,
                    });
                    setToast(t("ui.CompanyDetailPage.toast.edited", { n: outcomeIndex }));
                    reload();
                  }
                : undefined
            }
            onFlag={
              showWorkbench && has("feedback")
                ? async (o) => {
                    await postFeedback({
                      company_id: detail.id,
                      period: o.period,
                      metric: o.metric,
                      kind: "wrong_band",
                      comment: "Flagged from dossier evidence table",
                    });
                    trackEvent("feedback_submit");
                    setToast(t("ui.CompanyDetailPage.toast.flagged"));
                  }
                : undefined
            }
          />
        )}
        {hasThreads ? (
          <div id="threads" data-testid="promise-threads">
            <h3 style={{ marginBottom: 4 }}>{t("ui.CompanyDetailPage.threads.title")}</h3>
            <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
              {t("ui.CompanyDetailPage.threads.lede")}
            </p>
            <ThreadTimeline
              threads={detail.threads!}
              companyId={detail.id}
              gciByPeriod={Object.fromEntries(
                (detail.trend || []).map((pt) => [pt.period, pt.gci_score]),
              )}
            />
          </div>
        ) : null}
      </div>

      <div className="panel" id="revisions" data-testid="revision-panel">
        <div className="panel-head">
          <h2>
            {t("ui.CompanyDetailPage.revisions.title")} <InfoTip termId="delta" />
          </h2>
        </div>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.revisions.lede")}
        </p>
        <RevisionTimeline
          events={detail.revision_timeline}
          summaries={detail.revision_summaries}
        />
      </div>

      <div className="panel" id="calc" data-testid="dossier-calc">
        <div className="panel-head">
          <h2>{t("dossier.calc.title")}</h2>
        </div>
        <ScoreCalcPanel detail={detail} testId="example-calc" />
      </div>

      {showWorkbench && (
        <>
      <div className="panel" id="ledger" data-testid="ledger-panel">
        <div className="panel-head">
          <h2>{t("ui.CompanyDetailPage.ledger.title")}</h2>
        </div>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.ledger.lede")}
        </p>
        {ledgerSummary && (
          <p>
            {t("ui.CompanyDetailPage.ledger.summary", {
              closed: ledgerSummary.closed_count,
              open: ledgerSummary.open_promise_count,
            })}
            {ledgerSummary.filter
              ? t("ui.CompanyDetailPage.ledger.filter", { filter: ledgerSummary.filter })
              : ""}
          </p>
        )}
        <div className="queue-ingest-row" style={{ flexWrap: "wrap", gap: 8 }}>
          <label className="muted" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={creditOnly}
              onChange={(e) => setCreditOnly(e.target.checked)}
              data-testid="ledger-credit-only"
            />
            {t("ui.CompanyDetailPage.ledger.creditOnly")}
          </label>
          <button
            type="button"
            className="btn small"
            data-testid="ledger-pdf-btn"
            onClick={async () => {
              try {
                const blob = await downloadLedgerPdf(detail.id, { creditOnly });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `ledger-${detail.ticker}${creditOnly ? "-credit" : ""}.pdf`;
                a.click();
                URL.revokeObjectURL(url);
                setToast(t("ui.CompanyDetailPage.ledger.pdfDownloaded"));
              } catch (e) {
                setToast(e instanceof Error ? e.message : t("ui.CompanyDetailPage.ledger.pdfFailed"));
              }
            }}
          >
            {t("ui.CompanyDetailPage.ledger.downloadPdf")}
          </button>
          <button
            type="button"
            className="btn ghost small"
            data-testid="ledger-mirror-btn"
            onClick={async () => {
              try {
                const m = await fetchLedgerMirror(detail.id);
                setMirrorNote(
                  t("ui.CompanyDetailPage.ledger.mirrorNote", {
                    note: m.mirror_note || "",
                    avg: m.peer_context?.sector_avg_gci ?? "—",
                  }),
                );
                setLedgerSummary({
                  closed_count: m.summary.closed_count,
                  open_promise_count: m.summary.open_promise_count,
                  by_status: m.summary.by_status,
                  filter: "ir_mirror",
                });
                setToast(t("ui.CompanyDetailPage.ledger.mirrorLoaded"));
              } catch (e) {
                setToast(
                  e instanceof Error
                    ? e.message.includes("403") || e.message.includes("IR_MIRROR")
                      ? t("ui.CompanyDetailPage.ledger.mirrorNeedsFlag")
                      : e.message
                    : t("ui.CompanyDetailPage.ledger.mirrorUnavailable"),
                );
              }
            }}
          >
            {t("ui.CompanyDetailPage.ledger.mirror")}
          </button>
        </div>
        {mirrorNote && <p className="muted" style={{ fontSize: 13 }}>{mirrorNote}</p>}
        {ledgerRows.length > 0 && (
          <ul className="radar-list" data-testid="ledger-rows">
            {ledgerRows.map((r, i) => (
              <li key={`${r.period}-${r.metric}-${i}`}>
                <strong>{r.status}</strong> · {r.period} · {r.metric}
                {r.source_url && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="linkish"
                      onClick={() =>
                        openSource({
                          title: `${r.period} ${r.metric}`,
                          source_url: r.source_url,
                          highlight_url: withTextHighlight(r.source_url),
                        })
                      }
                    >
                      {t("ui.CompanyDetailPage.ledger.source")}
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        {nci && (
          <div style={{ marginTop: 16 }} data-testid="nci-block">
            <h3 style={{ marginBottom: 4 }}>{t("ui.CompanyDetailPage.nci.title")}</h3>
            <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
              {t("ui.CompanyDetailPage.nci.summary", { score: nci.nci_score, status: nci.status })}
            </p>
            {nci.conflicts.length > 0 && (
              <ul className="radar-list">
                {nci.conflicts.slice(0, 5).map((c, i) => (
                  <li key={`${c.kind}-${i}`}>
                    {c.kind}: {c.detail || "—"}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <Disclaimer compact />
      </div>

      <div className="panel" id="radar-diff" data-testid="radar-diff-panel">
        <div className="panel-head">
          <h2>{t("ui.CompanyDetailPage.radar.title")}</h2>
        </div>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.radar.lede")}
        </p>
        {radarDiffs.length === 0 ? (
          <p className="muted">{t("ui.CompanyDetailPage.radar.empty")}</p>
        ) : (
          <ul className="radar-list">
            {radarDiffs.slice(0, 8).map((d, i) => (
              <li key={`${d.metric}-${d.current_period}-${i}`}>
                <span className={`sev sev-${d.severity || "medium"}`}>{d.kind}</span>{" "}
                {d.metric} · {d.prior_period} → {d.current_period}
                {d.band_delta != null && ` · Δ ${d.band_delta}`}
                {d.detail && ` — ${d.detail}`}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel" id="docs" data-testid="period-docs">
        <h2>
          {t("ui.CompanyDetailPage.docs.title")} <InfoTip termId="source" />
        </h2>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.docs.lede.before")}{" "}
          <strong>{t("ui.CompanyDetailPage.docs.lede.strong")}</strong>
          {t("ui.CompanyDetailPage.docs.lede.after")}
        </p>
        {completeness && (
          <div className="period-matrix" data-testid="period-completeness">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("ui.CompanyDetailPage.docs.th.period")}</th>
                  <th>{t("ui.CompanyDetailPage.docs.th.status")}</th>
                  <th>{t("ui.CompanyDetailPage.docs.th.types")}</th>
                  <th>{t("ui.CompanyDetailPage.docs.th.docs")}</th>
                </tr>
              </thead>
              <tbody>
                {completeness.periods.map((p) => (
                  <tr key={p.period}>
                    <td>{p.period}</td>
                    <td>
                      <span className={`pill ${p.status}`}>{p.status}</span>
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {p.types_complete
                        ? t("ui.CompanyDetailPage.docs.typesComplete")
                        : p.expected_types?.join(" · ") || "—"}
                    </td>
                    <td>{p.doc_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {completeness.note && (
              <p className="muted" style={{ fontSize: 12 }}>
                {completeness.note}
              </p>
            )}
            {completeness.summary && (
              <p style={{ fontSize: 12 }} data-testid="tier1-gate">
                {t("ui.CompanyDetailPage.docs.tier1Gate")}{" "}
                {completeness.summary.tier1_gate ? (
                  <span className="score good">{t("ui.CompanyDetailPage.docs.gatePass")}</span>
                ) : (
                  <span className="score bad">{t("ui.CompanyDetailPage.docs.gateOpen")}</span>
                )}
                {" · "}
                {t("ui.CompanyDetailPage.docs.accepted", {
                  accepted: completeness.summary.accepted_periods,
                  total: completeness.summary.total_periods,
                })}
                {completeness.summary.types_complete_periods != null && (
                  <>
                    {" "}
                    {t("ui.CompanyDetailPage.docs.types", {
                      done: completeness.summary.types_complete_periods,
                      total: completeness.summary.total_periods,
                    })}
                  </>
                )}
                {completeness.summary.citeable_pct != null && (
                  <>{t("ui.CompanyDetailPage.docs.citeable", { pct: completeness.summary.citeable_pct })}</>
                )}
                {completeness.summary.citeable_bound_outcomes != null && (
                  <>{t("ui.CompanyDetailPage.docs.bound", { n: completeness.summary.citeable_bound_outcomes })}</>
                )}
              </p>
            )}
          </div>
        )}
        {docs.length === 0 ? (
          <p className="muted">
            {t("ui.CompanyDetailPage.docs.empty")}
          </p>
        ) : (
          <ul className="doc-list">
            {docs.slice(0, 12).map((d) => (
              <li key={String(d.doc_id)}>
                <strong>{String(d.title || d.doc_type || t("ui.CompanyDetailPage.docs.documentFallback"))}</strong>{" "}
                <span className="muted">
                  · {String(d.review_status || t("ui.CompanyDetailPage.docs.pendingFallback"))} ·{" "}
                  {String(d.source || d.source_type || "")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel" id="trend">
        <h2>
          {t("ui.CompanyDetailPage.trend.title")} <InfoTip termId="trend" />
        </h2>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.trend.lede")}
        </p>
        {showGciGraphs && hasCiteableDeltas && (
          <div className="chart-block" data-testid="delta-horizon-chart">
            <h3 style={{ marginBottom: 4 }}>{t("ui.CompanyDetailPage.trend.horizons")}</h3>
            <BarChart
              rows={[
                { label: "WoW", value: Number(changes!.wow_pct ?? 0) },
                { label: "MoM", value: Number(changes!.mom_pct ?? 0) },
                { label: "QoQ", value: Number(changes!.qoq_pct ?? 0) },
                { label: "YoY", value: Number(changes!.yoy_pct ?? 0) },
              ].filter((_, i) =>
                [changes!.wow_pct, changes!.mom_pct, changes!.qoq_pct, changes!.yoy_pct][
                  i
                ] != null
              )}
              unit="%"
              ariaLabel={t("ui.CompanyDetailPage.trend.horizonAria")}
            />
          </div>
        )}
        {showGciGraphs && detail.trend.length >= 2 && (
          <div className="chart-block">
            <LineChart
              points={detail.trend.map((pt) => ({
                label: pt.period,
                value: pt.gci_score,
              }))}
              yDomain={[0, 100]}
              ariaLabel={t("ui.CompanyDetailPage.trend.lineAria")}
            />
          </div>
        )}
        {canAnalytics &&
          priceHistory &&
          priceHistory.points.length >= 2 &&
          detail.trend.length >= 2 && (
            <div className="chart-block" data-testid="gci-price-overlay">
              <p className="pill experimental-banner">{t("dossier.experimentalBanner")}</p>
              <h3 style={{ marginBottom: 4 }}>{t("ui.CompanyDetailPage.overlay.title")}</h3>
              <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
                {t("ui.CompanyDetailPage.overlay.lede.before")}
                <strong>{t("ui.CompanyDetailPage.overlay.lede.strong")}</strong>
                {t("ui.CompanyDetailPage.overlay.lede.after")}
                {analytics?.sample_n != null && (
                  <>
                    {" "}
                    N={analytics.sample_n}
                    {analytics.window_label ? ` · ${analytics.window_label}` : ""}.
                  </>
                )}
              </p>
              {analytics?.pit_as_of && analytics.pit_as_of.length > 0 && (
                <p className="muted" style={{ fontSize: 11, marginTop: 0 }}>
                  {t("ui.CompanyDetailPage.overlay.pitAsOf", { dates: analytics.pit_as_of.slice(-6).join(" · ") })}
                  {analytics.pit_as_of.length > 6 ? "…" : ""}
                </p>
              )}
              <DualLineChart
                left={detail.trend.map((pt) => ({
                  label: pt.period,
                  value: pt.gci_score,
                }))}
                right={priceHistory.points
                  .slice(-detail.trend.length)
                  .map((p) => ({
                    label: p.date.slice(0, 7),
                    value: p.close,
                  }))}
                leftName="GCI"
                rightName={priceHistory.ticker}
                ariaLabel={t("ui.CompanyDetailPage.overlay.aria")}
              />
            </div>
          )}
        {canAnalytics && priceHistory && priceHistory.points.length >= 2 && (
          <div className="chart-block" data-testid="stock-history">
            <h3 style={{ marginBottom: 4 }}>
              {t("common.history")} · {priceHistory.ticker}{" "}
              <span className="muted" style={{ fontSize: 12, fontWeight: 500 }}>
                ({priceHistory.kind?.includes("fmp") || priceHistory.kind?.includes("eod")
                  ? priceHistory.kind
                  : t("common.demoTape")}
                )
              </span>
            </h3>
            <LineChart
              points={priceHistory.points.map((p) => ({
                label: p.date.slice(0, 7),
                value: p.close,
              }))}
              height={140}
              ariaLabel={t("ui.CompanyDetailPage.trend.priceAria", {
                ticker: priceHistory.ticker,
                kind: priceHistory.kind || "demo",
              })}
            />
            {priceHistory.note ? (
              <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                {priceHistory.note}
              </p>
            ) : null}
          </div>
        )}
        <div className="trend-row" data-testid="trend-row">
          {detail.trend.map((pt) => (
            <div key={pt.period} className="trend-point">
              <div className="muted">{pt.period}</div>
              <div className={`score ${scoreClass(pt.gci_score)}`}>
                {pt.gci_score ?? "—"}
              </div>
              <ChangeChip value={pt.change_pct} horizon={pt.change_horizon} />
            </div>
          ))}
        </div>
      </div>

      {canAnalytics && (
      <div className="panel" id="analytics" data-testid="analytics-panel">
        <h2>
          {t("ui.CompanyDetailPage.analytics.title")}{" "}
          <span className="pill" title={t("ui.CompanyDetailPage.analytics.experimentalTitle")}>
            {t("ui.CompanyDetailPage.analytics.experimental")}
          </span>
        </h2>
        <p className="pill experimental-banner" data-testid="experimental-banner">
          {t("dossier.experimentalBanner")}
        </p>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.analytics.lede.a")}
          <strong>GCI</strong>
          {t("ui.CompanyDetailPage.analytics.lede.b")}
          <strong>{t("ui.CompanyDetailPage.analytics.lede.strong")}</strong>
          {t("ui.CompanyDetailPage.analytics.lede.c")}
          {analytics?.series_kind ? (
            <>
              {" "}
              {t("ui.CompanyDetailPage.analytics.series")}
              <strong>{String(analytics.series_kind)}</strong>
              {analytics.citeable
                ? t("ui.CompanyDetailPage.analytics.citeable")
                : t("ui.CompanyDetailPage.analytics.nonCiteable")}
            </>
          ) : null}
        </p>
        {analytics?.granger && (analytics.granger as { enabled?: boolean }).enabled !== false && (
          <div data-testid="granger-panel" style={{ marginBottom: 16 }}>
            <h3>{t("ui.CompanyDetailPage.granger.title")}</h3>
            <p className="muted" style={{ fontSize: 12 }}>
              {(analytics.granger as { disclaimer?: string }).disclaimer ||
                t("ui.CompanyDetailPage.granger.disclaimer")}
              {(analytics.granger as { sample_n?: number }).sample_n != null && (
                <> · N={(analytics.granger as { sample_n?: number }).sample_n}</>
              )}
              {(analytics.granger as { var_ready?: boolean }).var_ready ? (
                <>{t("ui.CompanyDetailPage.granger.varReady")}</>
              ) : (
                <>{t("ui.CompanyDetailPage.granger.varHeld")}</>
              )}
            </p>
            {Array.isArray((analytics.granger as { lasso_selected?: unknown[] }).lasso_selected) &&
              ((analytics.granger as { lasso_selected: Array<{ factor: string; coef?: number; corr?: number }> }).lasso_selected.length > 0) && (
                <p style={{ fontSize: 13 }}>
                  {t("ui.CompanyDetailPage.granger.lassoSelected")}{" "}
                  {(
                    analytics.granger as {
                      lasso_selected: Array<{ factor: string; coef?: number }>;
                    }
                  ).lasso_selected
                    .map((r) => `${r.factor}${r.coef != null ? ` (${r.coef})` : ""}`)
                    .join(", ")}
                </p>
              )}
            {Array.isArray((analytics.granger as { granger_tests?: unknown[] }).granger_tests) && (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t("ui.CompanyDetailPage.granger.th.factor")}</th>
                      <th>F</th>
                      <th>p</th>
                      <th>{t("ui.CompanyDetailPage.granger.th.bestLag")}</th>
                      <th>{t("ui.CompanyDetailPage.granger.th.sig")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      analytics.granger as {
                        granger_tests: Array<{
                          factor?: string;
                          ok?: boolean;
                          reason?: string;
                          f_stat?: number;
                          p_value?: number;
                          best?: { lag?: number; corr?: number | null };
                          significant_0_05?: boolean;
                        }>;
                      }
                    ).granger_tests.map((gt) => (
                      <tr key={gt.factor || gt.reason}>
                        <td>{gt.factor || "—"}</td>
                        <td>{gt.ok === false ? gt.reason || "—" : gt.f_stat ?? "—"}</td>
                        <td>{gt.p_value ?? "—"}</td>
                        <td>
                          {gt.best?.lag != null
                            ? t("ui.CompanyDetailPage.granger.lagCorr", { lag: gt.best.lag, corr: gt.best.corr ?? "—" })
                            : "—"}
                        </td>
                        <td>{gt.significant_0_05 ? t("ui.CompanyDetailPage.granger.yes") : t("ui.CompanyDetailPage.granger.no")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {Array.isArray((analytics.granger as { impact_map?: unknown[] }).impact_map) &&
              ((analytics.granger as { impact_map: Array<{ from?: string; to?: string; weight?: number; p_value?: number }> }).impact_map.length > 0) && (
                <>
                  <h3>{t("ui.CompanyDetailPage.granger.impactMap")}</h3>
                  <BarChart
                    rows={(
                      analytics.granger as {
                        impact_map: Array<{ from?: string; weight?: number }>;
                      }
                    ).impact_map.map((e) => ({
                      label: `${e.from || "?"} → GCI`,
                      value: e.weight ?? 0,
                    }))}
                    unit=""
                    ariaLabel={t("ui.CompanyDetailPage.granger.impactMapAria")}
                  />
                </>
              )}
          </div>
        )}
        {analytics && analytics.show_experimental_ui === false && !(analytics.granger as { enabled?: boolean } | undefined)?.enabled ? (
          <p className="muted">{t("ui.CompanyDetailPage.analytics.disabled")}</p>
        ) : analytics && analytics.show_experimental_ui !== false ? (
          <>
            <p>
              {t("ui.CompanyDetailPage.analytics.dependent")}
              <strong>{analytics.dependent || "gci"}</strong>
              {" · "}
              {t("ui.CompanyDetailPage.analytics.priceCorr")}
              <strong>{analytics.gci_price_corr ?? "—"}</strong>
              {analytics.sample_n != null && (
                <>
                  {" "}
                  · N={analytics.sample_n}
                  {analytics.window_label ? ` (${analytics.window_label})` : ""}
                </>
              )}
              {analytics.lead_lag_gci_vs_price?.best && (
                <>
                  {" "}
                  {t("ui.CompanyDetailPage.analytics.bestLag", {
                    lag: analytics.lead_lag_gci_vs_price.best.lag,
                    corr: analytics.lead_lag_gci_vs_price.best.corr ?? "",
                  })}
                </>
              )}
            </p>
            {analytics.methodology && (
              <p className="muted" style={{ fontSize: 12 }}>
                {analytics.methodology}
              </p>
            )}
            {analytics.correlation_matrix?.variables?.length ? (
              <div className="table-scroll" data-testid="corr-matrix">
                <h3>{t("ui.CompanyDetailPage.analytics.corrMatrix")}</h3>
                <table className="table corr-matrix">
                  <thead>
                    <tr>
                      <th />
                      {analytics.correlation_matrix.variables.map((v) => (
                        <th key={v} title={v}>
                          {v.replace("metric:", "").slice(0, 12)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.correlation_matrix.variables.map((row) => (
                      <tr key={row}>
                        <th title={row}>{row.replace("metric:", "").slice(0, 14)}</th>
                        {analytics.correlation_matrix!.variables.map((col) => {
                          const cell =
                            analytics.correlation_matrix!.matrix[row]?.[col];
                          return (
                            <td
                              key={col}
                              className={
                                cell == null
                                  ? "muted"
                                  : cell >= 0.5
                                    ? "corr-pos"
                                    : cell <= -0.5
                                      ? "corr-neg"
                                      : ""
                              }
                            >
                              {cell == null ? "—" : cell.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            <h3>{t("ui.CompanyDetailPage.analytics.impactFactors")}</h3>
            <BarChart
              rows={(analytics.impact_factors || []).slice(0, 8).map((f) => ({
                label: f.factor.replaceAll("_", " "),
                value: f.impact_vs_gci,
              }))}
              unit=""
              ariaLabel={t("ui.CompanyDetailPage.analytics.impactFactorsAria")}
            />
            <p className="muted" style={{ fontSize: 12 }}>
              {analytics.note}
            </p>
          </>
        ) : analytics ? (
          <p className="muted" style={{ fontSize: 12 }}>
            {analytics.methodology || analytics.note}
          </p>
        ) : (
          <p className="muted">{t("ui.CompanyDetailPage.analytics.unavailable")}</p>
        )}
      </div>
      )}

      {canNotes && (
      <div className="panel" id="notes" data-testid="private-notes">
        <h2>{t("ui.CompanyDetailPage.notes.title")}</h2>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.notes.lede")}
        </p>
        <textarea
          value={noteDraft}
          onChange={(e) => setNoteDraft(e.target.value)}
          rows={3}
          placeholder={t("ui.CompanyDetailPage.notes.placeholder")}
          style={{ width: "100%" }}
        />
        <button
          type="button"
          className="btn small"
          style={{ marginTop: 8 }}
          disabled={!noteDraft.trim()}
          onClick={async () => {
            await postNote({ company_id: detail.id, body: noteDraft.trim(), title: "Insight" });
            setNoteDraft("");
            setToast(t("ui.CompanyDetailPage.notes.saved"));
            reload();
          }}
        >
          {t("ui.CompanyDetailPage.notes.save")}
        </button>
        <ul>
          {notes.map((n) => (
            <li key={n.id}>
              <strong>{n.title}</strong> — {n.body}
            </li>
          ))}
        </ul>
      </div>
      )}

      {has("ic_export") && (
      <div className="panel" id="report" data-testid="report-panel">
        <h2>{t("ui.CompanyDetailPage.report.title")}</h2>
        <p className="muted" style={{ fontSize: 13 }}>
          {t("ui.CompanyDetailPage.report.lede")}
        </p>
        <div className="queue-ingest-row">
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
          >
            {templates.map((tpl) => (
              <option key={tpl.id} value={tpl.id}>
                {tpl.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn"
            onClick={async () => {
              const r = await postGenerateReport({
                company_id: detail.id,
                template_id: templateId || "ic_audit",
                format: "markdown",
              });
              setReportMd(r.markdown || "");
              setToast(t("ui.CompanyDetailPage.report.toast", { name: r.template_name }));
            }}
          >
            Markdown
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={async () => {
              const r = await postGenerateReport({
                company_id: detail.id,
                template_id: "ic_audit",
                format: "json",
              });
              setReportMd(JSON.stringify(r.dossier || r, null, 2));
              setToast(t("ui.CompanyDetailPage.report.jsonToast", { n: r.citeable_count ?? "—" }));
            }}
          >
            JSON
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={async () => {
              const blob = await downloadIcAuditPdf(detail.id);
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `ic-audit-${detail.ticker}.pdf`;
              a.click();
              URL.revokeObjectURL(url);
              setToast(t("ui.CompanyDetailPage.report.pdfDownloaded"));
            }}
          >
            PDF
          </button>
        </div>
        {reportMd && (
          <pre
            style={{
              whiteSpace: "pre-wrap",
              fontSize: 12,
              maxHeight: 320,
              overflow: "auto",
              marginTop: 12,
            }}
          >
            {reportMd}
          </pre>
        )}
      </div>
      )}

      {hasMetricChanges && (
        <div className="panel" id="metrics">
          <h2>
            {t("ui.CompanyDetailPage.metrics.title")} <InfoTip termId="change_trend" />
          </h2>
          {showGciGraphs && (
          <div className="chart-block">
            <BarChart
              rows={Object.entries(detail.by_metric_changes!).map(([metric, b]) => ({
                label: metric.replaceAll("_", " "),
                value: Number(b.yoy_pct ?? b.qoq_pct ?? b.pop_pct ?? 0),
                color:
                  Number(b.yoy_pct ?? b.qoq_pct ?? b.pop_pct ?? 0) >= 0
                    ? "var(--good)"
                    : "var(--bad)",
              }))}
              unit="%"
              ariaLabel={t("ui.CompanyDetailPage.metrics.aria")}
            />
            <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
              {t("ui.CompanyDetailPage.metrics.note")}
            </p>
          </div>
          )}
          <div className="metrics">
            {Object.entries(detail.by_metric_changes!).map(([metric, b]) => (
              <div className="metric" key={metric}>
                <div className="label">{metric}</div>
                <div className="value" style={{ fontSize: 22 }}>
                  {b.value ?? "—"}
                </div>
                <ChangeTriple
                  mom={b.mom_pct}
                  qoq={b.qoq_pct}
                  yoy={b.yoy_pct}
                  pop={b.pop_pct}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel" id="pit">
        <h2>
          {t("ui.CompanyDetailPage.pit.title")} <InfoTip termId="pit" />
        </h2>
        {showGciGraphs && history.length >= 2 && (
          <div className="chart-block">
            <LineChart
              points={history.map((h) => ({
                label: h.as_of.slice(0, 7),
                value: h.gci_score,
              }))}
              yDomain={[0, 100]}
              ariaLabel={t("ui.CompanyDetailPage.pit.aria")}
            />
          </div>
        )}
        <div className="table-scroll">
          <table className="table" data-testid="pit-table">
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
                  <td className={`score ${scoreClass(h.gci_score)}`}>
                    {h.gci_score ?? "—"}
                  </td>
                  <td>
                    <ChangeChip value={h.change_pct} horizon={h.change_horizon} />
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={3} className="muted">
                    {t("ui.CompanyDetailPage.pit.empty")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {(canWordmap || canVernacular) && (
      <div className="panel" id="context">
        <h2>
          {t("ui.CompanyDetailPage.context.title")} <InfoTip termId="sentiment" />
        </h2>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("ui.CompanyDetailPage.context.lede")}
        </p>
        {canWordmap && wordmap && (
          <>
            <p className="pill experimental-banner">{t("dossier.experimentalBanner")}</p>
            <CompareBars
              rows={Object.keys(wordmap.entity).map((k) => ({
                label: k,
                left: wordmap.entity[k],
                right: wordmap.industry[k],
              }))}
              ariaLabel={t("ui.CompanyDetailPage.context.wordmapAria")}
            />
          </>
        )}

        {canVernacular && (
        <>
        <h3 style={{ marginTop: 24 }}>{t("ui.CompanyDetailPage.context.blurb")}</h3>
        <div className="desk-lang-row">
          {(vernacular?.supported_langs ?? ["en", "hi", "ta"]).map((l) => (
            <button
              key={l}
              type="button"
              className={`btn ghost small ${lang === l ? "active-lang" : ""}`}
              onClick={() => setLang(l)}
            >
              {l}
            </button>
          ))}
        </div>
        {vernacular && <blockquote className="desk-blurb">{vernacular.text}</blockquote>}

        <h3 style={{ marginTop: 24 }}>{t("ui.CompanyDetailPage.context.digest")}</h3>
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          {t("ui.CompanyDetailPage.context.digestLede")}
        </p>
        {vernacularDigest && (
          <div data-testid="vernacular-digest">
            <blockquote className="desk-blurb">{vernacularDigest.text}</blockquote>
            {vernacularDigest.sources.length > 0 && (
              <ul className="radar-list">
                {vernacularDigest.sources.map((s, i) =>
                  s.url ? (
                    <li key={i}>
                      <button
                        type="button"
                        className="linkish"
                        onClick={() =>
                          openSource({
                            title: t("ui.CompanyDetailPage.context.sourceTitle"),
                            source_url: s.url,
                            highlight_url: withTextHighlight(s.url, vernacularDigest.text),
                            quote: vernacularDigest.text,
                          })
                        }
                      >
                        {s.url}
                      </button>
                    </li>
                  ) : null,
                )}
              </ul>
            )}
          </div>
        )}
        </>
        )}
        <Disclaimer compact />
      </div>
      )}
        </>
      )}

      <p className="muted dossier-footer" data-testid="dossier-footer">
        <Link to="/methodology" className="inline-link">
          {t("dossier.footer.methodology")}
        </Link>
        {" · "}
        <Link
          to={`/changelog?company=${encodeURIComponent(detail.id)}`}
          className="inline-link"
          data-testid="dossier-changelog-link"
        >
          {t("dossier.footer.changelog", { name: detail.name })}
        </Link>
        {" · "}
        <button
          type="button"
          className="linkish"
          data-testid="dossier-cite-page"
          onClick={() => {
            const url = `${window.location.origin}/companies/${detail.id}`;
            const md = `[${detail.name} GCI ${detail.gci_score ?? "—"}](${url})`;
            const bib = `${detail.name}. Guidance Credibility Index (GCI). CiteAlpha. Data as of ${detail.as_of || "n.d."}. ${url}`;
            void navigator.clipboard.writeText(`${md}\n${bib}`).then(() => {
              setCiteCopied(true);
              recordCiteCopy(detail.id);
              window.setTimeout(() => setCiteCopied(false), 1600);
            });
          }}
        >
          {citeCopied ? t("dossier.footer.cited") : t("dossier.footer.cite")}
        </button>
        {" · "}
        <a
          href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`GCI error: ${detail.id}`)}`}
          className="inline-link"
          data-testid="dossier-report-error"
        >
          {t("dossier.footer.report")}
        </a>
        {" · "}
        <span>{t("dossier.footer.disclaimer")}</span>
        {detail.algorithm_id ? (
          <>
            {" · "}
            {t("dossier.footer.method", {
              v: detail.algorithm_id.replace(/^gci_scoring_/, ""),
            })}
          </>
        ) : null}
      </p>
    </section>
  );
}
