import { useEffect, useState } from "react";
import {
  fetchCompanionIndexes,
  fetchCoreDetail,
  fetchCoreFamily,
  fetchCoreMarketProfiles,
  fetchCoreReadiness,
  fetchCoreShadow,
  fetchIndexMethodology,
  type CompanionIndexes,
  type CoreDetail,
  type CoreFamilyEvidence,
  type CoreMarketProfile,
  type CoreReleaseGates,
  type CoreRuleset,
  type CoreShadowRow,
  type GciMethod,
  type GciMethodStatus,
} from "../lib/api";
import { metricDisplayName } from "../lib/score";

const REASON_TEXT: Record<string, string> = {
  PENDING_GUIDANCE_CITE: "Promise quote not yet cited",
  UNREVIEWED: "Awaiting reviewer sign-off",
  OUTCOME_NOT_DUE: "Result not yet reported",
  WITHDRAWN: "Guidance withdrawn",
  NO_ELIGIBLE_PROMISE: "No numeric promise",
  FUTURE_SOURCE: "Promise dated after the result",
  QUOTE_OFFSET_MISMATCH: "Quote not found in the filing",
  ACCOUNTING_BASIS_MISMATCH: "Guided and reported on different bases",
  UNIT_CONVERSION_ERROR: "Guided and reported in different units",
  SCOPE_MISMATCH: "Guided and reported for different scopes",
  ZERO_REFERENCE_UNAVAILABLE: "Guided at zero with no prior-period figure",
  GUIDANCE_AFTER_PERIOD_END: "First given after the period closed",
  LATE_GUIDANCE_FLAG: "First given within 30 days of period end",
  CONDITION_NOT_ACTIVATED: "Condition not met",
  CONDITION_UNKNOWN: "Condition not yet known",
  AMBIGUOUS_DIRECTION: "Direction unclear",
  UNAPPROVED_ENGINE: "Shadow method — not published",
  REGIME_ADAPTER_PENDING: "Accounting regime not yet supported",
  MARKET_DIAGNOSTIC_ONLY: "Market has too little forward guidance",
  ISSUANCE_TIME_UNKNOWN: "Guidance date missing",
  PERIOD_END_UNKNOWN: "Period not recognised",
  REVISION_MAGNITUDE_UNAVAILABLE: "Revision size not measurable",
  OUTCOME_UNRESOLVED: "Outcome not yet evidenced",
  SUPERSEDED: "Replaced by a newer commitment",
  AMBIGUOUS_ACCEPTANCE_EVENT: "Deadline unclear",
  SAME_DAY_CONFLICT: "Two statements on the same day disagree",
  BASIS_SWITCH: "Reporting basis changed from the prior period",
  THIN_HISTORY: "Fewer than two closed periods",
  ACTUAL_UNAVAILABLE: "Results deadline passed; reported figure not yet captured",
  PRE_PERIOD_GUIDANCE: "Given before the period began",
  SCALE_FLOOR_APPLIED: "Growth miss read against a 5-point floor",
};

const METHOD_STATUS_TEXT: Record<GciMethodStatus, string> = {
  published: "Published",
  shadow: "Shadow, not published",
  pending_ruling: "Awaiting methodology ruling",
  alternative: "Alternative view",
  change_control: "Proposal",
  retired: "Retired",
};

const METHOD_KEY = "citealpha.gciMethod";

function storedRuleset(): CoreRuleset | null {
  try {
    return (window.localStorage.getItem(METHOD_KEY) as CoreRuleset | null) || null;
  } catch {
    return null;
  }
}

const LINK_BUTTON = {
  background: "none",
  border: "none",
  padding: 0,
  color: "inherit",
  font: "inherit",
  textDecoration: "underline",
  cursor: "pointer",
} as const;

const STATE_TEXT: Record<string, string> = {
  DOCUMENT_AVAILABLE: "Filing held",
  EXTRACTED: "Read, awaiting review",
  REVIEWER_ACCEPTED: "Reviewed",
  SCORE_COMPUTED: "Scored (shadow)",
  PUBLISHED: "Published",
};

const BASIS_TEXT: Record<string, string> = {
  quant_and_qual: "80% numeric guidance, 20% commitments",
  quant_only: "numeric guidance only",
  qual_only: "commitments only",
};

function level(point: number | null, low: number | null, high: number | null): string {
  if (point !== null) return `${point}`;
  if (low !== null && high !== null) return `${low}–${high}`;
  return "—";
}

const STATUS_TEXT: Record<string, string> = {
  publish: "Publishes after review",
  shadow: "Shadow only",
  diagnostic_only: "Diagnostics only",
};

