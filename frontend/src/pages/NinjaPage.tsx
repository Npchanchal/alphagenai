import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import PlanAccessGate from "../components/PlanAccessGate";
import { useI18n } from "../i18n";
import {
  fetchNinjaIndex,
  fetchNinjaTaxonomy,
  fetchNinjaTests,
  postNinjaObservation,
  postNinjaWorksheet,
  type NinjaWorksheet,
} from "../lib/api";
import { useAuth } from "../lib/auth";

const TEMPLATES = [
  { id: "dcf", labelKey: "ninja.template.dcf" },
  { id: "relative", labelKey: "ninja.template.relative" },
  { id: "residual_income", labelKey: "ninja.template.residual" },
  { id: "reverse_dcf", labelKey: "ninja.template.reverse" },
  { id: "asset_value", labelKey: "ninja.template.asset" },
] as const;

const LAYERS = ["accounting", "causality", "conduct", "execution"] as const;

function ValuationDesk() {
  const { t } = useI18n();
  const { token } = useAuth();
  const [template, setTemplate] = useState<(typeof TEMPLATES)[number]["id"]>("dcf");
  const [cashFlows, setCashFlows] = useState("100, 110");
  const [discount, setDiscount] = useState("10");
  const [terminal, setTerminal] = useState("0");
  const [metric, setMetric] = useState("");
  const [multiple, setMultiple] = useState("");
  const [book, setBook] = useState("");
  const [roe, setRoe] = useState("");
  const [cost, setCost] = useState("");
  const [payout, setPayout] = useState("");
  const [years, setYears] = useState("5");
  const [price, setPrice] = useState("");
  const [cash, setCash] = useState("");
  const [items, setItems] = useState("Cash, 10\nDebt, -4");
  const [result, setResult] = useState<NinjaWorksheet | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function body(): Record<string, unknown> {
    if (template === "dcf") {
      return {
        cash_flows: cashFlows.split(",").map((part) => Number(part.trim())).filter((n) => !Number.isNaN(n)),
        discount_rate_pct: Number(discount),
        terminal_value: Number(terminal),
      };
    }
    if (template === "relative") return { metric: Number(metric), multiple: Number(multiple) };
    if (template === "residual_income") {
      return {
        book_value: Number(book),
        roe_pct: Number(roe),
        cost_of_equity_pct: Number(cost),
        payout_pct: Number(payout),
        years: Number(years),
      };
    }
    if (template === "reverse_dcf") {
      return { price: Number(price), cash_flow: Number(cash), discount_rate_pct: Number(discount) };
    }
    const lines = items
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, amount] = line.split(",").map((part) => part.trim());
        return { name, amount: Number(amount) };
      });
    return { items: lines };
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        void postNinjaWorksheet(template, body(), token)
          .then(setResult)
          .catch((ex: Error) => setError(ex.message))
          .finally(() => setBusy(false));
      }}
    >
      <label>
        {t("ninja.templateLabel")}
        <select value={template} onChange={(e) => setTemplate(e.target.value as typeof template)} data-testid="ninja-template">
          {TEMPLATES.map((item) => (
            <option key={item.id} value={item.id}>
              {t(item.labelKey)}
            </option>
          ))}
        </select>
      </label>
      {template === "dcf" ? (
        <>
          <label>{t("ninja.cashFlows")}<input value={cashFlows} onChange={(e) => setCashFlows(e.target.value)} /></label>
          <label>{t("ninja.discount")}<input value={discount} onChange={(e) => setDiscount(e.target.value)} /></label>
          <label>{t("ninja.terminal")}<input value={terminal} onChange={(e) => setTerminal(e.target.value)} /></label>
        </>
      ) : null}
      {template === "relative" ? (
        <>
          <label>{t("ninja.metric")}<input value={metric} onChange={(e) => setMetric(e.target.value)} /></label>
          <label>{t("ninja.multiple")}<input value={multiple} onChange={(e) => setMultiple(e.target.value)} /></label>
        </>
      ) : null}
      {template === "residual_income" ? (
        <>
          <label>{t("ninja.book")}<input value={book} onChange={(e) => setBook(e.target.value)} /></label>
          <label>{t("ninja.roe")}<input value={roe} onChange={(e) => setRoe(e.target.value)} /></label>
          <label>{t("ninja.cost")}<input value={cost} onChange={(e) => setCost(e.target.value)} /></label>
          <label>{t("ninja.payout")}<input value={payout} onChange={(e) => setPayout(e.target.value)} /></label>
          <label>{t("ninja.years")}<input value={years} onChange={(e) => setYears(e.target.value)} /></label>
        </>
      ) : null}
      {template === "reverse_dcf" ? (
        <>
          <label>{t("ninja.price")}<input value={price} onChange={(e) => setPrice(e.target.value)} /></label>
          <label>{t("ninja.cash")}<input value={cash} onChange={(e) => setCash(e.target.value)} /></label>
          <label>{t("ninja.discount")}<input value={discount} onChange={(e) => setDiscount(e.target.value)} /></label>
        </>
      ) : null}
      {template === "asset_value" ? (
        <label>
          {t("ninja.items")}
          <textarea value={items} onChange={(e) => setItems(e.target.value)} rows={4} style={{ width: "100%" }} />
        </label>
      ) : null}
      <button type="submit" className="btn-primary" disabled={busy} style={{ marginTop: 12 }} data-testid="ninja-run">
        {busy ? t("ninja.working") : t("ninja.run")}
      </button>
      {error ? <p className="error">{error}</p> : null}
      {result ? (
        <p data-testid="ninja-figure">
          {result.figure} {result.unit}. {result.statement}
        </p>
      ) : null}
    </form>
  );
}

