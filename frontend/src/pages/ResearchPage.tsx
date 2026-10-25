import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import ChangeChip, { ChangeTriple } from "../components/ChangeChip";
import { LineChart, Sparkline } from "../components/Charts";
import CompanyPicker from "../components/CompanyPicker";
import Disclaimer from "../components/Disclaimer";
import InfoTip from "../components/InfoTip";
import QualityBadge from "../components/QualityBadge";
import ScoreReveal from "../components/ScoreReveal";
import TabBar from "../components/TabBar";
import CitationCard from "../components/CitationCard";
import CitedAnswer from "../components/CitedAnswer";
import WatchlistToggle from "../components/WatchlistToggle";
import PlanAccessGate from "../components/PlanAccessGate";
import {
  fetchCompanies,
  fetchReadingRoom,
  fetchResearchBrief,
  fetchResearchChat,
  fetchResearchEstimates,
  fetchResearchNews,
  fetchResearchSearch,
  fetchResearchSnapshot,
  fetchResearchTranscripts,
  fetchResearchWatchlist,
  type CompanySummary,
  type PromiseBrief,
  type ResearchDoc,
  type CitationRecord,
  type ResearchEstimateRow,
  type ResearchSnapshot,
  type WatchlistItem,
} from "../lib/api";
import { formatCompanyScore, publicDocTitle, scoreClass } from "../lib/score";
import { tipText } from "../lib/glossary";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";
import { useI18n } from "../i18n";
import { useSourceViewer } from "../lib/SourceViewerContext";
import { withTextHighlight } from "../lib/sourceHighlight";

type Tab = "search" | "chat" | "desk" | "news" | "watch";

const TABS: { id: Tab; labelKey: string; titleKey?: string; title?: string }[] = [
  {
    id: "search",
    labelKey: "ui.ResearchPage.tab.search.label",
    titleKey: "ui.ResearchPage.tab.search.title",
  },
  {
    id: "chat",
    labelKey: "ui.ResearchPage.tab.chat.label",
    titleKey: "ui.ResearchPage.tab.chat.title",
  },
  {
    id: "desk",
    labelKey: "ui.ResearchPage.tab.desk.label",
    title: tipText("research_terminal"),
  },
  {
    id: "news",
    labelKey: "ui.ResearchPage.tab.news.label",
    titleKey: "ui.ResearchPage.tab.news.title",
  },
  {
    id: "watch",
    labelKey: "ui.ResearchPage.tab.watch.label",
    titleKey: "ui.ResearchPage.tab.watch.title",
  },
];

const DOC_TYPES = ["all", "guidance", "transcript", "filing", "news", "expert"] as const;
const SAVED_KEY = "citealpha_sights_saved_queries";

