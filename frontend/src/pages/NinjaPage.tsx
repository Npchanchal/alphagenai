import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import PlanAccessGate from "../components/PlanAccessGate";
import ThreadTimeline from "../components/ThreadTimeline";
import { useI18n } from "../i18n";
import {
  fetchCompanyGci,
  fetchNinjaCalculations,
  fetchNinjaIndex,
  fetchNinjaTaxonomy,
  fetchNinjaTests,
  postNinjaObservation,
  postNinjaWorksheet,
  type NinjaCalculation,
  type NinjaChronology,
  type NinjaListingRow,
  type NinjaWorksheet,
  type OutcomeView,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDossierDate } from "../lib/score";

const TEMPLATES = [
  { id: "dcf", labelKey: "ninja.template.dcf" },
  { id: "relative", labelKey: "ninja.template.relative" },
  { id: "residual_income", labelKey: "ninja.template.residual" },
  { id: "reverse_dcf", labelKey: "ninja.template.reverse" },
  { id: "asset_value", labelKey: "ninja.template.asset" },
] as const;

const LAYERS = ["accounting", "causality", "conduct", "execution"] as const;

function yOf(value: number, top: number, height: number): number {
  return top + (1 - Math.min(100, Math.max(0, value)) / 100) * height;
}

function PathChart({ company }: { company: NinjaCalculation }) {
  const points = company.path;
  if (!points.length) return null;
  const w = 560;
  const h = 210;
  const padL = 36;
  const padR = 40;
  const padT = 16;
  const padB = 32;
  const innerW = w - padL - padR;
  const innerH = h - padT - padB;
  const xAt = (index: number) =>
    padL + (points.length === 1 ? innerW / 2 : (index / (points.length - 1)) * innerW);
  const ceiling = points.map((point, index) => `${index === 0 ? "M" : "L"}${xAt(index)},${yOf(point.ceiling, padT, innerH)}`).join(" ");
  const floor = [...points]
    .reverse()
    .map((point) => `L${xAt(points.indexOf(point))},${yOf(point.floor, padT, innerH)}`)
    .join(" ");
  const delivery = points
    .map((point, index) => `${index === 0 ? "M" : "L"}${xAt(index)},${yOf(point.delivery, padT, innerH)}`)
    .join(" ");
  const published = points
    .filter((point) => point.published != null)
    .map((point) => {
      const index = points.indexOf(point);
      return { x: xAt(index), y: yOf(point.published as number, padT, innerH), point };
    });
  const publishedLine = published.map((mark, index) => `${index === 0 ? "M" : "L"}${mark.x},${mark.y}`).join(" ");
  const band = points.length === 1
    ? null
    : <path d={`${ceiling} ${floor} Z`} fill="var(--band, #e7dfd4)" />;
  const single = points.length === 1 ? points[0] : null;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={company.statement} style={{ width: "100%", height: "auto" }}>
      {[0, 25, 50, 75, 100].map((tick) => (
        <g key={tick}>
          <line x1={padL} x2={w - padR} y1={yOf(tick, padT, innerH)} y2={yOf(tick, padT, innerH)} stroke="var(--line, #e4ddd4)" strokeWidth="0.6" />
          <text x={padL - 6} y={yOf(tick, padT, innerH) + 3} textAnchor="end" fontSize="10" fill="var(--muted, #5c564e)">{tick}</text>
        </g>
      ))}
      {band}
      {single ? (
        <rect
          x={xAt(0) - 10}
          y={yOf(single.ceiling, padT, innerH)}
          width="20"
          height={Math.max(2, yOf(single.floor, padT, innerH) - yOf(single.ceiling, padT, innerH))}
          fill="var(--band, #e7dfd4)"
        />
      ) : null}
      <path d={delivery} fill="none" stroke="var(--bad)" strokeWidth="1.7" strokeDasharray="4 3" />
      {points.map((point, index) => (
        <circle key={`d-${point.as_of}`} cx={xAt(index)} cy={yOf(point.delivery, padT, innerH)} r="2.6" fill="var(--bad)" />
      ))}
      {publishedLine ? <path d={publishedLine} fill="none" stroke="var(--ink)" strokeWidth="2.2" /> : null}
      {published.map((mark) => (
        <circle
          key={mark.point.as_of}
          cx={mark.x}
          cy={mark.y}
          r="3.2"
          fill={mark.point.published != null && mark.point.published > mark.point.ceiling ? "var(--bad)" : "var(--ink)"}
        />
      ))}
      {points.map((point, index) => (
        <text key={point.as_of} x={xAt(index)} y={h - 8} textAnchor="middle" fontSize="10" fill="var(--muted, #5c564e)">
          {point.as_of.slice(0, 7)}
        </text>
      ))}
    </svg>
  );
}

