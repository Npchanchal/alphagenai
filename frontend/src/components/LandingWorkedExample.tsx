import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import { fetchCompanyGci, type CompanyGCIDetail, type OutcomeView } from "../lib/api";
import { compareEvidenceLatestFirst, formatCompanyScore, metricDisplayName, scoreClass } from "../lib/score";
import ScoreCalcPanel from "./ScoreCalcPanel";

export const EXAMPLE_COMPANY_ID = "infy";

const EXAMPLES = [
  { id: "infy", tabKey: "landing.example.tab.infy", whyTitleKey: "landing.example.whyTitle", whyKey: "landing.example.why" },
  {
    id: "apollohosp",
    tabKey: "landing.example.tab.apollo",
    whyTitleKey: "landing.example.apollo.whyTitle",
    whyKey: "landing.example.apollo.why",
  },
] as const;

function fmtBand(low: number, high: number): string {
  return low === high ? `${low}%` : `${low}–${high}%`;
}

function band(o: OutcomeView): string {
  return fmtBand(o.guided_low ?? o.guided_value, o.guided_high ?? o.guided_value);
}

function sourceHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function latestDate(outcomes: OutcomeView[]): string | null {
  const dates = outcomes.map((o) => o.as_of).filter((d): d is string => Boolean(d));
  return dates.length ? dates.sort()[dates.length - 1] : null;
}

function TrailStep({
  kind,
  label,
  date,
  quote,
  url,
}: {
  kind: "guidance" | "actual" | "source";
  label: string;
  date?: string | null;
  quote?: string | null;
  url: string;
}) {
  const { t } = useI18n();
  return (
    <a
      className={`landing-example-step ${kind}`}
      href={url}
      rel="noopener noreferrer"
      target="_blank"
    >
      <span className={`landing-example-chip ${kind}`}>
        {label}
        {date ? ` · ${date}` : ""}
      </span>
      {quote ? <q>{quote}</q> : null}
      <span className="landing-example-host">
        {t("landing.example.source")}: {sourceHost(url)}
      </span>
    </a>
  );
}

function Revisions({ o }: { o: OutcomeView }) {
  const { t } = useI18n();
  const revs = o.revisions ?? [];
  if (!revs.length) return null;
  return (
    <div className="landing-example-revisions" data-testid={`example-revisions-${o.period}`}>
      <span className="muted">
        {t(o.revision_direction === "cut" ? "landing.example.revisedDown" : "landing.example.revisedUp")}:
      </span>{" "}
      {revs.map((r, i) => (
        <span key={r.as_of}>
          {i > 0 ? " → " : null}
          {r.source_url ? (
            <a href={r.source_url} rel="noopener noreferrer" target="_blank" title={r.quote ?? undefined}>
              {fmtBand(r.guided_low, r.guided_high)} ({r.as_of})
            </a>
          ) : (
            `${fmtBand(r.guided_low, r.guided_high)} (${r.as_of})`
          )}
        </span>
      ))}
      {o.final_label ? (
        <>
          {" · "}
          <span className="muted">{t("landing.example.vsFinal")}</span>{" "}
          <span className={`pill ${o.final_label}`} data-testid={`example-final-${o.period}`}>
            {o.final_label}
          </span>{" "}
          <span className="muted">{t("landing.example.notScored")}</span>
        </>
      ) : null}
    </div>
  );
}

