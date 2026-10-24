import { useEffect, useMemo, useState } from "react";
import Disclaimer from "../components/Disclaimer";
import PlanAccessGate from "../components/PlanAccessGate";
import { useI18n } from "../i18n";
import {
  fetchHoldingsLatest,
  postHoldingsLookthrough,
  type HoldingsLine,
  type HoldingsReport,
} from "../lib/api";
import { useAuth } from "../lib/auth";

type DraftLine = { isin?: string; weight: number; residual?: string; name?: string };

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

function parseHoldings(text: string): DraftLine[] {
  const rows: DraftLine[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || /^isin\b/i.test(line)) continue;
    const [isin, weight, residual, name] = line.split(",").map((part) => part.trim());
    const kind = (residual || "").toLowerCase();
    rows.push({
      isin: isin || undefined,
      weight: Number(weight),
      residual: kind || undefined,
      name: name || undefined,
    });
  }
  return rows;
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
  const { token } = useAuth();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [asOf, setAsOf] = useState(today);
  const [fileText, setFileText] = useState("isin,weight,residual,name\n");
  const [schemeText, setSchemeText] = useState("");
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
          setSchemeText(points.map((point) => `${point.as_of}, ${point.value}`).join("\n"));
        }
        if (view.lines?.length) {
          const body = view.lines
            .map((line) => [line.isin || "", line.weight, line.residual || "", line.name || ""].join(","))
            .join("\n");
          setFileText(`isin,weight,residual,name\n${body}\n`);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <section className="landing-page" data-testid="holdings-page">
      <div className="panel">
        <p className="landing-kicker">{t("holdings.kicker")}</p>
        <h1 style={{ marginTop: 0 }}>{t("holdings.title")}</h1>
        <p className="muted">{t("holdings.lede")}</p>
        <form
          className="admin-inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            setBusy(true);
            void postHoldingsLookthrough(
              { as_of: asOf, lines: parseHoldings(fileText), scheme: parseScheme(schemeText) },
              token,
            )
              .then(setReport)
              .catch((ex: Error) => setError(ex.message))
              .finally(() => setBusy(false));
          }}
        >
          <label>
            {t("holdings.asOf")}
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} required />
          </label>
          <label style={{ display: "block", marginTop: 12 }}>
            {t("holdings.file")}
            <textarea
              value={fileText}
              onChange={(e) => setFileText(e.target.value)}
              rows={8}
              style={{ width: "100%", marginTop: 6 }}
              aria-label={t("holdings.file")}
              data-testid="holdings-file"
            />
          </label>
          <label style={{ display: "block", marginTop: 12 }}>
            {t("holdings.scheme")}
            <textarea
              value={schemeText}
              onChange={(e) => setSchemeText(e.target.value)}
              rows={3}
              style={{ width: "100%", marginTop: 6 }}
              aria-label={t("holdings.scheme")}
              data-testid="holdings-scheme"
              placeholder={t("holdings.schemePlaceholder")}
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy} style={{ marginTop: 12 }}>
            {busy ? t("holdings.working") : t("holdings.run")}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
        {report ? (
          <div data-testid="holdings-result">
            <p>{report.statement}</p>
            <p className="muted">{report.note}</p>
            <p data-testid="holdings-covered-gci">
              {t("holdings.covered")}: {report.covered_gci ?? "—"} · {report.covered_weight_pct}%{" "}
              {t("holdings.ofFile")}
            </p>
            {report.manager ? <p data-testid="holdings-manager">{report.manager.statement}</p> : null}
            {report.scheme ? <p data-testid="holdings-scheme-result">{report.scheme.statement}</p> : null}
            {report.diff?.prior_as_of ? (
              <p data-testid="holdings-diff">
                {t("holdings.prior", { date: report.diff.prior_as_of })}{" "}
                {report.diff.prior_covered_gci ?? "—"}
                {report.diff.covered_gci_change != null
                  ? ` (${report.diff.covered_gci_change > 0 ? "+" : ""}${report.diff.covered_gci_change})`
                  : ""}
              </p>
            ) : null}
            <WeightTable title={t("holdings.scored")} rows={report.scored} testId="holdings-scored" />
            <WeightTable title={t("holdings.gaps")} rows={report.gaps} testId="holdings-gaps" />
            <WeightTable title={t("holdings.residual")} rows={report.residual} testId="holdings-residual" />
          </div>
        ) : null}
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
    >
      <HoldingsDesk />
    </PlanAccessGate>
  );
}
