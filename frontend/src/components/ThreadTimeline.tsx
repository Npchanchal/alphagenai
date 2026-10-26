import { useState, type MouseEvent } from "react";
import InfoTip from "./InfoTip";
import { useI18n } from "../i18n";
import type { OutcomeView } from "../lib/api";
import { formatOutcomeLabel, tipForLabel } from "../lib/glossary";
import { useSourceViewer } from "../lib/SourceViewerContext";
import { withTextHighlight } from "../lib/sourceHighlight";
import {
  compareEvidence,
  formatActual,
  formatDossierDate,
  formatGuidedBand,
  formatScore,
  heatLevel,
  metricDisplayName,
  readInYearRevision,
  revisionCandle,
  scoreClass,
  type InYearStep,
  type RevisionCandle,
} from "../lib/score";

type Props = {
  threads: Record<string, OutcomeView[]>;
  /** Cumulative GCI after each period, from the dossier trend. Never invented. */
  gciByPeriod?: Record<string, number | null | undefined>;
  companyId?: string | null;
  testId?: string;
};

type TrendPoint = {
  period: string;
  guidance: number | null;
  guidanceLabel: string;
  actual: number | null;
  actualLabel: string;
  gci: number | null;
  label: string;
  candle: RevisionCandle | null;
  revisionLabels: string[];
};

function openingMid(o: OutcomeView): number {
  if (o.guided_low != null && o.guided_high != null) return (o.guided_low + o.guided_high) / 2;
  return o.guided_value;
}

function columnsFor(rows: OutcomeView[]): OutcomeView[] {
  return [...rows].sort((a, b) => compareEvidence(a, b, { key: "period", dir: "desc" }));
}

function finite(n: number | null | undefined): n is number {
  return n != null && Number.isFinite(n);
}

function stepView(
  o: OutcomeView,
  index: number,
): { band: string; direction: InYearStep; asOf: string } | null {
  const rev = o.revisions?.[index];
  if (!rev) return null;
  const prev =
    index === 0
      ? openingMid(o)
      : (o.revisions![index - 1].guided_low + o.revisions![index - 1].guided_high) / 2;
  const mid = (rev.guided_low + rev.guided_high) / 2;
  const direction: InYearStep =
    mid > prev + 1e-9 ? "raised" : mid < prev - 1e-9 ? "cut" : "unchanged";
  return {
    band: formatGuidedBand({
      guided_low: rev.guided_low,
      guided_high: rev.guided_high,
      guided_value: mid,
      metric: o.metric,
    }),
    direction,
    asOf: rev.as_of ? formatDossierDate(rev.as_of) : "",
  };
}

function trendPoints(
  rows: OutcomeView[],
  gciByPeriod?: Record<string, number | null | undefined>,
): TrendPoint[] {
  return rows.map((o) => {
    const candle = revisionCandle(o);
    const gci = gciByPeriod?.[o.period];
    return {
      period: o.period,
      guidance: openingMid(o),
      guidanceLabel: formatGuidedBand(o),
      actual: o.actual_value,
      actualLabel: o.actual_value != null ? formatActual(o) : "",
      gci: finite(gci) ? gci : null,
      label: o.label,
      candle,
      revisionLabels: (o.revisions || []).map((rev) =>
        formatGuidedBand({
          guided_low: rev.guided_low,
          guided_high: rev.guided_high,
          guided_value: (rev.guided_low + rev.guided_high) / 2,
          metric: o.metric,
        }),
      ),
    };
  });
}

