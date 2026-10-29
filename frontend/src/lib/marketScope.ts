import type { Coverage } from "./api";

type Listing = { market_id?: string | null; exchange?: string | null };

export type MarketAccess = "all" | "some" | "none";

/** Mirrors `market_scope.listing_in_scope`: a dual-listed company counts under either exchange. */
export function listingInPlan(coverage: Coverage | undefined, row: Listing): boolean {
  const grants = coverage?.grants ?? [];
  if (grants.includes("*")) return true;
  const market = (row.market_id || "").toUpperCase();
  if (!market) return true;
  if (grants.includes(market)) return true;
  return (row.exchange || "")
    .toUpperCase()
    .split("+")
    .filter(Boolean)
    .some((ex) => grants.includes(`${market}:${ex}`));
}

/** Whole market, some of its exchanges, or none of it. */
export function marketAccess(coverage: Coverage | undefined, marketId: string): MarketAccess {
  const grants = coverage?.grants ?? [];
  const market = marketId.toUpperCase();
  if (grants.includes("*") || grants.includes(market)) return "all";
  return grants.some((g) => g.startsWith(`${market}:`)) ? "some" : "none";
}
