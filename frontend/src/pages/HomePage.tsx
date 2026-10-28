import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChangeTriple } from "../components/ChangeChip";
import Disclaimer from "../components/Disclaimer";
import InfoTip from "../components/InfoTip";
import PublishedCountLine from "../components/PublishedCountLine";
import QualityBadge from "../components/QualityBadge";
import TierBadge from "../components/TierBadge";
import SectorLeaderboard from "../components/SectorLeaderboard";
import Skeleton from "../components/Skeleton";
import TabBar from "../components/TabBar";
import WatchlistToggle from "../components/WatchlistToggle";
import { useAuth } from "../lib/auth";
import { useI18n } from "../i18n";
import {
  fetchAlerts,
  fetchCompanies,
  fetchCompaniesCount,
  fetchMarketIndexes,
  fetchMarkets,
  rateLimitRetrySeconds,
  searchCompanies,
  withRateLimitRetry,
  type AlertItem,
  type CompanySummary,
  type Market,
  type MarketIndex,
} from "../lib/api";
import { formatScore, scoreClass, formatCompanyScore, formatDossierDate } from "../lib/score";
import { severityLabel } from "../lib/severity";
import { setSeoOverride } from "../lib/seoOverride";

const GCI_DEEP = new Set(["IN"]);
const PAGE_SIZE = 100;
const COVERAGE_SENTENCES = new Set(["open_period", "filing_in_review", "no_quantified_guidance", "listed_only"]);

type SortKey = "name" | "gci" | "delta" | "sector" | "tier";
type HomeTab = "universe" | "sectors";