function IndexDesk() {
  const { t } = useI18n();
  const { token } = useAuth();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [companyId, setCompanyId] = useState("infy");
  const [layer, setLayer] = useState<(typeof LAYERS)[number]>("accounting");
  const [stance, setStance] = useState("supported");
  const [quote, setQuote] = useState("");
  const [source, setSource] = useState("");
  const [asOf, setAsOf] = useState(today);
  const [report, setReport] = useState<Awaited<ReturnType<typeof fetchNinjaIndex>> | null>(null);
  const [sectors, setSectors] = useState<{ sector: string; companies: number }[]>([]);
  const [sectorNote, setSectorNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchNinjaTaxonomy(token)
      .then((body) => {
        if (cancelled) return;
        setSectors(body.sectors);
        setSectorNote(body.note);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  function load(id = companyId) {
    void fetchNinjaIndex(id, token).then(setReport).catch((ex: Error) => setError(ex.message));
  }

  return (
    <div data-testid="ninja-indices">
      <p className="muted">{t("ninja.indicesLede")}</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          void postNinjaObservation(
            { company_id: companyId, layer, stance, quote, source_url: source, as_of: asOf },
            token,
          )
            .then(() => {
              setQuote("");
              load();
            })
            .catch((ex: Error) => setError(ex.message));
        }}
      >
        <label>
          {t("ninja.company")}
          <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="ninja-company" />
        </label>
        <label>
          {t("ninja.layer")}
          <select value={layer} onChange={(e) => setLayer(e.target.value as typeof layer)}>
            {LAYERS.map((item) => (
              <option key={item} value={item}>{t(`ninja.layer.${item}`)}</option>
            ))}
          </select>
        </label>
        <label>
          {t("ninja.stance")}
          <select value={stance} onChange={(e) => setStance(e.target.value)}>
            <option value="supported">{t("ninja.supported")}</option>
            <option value="contradicted">{t("ninja.contradicted")}</option>
          </select>
        </label>
        <label>{t("ninja.quote")}<input value={quote} onChange={(e) => setQuote(e.target.value)} /></label>
        <label>{t("ninja.source")}<input value={source} onChange={(e) => setSource(e.target.value)} /></label>
        <label>{t("ninja.asOf")}<input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label>
        <button type="submit" className="btn-primary" style={{ marginTop: 12 }}>{t("ninja.saveNote")}</button>
        <button type="button" className="btn" style={{ marginLeft: 8 }} onClick={() => load()}>{t("ninja.refresh")}</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {report ? (
        <div>
          <p>{report.statement}</p>
          <table className="admin-table">
            <tbody>
              {report.layers.map((row) => (
                <tr key={row.layer}>
                  <td>{t(`ninja.layer.${row.layer}`)}</td>
                  <td data-testid={`ninja-level-${row.layer}`}>{row.published ? row.level : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {sectors.length > 0 ? (
        <div data-testid="ninja-sectors">
          <h2>{t("ninja.sectorsTitle")}</h2>
          <p className="muted">{sectorNote}</p>
          <table className="admin-table">
            <tbody>
              {sectors.map((row) => (
                <tr key={row.sector}>
                  <td>{row.sector}</td>
                  <td>{row.companies}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function TestsDesk() {
  const { t } = useI18n();
  const { token } = useAuth();
  const [report, setReport] = useState<Awaited<ReturnType<typeof fetchNinjaTests>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div data-testid="ninja-tests">
      <p className="muted">{t("ninja.testsLede")}</p>
      <button
        type="button"
        className="btn-primary"
        data-testid="ninja-tests-run"
        onClick={() => {
          setError(null);
          void fetchNinjaTests(token).then(setReport).catch((ex: Error) => setError(ex.message));
        }}
      >
        {t("ninja.testsRun")}
      </button>
      {error ? <p className="error">{error}</p> : null}
      {report ? (
        <div>
          <p>{report.statement}</p>
          <p data-testid="ninja-revision">{report.downward_revision.statement}</p>
          <p data-testid="ninja-revision-counts">
            {t("ninja.tests.revisionCounts", {
              withN: report.downward_revision.with_revision.n,
              withShare: report.downward_revision.with_revision.miss_share_pct == null ? "—" : `${report.downward_revision.with_revision.miss_share_pct}%`,
              withoutN: report.downward_revision.without_revision.n,
              withoutShare: report.downward_revision.without_revision.miss_share_pct == null ? "—" : `${report.downward_revision.without_revision.miss_share_pct}%`,
            })}
          </p>
          <p data-testid="ninja-persistence">{report.persistence.statement}</p>
          <p data-testid="ninja-persistence-counts">
            {t("ninja.tests.persistenceCounts", {
              n: report.persistence.companies,
              share: report.persistence.both_missed_share_pct == null ? "—" : `${report.persistence.both_missed_share_pct}%`,
            })}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function NinjaDesk() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  const section = pathname.endsWith("/indices") ? "indices" : pathname.endsWith("/tests") ? "tests" : "valuation";
  return (
    <section className="landing-page" data-testid="ninja-page">
      <div className="panel">
        <p className="landing-kicker">{t("ninja.kicker")}</p>
        <h1 style={{ marginTop: 0 }}>{t("ninja.title")}</h1>
        <p className="muted">{t("ninja.lede")}</p>
        {section === "valuation" ? <ValuationDesk /> : null}
        {section === "indices" ? <IndexDesk /> : null}
        {section === "tests" ? <TestsDesk /> : null}
      </div>
      <Disclaimer />
    </section>
  );
}

export default function NinjaPage() {
  const { t } = useI18n();
  return (
    <PlanAccessGate
      feature="ninja"
      title={t("ninja.title")}
      description={t("ninja.gate")}
      returnTo="/ninja"
      testId="ninja-gate"
    >
      <NinjaDesk />
    </PlanAccessGate>
  );
}
