import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";
import { fetchMarkets, fetchProductsCatalog, type CoverageUnit, type PortfolioProduct } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";
import { DESK_GUIDES } from "../lib/deskPaths";
import { CONTACT_EMAIL } from "../lib/legal";

const SHOT = "/screenshots/tiers";
/** Bump when recapturing: /screenshots is cached 30 days under unchanged file names. */
const SHOT_VERSION = "2026-10-25";
const shotSrc = (src: string) => `${src}?v=${SHOT_VERSION}`;

type Feature = {
  id: string;
  title: string;
  body: string;
  images: { src: string; alt: string }[];
  rows?: { label: string; status: string }[];
};

const TF = "ui.TierFeaturesPage";

/** Live surfaces only; synthetic-input analytics (price overlays, lead-lag, impact map) stay off public pages. */
const FEATURE_GROUPS: { id: string; title: string; intro: string; features: Feature[] }[] = [
  {
    id: "features-foundation",
    title: `${TF}.tier1.title`,
    intro: `${TF}.tier1.intro`,
    features: [
      {
        id: "ask-1",
        title: `${TF}.ask-1.title`,
        body: `${TF}.ask-1.body`,
        images: [{ src: `${SHOT}/01-entity-search.png`, alt: `${TF}.ask-1.img0` }],
        rows: [0, 1, 2].map((i) => ({ label: `${TF}.ask-1.row${i}`, status: `${TF}.status.live` })),
      },
      {
        id: "ask-4-5",
        title: `${TF}.ask-4-5.title`,
        body: `${TF}.ask-4-5.body`,
        images: [
          { src: `${SHOT}/05-auto-ingest-crawl.png`, alt: `${TF}.ask-4-5.img0` },
          { src: `${SHOT}/05b-corpus-foundation.png`, alt: `${TF}.ask-4-5.img1` },
          { src: `${SHOT}/04-period-documents.png`, alt: `${TF}.ask-4-5.img2` },
        ],
        rows: [
          { label: `${TF}.ask-4-5.row0`, status: `${TF}.status.live` },
          { label: `${TF}.ask-4-5.row1`, status: `${TF}.status.live_sensex_hl` },
          { label: `${TF}.ask-4-5.row2`, status: `${TF}.status.live` },
          { label: `${TF}.ask-4-5.row3`, status: `${TF}.status.exception_only` },
        ],
      },
      {
        id: "ask-6",
        title: `${TF}.ask-6.title`,
        body: `${TF}.ask-6.body`,
        images: [{ src: `${SHOT}/06-citability-evidence.png`, alt: `${TF}.ask-6.img0` }],
        rows: [
          { label: `${TF}.ask-6.row0`, status: `${TF}.status.live_on_hand_labeled` },
          { label: `${TF}.ask-6.row1`, status: `${TF}.status.live` },
          { label: `${TF}.ask-6.row2`, status: `${TF}.status.live` },
        ],
      },
    ],
  },
  {
    id: "features-workflow",
    title: `${TF}.tier2.title`,
    intro: `${TF}.tier2.intro`,
    features: [
      {
        id: "ask-10",
        title: `${TF}.ask-10.title`,
        body: `${TF}.ask-10.body`,
        images: [{ src: `${SHOT}/10-private-notes.png`, alt: `${TF}.ask-10.img0` }],
      },
      {
        id: "ask-11",
        title: `${TF}.ask-11.title`,
        body: `${TF}.ask-11.body`,
        images: [
          { src: `${SHOT}/11-report-templates-desk.png`, alt: `${TF}.ask-11.img0` },
          { src: `${SHOT}/11-report-templates-dossier.png`, alt: `${TF}.ask-11.img1` },
        ],
      },
    ],
  },
];

const SURFACES = [
  { id: "screener", to: "/tracker", link: "products.openTracker" },
  { id: "analyst", to: "/analyst", link: "products.openAnalyst" },
  { id: "search", to: "/research", link: "products.openResearch" },
  { id: "sights", to: "/sights", link: "products.openSights" },
  { id: "workbench", to: "/desk", link: "nav.desk" },
  { id: "api", to: "/developers", link: "products.openDevelopers" },
] as const;

const PLAN_IDS = ["pilot", "desk", "enterprise"] as const;

const SKU_LINKS: Record<string, string> = {
  score: "/tracker",
  cite: "/research",
  sights: "/sights",
  radar: "/tracker",
  ledger: "/tracker",
  data: "/developers",
};

