import { describe, expect, it } from "vitest";
import {
  buildRecordParts,
  compareEvidence,
  compareEvidenceLatestFirst,
  englishRecordSentence,
  formatCharLocator,
  formatGuideGap,
  heatLevel,
  listEvidenceRows,
  metricDisplayName,
  periodRank,
  readInYearRevision,
} from "./score";
import { dossierSeo, resolveSeo } from "./seo";

describe("evidence listing order", () => {
  it("orders latest period, then latest result date, and leaves unknown labels last", () => {
    expect(periodRank("FY26")).toBeGreaterThan(periodRank("FY22") ?? 0);
    const rows = [
      { period: "FY22", metric: "revenue", as_of: "2022-04-13" },
      { period: "FY26", metric: "margin", as_of: "2026-04-01" },
      { period: "FY26", metric: "revenue", as_of: "2026-04-16" },
      { period: "note", metric: "revenue", as_of: "2026-04-16" },
    ].sort(compareEvidenceLatestFirst);
    expect(rows.map((r) => `${r.period}:${r.metric}:${r.as_of}`)).toEqual([
      "FY26:revenue:2026-04-16",
      "FY26:margin:2026-04-01",
      "FY22:revenue:2022-04-13",
      "note:revenue:2026-04-16",
    ]);
  });

  it("defaults to metric name, then latest period, and can filter either field", () => {
    const rows = [
      { period: "FY22", metric: "revenue_growth_cc_pct", as_of: "2022-04-13" },
      { period: "FY26", metric: "operating_margin_pct", as_of: "2026-04-01" },
      { period: "FY26", metric: "revenue_growth_cc_pct", as_of: "2026-04-16" },
      { period: "FY24", metric: "revenue_growth_cc_pct", as_of: "2024-04-18" },
      { period: "note", metric: "revenue_growth_cc_pct", as_of: "2026-04-16" },
    ];
    expect(listEvidenceRows(rows).map((r) => `${r.period}:${r.metric}`)).toEqual([
      "FY26:operating_margin_pct",
      "FY26:revenue_growth_cc_pct",
      "FY24:revenue_growth_cc_pct",
      "FY22:revenue_growth_cc_pct",
      "note:revenue_growth_cc_pct",
    ]);
    expect(
      listEvidenceRows(rows, { sort: { key: "period", dir: "desc" } }).map((r) => r.period),
    ).toEqual(["FY26", "FY26", "FY24", "FY22", "note"]);
    expect(
      listEvidenceRows(rows, { sort: { key: "period", dir: "asc" } }).map((r) => r.period),
    ).toEqual(["FY22", "FY24", "FY26", "FY26", "note"]);
    expect(
      listEvidenceRows(rows, { metric: "operating_margin_pct" }).map((r) => r.period),
    ).toEqual(["FY26"]);
    expect(listEvidenceRows(rows, { period: "FY22" })).toHaveLength(1);
    expect(
      compareEvidence(rows[2], rows[1], { key: "metric", dir: "asc" }),
    ).toBeGreaterThan(0);
  });
});

describe("promise thread heatmap", () => {
  it("reads raises, cuts, and a flat range shade", () => {
    const raised = readInYearRevision({
      metric: "revenue_growth_cc_pct",
      guided_value: 13,
      guided_low: 12,
      guided_high: 14,
      revisions: [
        { guided_low: 14, guided_high: 16 },
        { guided_low: 19.5, guided_high: 20 },
      ],
    });
    expect(raised.direction).toBe("raised");
    expect(raised.steps).toEqual(["raised", "raised"]);
    expect(raised.finalBand).toBe("19.5%–20%");
    expect(raised.path).toContain("12%–14%");

    const cut = readInYearRevision({
      metric: "revenue_growth_cc_pct",
      guided_value: 5.5,
      guided_low: 4,
      guided_high: 7,
      revisions: [{ guided_low: 1, guided_high: 2.5 }],
    });
    expect(cut.direction).toBe("cut");

    const mixed = readInYearRevision({
      metric: "revenue_growth_cc_pct",
      guided_value: 14,
      guided_low: 13,
      guided_high: 15,
      revisions: [
        { guided_low: 15, guided_high: 16 },
        { guided_low: 10, guided_high: 12 },
      ],
    });
    expect(mixed.direction).toBe("mixed");
    expect(readInYearRevision({ guided_value: 10, metric: "revenue_growth_pct" }).direction).toBe(
      "none",
    );
    expect(heatLevel(10, 0, 10)).toBe(5);
    expect(heatLevel(0, 0, 10)).toBe(1);
    expect(heatLevel(4, 4, 4)).toBe(3);
  });
});

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