function reason(code: string | null | undefined): string {
  if (!code) return "—";
  return REASON_TEXT[code] ?? code.toLowerCase().replace(/_/g, " ");
}

function band(low: number, high: number): string {
  return low === high ? `${low}` : `${low}–${high}`;
}

/** Workbench only: GCI Core rulesets and companion indexes beside the published level. Nothing here is a published number. */
export default function CorePreviewPanel({ companyId }: { companyId: string }) {
  const [ruleset, setRuleset] = useState<CoreRuleset>(() => storedRuleset() ?? "v2.4");
  const [methods, setMethods] = useState<GciMethod[]>([]);
  const [detail, setDetail] = useState<CoreDetail | null>(null);
  const [companions, setCompanions] = useState<CompanionIndexes | null>(null);
  const [gates, setGates] = useState<CoreReleaseGates | null>(null);
  const [evidence, setEvidence] = useState<CoreFamilyEvidence | null>(null);
  const [shadow, setShadow] = useState<CoreShadowRow[]>([]);
  const [markets, setMarkets] = useState<CoreMarketProfile[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void fetchCoreShadow()
      .then((r) => setShadow(r.rows.filter((x) => x.v4_gci !== null || x.core_gci !== null)))
      .catch((e: Error) => setErr(e.message));
    void fetchCoreMarketProfiles()
      .then((r) => setMarkets(r.markets))
      .catch(() => setMarkets([]));
    void fetchIndexMethodology()
      .then((m) => {
        setMethods(m.methods);
        setRuleset((cur) => (m.methods.some((x) => x.ruleset === cur) ? cur : m.default_ruleset));
      })
      .catch(() => setMethods([]));
  }, []);

  const chooseMethod = (rs: CoreRuleset) => {
    setRuleset(rs);
    try {
      window.localStorage.setItem(METHOD_KEY, rs);
    } catch {
      /* private mode: the choice lasts for this page only */
    }
  };
  const published = methods.find((m) => m.status === "published");
  const comparable = methods.filter((m) => m.ruleset !== null);
  const nameOf = (rs: CoreRuleset | null) => methods.find((m) => m.ruleset === rs)?.name;

  useEffect(() => {
    if (!companyId) return;
    setDetail(null);
    setEvidence(null);
    void fetchCoreDetail(companyId, ruleset)
      .then(setDetail)
      .catch((e: Error) => setErr(e.message));
    void fetchCoreReadiness(companyId, ruleset)
      .then(setGates)
      .catch(() => setGates(null));
  }, [companyId, ruleset]);

  useEffect(() => {
    if (!companyId) return;
    setCompanions(null);
    void fetchCompanionIndexes(companyId)
      .then(setCompanions)
      .catch(() => setCompanions(null));
  }, [companyId]);

  const openFamily = (familyId: string) => {
    void fetchCoreFamily(companyId, familyId, ruleset)
      .then(setEvidence)
      .catch((e: Error) => setErr(e.message));
  };
  const selected = comparable.find((m) => m.ruleset === ruleset);

  return (
    <div className="panel desk-panel" data-testid="core-preview">
      <h2 style={{ marginTop: 0 }}>GCI methods — side by side</h2>
      <p className="muted">
        {published ? `${published.label} is the published level. ` : ""}
        The methods below are comparisons, not published levels. Published scores change method only after review
        and a methodology entry.
      </p>
      <div
        role="group"
        aria-label="GCI method"
        data-testid="gci-method-picker"
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}
      >
        {comparable.map((m) => (
          <button
            key={m.code}
            type="button"
            className={m.ruleset === ruleset ? "btn-primary" : "btn-ghost"}
            aria-pressed={m.ruleset === ruleset}
            title={`${m.label} · ${METHOD_STATUS_TEXT[m.status]}`}
            onClick={() => m.ruleset && chooseMethod(m.ruleset)}
          >
            {m.name} <span style={{ opacity: 0.75, fontWeight: 400 }}>{m.version}</span>
          </button>
        ))}
      </div>
      {selected && (
        <p className="muted" data-testid="gci-method-note">
          <strong>{selected.label}</strong> · {METHOD_STATUS_TEXT[selected.status]}. {selected.summary}
        </p>
      )}
      {err && <p className="error">{err}</p>}

      {detail && (
        <section style={{ marginBottom: 20 }}>
          <h3>{detail.name || detail.company_id}</h3>
          <p>
            {detail.method?.name ?? "Core"} level{" "}
            <strong>
              {detail.headline === "quant"
                ? detail.quant_gci ?? "—"
                : level(detail.composite_gci, detail.composite_low, detail.composite_high)}
            </strong>
            {detail.headline === "quant"
              ? " (numeric guidance)"
              : detail.composite_basis
                ? ` (${BASIS_TEXT[detail.composite_basis]})`
                : ""}
            {detail.confidence_tier ? ` · ${detail.confidence_tier}` : ""} · {detail.closed_periods} closed
            periods · {reason(detail.publication_reason)}
          </p>
          <p className="muted">
            Numeric guidance {detail.quant_gci ?? "—"} · Commitments{" "}
            {level(detail.qual_gci, detail.qual_low, detail.qual_high)}.{" "}
            {detail.headline_rule === "QUANT_DOMINANT"
              ? `Commitments join the level at 3 with evidence covering half of those due, and none past its deadline unresolved (now ${detail.qual.coverage.qual_commitment_count} of ${detail.qual.coverage.expected_family_count}, ${detail.qual.coverage.unresolved} unresolved).`
              : detail.headline === "quant"
                ? "Commitments are shown, not blended into the level."
                : "The 80/20 split is not yet calibrated."}
          </p>
          <p className="muted">
            {detail.coverage.families_computable} of {detail.coverage.families_quant} numeric figures scored
            {detail.coverage.families_total > detail.coverage.families_quant
              ? ` (${detail.coverage.families_total - detail.coverage.families_quant} not yet scorable)`
              : ""}
            {detail.company_flags.length ? ` · ${detail.company_flags.map(reason).join("; ")}` : ""}
            {detail.uncertainty.source ? ` · range from ${detail.uncertainty.source}` : ""}
          </p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Metric</th>
                  <th>Opening guidance</th>
                  <th>Revisions</th>
                  <th>Actual</th>
                  <th>Lead time</th>
                  <th>Score</th>
                  <th>Stage</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {detail.families.map((f, i) => {
                  const opening = f.vintages[0];
                  return (
                    <tr key={`${f.parameter}-${f.period}-${i}`}>
                      <td>{f.period}</td>
                      <td>{metricDisplayName(f.parameter)}</td>
                      <td>{opening ? band(opening.low, opening.high) : "—"}</td>
                      <td>
                        {f.vintages.length > 1
                          ? `${f.vintages.length - 1} (${f.revisions_counted ?? 0} in period${
                              f.revisions_weighted != null ? `, weighted ${f.revisions_weighted}` : ""
                            })`
                          : "—"}
                      </td>
                      <td>{f.actual_value ?? "—"}</td>
                      <td>
                        {f.lead_time_days != null
                          ? `${f.lead_time_days} days${f.lead_time_factor != null ? ` × ${f.lead_time_factor}` : ""}`
                          : "—"}
                      </td>
                      <td>
                        {f.score != null ? (
                          <button type="button" style={LINK_BUTTON} onClick={() => openFamily(f.family_id)}>
                            {f.score}
                          </button>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>{f.record_state ? STATE_TEXT[f.record_state] ?? f.record_state : "—"}</td>
                      <td>{[f.reason_code, ...f.flags].filter(Boolean).map(reason).join("; ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {evidence && (
        <section style={{ marginBottom: 20 }} data-testid="core-evidence">
          <h3>
            Evidence — {metricDisplayName(evidence.family.parameter)} {evidence.family.period}
          </h3>
          <ul>
            {evidence.evidence.vintages.map((v, i) => (
              <li key={v.vintage_id}>
                {i === 0 ? "Opening guidance" : `Revision ${i}`}: {v.quote ?? "—"}{" "}
                {v.source_url ? (
                  <a href={v.source_url} target="_blank" rel="noreferrer">
                    source
                  </a>
                ) : null}
                {v.stored ? ` · filed ${v.filing_date ?? "—"} · held since ${v.ingested_at ?? "—"}` : " · copy not held"}
              </li>
            ))}
            {evidence.evidence.actual && (
              <li>
                Reported: {evidence.evidence.actual.quote ?? "—"}{" "}
                {evidence.evidence.actual.source_url ? (
                  <a href={evidence.evidence.actual.source_url} target="_blank" rel="noreferrer">
                    source
                  </a>
                ) : null}
              </li>
            )}
          </ul>
          <p className="muted">
            Reviewed by {evidence.evidence.reviewed_by ?? "—"} on {evidence.evidence.reviewed_at ?? "—"}.
          </p>
        </section>
      )}

      {companions && (
        <section style={{ marginBottom: 20 }} data-testid="companion-indexes">
          <h3>Companion indexes (preview)</h3>
          <p className="muted">
            Each measures one thing a delivery score should not blend in. Not ranked and not part of any published
            GCI; no reading below {companions.indexes[0]?.min_rows ?? 3} closed figures.
          </p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Index</th>
                  <th>Reading</th>
                  <th>What it shows</th>
                  <th>Moved out of the GCI</th>
                </tr>
              </thead>
              <tbody>
                {companions.indexes.map((c) => (
                  <tr key={c.id}>
                    <td title={c.question}>{c.name}</td>
                    <td>{level(c.value, c.low ?? null, c.high ?? null)}</td>
                    <td>{c.sentence}</td>
                    <td className="muted">{c.replaces}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(() => {
            const d = companions.diagnostics;
            const lines = [
              ...d.withdrawals.map((w) => `${metricDisplayName(w.parameter)} ${w.period}: guidance withdrawn`),
              ...d.reinstatements.map(
                (r) => `${metricDisplayName(r.parameter)}: withdrawn ${r.withdrawn}, given again ${r.reinstated}`,
              ),
              ...d.basis_switches.map(
                (b) =>
                  `${metricDisplayName(b.parameter)}: ${b.from_basis.replace(/_/g, " ")} in ${b.from_period}, ` +
                  `${b.to_basis.replace(/_/g, " ")} in ${b.to_period}`,
              ),
              ...d.deadline_extensions.map(
                (e) => `${e.subject}: deadline moved from ${e.old_deadline ?? "—"} to ${e.new_deadline ?? "—"}`,
              ),
            ];
            return (
              <>
                {lines.length > 0 && (
                  <ul>
                    {lines.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                )}
                {d.thin_history.thin && <p className="muted">{d.thin_history.policy}</p>}
              </>
            );
          })()}
        </section>
      )}

      {gates && (
        <section style={{ marginBottom: 20 }} data-testid="core-gates">
          <h3>Release gates</h3>
          <p className="muted">
            {gates.passed
              ? "Every gate has passed; a second reviewer may approve publication."
              : `${gates.failed.length} of ${gates.gates.length} gates open. Nothing publishes until all pass and a second reviewer approves.`}
          </p>
          <ul>
            {gates.gates.map((g) => (
              <li key={g.id}>
                {g.passed ? "Passed" : "Open"} — {g.name}
                {g.manual ? " (signed off by an admin)" : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {detail && detail.qual.families.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h3>Commitments (qualitative branch)</h3>
          <p className="muted">
            Reviewed commitments that have fallen due. A commitment without evidence of its outcome widens the
            range; it is not scored as missed.
          </p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Commitment</th>
                  <th>Deadline</th>
                  <th>Fulfilled</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {detail.qual.families.map((q) => (
                  <tr key={q.id}>
                    <td>{q.subject}</td>
                    <td>{q.deadline ?? "—"}</td>
                    <td>
                      {q.low === null || q.high === null
                        ? "—"
                        : q.low === q.high
                          ? `${Math.round(q.low * 100)}%`
                          : `${Math.round(q.low * 100)}–${Math.round(q.high * 100)}%`}
                    </td>
                    <td>{reason(q.reason)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {shadow.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h3>Published level beside each method</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>{published?.name ?? "Published"} (published)</th>
                <th>{nameOf("v2.4") ?? "Core"}</th>
                <th>Difference</th>
                <th>{nameOf("v2.4-R2") ?? "v2.4-R2"}</th>
                <th>{nameOf("delivery") ?? "Delivery only"}</th>
                <th>{nameOf("v2.5-proposal") ?? "v2.5 proposals"}</th>
              </tr>
            </thead>
            <tbody>
              {shadow.map((r) => (
                <tr key={r.company_id}>
                  <td>{r.company_id}</td>
                  <td>{r.v4_gci ?? "—"}</td>
                  <td>{r.core_gci ?? "—"}</td>
                  <td>{r.difference ?? "—"}</td>
                  <td>{r.r2_gci ?? "—"}</td>
                  <td>{r.delivery_gci ?? "—"}</td>
                  <td>{r.proposal_gci ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {markets.length > 0 && (
        <section>
          <h3>What Core can do in each market</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Status</th>
                  <th>Numeric guidance</th>
                  <th>Reporting</th>
                  <th>Accounting</th>
                  <th>Main adjustment</th>
                </tr>
              </thead>
              <tbody>
                {markets.map((m) => (
                  <tr key={m.market_id}>
                    <td>{m.name}</td>
                    <td>{STATUS_TEXT[m.core_status] ?? m.core_status}</td>
                    <td>{m.numeric_guidance}</td>
                    <td>{m.reporting_cadence === "Q" ? "Quarterly" : "Half-yearly"}</td>
                    <td>{m.regimes.length ? m.regimes.join(", ") : "None supported"}</td>
                    <td>{m.modifications[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
