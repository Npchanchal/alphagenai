import InfoTip from "./InfoTip";
import { useI18n } from "../i18n";
import type { GuidanceRevision, OutcomeView } from "../lib/api";
import { formatOutcomeLabel, tipForLabel } from "../lib/glossary";
import { metricDisplayName } from "../lib/score";

type Props = {
  threads: Record<string, OutcomeView[]>;
  testId?: string;
};

function midpoint(o: OutcomeView): number {
  if (o.guided_low != null && o.guided_high != null) {
    return (o.guided_low + o.guided_high) / 2;
  }
  return o.guided_value;
}

function bandText(o: OutcomeView): string {
  if (o.guided_low != null && o.guided_high != null) {
    return `${o.guided_low}–${o.guided_high}`;
  }
  return String(o.guided_value);
}

type Direction = "stated" | "raised" | "lowered" | "reiterated";

const DIRECTION_KEY: Record<Direction, string> = {
  stated: "ui.ThreadTimeline.dir.stated",
  raised: "ui.ThreadTimeline.dir.raised",
  lowered: "ui.ThreadTimeline.dir.lowered",
  reiterated: "ui.ThreadTimeline.dir.reiterated",
};

function revisionBand(rev: GuidanceRevision): string {
  return `${rev.guided_low}–${rev.guided_high}`;
}

function direction(prev: OutcomeView | null, cur: OutcomeView): Direction {
  if (!prev) return "stated";
  const a = midpoint(prev);
  const b = midpoint(cur);
  if (b > a) return "raised";
  if (b < a) return "lowered";
  return "reiterated";
}

/**
 * Promise Threads — restatement history of the same guidance commitment.
 * Shows how a promise was first stated, then raised / lowered / reiterated,
 * and how it finally resolved (met / missed / exceeded / dropped / pending).
 */
export default function ThreadTimeline({ threads, testId = "thread-timeline" }: Props) {
  const { t } = useI18n();
  const entries = Object.entries(threads)
    .map(([id, rows]) => {
      const sorted = [...rows].sort((a, b) => {
        const ka = a.as_of ?? a.period;
        const kb = b.as_of ?? b.period;
        return ka < kb ? -1 : ka > kb ? 1 : 0;
      });
      return { id, rows: sorted };
    })
    .sort((a, b) => b.rows.length - a.rows.length);

  if (entries.length === 0) {
    return <p className="muted">{t("ui.ThreadTimeline.empty")}</p>;
  }

  return (
    <div className="thread-list" data-testid={testId}>
      {entries.map(({ id, rows }) => {
        const last = rows[rows.length - 1];
        return (
          <div className="thread-row" key={id} data-testid={`thread-${id}`}>
            <div className="thread-head">
              <span className="thread-metric">{metricDisplayName(last.metric)}</span>
              <span className={`pill ${last.label}`}>
                {formatOutcomeLabel(last.label)}
              </span>{" "}
              <InfoTip termId={last.label.toLowerCase()} text={tipForLabel(last.label)} />
            </div>
            <div className="thread-timeline">
              {rows.map((o, i) => {
                const dir = direction(i > 0 ? rows[i - 1] : null, o);
                return (
                  <div className="thread-node-wrap" key={`${o.period}-${i}`}>
                    {i > 0 && <span className="thread-arrow" aria-hidden="true">→</span>}
                    <div className={`thread-node ${dir}`}>
                      <div className="thread-node-period">
                        {o.guidance_as_of ? o.guidance_as_of.slice(0, 7) : o.period}
                      </div>
                      <div className="thread-node-band">{bandText(o)}</div>
                      <span className={`thread-dir ${dir}`}>{t(DIRECTION_KEY[dir])}</span>
                    </div>
                  </div>
                );
              })}
              <div className="thread-node-wrap">
                <span className="thread-arrow" aria-hidden="true">→</span>
                <div className="thread-node outcome">
                  <div className="thread-node-period">{last.period}</div>
                  <div className="thread-node-band">
                    {last.actual_value != null
                      ? t("ui.ThreadTimeline.actual", { value: last.actual_value })
                      : t("ui.ThreadTimeline.periodOpen")}
                  </div>
                  <span className={`pill ${last.label}`}>{formatOutcomeLabel(last.label)}</span>
                </div>
              </div>
            </div>
            {rows.map((o) => {
              const promise = o.guidance_quote || o.guided_text;
              return (
                <div key={`${o.period}-cites`} className="thread-cites">
                  {promise ? (
                    <blockquote className="thread-quote" data-testid="thread-promise">
                      {o.guidance_source_url ? (
                        <a href={o.guidance_source_url} target="_blank" rel="noopener noreferrer">
                          {o.guidance_as_of || o.period}
                        </a>
                      ) : (
                        <span>{o.guidance_as_of || o.period}</span>
                      )}
                      {" · "}“{promise}”
                    </blockquote>
                  ) : null}
                  {(o.revisions || []).map((rev, i) => (
                    <p key={`${o.period}-rev-${i}`} className="muted thread-quote" data-testid="thread-revision">
                      {rev.source_url ? (
                        <a href={rev.source_url} target="_blank" rel="noopener noreferrer">
                          {rev.as_of}
                        </a>
                      ) : (
                        rev.as_of
                      )}
                      {" · "}
                      {t("ui.ThreadTimeline.revision", { band: revisionBand(rev) })}
                      {rev.quote ? ` · “${rev.quote}”` : ""}
                    </p>
                  ))}
                  {o.actual_value != null && o.quote_span ? (
                    <blockquote className="thread-quote" data-testid="thread-actual">
                      {o.source_url ? (
                        <a href={o.source_url} target="_blank" rel="noopener noreferrer">
                          {o.as_of || o.period}
                        </a>
                      ) : (
                        <span>{o.as_of || o.period}</span>
                      )}
                      {" · "}“{o.quote_span}”
                    </blockquote>
                  ) : (
                    <p className="muted thread-quote" data-testid="thread-open">
                      {t("ui.ThreadTimeline.periodOpen")}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
