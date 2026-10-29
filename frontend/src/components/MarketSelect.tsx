import { useI18n } from "../i18n";
import { useEntitlements } from "../lib/entitlements";
import { marketOptionLabel, useMarketChoice } from "../lib/markets";

/** Topbar market picker. Writes the same preference the Screener and Workbench read. */
export default function MarketSelect() {
  const { t } = useI18n();
  const { markets, market, setMarket } = useMarketChoice();
  const { marketAccess } = useEntitlements();
  if (markets.length < 2) return null;

  return (
    <label className="lang-select market-select" title={t("common.market")}>
      <span className="sr-only">{t("common.market")}</span>
      <select
        value={market}
        data-testid="global-market-select"
        aria-label={t("common.market")}
        onChange={(e) => void setMarket(e.target.value)}
      >
        {markets.map((m) => (
          <option key={m.id} value={m.id}>
            {marketOptionLabel(m.name, marketAccess(m.id), t)}
          </option>
        ))}
      </select>
    </label>
  );
}
