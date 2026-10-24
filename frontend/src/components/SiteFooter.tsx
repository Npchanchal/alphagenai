import { Link, useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { copyrightLine, LEGAL_ENTITY, PRODUCT_NAME } from "../lib/legal";
import { useAuth } from "../lib/auth";
/** Persistent copyright + legal links — Ocotillo Innovation Private Limited. */
export default function SiteFooter() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  const { token, user } = useAuth();
  const signedIn = Boolean(token && user?.kind !== "guest");
  const onHome = pathname === "/";

  return (
    <footer className="site-footer" data-testid="site-footer">
      <div className="site-footer-inner">
        <p className="site-footer-copy">{copyrightLine()}</p>
        <nav className="site-footer-links" aria-label={t("ui.SiteFooter.legalNav")}>
          <Link to="/terms">{t("footer.terms")}</Link>
          <Link to="/privacy">{t("footer.privacy")}</Link>
          <Link to="/trust">{t("footer.trust")}</Link>
          <Link to="/methodology">{t("footer.methodology")}</Link>
          <Link to="/changelog">{t("footer.changelog")}</Link>
          <Link to="/help">{t("footer.help")}</Link>
          <Link to="/answers">{t("footer.answers")}</Link>
          <Link to="/press">{t("footer.press")}</Link>
          <Link to="/rankings">{t("footer.rankings")}</Link>
          <Link to="/blog">{t("footer.blog")}</Link>
          {signedIn ? <Link to="/billing">{t("footer.billing")}</Link> : null}
          <Link to="/developers">API</Link>
          <Link to="/status">Status</Link>
          <Link to="/products#plans">{t("footer.package")}</Link>
          {onHome ? (
            <a href="#pilot-request">{t("footer.pilot")}</a>
          ) : (
            <Link to="/pilot">{t("footer.pilot")}</Link>
          )}
          <Link to="/about">{t("footer.about")}</Link>
        </nav>
        <p className="muted site-footer-note">
          {t("footer.note", { product: PRODUCT_NAME, entity: LEGAL_ENTITY })}
        </p>
      </div>
    </footer>
  );
}
