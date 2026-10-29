import { useEffect, useState } from "react";
import type { CoverageUnit } from "../lib/api";

type Props = {
  units: CoverageUnit[];
  grants: string[];
  onSave: (grants: string[]) => Promise<unknown>;
  testId?: string;
};

/** Platform billing sets the markets a desk bought: all, whole markets, or single exchanges. */
export default function CoverageEditor({ units, grants, onSave, testId = "coverage-editor" }: Props) {
  const [picked, setPicked] = useState<Set<string>>(new Set(grants));
  const [busy, setBusy] = useState(false);

  useEffect(() => setPicked(new Set(grants)), [grants]);

  const all = picked.has("*");
  const toggle = (id: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const box = (id: string, label: string, disabled = false) => (
    <label key={id} style={{ display: "block", fontSize: 13 }}>
      <input
        type="checkbox"
        checked={picked.has(id)}
        disabled={disabled || busy}
        onChange={() => toggle(id)}
        data-testid={`${testId}-${id}`}
      />{" "}
      {label}
    </label>
  );

  return (
    <details data-testid={testId}>
      <summary>Edit markets</summary>
      {box("*", "All markets and exchanges")}
      {units.map((u) => (
        <div key={u.id} style={{ marginLeft: 8 }}>
          {box(u.market_id, `${u.label} (whole market)`, all)}
          {u.exchanges.length > 1 && (
            <div style={{ marginLeft: 16 }}>
              {u.exchanges.map((x) => box(x.id, `${x.exchange} only`, all || picked.has(u.market_id)))}
            </div>
          )}
        </div>
      ))}
      <button
        type="button"
        className="btn-ghost"
        disabled={busy || picked.size === 0}
        data-testid={`${testId}-save`}
        onClick={() => {
          setBusy(true);
          void onSave(all ? ["*"] : [...picked]).finally(() => setBusy(false));
        }}
      >
        Save markets
      </button>
    </details>
  );
}
