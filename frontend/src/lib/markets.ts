import { useCallback, useEffect, useState } from "react";
import {
  fetchMarketIndexes,
  fetchMarkets,
  withRateLimitRetry,
  type Market,
  type MarketIndex,
} from "./api";
import { useAuth } from "./auth";
import type { MarketAccess } from "./marketScope";

export const HOME_MARKET = "IN";

const FALLBACK: Market[] = [
  { id: HOME_MARKET, name: "India", currency: "INR", timezone: "Asia/Kolkata", listed: true },
];

let listedMarkets: Promise<Market[]> | null = null;

/** Markets whose rows come from a published listing. Placeholder markets never reach a picker. */
export function loadListedMarkets(): Promise<Market[]> {
  if (!listedMarkets) {
    listedMarkets = withRateLimitRetry(fetchMarkets)
      .then((r) => {
        const rows = r.markets.filter((m) => m.listed);
        return rows.length ? rows : FALLBACK;
      })
      .catch(() => {
        listedMarkets = null;
        return FALLBACK;
      });
  }
  return listedMarkets;
}

/** Picker text: the market name, marked when a seat's plan covers none or part of it. */
export function marketOptionLabel(name: string, access: MarketAccess, t: (key: string) => string): string {
  if (access === "none") return `${name} · ${t("scope.outsidePlan")}`;
  if (access === "some") return `${name} · ${t("scope.partOfPlan")}`;
  return name;
}

export function listedIndexes(indexes: MarketIndex[]): MarketIndex[] {
  return indexes.filter((ix) => ix.listed !== false);
}

/**
 * The site-wide market: the `default_market` preference, held to listed markets.
 * Choosing a market also moves `default_index` to an index of that market, so
 * every page that reads preferences (Screener, Filing Search, Workbench) follows.
 */
export function useMarketChoice() {
  const { preferences, updatePreferences } = useAuth();
  const [markets, setMarkets] = useState<Market[]>(FALLBACK);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void loadListedMarkets().then((rows) => {
      if (cancelled) return;
      setMarkets(rows);
      setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const wanted = (preferences?.default_market || HOME_MARKET).toUpperCase();
  const market = markets.some((m) => m.id === wanted) ? wanted : HOME_MARKET;

  const setMarket = useCallback(
    async (next: string) => {
      let nextIndex: string | undefined;
      try {
        const r = await fetchMarketIndexes(next);
        const rows = listedIndexes(r.indexes);
        nextIndex = (rows.find((ix) => ix.id === preferences?.default_index) ?? rows[0])?.id;
      } catch {
        /* keep the stored index; the page falls back to the market's first index */
      }
      await updatePreferences({
        default_market: next,
        ...(nextIndex ? { default_index: nextIndex } : {}),
      });
    },
    [preferences?.default_index, updatePreferences],
  );

  return { markets, market, setMarket, ready };
}
