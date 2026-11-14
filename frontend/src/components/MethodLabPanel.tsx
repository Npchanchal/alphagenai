import { useEffect, useMemo, useState } from "react";
import {
  fetchMethodLab,
  runMethodLab,
  type LabBehaviour,
  type LabCatalogue,
  type LabComparisonInput,
  type LabHypotheticalRow,
  type LabMethod,
  type LabParamSpec,
  type LabParamValue,
  type LabRowScope,
  type LabRunResult,
  type LabTag,
} from "../lib/api";
import { metricDisplayName } from "../lib/score";

type Slot = {
  key: string;
  method: string;
  preset: string;
  params: Record<string, LabParamValue>;
  rollup: Record<string, LabParamValue>;
};

type Saved = { slots: Slot[]; base: string; scope: LabRowScope; hypo: LabHypotheticalRow[] };

const STORE_KEY = "citealpha.methodLab";

const TAG_TEXT: Record<LabTag, string> = {
  beat: "Beat",
  in_line: "In line",
  miss: "Miss",
  outside_range: "Outside range",
};

const STATUS_TEXT: Record<string, string> = {
  published: "Published",
  shadow: "Shadow",
  pending_ruling: "Awaiting ruling",
  alternative: "Alternative",
  change_control: "Proposal",
  research: "Research",
};

const KIND_TEXT: Record<string, string> = {
  accuracy: "Higher = closer to guidance",
  direction: "50 = on the midpoint; above = above guidance",
  hit: "Share of figures inside the range",
};

const HYPO_METRICS = [
  "revenue_growth_cc_pct",
  "revenue_growth_pct",
  "operating_margin_pct",
  "ebitda_margin_pct",
  "rd_spend_pct_of_revenue",
  "wc_days",
  "production_volume_mmt",
  "capex_usd_mn",
];

const CHECKS: { key: keyof LabBehaviour; label: string; better: "low" | "high" | null }[] = [
  { key: "gain_from_guiding_low", label: "Points gained by guiding low", better: "low" },
  { key: "best_half_width_pp", label: "Range half-width that scores best (pp)", better: null },
  { key: "one_pp_miss_at_2", label: "1-point miss on 1–3% guidance", better: null },
  { key: "one_pp_miss_at_20", label: "1-point miss on 19–21% guidance", better: null },
  { key: "alternating_record", label: "Alternating record: 2%, then 8% on 4–6%", better: null },
  { key: "steady_record", label: "Steady record: 5.5%, then 4.5% on 4–6%", better: null },
  { key: "low_growth_beat", label: "Guided 0–3%, reported 3.1%", better: null },
];

function loadSaved(): Saved | null {
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    return raw ? (JSON.parse(raw) as Saved) : null;
  } catch {
    return null;
  }
}

function fmt(v: number | null | undefined, digits = 1): string {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(digits);
}

function band(low: number, high: number): string {
  return low === high ? `${low}` : `${low}–${high}`;
}

let slotSeq = 0;
function newSlot(method: string, preset: string): Slot {
  slotSeq += 1;
  return { key: `${method}-${Date.now().toString(36)}-${slotSeq}`, method, preset, params: {}, rollup: {} };
}

