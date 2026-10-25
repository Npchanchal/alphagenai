import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { copyrightLine, LEGAL_ENTITY, PRODUCT_NAME } from "../lib/legal";
import { useAuth } from "../lib/auth";

type FooterLink = { to: string; labelKey: string; hashHome?: string };

const PRODUCT: FooterLink[] = [
  { to: "/tracker", labelKey: "nav.tracker" },
  { to: "/research", labelKey: "nav.research" },
  { to: "/analyst", labelKey: "nav.analyst" },
  { to: "/rankings", labelKey: "nav.rankings" },
  { to: "/products#plans", labelKey: "footer.package" },
  { to: "/pilot", labelKey: "footer.pilot", hashHome: "#pilot-request" },
];

const WORKSPACE: FooterLink[] = [
  { to: "/desk", labelKey: "nav.desk" },
  { to: "/sights", labelKey: "nav.sights" },
  { to: "/holdings", labelKey: "nav.holdings" },
  { to: "/developers", labelKey: "nav.api" },
  { to: "/status", labelKey: "nav.status" },
];

const LEARN: FooterLink[] = [
  { to: "/workflows", labelKey: "nav.workflows" },
  { to: "/methodology", labelKey: "footer.methodology" },
  { to: "/changelog", labelKey: "footer.changelog" },
  { to: "/blog", labelKey: "footer.blog" },
  { to: "/help", labelKey: "footer.help" },
  { to: "/answers", labelKey: "footer.answers" },
  { to: "/press", labelKey: "footer.press" },
];

const COMPANY: FooterLink[] = [
  { to: "/about", labelKey: "footer.about" },
  { to: "/trust", labelKey: "footer.trust" },
  { to: "/terms", labelKey: "footer.terms" },
  { to: "/privacy", labelKey: "footer.privacy" },
];

function FooterColumn({
  titleKey,
  links,
  onHome,
  extra,
}: {
  titleKey: string;
  links: FooterLink[];
  onHome: boolean;
  extra?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <div className="site-footer-col">
      <p className="site-footer-col-title">{t(titleKey)}</p>
      <nav aria-label={t(titleKey)}>
        {links.map((link) => {
          if (link.hashHome && onHome) {
            return (
              <a key={link.labelKey} href={link.hashHome}>
                {t(link.labelKey)}
              </a>
            );
          }
          return (
            <Link key={link.labelKey} to={link.to}>
              {t(link.labelKey)}
            </Link>
          );
        })}
        {extra}
      </nav>
    </div>
  );
}

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
        <div className="site-footer-grid">
          <FooterColumn titleKey="footer.col.product" links={PRODUCT} onHome={onHome} />
          <FooterColumn titleKey="footer.col.workspace" links={WORKSPACE} onHome={onHome} />
          <FooterColumn titleKey="footer.col.learn" links={LEARN} onHome={onHome} />
          <FooterColumn
            titleKey="footer.col.company"
            links={COMPANY}
            onHome={onHome}
            extra={signedIn ? <Link to="/billing">{t("footer.billing")}</Link> : null}
          />
        </div>
        <p className="site-footer-copy">{copyrightLine()}</p>
        <p className="muted site-footer-note">
          {t("footer.note", { product: PRODUCT_NAME, entity: LEGAL_ENTITY })}
        </p>
      </div>
    </footer>
  );
}
