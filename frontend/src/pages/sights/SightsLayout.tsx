import { NavLink, Outlet, useLocation } from "react-router-dom";
import Disclaimer from "../../components/Disclaimer";
import { useI18n } from "../../i18n";

const PRIMARY: { to: string; label: string; end?: boolean }[] = [
  { to: "/sights", label: "ui.SightsLayout.nav.hub", end: true },
  { to: "/sights/themes", label: "ui.SightsLayout.nav.themes" },
  { to: "/sights/street", label: "ui.SightsLayout.nav.street" },
  { to: "/sights/field", label: "ui.SightsLayout.nav.field" },
  { to: "/sights/grid", label: "ui.SightsLayout.nav.grid" },
  { to: "/sights/deep-dive", label: "ui.SightsLayout.nav.deepDive" },
  { to: "/sights/fundamentals", label: "ui.SightsLayout.nav.fundamentals" },
  { to: "/sights/settings", label: "ui.SightsLayout.nav.settings" },
];

function linkClass(isActive: boolean) {
  return isActive ? "sights-nav-link active" : "sights-nav-link";
}

/** Disclosure Explorer shell. Section links match the top-menu list. */
export default function SightsLayout() {
  const { t } = useI18n();
  const { pathname } = useLocation();

  return (
    <div className="page sights-page" data-testid="sights-shell">
      <p className="page-kicker">{t("ui.SightsLayout.kicker")}</p>
      <h1>{t("ui.SightsLayout.title")}</h1>
      <p className="lede">{t("ui.SightsLayout.lede")}</p>
      <nav className="sights-nav" aria-label={t("ui.SightsLayout.navAria")}>
        {PRIMARY.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => linkClass(isActive || pathname === l.to)}
          >
            {t(l.label)}
          </NavLink>
        ))}
      </nav>
      <Outlet />
      <Disclaimer compact />
    </div>
  );
}
