import { Link } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useI18n } from "../i18n";

type Props = {
  error?: ApiError | null;
  cap?: number;
};

/** Guest 15-dossier cap — register a desk or request a Pilot seat. */
export default function GuestPaywallModal({ error, cap = 15 }: Props) {
  const { t } = useI18n();
  const limit = cap;

  return (
    <div className="source-viewer-overlay" data-testid="guest-paywall" role="dialog" aria-modal="true">
      <div className="source-viewer">
        <h2 style={{ marginTop: 0 }}>{t("ui.GuestPaywallModal.title")}</h2>
        <p>
          {error?.message ||
            t("ui.GuestPaywallModal.body", { limit })}
        </p>
        <p className="muted" style={{ fontSize: 13 }}>
          {t("ui.GuestPaywallModal.note")}
        </p>
        <p className="muted" style={{ fontSize: 13 }}>
          {t("ui.GuestPaywallModal.pilotHint")}
        </p>
        <div className="citation-actions" style={{ marginTop: 16 }}>
          <Link className="btn" to="/register" data-testid="guest-paywall-register">
            {t("common.register")}
          </Link>
          <Link className="btn ghost" to="/login">
            {t("ui.GuestPaywallModal.signIn")}
          </Link>
          <Link className="btn ghost" to="/pilot">
            {t("footer.pilot")}
          </Link>
          <Link className="btn ghost" to="/products#plans">
            {t("footer.package")}
          </Link>
        </div>
      </div>
    </div>
  );
}
