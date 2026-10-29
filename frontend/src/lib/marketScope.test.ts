import { describe, expect, it } from "vitest";
import type { Coverage } from "./api";
import { listingInPlan, marketAccess } from "./marketScope";

const scope = (grants: string[]): Coverage => ({
  grants,
  all: grants.includes("*"),
  markets: [],
  exchanges: {},
  label: "",
});

describe("market scope", () => {
  it("counts a dual-listed company under either exchange", () => {
    expect(listingInPlan(scope(["IN:NSE"]), { market_id: "IN", exchange: "NSE+BSE" })).toBe(true);
    expect(listingInPlan(scope(["IN:NSE"]), { market_id: "IN", exchange: "BSE" })).toBe(false);
  });

  it("keeps markets apart", () => {
    expect(listingInPlan(scope(["IN"]), { market_id: "US", exchange: "US" })).toBe(false);
    expect(listingInPlan(scope(["*"]), { market_id: "US", exchange: "US" })).toBe(true);
    expect(listingInPlan(undefined, { market_id: "IN", exchange: "NSE" })).toBe(false);
  });

  it("reads a market as whole, partial, or absent", () => {
    expect(marketAccess(scope(["IN:BSE", "US"]), "IN")).toBe("some");
    expect(marketAccess(scope(["IN:BSE", "US"]), "US")).toBe("all");
    expect(marketAccess(scope(["IN"]), "US")).toBe("none");
  });
});
