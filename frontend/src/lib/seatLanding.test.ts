import { describe, expect, it } from "vitest";
import { canAcceptRole, groupAnalystSkills, seatLanding, SEAT_COPY } from "./seatLanding";

describe("seat landing", () => {
  it("sends each seat to its first screen", () => {
    expect(seatLanding("pm")).toBe("/holdings");
    expect(seatLanding("data")).toBe("/developers");
    expect(seatLanding("oversight")).toBe("/org/settings?section=audit");
    expect(seatLanding("analyst")).toBe("/analyst");
    expect(seatLanding("reviewer")).toBe("/desk?tab=review");
    expect(seatLanding("labeler")).toBe("/desk?tab=labeling");
    expect(seatLanding("viewer")).toBe("/tracker");
    expect(seatLanding("owner")).toBe("/tracker");
    expect(seatLanding(undefined)).toBe("/tracker");
  });

  it("lands an IR seat on its one company, its short list, or the empty-list line", () => {
    expect(seatLanding("ir", ["INFY"])).toBe("/companies/infy");
    expect(seatLanding("ir", ["infy", "tcs"])).toBe("/tracker?packed=infy,tcs");
    expect(seatLanding("ir", [])).toBe("/tracker?ir=unnamed");
  });

  it("lets only reviewer, admin, and owner accept", () => {
    expect(["reviewer", "admin", "owner"].every((r) => canAcceptRole(r))).toBe(true);
    expect(["analyst", "labeler", "pm", "data", "ir", "oversight", "viewer"].some((r) => canAcceptRole(r))).toBe(false);
  });

  it("labels every appointable seat in words", () => {
    for (const id of ["viewer", "pm", "data", "ir", "oversight", "analyst", "labeler", "reviewer", "admin"]) {
      expect(SEAT_COPY[id]?.label).toBeTruthy();
      expect(SEAT_COPY[id]?.sentence).toMatch(/\.$/);
    }
    expect(SEAT_COPY.pm.label).toBe("Portfolio");
    expect(SEAT_COPY.ir.label).toBe("Investor relations");
  });
});

describe("analyst skill groups", () => {
  it("puts this print first and an unknown skill in the last group", () => {
    const groups = groupAnalystSkills([
      { id: "board_scorecard" },
      { id: "results_prep" },
      { id: "company_note" },
      { id: "brand_new_skill" },
    ]);
    expect(groups.map((g) => g.title)).toEqual(["This print", "Learn a name", "Board, credit, and events"]);
    expect(groups[2].skills.map((s) => s.id)).toEqual(["board_scorecard", "brand_new_skill"]);
  });
});
