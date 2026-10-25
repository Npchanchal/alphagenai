/**
 * CiteAlpha Desk Console — multi-pane ops surface inspired by institutional
 * terminal density. Content is GCI / guidance / evidence only (not a quote OMS).
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import BrandLogo from "./BrandLogo";
import ChangeChip from "./ChangeChip";
import { LineChart } from "./Charts";
import QualityBadge from "./QualityBadge";
import ScoreReveal from "./ScoreReveal";
import {
  fetchAlerts,
  fetchCompanies,
  fetchCompanyGci,
  fetchExtractPending,
  fetchHistory,
  fetchLabelingQueue,
  type AlertItem,
  type CompanyGCIDetail,
  type CompanySummary,
  type LabelingQueueItem,
  type PendingExtractBatch,
} from "../lib/api";
import { compareEvidenceLatestFirst, formatScore, formatCompanyScore, metricDisplayName } from "../lib/score";
import { useAuth } from "../lib/auth";
import { isPlatformSuper } from "../lib/platformRole";
import { useI18n } from "../i18n";

type Props = {
  companyId: string;
  onSelectCompany: (id: string) => void;
  onJumpTab?: (tab: string) => void;
};

function gciTone(score: number | null | undefined): "up" | "down" | "flat" {
  if (score == null) return "flat";
  if (score >= 75) return "up";
  if (score < 55) return "down";
  return "flat";
}

function severityClass(sev: string): string {
  const s = (sev || "").toLowerCase();
  if (s.includes("high") || s.includes("crit")) return "ilc-tag ilc-tag-high";
  if (s.includes("med") || s.includes("warn")) return "ilc-tag ilc-tag-med";
  return "ilc-tag ilc-tag-low";
}

export default function DeskConsole({ companyId, onSelectCompany, onJumpTab }: Props) {
  const { t } = useI18n();
  const { user } = useAuth();
  const showGciGraphs = isPlatformSuper(user);
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<CompanySummary[]>([]);
  const [detail, setDetail] = useState<CompanyGCIDetail | null>(null);
  const [history, setHistory] = useState<{ as_of: string; gci_score: number | null }[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [pending, setPending] = useState<PendingExtractBatch[]>([]);
  const [labelQ, setLabelQ] = useState<LabelingQueueItem[]>([]);
  const [clock, setClock] = useState(() => new Date());
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const [cos, al, ext, lq] = await Promise.all([
          fetchCompanies({ market: "IN", index: "SENSEX", limit: 40 }),
          fetchAlerts().catch(() => [] as AlertItem[]),
          fetchExtractPending().catch(() => ({ count: 0, batches: [] as PendingExtractBatch[] })),
          fetchLabelingQueue().catch(() => ({ count: 0, items: [] as LabelingQueueItem[] })),
        ]);
        if (cancelled) return;
        setRows(cos);
        setAlerts(al.slice(0, 24));
        setPending((ext.batches || []).slice(0, 12));
        setLabelQ((lq.items || []).slice(0, 12));
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : t("ui.DeskConsole.loadFailed"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [d, h] = await Promise.all([
          fetchCompanyGci(companyId),
          fetchHistory(companyId).catch(() => []),
        ]);
        if (cancelled) return;
        setDetail(d);
        setHistory(h);
      } catch {
        if (!cancelled) setDetail(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.ticker.toLowerCase().includes(needle) ||
        r.name.toLowerCase().includes(needle) ||
        r.id.toLowerCase().includes(needle) ||
        (r.sector || "").toLowerCase().includes(needle)
    );
  }, [rows, q]);

  const selected = rows.find((r) => r.id === companyId) || null;
  const peers = useMemo(() => {
    if (!selected) return rows.slice(0, 6);
    return rows
      .filter((r) => r.sector === selected.sector && r.id !== selected.id)
      .slice(0, 6);
  }, [rows, selected]);

  const chartPts = useMemo(
    () =>
      history
        .filter((p) => p.gci_score != null)
        .map((p) => ({ label: p.as_of, value: p.gci_score })),
    [history]
  );

  const outcomes = [...(detail?.outcomes || [])].sort(compareEvidenceLatestFirst).slice(0, 14);
  const byMetric = detail?.by_metric || {};
  const metricBars = Object.entries(byMetric)
    .slice(0, 8)
    .map(([metric, score]) => ({ metric, score: score as number }));

  const hlCount = rows.filter((r) => r.data_quality === "hand_labeled").length;
  const scored = rows.filter((r) => r.gci_score != null).length;

  function runCommand(raw: string) {
    const s = raw.trim();
    if (!s) return;
    if (s.startsWith("/")) {
      const cmd = s.slice(1).toLowerCase();
      if (cmd.startsWith("tab ")) onJumpTab?.(cmd.slice(4).trim());
      else if (["review", "evidence", "tracker", "corpus", "pit"].includes(cmd))
        onJumpTab?.(cmd);
      return;
    }
    const hit = rows.find(
      (r) =>
        r.ticker.toLowerCase() === s.toLowerCase() ||
        r.id.toLowerCase() === s.toLowerCase()
    );
    if (hit) onSelectCompany(hit.id);
    else setQ(s);
  }

  return (
    <div className="il-console" data-testid="desk-console">
      <header className="ilc-top">
        <div className="ilc-brand" aria-label={t("ui.DeskConsole.brandAria")}>
          <BrandLogo variant="header" link={false} className="ilc-logo-wordmark" />
          <span className="ilc-product">{t("ui.DeskConsole.product")}</span>
        </div>
        <form
          className="ilc-cmd"
          onSubmit={(e) => {
            e.preventDefault();
            runCommand(q);
          }}
        >
          <span className="ilc-cmd-prompt" aria-hidden>
            ⌘
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("ui.DeskConsole.cmdPlaceholder")}
            aria-label={t("ui.DeskConsole.cmdAria")}
            data-testid="desk-console-cmd"
          />
        </form>
        <div className="ilc-top-meta">
          <span className="ilc-pill">{t("ui.DeskConsole.sensexPill", { scored, total: rows.length })}</span>
          <span className="ilc-pill ilc-pill-ok">{t("ui.DeskConsole.hlPill", { n: hlCount })}</span>
          <time dateTime={clock.toISOString()}>
            {clock.toLocaleTimeString("en-IN", { hour12: false })}
          </time>
        </div>
      </header>

      <nav className="ilc-nav" aria-label={t("ui.DeskConsole.navAria")}>
        <Link className="ilc-nav-btn" to="/tracker">
          {t("ui.DeskConsole.nav.monitor")}
        </Link>
        <Link className="ilc-nav-btn" to={`/companies/${companyId}`}>
          {t("ui.DeskConsole.nav.evidence")}
        </Link>
        <button type="button" className="ilc-nav-btn" onClick={() => onJumpTab?.("review")}>
          {t("ui.DeskConsole.nav.review")}
        </button>
        <button type="button" className="ilc-nav-btn" onClick={() => onJumpTab?.("corpus")}>
          {t("ui.DeskConsole.nav.corpus")}
        </button>
        <button type="button" className="ilc-nav-btn" onClick={() => onJumpTab?.("pit")}>
          PIT
        </button>
        <Link className="ilc-nav-btn" to="/tracker?tab=sectors">
          {t("ui.DeskConsole.nav.sectors")}
        </Link>
        <Link className="ilc-nav-btn" to={`/companies/${companyId}`}>
          {t("ui.DeskConsole.nav.dossier")}
        </Link>
        <Link className="ilc-nav-btn" to="/research">
          {t("ui.DeskConsole.nav.research")}
        </Link>
      </nav>

      {err && <p className="ilc-error">{err}</p>}
      {loading && <p className="ilc-muted">{t("ui.DeskConsole.loading")}</p>}

      <div className="ilc-grid">
        {/* GCI Monitor */}
        <section className="ilc-panel ilc-span-monitor" aria-label={t("ui.DeskConsole.monitor.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.monitor.title")}</h3>
            <span className="ilc-muted">{t("ui.DeskConsole.monitor.sub")}</span>
          </header>
          <div className="ilc-table-wrap">
            <table className="ilc-table">
              <thead>
                <tr>
                  <th>{t("ui.DeskConsole.col.ticker")}</th>
                  <th>GCI</th>
                  <th>Δ</th>
                  <th>{t("ui.DeskConsole.col.quality")}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 16).map((r) => (
                  <tr
                    key={r.id}
                    className={r.id === companyId ? "is-active" : undefined}
                    onClick={() => onSelectCompany(r.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onSelectCompany(r.id);
                    }}
                    tabIndex={0}
                    role="button"
                  >
                    <td>
                      <strong>{r.ticker}</strong>
                      <div className="ilc-sub">{r.sector}</div>
                    </td>
                    <td className={`ilc-num tone-${gciTone(r.gci_score)}`}>
                      {formatCompanyScore(r.gci_score)}
                    </td>
                    <td>
                      <ChangeChip value={r.gci_change_pct} horizon={r.gci_change_horizon} />
                    </td>
                    <td>
                      <QualityBadge quality={r.data_quality} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Main GCI chart */}
        <section className="ilc-panel ilc-span-chart" aria-label={t("ui.DeskConsole.chart.aria")}>
          <header className="ilc-panel-h">
            <div>
              <h3>
                {t("ui.DeskConsole.chart.title", { ticker: selected?.ticker || companyId })}
              </h3>
              <p className="ilc-sub">
                {t("ui.DeskConsole.chart.sub", { name: selected?.name || detail?.name || "—" })}
              </p>
            </div>
            <div className="ilc-score-block">
              <ScoreReveal score={detail?.gci_score ?? selected?.gci_score} size="md" />
              <ChangeChip
                value={detail?.gci_change_pct ?? selected?.gci_change_pct}
                horizon={detail?.gci_change_horizon ?? selected?.gci_change_horizon}
              />
            </div>
          </header>
          {showGciGraphs && (
          <div className="ilc-chart">
            {chartPts.length >= 2 ? (
              <LineChart
                points={chartPts}
                height={220}
                color="#3dff9a"
                yDomain={[0, 100]}
                ariaLabel={t("ui.DeskConsole.chart.historyAria")}
              />
            ) : (
              <p className="ilc-muted">{t("ui.DeskConsole.chart.empty")}</p>
            )}
          </div>
          )}
        </section>

        {/* Outcomes strip */}
        <section className="ilc-panel ilc-span-chain" aria-label={t("ui.DeskConsole.outcomes.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.outcomes.title")}</h3>
            <span className="ilc-muted">{t("ui.DeskConsole.outcomes.sub")}</span>
          </header>
          <div className="ilc-table-wrap">
            <table className="ilc-table ilc-compact">
              <thead>
                <tr>
                  <th>{t("ui.DeskConsole.col.period")}</th>
                  <th>{t("ui.DeskConsole.col.metric")}</th>
                  <th>{t("ui.DeskConsole.col.label")}</th>
                  <th>{t("ui.DeskConsole.col.score")}</th>
                </tr>
              </thead>
              <tbody>
                {outcomes.length === 0 && (
                  <tr>
                    <td colSpan={4} className="ilc-muted">
                      {t("ui.DeskConsole.outcomes.empty")}
                    </td>
                  </tr>
                )}
                {outcomes.map((o, i) => (
                  <tr key={`${o.period}-${o.metric}-${i}`}>
                    <td>{o.period}</td>
                    <td className="ilc-mono">{metricDisplayName(o.metric)}</td>
                    <td>
                      <span className={`ilc-tag label-${o.label}`}>{o.label}</span>
                    </td>
                    <td className="ilc-num">{formatScore(o.contribution_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Alerts feed */}
        <section className="ilc-panel ilc-span-news" aria-label={t("ui.DeskConsole.alerts.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.alerts.title")}</h3>
            <span className="ilc-muted">{t("ui.DeskConsole.alerts.sub")}</span>
          </header>
          <ul className="ilc-feed">
            {alerts.length === 0 && <li className="ilc-muted">{t("ui.DeskConsole.alerts.empty")}</li>}
            {alerts.map((a, i) => (
              <li key={`${a.company_id}-${a.kind}-${i}`}>
                <button
                  type="button"
                  className="ilc-feed-row"
                  onClick={() => onSelectCompany(a.company_id)}
                >
                  <span className={severityClass(a.severity)}>{a.severity || a.kind}</span>
                  <span className="ilc-feed-ticker">{a.ticker}</span>
                  <span className="ilc-feed-msg">{a.message}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        {/* Peer quick view */}
        <section className="ilc-panel ilc-span-peers" aria-label={t("ui.DeskConsole.peers.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.peers.title", { sector: selected?.sector || t("ui.DeskConsole.peers.sector") })}</h3>
          </header>
          <div className="ilc-peer-grid">
            {peers.map((p) => (
              <button
                key={p.id}
                type="button"
                className="ilc-peer"
                onClick={() => onSelectCompany(p.id)}
              >
                <strong>{p.ticker}</strong>
                <span className={`ilc-num tone-${gciTone(p.gci_score)}`}>
                  {formatCompanyScore(p.gci_score)}
                </span>
                <ChangeChip value={p.gci_change_pct} horizon={p.gci_change_horizon} />
              </button>
            ))}
            {peers.length === 0 && <p className="ilc-muted">{t("ui.DeskConsole.peers.empty")}</p>}
          </div>
        </section>

        {/* Queue screener */}
        <section className="ilc-panel ilc-span-screen" aria-label={t("ui.DeskConsole.queues.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.queues.title")}</h3>
            <button type="button" className="ilc-linkish" onClick={() => onJumpTab?.("review")}>
              {t("ui.DeskConsole.queues.openReview")}
            </button>
          </header>
          <div className="ilc-queue-cols">
            <div>
              <h4>{t("ui.DeskConsole.queues.extract")}</h4>
              <ul>
                {(pending.length ? pending : []).slice(0, 5).map((b) => (
                  <li key={b.id}>
                    <button type="button" onClick={() => onSelectCompany(b.company_id)}>
                      {t("ui.DeskConsole.queues.stmts", { company: b.company_id, n: b.statements?.length || 0 })}
                    </button>
                  </li>
                ))}
                {!pending.length && <li className="ilc-muted">{t("ui.DeskConsole.queues.clear")}</li>}
              </ul>
            </div>
            <div>
              <h4>{t("ui.DeskConsole.queues.labeling")}</h4>
              <ul>
                {labelQ.slice(0, 5).map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => item.company_id && onSelectCompany(item.company_id)}
                    >
                      {item.company_id} · {item.status || t("ui.DeskConsole.queues.queued")}
                    </button>
                  </li>
                ))}
                {!labelQ.length && <li className="ilc-muted">{t("ui.DeskConsole.queues.empty")}</li>}
              </ul>
            </div>
          </div>
        </section>

        {/* Metric breakdown */}
        <section className="ilc-panel ilc-span-metric" aria-label={t("ui.DeskConsole.metric.aria")}>
          <header className="ilc-panel-h">
            <h3>{t("ui.DeskConsole.metric.title")}</h3>
            <span className="ilc-muted">{selected?.ticker || companyId}</span>
          </header>
          <ul className="ilc-bars">
            {metricBars.map(({ metric, score }) => (
              <li key={metric}>
                <span className="ilc-bar-label">{metric.replace(/_/g, " ")}</span>
                <span className="ilc-bar-track">
                  <span
                    className={`ilc-bar-fill tone-${gciTone(score)}`}
                    style={{ width: `${Math.max(4, Math.min(100, score))}%` }}
                  />
                </span>
                <span className="ilc-num">{formatCompanyScore(score)}</span>
              </li>
            ))}
            {!metricBars.length && <li className="ilc-muted">{t("ui.DeskConsole.metric.empty")}</li>}
          </ul>
        </section>
      </div>

      <footer className="ilc-status">
        <span>{t("ui.DeskConsole.footer.desk")}</span>
        <span>{t("ui.DeskConsole.footer.coverage")}</span>
        <span>{t("ui.DeskConsole.footer.noAdvice")}</span>
        <span>
          {t("ui.DeskConsole.footer.peerRank", {
            rank: detail?.peer_rank_in_sector ?? "—",
            avg: formatScore(detail?.sector_avg_gci),
          })}
        </span>
      </footer>
    </div>
  );
}
