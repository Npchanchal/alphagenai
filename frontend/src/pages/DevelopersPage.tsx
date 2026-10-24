import { Link } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";

const READS = [
  { path: "/api/v1/companies", note: "Universe + scores" },
  { path: "/api/v1/companies/{id}/gci", note: "Dossier payload" },
  { path: "/api/v1/companies/{id}/gci/history", note: "Point-in-time path" },
  { path: "/api/v1/rankings", note: "Public Snapshot" },
  { path: "/api/v1/index/ledger", note: "Append-only score ledger" },
  { path: "/api/v1/index/changelog", note: "Methodology changelog" },
  { path: "/api/v1/index/changelog.rss", note: "Changelog RSS" },
  { path: "/api/v1/index/files", note: "Frozen daily levels" },
];

export default function DevelopersPage() {
  const { t } = useI18n();
  return (
    <section className="help-page" data-testid="developers-page">
      <p className="page-kicker">{t("developers.kicker")}</p>
      <h1>{t("developers.title")}</h1>
      <p className="muted lede">{t("developers.lede")}</p>
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Public reads</h2>
        <ul className="about-list">
          {READS.map((r) => (
            <li key={r.path}>
              <code>{r.path}</code> — {r.note}
            </li>
          ))}
        </ul>
        <p>
          <a href="/docs" rel="noreferrer">
            OpenAPI
          </a>
          {" · "}
          <Link to="/products#plans">Request a quote</Link>
          {" · "}
          <Link to="/changelog">Changelog</Link>
        </p>
      </div>
      <Disclaimer />
    </section>
  );
}