function YearChart({ company }: { company: NinjaCalculation }) {
  const rows = company.years;
  if (!rows.length) return null;
  const w = 560;
  const h = 220;
  const padL = 36;
  const padR = 12;
  const padT = 12;
  const padB = 36;
  const innerH = h - padT - padB;
  const slot = (w - padL - padR) / rows.length;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={company.name} style={{ width: "100%", height: "auto" }}>
      {[0, 25, 50, 75, 100].map((tick) => (
        <g key={tick}>
          <line x1={padL} x2={w - padR} y1={yOf(tick, padT, innerH)} y2={yOf(tick, padT, innerH)} stroke="var(--line, #e4ddd4)" strokeWidth="0.6" />
          <text x={padL - 6} y={yOf(tick, padT, innerH) + 3} textAnchor="end" fontSize="10" fill="var(--muted, #5c564e)">{tick}</text>
        </g>
      ))}
      {rows.map((row, index) => {
        const cx = padL + slot * index + slot / 2;
        const top = yOf(row.ceiling, padT, innerH);
        const bottom = yOf(row.floor, padT, innerH);
        return (
          <g key={`${row.period}-${row.metric}`}>
            <rect x={cx - 8} y={top} width="16" height={Math.max(2, bottom - top)} fill="var(--band, #e7dfd4)" />
            <circle
              cx={cx}
              cy={row.published_year > 100 ? padT - 4 : yOf(row.published_year, padT, innerH)}
              r="4"
              fill={row.reachable ? "var(--ink)" : "var(--bad)"}
            />
            <circle cx={cx} cy={yOf(row.delivery, padT, innerH)} r="3" fill="var(--bad)" />
            <text x={cx} y={h - 16} textAnchor="middle" fontSize="10" fill="var(--ink)">{row.period}</text>
          </g>
        );
      })}
    </svg>
  );
}

function heatBackground(value: number): string {
  if (value > 100) return "color-mix(in srgb, var(--bad) 18%, var(--paper, #f4f1ea))";
  const ink = Math.round(8 + (Math.min(100, Math.max(0, value)) / 100) * 48);
  return `color-mix(in srgb, var(--ink) ${ink}%, var(--paper, #f4f1ea))`;
}

