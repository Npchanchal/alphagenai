import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, fetchEntitlementsMe, type CompanySummary, type Entitlements } from "./api";
import { useAuth } from "./auth";
import { listingInPlan, marketAccess, type MarketAccess } from "./marketScope";

const GUEST: Entitlements = {
  plan: "guest",
  role: "guest",
  kind: "guest",
  features: ["tracker"],
  limits: { companies_viewed: 15, chat: 0 },
  source: "guest",
};

type Ctx = {
  entitlements: Entitlements;
  has: (feature: string) => boolean;
  /** A seat (not a guest) whose plan covers some markets, not all. */
  scoped: boolean;
  /** Seat tools open on this company. Published GCI reads stay open regardless. */
  inPlan: (row: Pick<CompanySummary, "market_id" | "exchange">) => boolean;
  marketAccess: (marketId: string) => MarketAccess;
  loading: boolean;
  refresh: () => Promise<void>;
};

const EntitlementsContext = createContext<Ctx | null>(null);

export function EntitlementsProvider({ children }: { children: ReactNode }) {
  const { user, token } = useAuth();
  const [entitlements, setEntitlements] = useState<Entitlements>(GUEST);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      let row: Entitlements | null = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          row = await fetchEntitlementsMe();
          break;
        } catch (e) {
          const status = e instanceof ApiError ? e.status : 0;
          if (status === 429 && attempt < 2) {
            await new Promise((resolve) => window.setTimeout(resolve, 1500 * (attempt + 1)));
            continue;
          }
          if (status === 429) return;
          throw e;
        }
      }
      if (row) setEntitlements(row);
    } catch {
      setEntitlements(GUEST);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, user?.id, user?.role, token]);

  const has = useCallback(
    (feature: string) => (entitlements.features || []).includes(feature),
    [entitlements.features],
  );

  const scope = useMemo(() => scopeHelpers(entitlements), [entitlements]);

  const value = useMemo(
    () => ({ entitlements, has, ...scope, loading, refresh }),
    [entitlements, has, scope, loading, refresh],
  );

  return (
    <EntitlementsContext.Provider value={value}>{children}</EntitlementsContext.Provider>
  );
}

function scopeHelpers(ent: Entitlements) {
  const seat = (ent.source || "guest") !== "guest";
  const coverage = ent.coverage;
  return {
    scoped: seat && !!coverage && !coverage.all,
    inPlan: (row: Pick<CompanySummary, "market_id" | "exchange">) => !seat || listingInPlan(coverage, row),
    marketAccess: (marketId: string): MarketAccess => (seat ? marketAccess(coverage, marketId) : "all"),
  };
}

export function useEntitlements(): Ctx {
  const ctx = useContext(EntitlementsContext);
  if (!ctx) {
    return {
      entitlements: GUEST,
      has: (f) => GUEST.features.includes(f),
      ...scopeHelpers(GUEST),
      loading: false,
      refresh: async () => {},
    };
  }
  return ctx;
}
