import { describe, expect, it } from "vitest";
import { adminItemActive, organisationMenu, platformMenu } from "./adminMenu";

const SUPER = [
  "overview",
  "orgs",
  "users",
  "feedback",
  "legal",
  "billing",
  "audit",
  "labeling",
  "commitments",
  "reports",
  "pilot-requests",
  "system",
].map((id) => ({ id }));

const SUPER_PERMS = [
  "orgs.read",
  "orgs.write",
  "users.read",
  "users.write",
  "feedback.read",
  "feedback.write",
  "legal.read",
  "legal.write",
  "billing.read",
  "billing.write",
  "pilot.manage",
  "audit.read",
  "system.ops",
  "portal.access",
];

describe("admin menus", () => {
  it("gives a super every platform group, including system", () => {
    const groups = platformMenu(SUPER, SUPER_PERMS);
    const labels = groups.flatMap((g) => g.items.map((i) => i.label));
    expect(labels).toContain("Board");
    expect(labels).toContain("Jobs and cleanup");
    expect(labels).toContain("Index health");
    expect(labels).toContain("Trust snapshot");
    expect(groups.find((g) => g.id === "system")?.items[0].to).toBe("/admin?section=system");
  });

  it("omits system, invoices, and trust for ops", () => {
    const sections = SUPER.filter((s) => !["system", "legal", "billing"].includes(s.id));
    const perms = ["orgs.read", "orgs.write", "users.read", "feedback.read", "feedback.write", "pilot.manage", "audit.read"];
    const labels = platformMenu(sections, perms).flatMap((g) => g.items.map((i) => i.label));
    expect(labels).toContain("Feedback");
    expect(labels).toContain("Organisations");
    expect(labels).not.toContain("Jobs and cleanup");
    expect(labels).not.toContain("Invoices");
    expect(labels).not.toContain("Trust snapshot");
    expect(labels).toContain("Index health");
  });

  it("shows invoices for billing and hides feedback", () => {
    const sections = [
      { id: "overview" },
      { id: "orgs" },
      { id: "billing" },
      { id: "audit" },
      { id: "reports" },
    ];
    const labels = platformMenu(sections, ["orgs.read", "billing.read", "billing.write", "audit.read"]).flatMap(
      (g) => g.items.map((i) => i.label),
    );
    expect(labels).toContain("Invoices");
    expect(labels).toContain("Seat and agent use");
    expect(labels).toContain("Index health");
    expect(labels).toContain("Audit counters");
    expect(labels).not.toContain("Feedback");
    expect(labels).not.toContain("Jobs and cleanup");
    expect(labels).not.toContain("Trust snapshot");
  });

  it("hides delivery without Analyst and the checklist off Pilot", () => {
    const plain = organisationMenu({ analyst: false, pilot: false }).flatMap((g) => g.items.map((i) => i.id));
    expect(plain).toContain("members");
    expect(plain).toContain("keys");
    expect(plain).toContain("billing");
    expect(plain).not.toContain("destinations");
    expect(plain).not.toContain("style");
    expect(plain).not.toContain("pilot");

    const full = organisationMenu({ analyst: true, pilot: true }).flatMap((g) => g.items.map((i) => i.id));
    expect(full).toContain("destinations");
    expect(full).toContain("pilot");
  });

  it("marks the open query as the active item", () => {
    expect(adminItemActive("/admin", "", "/admin?section=overview")).toBe(true);
    expect(adminItemActive("/admin", "?section=system", "/admin?section=system")).toBe(true);
    expect(adminItemActive("/admin", "?section=system", "/admin?section=overview")).toBe(false);
    expect(
      adminItemActive("/admin", "?section=reports&report=index", "/admin?section=reports&report=index"),
    ).toBe(true);
    expect(
      adminItemActive("/admin", "?section=reports&report=index", "/admin?section=reports&report=coverage"),
    ).toBe(false);
    expect(adminItemActive("/org/settings", "", "/org/settings?section=overview")).toBe(true);
    expect(adminItemActive("/tracker", "", "/admin?section=overview")).toBe(false);
  });
});
