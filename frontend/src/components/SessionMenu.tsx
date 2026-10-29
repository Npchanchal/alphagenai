import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import LanguageSelect from "./LanguageSelect";
import MarketSelect from "./MarketSelect";
import { useAuth } from "../lib/auth";
import { useI18n } from "../i18n";
import type { LangCode } from "../i18n/languages";

export default function SessionMenu() {
  const { user, logout, updatePreferences, loading } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const canOrgAdmin =
    user?.org_id && (user.role === "owner" || user.role === "admin");

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (loading) return null;

  const label = user
    ? user.kind === "guest"
      ? t("session.guestLabel")
      : user.email ?? user.name
    : t("common.account");

  return (
    <div className="session-menu" ref={ref}>
      <MarketSelect />
      <LanguageSelect
        onChange={(code: LangCode) => {
          void updatePreferences({ language: code });
        }}
      />
      <button
        type="button"
        className="session-trigger"
        data-testid="session-menu"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {label}
      </button>
      {open && (
        <div className="session-dropdown" role="menu">
          {!user && (
            <>
              <Link to="/login" role="menuitem" onClick={() => setOpen(false)}>
                {t("common.login")}
              </Link>
              <Link to="/register" role="menuitem" onClick={() => setOpen(false)}>
                {t("common.register")}
              </Link>
              <Link to="/login" role="menuitem" onClick={() => setOpen(false)}>
                {t("common.guest")}
              </Link>
            </>
          )}
          {user && (
            <>
              <Link to="/account" role="menuitem" onClick={() => setOpen(false)}>
                {t("common.account")}
              </Link>
              {canOrgAdmin && (
                <Link to="/org/settings" role="menuitem" onClick={() => setOpen(false)}>
                  {t("session.orgSettings")}
                </Link>
              )}
              {user.platform_admin_role && (
                <Link to="/admin" role="menuitem" onClick={() => setOpen(false)}>
                  {t("session.adminPortal")}
                </Link>
              )}
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  void logout().then(() => setOpen(false));
                }}
              >
                {t("common.logout")}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