/** Workbench only: every GCI scoring method side by side, each configurable. Research — nothing here is published. */
export default function MethodLabPanel() {
  const saved = useMemo(loadSaved, []);
  const [cat, setCat] = useState<LabCatalogue | null>(null);
  const [slots, setSlots] = useState<Slot[]>(saved?.slots ?? []);
  const [base, setBase] = useState<string>(saved?.base ?? "");
  const [scope, setScope] = useState<LabRowScope>(saved?.scope ?? "published");
  const [hypo, setHypo] = useState<LabHypotheticalRow[]>(saved?.hypo ?? []);
  const [active, setActive] = useState<string>("");
  const [result, setResult] = useState<LabRunResult | null>(null);
  const [detail, setDetail] = useState<string>("");
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const methodOf = (code: string): LabMethod | undefined => cat?.methods.find((m) => m.code === code);

  const applyView = (c: LabCatalogue, viewId: string) => {
    const view = c.actor_views.find((v) => v.id === viewId);
    if (!view) return;
    const next = view.comparisons.map((x) => newSlot(x.method, x.preset));
    setSlots(next);
    setBase((next.find((s) => s.method === c.base_method) ?? next[0]).key);
    setActive("");
  };

  useEffect(() => {
    void fetchMethodLab()
      .then((c) => {
        setCat(c);
        const valid = (saved?.slots ?? []).filter((s) => c.methods.some((m) => m.code === s.method));
        if (!valid.length) applyView(c, c.actor_views[0].id);
      })
      .catch((e: Error) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify({ slots, base, scope, hypo } satisfies Saved));
    } catch {
      /* private mode: the setup lasts for this page only */
    }
  }, [slots, base, scope, hypo]);

  const request = useMemo(() => {
    if (!cat || !slots.length) return null;
    const comparisons: LabComparisonInput[] = slots.map((s) => ({
      id: s.key,
      method: s.method,
      preset: s.preset,
      params: s.params,
      rollup: s.rollup,
    }));
    const typed = hypo.filter((h) => [h.low, h.high, h.actual].every((v) => Number.isFinite(v)));
    return { comparisons, row_scope: scope, hypothetical_rows: typed };
  }, [cat, slots, scope, hypo]);

  useEffect(() => {
    if (!request) return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void runMethodLab(request)
        .then((r) => {
          setResult(r);
          setErr(null);
          setDetail((d) => (d && r.companies.some((c) => c.company_id === d) ? d : r.companies[0]?.company_id ?? ""));
        })
        .catch((e: Error) => setErr(e.message))
        .finally(() => setBusy(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [request]);

  const update = (key: string, patch: Partial<Slot>) =>
    setSlots((cur) => cur.map((s) => (s.key === key ? { ...s, ...patch } : s)));

  const addSlot = () => {
    if (!cat || slots.length >= cat.max_comparisons) return;
    const m = cat.methods[0];
    const s = newSlot(m.code, m.presets[0].id);
    setSlots((cur) => [...cur, s]);
    setActive(s.key);
  };

  const duplicate = (s: Slot) => {
    if (!cat || slots.length >= cat.max_comparisons) return;
    const copy = { ...newSlot(s.method, s.preset), params: { ...s.params }, rollup: { ...s.rollup } };
    setSlots((cur) => [...cur, copy]);
    setActive(copy.key);
  };

  const remove = (key: string) => {
    setSlots((cur) => {
      const next = cur.filter((s) => s.key !== key);
      if (key === base && next.length) setBase(next[0].key);
      return next;
    });
  };

  const comparisons = result?.comparisons ?? [];
  const baseCmp = comparisons.find((c) => c.id === base) ?? comparisons[0];
  const companies = (result?.companies ?? []).filter((c) => !hidden.has(c.company_id));
  const detailCompany = result?.companies.find((c) => c.company_id === detail);

  const copyConfig = () => {
    const text = JSON.stringify({ comparisons: request?.comparisons, row_scope: scope }, null, 2);
    void navigator.clipboard
      ?.writeText(text)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => undefined);
  };

  return (
    <div className="panel desk-panel method-lab" data-testid="method-lab">
      <div className="method-lab__main">
        <h2 style={{ marginTop: 0 }}>GCI method lab</h2>
        <p className="muted">
          Every scoring method put forward for the GCI, each with its own settings. Pick a view for your role or build
          your own comparison on the right. These are research calculations: nothing here is a published level, is
          stored, or ranks a company. GCI Classic is the published method.
        </p>
        {err && <p className="error">{err}</p>}
        {busy && <p className="muted">Calculating…</p>}

        {result && (
          <section style={{ marginBottom: 20 }} data-testid="lab-levels">
            <h3>Company levels</h3>
            <p className="muted">
              Difference is read against <strong>{baseCmp?.label ?? "the base"}</strong>. For a named method, the
              engine level (revisions, lead time and commitments included, settings fixed) is shown under the lab
              level, which scores one guidance figure per period with the settings on the right.
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Figures</th>
                    {comparisons.map((c) => (
                      <th key={c.id} title={`${KIND_TEXT[c.kind]}. ${methodOf(c.method)?.formula ?? ""}`}>
                        {c.label}
                        {c.id === baseCmp?.id ? " (base)" : ""}
                        <div className="muted" style={{ fontWeight: 400, fontSize: "0.8em" }}>
                          {STATUS_TEXT[c.status] ?? c.status}
                          {c.params_changed.length
                            ? ` · edited: ${c.params_changed
                                .map((k) => methodOf(c.method)?.params.find((p) => p.key === k)?.label ?? k)
                                .join(", ")}`
                            : ""}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {companies.map((co) => {
                    const b = baseCmp ? co.levels[baseCmp.id]?.level : null;
                    return (
                      <tr key={co.company_id}>
                        <td>
                          <button type="button" className="linkish" onClick={() => setDetail(co.company_id)}>
                            {co.name ?? co.company_id}
                          </button>
                        </td>
                        <td>{co.rows_scored}</td>
                        {comparisons.map((c) => {
                          const lv = co.levels[c.id];
                          const diff = lv?.level != null && b != null && c.id !== baseCmp?.id ? lv.level - b : null;
                          return (
                            <td key={c.id}>
                              <strong>{fmt(lv?.level)}</strong>
                              {diff != null && (
                                <span className="muted">
                                  {" "}
                                  ({diff >= 0 ? "+" : ""}
                                  {diff.toFixed(1)})
                                </span>
                              )}
                              {lv?.engine_level !== undefined && lv?.engine_level !== null && (
                                <div className="muted" style={{ fontSize: "0.8em" }}>
                                  engine {fmt(lv.engine_level)}
                                </div>
                              )}
                              {lv?.audit_deduction ? (
                                <div className="muted" style={{ fontSize: "0.8em" }}>
                                  after −{fmt(lv.audit_deduction, 0)} audit flags
                                </div>
                              ) : null}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {result.companies.length === 0 && (
              <p className="muted">No company in your markets has a closed figure under this row scope.</p>
            )}
          </section>
        )}

        {detailCompany && (
          <section style={{ marginBottom: 20 }} data-testid="lab-rows">
            <h3>{detailCompany.name ?? detailCompany.company_id} — figure by figure</h3>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Metric</th>
                    <th>Opening guidance</th>
                    <th>Reported</th>
                    <th>Result</th>
                    {comparisons.map((c) => (
                      <th key={c.id}>{c.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detailCompany.rows.map((r, i) => (
                    <tr key={`${r.period}-${r.metric}-${i}`}>
                      <td>{r.period}</td>
                      <td>{metricDisplayName(r.metric)}</td>
                      <td>
                        {band(r.low, r.high)}
                        {r.revisions ? <span className="muted"> · {r.revisions} revisions</span> : null}
                      </td>
                      <td>{r.actual}</td>
                      <td>
                        {TAG_TEXT[r.tag]}
                        {!r.published_eligible && <div className="muted">awaiting citation or review</div>}
                      </td>
                      {comparisons.map((c) => {
                        const b = r.bands[c.id];
                        const scored = r.scores[c.id];
                        return (
                          <td key={c.id} title={r.reasons[c.id] ?? undefined}>
                            {fmt(scored)}
                            {b && (b[0] !== r.low || b[1] !== r.high) && (
                              <div className="muted" style={{ fontSize: "0.8em" }}>
                                on {band(b[0], b[1])}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {result?.hypothetical && result.hypothetical.rows.length > 0 && (
          <section style={{ marginBottom: 20 }} data-testid="lab-hypothetical">
            <h3>Typed-in figures</h3>
            <p className="muted">Your own numbers, scored under each configuration. Not company data.</p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Guided</th>
                    <th>Reported</th>
                    <th>Result</th>
                    {comparisons.map((c) => (
                      <th key={c.id}>{c.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.hypothetical.rows.map((r, i) => (
                    <tr key={i}>
                      <td>{metricDisplayName(r.metric)}</td>
                      <td>
                        {r.bound ? `${r.bound === "floor" ? "at least" : "at most"} ` : ""}
                        {band(r.low, r.high)}
                      </td>
                      <td>{r.actual}</td>
                      <td>{TAG_TEXT[r.tag]}</td>
                      {comparisons.map((c) => (
                        <td key={c.id} title={r.reasons[c.id] ?? undefined}>
                          {fmt(r.scores[c.id])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {result?.behaviour && cat && (
          <section style={{ marginBottom: 20 }} data-testid="lab-behaviour">
            <h3>How each configuration behaves</h3>
            <p className="muted">
              Tests from the 12 Nov algorithm scan, on a growth figure whose true expectation is{" "}
              {cat.checks.expected_growth_pct}% with a {cat.checks.spread_pp}-point spread. An honest 80% range is ±
              {cat.checks.honest_half_width_pp} points. A method that pays for guiding low ranks sandbaggers first.
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Check</th>
                    {comparisons.map((c) => (
                      <th key={c.id}>{c.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CHECKS.map((chk) => (
                    <tr key={chk.key}>
                      <td>{chk.label}</td>
                      {comparisons.map((c) => {
                        const b = result.behaviour?.[c.id];
                        if (!b) return <td key={c.id}>—</td>;
                        if (chk.key === "best_half_width_pp") {
                          const w = b.best_half_width_pp;
                          return (
                            <td key={c.id}>
                              {b.width_ignored ? "Width ignored" : w != null && w >= 6 ? "Widest tested" : `±${fmt(w, 2)}`}
                            </td>
                          );
                        }
                        const v = b[chk.key] as number | null;
                        const warn = chk.better === "low" && v != null && v > 0.5;
                        return (
                          <td key={c.id} style={warn ? { color: "var(--bad)", fontWeight: 600 } : undefined}>
                            {chk.key === "gain_from_guiding_low" && v != null && v > 0 ? "+" : ""}
                            {fmt(v)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>

      <aside className="method-lab__side" aria-label="Method configuration" data-testid="lab-config">
        <h3 style={{ marginTop: 0 }}>Configuration</h3>
        {cat && (
          <>
            <label className="method-lab__field">
              <span>View for</span>
              <select
                defaultValue=""
                onChange={(e) => {
                  if (e.target.value) applyView(cat, e.target.value);
                  e.target.value = "";
                }}
              >
                <option value="">Choose a role…</option>
                {cat.actor_views.map((v) => (
                  <option key={v.id} value={v.id} title={v.question}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="method-lab__field">
              <span>Rows read</span>
              <select value={scope} onChange={(e) => setScope(e.target.value as LabRowScope)}>
                {cat.row_scopes.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            {result && result.companies.length > 1 && (
              <fieldset className="method-lab__fieldset">
                <legend>Companies shown</legend>
                {result.companies.map((c) => (
                  <label key={c.company_id} className="method-lab__check">
                    <input
                      type="checkbox"
                      checked={!hidden.has(c.company_id)}
                      onChange={(e) =>
                        setHidden((cur) => {
                          const next = new Set(cur);
                          if (e.target.checked) next.delete(c.company_id);
                          else next.add(c.company_id);
                          return next;
                        })
                      }
                    />
                    {c.name ?? c.company_id}
                  </label>
                ))}
              </fieldset>
            )}

            <h4>
              Comparisons ({slots.length}/{cat.max_comparisons})
            </h4>
            {slots.map((s) => {
              const m = methodOf(s.method);
              if (!m) return null;
              const open = active === s.key;
              const preset = m.presets.find((p) => p.id === s.preset) ?? m.presets[0];
              return (
                <div key={s.key} className={`method-lab__slot${open ? " is-open" : ""}`}>
                  <div className="method-lab__slot-head">
                    <button
                      type="button"
                      className="linkish"
                      aria-expanded={open}
                      onClick={() => setActive(open ? "" : s.key)}
                    >
                      {m.name} · {preset.label}
                      {Object.keys(s.params).length || Object.keys(s.rollup).length ? " (edited)" : ""}
                    </button>
                    <label className="method-lab__check" title="Read every other column against this one">
                      <input type="radio" name="lab-base" checked={base === s.key} onChange={() => setBase(s.key)} />
                      Base
                    </label>
                  </div>
                  {open && (
                    <SlotEditor
                      slot={s}
                      method={m}
                      methods={cat.methods}
                      rollupSpecs={cat.rollup_params}
                      onChange={(patch) => update(s.key, patch)}
                      onDuplicate={() => duplicate(s)}
                      onRemove={slots.length > 1 ? () => remove(s.key) : undefined}
                    />
                  )}
                </div>
              );
            })}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0 16px" }}>
              <button type="button" className="btn-ghost" onClick={addSlot} disabled={slots.length >= cat.max_comparisons}>
                Add comparison
              </button>
              <button type="button" className="btn-ghost" onClick={copyConfig}>
                {copied ? "Copied" : "Copy configuration"}
              </button>
            </div>

            <h4>Typed-in figures</h4>
            <p className="muted" style={{ fontSize: "0.85em" }}>
              Try a promise and a result of your own. Scored under every comparison; never stored.
            </p>
            {hypo.map((h, i) => (
              <div key={i} className="method-lab__hypo">
                <select
                  value={h.metric}
                  aria-label="Metric"
                  onChange={(e) => setHypo((cur) => cur.map((x, j) => (j === i ? { ...x, metric: e.target.value } : x)))}
                >
                  {HYPO_METRICS.map((id) => (
                    <option key={id} value={id}>
                      {metricDisplayName(id)}
                    </option>
                  ))}
                </select>
                {(["low", "high", "actual"] as const).map((k) => (
                  <label key={k} className="method-lab__mini">
                    <span>{k === "actual" ? "Reported" : k === "low" ? "Low" : "High"}</span>
                    <input
                      type="number"
                      step="any"
                      value={Number.isFinite(h[k]) ? h[k] : ""}
                      onChange={(e) =>
                        setHypo((cur) =>
                          cur.map((x, j) => (j === i ? { ...x, [k]: e.target.value === "" ? NaN : Number(e.target.value) } : x)),
                        )
                      }
                    />
                  </label>
                ))}
                <button type="button" className="linkish" onClick={() => setHypo((cur) => cur.filter((_, j) => j !== i))}>
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              className="btn-ghost"
              disabled={hypo.length >= 20}
              onClick={() => setHypo((cur) => [...cur, { metric: "revenue_growth_cc_pct", low: 4, high: 6, actual: 5 }])}
            >
              Add a figure
            </button>
          </>
        )}
      </aside>
    </div>
  );
}

function ParamControl({
  spec,
  value,
  edited,
  onChange,
  onReset,
}: {
  spec: LabParamSpec;
  value: LabParamValue;
  edited: boolean;
  onChange: (v: LabParamValue) => void;
  onReset: () => void;
}) {
  const reset = edited ? (
    <button type="button" className="linkish" onClick={onReset} style={{ fontSize: "0.8em" }}>
      reset
    </button>
  ) : null;
  if (spec.kind === "toggle") {
    return (
      <label className="method-lab__check" title={spec.help}>
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        {spec.label} {reset}
      </label>
    );
  }
  if (spec.kind === "choice") {
    return (
      <label className="method-lab__field" title={spec.help}>
        <span>
          {spec.label} {reset}
        </span>
        <select value={String(value)} onChange={(e) => onChange(e.target.value)}>
          {(spec.options ?? []).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
    );
  }
  const num = Number(value);
  return (
    <div className="method-lab__field" title={spec.help}>
      <span>
        {spec.label} {reset}
      </span>
      <div className="method-lab__range">
        <input
          type="range"
          min={spec.min}
          max={spec.max}
          step={spec.step}
          value={num}
          aria-label={spec.label}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <input
          type="number"
          min={spec.min}
          max={spec.max}
          step={spec.step}
          value={num}
          aria-label={`${spec.label} value`}
          onChange={(e) => e.target.value !== "" && onChange(Number(e.target.value))}
        />
      </div>
      <small className="muted">
        {spec.min}–{spec.max}
        {spec.unit ? ` ${spec.unit}` : ""}
        {spec.help ? ` · ${spec.help}` : ""}
      </small>
    </div>
  );
}

function SlotEditor({
  slot,
  method,
  methods,
  rollupSpecs,
  onChange,
  onDuplicate,
  onRemove,
}: {
  slot: Slot;
  method: LabMethod;
  methods: LabMethod[];
  rollupSpecs: LabParamSpec[];
  onChange: (patch: Partial<Slot>) => void;
  onDuplicate: () => void;
  onRemove?: () => void;
}) {
  const preset = method.presets.find((p) => p.id === slot.preset) ?? method.presets[0];
  const paramValue = (spec: LabParamSpec): LabParamValue =>
    slot.params[spec.key] ?? preset.params[spec.key] ?? spec.default;
  const rollupValue = (spec: LabParamSpec): LabParamValue =>
    slot.rollup[spec.key] ?? method.rollup_defaults[spec.key] ?? spec.default;
  const without = (obj: Record<string, LabParamValue>, key: string) => {
    const next = { ...obj };
    delete next[key];
    return next;
  };

  return (
    <div className="method-lab__editor">
      <label className="method-lab__field">
        <span>Method</span>
        <select
          value={slot.method}
          onChange={(e) => {
            const m = methods.find((x) => x.code === e.target.value);
            if (m) onChange({ method: m.code, preset: m.presets[0].id, params: {}, rollup: {} });
          }}
        >
          {methods.map((m) => (
            <option key={m.code} value={m.code}>
              {m.name} ({m.version}) — {STATUS_TEXT[m.status] ?? m.status}
            </option>
          ))}
        </select>
      </label>
      <p className="muted" style={{ fontSize: "0.85em", margin: "4px 0 8px" }}>
        {method.summary} <span style={{ fontFamily: "var(--mono)" }}>{method.formula}</span>
      </p>
      <label className="method-lab__field">
        <span>Preset</span>
        <select value={slot.preset} onChange={(e) => onChange({ preset: e.target.value, params: {} })}>
          {method.presets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      {method.params.map((spec) => (
        <ParamControl
          key={spec.key}
          spec={spec}
          value={paramValue(spec)}
          edited={spec.key in slot.params}
          onChange={(v) => onChange({ params: { ...slot.params, [spec.key]: v } })}
          onReset={() => onChange({ params: without(slot.params, spec.key) })}
        />
      ))}
      <details>
        <summary>Roll-up to a company level</summary>
        {rollupSpecs.map((spec) => (
          <ParamControl
            key={spec.key}
            spec={spec}
            value={rollupValue(spec)}
            edited={spec.key in slot.rollup}
            onChange={(v) => onChange({ rollup: { ...slot.rollup, [spec.key]: v } })}
            onReset={() => onChange({ rollup: without(slot.rollup, spec.key) })}
          />
        ))}
      </details>
      <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
        <button type="button" className="linkish" onClick={onDuplicate}>
          Duplicate
        </button>
        {onRemove && (
          <button type="button" className="linkish" onClick={onRemove}>
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