function loadSaved(fromPrefs?: string[]): string[] {
  if (fromPrefs?.length) return fromPrefs;
  try {
    const raw = localStorage.getItem(SAVED_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export default function ResearchPage() {
  const { preferences, token, updatePreferences, user } = useAuth();
  const { has, loading: entitlementsLoading, entitlements, refresh } = useEntitlements();
  const { t } = useI18n();
  const readingRoom =
    !entitlementsLoading && !has("research") && user?.platform_admin_role !== "super";
  const searchCap = entitlements.limits?.searches ?? 8;
  const [roomCap, setRoomCap] = useState(searchCap);
  const [roomUsed, setRoomUsed] = useState(0);
  const [scoredCompanies, setScoredCompanies] = useState<CompanySummary[]>([]);
  const { openSource } = useSourceViewer();
  const tabs = TABS.map((x) => ({
    id: x.id,
    label: t(x.labelKey),
    title: x.titleKey ? t(x.titleKey) : x.title,
  }));
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab: Tab = TABS.some((x) => x.id === tabParam)
    ? (tabParam as Tab)
    : "search";
  const setTab = (id: Tab) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", id);
        return next;
      },
      { replace: true }
    );
  };
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [companyId, setCompanyId] = useState(
    searchParams.get("scope") === "all" ? "" : "infy"
  );
  const [q, setQ] = useState(searchParams.get("q") || "guidance margin");
  const [expand, setExpand] = useState(true);
  const [expandedQuery, setExpandedQuery] = useState<string | null>(null);
  const [saved, setSaved] = useState<string[]>(() => loadSaved(preferences?.saved_queries));
  const [docType, setDocType] = useState<(typeof DOC_TYPES)[number]>("all");
  const [results, setResults] = useState<ResearchDoc[]>([]);
  const [question, setQuestion] = useState(
    "How credible is management guidance on revenue growth?"
  );
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<CitationRecord[]>([]);
  const [snapshot, setSnapshot] = useState<ResearchSnapshot | null>(null);
  const [brief, setBrief] = useState<PromiseBrief | null>(null);
  const [estimates, setEstimates] = useState<ResearchEstimateRow[]>([]);
  const [news, setNews] = useState<ResearchDoc[]>([]);
  const [watch, setWatch] = useState<WatchlistItem[]>([]);
  const [transcripts, setTranscripts] = useState<ResearchDoc[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const market = preferences?.default_market ?? "IN";
  const index = preferences?.default_index ?? "SENSEX";

  useEffect(() => {
    if (readingRoom) return;
    fetchCompanies({ market, index, limit: 200 })
      .then((c) => {
        setCompanies(c);
        if (companyId && !c.find((r) => r.id === companyId) && c[0]) setCompanyId(c[0].id);
      })
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market, index, readingRoom]);

  useEffect(() => {
    if (!readingRoom) return;
    let cancelled = false;
    fetchCompanies({ scored: true })
      .then((rows) => {
        if (!cancelled) setScoredCompanies(rows);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    fetchReadingRoom()
      .then((row) => {
        if (cancelled || row.limited === false) return;
        setRoomCap(row.cap || 8);
        setRoomUsed(row.used || 0);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [readingRoom]);

  useEffect(() => {
    if (preferences?.saved_queries?.length) setSaved(preferences.saved_queries);
  }, [preferences?.saved_queries]);

  const deskCompanyId = companyId || companies[0]?.id || "infy";

  useEffect(() => {
    if (tab === "desk") {
      Promise.all([
        fetchResearchSnapshot(deskCompanyId),
        fetchResearchEstimates(deskCompanyId),
        fetchResearchTranscripts(deskCompanyId),
        fetchResearchBrief(deskCompanyId).catch(() => null),
      ])
        .then(([s, e, t, b]) => {
          setSnapshot(s);
          setEstimates(e.estimates);
          setTranscripts(t.transcripts);
          setBrief(b);
        })
        .catch((err: Error) => setError(err.message));
    }
    if (tab === "news") {
      fetchResearchNews(companyId || undefined)
        .then((n) => setNews(n.items))
        .catch((err: Error) => setError(err.message));
    }
    if (tab === "watch") {
      const ids = preferences?.watchlist?.length ? preferences.watchlist : undefined;
      fetchResearchWatchlist({ companyIds: ids, token })
        .then((w) => setWatch(w.items))
        .catch((err: Error) => setError(err.message));
    }
  }, [tab, companyId, deskCompanyId, preferences?.watchlist, token]);

  const filteredResults = useMemo(() => {
    if (docType === "all") return results;
    return results.filter((r) => r.doc_type === docType);
  }, [results, docType]);

  const chooseCompany = (id: string) => {
    setCompanyId(id);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (id) next.delete("scope");
        else next.set("scope", "all");
        return next;
      },
      { replace: true }
    );
  };

  const persistSaved = (next: string[]) => {
    setSaved(next);
    localStorage.setItem(SAVED_KEY, JSON.stringify(next));
    if (token) void updatePreferences({ saved_queries: next });
  };

  const visibleCompanies = readingRoom ? scoredCompanies : companies;
  useEffect(() => {
    if (!readingRoom || visibleCompanies.length === 0) return;
    if (visibleCompanies.some((c) => c.id === companyId)) return;
    setCompanyId(visibleCompanies[0].id);
  }, [readingRoom, companyId, visibleCompanies]);
  const readingRemaining = Math.max(0, roomCap - roomUsed);

  const runSearch = async (query = q) => {
    if (readingRoom && !companyId) {
      setError(t("research.readingRoom.pick"));
      return;
    }
    if (readingRoom && readingRemaining <= 0) {
      setError(t("research.readingRoom.cap", { cap: roomCap }));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetchResearchSearch(query, companyId || undefined, {
        expand,
        readingRoom,
      });
      setResults(res.results);
      setExpandedQuery(
        res.expanded_query && res.expanded_query !== res.original_query ? res.expanded_query : null
      );
      if (readingRoom && res.reading_room) {
        const cap = res.reading_room.cap || roomCap;
        const remaining = res.reading_room.remaining;
        setRoomCap(cap);
        setRoomUsed(remaining == null ? roomUsed + 1 : cap - remaining);
        if (token) void refresh();
      }
    } catch (e) {
      setError((e as Error).message);
      if (readingRoom) void refresh();
    } finally {
      setBusy(false);
    }
  };

  const runChat = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetchResearchChat(question, companyId || undefined, { expand });
      setAnswer(res.answer);
      setCitations(res.citations || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (tabParam === "sectors") return <Navigate to="/tracker?tab=sectors" replace />;

  const lockedTab = readingRoom && tab !== "search";

  return (
    <section className="research-page" data-testid="research-page">
      <p className="page-kicker">{t(readingRoom ? "research.readingRoom.kicker" : "research.kicker")}</p>
      <h1>
        {t("research.title")} <InfoTip termId="research_terminal" />
      </h1>
      <p className="muted lede">
        {t(readingRoom ? "research.readingRoom.lede" : "research.lede")}
        {t("ui.ResearchPage.lede.after")}{" "}
        <InfoTip termId="citability" />
      </p>

      <div className="panel research-toolbar research-sticky">
        <CompanyPicker
          companies={visibleCompanies}
          value={companyId}
          onChange={chooseCompany}
          label={t("research.focus")}
          testId="research-company"
          allLabel={readingRoom ? undefined : t("ui.ResearchPage.scope.all")}
        />
        <TabBar
          tabs={tabs}
          active={tab}
          onChange={(id) => setTab(id as Tab)}
          ariaLabel={t("ui.ResearchPage.modesAria")}
        />
      </div>

      {error && <p className="error">{error}</p>}

      {lockedTab && (
        <PlanAccessGate
          feature="research"
          title={t("research.title")}
          description={`${t("research.lede")}${t("ui.ResearchPage.gate.description")}`}
          returnTo={`/research?tab=${tab}`}
          testId="research-access-gate"
        >
          <span />
        </PlanAccessGate>
      )}

      {!lockedTab && tab === "search" && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.ResearchPage.search.title")}</h2>
          {readingRoom && (
            <p className="muted" data-testid="reading-room-allowance">
              {t("research.readingRoom.allowance", {
                cap: roomCap,
                remaining: readingRemaining,
              })}{" "}
              <Link to="/pilot">{t("research.readingRoom.evaluate")}</Link>
            </p>
          )}
          <p className="muted">{t("ui.ResearchPage.search.subtitle")}</p>
          <div className="chip-row" role="group" aria-label={t("ui.ResearchPage.search.docTypeAria")}>
            {DOC_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                className={`type-chip ${docType === t ? "active" : ""}`}
                onClick={() => setDocType(t)}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="search-row">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("ui.ResearchPage.search.placeholder")}
              data-testid="research-query"
              onKeyDown={(e) => {
                if (e.key === "Enter") void runSearch();
              }}
            />
            <button
              type="button"
              className="btn"
              onClick={() => void runSearch()}
              disabled={busy || (readingRoom && readingRemaining <= 0)}
            >
              {t("ui.ResearchPage.search.button")}
            </button>
            <button
              type="button"
              className="btn ghost"
              data-testid="research-save-query"
              disabled={!q.trim()}
              onClick={() => persistSaved([...saved.filter((x) => x !== q.trim()), q.trim()].slice(-20))}
            >
              {t("ui.ResearchPage.saved.save")}
            </button>
          </div>
          <label className="row gap" style={{ fontSize: 13, marginTop: 8 }}>
            <input
              type="checkbox"
              checked={expand}
              onChange={(e) => setExpand(e.target.checked)}
              data-testid="research-expand"
            />
            {t("ui.ResearchPage.expand.label")}
          </label>
          {expandedQuery && (
            <p className="muted" style={{ fontSize: 13 }} data-testid="research-expanded">
              {t("ui.ResearchPage.expand.searched", { query: expandedQuery })}
            </p>
          )}
          {saved.length > 0 && (
            <div className="chip-row" role="group" aria-label={t("ui.ResearchPage.saved.title")} data-testid="research-saved">
              <span className="field-label">{t("ui.ResearchPage.saved.title")}</span>
              {saved.map((sq) => (
                <span key={sq} className="type-chip">
                  <button
                    type="button"
                    className="linkish"
                    onClick={() => {
                      setQ(sq);
                      void runSearch(sq);
                    }}
                  >
                    {sq}
                  </button>{" "}
                  <button
                    type="button"
                    className="btn-text"
                    aria-label={t("ui.ResearchPage.saved.remove", { query: sq })}
                    onClick={() => persistSaved(saved.filter((x) => x !== sq))}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <ul className="doc-list">
            {filteredResults.map((r) => (
              <li key={r.id}>
                <div className="doc-meta">
                  <span className={`pill ${r.doc_type}`}>{r.doc_type}</span>
                  <strong>{r.ticker}</strong>
                  <span className="muted">{r.date}</span>
                  {r.source && <span className="muted">{r.source}</span>}
                </div>
                <div>{publicDocTitle(r.title, r.doc_type)}</div>
                <p className="muted">{r.snippet}</p>
                <button
                  type="button"
                  className="linkish"
                  onClick={() =>
                    openSource({
                      doc_id: r.id,
                      title: publicDocTitle(r.title, r.doc_type),
                      source_url: r.url,
                      highlight_url: withTextHighlight(r.url, r.snippet),
                      quote: r.snippet,
                      document_text: r.body,
                      company_id: r.company_id,
                    })
                  }
                >
                  {t("ui.ResearchPage.openSource")}
                </button>
              </li>
            ))}
            {results.length > 0 && filteredResults.length === 0 && (
              <li className="muted">{t("ui.ResearchPage.search.noDocsForType", { type: docType })}</li>
            )}
          </ul>
        </div>
      )}

      {!lockedTab && tab === "chat" && (
        <PlanAccessGate
          feature="research_chat"
          variant="panel"
          title={t("ui.ResearchPage.chat.title")}
          description={t("ui.ResearchPage.chat.gateDescription")}
          returnTo="/research?tab=chat"
          testId="research-chat-gate"
        >
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.ResearchPage.chat.title")}</h2>
          <p className="muted">
            {t("ui.ResearchPage.chat.subtitle")}
          </p>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            data-testid="research-question"
          />
          <button
            type="button"
            className="btn"
            onClick={() => void runChat()}
            disabled={busy}
            style={{ marginTop: 8 }}
          >
            {t("ui.ResearchPage.chat.ask")}
          </button>
          {answer && (
            <div className="chat-answer" data-testid="research-answer">
              <CitedAnswer text={answer} citations={citations} />
              {citations.length > 0 ? (
                <>
                  <h3>{t("ui.ResearchPage.chat.citations")}</h3>
                  <div className="citation-stack">
                    {citations.map((c, idx) => (
                      <CitationCard
                        key={c.citation_id || c.doc_id || String(idx)}
                        citation={c}
                      />
                    ))}
                  </div>
                </>
              ) : (
                <p className="muted">{t("ui.ResearchPage.chat.noCitations")}</p>
              )}
            </div>
          )}
        </div>
        </PlanAccessGate>
      )}

      {!lockedTab && tab === "desk" && snapshot && (
        <div className="panel">
          <div className="dossier-hero" style={{ borderBottom: "1px solid var(--line)" }}>
            <div>
              <p className="page-kicker">{t("ui.ResearchPage.tab.desk.label")}</p>
              <h2 style={{ marginTop: 0 }}>
                {snapshot.ticker} · {snapshot.name}
              </h2>
              <div className="dossier-meta">
                <span>{snapshot.sector}</span>
                <QualityBadge quality={snapshot.gci.data_quality} />
                <span className="pill warn">{t("ui.ResearchPage.desk.demoTape")}</span>
              </div>
            </div>
            <div className="dossier-score-block">
              <span className="field-label">GCI</span>
              <ScoreReveal score={snapshot.gci.score} size="md" />
              <div style={{ marginTop: 6 }}>
                <ChangeChip
                  value={snapshot.gci.change_pct}
                  horizon={snapshot.gci.change_horizon}
                />
              </div>
            </div>
          </div>
          <p className="muted" style={{ fontSize: 13 }}>
            {t("ui.ResearchPage.desk.levelsNote")}{" "}
            <InfoTip termId="change_trend" />
          </p>
          {snapshot.gci.trend && snapshot.gci.trend.length >= 2 && (
            <div className="chart-block">
              <h3 className="chart-title">{t("ui.ResearchPage.desk.gciPath")}</h3>
              <LineChart
                points={snapshot.gci.trend.map((pt) => ({
                  label: pt.period,
                  value: pt.gci_score,
                }))}
                yDomain={[0, 100]}
                ariaLabel={t("ui.ResearchPage.desk.trendAria")}
              />
            </div>
          )}
          <div className="metrics">
            <div className="metric">
              <div className="label">{t("ui.ResearchPage.desk.last")}</div>
              <div className="value">{snapshot.market.last}</div>
              <ChangeTriple
                mom={snapshot.market.mom_pct}
                qoq={snapshot.market.qoq_pct}
                yoy={snapshot.market.yoy_pct}
                pop={snapshot.market.change_pct}
              />
            </div>
            <div className="metric">
              <div className="label">{t("ui.ResearchPage.desk.mktCap")}</div>
              <div className="value" style={{ fontSize: 22 }}>
                {snapshot.market.mkt_cap_cr}
              </div>
            </div>
            <div className="metric">
              <div className="label">{t("ui.ResearchPage.desk.volume")}</div>
              <div className="value" style={{ fontSize: 22 }}>
                {snapshot.market.volume.toLocaleString()}
              </div>
            </div>
          </div>
          <p className="muted">{snapshot.market.note}</p>

          {brief && (
            <div className="brief-card" data-testid="promise-brief">
              <div className="brief-head">
                <div>
                  <h2 style={{ margin: 0 }}>{t("ui.ResearchPage.brief.title")}</h2>
                  <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                    {brief.note}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() => window.print()}
                >
                  {t("ui.ResearchPage.brief.print")}
                </button>
              </div>
              {brief.promises.length === 0 ? (
                <p className="muted">
                  {t("ui.ResearchPage.brief.noOpen", { ticker: brief.ticker })}
                </p>
              ) : (
                <ul className="brief-list">
                  {brief.promises.map((p) => (
                    <li key={`${p.period}-${p.metric}`} className="brief-item">
                      <div className="brief-item-head">
                        <strong style={{ textTransform: "capitalize" }}>
                          {p.metric.replaceAll("_", " ")}
                        </strong>
                        <span className="muted">{p.period}</span>
                        <span className="queue-band">
                          {p.guided_band[0] != null && p.guided_band[1] != null
                            ? `${p.guided_band[0]}–${p.guided_band[1]}`
                            : p.guided_value}
                        </span>
                        <span className="muted">{t("ui.ResearchPage.brief.street", { value: p.street_consensus })}</span>
                      </div>
                      <p className="muted brief-quote">
                        “{p.guided_text}” — {p.speaker}
                      </p>
                      <p className="brief-hitrate">
                        {p.history.closed > 0 ? (
                          <>
                            {t("ui.ResearchPage.brief.keptBefore")}{" "}
                            <strong>
                              {t("ui.ResearchPage.brief.keptCount", {
                                kept: p.history.kept,
                                closed: p.history.closed,
                              })}
                            </strong>{" "}
                            {t("ui.ResearchPage.brief.keptAfter", { pct: p.history.hit_rate_pct ?? "" })}
                            {p.history.missed > 0 &&
                              t("ui.ResearchPage.brief.missed", { n: p.history.missed })}
                            {p.history.dropped > 0 &&
                              t("ui.ResearchPage.brief.dropped", { n: p.history.dropped })}
                          </>
                        ) : (
                          t("ui.ResearchPage.brief.noHistory")
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
              <p className="muted" style={{ fontSize: 12 }}>
                {brief.disclaimer}
              </p>
            </div>
          )}

          <h2>{t("ui.ResearchPage.fundamentals.title")}</h2>
          <p className="muted">
            {t("ui.ResearchPage.fundamentals.before")}{" "}
            <strong>{t("ui.ResearchPage.fundamentals.strong")}</strong>
            {t("ui.ResearchPage.fundamentals.after")}
          </p>
          <div className="metrics">
            {Object.entries(snapshot.fundamentals_demo).map(([k, v]) => {
              const bundle =
                typeof v === "number"
                  ? {
                      value: v,
                      mom_pct: null,
                      qoq_pct: null,
                      yoy_pct: null,
                      pop_pct: null,
                    }
                  : v;
              return (
                <div className="metric" key={k}>
                  <div className="label">{k.replaceAll("_", " ")}</div>
                  <div className="value" style={{ fontSize: 22 }}>
                    {bundle.value ?? "—"}
                  </div>
                  {typeof v !== "number" && v.history && v.history.length >= 2 && (
                    <Sparkline values={v.history.map((h) => h.value)} />
                  )}
                  <ChangeTriple
                    mom={bundle.mom_pct}
                    qoq={bundle.qoq_pct}
                    yoy={bundle.yoy_pct}
                    pop={bundle.pop_pct}
                    popHorizon={typeof v === "object" ? v.pop_horizon : null}
                  />
                </div>
              );
            })}
          </div>

          <h2>{t("ui.ResearchPage.estimates.title")}</h2>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("ui.ResearchPage.estimates.th.period")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.metric")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.street")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.dStreet")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.guidance")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.dGuide")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.actual")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.dActual")}</th>
                  <th>{t("ui.ResearchPage.estimates.th.label")}</th>
                </tr>
              </thead>
              <tbody>
                {estimates.map((e) => (
                  <tr key={`${e.period}-${e.metric}`}>
                    <td>{e.period}</td>
                    <td>{e.metric}</td>
                    <td>
                      {e.street_consensus ?? "—"}
                      {e.street_source ? (
                        <span className="muted" style={{ marginLeft: 6, fontSize: 11 }}>
                          ({e.street_source})
                        </span>
                      ) : null}
                    </td>
                    <td>
                      <ChangeChip
                        value={e.street_consensus_change_pct}
                        horizon={e.street_consensus_change_horizon}
                      />
                    </td>
                    <td>{e.management_guidance}</td>
                    <td>
                      <ChangeChip
                        value={e.management_guidance_change_pct}
                        horizon={e.management_guidance_change_horizon}
                      />
                    </td>
                    <td>{e.actual ?? "—"}</td>
                    <td>
                      <ChangeChip
                        value={e.actual_change_pct}
                        horizon={e.actual_change_horizon}
                      />
                    </td>
                    <td>
                      <span className={`pill ${e.gci_label}`}>{e.gci_label}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 style={{ marginTop: 24 }}>{t("ui.ResearchPage.transcripts.title")}</h2>
          <ul className="doc-list">
            {transcripts.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  className="linkish"
                  onClick={() =>
                    openSource({
                      doc_id: t.id,
                      title: t.title,
                      source_url: t.url,
                      highlight_url: withTextHighlight(t.url, t.snippet || t.body?.slice(0, 80)),
                      quote: t.snippet,
                      document_text: t.body,
                      company_id: t.company_id,
                    })
                  }
                >
                  <strong>{t.title}</strong>
                </button>
                <p className="muted">{t.body}</p>
              </li>
            ))}
            {transcripts.length === 0 && (
              <li className="muted">{t("ui.ResearchPage.transcripts.empty")}</li>
            )}
          </ul>
          <p style={{ marginTop: 12 }}>
            <Link
              to={`/companies/${deskCompanyId}`}
              style={{ color: "var(--accent)", fontWeight: 600 }}
            >
              {t("ui.ResearchPage.openEvidence")}
            </Link>
          </p>
          <Disclaimer />
        </div>
      )}

      {!lockedTab && tab === "news" && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.ResearchPage.news.title")}</h2>
          <ul className="doc-list">
            {news.map((n) => (
              <li key={n.id}>
                <div className="doc-meta">
                  <span className={`pill ${n.doc_type}`}>{n.doc_type}</span>
                  <strong>{n.ticker}</strong>
                  <span className="muted">{n.date}</span>
                </div>
                <div>{n.title}</div>
                <p className="muted">{n.snippet}</p>
                <button
                  type="button"
                  className="linkish"
                  onClick={() =>
                    openSource({
                      doc_id: n.id,
                      title: n.title,
                      source_url: n.url,
                      highlight_url: withTextHighlight(n.url, n.snippet),
                      quote: n.snippet,
                      document_text: n.body,
                      company_id: n.company_id,
                    })
                  }
                >
                  {t("ui.ResearchPage.openSource")}
                </button>
              </li>
            ))}
            {news.length === 0 && <li className="muted">{t("ui.ResearchPage.news.empty")}</li>}
          </ul>
        </div>
      )}

      {!lockedTab && tab === "watch" && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.ResearchPage.tab.watch.label")}</h2>
          <p className="muted" style={{ fontSize: 13 }}>
            {t("ui.ResearchPage.watch.intro")}
          </p>
          {(!preferences?.watchlist || preferences.watchlist.length === 0) && (
            <p className="muted" style={{ fontSize: 13 }}>
              {t("ui.ResearchPage.watch.defaultBefore")}{" "}
              <Link to="/tracker">{t("ui.ResearchPage.watch.defaultLink")}</Link>
              {t("ui.ResearchPage.watch.defaultAfter")}
            </p>
          )}
          <div className="table-scroll">
            <table className="table" data-testid="research-watchlist">
              <thead>
                <tr>
                  <th aria-label={t("ui.ResearchPage.tab.watch.label")} />
                  <th>{t("ui.ResearchPage.watch.th.ticker")}</th>
                  <th>{t("ui.ResearchPage.watch.th.name")}</th>
                  <th>{t("ui.ResearchPage.watch.th.last")}</th>
                  <th>{t("ui.ResearchPage.watch.th.mqy")}</th>
                  <th>GCI</th>
                  <th>{t("ui.ResearchPage.watch.th.dGci")}</th>
                </tr>
              </thead>
              <tbody>
                {watch.map((w) => (
                  <tr key={w.company_id} className="row-link">
                    <td>
                      <WatchlistToggle companyId={w.company_id} compact />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="linkish"
                        onClick={() => {
                          chooseCompany(w.company_id);
                          setTab("desk");
                        }}
                      >
                        {w.ticker}
                      </button>
                    </td>
                    <td>{w.name}</td>
                    <td>{w.last}</td>
                    <td>
                      <ChangeTriple
                        mom={w.mom_pct}
                        qoq={w.qoq_pct}
                        yoy={w.yoy_pct}
                        pop={w.change_pct}
                      />
                    </td>
                    <td className={`score ${scoreClass(w.gci_score)}`}>
                      {formatCompanyScore(w.gci_score)}
                    </td>
                    <td>
                      <ChangeChip
                        value={w.gci_change_pct}
                        horizon={w.gci_change_horizon}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {watch.length > 0 && preferences?.watchlist && preferences.watchlist.length > 0 && (
            <p style={{ marginTop: 12 }}>
              <button
                type="button"
                className="btn ghost"
                onClick={() => void updatePreferences({ watchlist: [] })}
              >
                {t("ui.ResearchPage.watch.reset")}
              </button>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
