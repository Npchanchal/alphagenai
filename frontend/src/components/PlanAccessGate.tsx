import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";
import { isIndexingCrawler } from "../lib/indexingCrawler";
import { useI18n } from "../i18n";

type Props = {
  /** Entitlement feature key (plan ∩ role). */
  feature: string;
  title: string;
  description: string;
  /** Post-login return path (e.g. /desk). */
  returnTo?: string;
  kicker?: string;
  children: ReactNode;
  /** page = full route shell; panel = inset block inside a tab/panel */
  variant?: "page" | "panel";
  testId?: string;
};

/** Renders children when entitled; otherwise plans / login upsell (nav stays visible). */
export default function PlanAccessGate({
  feature,
  title,
  description,
  returnTo = "/",
  kicker,
  children,
  variant = "page",
  testId = "plan-access-gate",
}: Props) {
  const { t } = useI18n();
  const { user, token } = useAuth();
  const { has, entitlements, loading } = useEntitlements();

  // Google and other indexers render this shell. The seat wall would replace
  // the page, so Search would store the sign-in prompt instead of the page.
  if (isIndexingCrawler()) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <section className={variant === "page" ? "plan-access-page" : "plan-access-panel"}>
        <p className="muted">{t("ui.PlanAccessGate.loading")}</p>
      </section>
    );
  }

  if (has(feature) || user?.platform_admin_role === "super") {
    return <>{children}</>;
  }

  const guestOrSignedOut =
    !token || user?.kind === "guest" || entitlements.plan === "guest";

  const body = (
    <>
      {kicker && variant === "page" && <p className="page-kicker">{kicker}</p>}
      <h2 style={variant === "panel" ? { marginTop: 0 } : undefined}>{title}</h2>
      <p className="muted lede">{description}</p>
      <p className="muted">{t("ui.PlanAccessGate.currentAccess")}</p>
      {guestOrSignedOut ? (
        <div className="plan-access-cta row gap">
          <Link to="/login" state={{ from: returnTo }} className="btn-primary">
            {t("common.login")}
          </Link>
          <Link to="/register" className="btn">
            {t("common.register")}
          </Link>
          <Link to="/products#plans" className="btn-ghost">
            {t("nav.package_plans")}
          </Link>
        </div>
      ) : (
        <div className="plan-access-cta row gap">
          <Link to="/products#plans" className="btn-primary">
            {t("nav.package_plans")}
          </Link>
          <Link to="/billing" className="btn">
            {t("nav.billing")}
          </Link>
        </div>
      )}
      {guestOrSignedOut && (
        <p className="muted" style={{ fontSize: 13, marginTop: "0.75rem" }}>
          {t("ui.PlanAccessGate.unlockHint")}{" "}
          <Link to="/products#plans">{t("nav.package_plans")}</Link>
        </p>
      )}
    </>
  );

  if (variant === "panel") {
    return (
      <div className="plan-access-panel panel" data-testid={testId}>
        {body}
      </div>
    );
  }

  return (
    <section className="plan-access-page" data-testid={testId}>
      {body}
    </section>
  );
}
