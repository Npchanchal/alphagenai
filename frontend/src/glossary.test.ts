import { describe, expect, it } from "vitest";
import { GLOSSARY, HELP_SECTIONS, tipText } from "./lib/glossary";

describe("glossary", () => {
  it("does not name competitors in product chrome", () => {
    const blob = Object.values(GLOSSARY)
      .map((g) => `${g.term} ${g.tip}`)
      .join("\n")
      .toLowerCase();
    expect(blob).not.toMatch(/bloomberg/);
    expect(blob).not.toMatch(/alphasense/);
  });

  it("states the scorer rules for dropped, beats and listings in plain words", () => {
    expect(GLOSSARY.dropped.tip).toMatch(/15-point withdrawal deduction/);
    expect(GLOSSARY.nse_bse.tip).toMatch(/Not scored/);
    expect(GLOSSARY.exceeded.tip).toMatch(/never go below 60/);
    const blob = Object.values(GLOSSARY).map((g) => g.tip).join("\n");
    expect(blob).not.toMatch(/\bv4\b/);
  });

  it("includes Sights, SKUs, rankings, and Trust Center", () => {
    for (const id of ["sights", "score_sku", "radar", "ledger", "data_sku", "rankings", "trust_center"]) {
      expect(GLOSSARY[id]).toBeTruthy();
      expect(tipText(id).length).toBeGreaterThan(20);
    }
    const where = HELP_SECTIONS.find((s) => s.title === "Where to work");
    expect(where?.ids).toEqual(expect.arrayContaining(["sights", "trust_center", "radar"]));
  });
});
