import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import { useEntitlements } from "../lib/entitlements";

type Props = {
  /** Market (or company) the page is showing, e.g. "United States" or "Apple Inc.". */
  subject: string;
  testId?: string;
};

/** One line when the seat's plan does not cover what is on screen. Scores stay readable. */
export default function PlanScopeNotice({ subject, testId = "plan-scope-notice" }: Props) {
  const { t } = useI18n();
  const { entitlements } = useEntitlements();
  return (
    <p className="scaffold-banner" data-testid={testId}>
      {t("scope.notice", { subject, plan: entitlements.coverage?.label || t("scope.none") })}{" "}
      <Link to="/products#coverage">{t("scope.addMarket")}</Link>
    </p>
  );
}
