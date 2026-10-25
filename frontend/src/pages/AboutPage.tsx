import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import InfoTip from "../components/InfoTip";
import { useI18n } from "../i18n";
import { CONTACT_EMAIL, LEGAL_ENTITY, copyrightLine } from "../lib/legal";
const PIPELINE = [
  { step: "1", tip: "source", titleKey: "about.pipeline.1.title", textKey: "about.pipeline.1.text" },
  { step: "2", tip: "extract", titleKey: "about.pipeline.2.title", textKey: "about.pipeline.2.text" },
  { step: "3", tip: "gci", titleKey: "about.pipeline.3.title", textKey: "about.pipeline.3.text" },
  { step: "4", tip: "evidence", titleKey: "about.pipeline.4.title", textKey: "about.pipeline.4.text" },
] as const;

const PERSONAS = [
  {
    whoKey: "about.persona.buy.who",
    needKey: "about.persona.buy.need",
    pathKey: "about.persona.buy.path",
  },
  {
    whoKey: "about.persona.sell.who",
    needKey: "about.persona.sell.need",
    pathKey: "about.persona.sell.path",
  },
  {
    whoKey: "about.persona.quant.who",
    needKey: "about.persona.quant.need",
    pathKey: "about.persona.quant.path",
  },
  {
    whoKey: "about.persona.ir.who",
    needKey: "about.persona.ir.need",
    pathKey: "about.persona.ir.path",
  },
] as const;

const ALSO = [
  { to: "/products", titleKey: "about.also.products.title", textKey: "about.also.products.text" },
  { to: "/sights", titleKey: "about.also.sights.title", textKey: "about.also.sights.text" },
  { to: "/rankings", titleKey: "about.also.rankings.title", textKey: "about.also.rankings.text" },
  { to: "/trust", titleKey: "about.also.trust.title", textKey: "about.also.trust.text" },
] as const;

const HOW_TO = [
  { to: "/tracker", titleKey: "about.howto.screen.title", textKey: "about.howto.screen.text" },
  { to: "/companies/infy", titleKey: "about.howto.dossier.title", textKey: "about.howto.dossier.text" },
  { to: "/desk", titleKey: "about.howto.desk.title", textKey: "about.howto.desk.text" },
  { to: "/research", titleKey: "about.howto.research.title", textKey: "about.howto.research.text" },
  { to: "/sights", titleKey: "about.howto.sights.title", textKey: "about.howto.sights.text" },
] as const;

