import { describe, expect, it } from "vitest";
import { TOURS, getTour, TOUR_STORAGE_KEY } from "./lib/tours";

describe("site tours", () => {
  it("defines workbench + learn tours with steps", () => {
    expect(TOURS.map((t) => t.id)).toEqual([
      "tracker",
      "dossier",
      "desk",
      "research",
      "sights",
      "analyst",
      "holdings",
      "ninja",
      "workflows",
      "about_help",
    ]);
    expect(TOUR_STORAGE_KEY).toBe("citealpha.tours.seen.v2");
    for (const t of TOURS) {
      expect(t.steps.length).toBeGreaterThanOrEqual(3);
      expect(t.startRoute).toBeTruthy();
      expect(t.group === "workbench" || t.group === "learn").toBe(true);
      for (const s of t.steps) {
        expect(s.selector).toBeTruthy();
        expect(s.title).toBeTruthy();
        expect(s.body.length).toBeGreaterThan(20);
      }
    }
  });

  it("getTour resolves known ids", () => {
    expect(getTour("tracker")?.title).toMatch(/Screener/i);
    expect(getTour("desk")?.title).toBe("Analyst Workbench");
    expect(getTour("desk")?.steps.some((s) => s.search?.includes("corpus"))).toBe(true);
    expect(getTour("desk")?.steps.some((s) => s.search?.includes("pit"))).toBe(true);
    expect(getTour("sights")?.startRoute).toBe("/sights");
    expect(getTour("about_help")?.steps.some((s) => s.route === "/trust")).toBe(true);
    expect(getTour("analyst")?.startRoute).toBe("/analyst");
    expect(getTour("workflows")?.group).toBe("learn");
  });
});
