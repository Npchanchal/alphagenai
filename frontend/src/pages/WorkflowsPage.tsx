import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";

const JOBS = [
  {
    id: "earnings-season",
    titleKey: "workflows.earnings.title",
    ledeKey: "workflows.earnings.lede",
    bodyKey: "workflows.earnings.body",
    links: [
      { to: "/companies/infy", labelKey: "workflows.earnings.linkDossier" },
      { to: "/analyst", labelKey: "workflows.earnings.linkMonitor" },
    ],
  },
  {
    id: "management-delivery",
    titleKey: "workflows.delivery.title",
    ledeKey: "workflows.delivery.lede",
    bodyKey: "workflows.delivery.body",
    links: [
      { to: "/tracker", labelKey: "workflows.delivery.linkScreener" },
      { to: "/companies/infy", labelKey: "workflows.delivery.linkEvidence" },
      { to: "/methodology", labelKey: "workflows.delivery.linkMethod" },
    ],
  },
  {
    id: "coverage",
    titleKey: "workflows.coverage.title",
    ledeKey: "workflows.coverage.lede",
    bodyKey: "workflows.coverage.body",
    links: [
      { to: "/tracker", labelKey: "workflows.coverage.linkScreener" },
      { to: "/rankings", labelKey: "workflows.coverage.linkSnapshot" },
      { to: "/sights", labelKey: "workflows.coverage.linkExplorer" },
    ],
  },
  {
    id: "desk-note",
    titleKey: "workflows.note.title",
    ledeKey: "workflows.note.lede",
    bodyKey: "workflows.note.body",
    links: [
      { to: "/analyst", labelKey: "workflows.note.linkAnalyst" },
      { to: "/desk", labelKey: "workflows.note.linkWorkbench" },
    ],
  },
] as const;

/** Four desk jobs, each pointing at a route that already does the work. */
export default function WorkflowsPage() {
  const { t } = useI18n();
  const location = useLocation();

  useEffect(() => {
    const id = location.hash.replace(/^#/, "");
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  return (
    <section className="page workflows-page" data-testid="workflows-page">
      <p className="page-kicker">{t("workflows.kicker")}</p>
      <h1>{t("workflows.title")}</h1>
      <p className="lede muted">{t("workflows.lede")}</p>
      <nav className="about-toc" aria-label={t("workflows.toc")}>
        {JOBS.map((job) => (
          <a key={job.id} href={`#${job.id}`}>
            {t(job.titleKey)}
          </a>
        ))}
      </nav>
      {JOBS.map((job) => (
        <article key={job.id} id={job.id} className="panel" data-testid={`workflow-${job.id}`}>
          <h2 style={{ marginTop: 0 }}>{t(job.titleKey)}</h2>
          <p>{t(job.ledeKey)}</p>
          <p className="muted">{t(job.bodyKey)}</p>
          <p>
            {job.links.map((link, i) => (
              <span key={link.to}>
                {i > 0 ? " · " : null}
                <Link to={link.to}>{t(link.labelKey)}</Link>
              </span>
            ))}
          </p>
        </article>
      ))}
      <p className="muted">
        <Link to="/products#plans">{t("workflows.pricing")}</Link>
      </p>
      <Disclaimer compact />
    </section>
  );
}
