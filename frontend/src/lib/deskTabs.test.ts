import { describe, expect, it } from "vitest";
import { deskTabVisible } from "./deskTabs";

function allow(...features: string[]) {
  const set = new Set(features);
  return (feature: string) => set.has(feature);
}

describe("deskTabVisible", () => {
  const labeler = allow("desk", "labeling", "feedback");
  const analyst = allow("desk", "desk_write", "wordmap", "ic_export", "feedback");

  it("lets a labeler read the queue and label, and keeps write tabs off", () => {
    expect(deskTabVisible("review", labeler)).toBe(true);
    expect(deskTabVisible("labeling", labeler)).toBe(true);
    expect(deskTabVisible("wordmap", labeler)).toBe(false);
    expect(deskTabVisible("vernacular", labeler)).toBe(false);
    expect(deskTabVisible("import", labeler)).toBe(false);
    expect(deskTabVisible("reports", labeler)).toBe(false);
  });

  it("opens word map and reports for an analyst seat that has them", () => {
    expect(deskTabVisible("wordmap", analyst)).toBe(true);
    expect(deskTabVisible("reports", analyst)).toBe(true);
    expect(deskTabVisible("vernacular", analyst)).toBe(false);
    expect(deskTabVisible("labeling", analyst)).toBe(false);
  });

  it("opens vernacular only when the plan includes it", () => {
    expect(deskTabVisible("vernacular", allow("desk", "vernacular"))).toBe(true);
  });
});