function FeatureBlock({ feature }: { feature: Feature }) {
  const { t } = useI18n();
  return (
    <article className="tier-feature" id={feature.id} data-testid={`tier-feature-${feature.id}`}>
      <header className="tier-feature-head">
        <h3>{t(feature.title)}</h3>
      </header>
      <p className="muted">{t(feature.body)}</p>
      <div className={`tier-shots ${feature.images.length > 1 ? "multi" : ""}`}>
        {feature.images.map((img) => (
          <figure key={img.src} className="tier-shot">
            <a href={shotSrc(img.src)} target="_blank" rel="noreferrer">
              <img src={shotSrc(img.src)} alt={t(img.alt)} loading="lazy" />
            </a>
            <figcaption>{t(img.alt)}</figcaption>
          </figure>
        ))}
      </div>
      {feature.rows && (
        <table className="table tier-status-table">
          <thead>
            <tr>
              <th>{t(`${TF}.th.whatYouSee`)}</th>
              <th>{t(`${TF}.th.status`)}</th>
            </tr>
          </thead>
          <tbody>
            {feature.rows.map((r) => (
              <tr key={r.label}>
                <td>{t(r.label)}</td>
                <td>{t(r.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

/** Products and plans: surfaces, buyer plans, desk pathways, live feature status, SKU names. */
export default function ProductsPage() {
  const { t } = useI18n();
  const location = useLocation();
  const { token, user } = useAuth();
  const signedIn = Boolean(token && user?.kind !== "guest");
  const [products, setProducts] = useState<PortfolioProduct[]>([]);
  const [units, setUnits] = useState<CoverageUnit[]>([]);
  const { entitlements } = useEntitlements();

  useEffect(() => {
    let cancelled = false;
    fetchProductsCatalog()
      .then((catalog) => {
        if (!cancelled) setProducts(catalog.products);
      })
      .catch(() => undefined);
    fetchMarkets()
      .then((m) => {
        if (!cancelled) setUnits(m.coverage_units || []);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const id = location.hash.replace(/^#/, "");
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash, products.length]);

  return (
    <div className="page products-page" data-testid="products-page">
      <header className="page-header">
        <p className="kicker">{t("products.kicker")}</p>
        <h1>{t("products.title")}</h1>
        <p className="lede">{t("products.lede")}</p>
      </header>

      <nav className="about-toc" aria-label={t(`${TF}.tocAria`)}>
        <a href="#surfaces">{t("products.toc.surfaces")}</a>
        <a href="#plans">{t("products.toc.plans")}</a>
        <a href="#coverage">{t("products.coverage.title")}</a>
        <a href="#by-desk">{t("products.toc.desk")}</a>
        <a href="#features">{t("products.toc.features")}</a>
        <a href="#names">{t("products.toc.names")}</a>
      </nav>

      <section id="surfaces" className="products-section" data-testid="what-you-get">
        <h2>{t("products.whatYouGet")}</h2>
        <div className="desk-guide-grid">
          {SURFACES.map((s) => (
            <article key={s.id} className="desk-guide" data-testid={`surface-${s.id}`}>
              <h3>{t(`products.get.${s.id}.title`)}</h3>
              <p>{t(`products.get.${s.id}.text`)}</p>
              <p>
                <Link to={s.to}>{t(s.link)}</Link>
              </p>
            </article>
          ))}
        </div>
      </section>

      <section id="plans" className="products-section" data-testid="plans-section">
        <h2>{t("package.plans.title")}</h2>
        <p className="muted">{t("package.plans.lede")}</p>
        <article className="panel" data-testid="evaluation-scope">
          <h3 style={{ marginTop: 0 }}>{t("products.evaluation.title")}</h3>
          <ul className="about-list">
            <li>{t("products.evaluation.i1")}</li>
            <li>{t("products.evaluation.i2")}</li>
            <li>{t("products.evaluation.i3")}</li>
            <li>{t("products.evaluation.i4")}</li>
          </ul>
          <p className="muted">{t("products.evaluation.price")}</p>
        </article>
        <aside className="disclaimer" role="note" data-testid="retail-marketing-gate">
          {t("package.retailGate")}
        </aside>
        <div className="plan-grid">
          {PLAN_IDS.map((id) => (
            <div key={id} className="plan" data-testid={`plan-${id}`}>
              <div className="plan-name">{t(`package.plan.${id}.name`)}</div>
              <div className="plan-price">{t(`package.plan.${id}.price`)}</div>
              <div className="plan-period muted">{t(`package.plan.${id}.period`)}</div>
              <p className="plan-best">{t(`package.plan.${id}.best`)}</p>
              <ul>
                {[1, 2, 3, 4].map((i) => (
                  <li key={i}>{t(`package.plan.${id}.i${i}`)}</li>
                ))}
              </ul>
              <p style={{ marginTop: 16 }}>
                <Link className="btn" to="/pilot" data-testid={`quote-${id}`}>
                  {t("package.quoteCta")}
                </Link>
              </p>
            </div>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 16 }} data-testid="package-independence">
          {t("landing.trust.item4")}
        </p>
        <p className="cta-line">
          {t("package.buy.contact")} <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          {signedIn ? (
            <>
              {" · "}
              <Link to="/billing">{t("package.orderFormLink")}</Link>
            </>
          ) : null}
        </p>
      </section>

      <section id="coverage" className="products-section" data-testid="coverage-section">
        <h2>{t("products.coverage.title")}</h2>
        <p className="muted">{t("products.coverage.lede")}</p>
        <ul className="about-list">
          {units.map((u) => (
            <li key={u.id} data-testid={`coverage-unit-${u.id}`}>
              {u.exchanges.length > 1
                ? t("products.coverage.byExchange", {
                    market: u.label,
                    exchanges: u.exchanges.map((x) => x.exchange).join(" or "),
                  })
                : t("products.coverage.whole", { market: u.label })}
            </li>
          ))}
          <li>{t("products.coverage.all")}</li>
        </ul>
        <p className="muted">{t("products.coverage.price")}</p>
        {signedIn && entitlements.coverage ? (
          <p data-testid="coverage-yours">
            {t("scope.yourPlan")}: <strong>{entitlements.coverage.label}</strong>
          </p>
        ) : null}
      </section>

      <section
        id="by-desk"
        className="products-section desk-guides"
        data-testid="by-desk-section"
        aria-label={t("products.byDesk")}
      >
        <h2>{t("products.byDesk")}</h2>
        <p className="muted">{t("products.byDesk.lede")}</p>
        <div className="desk-guide-grid">
          {DESK_GUIDES.map((desk) => (
            <article key={desk.id} id={desk.hash} className="desk-guide" data-testid={`desk-guide-${desk.id}`}>
              <h3>{desk.title}</h3>
              <p>{desk.blurb}</p>
              <p className="muted desk-skus">{t("products.skus", { skus: desk.skus.join(" · ") })}</p>
              <p className="desk-guide-links">
                <Link to={desk.primary.to}>{desk.primary.label}</Link>
                {desk.links.map((l) => (
                  <span key={l.to + l.label}>
                    {" · "}
                    <Link to={l.to}>{l.label}</Link>
                  </span>
                ))}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section id="features" className="products-section" data-testid="features-section">
        <h2>{t("products.features.title")}</h2>
        <p className="muted">{t("products.features.lede")}</p>
        {FEATURE_GROUPS.map((g) => (
          <div className="panel" id={g.id} key={g.id}>
            <h3 style={{ marginTop: 0 }}>{t(g.title)}</h3>
            <p className="muted" style={{ marginTop: 0 }}>
              {t(g.intro)}
            </p>
            <div className="tier-feature-list">
              {g.features.map((f) => (
                <FeatureBlock key={f.id} feature={f} />
              ))}
            </div>
          </div>
        ))}
      </section>

      <section id="names" className="sku-grid" aria-label={t("products.byProduct")}>
        <h2 className="sku-grid-heading">{t("products.skuAppendix")}</h2>
        <p className="muted">{t("products.skuAppendix.lede")}</p>
        {products.map((p) => (
          <article key={p.id} className="sku-card" data-testid={`sku-${p.id}`}>
            <div className="sku-status">{p.status}</div>
            <h2>{p.name}</h2>
            <p>{p.job}</p>
            <p className="muted">{t("products.buyer", { buyer: p.buyer })}</p>
            <Link to={SKU_LINKS[p.id] ?? "#plans"}>{t("products.open")}</Link>
          </article>
        ))}
      </section>

      <Disclaimer />
    </div>
  );
}
