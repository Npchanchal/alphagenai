import { describe, expect, it } from "vitest";
import {
  buildRecordParts,
  englishRecordSentence,
  formatCharLocator,
  formatGuideGap,
  metricDisplayName,
} from "./score";
import { dossierSeo, resolveSeo } from "./seo";

describe("score helpers (W3)", () => {
  it("maps metric ids to display names and never leaves a raw id", () => {
    expect(metricDisplayName("revenue_growth_cc_pct")).toBe(
      "Revenue growth (constant currency) %",
    );
    expect(metricDisplayName("production_volume_mmt")).not.toMatch(/_/);
  });

  it("formats a character locator without brace placeholders", () => {
    expect(formatCharLocator(85, 120)).toBe("chars 85–120");
    expect(formatCharLocator(85, 120)).not.toMatch(/\{/);
    expect(formatCharLocator(null, 120)).toBe("");
  });

  it("states the guided-vs-actual gap in percentage points", () => {
    expect(
      formatGuideGap({
        actual_value: 19.7,
        guided_low: 12,
        guided_high: 14,
        guided_value: 13,
        metric: "revenue_growth_cc_pct",
      }),
    ).toBe("+6.7 pp");
  });

  it("builds a delivery-record sentence from closed rows", () => {
    const parts = buildRecordParts([
      { metric: "revenue_growth_cc_pct", period: "FY22", label: "exceeded", actual_value: 19.7 },
      { metric: "revenue_growth_cc_pct", period: "FY23", label: "met", actual_value: 15.4 },
      { metric: "revenue_growth_cc_pct", period: "FY24", label: "missed", actual_value: 1.4 },
      { metric: "operating_margin_pct", period: "FY25", label: "pending_guidance_cite", actual_value: 21.1 },
    ]);
    expect(parts.closed).toBe(3);
    expect(parts.metOrBeat).toBe(2);
    expect(parts.missedClause).toBe("; missed FY24");
    expect(englishRecordSentence(parts)).toMatch(/Met or beat/);
  });
});

describe("dossier SEO (W5.1)", () => {
  it("indexes hand-labeled names and noindexes others", () => {
    const indexed = dossierSeo({
      id: "infy",
      name: "Infosys",
      gci: 76.5,
      asOf: "2026-04-23",
      dataQuality: "hand_labeled",
      recordSentence: "Met or beat revenue guidance in 2 of 3 closed years; missed FY24.",
    });
    expect(indexed.robots).toBe("index,follow");
    expect(indexed.title).toContain("Infosys — Guidance Credibility Index (GCI) 76.5");
    expect(indexed.title).toContain("Data as of 23 Apr 2026");
    expect(indexed.jsonLd?.["@type"]).toBe("Dataset");

    const hidden = dossierSeo({
      id: "foo",
      name: "Foo",
      gci: null,
      asOf: null,
      dataQuality: "listing_master",
      recordSentence: "No closed, dual-cited results yet.",
    });
    expect(hidden.robots).toBe("noindex,follow");
  });

  it("does not flip a published dossier to noindex before the company request returns", () => {
    const seo = resolveSeo("/companies/infy");
    expect(seo.robots).toBe("index,follow");
    expect(seo.path).toBe("/companies/infy");
    expect(seo.title).toContain("Infosys");
    expect(seo.title).toContain("Guidance Credibility Index (GCI)");
    expect(resolveSeo("/companies/not-a-listed-company").robots).toBe("noindex,follow");
    expect(resolveSeo("/companies/INFY").robots).toBe("index,follow");
    expect(resolveSeo("/companies/INFY").path).toBe("/companies/infy");
  });

  it("indexes public product routes and noindexes unknown or private ones", () => {
    expect(resolveSeo("/analyst").robots ?? "index,follow").not.toMatch(/noindex/);
    expect(resolveSeo("/analyst").title).toContain("CiteAlpha Analyst");
    expect(resolveSeo("/sights/themes").robots ?? "index,follow").not.toMatch(/noindex/);
    expect(resolveSeo("/sights/grid").title).toContain("Compare Grid");
    expect(resolveSeo("/account").robots).toMatch(/noindex/);
    expect(resolveSeo("/org/settings").robots).toMatch(/noindex/);
    expect(resolveSeo("/sights/settings").robots).toMatch(/noindex/);
    expect(resolveSeo("/this-route-does-not-exist").robots).toBe("noindex,follow");
  });
});
