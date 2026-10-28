import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import type { ProductMeta } from "../lib/api";
import PublishedCountLine from "./PublishedCountLine";

/** Live coverage counts, stated at the precision a research head will check. */
export default function LandingProofPanel({ meta }: { meta: ProductMeta | null }) {
  const { t } = useI18n();

  return (
    <div className="panel landing-proof" data-testid="landing-proof">
      <h2 style={{ marginTop: 0 }}>{t("landing.coverage.title")}</h2>
      <p className="muted">{t("landing.coverage.lede")}</p>
      {meta ? (
        <ul className="about-list landing-proof-stats">
          {meta.sensex_scored_count != null && meta.sensex_count ? (
            <li data-testid="coverage-sensex">
              <strong>
                {t("landing.coverage.sensex", {
                  count: meta.sensex_scored_count,
                  total: meta.sensex_count,
                })}
              </strong>
            </li>
          ) : null}
          <li data-testid="coverage-hand-labeled">
            <PublishedCountLine meta={meta} />
          </li>
          <li data-testid="coverage-demo">
            {t("landing.coverage.demo", { count: meta.demo_structured_count })}
          </li>
          <li data-testid="coverage-listings">
            {t("landing.coverage.listings", {
              count: meta.gci_listing_unscored_count ?? meta.gci_listing_scored_count,
            })}
          </li>
          <li data-testid="coverage-commitments">{t("landing.coverage.next")}</li>
          <li data-testid="coverage-pit">{t("landing.coverage.pit")}</li>
        </ul>
      ) : (
        <p className="muted">{t("landing.coverage.loading")}</p>
      )}
      <p className="muted landing-proof-links">
        <Link to="/blog/hand-labeled-vs-demo-data">{t("landing.coverage.badgesLink")}</Link>
        {" · "}
        <Link to="/trust">{t("footer.trust")}</Link>
      </p>
    </div>
  );
}