function ScoreHeatmap({ company }: { company: NinjaCalculation }) {
  const { t } = useI18n();
  const heat = company.heatmap;
  if (!heat?.columns?.length) return null;
  const labelFor = (id: string, fallback: string) => {
    if (id === "delivery") return t("ninja.calcDelivery");
    if (id === "published_year") return t("ninja.calcYearScore");
    if (id === "floor") return t("ninja.calcFloor");
    if (id === "ceiling") return t("ninja.calcCeiling");
    return fallback;
  };
  return (
    <div>
      <h3>{t("ninja.heatTitle")}</h3>
      <p className="muted">{t("ninja.heatLede")}</p>
      <div className="table-scroll">
        <table className="admin-table ninja-heat" data-testid="ninja-heatmap">
          <thead>
            <tr>
              <th />
              {heat.columns.map((column) => (
                <th key={column.key}>
                  {column.period}
                  <br />
                  <span className="muted">{column.in_composite ? column.metric_name : `${column.metric_name} · ${t("ninja.calcContext")}`}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {heat.rows.map((row) => (
              <tr key={row.id}>
                <th scope="row">{labelFor(row.id, row.label)}</th>
                {row.values.map((value, index) => (
                  <td
                    key={heat.columns[index].key}
                    className={value > 100 ? "is-above" : undefined}
                    style={{ background: heatBackground(value) }}
                    title={String(value)}
                  >
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Chronology({ chronology }: { chronology: NinjaChronology }) {
  const { t } = useI18n();
  return (
    <div>
      <h3>{t("ninja.chronoTitle")}</h3>
      <p className="muted">{chronology.statement}</p>
      {chronology.events.length > 0 ? (
        <ol className="ninja-chrono" data-testid="ninja-chronology">
          {chronology.events.map((event, index) => (
            <li key={`${event.date}-${event.kind}-${event.period}-${event.metric}-${index}`}>
              <time dateTime={event.date || undefined}>{event.date ? formatDossierDate(event.date) : "—"}</time>
              <strong>
                {t(`ninja.chrono.${event.kind}`)} · {event.period} · {event.metric_name}
              </strong>
              {event.text ? <p>{event.text}</p> : null}
              {event.quote ? <blockquote>“{event.quote}”</blockquote> : null}
              {event.source_url ? (
                <a href={event.source_url} target="_blank" rel="noopener noreferrer">
                  {t("ninja.chronoSource")}
                </a>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function CalculationBook({ companyId, onSelect }: { companyId: string; onSelect: (id: string) => void }) {
  const { t } = useI18n();
  const { token } = useAuth();
  const [companies, setCompanies] = useState<NinjaCalculation[]>([]);
  const [listing, setListing] = useState<NinjaListingRow[]>([]);
  const [query, setQuery] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [remoteChronology, setRemoteChronology] = useState<NinjaChronology | null>(null);
  const [threads, setThreads] = useState<Record<string, OutcomeView[]> | null>(null);

  const report = companies.find((row) => row.company_id === companyId) ?? null;
  const listed = listing.find((row) => row.company_id === companyId) ?? null;
  const needle = query.trim().toLowerCase();
  const visible = listing.filter((row) => {
    if (!needle) return true;
    return [row.ticker, row.name, row.sector].join(" ").toLowerCase().includes(needle);
  });
  const worksheets = listing.filter((row) => row.has_worksheet).length;
  const chronology = report?.chronology ?? remoteChronology;

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchNinjaCalculations(token)
      .then((body) => {
        if (cancelled) return;
        setCompanies(body.companies);
        setListing(body.listing);
        setNote(body.statement);
      })
      .catch((ex: Error) => {
        if (!cancelled) setError(ex.message);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!listing.length) return;
    document.querySelector(`[data-testid="ninja-pick-${companyId}"]`)?.scrollIntoView({ block: "nearest" });
  }, [companyId, listing]);

  useEffect(() => {
    if (!token || !listed) {
      setRemoteChronology(null);
      setThreads(null);
      return;
    }
    let cancelled = false;
    if (report) {
      setRemoteChronology(null);
    } else {
      fetchNinjaIndex(companyId, token)
        .then((body) => {
          if (!cancelled) setRemoteChronology(body.chronology);
        })
        .catch(() => {
          if (!cancelled) setRemoteChronology(null);
        });
    }
    if (listed.data_quality === "hand_labeled") {
      fetchCompanyGci(companyId)
        .then((detail) => {
          if (!cancelled) setThreads(detail.threads || {});
        })
        .catch(() => {
          if (!cancelled) setThreads(null);
        });
    } else {
      setThreads(null);
    }
    return () => {
      cancelled = true;
    };
  }, [token, companyId, listed, report]);

  if (error) return <p className="error">{error}</p>;
  return (
    <div data-testid="ninja-calculations">
      <p className="muted">{t("ninja.calcLede")}</p>
      {note ? <p>{note}</p> : null}
      <h2>{t("ninja.listingTitle")}</h2>
      <label>
        {t("ninja.listingSearch")}
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          data-testid="ninja-listing-search"
        />
      </label>
      {listing.length > 0 ? (
        <p className="muted">{t("ninja.listingCount", { names: listing.length, worksheets })}</p>
      ) : null}
      <div className="ninja-listing">
        <table className="admin-table" data-testid="ninja-listing">
          <thead>
            <tr>
              <th>{t("ninja.company")}</th>
              <th>{t("ninja.listingSector")}</th>
              <th>{t("ninja.calcPublished")}</th>
              <th>{t("ninja.listingWorksheet")}</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.company_id}
                className={row.company_id === companyId ? "is-selected" : undefined}
                onClick={() => onSelect(row.company_id)}
                data-testid={`ninja-pick-${row.company_id}`}
              >
                <td>
                  <strong>{row.ticker}</strong> {row.name}
                </td>
                <td>{row.sector}</td>
                <td>{row.published_gci ?? "—"}</td>
                <td>
                  {row.data_quality === "demo_structured"
                    ? t("ninja.listingDemo")
                    : row.has_worksheet
                      ? t("ninja.listingWorksheet")
                      : t("ninja.listingNone")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {visible.length === 0 && listing.length > 0 ? <p className="muted">{t("ninja.listingEmpty")}</p> : null}
      {report ? (
        <article data-testid={`ninja-calc-${report.company_id}`} style={{ marginTop: 28 }}>
          <h2 style={{ marginBottom: 4 }}>{listed?.ticker ? `${listed.ticker} — ${report.name}` : report.name}</h2>
          <p>
            {report.sector_rule
              ? t("ninja.calcScale", {
                  rule: report.sector_rule,
                  floor: report.scale_floor ?? "",
                  decay: report.decay ?? "",
                })
              : t("ninja.calcNoScale")}
          </p>
          <p>{report.statement}</p>
          <p>
            <strong>{t("ninja.calcPublished")}</strong> {report.published_gci ?? "—"}
            {" · "}
            <strong>{t("ninja.calcDelivery")}</strong> {report.delivery}
            {" · "}
            <strong>{t("ninja.calcFloor")}</strong> {report.floor}
            {" · "}
            <strong>{t("ninja.calcCeiling")}</strong> {report.ceiling}
          </p>
          <h3>{t("ninja.calcYears")}</h3>
          <YearChart company={report} />
          <p className="muted">{t("ninja.calcMarks")}</p>
          <h3>{t("ninja.calcPath")}</h3>
          <PathChart company={report} />
          <ScoreHeatmap company={report} />
          <div className="table-scroll">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t("ninja.calcYears")}</th>
                  <th>{t("ninja.calcMetric")}</th>
                  <th>{t("ninja.calcBand")}</th>
                  <th>{t("ninja.calcActual")}</th>
                  <th>{t("ninja.calcDelivery")}</th>
                  <th>{t("ninja.calcYearScore")}</th>
                  <th>{t("ninja.calcFloor")}</th>
                  <th>{t("ninja.calcCeiling")}</th>
                  <th>{t("ninja.calcRubric")}</th>
                </tr>
              </thead>
              <tbody>
                {report.years.map((row) => (
                  <tr key={`${row.period}-${row.metric}`}>
                    <td>
                      {row.period}
                      {row.in_composite ? "" : ` · ${t("ninja.calcContext")}`}
                    </td>
                    <td>{row.metric_name}</td>
                    <td>{row.band_low}–{row.band_high}</td>
                    <td>{row.actual}</td>
                    <td>{row.delivery}</td>
                    <td>{row.reachable ? row.published_year : `${row.published_year} · ${t("ninja.calcAbove")}`}</td>
                    <td>{row.floor}</td>
                    <td>{row.ceiling}</td>
                    <td>{row.rubric_needed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : listed ? (
        <article data-testid={`ninja-calc-${listed.company_id}`} style={{ marginTop: 28 }}>
          <h2>{listed.ticker} — {listed.name}</h2>
          <p>{t("ninja.calcBlank")}</p>
        </article>
      ) : null}
      {chronology ? <Chronology chronology={chronology} /> : null}
      {threads && Object.keys(threads).length > 0 ? (
        <div>
          <h3>{t("ninja.filingHeat")}</h3>
          <ThreadTimeline threads={threads} testId="ninja-filing-heat" />
        </div>
      ) : null}
    </div>
  );
}

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
  const [params, setParams] = useSearchParams();
  const companyId = params.get("company") || "infy";
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
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
      <CalculationBook
        companyId={companyId}
        onSelect={(id) => {
          const next = new URLSearchParams(params);
          next.set("company", id);
          setParams(next, { replace: true });
        }}
      />
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
          <input
            value={companyId}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              next.set("company", e.target.value);
              setParams(next, { replace: true });
            }}
            data-testid="ninja-company"
          />
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
