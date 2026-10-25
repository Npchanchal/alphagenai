import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { fetchAdminPortalMe, type AdminPortalMe } from "../lib/api";
import {
  adminItemActive,
  organisationMenu,
  platformChip,
  platformMenu,
  type AdminMenuGroup,
} from "../lib/adminMenu";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";

type BarMenu = {
  id: "organisation" | "platform";
  label: string;
  chip: string;
  groups: AdminMenuGroup[];
};

function MenuPanel({
  menu,
  pathname,
  search,
  onPick,
}: {
  menu: BarMenu;
  pathname: string;
  search: string;
  onPick: () => void;
}) {
  return (
    <div className="admin-bar-panel" role="menu" id={`admin-menu-panel-${menu.id}`}>
      {menu.groups.map((group) => (
        <div key={group.id} className="admin-bar-group">
          <div className="admin-bar-group-label">{group.label}</div>
          {group.items.map((item) => {
            const active = adminItemActive(pathname, search, item.to);
            return (
              <Link
                key={item.id}
                to={item.to}
                role="menuitem"
                className={active ? "active" : ""}
                aria-current={active ? "page" : undefined}
                data-testid={`admin-nav-${item.id}`}
                onClick={onPick}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/** Second bar under the public nav. Absent unless the session is an org or platform admin. */
export default function AdminMenuBar() {
  const { user, token } = useAuth();
  const { entitlements, has, loading: entitlementsLoading } = useEntitlements();
  const location = useLocation();
  const [open, setOpen] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [portal, setPortal] = useState<AdminPortalMe | null>(null);
  const rootRef = useRef<HTMLElement>(null);

  const orgAdmin =
    !!user &&
    user.kind !== "guest" &&
    user.account_type !== "retail" &&
    !!user.org_id &&
    (user.role === "owner" || user.role === "admin");
  const platformRole = user?.platform_admin_role || "";

  useEffect(() => {
    if (!token || !platformRole) {
      setPortal(null);
      return;
    }
    let cancelled = false;
    void fetchAdminPortalMe(token)
      .then((row) => {
        if (!cancelled) setPortal(row);
      })
      .catch(() => {
        if (!cancelled) setPortal(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token, platformRole]);

  useEffect(() => {
    setOpen(null);
    setMobileOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(null);
        setMobileOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(null);
        setMobileOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (!orgAdmin && !platformRole) return null;

  const menus: BarMenu[] = [];
  if (orgAdmin) {
    menus.push({
      id: "organisation",
      label: "Organisation",
      chip: user?.role === "owner" ? "Organisation owner" : "Organisation admin",
      groups: organisationMenu({
        analyst: !entitlementsLoading && has("analyst_agent"),
        pilot: !entitlementsLoading && (entitlements.plan || "") === "pilot",
      }),
    });
  }
  if (platformRole && portal) {
    const groups = platformMenu(portal.sections || [], portal.permissions || []);
    if (groups.length > 0) {
      menus.push({
        id: "platform",
        label: "Platform",
        chip: platformChip(portal.platform_admin_role || platformRole),
        groups,
      });
    }
  }

  if (menus.length === 0 && !platformRole) return null;
  if (menus.length === 0) return null;

  function close() {
    setOpen(null);
    setMobileOpen(false);
  }

  return (
    <nav className="admin-bar" aria-label="Administration" data-testid="admin-bar" ref={rootRef}>
      <div className="admin-bar-chips">
        {menus.map((menu) => (
          <span key={menu.id} className="admin-bar-chip" data-testid={`admin-chip-${menu.id}`}>
            {menu.chip}
          </span>
        ))}
      </div>
      <button
        type="button"
        className="admin-bar-collapse"
        aria-expanded={mobileOpen}
        data-testid="admin-bar-toggle"
        onClick={() => setMobileOpen((v) => !v)}
      >
        Admin
      </button>
      <div className={`admin-bar-menus ${mobileOpen ? "open" : ""}`}>
        {menus.map((menu) => (
          <div key={menu.id} className="admin-bar-menu">
            <button
              type="button"
              className={open === menu.id ? "active" : ""}
              aria-expanded={open === menu.id}
              aria-controls={`admin-menu-panel-${menu.id}`}
              data-testid={`admin-menu-${menu.id}`}
              onClick={() => setOpen((current) => (current === menu.id ? null : menu.id))}
            >
              {menu.label}
            </button>
            {open === menu.id && (
              <MenuPanel menu={menu} pathname={location.pathname} search={location.search} onPick={close} />
            )}
          </div>
        ))}
      </div>
    </nav>
  );
}
