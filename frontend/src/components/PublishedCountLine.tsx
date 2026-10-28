import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { fetchProductMeta, type ProductMeta } from "../lib/api";

let pending: Promise<ProductMeta> | null = null;

function loadMeta(): Promise<ProductMeta> {
  if (!pending) {
    pending = fetchProductMeta().catch((err) => {
      pending = null;
      throw err;
    });
  }
  return pending;
}

/** The one published-GCI count the homepage, screener, snapshot, and Filing Search all print. */
export default function PublishedCountLine({ meta }: { meta?: ProductMeta | null }) {
  const { t } = useI18n();
  const [loaded, setLoaded] = useState<ProductMeta | null>(meta ?? null);

  useEffect(() => {
    if (meta) {
      setLoaded(meta);
      return;
    }
    let cancelled = false;
    void loadMeta()
      .then((row) => !cancelled && setLoaded(row))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [meta]);

  if (loaded?.published_gci_count == null) return null;
  return (
    <p className="muted published-count" data-testid="published-count">
      {t("published.sentence", {
        count: loaded.published_gci_count,
        ranked: loaded.published_ranked_count ?? 0,
      })}
    </p>
  );
}
