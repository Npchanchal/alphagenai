import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import PlanAccessGate from "../components/PlanAccessGate";
import { NinjaNav } from "./NinjaPage";
import { useI18n } from "../i18n";
import {
  fetchHoldingsLatest,
  postHoldingsLookthrough,
  type HoldingsLine,
  type HoldingsReport,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { metricDisplayName } from "../lib/score";

type EditorLine = { isin: string; weight: string; residual: string; name: string };
type SchemePoint = { as_of: string; value: string };

const EMPTY_LINE: EditorLine = { isin: "", weight: "", residual: "", name: "" };

function parseScheme(text: string): { as_of: string; value: number }[] {
  const rows: { as_of: string; value: number }[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || /^date\b/i.test(line)) continue;
    const [asOf, value] = line.split(",").map((part) => part.trim());
    if (!asOf) continue;
    rows.push({ as_of: asOf, value: Number(value) });
  }
  return rows;
}

function parseHoldings(text: string): EditorLine[] {
  const rows: EditorLine[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || /^isin\b/i.test(line)) continue;
    const [isin, weight, residual, name] = line.split(",").map((part) => part.trim());
    rows.push({
      isin: isin || "",
      weight: weight || "",
      residual: (residual || "").toLowerCase(),
      name: name || "",
    });
  }
  return rows;
}

function SchemeChart({ points }: { points: { as_of: string; value: number }[] }) {
  if (points.length < 2) return null;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 280;
  const h = 72;
  const coords = points.map((point, index) => {
    const x = points.length === 1 ? w / 2 : (index / (points.length - 1)) * (w - 8) + 4;
    const y = 8 + (1 - (point.value - min) / span) * (h - 20);
    return `${x},${y}`;
  });
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Scheme values" style={{ width: "100%", maxWidth: 320, height: "auto" }}>
      <polyline fill="none" stroke="var(--ink)" strokeWidth="1.6" points={coords.join(" ")} />
    </svg>
  );
}

