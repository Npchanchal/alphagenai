import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import Skeleton from "../components/Skeleton";
import { useI18n } from "../i18n";
import { fetchTrustCenter, type TrustCenterPayload } from "../lib/api";
import { CONTACT_EMAIL, copyrightLine, LEGAL_ENTITY, PRODUCT_NAME } from "../lib/legal";
import { metricDisplayName } from "../lib/score";

/** Procurement / security Trust Center — honest status, not marketing. */
export default function TrustPage() {
  const { t } = useI18n();
  const location = useLocation();
  const [data, setData] = useState<TrustCenterPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await fetchTrustCenter();
        if (!cancelled) setData(next);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("trust.loadError"));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    const id = location.hash.replace(/^#/, "");
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash, data]);

  return (
    <section className="trust-page" data-testid="trust-page">
      <p className="page-kicker">{t("trust.kicker")}</p>
      <h1>{t("trust.title", { product: PRODUCT_NAME })}</h1>
      <p className="muted lede">
        {t("trust.lede", { product: PRODUCT_NAME, entity: LEGAL_ENTITY })}
      </p>

      {error && <p className="error">{error}</p>}
      {!data && !error && <Skeleton rows={8} label={t("trust.loading")} />}

      {data && (
        <div className="trust-grid">
          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("trust.productEntity")}</h2>
            <ul className="about-list">
              <li>
                {t("ui.TrustPage.product")} <strong>{data.product}</strong>
              </li>
              <li>{t("ui.TrustPage.legalEntity", { value: data.legal_entity })}</li>
              <li>
                {t("ui.TrustPage.domain")}{" "}
                <a href={`https://${data.domain}`} rel="noreferrer" target="_blank">
                  {data.domain}
                </a>
              </li>
              <li>{data.data.gci}</li>
              <li>{t("ui.TrustPage.beachhead", { value: data.data.beachhead })}</li>
              <li>
                {t("ui.TrustPage.inventedActuals")}{" "}
                {data.data.invent_actuals
                  ? t("ui.TrustPage.inventedYes")
                  : t("ui.TrustPage.inventedNever")}
              </li>
              {data.data.quality_badges ? <li>{data.data.quality_badges}</li> : null}
            </ul>
          </article>

          <article className="panel" data-testid="trust-independence">
            <h2 style={{ marginTop: 0 }}>{t("landing.trust.independence.title")}</h2>
            <p>{t("landing.trust.item4")}</p>
            <p className="muted">
              {t("ui.TrustPage.independence", { product: PRODUCT_NAME })}
            </p>
          </article>

          <article className="panel" data-testid="trust-link-out">
            <h2 style={{ marginTop: 0 }}>{t("trust.linkOut.title")}</h2>
            <p>{data.compliance.link_out_policy || t("trust.linkOut.body")}</p>
            <p className="muted">{t("trust.refund.body")}</p>
          </article>

          <article className="panel" data-testid="trust-legal">
            <h2 style={{ marginTop: 0 }}>{t("trust.counselLegal")}</h2>
            <ul className="about-list">
              <li>
                {t("ui.TrustPage.versions", {
                  terms: data.compliance.terms_version ?? "—",
                  privacy: data.compliance.privacy_version ?? "—",
                })}
              </li>
              <li>
                {t("ui.TrustPage.contactLabel")}{" "}
                <a href={`mailto:${data.compliance.contact_email || CONTACT_EMAIL}`}>
                  {data.compliance.contact_email || CONTACT_EMAIL}
                </a>
              </li>
              {data.compliance.privacy_email ? (
                <li>
                  {t("trust.privacyEmail")}{" "}
                  <a href={`mailto:${data.compliance.privacy_email}`}>
                    {data.compliance.privacy_email}
                  </a>
                </li>
              ) : null}
            </ul>
            <p>
              <Link to="/terms">{t("footer.terms")}</Link>
              {" · "}
              <Link to="/privacy">{t("footer.privacy")}</Link>
              {" · "}
              <Link to="/help">{t("footer.help")}</Link>
              {" · "}
              <Link to="/about">{t("footer.about")}</Link>
            </p>
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.residency")}</h2>
            {data.residency ? (
              <ul className="about-list">
                <li>
                  {t("ui.TrustPage.region")} <code>{data.residency.region}</code> ({data.residency.provider})
                </li>
              </ul>
            ) : (
              <p className="muted">{t("ui.TrustPage.residencyUnavailable")}</p>
            )}
            <p className="muted">{data.residency?.note}</p>
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.tenancy")}</h2>
            {data.tenancy ? (
              <ul className="about-list">
                <li>{data.tenancy.model}</li>
                <li>{t("ui.TrustPage.auth", { value: data.tenancy.auth })}</li>
              </ul>
            ) : (
              <p className="muted">{t("ui.TrustPage.tenancyFallback")}</p>
            )}
          </article>

          <article className="panel" id="security" data-testid="trust-security">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.security")}</h2>
            <ul className="about-list">
              <li>{t("ui.TrustPage.forceHttps", { value: data.security.force_https ? t("ui.TrustPage.on") : t("ui.TrustPage.offEnv") })}</li>
              <li>{t("ui.TrustPage.hsts", { value: data.security.hsts ? t("ui.TrustPage.on") : t("ui.TrustPage.offEnv") })}</li>
              <li>{t("ui.TrustPage.authModes", { value: data.security.auth_modes.join(", ") })}</li>
            </ul>
            <p className="muted" style={{ fontSize: 13 }}>
              {t("ui.TrustPage.headers", { value: data.security.headers.join("; ") })}
            </p>
            {data.security.csp ? (
              <p className="muted" style={{ fontSize: 13 }}>
                {data.security.csp}
              </p>
            ) : null}
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.sso")}</h2>
            <ul className="about-list">
              <li>{t("ui.TrustPage.ssoEnabled", { value: data.sso.enabled ? t("ui.TrustPage.yes") : t("ui.TrustPage.no") })}</li>
              <li>{t("ui.TrustPage.oidcConfigured", { value: data.sso.configured ? t("ui.TrustPage.yes") : t("ui.TrustPage.no") })}</li>
            </ul>
            <p className="muted">{data.sso.note}</p>
          </article>

          <article className="panel" data-testid="trust-llm">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.llm")}</h2>
            <ul className="about-list">
              <li>
                {t("ui.TrustPage.modelConfigured", {
                  value: data.llm?.configured ? t("ui.TrustPage.yes") : t("ui.TrustPage.noHeuristic"),
                })}
              </li>
            </ul>
            <p className="muted" style={{ fontSize: 13 }}>
              {data.llm?.note ??
                t("ui.TrustPage.llmNote")}
            </p>
          </article>

          <article className="panel" data-testid="trust-labeling">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.labeling")}</h2>
            {data.labeling_governance ? (
              <>
                <p data-testid="trust-review-process">{t("method.page.review.i4")}</p>
                <ul className="about-list">
                  <li>{t("ui.TrustPage.filingCheck")}</li>
                  <li>
                    {t("ui.TrustPage.counts", {
                      drafts: data.labeling_governance.drafts ?? 0,
                      submitted: data.labeling_governance.submitted ?? 0,
                      accepted: data.labeling_governance.accepted ?? 0,
                    })}
                  </li>
                </ul>
                {data.labeling_governance.recent && data.labeling_governance.recent.length > 0 ? (
                  <ul className="about-list">
                    {data.labeling_governance.recent.slice(0, 8).map((row) => (
                      <li key={row.id || `${row.company_id}-${row.updated_at}`}>
                        {row.company_id} {row.period} {row.metric ? metricDisplayName(row.metric) : ""} — {row.status}
                        {row.submitter_id ? ` · ${t("ui.TrustPage.submitter", { id: row.submitter_id })}` : ""}
                        {row.reviewer_id ? ` · ${t("ui.TrustPage.reviewer", { id: row.reviewer_id })}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="muted">{t("ui.TrustPage.labelingFallback")}</p>
            )}
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.citations")}</h2>
            <p>{data.citations.model}</p>
            <p className="muted">{data.citations.research_chat}</p>
            {data.source_verification ? (
              <ul className="about-list" data-testid="trust-source-verification">
                <li>
                  {(data.source_verification.checked || 0) > 0
                    ? t("ui.TrustPage.sourceLinks", {
                        verified: data.source_verification.verified ?? 0,
                        checked: data.source_verification.checked ?? 0,
                      })
                    : t("ui.TrustPage.sourceLinksPending")}
                  {data.source_verification.as_of
                    ? ` · ${data.source_verification.as_of}`
                    : ""}
                </li>
                {(data.source_verification.failed || 0) > 0 ? (
                  <li>
                    {t("ui.TrustPage.sourceLinksFailed", {
                      failed: data.source_verification.failed ?? 0,
                    })}
                  </li>
                ) : null}
              </ul>
            ) : null}
            {data.filing_to_score ? (
              <ul className="about-list" data-testid="trust-filing-sla">
                <li>
                  {t("ui.TrustPage.filingSla", {
                    days: data.filing_to_score.target_business_days,
                  })}
                </li>
                <li>
                  {data.filing_to_score.live && data.filing_to_score.live.n > 0
                    ? t("ui.TrustPage.filingSlaLive", {
                        median: data.filing_to_score.live.median_business_days ?? "—",
                        n: data.filing_to_score.live.n,
                      })
                    : t("ui.TrustPage.filingSlaLiveEmpty")}
                </li>
                {data.filing_to_score.backfill && data.filing_to_score.backfill.n > 0 ? (
                  <li>
                    {t("ui.TrustPage.filingSlaBackfill", {
                      median: data.filing_to_score.backfill.median_business_days ?? "—",
                      n: data.filing_to_score.backfill.n,
                      reviewedOn: data.filing_to_score.backfill.reviewed_on ?? "2026-09-29",
                    })}
                  </li>
                ) : null}
              </ul>
            ) : null}
            <ul className="about-list">
              {data.citations.endpoints.map((ep) => (
                <li key={ep}>
                  <code>{ep}</code>
                </li>
              ))}
            </ul>
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.compliance")}</h2>
            <p>{data.compliance.posture}</p>
            <p className="muted">{data.compliance.sebi}</p>
            <p>
              <Link to="/products#plans">{t("footer.package")}</Link>
            </p>
          </article>

          <article className="panel" data-testid="trust-subprocessors">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.subprocessors")}</h2>
            {data.subprocessors && data.subprocessors.length > 0 ? (
              <ul className="about-list">
                {data.subprocessors.map((p) => (
                  <li key={p.name}>
                    {p.name} — {p.role}
                    {p.optional ? ` (${t("ui.TrustPage.optional")})` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">{t("ui.TrustPage.subprocessorsFallback")}</p>
            )}
          </article>

          <article className="panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.TrustPage.incident")}</h2>
            <p>
              {t("ui.TrustPage.contact")}{" "}
              <a href={`mailto:${data.incident?.contact || CONTACT_EMAIL}`}>
                {data.incident?.contact || CONTACT_EMAIL}
              </a>
              .
            </p>
            <p className="muted">{data.incident?.note}</p>
          </article>
        </div>
      )}

      <Disclaimer />
      <p className="muted">{copyrightLine()}</p>
    </section>
  );
}