export default function AboutPage() {
  const { t } = useI18n();
  const location = useLocation();

  useEffect(() => {
    const id = location.hash.replace(/^#/, "");
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  return (
    <section className="about-page" data-testid="about-page">
      <p className="page-kicker">{t("about.kicker")}</p>
      <h1>
        {t("about.title")} <InfoTip termId="gci" />
      </h1>
      <p className="muted lede">{t("about.lede")}</p>
      <div className="panel" id="company" data-testid="about-company">
        <h2 style={{ marginTop: 0 }}>{t("about.company.title")}</h2>
        <p>{t("about.company.body", { entity: LEGAL_ENTITY })}</p>
        <p className="muted">
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          {" · "}
          <Link to="/trust#security">{t("about.company.security")}</Link>
          {" · "}
          <Link to="/workflows">{t("nav.workflows")}</Link>
        </p>
      </div>
      <p className="muted" data-testid="about-owner">
        {copyrightLine()} {t("about.contactBefore")}{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. {t("about.contactAfter")}{" "}
        <Link to="/terms">{t("footer.terms")}</Link>
        {" · "}
        <Link to="/privacy">{t("footer.privacy")}</Link>.
      </p>

      <nav className="about-toc" aria-label={t("about.tocLabel")}>
        <a href="#what">{t("about.toc.what")}</a>
        <a href="#why">{t("about.toc.why")}</a>
        <a href="#how">{t("about.toc.how")}</a>
        <a href="#layers">{t("about.toc.layers")}</a>
        <Link to="/products#features">{t("about.toc.tiers")}</Link>
        <a href="#who">{t("about.toc.who")}</a>
        <a href="#also">{t("about.toc.also")}</a>
      </nav>

      <div className="panel" id="what">
        <h2 style={{ marginTop: 0 }}>
          {t("about.what.title")} <InfoTip termId="gci" />
        </h2>
        <p>{t("about.what.p1")}</p>
        <ul className="about-list">
          <li>{t("about.what.li1")}</li>
          <li>{t("about.what.li2")}</li>
          <li>{t("about.what.li3")}</li>
        </ul>
        <Disclaimer compact />
      </div>

      <div className="panel" id="why">
        <h2 style={{ marginTop: 0 }}>{t("about.why.title")}</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("about.why.lede")}
        </p>
        <div className="about-why-grid">
          <div>
            <h3>{t("about.why.drift.title")}</h3>
            <p className="muted">{t("about.why.drift.text")}</p>
          </div>
          <div>
            <h3>{t("about.why.india.title")}</h3>
            <p className="muted">{t("about.why.india.text")}</p>
          </div>
          <div>
            <h3>{t("about.why.compliance.title")}</h3>
            <p className="muted">{t("about.why.compliance.text")}</p>
          </div>
          <div>
            <h3>{t("about.why.hitl.title")}</h3>
            <p className="muted">{t("about.why.hitl.text")}</p>
          </div>
        </div>
      </div>

      <div className="panel" id="how">
        <h2 style={{ marginTop: 0 }}>{t("about.how.title")}</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("about.how.lede")}
        </p>
        <ol className="about-pipeline">
          {PIPELINE.map((p) => (
            <li key={p.step}>
              <span className="about-step">{p.step}</span>
              <div>
                <strong>
                  {t(p.titleKey)} <InfoTip termId={p.tip} />
                </strong>
                <p className="muted">{t(p.textKey)}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="muted" style={{ fontSize: 13 }}>
          {t("about.how.note")}
        </p>
      </div>

      <div className="panel" id="layers">
        <h2 style={{ marginTop: 0 }}>
          {t("about.layers.title")} <InfoTip termId="tier1" />
        </h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("about.layers.lede")}{" "}
          <Link to="/products#plans">{t("footer.package")}</Link>
          {" · "}
          <Link to="/products#features">{t("about.toc.tiers")}</Link>.
        </p>
        <div className="about-why-grid">
          <div>
            <h3>{t("about.layers.foundation.title")}</h3>
            <p className="muted">{t("about.layers.foundation.text")}</p>
          </div>
          <div>
            <h3>{t("about.layers.workflow.title")}</h3>
            <p className="muted">{t("about.layers.workflow.text")}</p>
          </div>
          <div>
            <h3>{t("about.layers.analytics.title")}</h3>
            <p className="muted">{t("about.layers.analytics.text")}</p>
          </div>
          <div>
            <h3>{t("about.layers.oos.title")}</h3>
            <p className="muted">{t("about.layers.oos.text")}</p>
          </div>
        </div>
      </div>

      <div className="panel" id="who">
        <h2 style={{ marginTop: 0 }}>{t("about.who.title")}</h2>
        <div className="about-persona-grid">
          {PERSONAS.map((p) => (
            <article key={p.whoKey} className="about-persona">
              <h3>{t(p.whoKey)}</h3>
              <p>{t(p.needKey)}</p>
              <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>
                {t(p.pathKey)}
              </p>
            </article>
          ))}
        </div>

        <h3 style={{ marginTop: 28 }} id="also">
          {t("about.also.title")}
        </h3>
        <div className="help-quick">
          {ALSO.map((item) => (
            <Link key={item.to} to={item.to} className="help-quick-card">
              <strong>{t(item.titleKey)}</strong>
              <span className="muted">{t(item.textKey)}</span>
            </Link>
          ))}
        </div>

        <h3 style={{ marginTop: 28 }}>{t("about.howto.title")}</h3>
        <div className="help-quick">
          {HOW_TO.map((item) => (
            <Link key={item.titleKey} to={item.to} className="help-quick-card">
              <strong>{t(item.titleKey)}</strong>
              <span className="muted">{t(item.textKey)}</span>
            </Link>
          ))}
        </div>

        <div className="about-cta-row">
          <Link to="/tracker" className="btn">
            {t("about.cta.tracker")}
          </Link>
          <Link to="/products" className="btn ghost">
            {t("about.cta.products")}
          </Link>
          <Link to="/help" className="btn ghost">
            {t("about.cta.help")}
          </Link>
        </div>
      </div>

      <Disclaimer />
    </section>
  );
}