function WeightTable({ title, rows, testId }: { title: string; rows: HoldingsLine[]; testId: string }) {
  if (rows.length === 0) return null;
  return (
    <div>
      <h2>{title}</h2>
      <table className="admin-table" data-testid={testId}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Weight</th>
            <th>Published GCI</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={`${row.isin || row.kind || row.name}-${i}`}>
              <td>
                {row.name || row.isin || row.kind}
                {row.ticker ? ` · ${row.ticker}` : ""}
                {row.reason ? <div className="muted">{row.reason}</div> : null}
              </td>
              <td>{row.weight}</td>
              <td>{row.gci_score ?? "—"}</td>
              <td>{row.confidence_tier || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HoldingsDesk() {
  const { t } = useI18n();
  const { token, preferences } = useAuth();
  const starred = preferences?.watchlist ?? [];
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [asOf, setAsOf] = useState(today);
  const [lines, setLines] = useState<EditorLine[]>([{ ...EMPTY_LINE }]);
  const [scheme, setScheme] = useState<SchemePoint[]>([
    { as_of: "", value: "" },
    { as_of: "", value: "" },
  ]);
  const [paste, setPaste] = useState("");
  const [schemePaste, setSchemePaste] = useState("");
  const [report, setReport] = useState<HoldingsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchHoldingsLatest(token)
      .then((view) => {
        if (cancelled) return;
        setReport(view);
        if (view.as_of) setAsOf(view.as_of);
        const points = view.scheme?.points || [];
        if (points.length) {
          setScheme(points.map((point) => ({ as_of: point.as_of, value: String(point.value) })));
          setSchemePaste(points.map((point) => `${point.as_of}, ${point.value}`).join("\n"));
        }
        if (view.lines?.length) {
          setLines(
            view.lines.map((line) => ({
              isin: line.isin || "",
              weight: String(line.weight ?? ""),
              residual: line.residual || "",
              name: line.name || "",
            })),
          );
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  function updateLine(index: number, patch: Partial<EditorLine>) {
    setLines((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  return (
    <section className="landing-page" data-testid="holdings-page">
      <div className="panel">
        <NinjaNav />
        <p className="landing-kicker">{t("holdings.kicker")}</p>
        <h1 style={{ marginTop: 0 }}>{t("holdings.title")}</h1>
        <p className="muted">
          {t("holdings.lede")} <Link to="/tracker">{t("holdings.openScreener")}</Link>
        </p>
        {report ? (
          <div data-testid="holdings-result">
            <div className="ninja-figures">
              <div className="ninja-figure-card">
                <span>{t("holdings.covered")}</span>
                <strong data-testid="holdings-covered-gci">{report.covered_gci ?? "—"}</strong>
                <p>{report.covered_weight_pct}% {t("holdings.ofFile")}</p>
              </div>
              <div className="ninja-figure-card">
                <span>{t("holdings.tilt")}</span>
                <strong data-testid="holdings-manager">{report.manager?.delivery_tilt ?? "—"}</strong>
                <p>{t("holdings.tiltHelp")} {report.manager?.equal_weight_gci ?? "—"}.</p>
              </div>
              <div className="ninja-figure-card">
                <span>{t("holdings.schemeChange")}</span>
                <strong data-testid="holdings-scheme-result">{report.scheme?.change_pct == null ? "—" : `${report.scheme.change_pct}%`}</strong>
                <p>{t("holdings.schemeHelp")}</p>
              </div>
            </div>
            <p>{report.statement}</p>
            {report.manager ? <p className="muted">{report.manager.statement}</p> : null}
            {report.scheme?.points && report.scheme.points.length > 1 ? (
              <div>
                <h2>{t("holdings.schemeSeries")}</h2>
                <SchemeChart points={report.scheme.points} />
                <p className="muted">{report.scheme.statement}</p>
              </div>
            ) : null}
            {report.diff?.prior_as_of ? (
              <p data-testid="holdings-diff">
                {t("holdings.prior", { date: report.diff.prior_as_of })}{" "}
                {report.diff.prior_covered_gci ?? "—"}
                {report.diff.covered_gci_change != null
                  ? ` (${report.diff.covered_gci_change > 0 ? "+" : ""}${report.diff.covered_gci_change})`
                  : ""}
              </p>
            ) : null}
            <WeightTable title={t("holdings.entered")} rows={report.diff?.entered || []} testId="holdings-entered" />
            <WeightTable title={t("holdings.exited")} rows={report.diff?.exited || []} testId="holdings-exited" />
            {(report.diff?.weight_changes || []).length > 0 ? (
              <div>
                <h2>{t("holdings.weightChanges")}</h2>
                <table className="admin-table" data-testid="holdings-weights">
                  <thead>
                    <tr>
                      <th>{t("holdings.name")}</th>
                      <th>{t("holdings.priorWeight")}</th>
                      <th>{t("holdings.weight")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.diff?.weight_changes?.map((row) => (
                      <tr key={`${row.name}-${row.weight}`}>
                        <td>{row.name}</td>
                        <td>{row.prior_weight}</td>
                        <td>{row.weight}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            <WeightTable title={t("holdings.scored")} rows={report.scored} testId="holdings-scored" />
            <WeightTable title={t("holdings.gaps")} rows={report.gaps} testId="holdings-gaps" />
            <WeightTable title={t("holdings.residual")} rows={report.residual} testId="holdings-residual" />
            <h2>Since you last opened this</h2>
            {report.last_opened_at ? (
              <p className="muted" style={{ fontSize: 12 }}>
                Last opened {String(report.last_opened_at).slice(0, 10)}.
              </p>
            ) : null}
            {(report.since_last_open || []).length > 0 ? (
              <ul data-testid="holdings-since">
                {(report.since_last_open || []).map((item, i) => (
                  <li key={`${item.company_id}-${item.kind}-${i}`}>
                    <Link to={`/companies/${item.company_id}`}>{item.name}</Link>
                    {": "}
                    {item.kind === "filing"
                      ? `new filing${item.title ? `, ${item.title}` : ""}${item.at ? ` (${String(item.at).slice(0, 10)})` : ""}`
                      : item.kind === "open_guidance"
                        ? `${item.count} open guidance ${item.count === 1 ? "item" : "items"}`
                        : `missed ${item.period ?? ""} ${item.metric ? metricDisplayName(item.metric) : ""}`.trim()}
                  </li>
                ))}
              </ul>
            ) : (
              <p data-testid="holdings-since">Nothing new on the names this book can score.</p>
            )}
          </div>
        ) : null}
        {!report?.lines?.length ? (
          <div data-testid="holdings-intro">
            <p>{t("holdings.introPaste")}</p>
            <p className="muted">{t("holdings.introKinds")}</p>
          </div>
        ) : null}
        {starred.length > 0 ? (
          <div data-testid="holdings-starred">
            <h2>{t("holdings.starredTitle")}</h2>
            <p className="muted">{t("holdings.starredHelp")}</p>
            <ul className="about-list">
              {starred.map((id) => (
                <li key={id}>
                  <Link to={`/companies/${id}`} className="mono">
                    {id.toUpperCase()}
                  </Link>{" "}
                  <button
                    type="button"
                    className="btn-ghost small"
                    data-testid={`holdings-add-starred-${id}`}
                    onClick={() =>
                      setLines((current) => [
                        ...current.filter((line) => line.isin || line.name || line.weight),
                        { ...EMPTY_LINE, name: id.toUpperCase() },
                      ])
                    }
                  >
                    {t("holdings.addStarred")}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            setBusy(true);
            const payload = lines
              .filter((line) => line.isin || line.name || line.weight)
              .map((line) => ({
                isin: line.isin || undefined,
                weight: Number(line.weight),
                residual: line.residual || undefined,
                name: line.name || undefined,
              }));
            const schemeRows = scheme
              .filter((point) => point.as_of && point.value)
              .map((point) => ({ as_of: point.as_of, value: Number(point.value) }));
            void postHoldingsLookthrough({ as_of: asOf, lines: payload, scheme: schemeRows }, token)
              .then(setReport)
              .catch((ex: Error) => setError(ex.message))
              .finally(() => setBusy(false));
          }}
        >
          <label>
            {t("holdings.asOf")}
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} required />
          </label>
          <div style={{ marginTop: 12 }}>
            {lines.map((line, index) => (
              <div className="holdings-line" key={`line-${index}`}>
                <input
                  aria-label={t("holdings.identifier")}
                  placeholder={t("holdings.identifier")}
                  value={line.isin}
                  onChange={(e) => updateLine(index, { isin: e.target.value })}
                />
                <input
                  aria-label={t("holdings.weight")}
                  placeholder={t("holdings.weight")}
                  value={line.weight}
                  onChange={(e) => updateLine(index, { weight: e.target.value })}
                />
                <select
                  aria-label={t("holdings.kind")}
                  value={line.residual}
                  onChange={(e) => updateLine(index, { residual: e.target.value })}
                >
                  <option value="">{t("holdings.kind")}</option>
                  <option value="cash">{t("holdings.kindCash")}</option>
                  <option value="debt">{t("holdings.kindDebt")}</option>
                  <option value="indirect">{t("holdings.kindIndirect")}</option>
                  <option value="other">{t("holdings.kindOther")}</option>
                </select>
                <input
                  aria-label={t("holdings.name")}
                  placeholder={t("holdings.name")}
                  value={line.name}
                  onChange={(e) => updateLine(index, { name: e.target.value })}
                />
                <button type="button" className="btn" onClick={() => setLines((current) => current.filter((_, i) => i !== index))}>
                  {t("holdings.removeLine")}
                </button>
              </div>
            ))}
            <button type="button" className="btn" onClick={() => setLines((current) => [...current, { ...EMPTY_LINE }])}>
              {t("holdings.addLine")}
            </button>
          </div>
          <details style={{ marginTop: 12 }}>
            <summary>{t("holdings.paste")}</summary>
            <textarea
              value={paste}
              onChange={(e) => {
                setPaste(e.target.value);
                const parsed = parseHoldings(e.target.value);
                if (parsed.length) setLines(parsed);
              }}
              rows={5}
              style={{ width: "100%", marginTop: 6 }}
              aria-label={t("holdings.file")}
              data-testid="holdings-file"
              placeholder="isin,weight,residual,name"
            />
          </details>
          <h2>{t("holdings.scheme")}</h2>
          {scheme.map((point, index) => (
            <div className="holdings-scheme-line" key={`scheme-${index}`}>
              <input type="date" value={point.as_of} aria-label={t("holdings.asOf")} onChange={(e) => setScheme((current) => current.map((row, i) => i === index ? { ...row, as_of: e.target.value } : row))} />
              <input value={point.value} aria-label={t("holdings.scheme")} onChange={(e) => setScheme((current) => current.map((row, i) => i === index ? { ...row, value: e.target.value } : row))} />
              <button type="button" className="btn" onClick={() => setScheme((current) => current.filter((_, i) => i !== index))}>{t("holdings.removeLine")}</button>
            </div>
          ))}
          <button type="button" className="btn" onClick={() => setScheme((current) => [...current, { as_of: "", value: "" }])}>{t("holdings.addLine")}</button>
          <details style={{ marginTop: 8 }}>
            <summary>{t("holdings.paste")}</summary>
            <textarea
              value={schemePaste}
              onChange={(e) => {
                setSchemePaste(e.target.value);
                const parsed = parseScheme(e.target.value);
                if (parsed.length) setScheme(parsed.map((point) => ({ as_of: point.as_of, value: String(point.value) })));
              }}
              rows={3}
              style={{ width: "100%", marginTop: 6 }}
              aria-label={t("holdings.scheme")}
              data-testid="holdings-scheme"
              placeholder={t("holdings.schemePlaceholder")}
            />
          </details>
          <button type="submit" className="btn-primary" disabled={busy} style={{ marginTop: 12 }}>
            {busy ? t("holdings.working") : t("holdings.run")}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </div>
      <Disclaimer />
    </section>
  );
}

export default function HoldingsPage() {
  const { t } = useI18n();
  return (
    <PlanAccessGate
      feature="holdings"
      title={t("holdings.title")}
      description={t("holdings.gate")}
      returnTo="/holdings"
      testId="holdings-gate"
      alternate={{ to: "/tracker", label: t("holdings.openScreener") }}
    >
      <HoldingsDesk />
    </PlanAccessGate>
  );
}
