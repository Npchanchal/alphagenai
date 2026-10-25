import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import InfoTip from "../components/InfoTip";
import { GLOSSARY, HELP_SECTIONS } from "../lib/glossary";
import { CONTACT_EMAIL } from "../lib/legal";
import { useTour } from "../lib/TourProvider";
import { TOURS, TOUR_GROUPS, type TourId } from "../lib/tours";
import { useI18n } from "../i18n";

function TermSection({
  title,
  ids,
  needle,
}: {
  title: string;
  ids: string[];
  needle: string;
}) {
  const rows = ids
    .map((id) => GLOSSARY[id])
    .filter(Boolean)
    .filter((item) => {
      if (!needle) return true;
      return (
        item.term.toLowerCase().includes(needle) ||
        item.tip.toLowerCase().includes(needle) ||
        item.id.toLowerCase().includes(needle)
      );
    });
  if (rows.length === 0) return null;
  return (
    <div className="help-section">
      <h2>{title}</h2>
      <dl className="glossary">
        {rows.map((item) => (
          <div className="glossary-row" key={item.id}>
            <dt>
              {item.term} <InfoTip termId={item.id} />
            </dt>
            <dd>{item.tip}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const SHOT = "/screenshots/tiers";
const SHOT_VERSION = "2026-10-25";

const QUICK = [
  {
    to: "/tracker",
    titleKey: "help.quick.tracker.title",
    textKey: "help.quick.tracker.text",
    tip: "tracker",
  },
  {
    to: "/companies/infy",
    titleKey: "help.quick.dossier.title",
    textKey: "help.quick.dossier.text",
    tip: "evidence",
  },
  {
    to: "/research",
    titleKey: "help.quick.research.title",
    textKey: "help.quick.research.text",
    tip: "reading_room",
  },
  {
    to: "/rankings",
    titleKey: "help.quick.rankings.title",
    textKey: "help.quick.rankings.text",
    tip: "rankings",
  },
  {
    to: "/workflows",
    titleKey: "help.quick.workflows.title",
    textKey: "help.quick.workflows.text",
    tip: "workflows",
  },
  {
    to: "/analyst",
    titleKey: "help.quick.analyst.title",
    textKey: "help.quick.analyst.text",
    tip: "analyst",
  },
  {
    to: "/desk",
    titleKey: "help.quick.desk.title",
    textKey: "help.quick.desk.text",
    tip: "desk_sku",
  },
  {
    to: "/sights",
    titleKey: "help.quick.sights.title",
    textKey: "help.quick.sights.text",
    tip: "sights",
  },
  {
    to: "/holdings",
    titleKey: "help.quick.holdings.title",
    textKey: "help.quick.holdings.text",
    tip: "holdings",
  },
  {
    to: "/ninja",
    titleKey: "help.quick.ninja.title",
    textKey: "help.quick.ninja.text",
    tip: "financial_ninja",
  },
  {
    to: "/products",
    titleKey: "help.quick.products.title",
    textKey: "help.quick.products.text",
    tip: "score_sku",
  },
  {
    to: "/trust",
    titleKey: "help.quick.trust.title",
    textKey: "help.quick.trust.text",
    tip: "trust_center",
  },
] as const;

const WALKTHROUGH = [
  { src: `${SHOT}/00-tracker-overview.png`, altKey: "help.shot.tracker" },
  { src: `${SHOT}/01-entity-search.png`, altKey: "help.shot.search" },
  { src: `${SHOT}/06-citability-evidence.png`, altKey: "help.shot.evidence" },
  { src: `${SHOT}/12-delivery-record.png`, altKey: "help.shot.record" },
] as const;

export default function HelpPage() {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const { startTour, seen, resetSeen } = useTour();
  const navigate = useNavigate();

  function launch(id: TourId) {
    const tour = TOURS.find((x) => x.id === id);
    if (!tour) return;
    navigate(tour.startRoute);
    window.setTimeout(() => startTour(id), 150);
  }

  return (
    <section className="help-page" data-testid="help-page">
      <p className="page-kicker">{t("help.kicker")}</p>
      <h1>
        {t("help.title")} <InfoTip termId="gci" />
      </h1>
      <p className="muted lede">{t("help.lede")}</p>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>{t("help.startHere")}</h2>
        <div className="help-quick">
          {QUICK.map((item) => (
            <Link key={item.to} to={item.to} className="help-quick-card">
              <strong>
                {t(item.titleKey)} <InfoTip termId={item.tip} />
              </strong>
              <span className="muted">{t(item.textKey)}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="panel" id="product-walkthrough" data-testid="help-walkthrough">
        <h2 style={{ marginTop: 0 }}>{t("help.walkthrough.title")}</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("help.walkthrough.lede")}
        </p>
        <div className="tier-shots multi" data-testid="help-shots">
          {WALKTHROUGH.map((shot) => (
            <figure className="tier-shot" key={shot.src}>
              <img src={`${shot.src}?v=${SHOT_VERSION}`} alt={t(shot.altKey)} />
            </figure>
          ))}
        </div>
        <p>
          <Link to="/products#features">{t("help.walkthrough.link")}</Link>
        </p>
      </div>

      <div className="panel" id="tours" data-testid="tours-hub">
        <h2 style={{ marginTop: 0 }}>{t("help.tours.title")}</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("help.tours.lede")}
        </p>
        {TOUR_GROUPS.map((group) => (
          <div key={group.id}>
            <h3 className="help-tour-group">{group.label}</h3>
            <div className="help-quick">
              {TOURS.filter((tour) => tour.group === group.id).map((tour) => (
                <button
                  key={tour.id}
                  type="button"
                  className="help-quick-card"
                  data-testid={`help-tour-${tour.id}`}
                  onClick={() => launch(tour.id)}
                  style={{ cursor: "pointer", textAlign: "left", border: "none", width: "100%" }}
                >
                  <strong>
                    {tour.title}
                    {seen[tour.id] ? ` · ${t("help.tours.seen")}` : ""}
                  </strong>
                  <span className="muted">{tour.blurb}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
        <button
          type="button"
          className="btn ghost"
          style={{ marginTop: 12 }}
          onClick={() => resetSeen()}
        >
          {t("help.tours.reset")}
        </button>
      </div>

      <label className="universe-search help-search">
        {t("help.searchLabel")}
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("help.searchPlaceholder")}
          data-testid="help-search"
          autoComplete="off"
        />
      </label>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>
          {t("help.sourcePolicy.title")} <InfoTip termId="source_policy" />
        </h2>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("help.sourcePolicy.lede")}
        </p>
        <div className="source-pills" style={{ marginTop: 12 }}>
          {[
            { ok: true, labelKey: "help.source.in.transcripts" },
            { ok: true, labelKey: "help.source.in.filings" },
            { ok: true, labelKey: "help.source.in.ir" },
            { ok: true, labelKey: "help.source.in.asr" },
            { ok: true, labelKey: "help.source.in.actuals" },
            { ok: false, labelKey: "help.source.out.av" },
            { ok: false, labelKey: "help.source.out.technicals" },
            { ok: false, labelKey: "help.source.out.shenanigans" },
            { ok: false, labelKey: "help.source.out.sentiment" },
          ].map((s) => (
            <span key={s.labelKey} className={`source-pill ${s.ok ? "in" : "out"}`}>
              {s.ok ? "✓" : "✕"} {t(s.labelKey)}
            </span>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 12, marginBottom: 0, fontSize: 13 }}>
          {t("help.source.catalog")}{" "}
          <Link to="/desk" style={{ color: "var(--accent)", fontWeight: 600 }}>
            {t("help.source.deskParams")}
          </Link>
          {" · "}
          <Link to="/methodology">{t("help.source.methodology")}</Link>
        </p>
      </div>

      <div className="panel">
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          {t("help.glossaryNote")}
        </p>
        {HELP_SECTIONS.map((section) => (
          <TermSection
            key={section.title}
            title={section.title}
            ids={section.ids}
            needle={needle}
          />
        ))}
        {needle &&
          HELP_SECTIONS.every((section) =>
            section.ids.every((id) => {
              const item = GLOSSARY[id];
              if (!item) return true;
              return !(
                item.term.toLowerCase().includes(needle) ||
                item.tip.toLowerCase().includes(needle) ||
                item.id.toLowerCase().includes(needle)
              );
            })
          ) && (
            <div className="empty">{t("help.glossaryEmpty", { query: q.trim() })}</div>
          )}
      </div>

      <p className="muted" data-testid="help-legal-strip">
        <Link to="/terms">{t("footer.terms")}</Link>
        {" · "}
        <Link to="/privacy">{t("footer.privacy")}</Link>
        {" · "}
        <Link to="/trust">{t("footer.trust")}</Link>
        {" · "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
      </p>
      <Disclaimer />
    </section>
  );
}
