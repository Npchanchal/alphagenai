import { useEffect, useId, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { tipText } from "../lib/glossary";

type NavLeaf = {
  to?: string;
  end?: boolean;
  labelKey: string;
  tipId?: string;
  /** Non-clickable section label inside a dropdown */
  heading?: boolean;
};

type NavGroup = {
  id: string;
  labelKey: string;
  /** Highlights parent when any child path matches */
  matchPrefixes: string[];
  children: NavLeaf[];
};

type NavEntry =
  | ({ kind: "link" } & Required<Pick<NavLeaf, "to" | "labelKey">> &
      Omit<NavLeaf, "to" | "labelKey" | "heading">)
  | ({ kind: "group" } & NavGroup);

/**
 * Primary: GCI Screener · Analyst Workbench · Filing Search · Disclosure Explorer · More.
 * All items visible — entitlements gate content on each route, not in nav.
 */
export const NAV_ENTRIES: NavEntry[] = [
  {
    kind: "link",
    to: "/tracker",
    end: true,
    labelKey: "nav.tracker",
    tipId: "tracker",
  },
  {
    kind: "link",
    to: "/desk",
    labelKey: "nav.desk",
    tipId: "desk_sku",
  },
  {
    kind: "link",
    to: "/research",
    labelKey: "nav.research",
    tipId: "research_terminal",
  },
  {
    kind: "link",
    to: "/analyst",
    labelKey: "nav.analyst",
  },
  {
    kind: "group",
    id: "sights",
    labelKey: "nav.sights",
    matchPrefixes: ["/sights"],
    children: [
      { to: "/sights", end: true, labelKey: "nav.sights_hub", tipId: "sights" },
      { labelKey: "nav.sights_more", heading: true },
      { to: "/sights/themes", labelKey: "nav.sights_themes" },
      { to: "/sights/street", labelKey: "nav.sights_street" },
      { to: "/sights/field", labelKey: "nav.sights_field" },
      { to: "/sights/grid", labelKey: "nav.sights_grid" },
      { to: "/sights/deep-dive", labelKey: "nav.sights_deep_dive" },
      { to: "/sights/fundamentals", labelKey: "nav.sights_fundamentals" },
    ],
  },
  {
    kind: "group",
    id: "ninja",
    labelKey: "nav.ninja",
    matchPrefixes: ["/ninja"],
    children: [
      { to: "/ninja", end: true, labelKey: "nav.ninja_valuation" },
      { to: "/ninja/indices", labelKey: "nav.ninja_indices" },
      { to: "/ninja/tests", labelKey: "nav.ninja_tests" },
      { to: "/holdings", labelKey: "nav.ninja_holdings" },
    ],
  },
  {
    kind: "group",
    id: "more",
    labelKey: "nav.more",
    matchPrefixes: [
      "/products",
      "/holdings",
      "/billing",
      "/about",
      "/blog",
      "/help",
      "/rankings",
      "/trust",
      "/methodology",
      "/changelog",
    ],
    children: [
      { to: "/products", end: true, labelKey: "nav.products_plans", tipId: "one_stop" },
      { to: "/holdings", labelKey: "nav.holdings" },
      { to: "/billing", labelKey: "nav.billing" },
      { labelKey: "nav.by_desk", heading: true },
      { to: "/products#desk-buy-side", labelKey: "nav.desk_buy_side" },
      { to: "/products#desk-sell-side", labelKey: "nav.desk_sell_side" },
      { to: "/products#desk-quant", labelKey: "nav.desk_quant" },
      { to: "/products#desk-ir-compliance", labelKey: "nav.desk_ir" },
      { labelKey: "nav.resources", heading: true },
      { to: "/blog", labelKey: "nav.blog" },
      { to: "/methodology", labelKey: "footer.methodology" },
      { to: "/changelog", labelKey: "footer.changelog" },
      { to: "/about", end: true, labelKey: "nav.about" },
      { to: "/help", labelKey: "nav.help" },
      { to: "/rankings", labelKey: "nav.rankings" },
      { to: "/trust", labelKey: "nav.trust" },
    ],
  },
];

function pathActive(pathname: string, to: string, end?: boolean): boolean {
  const pathOnly = to.split("#")[0] || to;
  if (end) return pathname === pathOnly;
  return pathname === pathOnly || pathname.startsWith(`${pathOnly}/`);
}

function leafActive(
  pathname: string,
  hash: string,
  to: string,
  end?: boolean,
): boolean {
  const [pathOnly, frag] = to.split("#");
  if (!pathActive(pathname, pathOnly || to, end)) return false;
  if (frag) return hash === `#${frag}`;
  return !hash || hash === "#";
}

function groupActive(pathname: string, group: NavGroup): boolean {
  return group.matchPrefixes.some((p) => {
    return pathname === p || pathname.startsWith(`${p}/`);
  });
}

function finePointerHover(): boolean {
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

function NavDropdown({ group }: { group: NavGroup }) {
  const { t } = useI18n();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hoverOpened = useRef(false);
  const menuId = useId();
  const active = groupActive(location.pathname, group);

  function clearCloseTimer() {
    if (closeTimer.current != null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }

  function openMenu() {
    clearCloseTimer();
    setOpen(true);
  }

  function scheduleClose() {
    clearCloseTimer();
    closeTimer.current = setTimeout(() => setOpen(false), 280);
  }

  useEffect(() => {
    setOpen(false);
    clearCloseTimer();
  }, [location.pathname, location.hash]);

  useEffect(() => {
    return () => clearCloseTimer();
  }, []);

  useEffect(() => {
    if (!open) return;
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
  }, [open]);

  const expanded = open;

  return (
    <div
      className={`nav-item nav-dropdown ${active ? "active" : ""} ${expanded ? "open" : ""}`}
      ref={ref}
      data-testid={`nav-dropdown-${group.id}`}
      onMouseEnter={() => {
        if (finePointerHover() && !open) {
          hoverOpened.current = true;
          openMenu();
        }
      }}
      onMouseLeave={() => {
        if (finePointerHover()) {
          hoverOpened.current = false;
          scheduleClose();
        }
      }}
    >
      <button
        type="button"
        className={`nav-link nav-dropdown-trigger ${active ? "active" : ""}`}
        aria-expanded={expanded}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => {
          clearCloseTimer();
          if (hoverOpened.current) {
            hoverOpened.current = false;
            setOpen(true);
            return;
          }
          setOpen((v) => !v);
        }}
      >
        {t(group.labelKey)}
        <span className="nav-caret" aria-hidden>
          ▾
        </span>
      </button>
      {expanded && (
        <div
          className="nav-submenu"
          role="menu"
          id={menuId}
          onMouseEnter={openMenu}
          onMouseLeave={() => {
            if (finePointerHover()) scheduleClose();
          }}
        >
          {group.children.map((child) => {
            if (child.heading) {
              return (
                <p
                  key={`${group.id}-h-${child.labelKey}`}
                  className="nav-subheading"
                  role="presentation"
                >
                  {t(child.labelKey)}
                </p>
              );
            }
            if (!child.to) return null;
            const childActive = leafActive(
              location.pathname,
              location.hash,
              child.to,
              child.end,
            );
            return (
              <NavLink
                key={`${group.id}-${child.to}-${child.labelKey}`}
                to={child.to}
                end={child.end}
                role="menuitem"
                title={child.tipId ? tipText(child.tipId) : undefined}
                className={`nav-sublink ${childActive ? "active" : ""}`}
                onClick={() => setOpen(false)}
              >
                {t(child.labelKey)}
              </NavLink>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Primary topnav with dropdown groups. */
export default function NavMenu() {
  const { t } = useI18n();

  return (
    <>
      {NAV_ENTRIES.map((entry) => {
        if (entry.kind === "group") {
          return <NavDropdown key={entry.id} group={entry} />;
        }
        return (
          <NavLink
            key={entry.to}
            to={entry.to}
            end={entry.end}
            title={entry.tipId ? tipText(entry.tipId) : undefined}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {t(entry.labelKey)}
          </NavLink>
        );
      })}
    </>
  );
}
