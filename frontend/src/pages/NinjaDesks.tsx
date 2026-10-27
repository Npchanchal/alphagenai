import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CompanyPicker from "../components/CompanyPicker";
import { useI18n } from "../i18n";
import {
  deleteNinjaObservation,
  fetchCompanies,
  fetchNinjaIndex,
  fetchNinjaTests,
  fetchNinjaWorksheets,
  postNinjaObservation,
  postNinjaRating,
  postNinjaWorksheet,
  type CompanySummary,
  type NinjaIndex,
  type NinjaTestRow,
  type NinjaWorksheet,
  type NinjaWorksheetRecord,
} from "../lib/api";
import { useAuth } from "../lib/auth";

const TEMPLATES = [
  { id: "dcf", labelKey: "ninja.template.dcf", helpKey: "ninja.templateHelp.dcf" },
  { id: "relative", labelKey: "ninja.template.relative", helpKey: "ninja.templateHelp.relative" },
  { id: "residual_income", labelKey: "ninja.template.residual", helpKey: "ninja.templateHelp.residual" },
  { id: "reverse_dcf", labelKey: "ninja.template.reverse", helpKey: "ninja.templateHelp.reverse" },
  { id: "asset_value", labelKey: "ninja.template.asset", helpKey: "ninja.templateHelp.asset" },
] as const;

const LAYERS = ["accounting", "causality", "conduct", "execution"] as const;

type TemplateId = (typeof TEMPLATES)[number]["id"];

type Inputs = {
  cashFlows: string;
  discount: string;
  terminal: string;
  metric: string;
  multiple: string;
  book: string;
  roe: string;
  cost: string;
  payout: string;
  years: string;
  price: string;
  cash: string;
  items: string;
};

const EMPTY: Inputs = {
  cashFlows: "",
  discount: "",
  terminal: "",
  metric: "",
  multiple: "",
  book: "",
  roe: "",
  cost: "",
  payout: "",
  years: "",
  price: "",
  cash: "",
  items: "",
};

function textOf(value: unknown): string {
  if (value == null) return "";
  return String(value);
}

function inputsFromSaved(template: TemplateId, raw: Record<string, unknown> | undefined): Inputs {
  const next = { ...EMPTY };
  if (!raw) return next;
  if (template === "dcf") {
    const flows = Array.isArray(raw.cash_flows) ? raw.cash_flows.join(", ") : "";
    next.cashFlows = flows;
    next.discount = textOf(raw.discount_rate_pct);
    next.terminal = textOf(raw.terminal_value);
  } else if (template === "relative") {
    next.metric = textOf(raw.metric);
    next.multiple = textOf(raw.multiple);
  } else if (template === "residual_income") {
    next.book = textOf(raw.book_value);
    next.roe = textOf(raw.roe_pct);
    next.cost = textOf(raw.cost_of_equity_pct);
    next.payout = textOf(raw.payout_pct);
    next.years = textOf(raw.years);
  } else if (template === "reverse_dcf") {
    next.price = textOf(raw.price);
    next.cash = textOf(raw.cash_flow);
    next.discount = textOf(raw.discount_rate_pct);
  } else if (Array.isArray(raw.items)) {
    next.items = raw.items
      .map((item) => {
        const row = item as { name?: string; amount?: number };
        return `${row.name ?? ""}, ${row.amount ?? ""}`;
      })
      .join("\n");
  }
  return next;
}

function useCompanyParam() {
  const [params, setParams] = useSearchParams();
  const companyId = params.get("company") || "";
  function setCompany(id: string) {
    const next = new URLSearchParams(params);
    if (id) next.set("company", id);
    else next.delete("company");
    setParams(next, { replace: true });
  }
  return [companyId, setCompany] as const;
}

