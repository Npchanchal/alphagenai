/** Admin bar menus. Presentation over the platform section list and the org seat role. */

export type AdminMenuItem = {
  id: string;
  label: string;
  to: string;
};

export type AdminMenuGroup = {
  id: string;
  label: string;
  items: AdminMenuItem[];
};

type PlatformRow = {
  groupId: string;
  group: string;
  id: string;
  label: string;
  section?: string;
  report?: string;
  permission?: string;
};

const PLATFORM_LAYOUT: PlatformRow[] = [
  { groupId: "work", group: "Work", id: "overview", label: "Board" },
  { groupId: "work", group: "Work", id: "feedback", label: "Feedback" },
  { groupId: "work", group: "Work", id: "pilot-requests", label: "Pilot requests" },
  { groupId: "tenants", group: "Tenants", id: "orgs", label: "Organisations" },
  { groupId: "tenants", group: "Tenants", id: "users", label: "Users" },
  { groupId: "index", group: "Index", id: "labeling", label: "Labeling queue" },
  { groupId: "index", group: "Index", id: "commitments", label: "Commitments" },
  {
    groupId: "index",
    group: "Index",
    id: "report-index",
    label: "Index health",
    section: "reports",
    report: "index",
    permission: "audit.read",
  },
  {
    groupId: "index",
    group: "Index",
    id: "report-coverage",
    label: "Coverage",
    section: "reports",
    report: "coverage",
    permission: "audit.read",
  },
  {
    groupId: "index",
    group: "Index",
    id: "report-sla",
    label: "Filing to score",
    section: "reports",
    report: "sla",
    permission: "audit.read",
  },
  { groupId: "commercial", group: "Commercial", id: "billing", label: "Invoices" },
  {
    groupId: "commercial",
    group: "Commercial",
    id: "report-usage",
    label: "Seat and agent use",
    section: "reports",
    report: "usage",
    permission: "billing.read",
  },
  { groupId: "trust", group: "Trust", id: "legal", label: "Legal" },
  {
    groupId: "trust",
    group: "Trust",
    id: "report-trust",
    label: "Trust snapshot",
    section: "reports",
    report: "trust",
    permission: "legal.read",
  },
  { groupId: "trust", group: "Trust", id: "audit", label: "Audit counters" },
  {
    groupId: "trust",
    group: "Trust",
    id: "report-audit-events",
    label: "Auth events",
    section: "reports",
    report: "audit-events",
    permission: "audit.read",
  },
  { groupId: "system", group: "System", id: "system", label: "Jobs and cleanup" },
];

export function platformMenu(
  sections: Array<{ id: string }>,
  permissions: string[],
): AdminMenuGroup[] {
  const ids = new Set(sections.map((s) => s.id));
  const perms = new Set(permissions);
  const groups = new Map<string, AdminMenuGroup>();
  for (const row of PLATFORM_LAYOUT) {
    const section = row.section || row.id;
    if (!ids.has(section)) continue;
    if (row.permission && !perms.has(row.permission)) continue;
    const to = row.report
      ? `/admin?section=reports&report=${row.report}`
      : `/admin?section=${section}`;
    let group = groups.get(row.groupId);
    if (!group) {
      group = { id: row.groupId, label: row.group, items: [] };
      groups.set(row.groupId, group);
    }
    group.items.push({ id: row.id, label: row.label, to });
  }
  return [...groups.values()];
}

function item(id: string, label: string): AdminMenuItem {
  return { id, label, to: `/org/settings?section=${id}` };
}

export function organisationMenu(opts: { analyst: boolean; pilot: boolean }): AdminMenuGroup[] {
  const groups: AdminMenuGroup[] = [
    { id: "overview", label: "Overview", items: [item("overview", "Summary")] },
    {
      id: "people",
      label: "People",
      items: [item("members", "Members"), item("invites", "Invites"), item("partners", "Design partners")],
    },
    {
      id: "access",
      label: "Access",
      items: [item("signin", "Sign-in"), item("keys", "API keys")],
    },
  ];
  if (opts.analyst) {
    groups.push({
      id: "delivery",
      label: "Delivery",
      items: [item("destinations", "Destinations"), item("style", "Export style")],
    });
  }
  const commercial: AdminMenuItem[] = [item("billing", "Billing")];
  if (opts.pilot) commercial.push(item("pilot", "Pilot checklist"));
  groups.push({ id: "commercial", label: "Commercial", items: commercial });
  groups.push({ id: "activity", label: "Activity", items: [item("audit", "Audit")] });
  return groups;
}

export function adminItemActive(pathname: string, search: string, to: string): boolean {
  const [path, query = ""] = to.split("?");
  if (pathname !== path) return false;
  const want = new URLSearchParams(query);
  const have = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const wantSection = want.get("section") || "overview";
  const haveSection = have.get("section") || "overview";
  if (wantSection !== haveSection) return false;
  if (want.has("report")) return have.get("report") === want.get("report");
  return !have.get("report");
}

export function platformChip(role: string): string {
  const name = role.trim().toLowerCase();
  if (name === "super") return "Platform super";
  if (name === "ops") return "Platform ops";
  if (name === "compliance") return "Platform compliance";
  if (name === "billing") return "Platform billing";
  if (name === "support") return "Platform support";
  return "Platform";
}
