import InfoTip from "./InfoTip";
import { useI18n } from "../i18n";
import type { OutcomeView } from "../lib/api";
import { formatOutcomeLabel, tipForLabel } from "../lib/glossary";
import {
  compareEvidence,
  formatActual,
  formatDossierDate,
  formatGuidedBand,
  heatLevel,
  metricDisplayName,
  readInYearRevision,
} from "../lib/score";

type Props = {
  threads: Record<string, OutcomeView[]>;
  testId?: string;
};

type TrendPoint = {
  period: string;
  guidance: number | null;
  revision: number | null;
  actual: number | null;
  label: string;
};

function openingMid(o: OutcomeView): number {
  if (o.guided_low != null && o.guided_high != null) return (o.guided_low + o.guided_high) / 2;
  return o.guided_value;
}

function columnsFor(rows: OutcomeView[]): OutcomeView[] {
  return [...rows].sort((a, b) => compareEvidence(a, b, { key: "period", dir: "asc" }));
}

function trendPoints(rows: OutcomeView[]): TrendPoint[] {
  return rows.map((o) => {
    const rev = readInYearRevision(o);
    const finalRev = o.revisions?.length
      ? (o.revisions[o.revisions.length - 1].guided_low + o.revisions[o.revisions.length - 1].guided_high) / 2
      : null;
    return {
      period: o.period,
      guidance: openingMid(o),
      revision: rev.direction === "none" ? null : finalRev,
      actual: o.actual_value,
      label: o.label,
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
  if (points.length < 2) return null;
  const values = points.flatMap((p) =>
    [p.guidance, p.revision, p.actual].filter((n): n is number => n != null && Number.isFinite(n)),
  );
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = max === min ? Math.abs(max) * 0.08 || 1 : (max - min) * 0.14;
  const y0 = min - pad;
  const y1 = max + pad;
  const w = 640;
  const h = 92;
  const left = 12;
  const right = 12;
  const top = 12;
  const bottom = 22;
  const innerW = w - left - right;
  const innerH = h - top - bottom;
  const x = (i: number) => left + (i / (points.length - 1)) * innerW;
  const y = (v: number) => top + (1 - (v - y0) / (y1 - y0)) * innerH;

  const path = (key: "guidance" | "revision" | "actual") => {
    let d = "";
    let pen = false;
    points.forEach((p, i) => {
      const v = p[key];
      if (v == null || !Number.isFinite(v)) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  };

  return (
    <svg className="thread-trend" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label}>
      <path d={path("guidance")} className="trend-guide" />
      <path d={path("revision")} className="trend-rev" />
      <path d={path("actual")} className="trend-actual" />
      {points.map((p, i) =>
        p.actual != null ? (
          <circle
            key={`${p.period}-actual`}
            cx={x(i)}
            cy={y(p.actual)}
            r="3.4"
            className={`trend-dot ${p.label}`}
          />
        ) : null,
      )}
      {points.map((p, i) => (
        <text key={p.period} x={x(i)} y={h - 6} textAnchor="middle" className="trend-label">
          {p.period}
        </text>
      ))}
    </svg>
  );
}

/**
 * Promise threads as a heatmap: opening guidance, in-year revisions, and the
 * reported actual, oldest period on the left.
 */
export default function ThreadTimeline({ threads, testId = "thread-timeline" }: Props) {
  const { t } = useI18n();
  const entries = Object.entries(threads)
    .map(([id, rows]) => {
      const columns = columnsFor(rows);
      return { id, columns, metric: columns[columns.length - 1]?.metric || columns[0]?.metric || "" };
    })
    .filter((entry) => entry.columns.length > 0)
    .sort((a, b) => metricDisplayName(a.metric).localeCompare(metricDisplayName(b.metric)) || a.id.localeCompare(b.id));

  if (entries.length === 0) {
    return <p className="muted">{t("ui.ThreadTimeline.empty")}</p>;
  }

  return (
    <div data-testid={testId}>
      <ul className="thread-legend" data-testid="thread-legend">
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
        {entries.map(({ id, columns, metric }) => {
          const name = metricDisplayName(metric);
          const mids = columns.map(openingMid);
          const gMin = Math.min(...mids);
          const gMax = Math.max(...mids);
          const last = columns[columns.length - 1];
          const points = trendPoints(columns);
          return (
            <div className="thread-row" key={id} data-testid={`thread-${id}`}>
              <div className="thread-head">
                <span className="thread-metric">{name}</span>
                <span className={`pill ${last.label}`}>{formatOutcomeLabel(last.label)}</span>{" "}
                <InfoTip termId={last.label.toLowerCase()} text={tipForLabel(last.label)} />
              </div>
              <p className="sr-only">
                {columns
                  .map((o) => {
                    const rev = readInYearRevision(o);
                    const revText =
                      rev.direction === "none"
                        ? t("ui.ThreadTimeline.heat.none")
                        : t(`ui.ThreadTimeline.heat.${rev.direction}`, { band: rev.finalBand });
                    const actual =
                      o.actual_value != null ? formatActual(o) : t("ui.ThreadTimeline.periodOpen");
                    return `${o.period}: ${t("ui.ThreadTimeline.heat.guidance")} ${formatGuidedBand(o)}, ${revText}, ${t("ui.ThreadTimeline.heat.actual")} ${actual}`;
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
                    <tr>
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
                    <tr>
                      <th className="lane" scope="row">
                        {t("ui.ThreadTimeline.heat.revisions")}
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
                                {rev.steps.map((step, i) => (
                                  <i key={`${o.period}-dot-${i}`} className={`heat-dot ${step}`} />
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
                    <tr>
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
                  </tbody>
                </table>
              </div>
              <TrendChart
                points={points}
                label={t("ui.ThreadTimeline.trendLabel", { metric: name })}
              />
              <p className="muted thread-trend-key">{t("ui.ThreadTimeline.trendKey")}</p>
              <div className="thread-cites">
                <p className="muted thread-sources-title">{t("ui.ThreadTimeline.sources")}</p>
                {columns.map((o) => {
                  const promise = o.guidance_quote || o.guided_text;
                  return (
                    <div key={`${o.period}-cites`}>
                      {promise ? (
                        <blockquote className="thread-quote" data-testid="thread-promise">
                          {o.guidance_source_url ? (
                            <a href={o.guidance_source_url} target="_blank" rel="noopener noreferrer">
                              {o.guidance_as_of ? formatDossierDate(o.guidance_as_of) : o.period}
                            </a>
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
                            <a href={rev.source_url} target="_blank" rel="noopener noreferrer">
                              {formatDossierDate(rev.as_of)}
                            </a>
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
                            <a href={o.source_url} target="_blank" rel="noopener noreferrer">
                              {o.as_of ? formatDossierDate(o.as_of) : o.period}
                            </a>
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
        })}
      </div>
    </div>
  );
}
