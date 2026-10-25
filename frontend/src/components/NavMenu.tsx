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
  /** Two-column panel for a long tool list */
  wide?: boolean;
  /** Open toward the left so the panel stays on screen */
  alignEnd?: boolean;
};

type NavEntry =
  | ({ kind: "link" } & Required<Pick<NavLeaf, "to" | "labelKey">> &
      Omit<NavLeaf, "to" | "labelKey" | "heading">)
  | ({ kind: "group" } & NavGroup);

/**
 * Primary jobs, in the order a desk uses them:
 * GCI Screener · Research · Workspace · Pricing · Learn.
 * Tool names stay canonical. Entitlements gate each route, not the menu.
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
    kind: "group",
    id: "research",
    labelKey: "nav.research_group",
    matchPrefixes: ["/research", "/analyst", "/rankings"],
    children: [
      { to: "/research", labelKey: "nav.research", tipId: "research_terminal" },
      { to: "/analyst", labelKey: "nav.analyst" },
      { to: "/rankings", labelKey: "nav.rankings" },
    ],
  },
  {
    kind: "group",
    id: "workspace",
    labelKey: "nav.workspace",
    matchPrefixes: ["/desk", "/sights", "/ninja", "/holdings"],
    wide: true,
    alignEnd: true,
    children: [
      { to: "/desk", labelKey: "nav.desk", tipId: "desk_sku" },
      { labelKey: "nav.sights", heading: true },
      { to: "/sights", end: true, labelKey: "nav.sights_hub", tipId: "sights" },
      { to: "/sights/themes", labelKey: "nav.sights_themes" },
      { to: "/sights/street", labelKey: "nav.sights_street" },
      { to: "/sights/field", labelKey: "nav.sights_field" },
      { to: "/sights/grid", labelKey: "nav.sights_grid" },
      { to: "/sights/deep-dive", labelKey: "nav.sights_deep_dive" },
      { to: "/sights/fundamentals", labelKey: "nav.sights_fundamentals" },
      { labelKey: "nav.ninja", heading: true },
      { to: "/ninja", end: true, labelKey: "nav.ninja_valuation" },
      { to: "/ninja/indices", labelKey: "nav.ninja_indices" },
      { to: "/ninja/tests", labelKey: "nav.ninja_tests" },
      { to: "/holdings", labelKey: "nav.holdings" },
    ],
  },
  {
    kind: "link",
    to: "/products#plans",
    labelKey: "nav.pricing",
  },
  {
    kind: "group",
    id: "learn",
    labelKey: "nav.learn",
    matchPrefixes: [
      "/workflows",
      "/methodology",
      "/changelog",
      "/blog",
      "/help",
      "/answers",
      "/about",
      "/trust",
      "/developers",
      "/status",
      "/press",
    ],
    alignEnd: true,
    children: [
      { to: "/workflows", labelKey: "nav.workflows" },
      { to: "/methodology", labelKey: "footer.methodology" },
      { to: "/changelog", labelKey: "footer.changelog" },
      { to: "/blog", labelKey: "nav.blog" },
      { to: "/help", labelKey: "nav.help" },
      { to: "/answers", labelKey: "footer.answers" },
      { labelKey: "nav.company", heading: true },
      { to: "/about", end: true, labelKey: "nav.about" },
      { to: "/trust", labelKey: "nav.trust" },
      { to: "/developers", labelKey: "nav.api" },
      { to: "/status", labelKey: "nav.status" },
      { to: "/press", labelKey: "footer.press" },
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
          className={`nav-submenu${group.wide ? " nav-submenu-wide" : ""}${group.alignEnd ? " align-end" : ""}`}
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
