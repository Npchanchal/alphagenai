import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import {
  fetchCompanyGci,
  fetchRecentFilings,
  type CompanyGCIDetail,
  type OutcomeView,
  type RecentFiling,
} from "../lib/api";
import { metricDisplayName, publicDocTitle } from "../lib/score";
import { EXAMPLE_COMPANY_ID } from "./LandingWorkedExample";

function band(o: OutcomeView): string {
  const low = o.guided_low ?? o.guided_value;
  const high = o.guided_high ?? o.guided_value;
  const unit = o.unit && o.unit !== "%" ? ` ${o.unit}` : "%";
  return low === high ? `${low}${unit}` : `${low}–${high}${unit}`;
}

function actualText(o: OutcomeView): string {
  if (o.actual_value == null) return "—";
  const unit = o.actual_unit && o.actual_unit !== "%" ? ` ${o.actual_unit}` : "%";
  return `${o.actual_value}${unit}`;
}

function pickOutcome(detail: CompanyGCIDetail): OutcomeView | null {
  const rows = detail.outcomes.filter(
    (o) =>
      o.guidance_quote &&
      o.quote_span &&
      o.guidance_source_url &&
      o.source_url &&
      o.actual_value != null &&
      o.label !== "pending" &&
      o.label !== "pending_guidance_cite",
  );
  rows.sort((a, b) => (b.period || "").localeCompare(a.period || ""));
  return rows[0] ?? null;
}

/** A cited question and the newest stored filings, beside the worked score. */
export default function LandingProof() {
  const { t } = useI18n();
  const [detail, setDetail] = useState<CompanyGCIDetail | null>(null);
  const [filings, setFilings] = useState<RecentFiling[] | null>(null);

  useEffect(() => {
    fetchCompanyGci(EXAMPLE_COMPANY_ID)
      .then(setDetail)
      .catch(() => setDetail(null));
    fetchRecentFilings(6)
      .then((res) => setFilings(res.filings))
      .catch(() => setFilings([]));
  }, []);

  const outcome = detail ? pickOutcome(detail) : null;
  const metric = outcome ? metricDisplayName(outcome.metric) : "";

  return (
    <div className="landing-proof" data-testid="landing-proof">
      <article className="panel" data-testid="landing-cited-answer">
        <p className="page-kicker">{t("landing.proof.answerKicker")}</p>
        <h2 style={{ marginTop: 0 }}>{t("landing.proof.answerTitle")}</h2>
        {!detail ? (
          <p className="muted">{t("landing.proof.loading")}</p>
        ) : !outcome ? (
          <p className="muted">{t("landing.proof.answerEmpty")}</p>
        ) : (
          <>
            <p data-testid="landing-cited-question">
              {t("landing.proof.question", {
                name: detail.name,
                metric,
                period: outcome.period,
              })}
            </p>
            <p>
              {t("landing.proof.answer", {
                name: detail.name,
                band: band(outcome),
                actual: actualText(outcome),
                label: outcome.label,
                period: outcome.period,
              })}
            </p>
            <p className="muted">{t("landing.proof.asOf", { date: outcome.as_of || detail.as_of || "—" })}</p>
            <ul className="about-list">
              <li>
                <a href={outcome.guidance_source_url || "#"} rel="noopener noreferrer" target="_blank">
                  {t("landing.proof.promise", { date: outcome.guidance_as_of || "—" })}
                </a>
                {outcome.guidance_quote ? <q>{outcome.guidance_quote}</q> : null}
              </li>
              <li>
                <a href={outcome.source_url || "#"} rel="noopener noreferrer" target="_blank">
                  {t("landing.proof.reported", { date: outcome.as_of || "—" })}
                </a>
                {outcome.quote_span ? <q>{outcome.quote_span}</q> : null}
              </li>
            </ul>
            <p>
              <Link to={`/companies/${detail.id}`}>{t("landing.proof.openDossier", { name: detail.name })}</Link>
            </p>
          </>
        )}
      </article>

      <article className="panel" data-testid="landing-recent-filings">
        <p className="page-kicker">{t("landing.proof.filingsKicker")}</p>
        <h2 style={{ marginTop: 0 }}>{t("landing.proof.filingsTitle")}</h2>
        <p className="muted">{t("landing.proof.filingsLede")}</p>
        {filings == null ? (
          <p className="muted">{t("landing.proof.loading")}</p>
        ) : filings.length === 0 ? (
          <p className="muted">{t("landing.proof.filingsEmpty")}</p>
        ) : (
          <ul className="doc-list">
            {filings.map((row) => (
              <li key={row.doc_id}>
                <div className="doc-meta">
                  <strong>{row.ticker || row.name}</strong>
                  {row.date ? <span className="muted">{row.date}</span> : null}
                  {row.doc_type ? <span className="muted">{row.doc_type}</span> : null}
                </div>
                <div>{publicDocTitle(row.title, row.doc_type)}</div>
                {row.url ? (
                  <a href={row.url} rel="noopener noreferrer" target="_blank">
                    {t("landing.proof.openFiling")}
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        <p>
          <Link to="/research">{t("landing.proof.searchFilings")}</Link>
        </p>
      </article>
    </div>
  );
}