/** Real, cited guidance threads — proof before definition. */
export default function LandingWorkedExample() {
  const { t } = useI18n();
  const [active, setActive] = useState<string>(EXAMPLES[0].id);
  const [details, setDetails] = useState<Record<string, CompanyGCIDetail>>({});
  const [failed, setFailed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (details[active] || failed[active]) return;
    fetchCompanyGci(active)
      .then((d) => setDetails((prev) => ({ ...prev, [active]: d })))
      .catch(() => setFailed((prev) => ({ ...prev, [active]: true })));
  }, [active, details, failed]);

  const example = EXAMPLES.find((e) => e.id === active) ?? EXAMPLES[0];
  const detail = details[active];
  const closed = (detail?.outcomes ?? []).filter((o) => o.actual_value != null);
  const metricCounts = closed.reduce<Record<string, number>>((acc, o) => {
    acc[o.metric] = (acc[o.metric] ?? 0) + 1;
    return acc;
  }, {});
  const primaryMetric = Object.entries(metricCounts).sort((a, b) => b[1] - a[1])[0]?.[0];
  const rows = [...closed].sort(compareEvidenceLatestFirst);
  const asOf = detail ? latestDate(detail.outcomes) : null;
  const record = ["exceeded", "met", "missed", "dropped"]
    .map((label) => ({ label, n: closed.filter((o) => o.label === label).length }))
    .filter((r) => r.n > 0);
  const metricName = (m: string) => metricDisplayName(m);
  const rowKey = (o: OutcomeView) =>
    o.metric === primaryMetric ? o.period : `${o.period}-${o.metric}`;

  return (
    <div className="panel landing-example" data-testid="landing-worked-example">
      <p className="landing-kicker">{t("landing.example.kicker")}</p>
      <div className="landing-example-tabs" role="tablist" aria-label={t("landing.example.tabsLabel")}>
        {EXAMPLES.map((e) => (
          <button
            key={e.id}
            type="button"
            role="tab"
            aria-selected={active === e.id}
            className={`landing-example-tab${active === e.id ? " active" : ""}`}
            data-testid={`example-tab-${e.id}`}
            onClick={() => setActive(e.id)}
          >
            {t(e.tabKey)}
          </button>
        ))}
      </div>
      {failed[active] ? (
        <p className="muted">{t("landing.example.error")}</p>
      ) : !detail ? (
        <p className="muted">{t("landing.example.loading")}</p>
      ) : (
        <>
          <div className="landing-example-head">
            <h2>{t("landing.example.title", { name: detail.name })}</h2>
            <div className="landing-example-readouts">
              <span className="landing-example-gci" data-testid="example-company-gci">
                {t("landing.example.companyGci")}{" "}
                <strong className={`score ${scoreClass(detail.gci_score)}`}>
                  {formatCompanyScore(detail.gci_score)}
                </strong>
              </span>
              <span className="landing-example-record" data-testid="example-delivery-record">
                {t("landing.example.record")}{" "}
                {record.map((r, i) => (
                  <span key={r.label}>
                    {i > 0 ? " · " : null}
                    <strong>{r.n}</strong> {r.label}
                  </span>
                ))}
              </span>
            </div>
          </div>
          <p className="muted">{t(`landing.example.lede.${example.id}`)}</p>
          {asOf ? (
            <p className="muted landing-example-asof" data-testid="example-as-of">
              {t("landing.example.asOf", { date: asOf })}
            </p>
          ) : null}
          <ol className="landing-example-rows">
            {rows.map((o) => (
              <li key={`${o.period}-${o.metric}`} className="landing-example-row">
                <span className="landing-example-period">{o.period}</span>
                <span className="landing-example-metric">{metricName(o.metric)}</span>
                <span>
                  <span className="muted">{t("landing.example.guided")}</span> {band(o)}
                </span>
                <span>
                  <span className="muted">{t("landing.example.actual")}</span> {o.actual_value}%
                </span>
                <span className={`pill ${o.label}`} data-testid={`example-label-${rowKey(o)}`}>
                  {o.label}
                </span>
                <span className="muted">
                  {o.contribution_score != null
                    ? t("landing.example.points", { points: o.contribution_score })
                    : "—"}
                </span>
                <Revisions o={o} />
                <div className="landing-example-trail" data-testid={`example-trail-${rowKey(o)}`}>
                  {o.guidance_source_url ? (
                    <TrailStep
                      kind="guidance"
                      label={t("landing.example.trailGuidance")}
                      date={o.guidance_as_of}
                      quote={o.guidance_quote}
                      url={o.guidance_source_url}
                    />
                  ) : null}
                  {o.source_url ? (
                    <TrailStep
                      kind={o.guidance_source_url ? "actual" : "source"}
                      label={t(
                        o.guidance_source_url
                          ? "landing.example.trailActual"
                          : "landing.example.trailSource",
                      )}
                      date={o.as_of}
                      quote={o.quote_span}
                      url={o.source_url}
                    />
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
          <ScoreCalcPanel detail={detail} showMethodLink />
          <div className="landing-example-why">
            <strong>{t(example.whyTitleKey)}</strong> {t(example.whyKey)}{" "}
            <Link to="/methodology">{t("landing.example.methodLink")}</Link>
          </div>
          <p>
            <Link to={`/companies/${detail.id}`}>
              {t("landing.example.open", { name: detail.name })}
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
