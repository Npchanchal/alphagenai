import { Link } from "react-router-dom";
import { useI18n } from "../i18n";

const LINKS = [
  { to: "/", key: "app.notFound.home" },
  { to: "/tracker", key: "app.notFound.cta" },
  { to: "/about", key: "footer.about" },
  { to: "/blog", key: "footer.blog" },
  { to: "/help", key: "nav.help" },
  { to: "/products#plans", key: "footer.package" },
  { to: "/trust", key: "footer.trust" },
] as const;

type NotFoundPageProps = {
  path?: string;
};

/** In-app 404 with crawlable helpful links (also prerendered as /404.html). */
export default function NotFoundPage({ path }: NotFoundPageProps) {
  const { t } = useI18n();

  return (
    <section className="page not-found-page" data-testid="not-found-page">
      <p className="page-kicker">404</p>
      <h1>{t("app.notFound.title")}</h1>
      <p className="muted">{t("app.notFound.lede", { path: path ?? "this URL" })}</p>
      <p className="muted">{t("app.notFound.help")}</p>
      <div className="landing-cta">
        <Link to="/tracker" className="btn primary">
          {t("app.notFound.cta")}
        </Link>
        <Link to="/" className="btn">
          {t("app.notFound.home")}
        </Link>
      </div>
      <nav className="not-found-links" aria-label={t("app.notFound.navLabel")}>
        {LINKS.map((item) => (
          <Link key={item.to} to={item.to}>
            {t(item.key)}
          </Link>
        ))}
      </nav>
    </section>
  );
}