export default function HomePage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { preferences, updatePreferences } = useAuth();
  const homeTabs = useMemo(
    () =>
      [
        {
          id: "universe" as const,
          label: t("home.tab.universe"),
          title: t("home.tab.universeTitle"),
        },
        {
          id: "sectors" as const,
          label: t("home.tab.sectors"),
          title: t("home.tab.sectorsTitle"),
        },
      ] as const,
    [t],
  );
  const homeTab: HomeTab = searchParams.get("tab") === "sectors" ? "sectors" : "universe";
  const setHomeTab = (id: HomeTab) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (id === "universe") next.delete("tab");
        else next.set("tab", id);
        return next;
      },
      { replace: true },
    );
  };
  const [rows, setRows] = useState<CompanySummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsFailed, setAlertsFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [loading, setLoading] = useState(true);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [indexes, setIndexes] = useState<MarketIndex[]>([]);
  const [market, setMarket] = useState("IN");
  const [index, setIndex] = useState(preferences?.default_index ?? "SENSEX");
  const [query, setQuery] = useState("");
  const entityQuery = query;
  const [entityExchange, setEntityExchange] = useState("");
  const [entityQuality, setEntityQuality] = useState("");
  const [entityCorpus, setEntityCorpus] = useState("");
  const [entityHits, setEntityHits] = useState<
    Array<{
      id: string;
      name: string;
      ticker: string;
      gci_score: number | null;
      data_quality?: string;
      corpus_status?: string;
      citeable_outcomes?: number;
      doc_count?: number;
      exchange?: string;
      sector?: string;
    }>
  >([]);
  const [sortKey, setSortKey] = useState<SortKey>("gci");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  // India indexes open on scored names. scored=0 on the URL shows the rest.
  const [scoredOnly, setScoredOnly] = useState(searchParams.get("scored") !== "0");
  const deep = GCI_DEEP.has(market) && index === "SENSEX";
  const showLeaderboard = GCI_DEEP.has(market);
  const unscoredCount = useMemo(
    () => rows.filter((c) => c.gci_score == null).length,
    [rows],
  );
  const packed = useMemo(
    () =>
      (searchParams.get("packed") || "")
        .split(",")
        .map((id) => id.trim().toLowerCase())
        .filter(Boolean),
    [searchParams],
  );
  const indexName = indexes.find((ix) => ix.id === index)?.name || index;
  const scoredCount = rows.length - unscoredCount;
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = rows;
    if (packed.length > 0) {
      list = list.filter((c) => packed.includes(c.id.toLowerCase()));
    }
    if (scoredOnly) {
      list = list.filter((c) => c.gci_score != null);
    }
    if (q) {
      list = list.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.ticker.toLowerCase().includes(q) ||
          c.sector.toLowerCase().includes(q)
      );
    }
    const dir = sortDir === "asc" ? 1 : -1;
    const TIER_RANK: Record<string, number> = { deep: 3, established: 2, provisional: 1 };
    return [...list].sort((a, b) => {
      // Unscored rows go last whatever the sort direction.
      const aUn = a.gci_score == null;
      const bUn = b.gci_score == null;
      if (aUn !== bUn) return aUn ? 1 : -1;
      const na = (v: number | null | undefined) =>
        v == null || Number.isNaN(v) ? -Infinity * dir : v;
      switch (sortKey) {
        case "name":
          return a.name.localeCompare(b.name) * dir;
        case "sector":
          return a.sector.localeCompare(b.sector) * dir;
        case "delta":
          return (na(a.gci_change_pct) - na(b.gci_change_pct)) * dir;
        case "tier": {
          const ta = TIER_RANK[a.confidence_tier ?? ""] ?? 0;
          const tb = TIER_RANK[b.confidence_tier ?? ""] ?? 0;
          if (ta !== tb) return (ta - tb) * dir;
          return ((a.closed_periods ?? 0) - (b.closed_periods ?? 0)) * dir;
        }
        case "gci":
        default:
          return (na(a.gci_score) - na(b.gci_score)) * dir;
      }
    });
  }, [rows, query, sortKey, sortDir, scoredOnly, packed]);

  useEffect(() => {
    setSeoOverride({
      path: "/tracker",
      title: `GCI Screener: ${indexName} Guidance Credibility Scores — GCI by CiteAlpha`,
    });
    return () => setSeoOverride(null);
  }, [indexName]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" || key === "sector" ? "asc" : "desc");
    }
  }

  function openCompany(c: CompanySummary) {
    navigate(`/companies/${c.id}`);
  }

  useEffect(() => {
    setMarket("IN");
    if (preferences?.default_index) setIndex(preferences.default_index);
  }, [preferences?.default_index]);

  useEffect(() => {
    let cancelled = false;
    withRateLimitRetry(fetchMarkets)
      .then((r) => !cancelled && setMarkets(r.markets))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    withRateLimitRetry(() => fetchMarketIndexes(market))
      .then((r) => {
        if (cancelled) return;
        setIndexes(r.indexes);
        if (!r.indexes.some((i) => i.id === index) && r.indexes[0]) {
          setIndex(r.indexes[0].id);
        }
      })
      .catch(() => undefined);
    setPage(0);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market]);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;
    setError(null);
    setLoading(true);
    const offset = page * PAGE_SIZE;
    Promise.allSettled([
      Promise.all([
        fetchCompanies({ market, index, limit: PAGE_SIZE, offset }),
        fetchCompaniesCount({ market, index }),
      ]),
      fetchAlerts(),
    ]).then(([universe, a]) => {
      if (cancelled) return;
      if (universe.status === "fulfilled") {
        const [c, count] = universe.value;
        setRows(c);
        setTotal(count.count);
      } else {
        setError((universe.reason as Error)?.message || t("ui.HomePage.loadError"));
        const secs = rateLimitRetrySeconds(universe.reason);
        if (secs != null) {
          retryTimer = window.setTimeout(() => setReloadTick((n) => n + 1), secs * 1000);
        }
      }
      if (a.status === "fulfilled") {
        setAlerts(a.value.slice(0, 8));
        setAlertsFailed(false);
      } else {
        setAlertsFailed(true);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [market, index, page, reloadTick]);

  useEffect(() => {
    const q = entityQuery.trim();
    if (q.length < 2) {
      setEntityHits([]);
      return;
    }
    const handle = window.setTimeout(() => {
      searchCompanies(q, 12, {
        exchange: entityExchange || undefined,
        data_quality: entityQuality || undefined,
        corpus_status: entityCorpus || undefined,
      })
        .then((r) => setEntityHits(r.results || []))
        .catch(() => setEntityHits([]));
    }, 220);
    return () => window.clearTimeout(handle);
  }, [entityQuery, entityExchange, entityQuality, entityCorpus]);

  function setScored(next: boolean) {
    setScoredOnly(next);
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev);
        params.set("scored", next ? "1" : "0");
        return params;
      },
      { replace: true },
    );
  }

  function onMarketChange(m: string) {
    if (m !== "IN") return;
    setMarket("IN");
    setPage(0);
    void updatePreferences({ default_market: "IN" });
  }

  function onIndexChange(ix: string) {
    setIndex(ix);
    setPage(0);
    void updatePreferences({ default_index: ix });
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const sortMark = (key: SortKey) =>
    sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : "";

  return (
    <section>
      <p className="page-kicker" data-testid="screener-kicker">
        {!loading && total > 0 && total <= PAGE_SIZE
          ? t("screener.kicker", { index: indexName, scored: scoredCount, total })
          : `${indexName}${total > 0 ? ` · ${t("home.names", { n: total })}` : ""}`}
      </p>
      <h1>
        {t("home.title")} <InfoTip termId="tracker" />
      </h1>
      {searchParams.get("ir") === "unnamed" && (
        <p className="muted" data-testid="ir-unnamed">
          Your desk admin has not named a company for packs yet.
        </p>
      )}
      {packed.length > 0 && (
        <p className="muted" data-testid="ir-packed">
          The companies this seat may pack. <Link to="/tracker">Show the full index</Link>
        </p>
      )}
      <PublishedCountLine />
      <p className="muted lede">
        {t("home.lede")} <InfoTip termId="gci" /> {t("ui.HomePage.prefer")}{" "}
        <strong>{t("ui.HomePage.citeable")}</strong> {t("ui.HomePage.preferTail")}{" "}
        <InfoTip termId="corpus_status" />
      </p>

      <div className="universe-filters" data-testid="universe-filters">
        <label>
          {t("common.market")} <InfoTip termId="market" />
          <select
            value={market}
            onChange={(e) => onMarketChange(e.target.value)}
            data-testid="market-select"
          >
            {(markets.filter((m) => m.id === "IN").length
              ? markets.filter((m) => m.id === "IN")
              : [{ id: "IN", name: "India" }]
            ).map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <div className="index-chips" role="group" aria-label={t("common.index")}>
          {(indexes.length ? indexes : [{ id: index, name: index }]).map((ix) => (
            <button
              key={ix.id}
              type="button"
              className={ix.id === index ? "chip active" : "chip"}
              onClick={() => onIndexChange(ix.id)}
              data-testid={`index-chip-${ix.id}`}
            >
              {ix.name}
            </button>
          ))}
        </div>
        <label className="universe-search entity-search" data-testid="entity-search">
          {t("ui.HomePage.search")} <InfoTip termId="corpus_status" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("home.searchPlaceholder")}
            data-testid="universe-search"
            autoComplete="off"
          />
          <div className="entity-facets" data-testid="entity-facets">
            <select
              value={entityExchange}
              onChange={(e) => setEntityExchange(e.target.value)}
              aria-label={t("ui.HomePage.exchangeFacet")}
            >
              <option value="">{t("ui.HomePage.allExchanges")}</option>
              <option value="NSE">NSE</option>
              <option value="BSE">BSE</option>
            </select>
            <select
              value={entityQuality}
              onChange={(e) => setEntityQuality(e.target.value)}
              aria-label={t("ui.HomePage.qualityFacet")}
            >
              <option value="">{t("ui.HomePage.allQuality")}</option>
              <option value="hand_labeled">{t("ui.HomePage.handLabeled")}</option>
              <option value="demo_structured">{t("ui.HomePage.demo")}</option>
              <option value="listing_provisional">{t("ui.HomePage.notScored")}</option>
            </select>
            <select
              value={entityCorpus}
              onChange={(e) => setEntityCorpus(e.target.value)}
              aria-label={t("ui.HomePage.corpusFacet")}
            >
              <option value="">{t("ui.HomePage.allCorpus")}</option>
              <option value="gci_citeable">{t("ui.HomePage.citeableOpt")}</option>
              <option value="gci_available">{t("ui.HomePage.inCorpus")}</option>
              <option value="listed_not_in_corpus">{t("ui.HomePage.listedOnly")}</option>
            </select>
          </div>
          {entityHits.length > 0 && (
            <ul className="entity-search-results" data-testid="entity-search-results">
              {entityHits.map((h) => (
                <li key={h.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/companies/${h.id}`)}
                  >
                    <strong>{h.ticker}</strong> {h.name}{" "}
                    <span className={`score ${scoreClass(h.gci_score)}`}>
                      {formatScore(h.gci_score)}
                    </span>
                    <span className="muted" style={{ fontSize: 11, marginLeft: 6 }}>
                      {h.exchange ? `${h.exchange} · ` : ""}
                      {h.corpus_status === "gci_citeable"
                        ? t("ui.HomePage.citeable")
                        : h.corpus_status === "listed_not_in_corpus"
                          ? t("ui.HomePage.listedNotInCorpus")
                          : h.data_quality || ""}
                      {h.doc_count != null ? ` · ${t("ui.HomePage.docs", { n: h.doc_count })}` : ""}
                      {h.citeable_outcomes != null && h.citeable_outcomes > 0
                        ? ` · ${t("ui.HomePage.citeableCount", { n: h.citeable_outcomes })}`
                        : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </label>
      </div>

      {!deep && (
        <p className="scaffold-banner" data-testid="scaffold-banner">
          {index === "NSE_ALL" || index === "BSE_ALL" || index === "IN1000" ? (
            <>
              {t("ui.HomePage.fullMasters")} <InfoTip termId="nse_bse" />
            </>
          ) : (
            t("home.scaffold")
          )}
        </p>
      )}

      <TabBar
        tabs={homeTabs}
        active={homeTab}
        onChange={(id) => setHomeTab(id as HomeTab)}
        ariaLabel={t("home.gciViews")}
      />

      {homeTab === "sectors" ? (
        <div className="workbench" data-testid="gci-sectors-tab">
          <div className="workbench-main">
            {showLeaderboard ? (
              <SectorLeaderboard market={market} index={index} limit={40} />
            ) : (
              <div className="panel">
                <p className="muted">{t("home.sectorsIndiaOnly")}</p>
              </div>
            )}
            <Disclaimer />
          </div>
        </div>
      ) : (
      <div className="workbench">
        <div className="workbench-main">
          <div className="panel">
            <div className="panel-head">
              <h2>{t("home.universe")}</h2>
              <span className="muted" style={{ fontSize: 13 }}>
                {loading
                  ? t("common.loading")
                  : total > 0
                    ? `${t("home.names", { n: total })} · ${page + 1}/${pageCount}`
                    : "—"}
              </span>
            </div>
            {error && <p className="error">{error}</p>}
            {loading && !error && <Skeleton rows={8} label={t("common.loading")} />}
            {!loading && !error && rows.length > 0 && (
              <div className="screener-scope" data-testid="screener-scope">
                <div className="index-chips" role="group" aria-label="Scored names">
                  <button
                    type="button"
                    className={scoredOnly ? "chip active" : "chip"}
                    aria-pressed={scoredOnly}
                    data-testid="scored-only-toggle"
                    onClick={() => setScored(true)}
                  >
                    {t("screener.filter.scored")} ({scoredCount})
                  </button>
                  <button
                    type="button"
                    className={!scoredOnly ? "chip active" : "chip"}
                    aria-pressed={!scoredOnly}
                    data-testid="scored-all-toggle"
                    onClick={() => setScored(false)}
                  >
                    {t("screener.filter.all")} ({rows.length})
                  </button>
                </div>
              </div>
            )}
            {!loading && !error && filtered.length === 0 && (
              <div className="empty">
                {query
                  ? t("home.noSearchResults", { query })
                  : scoredOnly && rows.length > 0
                    ? t("screener.filter.noneScored")
                    : t("home.noCompanies")}
              </div>
            )}
            {!loading && filtered.length > 0 && (
              <div className="table-scroll table-scroll-tall">
                <table className="table" data-testid="company-table">
                  <thead>
                    <tr>
                      <th aria-label={t("ui.HomePage.watchlist")} />
                      <th>
                        <button type="button" className="th-sort" onClick={() => toggleSort("name")}>
                          {t("common.company")}
                          {sortMark("name")}
                        </button>
                      </th>
                      <th>{t("common.ticker")}</th>
                      <th>
                        <button
                          type="button"
                          className="th-sort"
                          onClick={() => toggleSort("sector")}
                        >
                          {t("common.sector")}
                          {sortMark("sector")}
                        </button>
                      </th>
                      <th>
                        <button type="button" className="th-sort" onClick={() => toggleSort("gci")}>
                          GCI
                          {sortMark("gci")}
                        </button>{" "}
                        <InfoTip termId="gci" />
                      </th>
                      <th>
                        <button
                          type="button"
                          className="th-sort"
                          onClick={() => toggleSort("delta")}
                        >
                          Δ GCI
                          {sortMark("delta")}
                        </button>{" "}
                        <InfoTip termId="change_trend" />
                      </th>
                      <th>
                        {t("common.quality")} <InfoTip termId="data_quality" />
                      </th>
                      <th>
                        <button type="button" className="th-sort" onClick={() => toggleSort("tier")}>
                          {t("common.confidence")}
                          {sortMark("tier")}
                        </button>
                      </th>
                      <th>{t("screener.th.closed")}</th>
                      <th>{t("screener.th.lastFiling")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((c) => {
                      return (
                        <tr
                          key={c.id}
                          className="row-link"
                          tabIndex={0}
                          onClick={() => openCompany(c)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              openCompany(c);
                            }
                          }}
                          aria-label={t("ui.HomePage.openDossier", { name: c.name })}
                        >
                          <td onClick={(e) => e.stopPropagation()}>
                            <WatchlistToggle companyId={c.id} compact />
                          </td>
                          <td>
                            <Link
                              to={`/companies/${c.id}`}
                              data-testid={`company-link-${c.id}`}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {c.name}
                            </Link>
                          </td>
                          <td className="mono">{c.ticker}</td>
                          <td>{c.sector}</td>
                          <td
                            className={`score ${scoreClass(c.gci_score)}${
                              c.gci_score == null ? " score-reason" : ""
                            }`}
                            title={
                              c.gci_score == null
                                ? t(
                                    c.coverage_status
                                      ? `coverage.tip.${c.coverage_status}`
                                      : "screener.notScored.tip",
                                  )
                                : undefined
                            }
                            data-testid={c.gci_score == null ? `not-scored-${c.id}` : undefined}
                          >
                            {c.gci_score == null
                              ? t(
                                  COVERAGE_SENTENCES.has(c.coverage_status || "")
                                    ? `screener.coverage.${c.coverage_status}`
                                    : "screener.coverage.default",
                                )
                              : formatCompanyScore(c.gci_score, 1)}
                          </td>
                          <td>
                            <ChangeTriple
                              wow={c.wow_pct}
                              mom={c.mom_pct}
                              qoq={c.qoq_pct}
                              yoy={c.yoy_pct}
                              pop={c.gci_change_pct}
                              popHorizon={c.gci_change_horizon}
                            />
                          </td>
                          <td>
                            {c.gci_score == null ? (
                              <span className="muted">—</span>
                            ) : (
                              <QualityBadge
                                quality={c.data_quality}
                                testId={`quality-${c.id}`}
                              />
                            )}
                          </td>
                          <td>
                            {c.gci_score == null ? (
                              <TierBadge unscored testId={`tier-${c.id}`} />
                            ) : c.confidence_tier ? (
                              <span title={t("tier.depth", { periods: c.closed_periods ?? 0, metrics: c.metrics_scored ?? 0 })}>
                                <TierBadge tier={c.confidence_tier} testId={`tier-${c.id}`} />
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>{c.closed_periods ?? "—"}</td>
                          <td>{c.as_of ? formatDossierDate(c.as_of) : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {total > PAGE_SIZE && (
              <div className="pager" data-testid="universe-pager">
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={page <= 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  {t("ui.HomePage.prev")}
                </button>
                <span className="muted" style={{ fontSize: 13 }}>
                  {t("ui.HomePage.range", {
                    from: page * PAGE_SIZE + 1,
                    to: Math.min((page + 1) * PAGE_SIZE, total),
                    total,
                  })}
                </span>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={page >= pageCount - 1}
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                >
                  {t("ui.HomePage.next")}
                </button>
              </div>
            )}
            <Disclaimer />
          </div>
        </div>

        <aside className="workbench-rail">
          <div className="panel" data-testid="alerts-panel">
            <div className="panel-head">
              <h2>
                {t("common.alerts")} <InfoTip termId="alerts" />
              </h2>
            </div>
            {loading && alerts.length === 0 ? (
              <Skeleton rows={4} />
            ) : alerts.length === 0 ? (
              <p className="muted">
                {alertsFailed ? t("common.alertsUnavailable") : t("common.noAlerts")}
              </p>
            ) : (
              <ul className="alert-list">
                {alerts.map((a) => (
                  <li
                    key={`${a.company_id}-${a.kind}-${a.message}`}
                    className={`alert-item severity-${a.severity}`}
                  >
                    <Link
                      to={
                        a.kind === "docs_pending_review"
                          ? `/desk?tab=review`
                          : `/companies/${a.company_id}`
                      }
                    >
                      <span className="alert-kind">{a.kind.replace(/_/g, " ")}</span>
                      <strong>{a.ticker}</strong> — {a.message}
                    </Link>
                    <span className={`pill ${a.severity}`}>{severityLabel(a.severity)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>
      )}
    </section>
  );
}