function TrendChart({
  points,
  label,
}: {
  points: TrendPoint[];
  label: string;
}) {
  const { t } = useI18n();
  const [hover, setHover] = useState<number | null>(null);
  if (points.length < 2) return null;
  const values = points.flatMap((p) => {
    const nums = [p.guidance, p.actual];
    if (p.candle) nums.push(p.candle.low, p.candle.high);
    return nums.filter(finite);
  });
  if (values.length < 2) return null;
  const showGci = points.some((p) => p.gci != null);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = max === min ? Math.abs(max) * 0.08 || 1 : (max - min) * 0.14;
  const y0 = min - pad;
  const y1 = max + pad;
  const w = 640;
  const h = 168;
  const left = 12;
  const right = showGci ? 36 : 12;
  const top = 16;
  const bottom = 22;
  const innerW = w - left - right;
  const innerH = h - top - bottom;
  const x = (i: number) => left + (i / (points.length - 1)) * innerW;
  const y = (v: number) => top + (1 - (v - y0) / (y1 - y0)) * innerH;
  const yGci = (v: number) => top + (1 - v / 100) * innerH;

  const path = (key: "guidance" | "actual") => {
    let d = "";
    let pen = false;
    points.forEach((p, i) => {
      const v = p[key];
      if (!finite(v)) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  };

  let gciPath = "";
  let gciPen = false;
  points.forEach((p, i) => {
    if (p.gci == null) {
      gciPen = false;
      return;
    }
    gciPath += `${gciPen ? "L" : "M"}${x(i).toFixed(1)},${yGci(p.gci).toFixed(1)} `;
    gciPen = true;
  });

  const hovered = hover != null ? points[hover] : null;

  function onMove(e: MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * w;
    let best = 0;
    let bestD = Infinity;
    points.forEach((_, i) => {
      const d = Math.abs(x(i) - px);
      if (d < bestD) {
        best = i;
        bestD = d;
      }
    });
    setHover(best);
  }

  return (
    <div className="thread-trend-wrap">
      <svg
        className="thread-trend"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={label}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {showGci ? (
          <>
            <text x={w - 4} y={top + 4} textAnchor="end" className="trend-axis">
              100
            </text>
            <text x={w - 4} y={top + innerH} textAnchor="end" className="trend-axis">
              0
            </text>
            <path d={gciPath.trim()} className="trend-gci" />
          </>
        ) : null}
        {points.map((p, i) =>
          p.candle ? (
            <g key={`${p.period}-candle`} className={`trend-candle ${p.candle.direction}`}>
              <line x1={x(i)} x2={x(i)} y1={y(p.candle.low)} y2={y(p.candle.high)} />
              <rect
                x={x(i) - 3.5}
                y={Math.min(y(p.candle.open), y(p.candle.close))}
                width={7}
                height={Math.max(2, Math.abs(y(p.candle.close) - y(p.candle.open)))}
              />
              {p.candle.ticks.map((tick, ti) => (
                <line
                  key={`${p.period}-tick-${ti}`}
                  x1={x(i) - 5}
                  x2={x(i) + 5}
                  y1={y(tick)}
                  y2={y(tick)}
                />
              ))}
            </g>
          ) : null,
        )}
        <path d={path("guidance")} className="trend-guide" />
        <path d={path("actual")} className="trend-actual" />
        {points.map((p, i) =>
          p.guidance != null ? (
            <circle key={`${p.period}-g`} cx={x(i)} cy={y(p.guidance)} r="2.4" className="trend-guide-dot">
              <title>{`${p.period} ${p.guidanceLabel}`}</title>
            </circle>
          ) : null,
        )}
        {points.map((p, i) =>
          p.actual != null ? (
            <circle
              key={`${p.period}-actual`}
              cx={x(i)}
              cy={y(p.actual)}
              r="3.4"
              className={`trend-dot ${p.label}`}
            >
              <title>{`${p.period} ${p.actualLabel}`}</title>
            </circle>
          ) : null,
        )}
        {showGci
          ? points.map((p, i) =>
              p.gci != null ? (
                <circle
                  key={`${p.period}-gci`}
                  cx={x(i)}
                  cy={yGci(p.gci)}
                  r="3"
                  className="trend-gci-dot"
                >
                  <title>{`${p.period} ${formatScore(p.gci)}`}</title>
                </circle>
              ) : null,
            )
          : null}
        {hovered && hover != null ? (
          <line
            x1={x(hover)}
            x2={x(hover)}
            y1={top}
            y2={top + innerH}
            className="trend-hover-line"
          />
        ) : null}
        {hovered && hover != null && hovered.actual != null ? (
          <text x={x(hover) + 6} y={y(hovered.actual) - 6} className="trend-value">
            {hovered.actualLabel}
          </text>
        ) : null}
        {hovered && hover != null && hovered.gci != null ? (
          <text x={x(hover) + 6} y={yGci(hovered.gci) - 6} className="trend-value trend-value-gci">
            {formatScore(hovered.gci)}
          </text>
        ) : null}
        {points.map((p, i) => (
          <text key={p.period} x={x(i)} y={h - 6} textAnchor="middle" className="trend-label">
            {p.period}
          </text>
        ))}
      </svg>
      {hovered ? (
        <div className="thread-trend-tip" role="tooltip" data-testid="thread-trend-tip">
          <strong>{hovered.period}</strong>
          {hovered.gci != null ? (
            <span>{t("ui.ThreadTimeline.tip.gci", { value: formatScore(hovered.gci) })}</span>
          ) : null}
          <span>{t("ui.ThreadTimeline.tip.opening", { band: hovered.guidanceLabel })}</span>
          {hovered.revisionLabels.map((band, i) => (
            <span key={`${hovered.period}-rev-${i}`}>
              {t("ui.ThreadTimeline.tip.revision", { band })}
            </span>
          ))}
          <span>
            {hovered.actual != null
              ? t("ui.ThreadTimeline.tip.actual", { value: hovered.actualLabel })
              : t("ui.ThreadTimeline.periodOpen")}
          </span>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Promise threads as a heatmap. Columns are latest period first.
 * Rows: cumulative GCI, reported actual, in-year revisions, opening guidance.
 * The trend line under each thread still reads older to newer.
 */
export default function ThreadTimeline({
  threads,
  gciByPeriod,
  companyId,
  testId = "thread-timeline",
}: Props) {
  const { t } = useI18n();
  const { openSource } = useSourceViewer();
  const entries = Object.entries(threads)
    .map(([id, rows]) => {
      const columns = columnsFor(rows);
      return { id, columns, metric: columns[0]?.metric || "" };
    })
    .filter((entry) => entry.columns.length > 0)
    .sort(
      (a, b) =>
        compareEvidence(a.columns[0], b.columns[0], { key: "period", dir: "desc" }) ||
        a.id.localeCompare(b.id),
    );

  if (entries.length === 0) {
    return <p className="muted">{t("ui.ThreadTimeline.empty")}</p>;
  }

  function openFiling(opts: {
    title: string;
    url?: string | null;
    quote?: string | null;
    citationId?: string | null;
    docId?: string | null;
    spanStart?: number | null;
    spanEnd?: number | null;
  }) {
    if (!opts.url && !opts.citationId && !opts.docId && !opts.quote) return;
    openSource({
      citation_id: opts.citationId,
      doc_id: opts.docId,
      title: opts.title,
      source_url: opts.url,
      highlight_url: withTextHighlight(opts.url, opts.quote),
      quote: opts.quote,
      span_start: opts.spanStart,
      span_end: opts.spanEnd,
      company_id: companyId,
      preferSplit: true,
    });
  }

  return (
    <div data-testid={testId}>
      <ul className="thread-legend" data-testid="thread-legend">
        <li>
          <i className="swatch swatch-gci" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.gci")}
        </li>
        <li>
          <i className="swatch swatch-guide" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.guide")}
        </li>
        <li>
          <i className="swatch swatch-raise" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.raise")}
        </li>
        <li>
          <i className="swatch swatch-cut" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.cut")}
        </li>
        <li>
          <i className="swatch swatch-met" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.met")}
        </li>
        <li>
          <i className="swatch swatch-miss" aria-hidden="true" />
          {t("ui.ThreadTimeline.legend.miss")}
        </li>
      </ul>
      <div className="thread-list">
        {entries.map(({ id, columns, metric }) => (
          <ThreadCard
            key={id}
            id={id}
            columns={columns}
            metric={metric}
            gciByPeriod={gciByPeriod}
            onOpen={openFiling}
          />
        ))}
      </div>
    </div>
  );
}

function ThreadCard({
  id,
  columns,
  metric,
  gciByPeriod,
  onOpen,
}: {
  id: string;
  columns: OutcomeView[];
  metric: string;
  gciByPeriod?: Record<string, number | null | undefined>;
  onOpen: (opts: {
    title: string;
    url?: string | null;
    quote?: string | null;
    citationId?: string | null;
    docId?: string | null;
    spanStart?: number | null;
    spanEnd?: number | null;
  }) => void;
}) {
  const { t } = useI18n();
  const [revisionsOpen, setRevisionsOpen] = useState(false);
  const name = metricDisplayName(metric);
  const mids = columns.map(openingMid);
  const gMin = Math.min(...mids);
  const gMax = Math.max(...mids);
  const latest = columns[0];
  const points = trendPoints([...columns].reverse(), gciByPeriod);
  const gciValues = columns.map((o) => gciByPeriod?.[o.period]);
  const showGci = gciValues.some(finite);
  const maxSteps = Math.max(0, ...columns.map((o) => o.revisions?.length ?? 0));

  return (
    <div className="thread-row" data-testid={`thread-${id}`}>
      <div className="thread-head">
        <span className="thread-metric">{name}</span>
        <span className={`pill ${latest.label}`}>{formatOutcomeLabel(latest.label)}</span>{" "}
        <InfoTip termId={latest.label.toLowerCase()} text={tipForLabel(latest.label)} />
      </div>
      <p className="sr-only">
        {columns
          .map((o) => {
            const rev = readInYearRevision(o);
            const gci = gciByPeriod?.[o.period];
            const gciText = finite(gci)
              ? `${t("ui.ThreadTimeline.heat.gci")} ${formatScore(gci)}`
              : "";
            const revText =
              rev.direction === "none"
                ? t("ui.ThreadTimeline.heat.none")
                : t(`ui.ThreadTimeline.heat.${rev.direction}`, { band: rev.finalBand });
            const actual =
              o.actual_value != null ? formatActual(o) : t("ui.ThreadTimeline.periodOpen");
            return `${o.period}: ${gciText} ${t("ui.ThreadTimeline.heat.actual")} ${actual}, ${revText}, ${t("ui.ThreadTimeline.heat.guidance")} ${formatGuidedBand(o)}`;
          })
          .join(". ")}
      </p>
      <div className="table-scroll">
        <table className="thread-heat" data-testid="thread-heatmap">
          <thead>
            <tr>
              <th className="lane" />
              {columns.map((o, i) => (
                <th key={`${o.period}-${i}`} scope="col">
                  {o.period}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {showGci ? (
              <tr data-testid="thread-gci-row">
                <th className="lane" scope="row">
                  {t("ui.ThreadTimeline.heat.gci")}
                </th>
                {columns.map((o, i) => {
                  const gci = gciByPeriod?.[o.period];
                  const known = finite(gci);
                  return (
                    <td
                      key={`${o.period}-${i}-gci`}
                      className={known ? `heat-gci ${scoreClass(gci)}` : "heat-gci"}
                      title={t("ui.ThreadTimeline.heat.gciTip")}
                    >
                      <span className="heat-value">{known ? formatScore(gci) : "—"}</span>
                    </td>
                  );
                })}
              </tr>
            ) : null}
            <tr data-testid="thread-actual-row">
              <th className="lane" scope="row">
                {t("ui.ThreadTimeline.heat.actual")}
              </th>
              {columns.map((o, i) => (
                <td key={`${o.period}-${i}-a`} className={`heat-actual ${o.label}`}>
                  <span className="heat-value">
                    {o.actual_value != null ? formatActual(o) : "—"}
                  </span>
                  <span className={`pill ${o.label}`}>{formatOutcomeLabel(o.label)}</span>
                </td>
              ))}
            </tr>
            <tr data-testid="thread-revisions-row">
              <th className="lane" scope="row">
                {maxSteps > 0 ? (
                  <button
                    type="button"
                    className="heat-toggle"
                    aria-expanded={revisionsOpen}
                    data-testid="thread-revisions-toggle"
                    onClick={() => setRevisionsOpen((open) => !open)}
                  >
                    <i className="chevron" aria-hidden="true" />
                    {t("ui.ThreadTimeline.heat.revisions")}
                  </button>
                ) : (
                  t("ui.ThreadTimeline.heat.revisions")
                )}
              </th>
              {columns.map((o, i) => {
                const rev = readInYearRevision(o);
                const text =
                  rev.direction === "none"
                    ? t("ui.ThreadTimeline.heat.none")
                    : t(`ui.ThreadTimeline.heat.${rev.direction}`, { band: rev.finalBand });
                return (
                  <td key={`${o.period}-${i}-r`} className={`heat-rev ${rev.direction}`} title={rev.path}>
                    <span className="heat-value">{text}</span>
                    {rev.steps.length > 0 ? (
                      <span className="heat-dots" aria-hidden="true">
                        {rev.steps.map((step, stepIndex) => (
                          <i key={`${o.period}-dot-${stepIndex}`} className={`heat-dot ${step}`} />
                        ))}
                      </span>
                    ) : null}
                    {rev.steps.length > 1 ? (
                      <span className="heat-sub">
                        {t("ui.ThreadTimeline.heat.steps", { n: rev.steps.length })}
                      </span>
                    ) : null}
                  </td>
                );
              })}
            </tr>
            {revisionsOpen
              ? Array.from({ length: maxSteps }, (_, step) => (
                  <tr key={`step-${step}`} data-testid="thread-revision-step">
                    <th className="lane" scope="row">
                      {t("ui.ThreadTimeline.heat.step", { n: step + 1 })}
                    </th>
                    {columns.map((o, i) => {
                      const view = stepView(o, step);
                      if (!view) {
                        return (
                          <td key={`${o.period}-${i}-s${step}`} className="heat-rev none">
                            <span className="heat-value">—</span>
                          </td>
                        );
                      }
                      return (
                        <td
                          key={`${o.period}-${i}-s${step}`}
                          className={`heat-rev ${view.direction}`}
                        >
                          <span className="heat-value">{view.band}</span>
                          {view.asOf ? <span className="heat-sub">{view.asOf}</span> : null}
                        </td>
                      );
                    })}
                  </tr>
                ))
              : null}
            <tr data-testid="thread-guidance-row">
              <th className="lane" scope="row">
                {t("ui.ThreadTimeline.heat.guidance")}
              </th>
              {columns.map((o, i) => (
                <td
                  key={`${o.period}-${i}-g`}
                  className={`heat-guide lvl-${heatLevel(openingMid(o), gMin, gMax)}`}
                  title={formatGuidedBand(o)}
                >
                  <span className="heat-value">{formatGuidedBand(o)}</span>
                  {o.guidance_as_of ? (
                    <span className="heat-sub">{formatDossierDate(o.guidance_as_of)}</span>
                  ) : null}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <TrendChart points={points} label={t("ui.ThreadTimeline.trendLabel", { metric: name })} />
      <p className="muted thread-trend-key">{t("ui.ThreadTimeline.trendKey")}</p>
      <div className="thread-cites">
        <p className="muted thread-sources-title">{t("ui.ThreadTimeline.sources")}</p>
        {columns.map((o) => {
          const promise = o.guidance_quote || o.guided_text;
          const title = `${o.period} ${name}`;
          return (
            <div key={`${o.period}-cites`}>
              {promise ? (
                <blockquote className="thread-quote" data-testid="thread-promise">
                  {o.guidance_source_url ? (
                    <button
                      type="button"
                      className="linkish"
                      onClick={() =>
                        onOpen({
                          title,
                          url: o.guidance_source_url,
                          quote: promise,
                        })
                      }
                    >
                      {o.guidance_as_of ? formatDossierDate(o.guidance_as_of) : o.period}
                    </button>
                  ) : (
                    <span>{o.guidance_as_of ? formatDossierDate(o.guidance_as_of) : o.period}</span>
                  )}
                  {" · "}“{promise}”
                </blockquote>
              ) : null}
              {(o.revisions || []).map((rev, i) => (
                <p
                  key={`${o.period}-rev-${i}`}
                  className="muted thread-quote"
                  data-testid="thread-revision"
                >
                  {rev.source_url ? (
                    <button
                      type="button"
                      className="linkish"
                      onClick={() =>
                        onOpen({
                          title,
                          url: rev.source_url,
                          quote: rev.quote,
                        })
                      }
                    >
                      {formatDossierDate(rev.as_of)}
                    </button>
                  ) : (
                    formatDossierDate(rev.as_of)
                  )}
                  {" · "}
                  {t("ui.ThreadTimeline.revision", {
                    band: formatGuidedBand({
                      guided_low: rev.guided_low,
                      guided_high: rev.guided_high,
                      guided_value: (rev.guided_low + rev.guided_high) / 2,
                      metric: o.metric,
                    }),
                  })}
                  {rev.quote ? ` · “${rev.quote}”` : ""}
                </p>
              ))}
              {o.actual_value != null && o.quote_span ? (
                <blockquote className="thread-quote" data-testid="thread-actual">
                  {o.source_url ? (
                    <button
                      type="button"
                      className="linkish"
                      onClick={() =>
                        onOpen({
                          title,
                          url: o.source_url,
                          quote: o.quote_span,
                          citationId: o.citation_id,
                          docId: o.doc_id,
                          spanStart: o.span_start,
                          spanEnd: o.span_end,
                        })
                      }
                    >
                      {o.as_of ? formatDossierDate(o.as_of) : o.period}
                    </button>
                  ) : (
                    <span>{o.as_of ? formatDossierDate(o.as_of) : o.period}</span>
                  )}
                  {" · "}“{o.quote_span}”
                </blockquote>
              ) : o.actual_value == null ? (
                <p className="muted thread-quote" data-testid="thread-open">
                  {t("ui.ThreadTimeline.periodOpen")}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