function useCompanyList() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  useEffect(() => {
    let cancelled = false;
    fetchCompanies({ limit: 500 })
      .then((rows) => {
        if (!cancelled) setCompanies(rows);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  return companies;
}

export function ValuationDesk() {
  const { t } = useI18n();
  const { token } = useAuth();
  const companies = useCompanyList();
  const [companyId, setCompany] = useCompanyParam();
  const [template, setTemplate] = useState<TemplateId>("dcf");
  const [inputs, setInputs] = useState<Inputs>(EMPTY);
  const [result, setResult] = useState<NinjaWorksheet | null>(null);
  const [history, setHistory] = useState<NinjaWorksheetRecord["history"]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const selected = companies.find((row) => row.id === companyId);
  const help = TEMPLATES.find((item) => item.id === template)?.helpKey ?? "ninja.templateHelp.dcf";

  function setField(key: keyof Inputs, value: string) {
    setInputs((current) => ({ ...current, [key]: value }));
  }

  useEffect(() => {
    if (!token || !companyId) {
      setInputs(EMPTY);
      setHistory([]);
      setResult(null);
      return;
    }
    let cancelled = false;
    fetchNinjaWorksheets(companyId, template, token)
      .then((body) => {
        if (cancelled) return;
        setHistory(body.history);
        const latest = body.latest && body.latest.template === template ? body.latest : null;
        setInputs(inputsFromSaved(template, latest?.inputs));
        setResult(latest);
      })
      .catch((ex: Error) => {
        if (!cancelled) setError(ex.message);
      });
    return () => {
      cancelled = true;
    };
  }, [token, companyId, template]);

  function body(): Record<string, unknown> {
    const common = { company_id: companyId };
    if (template === "dcf") {
      return {
        ...common,
        cash_flows: inputs.cashFlows.split(",").map((part) => Number(part.trim())).filter((n) => !Number.isNaN(n)),
        discount_rate_pct: Number(inputs.discount),
        terminal_value: Number(inputs.terminal),
      };
    }
    if (template === "relative") return { ...common, metric: Number(inputs.metric), multiple: Number(inputs.multiple) };
    if (template === "residual_income") {
      return {
        ...common,
        book_value: Number(inputs.book),
        roe_pct: Number(inputs.roe),
        cost_of_equity_pct: Number(inputs.cost),
        payout_pct: Number(inputs.payout),
        years: Number(inputs.years),
      };
    }
    if (template === "reverse_dcf") {
      return { ...common, price: Number(inputs.price), cash_flow: Number(inputs.cash), discount_rate_pct: Number(inputs.discount) };
    }
    const lines = inputs.items
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, amount] = line.split(",").map((part) => part.trim());
        return { name, amount: Number(amount) };
      });
    return { ...common, items: lines };
  }

  return (
    <form
      className="ninja-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!companyId) return;
        setBusy(true);
        setError(null);
        void postNinjaWorksheet(template, body(), token)
          .then((saved) => {
            setResult(saved);
            return fetchNinjaWorksheets(companyId, template, token);
          })
          .then((record) => setHistory(record.history))
          .catch((ex: Error) => setError(ex.message))
          .finally(() => setBusy(false));
      }}
    >
      <CompanyPicker
        companies={companies}
        value={companyId}
        onChange={setCompany}
        label={t("ninja.company")}
        allLabel={t("ninja.chooseCompany")}
        testId="ninja-valuation-company"
      />
      {selected ? (
        <p>
          <strong>{t("ninja.calcPublished")}</strong> {selected.gci_score ?? "—"}
          {selected.confidence_tier ? ` · ${selected.confidence_tier}` : ""}
          {selected.as_of ? ` · ${selected.as_of}` : ""}
        </p>
      ) : null}
      <label>
        {t("ninja.templateLabel")}
        <select value={template} onChange={(e) => setTemplate(e.target.value as TemplateId)} data-testid="ninja-template">
          {TEMPLATES.map((item) => (
            <option key={item.id} value={item.id}>{t(item.labelKey)}</option>
          ))}
        </select>
      </label>
      <p className="muted">{t(help)}</p>
      {template === "dcf" ? (
        <>
          <label>{t("ninja.cashFlows")}<input value={inputs.cashFlows} onChange={(e) => setField("cashFlows", e.target.value)} /></label>
          <label>{t("ninja.discount")}<input value={inputs.discount} onChange={(e) => setField("discount", e.target.value)} /></label>
          <label>{t("ninja.terminal")}<input value={inputs.terminal} onChange={(e) => setField("terminal", e.target.value)} /></label>
        </>
      ) : null}
      {template === "relative" ? (
        <>
          <label>{t("ninja.metric")}<input value={inputs.metric} onChange={(e) => setField("metric", e.target.value)} /></label>
          <label>{t("ninja.multiple")}<input value={inputs.multiple} onChange={(e) => setField("multiple", e.target.value)} /></label>
        </>
      ) : null}
      {template === "residual_income" ? (
        <>
          <label>{t("ninja.book")}<input value={inputs.book} onChange={(e) => setField("book", e.target.value)} /></label>
          <label>{t("ninja.roe")}<input value={inputs.roe} onChange={(e) => setField("roe", e.target.value)} /></label>
          <label>{t("ninja.cost")}<input value={inputs.cost} onChange={(e) => setField("cost", e.target.value)} /></label>
          <label>{t("ninja.payout")}<input value={inputs.payout} onChange={(e) => setField("payout", e.target.value)} /></label>
          <label>{t("ninja.years")}<input value={inputs.years} onChange={(e) => setField("years", e.target.value)} /></label>
        </>
      ) : null}
      {template === "reverse_dcf" ? (
        <>
          <label>{t("ninja.price")}<input value={inputs.price} onChange={(e) => setField("price", e.target.value)} /></label>
          <label>{t("ninja.cash")}<input value={inputs.cash} onChange={(e) => setField("cash", e.target.value)} /></label>
          <label>{t("ninja.discount")}<input value={inputs.discount} onChange={(e) => setField("discount", e.target.value)} /></label>
        </>
      ) : null}
      {template === "asset_value" ? (
        <label>
          {t("ninja.items")}
          <textarea value={inputs.items} onChange={(e) => setField("items", e.target.value)} rows={4} />
        </label>
      ) : null}
      <button type="submit" className="btn-primary" disabled={busy || !companyId} data-testid="ninja-run">
        {busy ? t("ninja.working") : t("ninja.run")}
      </button>
      {error ? <p className="error">{error}</p> : null}
      {result ? (
        <div>
          <p data-testid="ninja-figure">
            <strong>{result.unit === "percent" ? `${result.figure}%` : result.figure}</strong>
            {result.unit === "currency" ? ` ${t("ninja.unitsEntered")}` : ""}. {result.statement}
          </p>
          <p>
            <strong>{t("ninja.calcPublished")}</strong> {result.published_gci ?? "—"}
          </p>
          {result.sensitivity && result.sensitivity.length > 0 ? (
            <div>
              <h3>{t("ninja.sensitivity")}</h3>
              <ul>
                {result.sensitivity.map((row) => (
                  <li key={row.label}>{row.label}: {row.figure}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      <div>
        <h3>{t("ninja.history")}</h3>
        {history.length === 0 ? <p className="muted">{t("ninja.historyEmpty")}</p> : (
          <table className="admin-table">
            <tbody>
              {history.map((row) => (
                <tr key={row.id || `${row.template}-${row.saved_at}`}>
                  <td>{row.saved_at?.slice(0, 10)}</td>
                  <td>{t(TEMPLATES.find((item) => item.id === row.template)?.labelKey || "ninja.template.dcf")}</td>
                  <td>{row.unit === "percent" ? `${row.figure}%` : row.figure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </form>
  );
}

function SheetForm({
  companyId,
  period,
  report,
  onSaved,
}: {
  companyId: string;
  period: string;
  report: NinjaIndex;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const { token } = useAuth();
  const today = new Date().toISOString().slice(0, 10);
  const [error, setError] = useState<string | null>(null);
  const sheet: NinjaIndex["sheet"] = report.sheet;

  return (
    <div className="ninja-sheet" data-testid="ninja-sheet">
      <h2>{t("ninja.sheetTitle")}</h2>
      <p className="muted">{t("ninja.sheetLede")}</p>
      <p>{sheet.scale} {sheet.statement}</p>
      <div className="ninja-figure-card" data-testid="ninja-desk-blend">
        <span>{t("ninja.deskBlend")}</span>
        <strong>{sheet.desk_blend.available ? sheet.desk_blend.level : "—"}</strong>
        <p>{sheet.desk_blend.statement}</p>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {sheet.layers.map((layer) => (
        <section key={layer.layer}>
          <h3>
            {t(`ninja.layer.${layer.layer}`)}
            {" · "}
            {layer.complete ? layer.level : t("ninja.progress", { count: layer.cited, needed: layer.needed })}
          </h3>
          {layer.questions.map((question) => (
            <form
              key={`${question.id}-${question.score ?? "blank"}-${question.quote}`}
              className="ninja-question"
              onSubmit={(e) => {
                e.preventDefault();
                const form = new FormData(e.currentTarget);
                setError(null);
                void postNinjaRating(
                  {
                    company_id: companyId,
                    layer: layer.layer,
                    question: question.id,
                    period: period || question.period,
                    score: Number(form.get("score")),
                    quote: String(form.get("quote") || ""),
                    source_url: String(form.get("source") || ""),
                    as_of: String(form.get("as_of") || today),
                  },
                  token,
                )
                  .then(() => onSaved())
                  .catch((ex: Error) => setError(ex.message));
              }}
            >
              <p>{question.prompt}</p>
              <label>
                {t("ninja.score")}
                <select name="score" defaultValue={question.score == null ? "" : String(question.score)}>
                  <option value="">{t("ninja.chooseCompany")}</option>
                  {[0, 1, 2, 3, 4].map((score) => (
                    <option key={score} value={score}>{score}</option>
                  ))}
                </select>
              </label>
              <label>{t("ninja.quote")}<input name="quote" defaultValue={question.quote} /></label>
              <label>{t("ninja.source")}<input name="source" defaultValue={question.source_url} /></label>
              <label>{t("ninja.asOf")}<input name="as_of" type="date" defaultValue={question.as_of || today} /></label>
              <button type="submit" className="btn">{t("ninja.saveRating")}</button>
            </form>
          ))}
        </section>
      ))}
    </div>
  );
}

export function IndexDesk({ bridge }: { bridge?: (companyId: string, onSelect: (id: string) => void) => ReactNode }) {
  const { t } = useI18n();
  const { token } = useAuth();
  const companies = useCompanyList();
  const [companyId, setCompany] = useCompanyParam();
  const [period, setPeriod] = useState("");
  const [report, setReport] = useState<NinjaIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [layer, setLayer] = useState<(typeof LAYERS)[number]>("accounting");
  const [stance, setStance] = useState("supported");
  const [quote, setQuote] = useState("");
  const [source, setSource] = useState("");
  const [asOf, setAsOf] = useState(today);

  function load(nextPeriod = period) {
    if (!token || !companyId) {
      setReport(null);
      return;
    }
    void fetchNinjaIndex(companyId, token, nextPeriod || undefined)
      .then(setReport)
      .catch((ex: Error) => setError(ex.message));
  }

  useEffect(() => {
    load(period);
    // Reload when the company or the year changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, companyId, period]);

  const periods = Array.from(
    new Set([
      ...(report?.calculation?.years.map((row) => row.period) ?? []),
      ...(report?.sheet.periods ?? []),
    ]),
  );

  return (
    <div data-testid="ninja-indices">
      <p className="muted">{t("ninja.indicesLede")}</p>
      <CompanyPicker
        companies={companies}
        value={companyId}
        onChange={(id) => {
          setPeriod("");
          setCompany(id);
        }}
        label={t("ninja.company")}
        allLabel={t("ninja.chooseCompany")}
        testId="ninja-company"
      />
      {companyId ? (
        <label>
          {t("ninja.period")}
          <select value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="ninja-period">
            <option value="">{report?.sheet.period || t("ninja.chooseCompany")}</option>
            {periods.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
      ) : (
        <p className="muted">{t("ninja.chooseCompany")}</p>
      )}
      {bridge
        ? bridge(companyId, (id) => {
            setPeriod("");
            setCompany(id);
          })
        : null}
      {companyId && report ? (
        <>
          <h2>{t("ninja.supportedShare")}</h2>
          <p>{report.statement}</p>
          <table className="admin-table">
            <tbody>
              {report.layers.map((row) => (
                <tr key={row.layer}>
                  <td>{t(`ninja.layer.${row.layer}`)}</td>
                  <td>{t("ninja.progress", { count: row.count, needed: row.needed })}</td>
                  <td data-testid={`ninja-level-${row.layer}`}>{row.published ? row.level : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>{t("ninja.quoteList")}</h3>
          {report.observations.length === 0 ? <p>{t("ninja.quoteEmpty")}</p> : (
            <ul>
              {report.observations.map((row) => (
                <li key={row.id || `${row.layer}-${row.as_of}-${row.quote}`}>
                  {t(`ninja.layer.${row.layer}`)} · {row.stance === "supported" ? t("ninja.supported") : t("ninja.contradicted")} · {row.quote}{" "}
                  <a href={row.source_url} target="_blank" rel="noreferrer">{row.as_of}</a>
                  {row.id ? (
                    <button
                      type="button"
                      className="btn"
                      style={{ marginLeft: 8 }}
                      onClick={() => {
                        void deleteNinjaObservation(row.id as string, token)
                          .then(() => load())
                          .catch((ex: Error) => setError(ex.message));
                      }}
                    >
                      {t("ninja.remove")}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          <form
            className="ninja-form"
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
            <button type="submit" className="btn-primary">{t("ninja.saveNote")}</button>
          </form>
          {report.sheet ? (
            <SheetForm
              companyId={companyId}
              period={period || report.sheet.period || report.calculation?.years[report.calculation.years.length - 1]?.period || ""}
              report={report}
              onSaved={() => load()}
            />
          ) : null}
        </>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

function OutcomeTable({ rows }: { rows: NinjaTestRow[] }) {
  const { t } = useI18n();
  if (rows.length === 0) return null;
  return (
    <div className="table-scroll">
      <table className="admin-table" data-testid="ninja-test-rows">
        <thead>
          <tr>
            <th>{t("ninja.company")}</th>
            <th>{t("ninja.calcYears")}</th>
            <th>{t("ninja.calcMetric")}</th>
                <th>{t("ninja.tests.outcome")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.company_id}-${row.period}-${row.metric_name}`}>
              <td>{row.ticker} {row.name}</td>
              <td>{row.period}</td>
              <td>{row.metric_name}{row.downward ? ` · ${t("ninja.tests.cut")}` : ""}</td>
              <td>{t(`ninja.outcome.${row.outcome}`)}</td>
              <td><Link to={`/companies/${row.company_id}`}>{t("ninja.tests.openDossier")}</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TestsDesk() {
  const { t } = useI18n();
  const { token } = useAuth();
  const [report, setReport] = useState<Awaited<ReturnType<typeof fetchNinjaTests>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setError(null);
    void fetchNinjaTests(token).then(setReport).catch((ex: Error) => setError(ex.message));
  }

  useEffect(() => {
    if (token) load();
    // Load once the seat token is present.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div data-testid="ninja-tests">
      <p className="muted">{t("ninja.testsLede")}</p>
      <button type="button" className="btn" data-testid="ninja-tests-run" onClick={() => load()}>
        {t("ninja.testsRun")}
      </button>
      {error ? <p className="error">{error}</p> : null}
      {report ? (
        <div>
          <p>{report.statement}</p>
          <h2>{t("ninja.tests.rows")}</h2>
          <p data-testid="ninja-revision">{report.downward_revision.statement}</p>
          {report.downward_revision.sufficient ? (
            <p data-testid="ninja-revision-counts">
              {t("ninja.tests.revisionCounts", {
                withN: report.downward_revision.with_revision.n,
                withShare: report.downward_revision.with_revision.miss_share_pct == null ? "—" : `${report.downward_revision.with_revision.miss_share_pct}%`,
                withoutN: report.downward_revision.without_revision.n,
                withoutShare: report.downward_revision.without_revision.miss_share_pct == null ? "—" : `${report.downward_revision.without_revision.miss_share_pct}%`,
              })}
            </p>
          ) : (
            <p data-testid="ninja-revision-counts">
              {report.downward_revision.with_revision.n} / {report.downward_revision.without_revision.n}
            </p>
          )}
          <p data-testid="ninja-persistence">{report.persistence.statement}</p>
          {report.persistence.sufficient ? (
            <p data-testid="ninja-persistence-counts">
              {t("ninja.tests.persistenceCounts", {
                n: report.persistence.companies,
                share: report.persistence.both_missed_share_pct == null ? "—" : `${report.persistence.both_missed_share_pct}%`,
              })}
            </p>
          ) : (
            <p data-testid="ninja-persistence-counts">{report.persistence.companies}</p>
          )}
          <OutcomeTable rows={report.rows} />
          <h2>{t("ninja.tests.byCompany")}</h2>
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("ninja.company")}</th>
                <th>{t("ninja.tests.met")}</th>
                <th>{t("ninja.tests.exceeded")}</th>
                <th>{t("ninja.tests.missed")}</th>
              </tr>
            </thead>
            <tbody>
              {report.by_company.map((row) => (
                <tr key={row.company_id}>
                  <td><Link to={`/companies/${row.company_id}`}>{row.ticker} {row.name}</Link></td>
                  <td>{row.met}</td>
                  <td>{row.exceeded}</td>
                  <td>{row.missed}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>{t("ninja.tests.bySector")}</h2>
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("ninja.listingSector")}</th>
                <th>{t("ninja.tests.met")}</th>
                <th>{t("ninja.tests.exceeded")}</th>
                <th>{t("ninja.tests.missed")}</th>
              </tr>
            </thead>
            <tbody>
              {report.by_sector.map((row) => (
                <tr key={row.sector}>
                  <td>{row.sector}</td>
                  <td>{row.met}</td>
                  <td>{row.exceeded}</td>
                  <td>{row.missed}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>{t("ninja.tests.withdrawal")}</h2>
          {report.flags.guidance_withdrawal.n === 0 ? <p>{t("ninja.tests.flagEmpty")}</p> : (
            <ul>
              {report.flags.guidance_withdrawal.rows.map((row) => (
                <li key={`${row.company_id}-w`}>
                  <Link to={`/companies/${row.company_id}`}>{row.ticker} {row.name}</Link>
                  {row.set_at ? ` · ${row.set_at}` : ""}
                </li>
              ))}
            </ul>
          )}
          <h2>{t("ninja.tests.definition")}</h2>
          {report.flags.definition_shift.n === 0 ? <p>{t("ninja.tests.flagEmpty")}</p> : (
            <ul>
              {report.flags.definition_shift.rows.map((row) => (
                <li key={`${row.company_id}-d`}>
                  <Link to={`/companies/${row.company_id}`}>{row.ticker} {row.name}</Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
