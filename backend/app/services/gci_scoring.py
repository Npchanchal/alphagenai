"""GCI scorers — v4 (v3 engine + beat floor), v3 (exp δ / γ / recency), v2 (legacy heuristic).

Toggle with ``INTELLENS_GCI_VERSION=v2|v3|v4`` (default ``v4``). GCI Core v2.4
(``compute_core_detail``) runs beside them in shadow and is never the default.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


# --- v3 constants (Technical Spec) ---
GCI_ALPHA = 0.35
GCI_BETA = 1.25
GCI_LAMBDA = 0.15
GCI_GAMMA_MISS = 1.4
GCI_EPS = 1e-6
POINT_BAND_FRAC = 0.02
MIN_PERIODS_FULL_CONF = 4

# --- v4 evidence weighting (plan W1.4; see score_policy for the public tiers) ---
MIN_CLOSED_PERIODS_PER_METRIC = 2
METRIC_WEIGHT_CAP = 5
#: Methodology revision inside the gci_scoring_v4 family (ledger / changelog note).
ALGORITHM_REVISION = "v4.2 width floor + metric direction (2026-10-18)"

# --- v4.2 width floor: a band narrower than this is widened around its midpoint ---
LEVEL_FLOOR_FRAC = POINT_BAND_FRAC
#: Percentage-point metrics (margins, growth, NIM) never get a half-width below one
#: reporting step (0.1 pp). The spec's 0.5 pp would score an 18 bp NIM beat as in-band.
RATE_FLOOR_PP = 0.10

# --- v4: beats decay from 100 toward this floor instead of toward 0 ---
GCI_BEAT_FLOOR = 60.0

AUDIT_PENALTY_PTS: Dict[str, float] = {
    "guidance_withdrawal": 15.0,
    "restatement": 15.0,
    "definition_shift": 10.0,
}


class OutcomeLabel(str, Enum):
    EXCEEDED = "exceeded"
    MET = "met"
    MISSED = "missed"
    DROPPED = "dropped"
    PENDING = "pending"
    UNMAPPED = "unmapped"
    PENDING_GUIDANCE_CITE = "pending_guidance_cite"
    NOT_PRIOR_PROMISE = "not_prior_promise"
    BASIS_MISMATCH = "basis_mismatch"


@dataclass(frozen=True)
class GuidanceOutcome:
    period: str
    metric: str
    guided_value: float
    actual_value: Optional[float]
    guided_text: str
    confidence: float = 1.0
    speaker: str = "CFO"
    guided_low: Optional[float] = None
    guided_high: Optional[float] = None
    dropped: bool = False
    thread_id: Optional[str] = None
    source_url: Optional[str] = None
    source_ref: Optional[str] = None
    quote_span: Optional[str] = None
    as_of: Optional[str] = None  # YYYY-MM-DD point-in-time stamp
    doc_id: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    unmapped: bool = False  # qualitative / NLP UNMAPPED — excluded from GCI
    # Where the guidance was given, when source_* cites the actual.
    guidance_source_url: Optional[str] = None
    guidance_source_ref: Optional[str] = None
    guidance_quote: Optional[str] = None
    guidance_as_of: Optional[str] = None
    # In-year changes to the band after guidance_as_of, oldest first. Each item:
    # {"as_of", "guided_low", "guided_high", "source_url", "source_ref", "quote"}.
    # The headline score uses the opening band; revisions feed final_band_label().
    revisions: Tuple[Dict[str, Any], ...] = field(default=(), hash=False)
    # Labeling governance (W2.1 schema; W2.5 requires these on every scored row).
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None  # YYYY-MM-DD
    # W2.7: explicit False when a live fetch showed the quote is not on the URL.
    citeable: Optional[bool] = None
    source_verified: Optional[bool] = None
    # Comparability. A side left blank is unknown and still scores. Both sides
    # filled and different means the actual is not the figure that was guided.
    reporting_basis: Optional[str] = None
    actual_reporting_basis: Optional[str] = None
    unit: Optional[str] = None
    actual_unit: Optional[str] = None
    scope: Optional[str] = None
    actual_scope: Optional[str] = None
    # GCI Core inputs (shadow engine). v4 ignores all five.
    #: "floor" (at least g) | "ceiling" (at most g) for a one-sided promise.
    bound: Optional[str] = None
    #: Prior-period value of a percentage metric guided at exactly zero.
    prior_value: Optional[float] = None
    #: Company-stated scale for an amount guided at exactly zero (decision D-04).
    zero_reference: Optional[float] = None
    #: unconditional | satisfied | not_activated | unknown (blank = unconditional).
    condition_state: Optional[str] = None
    #: Later restated figure for the same period. Shown, never scored (D-25).
    restated_actual_value: Optional[float] = None


@dataclass
class GciComputeResult:
    gci: Optional[float]
    version: str
    low_confidence: bool = False
    periods_used: int = 0
    shenanigans_deduction: float = 0.0
    by_metric: Dict[str, float] = field(default_factory=dict)
    #: Metrics with too few closed periods to enter the composite (shown as context).
    context_metrics: Dict[str, float] = field(default_factory=dict)
    #: Closed periods per scored metric (drives evidence weights + confidence tier).
    periods_by_metric: Dict[str, int] = field(default_factory=dict)
    #: Effective composite weight per metric (evidence × optional metric weight).
    weights_used: Dict[str, float] = field(default_factory=dict)


def scorer_version(override: Optional[str] = None) -> str:
    raw = (override or os.environ.get("INTELLENS_GCI_VERSION") or "v4").strip().lower()
    if raw in ("v2", "2", "gci_v2", "gci_scoring_v2", "legacy"):
        return "v2"
    if raw in ("v3", "3", "gci_v3", "gci_scoring_v3"):
        return "v3"
    return "v4"


def algorithm_id(override: Optional[str] = None) -> str:
    return f"gci_scoring_{scorer_version(override)}"


def _band(outcome: GuidanceOutcome) -> Tuple[float, float]:
    low = outcome.guided_low if outcome.guided_low is not None else outcome.guided_value
    high = outcome.guided_high if outcome.guided_high is not None else outcome.guided_value
    if low > high:
        low, high = high, low
    return low, high


def metric_direction(metric: str) -> str:
    """higher | lower | two_sided — which side of the range is good news."""
    from app.data.metric_catalog import metric_direction as _direction

    return _direction(metric)


def band_floor(metric: str, midpoint: float) -> float:
    """Smallest half-width a band may have before scoring (spec v2.0 §3.2, recalibrated)."""
    from app.data.metric_catalog import metric_is_rate

    relative = LEVEL_FLOOR_FRAC * abs(midpoint)
    if metric_is_rate(metric):
        return max(relative, RATE_FLOOR_PP)
    return max(relative, GCI_EPS)


def _is_favorable(metric: str, actual: float, low: float, high: float) -> bool:
    """True when an out-of-band actual landed on the good-news side."""
    direction = metric_direction(metric)
    if direction == "lower":
        return actual < low
    if direction == "two_sided":
        return False
    return actual > high


def classify_outcome(outcome: GuidanceOutcome) -> OutcomeLabel:
    from app.services.score_policy import is_pending_guidance_cite

    if outcome.unmapped:
        return OutcomeLabel.UNMAPPED
    if outcome.dropped:
        return OutcomeLabel.DROPPED
    if outcome.actual_value is None:
        return OutcomeLabel.PENDING
    if is_pending_guidance_cite(outcome):
        return OutcomeLabel.PENDING_GUIDANCE_CITE
    from app.services.score_policy import is_basis_mismatch, is_not_prior_promise

    if is_not_prior_promise(outcome):
        return OutcomeLabel.NOT_PRIOR_PROMISE

    if is_basis_mismatch(outcome):
        return OutcomeLabel.BASIS_MISMATCH
    low, high = _band(outcome)
    actual = outcome.actual_value
    # 2% tolerance around band for "met", or the width floor where that is wider.
    pad = max(abs(outcome.guided_value) * 0.02, 0.05)
    shortfall = band_floor(outcome.metric, (low + high) / 2.0) - (high - low) / 2.0
    pad = max(pad, shortfall)
    if low - pad <= actual <= high + pad:
        return OutcomeLabel.MET
    if _is_favorable(outcome.metric, actual, low - pad, high + pad):
        return OutcomeLabel.EXCEEDED
    return OutcomeLabel.MISSED


def final_band(outcome: GuidanceOutcome) -> Optional[Tuple[float, float]]:
    """Last revised (low, high) band before the period closed, or None if never revised."""
    if not outcome.revisions:
        return None
    last = outcome.revisions[-1]
    low, high = float(last["guided_low"]), float(last["guided_high"])
    return (low, high) if low <= high else (high, low)


def final_band_label(outcome: GuidanceOutcome) -> Optional[OutcomeLabel]:
    """Outcome against the final revised band; None when there were no revisions."""
    band = final_band(outcome)
    if band is None:
        return None
    low, high = band
    return classify_outcome(
        replace(
            outcome,
            guided_low=low,
            guided_high=high,
            guided_value=(low + high) / 2.0,
            revisions=(),
        )
    )


def revision_direction(outcome: GuidanceOutcome) -> Optional[str]:
    """raised | cut | unchanged — final band midpoint vs opening band midpoint."""
    band = final_band(outcome)
    if band is None:
        return None
    o_low, o_high = _band(outcome)
    opening_mid = (o_low + o_high) / 2.0
    final_mid = (band[0] + band[1]) / 2.0
    if final_mid > opening_mid + GCI_EPS:
        return "raised"
    if final_mid < opening_mid - GCI_EPS:
        return "cut"
    return "unchanged"


# ---------------------------------------------------------------------------
# v2 — ranges, asymmetric beats, labels, dropped guidance
# ---------------------------------------------------------------------------


def outcome_score_v2(outcome: GuidanceOutcome) -> Optional[float]:
    """
    Score 0–100 for a closed outcome (v2).
    - Dropped → 35 (silence ≠ full miss, but hurts credibility)
    - Pending / unmapped → None (excluded from company average)
    - In-band (met) → 100
    - Exceeded (beat) → 92–100 (slightly below perfect — forecast quality)
    - Missed → decays with relative distance below low band; ≥50% miss → 0
    """
    from app.services.score_policy import excluded_from_score

    if excluded_from_score(outcome):
        return None
    label = classify_outcome(outcome)
    if label in (
        OutcomeLabel.PENDING,
        OutcomeLabel.UNMAPPED,
        OutcomeLabel.PENDING_GUIDANCE_CITE,
        OutcomeLabel.BASIS_MISMATCH,
    ):
        return None
    if label == OutcomeLabel.DROPPED:
        raw = 35.0
    elif label == OutcomeLabel.MET:
        raw = 100.0
    else:
        low, high = _band(outcome)
        actual = float(outcome.actual_value)
        edge = high if actual > high else low
        if label == OutcomeLabel.EXCEEDED:
            overshoot = abs(actual - edge) / max(abs(edge), 1e-6)
            raw = max(85.0, 100.0 - min(overshoot, 1.0) * 15.0)
        else:  # MISSED
            rel_err = abs(actual - edge) if edge == 0 else abs(actual - edge) / abs(edge)
            raw = max(0.0, 100.0 * (1.0 - min(rel_err / 0.5, 1.0)))

    weight = min(max(outcome.confidence, 0.5), 1.0)
    return raw * weight + (1.0 - weight) * 50.0


def compute_company_gci_v2(outcomes: List[GuidanceOutcome]) -> Optional[float]:
    scored: List[Tuple[float, float]] = []
    for o in outcomes:
        s = outcome_score_v2(o)
        if s is None:
            continue
        w = min(max(o.confidence, 0.5), 1.0)
        scored.append((s, w))
    if not scored:
        return None
    total_w = sum(w for _, w in scored)
    return round(sum(s * w for s, w in scored) / total_w, 1)


# ---------------------------------------------------------------------------
# v3 — normalized δ, exp decay, γ asymmetry, recency, audit deductions
# ---------------------------------------------------------------------------


def effective_band(outcome: GuidanceOutcome) -> Tuple[float, float, float, float]:
    """Return (G_min, G_max, G_mid, W*) with the band widened to the metric's floor."""
    low, high = _band(outcome)
    gmid = (low + high) / 2.0
    w = max((high - low) / 2.0, band_floor(outcome.metric, gmid))
    if w > (high - low) / 2.0:
        return gmid - w, gmid + w, gmid, w
    return low, high, gmid, w


def normalized_surprise(outcome: GuidanceOutcome) -> Optional[float]:
    """s* = σ·(A − M)/W*: positive is good news, ±1 is the band edge. None if not closed.

    Two-sided metrics report −|A − M|/W*, so any deviation reads as a shortfall.
    """
    if outcome.unmapped or outcome.dropped or outcome.actual_value is None:
        return None
    _gmin, _gmax, gmid, w = effective_band(outcome)
    gap = (float(outcome.actual_value) - gmid) / (w + GCI_EPS)
    direction = metric_direction(outcome.metric)
    if direction == "lower":
        return -gap
    if direction == "two_sided":
        return -abs(gap)
    return gap


def normalized_deviation(outcome: GuidanceOutcome) -> Optional[float]:
    """Out-of-band δ_t; 0 inside band; None if period excluded."""
    from app.services.score_policy import excluded_from_score

    if outcome.unmapped or outcome.dropped or outcome.actual_value is None:
        return None
    if excluded_from_score(outcome):
        return None
    gmin, gmax, gmid, w = effective_band(outcome)
    actual = float(outcome.actual_value)
    if gmin <= actual <= gmax:
        return 0.0
    return (abs(actual - gmid) - w) / (w + GCI_EPS)


def _outcome_score_exp(
    outcome: GuidanceOutcome,
    beat_floor: float,
    *,
    alpha: float = GCI_ALPHA,
    beta: float = GCI_BETA,
    gamma: float = GCI_GAMMA_MISS,
    check_policy: bool = True,
) -> Optional[float]:
    from app.services.score_policy import excluded_from_score

    if outcome.unmapped or outcome.dropped or outcome.actual_value is None:
        return None
    if check_policy and excluded_from_score(outcome):
        return None
    gmin, gmax, gmid, w = effective_band(outcome)
    actual = float(outcome.actual_value)
    if gmin <= actual <= gmax:
        return 100.0
    delta = (abs(actual - gmid) - w) / (w + GCI_EPS)
    # Guard negative base for fractional β on tiny float noise
    delta = max(0.0, delta)
    decay = math.exp(-alpha * (delta**beta))
    if _is_favorable(outcome.metric, actual, gmin, gmax):
        return beat_floor + (100.0 - beat_floor) * decay
    return max(0.0, 100.0 - gamma * (100.0 - 100.0 * decay))


def outcome_score_v3(outcome: GuidanceOutcome) -> Optional[float]:
    """Adjusted single-period score S̃_{m,t} (0–100). Excludes pending/unmapped/dropped."""
    return _outcome_score_exp(outcome, 0.0)


def outcome_score_v4(outcome: GuidanceOutcome) -> Optional[float]:
    """v3 with beats floored at GCI_BEAT_FLOOR; in-band and misses are identical to v3."""
    return _outcome_score_exp(outcome, GCI_BEAT_FLOOR)


_EXP_SCORERS = {"v3": outcome_score_v3, "v4": outcome_score_v4}


def audit_deduction(
    outcomes: Sequence[GuidanceOutcome],
    audit_flags: Optional[Sequence[str]] = None,
) -> float:
    """D_shenanigans from analyst-set flags only (W2.6).

    Dropped rows are excluded from the composite; they do not auto-apply
    ``guidance_withdrawal``. Pass that flag explicitly after a reviewer sets it.
    ``outcomes`` is unused and kept so existing call sites keep compiling.
    """
    del outcomes
    flags = set(audit_flags or [])
    return sum(AUDIT_PENALTY_PTS[f] for f in flags if f in AUDIT_PENALTY_PTS)


def _recency_weight(t_index: int) -> float:
    """t_index=1 is most recent → w = e^{-λ(t-1)}."""
    return math.exp(-GCI_LAMBDA * (t_index - 1))


def _periods_newest_first(outcomes: Sequence[GuidanceOutcome]) -> List[str]:
    from app.services.changes import sort_periods

    ordered = sort_periods(list({o.period for o in outcomes}))
    return list(reversed(ordered))


def _metric_score_v3(
    rows: List[GuidanceOutcome],
    period_rank: Dict[str, int],
    score_fn=outcome_score_v3,
) -> Optional[float]:
    """Recency-weighted multi-period S_m."""
    # One score per period (average if multiple rows in same period)
    by_period: Dict[str, List[float]] = {}
    conf_by_period: Dict[str, List[float]] = {}
    for o in rows:
        s = score_fn(o)
        if s is None:
            continue
        by_period.setdefault(o.period, []).append(s)
        conf_by_period.setdefault(o.period, []).append(min(max(o.confidence, 0.5), 1.0))
    if not by_period:
        return None
    num = 0.0
    den = 0.0
    for period, scores in by_period.items():
        t = period_rank.get(period)
        if t is None:
            continue
        s_bar = sum(scores) / len(scores)
        c_bar = sum(conf_by_period[period]) / len(conf_by_period[period])
        w = _recency_weight(t) * c_bar
        num += w * s_bar
        den += w
    if den <= 0:
        return None
    return num / den


def compute_company_gci_v3(
    outcomes: List[GuidanceOutcome],
    *,
    sector_mean: Optional[float] = None,
    metric_weights: Optional[Dict[str, float]] = None,
    audit_flags: Optional[Sequence[str]] = None,
    version: str = "v3",
) -> Optional[float]:
    result = compute_gci_v3_detail(
        outcomes,
        sector_mean=sector_mean,
        metric_weights=metric_weights,
        audit_flags=audit_flags,
        version=version,
    )
    return result.gci


def compute_company_gci_v4(
    outcomes: List[GuidanceOutcome],
    *,
    sector_mean: Optional[float] = None,
    metric_weights: Optional[Dict[str, float]] = None,
    audit_flags: Optional[Sequence[str]] = None,
) -> Optional[float]:
    return compute_company_gci_v3(
        outcomes,
        sector_mean=sector_mean,
        metric_weights=metric_weights,
        audit_flags=audit_flags,
        version="v4",
    )


def compute_gci_v3_detail(
    outcomes: List[GuidanceOutcome],
    *,
    sector_mean: Optional[float] = None,
    metric_weights: Optional[Dict[str, float]] = None,
    audit_flags: Optional[Sequence[str]] = None,
    version: str = "v3",
) -> GciComputeResult:
    """Full v3/v4 composite: φ-weighted metrics − D_shenanigans, optional sector shrinkage."""
    score_fn = _EXP_SCORERS.get(version, outcome_score_v3)
    scored_outcomes = [
        o
        for o in outcomes
        if not o.unmapped and score_fn(o) is not None
    ]
    periods = _periods_newest_first(scored_outcomes)
    period_rank = {p: i + 1 for i, p in enumerate(periods)}

    by_metric_rows: Dict[str, List[GuidanceOutcome]] = {}
    for o in outcomes:
        if o.unmapped:
            continue
        by_metric_rows.setdefault(o.metric, []).append(o)

    s_by_metric: Dict[str, float] = {}
    periods_by_metric: Dict[str, int] = {}
    for metric, rows in by_metric_rows.items():
        sm = _metric_score_v3(rows, period_rank, score_fn)
        if sm is not None:
            s_by_metric[metric] = sm
            periods_by_metric[metric] = len(
                {o.period for o in rows if score_fn(o) is not None and o.period in period_rank}
            )

    if not s_by_metric:
        # Only audit / dropped with no scored delivery — still no GCI
        return GciComputeResult(gci=None, version=version, by_metric={})

    # --- Evidence-weighted composite (v4, plan W1.4) -------------------------
    # A metric's weight is its number of closed periods (capped). A metric with
    # fewer than MIN_CLOSED_PERIODS_PER_METRIC closed periods is context-only —
    # shown on the dossier but not in the composite — *when* the company has at
    # least one deeper metric. If every metric is single-period the composite
    # falls back to a flat mean and the confidence tier says "provisional".
    evidence_weighted = version == "v4"
    context_metrics: Dict[str, float] = {}
    composite_metrics = dict(s_by_metric)
    if evidence_weighted:
        deep = {m for m, n in periods_by_metric.items() if n >= MIN_CLOSED_PERIODS_PER_METRIC}
        if deep:
            for metric in list(composite_metrics):
                if metric not in deep:
                    context_metrics[metric] = composite_metrics.pop(metric)

    weights = metric_weights or {}
    weights_used: Dict[str, float] = {}
    v_sum = 0.0
    weighted = 0.0
    for metric, sm in composite_metrics.items():
        v = float(weights.get(metric, 1.0))
        if evidence_weighted:
            v *= float(min(periods_by_metric.get(metric, 1), METRIC_WEIGHT_CAP))
        if v <= 0:
            continue
        weights_used[metric] = v
        v_sum += v
        weighted += v * sm
    if v_sum <= 0:
        return GciComputeResult(gci=None, version=version, by_metric=s_by_metric)

    gci_raw = weighted / v_sum
    d_shen = audit_deduction(outcomes, audit_flags)
    gci = max(0.0, min(100.0, gci_raw - d_shen))

    n_periods = len(periods)
    low_conf = n_periods < MIN_PERIODS_FULL_CONF
    # Sector shrinkage was removed in W1.5 (decision D5): the cohort is too
    # thin for sector means to carry information. ``sector_mean`` is accepted
    # for signature compatibility and ignored.
    del sector_mean

    return GciComputeResult(
        gci=round(gci, 1),
        version=version,
        low_confidence=low_conf,
        periods_used=n_periods,
        shenanigans_deduction=d_shen,
        by_metric={k: round(v, 1) for k, v in composite_metrics.items()},
        context_metrics={k: round(v, 1) for k, v in context_metrics.items()},
        periods_by_metric=periods_by_metric,
        weights_used=weights_used,
    )


# ---------------------------------------------------------------------------
# Version-routed public API (default v4)
# ---------------------------------------------------------------------------


def outcome_score(
    outcome: GuidanceOutcome,
    *,
    version: Optional[str] = None,
) -> Optional[float]:
    ver = scorer_version(version)
    if ver == "v2":
        return outcome_score_v2(outcome)
    return _EXP_SCORERS[ver](outcome)


def compute_company_gci(
    outcomes: List[GuidanceOutcome],
    *,
    version: Optional[str] = None,
    sector_mean: Optional[float] = None,
    metric_weights: Optional[Dict[str, float]] = None,
    audit_flags: Optional[Sequence[str]] = None,
) -> Optional[float]:
    ver = scorer_version(version)
    if ver == "v2":
        return compute_company_gci_v2(outcomes)
    return compute_company_gci_v3(
        outcomes,
        sector_mean=sector_mean,
        metric_weights=metric_weights,
        audit_flags=audit_flags,
        version=ver,
    )


def metric_breakdown(
    outcomes: List[GuidanceOutcome],
    *,
    version: Optional[str] = None,
) -> Dict[str, float]:
    by_metric: Dict[str, List[GuidanceOutcome]] = {}
    for o in outcomes:
        by_metric.setdefault(o.metric, []).append(o)
    result: Dict[str, float] = {}
    ver = scorer_version(version)
    for metric, rows in by_metric.items():
        score = compute_company_gci(rows, version=ver)
        if score is not None:
            result[metric] = score
    return result


def label_counts(outcomes: List[GuidanceOutcome]) -> Dict[str, int]:
    counts = {label.value: 0 for label in OutcomeLabel}
    for o in outcomes:
        counts[classify_outcome(o).value] += 1
    for label in (OutcomeLabel.BASIS_MISMATCH, OutcomeLabel.NOT_PRIOR_PROMISE):
        if counts.get(label.value) == 0:
            counts.pop(label.value, None)
    return counts


def delta_pct(guided: float, actual: Optional[float]) -> Optional[float]:
    if actual is None:
        return None
    if guided == 0:
        return 0.0
    return round(100.0 * (actual - guided) / abs(guided), 2)


def gci_trend_series(
    outcomes: List[GuidanceOutcome],
    periods: Optional[List[str]] = None,
    *,
    version: Optional[str] = None,
) -> List[Dict[str, Optional[float]]]:
    """Cumulative GCI after each period (ordered), with period-over-period change."""
    from app.services.changes import enrich_value_series, sort_periods

    ordered_periods = periods or sort_periods(list({o.period for o in outcomes}))
    ver = scorer_version(version)
    series: List[Dict[str, Any]] = []
    accumulated: List[GuidanceOutcome] = []
    for period in ordered_periods:
        accumulated.extend([o for o in outcomes if o.period == period])
        series.append({"period": period, "gci_score": compute_company_gci(accumulated, version=ver)})
    return enrich_value_series(series, period_key="period", value_key="gci_score")  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# GCI Core v2.4 — shadow engine (docs/PLAN_GCI_CORE.md)
# ---------------------------------------------------------------------------
# Locked methodology v2.4 is the default (owner ruling 2026-11-09). The v2.5
# change-control proposals run only with ``ruleset=CORE_RULESET_PROPOSAL``, for
# impact analysis. ``CORE_RULESET_R2`` is the owner's v2.4-R2 specification
# (2026-11-10) with the tech-team amendments A1–A5, in shadow until the owner rules on
# them. ``CORE_RULESET_DELIVERY`` is locked v2.4 measurement without the
# three elements that answer other questions (revision frequency, lead time, Qual);
# those are companion indexes in ``guidance_profile.companion_indexes``.
# ``scorer_version`` never returns Core: published levels stay on v4 until
# validation gate 8 passes and a methodology changelog entry says otherwise.

CORE_RULESET_LOCKED = "v2.4"
CORE_RULESET_R2 = "v2.4-R2"
CORE_RULESET_DELIVERY = "delivery"
CORE_RULESET_PROPOSAL = "v2.5-proposal"
CORE_RULESETS = (CORE_RULESET_LOCKED, CORE_RULESET_R2, CORE_RULESET_DELIVERY, CORE_RULESET_PROPOSAL)
#: Which ruleset Core runs when none is named. One line to switch after the owner rules.
CORE_DEFAULT_RULESET = CORE_RULESET_LOCKED
CORE_ALGORITHM_ID = "gci_core_v2_4"
CORE_R2_ALGORITHM_ID = "gci_core_v2_4_r2"
CORE_DELIVERY_ALGORITHM_ID = "gci_core_delivery_v1"
CORE_PROPOSAL_ALGORITHM_ID = "gci_core_v2_5_proposal"
CORE_ALGORITHM_IDS = {
    CORE_RULESET_LOCKED: CORE_ALGORITHM_ID,
    CORE_RULESET_R2: CORE_R2_ALGORITHM_ID,
    CORE_RULESET_DELIVERY: CORE_DELIVERY_ALGORITHM_ID,
    CORE_RULESET_PROPOSAL: CORE_PROPOSAL_ALGORITHM_ID,
}
CORE_METHODOLOGY_VERSION = "GCI_CORE_V2_4"
CORE_REVISION = "core v2.4 shadow r2 (2026-11-10)"
#: Flip only together with a ledger snapshot and a methodology changelog entry.
CORE_ENGINE_APPROVED = False

#: One display name per GCI method. ``code`` is what a customer may pass as ``ruleset``;
#: the version stays beside the name so a citation names the exact method. Renaming a
#: method changes no number, but the name must stay the same for the life of its algorithm id.
GCI_METHODS: Tuple[Dict[str, Any], ...] = (
    {
        "code": "classic",
        "name": "GCI Classic",
        "version": "v4",
        "algorithm_id": "gci_scoring_v4",
        "ruleset": None,
        "status": "published",
        "summary": "The published level on every dossier, the GCI Screener and the index files.",
    },
    {
        "code": "core",
        "name": "GCI Core",
        "version": "v2.4",
        "algorithm_id": CORE_ALGORITHM_ID,
        "ruleset": CORE_RULESET_LOCKED,
        "status": "shadow",
        "summary": "The approved v2.4 methodology run beside the published level: 80% numeric guidance, "
        "20% commitments, with revision-count and lead-time adjustments.",
    },
    {
        "code": "range",
        "name": "GCI Range",
        "version": "v2.4-R2",
        "algorithm_id": CORE_R2_ALGORITHM_ID,
        "ruleset": CORE_RULESET_R2,
        "status": "pending_ruling",
        "summary": "A result inside the guided range scores 100; a miss is read against the larger of range "
        "width, midpoint and a 5-point growth floor. Upward revisions weigh less than walk-downs.",
    },
    {
        "code": "delivery",
        "name": "GCI Delivery",
        "version": "v1",
        "algorithm_id": CORE_DELIVERY_ALGORITHM_ID,
        "ruleset": CORE_RULESET_DELIVERY,
        "status": "alternative",
        "summary": "Guidance against the reported result only: no revision-count penalty, lead-time multiplier "
        "or commitments weight. Those are reported as companion indexes.",
    },
    {
        "code": "draft",
        "name": "GCI Draft",
        "version": "v2.5",
        "algorithm_id": CORE_PROPOSAL_ALGORITHM_ID,
        "ruleset": CORE_RULESET_PROPOSAL,
        "status": "change_control",
        "summary": "Proposed methodology changes, for impact analysis only.",
    },
)

CORE_ALPHA = Decimal("1")
CORE_LAMBDA = Decimal("1")
CORE_ETA = Decimal("0.5")
CORE_HORIZON_DAYS = {"Q": 90, "H": 180, "FY": 365}
#: Days after period end by which results must be filed (SEBI LODR Reg 33). A missing actual
#: past this point is ``ACTUAL_UNAVAILABLE``, not ``OUTCOME_NOT_DUE``.
CORE_ACTUAL_DUE_DAYS = {"Q": 45, "H": 45, "FY": 60}
#: §13.3: lead time below N days earns the factor; 180 days or more earns ``CORE_LEAD_TIME_TOP``.
CORE_LEAD_TIME_STEPS: Tuple[Tuple[int, Decimal], ...] = (
    (30, Decimal("0.8")),
    (90, Decimal("0.9")),
    (180, Decimal("1.0")),
)
CORE_LEAD_TIME_TOP = Decimal("1.1")
CORE_LATE_GUIDANCE_DAYS = 30
#: §17. Calibration of the split is an open v2.5 item.
CORE_QUANT_WEIGHT = Decimal("0.8")
CORE_QUAL_WEIGHT = Decimal("0.2")
#: §14.1: (revisions at the normal ceiling, penalty there, slope beyond). The methodology
#: names annual and quarterly ceilings only; half-year guidance uses the annual curve.
CORE_FREQUENCY_CURVES: Dict[str, Tuple[int, Decimal, Decimal]] = {
    "FY": (5, Decimal("0.5"), Decimal("0.08")),
    "Q": (2, Decimal("0.5"), Decimal("0.08")),
}
CORE_FIRST_REVISION_PENALTY = Decimal("0.2")
CORE_FREQUENCY_CAP = Decimal("0.9")

# v2.5 proposals (docs/PLAN_GCI_CORE.md change-control backlog) — never the default.
PROPOSAL_FAVOURABLE_BOUND_RATE = Decimal("0.5")  # D-01
PROPOSAL_MIN_FAMILIES_PER_PARAMETER = 2  # D-10
PROPOSAL_FREQUENCY_CURVES: Dict[str, Tuple[int, Decimal, Decimal]] = {  # D-08
    "FY": (5, Decimal("0.5"), Decimal("0.08")),
    "H": (3, Decimal("0.5"), Decimal("0.12")),
    "Q": (2, Decimal("0.5"), Decimal("0.20")),
}
#: Delivery ruleset: a growth miss is read against a reference of at least this many
#: points, so a 1.2-point beat on 1–3% guidance is not scored as a total miss. Uncalibrated.
DELIVERY_GROWTH_FLOOR_PP = Decimal("10")
#: What the delivery ruleset leaves out of the level, and the companion index that measures it.
CORE_DELIVERY_EXCLUDES = (
    {"element": "revision_frequency_penalty", "section": "§14", "companion": "revision_discipline"},
    {"element": "lead_time_factor", "section": "§13.3", "companion": "guidance_visibility"},
    {"element": "qual_composite_weight", "section": "§17", "companion": "commitment_delivery"},
    {"element": "growth_relative_deviation", "section": "§9", "companion": "growth_accuracy_pp"},
)
#: GAP-21: below this many closed periods the level carries THIN_HISTORY (shown, not scored).
CORE_THIN_HISTORY_PERIODS = 2

# v2.4-R2 (owner specification 2026-11-10) with the tech-team amendments in
# docs/review/GCI_v2.4-R2_Reply_10_Nov_2026.md. Shadow only until the owner rules on them.
#: §2: weight of one in-window revision in N_eff, by what it did to the promise.
R2_REVISION_WEIGHTS: Dict[str, Decimal] = {
    "walk_down": Decimal("1.0"),
    "raise": Decimal("0.3"),
    "mixed": Decimal("0.5"),
    "wider": Decimal("0.7"),
    "narrower": Decimal("0.0"),
    "no_op": Decimal("0.0"),
    "undirected": Decimal("1.0"),
}
#: §6: a growth-percentage miss is read against at least this many percentage points. Uncalibrated.
R2_GROWTH_FLOOR_PP = Decimal("5")
#: Amendment A1: a miss outside a range is scaled by max(width, |midpoint|, floor), not width alone.
#: False reproduces the specification as written (impact analysis only).
R2_SCALE_INCLUDES_MIDPOINT = True
#: Amendment A2 (§11 "all closed-set members score 100"): a met floor or ceiling scores 100.
#: False reproduces §6 as written, which scores distance from the bound both ways.
R2_MET_BOUND_SCORES_FULL = True
#: §4: LeadTimeFactor(r) = base + slope × min(r, 1), r = lead days / horizon days.
R2_LEAD_BASE = Decimal("0.80")
R2_LEAD_SLOPE = Decimal("0.30")
#: §5: Composite becomes the headline at this many evidenced commitments and this share of due ones.
R2_QUAL_MIN_COMMITMENTS = 3
R2_QUAL_MIN_COVERAGE = Decimal("0.5")
#: §8: parameters set by design that the calibration protocol must test before any is locked.
R2_CALIBRATION = {
    "protocol_id": "CAL-R2-01",
    "status": "pre-registration pending",
    "parameters": ["revision_weights", "lead_time_shape", "composite_weights", "growth_floor_pp"],
}

_CORE_PREC = 28
_HUNDRED = Decimal("100")
_ZERO = Decimal("0")
_ONE = Decimal("1")


def resolve_ruleset(value: Optional[str]) -> Optional[str]:
    """Core ruleset for a ruleset id or a method code (``range`` → ``v2.4-R2``); None stays None."""
    if value is None:
        return None
    if value in CORE_RULESETS:
        return value
    held = next((m for m in GCI_METHODS if m["code"] == value and m["ruleset"]), None)
    if held is None:
        raise ValueError(f"unknown GCI Core ruleset {value!r}")
    return str(held["ruleset"])


def _ruleset(value: Optional[str]) -> str:
    return resolve_ruleset(value) or CORE_DEFAULT_RULESET


def gci_method(algorithm_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Catalogue entry for an algorithm id; earlier published scorers keep the Classic name."""
    if not algorithm_id:
        return None
    held = next((m for m in GCI_METHODS if m["algorithm_id"] == algorithm_id), None)
    if held is not None:
        return dict(held)
    if algorithm_id.startswith("gci_scoring_"):
        classic = next(m for m in GCI_METHODS if m["code"] == "classic")
        return {**classic, "algorithm_id": algorithm_id, "version": algorithm_id[len("gci_scoring_"):],
                "status": "retired"}
    return None


def method_label(algorithm_id: Optional[str]) -> Optional[str]:
    """``GCI Range (v2.4-R2)`` — the name a reader cites."""
    m = gci_method(algorithm_id)
    return f"{m['name']} ({m['version']})" if m else None


def core_algorithm_id(ruleset: Optional[str] = None) -> str:
    return CORE_ALGORITHM_IDS[_ruleset(ruleset)]


def core_ruleset_for(algorithm_id: str) -> str:
    """Ruleset behind a Core ``algorithm_id`` (ledger replay)."""
    for rs, algo in CORE_ALGORITHM_IDS.items():
        if algo == algorithm_id:
            return rs
    raise ValueError(f"not a GCI Core algorithm id: {algorithm_id!r}")


def _id(prefix: str, *parts: Any) -> str:
    import hashlib

    blob = "|".join("" if p is None else str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]}"


def core_family_id(company_id: Optional[str], o: GuidanceOutcome) -> str:
    """Stable id for one metric, one period, one scope and basis. A basis switch is a new family."""
    from app.data.metric_catalog import normalize_basis

    return _id("fam", company_id, o.metric, o.period, (o.scope or "").strip().lower(), normalize_basis(o.reporting_basis))


def core_vintage_id(family_id: str, as_of: Optional[str], low: float, high: float, source_url: Optional[str]) -> str:
    return _id("vin", family_id, as_of, f"{float(low):.6g}", f"{float(high):.6g}", source_url)


_CURRENCY = {"inr_cr": "INR", "inr": "INR", "usd_mn": "USD", "usd": "USD"}


def core_units(o: GuidanceOutcome) -> Dict[str, Optional[str]]:
    from app.data.metric_catalog import get_metric

    unit = o.unit or (get_metric(o.metric) or {}).get("unit")
    return {"unit": unit, "currency": _CURRENCY.get(str(unit or "").lower())}


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _q(value: Optional[Decimal], places: str = "0.0001") -> Optional[float]:
    if value is None:
        return None
    return float(value.quantize(Decimal(places), rounding=ROUND_HALF_EVEN))


def core_cadence(period: str) -> str:
    head = str(period or "").strip().upper()[:1]
    return {"Q": "Q", "H": "H"}.get(head, "FY")


def core_frequency_penalty(revisions: Any, cadence: str = "FY", ruleset: Optional[str] = None) -> Decimal:
    """Share of the family score removed for ``revisions`` counted revisions (§14.1).

    Under v2.4-R2 ``revisions`` is the weighted count N_eff and may be fractional:
    the same curve, with ``0.2 × N_eff`` below one revision.
    """
    rs = _ruleset(ruleset)
    n = _dec(revisions) if rs == CORE_RULESET_R2 else Decimal(int(revisions))
    if n <= 0 or rs == CORE_RULESET_DELIVERY:
        return _ZERO
    curves = PROPOSAL_FREQUENCY_CURVES if rs == CORE_RULESET_PROPOSAL else CORE_FREQUENCY_CURVES
    ceiling, at_ceiling, slope = curves.get(cadence, curves["FY"])
    if n <= 1:
        p = CORE_FIRST_REVISION_PENALTY * n
    elif n <= ceiling:
        p = CORE_FIRST_REVISION_PENALTY + (at_ceiling - CORE_FIRST_REVISION_PENALTY) * (n - 1) / Decimal(ceiling - 1)
    else:
        p = at_ceiling + slope * (n - ceiling)
    return min(p, CORE_FREQUENCY_CAP)


def core_lead_time_factor(days: int) -> Decimal:
    """§13.3: 0.8 under 30 days, 0.9 under 90, 1.0 under 180, 1.1 from 180 days."""
    for limit, factor in CORE_LEAD_TIME_STEPS:
        if days < limit:
            return factor
    return CORE_LEAD_TIME_TOP


def r2_lead_time_factor(lead_days: int, horizon_days: int) -> Decimal:
    """R2 §4: ``0.80 + 0.30 × min(L / H, 1)``; continuous, the same curve for every horizon."""
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        r = Decimal(lead_days) / Decimal(horizon_days)
        return R2_LEAD_BASE + R2_LEAD_SLOPE * min(r, _ONE)


def r2_revision_kind(metric: str, prev: Tuple[Decimal, Decimal], cur: Tuple[Decimal, Decimal], bound: Optional[str] = None) -> str:
    """What one revision did to the promise (R2 §2, amendment A3).

    Directions are economic: a higher capex ceiling is a walk-down. ``mixed`` is a better
    midpoint with the weaker bound moved against the company (4–6% to 3.5–7%).
    """
    mid_prev, mid_cur = (prev[0] + prev[1]) / 2, (cur[0] + cur[1]) / 2
    width_prev, width_cur = prev[1] - prev[0], cur[1] - cur[0]
    if mid_cur == mid_prev:
        if width_cur < width_prev:
            return "narrower"
        return "wider" if width_cur > width_prev else "no_op"
    side = (bound or "").strip().lower()
    direction = {"floor": "higher", "ceiling": "lower"}.get(side) or metric_direction(metric)
    if direction == "two_sided":
        return "undirected"
    better = (mid_cur > mid_prev) == (direction != "lower")
    if not better:
        return "walk_down"
    weak_moved_against = cur[0] < prev[0] if direction != "lower" else cur[1] > prev[1]
    return "mixed" if weak_moved_against else "raise"


def _core_level(metric: str, value: Decimal, ruleset: str) -> Decimal:
    """v2.4 scores a percentage as stated. Proposal D-02 scores growth on its implied level."""
    if ruleset != CORE_RULESET_PROPOSAL:
        return value
    from app.data.metric_catalog import metric_is_growth

    return _ONE + value / _HUNDRED if metric_is_growth(metric) else value


def _zero_reference(
    metric: str, *, prior_value: Optional[float], zero_reference: Optional[float], ruleset: str
) -> Optional[Decimal]:
    """Denominator for guidance of exactly zero (§9.3, §9.4); None when unavailable."""
    from app.data.metric_catalog import metric_is_rate

    if metric_is_rate(metric):
        return None if prior_value in (None, 0) else abs(_dec(prior_value))
    if ruleset == CORE_RULESET_PROPOSAL:
        return None if zero_reference in (None, 0) else abs(_dec(zero_reference))  # D-04
    # Amounts are held in their presentation unit, so one displayed unit is 1.
    return _ONE


def core_vintage_z(
    metric: str,
    low: float,
    high: float,
    actual: float,
    *,
    bound: Optional[str] = None,
    prior_value: Optional[float] = None,
    zero_reference: Optional[float] = None,
    ruleset: Optional[str] = None,
    reference: Optional[str] = None,
    growth_floor_pp: Optional[float] = None,
    favourable_bound_rate: Optional[float] = None,
) -> Tuple[Optional[Decimal], Optional[str]]:
    """Normalised deviation ``z`` of one vintage, or ``(None, reason)`` when not computable.

    ``reference`` (``abs_bounds`` | ``max_mid_width`` | ``midpoint``), ``growth_floor_pp`` and
    ``favourable_bound_rate`` override what the ruleset sets; the method lab passes them.
    """
    rs = _ruleset(ruleset)
    if rs == CORE_RULESET_R2:
        terms = r2_vintage_terms(metric, low, high, actual, bound=bound, prior_value=prior_value)
        return terms["z"], terms["reason_code"]
    if reference is None:
        reference = "max_mid_width" if rs == CORE_RULESET_PROPOSAL else "abs_bounds"
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        lo, hi = sorted((_dec(low), _dec(high)))
        lo_t, hi_t = _core_level(metric, lo, rs), _core_level(metric, hi, rs)
        a_t = _core_level(metric, _dec(actual), rs)
        side = (bound or "").strip().lower()
        if side in ("floor", "ceiling"):
            mid = lo_t if side == "floor" else hi_t
            ref = abs(mid)
        else:
            mid = (lo_t + hi_t) / 2
            if reference == "max_mid_width":
                ref = max(abs(mid), hi_t - lo_t)
            elif reference == "midpoint":
                ref = abs(mid)
            else:
                ref = (abs(lo_t) + abs(hi_t)) / 2
        if growth_floor_pp is not None:
            from app.data.metric_catalog import metric_is_growth

            if metric_is_growth(metric):
                ref = max(ref, _dec(growth_floor_pp))
        elif rs == CORE_RULESET_DELIVERY:
            ref = _delivery_floor(metric, ref)
        if ref == 0:
            zref = _zero_reference(metric, prior_value=prior_value, zero_reference=zero_reference, ruleset=rs)
            if zref is None:
                return None, "ZERO_REFERENCE_UNAVAILABLE"
            return abs(a_t) / zref, None
        z = abs(a_t - mid) / ref
        favourable = side == "floor" and a_t > mid or side == "ceiling" and a_t < mid
        rate = (
            _dec(favourable_bound_rate)
            if favourable_bound_rate is not None
            else PROPOSAL_FAVOURABLE_BOUND_RATE if rs == CORE_RULESET_PROPOSAL else _ONE
        )
        if favourable:
            z *= rate
        return z, None


def r2_vintage_terms(
    metric: str,
    low: float,
    high: float,
    actual: float,
    *,
    bound: Optional[str] = None,
    prior_value: Optional[float] = None,
    growth_floor_pp: Optional[float] = None,
    scale_includes_midpoint: Optional[bool] = None,
    met_bound_full: Optional[bool] = None,
) -> Dict[str, Any]:
    """R2 §3/§6 target distance for one vintage, with amendments A1 (scale) and A2 (met bounds).

    Inside the promise (range, point, met floor or ceiling) ``z = 0``. Outside,
    ``z = distance to the nearest bound / scale`` where scale is
    ``max(width, |midpoint|, floor)``: floor = 5 pp for growth percentages. The scale
    never depends on the actual. A zero scale falls back to the v2.4 zero reference.
    The keyword overrides default to the R2 constants; the method lab passes them.
    """
    from app.data.metric_catalog import metric_is_growth

    floor_pp = R2_GROWTH_FLOOR_PP if growth_floor_pp is None else _dec(growth_floor_pp)
    with_mid = R2_SCALE_INCLUDES_MIDPOINT if scale_includes_midpoint is None else scale_includes_midpoint
    bound_full = R2_MET_BOUND_SCORES_FULL if met_bound_full is None else met_bound_full
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        lo, hi = sorted((_dec(low), _dec(high)))
        a = _dec(actual)
        side = (bound or "").strip().lower()
        growth = metric_is_growth(metric)
        floor = floor_pp if growth else _ZERO
        if side == "floor":
            target_type, lo_t, hi_t = "floor", lo, None
        elif side == "ceiling":
            target_type, lo_t, hi_t = "ceiling", None, hi
        else:
            target_type, lo_t, hi_t = ("point" if lo == hi else "range"), lo, hi
        if side in ("floor", "ceiling"):
            natural = abs(lo if side == "floor" else hi)
        elif lo == hi:
            natural = abs(lo)
        elif with_mid:
            natural = max(hi - lo, abs((lo + hi) / 2))
        else:
            natural = hi - lo
        scale = max(natural, floor)
        met = (lo_t is None or a >= lo_t) and (hi_t is None or a <= hi_t)
        if side in ("floor", "ceiling") and not bound_full:
            lo_t = hi_t = lo if side == "floor" else hi
        below = lo_t is not None and a < lo_t
        above = hi_t is not None and a > hi_t
        distance = (lo_t - a) if below else (a - hi_t) if above else _ZERO
        out: Dict[str, Any] = {
            "metric_kind": "growth_pct" if growth else "level",
            "target_type": target_type,
            "endpoint_flags": "inclusive",
            "target_met": met,
            "deviation": _q(distance, "0.000001"),
            "side": "under" if below else "over" if above else None,
            "natural_scale": _q(natural, "0.000001"),
            "scale_floor_pp": _q(floor_pp, "0.000001") if growth else None,
            "effective_scale": _q(scale, "0.000001"),
            "scale_floor_applied": bool(growth and floor > natural),
            "z": None,
            "reason_code": None,
        }
        if distance == 0:
            return {**out, "z": _ZERO}
        if scale == 0:
            zref = _zero_reference(metric, prior_value=prior_value, zero_reference=None, ruleset=CORE_RULESET_LOCKED)
            if zref is None:
                return {**out, "reason_code": "ZERO_REFERENCE_UNAVAILABLE"}
            scale = zref
            out["effective_scale"] = _q(scale, "0.000001")
        return {**out, "z": distance / scale}


def _delivery_floor(metric: str, ref: Decimal) -> Decimal:
    from app.data.metric_catalog import metric_is_growth

    return max(ref, DELIVERY_GROWTH_FLOOR_PP) if metric_is_growth(metric) else ref


def core_score_from_z(z: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        return max(_ZERO, _HUNDRED * (_ONE - z))


def core_revision_magnitude(
    metric: str,
    opening: Tuple[Decimal, Decimal],
    band: Tuple[Decimal, Decimal],
    *,
    ruleset: Optional[str] = None,
    prior_value: Optional[float] = None,
    zero_reference: Optional[float] = None,
) -> Optional[Decimal]:
    """Bounded revision size ``M = r / (1 + r)`` against the opening guidance (§11); None if unmeasurable."""
    rs = _ruleset(ruleset)
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        if rs != CORE_RULESET_PROPOSAL:
            scale: Optional[Decimal] = (abs(opening[0]) + abs(opening[1])) / 2
            if rs == CORE_RULESET_DELIVERY:
                scale = _delivery_floor(metric, scale)
            if scale == 0:
                scale = _zero_reference(metric, prior_value=prior_value, zero_reference=zero_reference, ruleset=rs)
            if scale is None:
                return None
            r = (abs(band[0] - opening[0]) + abs(band[1] - opening[1])) / 2 / scale
        else:
            open_mid = (opening[0] + opening[1]) / 2
            open_ref = max(abs(open_mid), opening[1] - opening[0])
            if open_ref == 0:
                return None
            r = abs((band[0] + band[1]) / 2 - open_mid) / open_ref
        return r / (_ONE + r)


def core_weight_exponent(elapsed_fraction: Decimal, magnitude: Optional[Decimal], direction: int) -> Decimal:
    """``ln(w_k / w_{k-1})`` (§12.1): longer gaps and larger or downward revisions weigh less."""
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        exponent = -CORE_ALPHA * elapsed_fraction
        if magnitude is not None:
            exponent -= CORE_LAMBDA * magnitude * (_ONE - CORE_ETA * Decimal(direction))
        return exponent


def _literal_outcome(low: float, high: float, actual: float, bound: Optional[str]) -> str:
    side = (bound or "").strip().lower()
    if side == "floor":
        return "met_floor" if actual >= low else "below_floor"
    if side == "ceiling":
        return "met_ceiling" if actual <= high else "above_ceiling"
    if low <= actual <= high:
        return "on_target" if low == high else "inside_range"
    return "above_range" if actual > high else "below_range"


def _econ_sign(metric: str, numerical: int, bound: Optional[str] = None) -> int:
    direction = metric_direction(metric)
    if direction == "two_sided" and not bound:
        return 0
    return -numerical if direction == "lower" else numerical


def _step_direction(prev: Tuple[Decimal, Decimal], cur: Tuple[Decimal, Decimal]) -> int:
    """+1 both ends up, −1 both ends down, 0 mixed (methodology §11.3)."""
    dl, dh = cur[0] - prev[0], cur[1] - prev[1]
    if dl >= 0 and dh >= 0 and (dl > 0 or dh > 0):
        return 1
    if dl <= 0 and dh <= 0 and (dl < 0 or dh < 0):
        return -1
    return 0


def _days(a: Optional[str], b: Optional[str]) -> Optional[int]:
    from datetime import date

    try:
        return (date.fromisoformat(str(b)[:10]) - date.fromisoformat(str(a)[:10])).days
    except (TypeError, ValueError):
        return None


def _vintages(o: GuidanceOutcome, issuance: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Opening band then each substantive revision, oldest first.

    Dropped: reaffirmations, and any repeat of a band already recorded on the same day
    (a re-run of an extract job must not add a revision). A different band on the same
    day as the previous vintage is a conflicting statement: the first one recorded
    stands and the vintage carries ``same_day_conflicts``.
    ``issuance`` maps a source URL to its stored public-availability date, which is
    used as the vintage time when known; the stated date stays in ``stated_as_of``.
    """
    held = issuance or {}

    def vintage(index: int, as_of: Optional[str], low: float, high: float, url: Optional[str], quote: Any) -> Dict[str, Any]:
        public = held.get(url or "")
        return {
            "index": index,
            "as_of": str(public)[:10] if public else as_of,
            "stated_as_of": as_of,
            "time_basis": "public_available_at" if public else "statement_date",
            "low": low,
            "high": high,
            "source_url": url,
            "quote": quote,
            "same_day_conflicts": 0,
        }

    low, high = _band(o)
    out = [vintage(0, o.guidance_as_of, low, high, o.guidance_source_url, o.guidance_quote)]
    seen = {(str(o.guidance_as_of or "")[:10], low, high)}
    for r in o.revisions or ():
        r_low = r.get("guided_low", r.get("guided_value"))
        r_high = r.get("guided_high", r.get("guided_value"))
        if r_low is None or r_high is None:
            continue
        r_low, r_high = sorted((float(r_low), float(r_high)))
        day = str(r.get("as_of") or "")[:10]
        if (day, r_low, r_high) in seen or (r_low, r_high) == (out[-1]["low"], out[-1]["high"]):
            continue
        seen.add((day, r_low, r_high))
        if day and day == str(out[-1]["stated_as_of"] or "")[:10]:
            out[-1]["same_day_conflicts"] += 1
            continue
        out.append(vintage(len(out), r.get("as_of"), r_low, r_high, r.get("source_url"), r.get("quote")))
    return out


def core_family_detail(
    o: GuidanceOutcome,
    *,
    period_end: Optional[str] = None,
    period_start: Optional[str] = None,
    ruleset: Optional[str] = None,
    company_id: Optional[str] = None,
    issuance: Optional[Dict[str, str]] = None,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Score one guidance family (one metric, one period): ``C_f = min(100, D_f × (1 − P_f) × L_f)``.

    The delivery ruleset sets ``P_f = 0`` and ``L_f = 1``; revisions are still counted and shown.
    """
    from app.services.score_policy import (
        CALCULATION_COMPUTED,
        CALCULATION_NOT_COMPUTABLE,
        ROUTE_QUANT,
        ROUTE_UNSCORABLE,
        core_route,
    )

    from dataclasses import replace

    rs = _ruleset(ruleset)
    locked = rs != CORE_RULESET_PROPOSAL
    r2 = rs == CORE_RULESET_R2
    lead_scored = rs in (CORE_RULESET_LOCKED, CORE_RULESET_R2)
    cutoff = str(as_of)[:10] if as_of else None
    if cutoff and o.actual_value is not None and o.as_of and str(o.as_of)[:10] > cutoff:
        o = replace(o, actual_value=None, restated_actual_value=None)
    route, reason = core_route(o)
    cadence = core_cadence(o.period)
    opening_as_of = str(_vintages(o, issuance)[0]["as_of"] or "")[:10]
    if cutoff and opening_as_of > cutoff:
        route, reason = ROUTE_UNSCORABLE, "FUTURE_SOURCE"
    if reason == "OUTCOME_NOT_DUE" and as_of and period_end:
        from datetime import date, timedelta

        due = date.fromisoformat(period_end) + timedelta(days=CORE_ACTUAL_DUE_DAYS[cadence])
        if str(as_of)[:10] > due.isoformat():
            route, reason = ROUTE_UNSCORABLE, "ACTUAL_UNAVAILABLE"
    family_id = core_family_id(company_id, o)
    base: Dict[str, Any] = {
        "family_id": family_id,
        "parameter": o.metric,
        "period": o.period,
        "cadence": cadence,
        **core_units(o),
        "reporting_basis": o.reporting_basis,
        "scope": o.scope,
        "route": route,
        "reason_code": reason,
        "flags": [],
        "score": None,
        "calculation_status": CALCULATION_NOT_COMPUTABLE,
        "actual_value": o.actual_value,
        "actual_as_of": o.as_of,
        "restated_actual_value": o.restated_actual_value,
        "period_start": period_start,
        "period_end": period_end,
        "vintages": [],
    }
    if route != ROUTE_QUANT:
        return base
    if period_end is None:
        return {**base, "reason_code": "PERIOD_END_UNKNOWN"}

    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        horizon = Decimal(CORE_HORIZON_DAYS[cadence])
        flags: List[str] = []
        vintages = _vintages(o, issuance)
        if any(v["same_day_conflicts"] for v in vintages):
            flags.append("SAME_DAY_CONFLICT")
        opening = vintages[0]
        lead = _days(opening["as_of"], period_end)
        base["lead_time_days"] = lead
        if lead is not None and lead < 0:
            return {**base, "reason_code": "GUIDANCE_AFTER_PERIOD_END"}
        if lead is not None and lead < CORE_LATE_GUIDANCE_DAYS:
            flags.append("LATE_GUIDANCE_FLAG")
        lead_factor = _ONE
        if lead_scored:
            if lead is None:
                return {**base, "reason_code": "ISSUANCE_TIME_UNKNOWN"}
            if r2:
                h_days = (_days(period_start, period_end) + 1) if period_start else int(horizon)
                l_days = lead + 1
                lead_factor = r2_lead_time_factor(l_days, h_days)
                base["lead_time"] = {
                    "horizon_type": cadence,
                    "h_days": h_days,
                    "l_days": l_days,
                    "r": _q(Decimal(l_days) / Decimal(h_days), "0.000001"),
                    "factor": _q(lead_factor, "0.000001"),
                    "interpolation_method": "LINEAR_NORMALISED",
                }
                if l_days > h_days:
                    flags.append("PRE_PERIOD_GUIDANCE")
            else:
                lead_factor = core_lead_time_factor(lead)

        def level(v: Dict[str, Any]) -> Tuple[Decimal, Decimal]:
            return _core_level(o.metric, _dec(v["low"]), rs), _core_level(o.metric, _dec(v["high"]), rs)

        open_band = level(opening)
        counted = 0
        n_eff = _ZERO
        eligible: List[Dict[str, Any]] = []
        weight = _ONE
        prev_band: Optional[Tuple[Decimal, Decimal]] = None
        prev_as_of: Optional[str] = None
        for v in vintages:
            band = level(v)
            row: Dict[str, Any] = {
                "vintage_id": core_vintage_id(family_id, v["as_of"], v["low"], v["high"], v["source_url"]),
                "index": v["index"],
                "as_of": v["as_of"],
                "stated_as_of": v["stated_as_of"],
                "time_basis": v["time_basis"],
                "low": v["low"],
                "high": v["high"],
                "source_url": v["source_url"],
                "quote": v["quote"],
                "same_day_conflicts": v["same_day_conflicts"],
                "literal_outcome": _literal_outcome(v["low"], v["high"], float(o.actual_value), o.bound),
                "eligible": True,
                "reason_code": None,
            }
            if v["index"] > 0 and v["as_of"] and (
                o.as_of and str(v["as_of"]) > str(o.as_of) or cutoff and str(v["as_of"])[:10] > cutoff
            ):
                row.update(eligible=False, reason_code="FUTURE_SOURCE")
                base["vintages"].append(row)
                continue
            gap_to_close = _days(v["as_of"], period_end) if v["index"] > 0 else None
            after_close = gap_to_close is not None and gap_to_close < 0
            if prev_band is not None:
                numerical = _step_direction(prev_band, band)
                if locked:
                    # §14.2: every substantive revision issued inside the target period.
                    row["direction"] = numerical
                    before_start = bool(period_start and v["as_of"] and str(v["as_of"])[:10] < period_start)
                    if not after_close and not before_start:
                        counted += 1
                        if r2:
                            kind = r2_revision_kind(o.metric, prev_band, band, o.bound)
                            row.update(revision_kind=kind, revision_weight=str(R2_REVISION_WEIGHTS[kind]))
                            n_eff += R2_REVISION_WEIGHTS[kind]
                else:
                    # Proposals D-05/D-06/D-08: weaker revisions only, up to the result date.
                    step = _econ_sign(o.metric, numerical, o.bound)
                    row["direction"] = step
                    if step < 0 or metric_direction(o.metric) == "two_sided" and not o.bound:
                        counted += 1
            prev_band = band
            if after_close:
                row.update(eligible=False, reason_code="GUIDANCE_AFTER_PERIOD_END")
                base["vintages"].append(row)
                continue
            if r2:
                terms = r2_vintage_terms(
                    o.metric, v["low"], v["high"], float(o.actual_value), bound=o.bound, prior_value=o.prior_value
                )
                z, z_reason = terms.pop("z"), terms.pop("reason_code")
                row.update(terms)
                if terms["scale_floor_applied"] and "SCALE_FLOOR_APPLIED" not in flags:
                    flags.append("SCALE_FLOOR_APPLIED")
            else:
                z, z_reason = core_vintage_z(
                    o.metric,
                    v["low"],
                    v["high"],
                    float(o.actual_value),
                    bound=o.bound,
                    prior_value=o.prior_value,
                    zero_reference=o.zero_reference,
                    ruleset=rs,
                )
            if z is None:
                if v["index"] == 0:
                    return {**base, "reason_code": z_reason, "vintages": [row]}
                row.update(eligible=False, reason_code=z_reason)
                base["vintages"].append(row)
                continue
            if v["index"] > 0:
                gap = _days(prev_as_of, v["as_of"])
                if gap is None:
                    gap = 0
                    if "ISSUANCE_TIME_UNKNOWN" not in flags:
                        flags.append("ISSUANCE_TIME_UNKNOWN")
                magnitude = core_revision_magnitude(
                    o.metric, open_band, band, ruleset=rs,
                    prior_value=o.prior_value, zero_reference=o.zero_reference,
                )
                if magnitude is None:
                    if "REVISION_MAGNITUDE_UNAVAILABLE" not in flags:
                        flags.append("REVISION_MAGNITUDE_UNAVAILABLE")
                else:
                    row["revision_magnitude"] = _q(magnitude)
                numerical = _step_direction(open_band, band)
                direction = numerical if locked else _econ_sign(o.metric, numerical, o.bound)
                weight = weight * core_weight_exponent(Decimal(max(gap, 0)) / horizon, magnitude, direction).exp()
            prev_as_of = v["as_of"]
            score = core_score_from_z(z)
            row.update(z=_q(z, "0.000001"), score=_q(score), raw_weight=weight)
            eligible.append(row)
            base["vintages"].append(row)

        total = sum((r["raw_weight"] for r in eligible), _ZERO)
        delivery = _ZERO
        for r in eligible:
            w = r.pop("raw_weight") / total
            r["weight"] = _q(w, "0.000001")
            delivery += w * _dec(r["score"])
        penalty = core_frequency_penalty(n_eff if r2 else counted, cadence, rs)
        family_score = min(_HUNDRED, delivery * (_ONE - penalty) * lead_factor)
        return {
            **base,
            "flags": flags,
            "delivery_score": _q(delivery),
            "revisions_counted": counted,
            "revisions_weighted": str(n_eff) if r2 else None,
            "frequency_penalty": _q(penalty),
            "lead_time_factor": _q(lead_factor) if lead_scored else None,
            "score": _q(family_score),
            "score_exact": str(family_score),
            "calculation_status": CALCULATION_COMPUTED,
        }


def core_qual_branch(commitments: Sequence[Dict[str, Any]], *, as_of: str) -> Dict[str, Any]:
    """Qual GCI (§10, §15.2, §16): equal families within a commitment type, equal types.

    An unresolved family widens the range instead of scoring zero (§10.4), so the
    branch is a point only when every due family is resolved.
    """
    from app.services.commitments import qual_family

    families = [f for f in (qual_family(c, as_of=as_of) for c in commitments) if f is not None]
    reason_counts: Dict[str, int] = {}
    by_param: Dict[str, List[Dict[str, Any]]] = {}
    for f in families:
        # R2 §7 with amendment A5: past its deadline, a commitment without evidence stays in
        # as an unresolved range (never zero, never dropped) and counts against coverage.
        if f["reason"] == "OUTCOME_NOT_DUE":
            f["evidence_status"] = "PENDING"
        elif f["low"] is None:
            f["evidence_status"] = None
        else:
            f["evidence_status"] = "AVAILABLE" if f["low"] == f["high"] else "UNAVAILABLE"
        if f["reason"]:
            reason_counts[f["reason"]] = reason_counts.get(f["reason"], 0) + 1
        if f["low"] is not None:
            by_param.setdefault(f["parameter"], []).append(f)
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        parameters: List[Dict[str, Any]] = []
        lows: List[Decimal] = []
        highs: List[Decimal] = []
        for name in sorted(by_param):
            rows = by_param[name]
            n = Decimal(len(rows))
            lo = sum((_HUNDRED * _dec(r["low"]) for r in rows), _ZERO) / n
            hi = sum((_HUNDRED * _dec(r["high"]) for r in rows), _ZERO) / n
            parameters.append({"parameter": name, "families": len(rows), "low": _q(lo), "high": _q(hi)})
            lows.append(lo)
            highs.append(hi)
        low = sum(lows, _ZERO) / Decimal(len(lows)) if lows else None
        high = sum(highs, _ZERO) / Decimal(len(highs)) if highs else None
    due = sum(1 for f in families if f["evidence_status"] in ("AVAILABLE", "UNAVAILABLE"))
    evidenced = sum(1 for f in families if f["evidence_status"] == "AVAILABLE")
    return {
        "coverage": {
            "qual_commitment_count": evidenced,
            "expected_family_count": due,
            "coverage_ratio": round(evidenced / due, 3) if due else None,
            "unresolved": due - evidenced,
            "pending": sum(1 for f in families if f["evidence_status"] == "PENDING"),
        },
        "as_of": as_of,
        "qual_gci": _q(low, "0.1") if low is not None and low == high else None,
        "qual_low": _q(low, "0.1"),
        "qual_high": _q(high, "0.1"),
        "qual_low_exact": None if low is None else str(low),
        "qual_high_exact": None if high is None else str(high),
        "parameters": parameters,
        "families": families,
        "reason_counts": reason_counts,
    }


def r2_headline_rule(coverage: Dict[str, Any]) -> str:
    """R2 §5: Quant is the headline until Qual has enough evidenced, due commitments.

    A5 keeps an unresolved commitment in as a range, and a range is not a level, so the
    Composite becomes the headline only once no due commitment is unresolved.
    """
    evidenced = int(coverage.get("qual_commitment_count") or 0)
    due = int(coverage.get("expected_family_count") or 0)
    if (
        evidenced >= R2_QUAL_MIN_COMMITMENTS
        and Decimal(evidenced) >= R2_QUAL_MIN_COVERAGE * Decimal(due)
        and not coverage.get("unresolved")
    ):
        return "COMPOSITE_PUBLISHED"
    return "QUANT_DOMINANT"


def r2_constants() -> Dict[str, Any]:
    return {
        "revision_weights": {k: str(v) for k, v in R2_REVISION_WEIGHTS.items()},
        "growth_floor_pp": str(R2_GROWTH_FLOOR_PP),
        "scale_rule": "max(width, |midpoint|, floor)" if R2_SCALE_INCLUDES_MIDPOINT else "max(width, floor)",
        "met_bound_scores_full": R2_MET_BOUND_SCORES_FULL,
        "lead_time": {"base": str(R2_LEAD_BASE), "slope": str(R2_LEAD_SLOPE), "method": "LINEAR_NORMALISED"},
        "headline_gate": {"min_commitments": R2_QUAL_MIN_COMMITMENTS, "min_coverage": str(R2_QUAL_MIN_COVERAGE),
                          "unresolved_allowed": 0},
        "calibration": dict(R2_CALIBRATION),
        "amendments": "docs/review/GCI_v2.4-R2_Reply_10_Nov_2026.md",
    }


def core_composite(quant: Optional[Decimal], qual_low: Optional[Decimal], qual_high: Optional[Decimal]) -> Dict[str, Any]:
    """§17: 0.8 Quant + 0.2 Qual; with one branch the composite is that branch, labelled."""
    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        if quant is not None and qual_low is not None and qual_high is not None:
            basis = "quant_and_qual"
            low = CORE_QUANT_WEIGHT * quant + CORE_QUAL_WEIGHT * qual_low
            high = CORE_QUANT_WEIGHT * quant + CORE_QUAL_WEIGHT * qual_high
        elif quant is not None:
            basis, low, high = "quant_only", quant, quant
        elif qual_low is not None and qual_high is not None:
            basis, low, high = "qual_only", qual_low, qual_high
        else:
            return {"composite_basis": None, "composite_gci": None, "composite_low": None,
                    "composite_high": None, "composite_exact": None}
    return {
        "composite_basis": basis,
        "composite_gci": _q(low, "0.1") if low == high else None,
        "composite_low": _q(low, "0.1"),
        "composite_high": _q(high, "0.1"),
        "composite_exact": str(low) if low == high else None,
    }


def _core_input_digest(
    outcomes: Sequence[GuidanceOutcome],
    market_id: str,
    ruleset: str,
    commitments: Sequence[Dict[str, Any]],
    as_of: Optional[str],
    company_id: Optional[str] = None,
    issuance_times: Optional[Dict[str, str]] = None,
    *,
    regime: Optional[str] = None,
    fy_end_mmdd: Optional[str] = None,
    audit_flags: Optional[Sequence[str]] = None,
) -> str:
    import hashlib
    import json
    from dataclasses import asdict

    def canon(d: Any) -> str:
        return json.dumps(d, sort_keys=True, separators=(",", ":"), default=str)

    payload = {
        "algorithm_id": core_algorithm_id(ruleset),
        "revision": CORE_REVISION,
        "market_id": market_id,
        "regime": regime,
        "fy_end_mmdd": fy_end_mmdd,
        "company_id": company_id,
        "audit_flags": sorted(audit_flags or []),
        "r2": r2_constants() if ruleset == CORE_RULESET_R2 else None,
        "issuance_times": dict(sorted((issuance_times or {}).items())),
        "rows": sorted((asdict(o) for o in outcomes), key=canon),
        "commitments": sorted(commitments, key=canon),
        "as_of": as_of,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compute_core_detail(
    outcomes: Sequence[GuidanceOutcome],
    *,
    market_id: str = "IN",
    regime: Optional[str] = None,
    fy_end_mmdd: Optional[str] = None,
    audit_flags: Optional[Sequence[str]] = None,
    commitments: Optional[Sequence[Dict[str, Any]]] = None,
    as_of: Optional[str] = None,
    ruleset: Optional[str] = None,
    company_id: Optional[str] = None,
    issuance_times: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Company GCI Core: Quant branch, Qual branch, and the 80/20 Composite (§15–§17).

    Pure: period bounds come from ``disclosures.period_bounds`` (calendar arithmetic only).
    ``as_of`` decides which commitments are due and is required when ``commitments`` is given.
    Under the delivery ruleset the headline is the Quant branch; Qual is reported beside it.
    """
    from app.data.markets import core_publication_status, gci_core_profile
    from app.data.metric_catalog import normalize_basis
    from app.services.disclosures import period_bounds
    from app.services.score_policy import (
        CALCULATION_COMPUTED,
        CALCULATION_NOT_COMPUTABLE,
        CALCULATION_PARTIAL,
        confidence_tier,
        core_record_state,
    )

    rs = _ruleset(ruleset)
    commitments = list(commitments or [])
    if commitments and not as_of:
        raise ValueError("as_of is required to score commitments")
    mid = (market_id or "IN").upper()
    profile = gci_core_profile(mid) or gci_core_profile("IN") or {}
    fy_end = fy_end_mmdd or profile.get("fy_end_mmdd")
    status, status_reason = core_publication_status(mid, regime)
    if status == "PUBLISHABLE" and not CORE_ENGINE_APPROVED:
        status, status_reason = "SHADOW", "UNAPPROVED_ENGINE"

    families = []
    for o in outcomes:
        bounds = period_bounds(o.period, mid, fy_end)
        families.append(core_family_detail(
            o,
            period_end=bounds[1].isoformat() if bounds else None,
            period_start=bounds[0].isoformat() if bounds else None,
            ruleset=rs,
            company_id=company_id,
            issuance=issuance_times,
            as_of=as_of,
        ))
    # A basis switch is a new family (its id differs); flag it so nobody reads it as continuity.
    last_basis: Dict[str, str] = {}
    for o, f in sorted(zip(outcomes, families), key=lambda p: (p[0].metric, str(p[1]["period_end"] or ""))):
        basis = normalize_basis(o.reporting_basis)
        if basis and last_basis.get(o.metric) not in (None, basis):
            f["flags"] = [*f["flags"], "BASIS_SWITCH"]
        if basis:
            last_basis[o.metric] = basis
    published = status == "PUBLISHABLE"
    for f in families:
        f["record_state"] = core_record_state(f["reason_code"], f["calculation_status"], published=published)
    reason_counts: Dict[str, int] = {}
    for f in families:
        for code in [f["reason_code"], *f["flags"]]:
            if code:
                reason_counts[code] = reason_counts.get(code, 0) + 1

    with localcontext() as ctx:
        ctx.prec = _CORE_PREC
        by_param: Dict[str, List[Decimal]] = {}
        for f in families:
            if f["calculation_status"] == CALCULATION_COMPUTED:
                by_param.setdefault(f["parameter"], []).append(Decimal(f["score_exact"]))
        deep = rs == CORE_RULESET_PROPOSAL and any(
            len(v) >= PROPOSAL_MIN_FAMILIES_PER_PARAMETER for v in by_param.values()
        )
        parameters: List[Dict[str, Any]] = []
        included: List[Decimal] = []
        for name in sorted(by_param):
            scores = by_param[name]
            g = sum(scores, _ZERO) / Decimal(len(scores))
            use = not deep or len(scores) >= PROPOSAL_MIN_FAMILIES_PER_PARAMETER
            parameters.append({
                "parameter": name,
                "score": _q(g),
                "families_computable": len(scores),
                "included": use,
            })
            if use:
                included.append(g)
        quant = sum(included, _ZERO) / Decimal(len(included)) if included else None

    qual = core_qual_branch(commitments, as_of=as_of or "")
    for code, n in qual["reason_counts"].items():
        reason_counts[code] = reason_counts.get(code, 0) + n
    q_low = None if qual["qual_low_exact"] is None else Decimal(qual["qual_low_exact"])
    q_high = None if qual["qual_high_exact"] is None else Decimal(qual["qual_high_exact"])
    if rs == CORE_RULESET_DELIVERY:
        composite = core_composite(quant, None, None)
    else:
        composite = core_composite(quant, q_low, q_high)
    headline_rule = r2_headline_rule(qual["coverage"]) if rs == CORE_RULESET_R2 else (
        "QUANT_ONLY" if rs == CORE_RULESET_DELIVERY else "COMPOSITE"
    )
    quant_headline = headline_rule in ("QUANT_ONLY", "QUANT_DOMINANT")
    if quant_headline:
        headline_gci = _q(quant, "0.1")
        headline_exact = None if quant is None else str(quant)
        lo = hi = headline_gci
    else:
        headline_gci, headline_exact = composite["composite_gci"], composite["composite_exact"]
        lo, hi = composite["composite_low"], composite["composite_high"]

    closed_periods = len({f["period"] for f in families if f["calculation_status"] == CALCULATION_COMPUTED})
    company_flags: List[str] = []
    if quant is not None and closed_periods < CORE_THIN_HISTORY_PERIODS:
        company_flags.append("THIN_HISTORY")
        reason_counts["THIN_HISTORY"] = reason_counts.get("THIN_HISTORY", 0) + 1
    quant_routed = [f for f in families if f["route"] == "QUANT"]
    computable = [f for f in families if f["calculation_status"] == CALCULATION_COMPUTED]
    coverage = {
        "families_total": len(families),
        "families_quant": len(quant_routed),
        "families_computable": len(computable),
        "computable_share": round(len(computable) / len(quant_routed), 3) if quant_routed else None,
        "parameters_computable": len(parameters),
        "closed_periods": closed_periods,
    }
    uncertainty = {
        "headline_low": lo,
        "headline_high": hi,
        "width": None if lo is None or hi is None else round(hi - lo, 1),
        "source": "unresolved commitments" if lo is not None and lo != hi else None,
    }
    if quant is None:
        calc = CALCULATION_NOT_COMPUTABLE
    elif any(f["route"] == "QUANT" and f["calculation_status"] != CALCULATION_COMPUTED for f in families):
        calc = CALCULATION_PARTIAL
    else:
        calc = CALCULATION_COMPUTED
    if status_reason:
        reason_counts[status_reason] = reason_counts.get(status_reason, 0) + 1
    method = gci_method(core_algorithm_id(rs)) or {}
    return {
        "algorithm_id": core_algorithm_id(rs),
        "method": {k: method.get(k) for k in ("code", "name", "version", "status")},
        "method_label": method_label(core_algorithm_id(rs)),
        "methodology_version": CORE_METHODOLOGY_VERSION,
        "ruleset": rs,
        "revision": CORE_REVISION,
        "market_id": mid,
        "publication_status": status,
        "publication_reason": status_reason,
        **composite,
        "quant_gci": _q(quant, "0.1"),
        "quant_gci_exact": None if quant is None else str(quant),
        "qual_gci": qual["qual_gci"],
        "qual_low": qual["qual_low"],
        "qual_high": qual["qual_high"],
        "calculation_status": calc,
        "confidence_tier": confidence_tier(
            closed_periods=closed_periods, metrics_scored=len(parameters)
        ) if quant is not None else None,
        "closed_periods": closed_periods,
        "company_flags": company_flags,
        "coverage": coverage,
        "uncertainty": uncertainty,
        "parameters": parameters,
        "families": families,
        "qual": {k: qual[k] for k in ("as_of", "parameters", "families", "coverage")},
        "reason_counts": reason_counts,
        "audit_flags_shown": sorted(audit_flags or []),
        "headline": "quant" if quant_headline else "composite",
        "headline_rule": headline_rule,
        "headline_gci": headline_gci,
        "headline_exact": headline_exact,
        "comparability": {"regime": regime, "flag": "CROSS_REGIME_UNCALIBRATED"} if rs == CORE_RULESET_R2 else None,
        "excluded_elements": list(CORE_DELIVERY_EXCLUDES) if rs == CORE_RULESET_DELIVERY else [],
        "constants": {
            "alpha": str(CORE_ALPHA),
            "lambda": str(CORE_LAMBDA),
            "eta": str(CORE_ETA),
            "horizon_days": dict(CORE_HORIZON_DAYS),
            "lead_time_steps": [[d, str(f)] for d, f in CORE_LEAD_TIME_STEPS] + [[None, str(CORE_LEAD_TIME_TOP)]],
            "late_guidance_days": CORE_LATE_GUIDANCE_DAYS,
            "composite_weights": {"quant": str(CORE_QUANT_WEIGHT), "qual": str(CORE_QUAL_WEIGHT)},
            "composite_calibration": "open (v2.5 change control)",
            "delivery_growth_floor_pp": str(DELIVERY_GROWTH_FLOOR_PP) if rs == CORE_RULESET_DELIVERY else None,
            "r2": r2_constants() if rs == CORE_RULESET_R2 else None,
        },
        "input_digest": _core_input_digest(
            outcomes, mid, rs, commitments, as_of, company_id, issuance_times,
            regime=regime, fy_end_mmdd=fy_end, audit_flags=audit_flags,
        ),
    }


# ---------------------------------------------------------------------------
# GCI method lab — research calculator (docs/PLAN_GCI_CORE.md, r7)
# ---------------------------------------------------------------------------
# Every scoring rule put forward for the GCI (the five named methods, the owner's
# diffusion note and the rules tested in the 12 Nov algorithm scan), each with its
# parameters, the range each may take, and named presets. The lab scores one vintage
# per figure and rolls rows up with the settings shown; the engine levels for the named
# methods (revisions, lead time and commitments included) are reported beside it.
# Pure. Nothing here is a published level, enters the ledger or ranks a company.

#: The column every other comparison is read against until the owner names a base.
LAB_BASE_METHOD = "classic"
LAB_MAX_COMPARISONS = 8
#: Behaviour checks: a growth figure whose true expectation is 5% with a 1.5 pp spread.
LAB_CHECK_METRIC = "revenue_growth_cc_pct"
LAB_CHECK_MEAN = 5.0
LAB_CHECK_SD = 1.5
#: Half-width of an honest 80% range (1.2816 σ).
LAB_CHECK_HONEST_HALF_WIDTH = round(1.2815516 * LAB_CHECK_SD, 2)


def _p(key: str, label: str, default: Any, *, kind: str = "number", lo: Any = None, hi: Any = None,
       step: Any = None, unit: str = "", help: str = "", options: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"key": key, "label": label, "kind": kind, "default": default, "unit": unit, "help": help}
    if kind == "number":
        spec.update({"min": lo, "max": hi, "step": step})
    if options is not None:
        spec["options"] = options
    return spec


_POINTS_PER_UNIT = _p(
    "points_per_unit", "Points lost per unit of error", 12.5, lo=1, hi=50, step=0.5, unit="points",
    help="A unit is one percentage point for growth rates and margins, one per cent of the guided midpoint for amounts.",
)
_WIDTH_CHARGE = _p(
    "width_charge", "Charge per unit of range width", 0.1, lo=0, hi=0.5, step=0.01,
    help="0.1 is the interval-score charge for an 80% range (α / 2 with α = 0.2). 0 ignores width.",
)
_GROWTH_FLOOR = "growth_floor_pp"

#: Settings that turn row scores into one company level. Each method sets its own defaults.
LAB_ROLLUP_PARAMS: Tuple[Dict[str, Any], ...] = (
    _p("vintage", "Guidance scored", "opening", kind="choice",
       options=[{"value": "opening", "label": "Opening guidance for the period"},
                {"value": "final", "label": "Last revision before results"}],
       help="Scoring the last revision rewards walking guidance to the result."),
    _p("half_life_periods", "Recency half-life", 3.0, lo=0, hi=10, step=0.5, unit="periods",
       help="A period this many periods older counts half as much. 0 weights every period equally."),
    _p("metric_weight_cap", "Evidence weight cap", 5, lo=1, hi=10, step=1, unit="periods",
       help="A metric weighs its number of closed periods, up to this cap. 1 weights every metric equally."),
    _p("min_periods_per_metric", "Closed periods before a metric counts", 2, lo=1, hi=5, step=1, unit="periods",
       help="Thinner metrics are shown, not counted, while a deeper metric exists."),
    _p("weight_by_confidence", "Weight periods by extraction confidence", False, kind="toggle",
       help="GCI Classic weights each period by the confidence recorded on its rows."),
    _p("audit_deduction", "Apply audit-flag deductions", False, kind="toggle",
       help="Reviewer-set withdrawal, restatement and definition-shift flags take points off the level, as in GCI Classic."),
)
#: Which closed rows the lab reads. ``published`` = rows the published method may score.
LAB_ROW_SCOPES = ("published", "all_closed")

LAB_METHODS: Tuple[Dict[str, Any], ...] = (
    {
        "code": "classic",
        "name": "GCI Classic",
        "version": "v4",
        "gci_method": "classic",
        "kind": "accuracy",
        "status": "published",
        "formula": "Inside the guided range (widened to the width floor) 100. Outside: decay = exp(−α δ^β), "
        "δ = distance beyond the range in half-widths. Beat = floor + (100 − floor) × decay; "
        "miss = 100 − γ (100 − 100 × decay).",
        "summary": "The published level. Beats decay toward a floor; misses decay faster than beats.",
        "params": [
            _p("beat_floor", "Lowest score for a beat", GCI_BEAT_FLOOR, lo=0, hi=100, step=5, unit="points",
               help="v4 floors beats at 60; v3 lets them decay to 0."),
            _p("gamma_miss", "Miss multiplier γ", GCI_GAMMA_MISS, lo=1, hi=3, step=0.1),
            _p("alpha", "Decay rate α", GCI_ALPHA, lo=0.05, hi=1.5, step=0.05),
            _p("beta", "Decay shape β", GCI_BETA, lo=0.5, hi=2.5, step=0.05),
        ],
        "presets": [
            {"id": "published", "label": "As published (v4)", "params": {}},
            {"id": "v3", "label": "v3: beats decay to 0", "params": {"beat_floor": 0.0}},
            {"id": "lenient_beats", "label": "Beats floored at 80", "params": {"beat_floor": 80.0}},
            {"id": "harsh_misses", "label": "Misses ×2", "params": {"gamma_miss": 2.0}},
        ],
        "rollup_defaults": {"half_life_periods": round(math.log(2) / GCI_LAMBDA, 2), "metric_weight_cap": METRIC_WEIGHT_CAP,
                            "min_periods_per_metric": MIN_CLOSED_PERIODS_PER_METRIC, "weight_by_confidence": True,
                            "audit_deduction": True},
    },
    {
        "code": "core",
        "name": "GCI Core",
        "version": "v2.4",
        "gci_method": "core",
        "kind": "accuracy",
        "status": "shadow",
        "formula": "100 × (1 − |actual − midpoint| / reference); reference (|low| + |high|) / 2 as locked.",
        "summary": "The approved v2.4 methodology. A miss is read relative to the size of the guided figure.",
        "params": [
            _p("reference", "Scale of a miss", "abs_bounds", kind="choice",
               options=[{"value": "abs_bounds", "label": "(|low| + |high|) / 2 (v2.4)"},
                        {"value": "max_mid_width", "label": "Larger of |midpoint| and width (D-03)"},
                        {"value": "midpoint", "label": "|midpoint|"}]),
            _p(_GROWTH_FLOOR, "Growth scale floor", 0.0, lo=0, hi=20, step=0.5, unit="pp",
               help="A growth miss is read against at least this many points. 0 = none (v2.4 as written)."),
            _p("favourable_bound_rate", "Share charged for beating a floor or ceiling", 1.0, lo=0, hi=1, step=0.1,
               help="1 charges a beaten bound like a missed one (v2.4)."),
        ],
        "presets": [
            {"id": "locked", "label": "Locked v2.4", "params": {}},
            {"id": "d03", "label": "With D-03 reference", "params": {"reference": "max_mid_width"}},
            {"id": "growth_floor_5", "label": "5 pp growth floor", "params": {_GROWTH_FLOOR: 5.0}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "range",
        "name": "GCI Range",
        "version": "v2.4-R2",
        "gci_method": "range",
        "kind": "accuracy",
        "status": "pending_ruling",
        "formula": "Inside the promise 100. Outside: 100 × (1 − distance to the nearest bound / scale), "
        "scale = max(width, |midpoint|, growth floor).",
        "summary": "A result inside the guided range scores 100; a miss is read against the larger of width, "
        "midpoint and a growth floor.",
        "params": [
            _p(_GROWTH_FLOOR, "Growth scale floor", float(R2_GROWTH_FLOOR_PP), lo=0, hi=20, step=0.5, unit="pp"),
            _p("scale_includes_midpoint", "Scale includes |midpoint| (A1)", R2_SCALE_INCLUDES_MIDPOINT, kind="toggle",
               help="Off reproduces R2 as written: a miss is read against width alone."),
            _p("met_bound_full", "A met floor or ceiling scores 100 (A2)", R2_MET_BOUND_SCORES_FULL, kind="toggle"),
        ],
        "presets": [
            {"id": "with_amendments", "label": "R2 with A1–A5", "params": {}},
            {"id": "as_written", "label": "R2 as written", "params": {"scale_includes_midpoint": False,
                                                                     "met_bound_full": False}},
            {"id": "no_floor", "label": "No growth floor", "params": {_GROWTH_FLOOR: 0.0}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "delivery",
        "name": "GCI Delivery",
        "version": "v1",
        "gci_method": "delivery",
        "kind": "accuracy",
        "status": "alternative",
        "formula": "GCI Core row score with a growth scale floor; no revision-count, lead-time or commitments weight.",
        "summary": "Guidance against the reported result only.",
        "params": [
            _p(_GROWTH_FLOOR, "Growth scale floor", float(DELIVERY_GROWTH_FLOOR_PP), lo=0, hi=20, step=0.5, unit="pp"),
        ],
        "presets": [
            {"id": "v1", "label": "Delivery v1", "params": {}},
            {"id": "floor_5", "label": "5 pp floor", "params": {_GROWTH_FLOOR: 5.0}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "draft",
        "name": "GCI Draft",
        "version": "v2.5",
        "gci_method": "draft",
        "kind": "accuracy",
        "status": "change_control",
        "formula": "GCI Core with the v2.5 proposals: reference max(|midpoint|, width), a beaten bound charged at "
        "a share, growth scored on its implied level (D-02, withdrawn as built).",
        "summary": "The team's change-control proposals, for impact analysis.",
        "params": [
            _p("favourable_bound_rate", "Share charged for beating a floor or ceiling",
               float(PROPOSAL_FAVOURABLE_BOUND_RATE), lo=0, hi=1, step=0.1),
            _p("implied_growth_level", "Score growth on its implied level (D-02)", True, kind="toggle",
               help="Withdrawn: Infosys FY24 (guided 4–7%, reported 1.4%) scores 96.1."),
        ],
        "presets": [
            {"id": "as_built", "label": "v2.5 proposals as built", "params": {}},
            {"id": "without_d02", "label": "Without D-02", "params": {"implied_growth_level": False}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "range_p",
        "name": "Range-P",
        "version": "proposed",
        "gci_method": None,
        "kind": "accuracy",
        "status": "research",
        "formula": "clip(100 − K × (c × width + distance outside the range − allowance), 0, 100).",
        "summary": "Proper range score from the 12 Nov scan: no reward for guiding low or for wider ranges; "
        "a 1 pp miss costs the same at 2% and 20% growth.",
        "params": [
            _POINTS_PER_UNIT,
            _WIDTH_CHARGE,
            _p("allowance", "Allowance", 0.2, lo=0, hi=2, step=0.05, unit="units",
               help="0.2 = width charge × a typical 2-point range, so a typical range that contains the result scores 100."),
        ],
        "presets": [
            {"id": "scan", "label": "As in the scan", "params": {}},
            {"id": "strict", "label": "Strict (20 points per pp)", "params": {"points_per_unit": 20.0}},
            {"id": "lenient", "label": "Lenient (8 points per pp)", "params": {"points_per_unit": 8.0}},
        ],
        "rollup_defaults": {"half_life_periods": 3.0, "metric_weight_cap": 5, "min_periods_per_metric": 1},
    },
    {
        "code": "interval",
        "name": "Interval score",
        "version": "Gneiting–Raftery 2007",
        "gci_method": None,
        "kind": "accuracy",
        "status": "research",
        "formula": "max(0, 100 − K × (c × width + distance outside the range)).",
        "summary": "The textbook proper score for a range. Range-P without the allowance or the cap.",
        "params": [_POINTS_PER_UNIT, _WIDTH_CHARGE],
        "presets": [{"id": "linear", "label": "Linear, 80% range", "params": {}}],
        "rollup_defaults": {"half_life_periods": 3.0, "metric_weight_cap": 5, "min_periods_per_metric": 1},
    },
    {
        "code": "midpoint_pp",
        "name": "Midpoint error in points",
        "version": "research",
        "gci_method": None,
        "kind": "accuracy",
        "status": "research",
        "formula": "max(0, 100 − K × |actual − midpoint|).",
        "summary": "Distance from the guided midpoint in points. Cannot see the range: 0–30% scores like a point guide of 15%.",
        "params": [_POINTS_PER_UNIT],
        "presets": [{"id": "scan", "label": "As in the scan", "params": {}}],
        "rollup_defaults": {"half_life_periods": 3.0, "metric_weight_cap": 5, "min_periods_per_metric": 1},
    },
    {
        "code": "mape",
        "name": "Relative error",
        "version": "MAPE",
        "gci_method": None,
        "kind": "accuracy",
        "status": "research",
        "formula": "max(0, 100 × (1 − |actual − midpoint| / (|midpoint| × full scale))).",
        "summary": "Error as a share of the guided midpoint. Fails near zero growth: a 1 pp miss on 2% scores 0.",
        "params": [
            _p("full_scale", "Error that scores 0", 1.0, lo=0.1, hi=2, step=0.05, unit="× midpoint"),
        ],
        "presets": [{"id": "plain", "label": "Plain MAPE", "params": {}}],
        "rollup_defaults": {"half_life_periods": 3.0, "metric_weight_cap": 5, "min_periods_per_metric": 1},
    },
    {
        "code": "hit_rate",
        "name": "Hit rate",
        "version": "tracker",
        "gci_method": None,
        "kind": "hit",
        "status": "research",
        "formula": "100 if the result lands inside the guided range (plus tolerance), else 0.",
        "summary": "What most tracker products publish: share of figures delivered inside the range.",
        "params": [
            _p("tolerance_pct", "Tolerance", 0.0, lo=0, hi=5, step=0.5, unit="% of midpoint"),
            _p("beat_counts", "A beat counts as a hit", False, kind="toggle"),
        ],
        "presets": [
            {"id": "strict", "label": "Inside the range", "params": {}},
            {"id": "met_or_beat", "label": "Met or beat", "params": {"beat_counts": True}},
            {"id": "tolerance_1", "label": "±1% tolerance", "params": {"tolerance_pct": 1.0}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "diffusion",
        "name": "Diffusion",
        "version": "owner v2.5 note",
        "gci_method": None,
        "kind": "direction",
        "status": "research",
        "formula": "50 + 50 × clamp((actual − midpoint) / (max(|midpoint|, floor) × full scale), −1, 1).",
        "summary": "Signed, 50-centred: above 50 the result was above the midpoint. Measures direction, not reliability.",
        "params": [
            _p("full_scale", "Deviation that reaches 0 or 100", 1.0, lo=0.05, hi=2, step=0.05, unit="× midpoint"),
            _p(_GROWTH_FLOOR, "Growth scale floor", 0.0, lo=0, hi=20, step=0.5, unit="pp"),
            _p("use_direction", "Respect metric direction", False, kind="toggle",
               help="On: a cost above guidance reads below 50; a two-sided metric reads below 50 either way."),
        ],
        "presets": [
            {"id": "owner_note", "label": "As in the owner's note", "params": {}},
            {"id": "guidance_bias", "label": "Guidance Bias (team proposal)",
             "params": {_GROWTH_FLOOR: 5.0, "use_direction": True}},
        ],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
    {
        "code": "rubric",
        "name": "Conversation rubric",
        "version": "paper 1",
        "gci_method": None,
        "kind": "direction",
        "status": "research",
        "formula": "Relative error to the midpoint with a tolerance band, a beat bonus and a miss penalty down to −100.",
        "summary": "Pays for results above guidance; shown for comparison with the scan.",
        "params": [
            _p("tau", "In-line band", 0.01, lo=0.0025, hi=0.05, step=0.0025, unit="× midpoint"),
            _p("miss_alpha", "Miss slope", 45.0, lo=10, hi=100, step=5),
        ],
        "presets": [{"id": "paper", "label": "As in paper 1", "params": {}}],
        "rollup_defaults": {"half_life_periods": 0.0, "metric_weight_cap": 1, "min_periods_per_metric": 1},
    },
)

#: Comparisons a reader in each role usually starts from. A starting point, not a ruling.
LAB_ACTOR_VIEWS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "methodology_owner",
        "label": "Methodology owner / PM",
        "question": "Which method should be the base, and what moves if it changes?",
        "comparisons": [("classic", "published"), ("core", "locked"), ("range", "with_amendments"),
                        ("range_p", "scan"), ("diffusion", "owner_note")],
    },
    {
        "id": "analyst",
        "label": "Research analyst",
        "question": "Does the level match how the desk reads the delivery record?",
        "comparisons": [("classic", "published"), ("range_p", "scan"), ("hit_rate", "strict"),
                        ("hit_rate", "met_or_beat")],
    },
    {
        "id": "portfolio_manager",
        "label": "Portfolio manager",
        "question": "How reliable is the guidance, and does management guide low or high?",
        "comparisons": [("classic", "published"), ("range_p", "scan"), ("diffusion", "guidance_bias")],
    },
    {
        "id": "quant",
        "label": "Quant researcher",
        "question": "Which rule is proper and stable enough to backtest?",
        "comparisons": [("range_p", "scan"), ("interval", "linear"), ("midpoint_pp", "scan"), ("mape", "plain"),
                        ("classic", "published")],
    },
    {
        "id": "ir_officer",
        "label": "Investor relations",
        "question": "How does our guidance record read under each method a desk might use?",
        "comparisons": [("classic", "published"), ("range", "with_amendments"), ("hit_rate", "met_or_beat"),
                        ("diffusion", "guidance_bias")],
    },
)


def lab_method(code: str) -> Dict[str, Any]:
    held = next((m for m in LAB_METHODS if m["code"] == code), None)
    if held is None:
        raise ValueError(f"unknown lab method {code!r}; one of {[m['code'] for m in LAB_METHODS]}")
    return held


def _lab_coerce(spec: Dict[str, Any], value: Any) -> Any:
    kind = spec["kind"]
    if kind == "toggle":
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if kind == "choice":
        allowed = [o["value"] for o in spec["options"]]
        if value not in allowed:
            raise ValueError(f"{spec['key']} must be one of {allowed}")
        return value
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{spec['key']} must be a number") from None
    if not math.isfinite(num):
        raise ValueError(f"{spec['key']} must be finite")
    return min(max(num, float(spec["min"])), float(spec["max"]))


def lab_resolve(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Method defaults, then the preset, then explicit values, each clamped to its range."""
    method = lab_method(str(comparison.get("method") or ""))
    preset_id = comparison.get("preset") or method["presets"][0]["id"]
    preset = next((p for p in method["presets"] if p["id"] == preset_id), None)
    if preset is None:
        raise ValueError(f"unknown preset {preset_id!r} for {method['code']}")
    specs = {s["key"]: s for s in method["params"]}
    roll_specs = {s["key"]: s for s in LAB_ROLLUP_PARAMS}
    explicit = dict(comparison.get("params") or {})
    rollup_in = dict(comparison.get("rollup") or {})
    for key in explicit:
        if key not in specs:
            raise ValueError(f"{method['code']} has no parameter {key!r}")
    for key in rollup_in:
        if key not in roll_specs:
            raise ValueError(f"no roll-up setting {key!r}")
    merged = {**{k: s["default"] for k, s in specs.items()}, **preset["params"], **explicit}
    params = {k: _lab_coerce(s, merged[k]) for k, s in specs.items()}
    rollup_raw = {**{k: s["default"] for k, s in roll_specs.items()}, **method["rollup_defaults"], **rollup_in}
    rollup = {k: _lab_coerce(s, rollup_raw[k]) for k, s in roll_specs.items()}
    changed = sorted(k for k in specs if params[k] != _lab_coerce(specs[k], specs[k]["default"]))
    cid = str(comparison.get("id") or f"{method['code']}:{preset['id']}")
    return {
        "id": cid,
        "method": method["code"],
        "method_name": method["name"],
        "method_version": method["version"],
        "kind": method["kind"],
        "status": method["status"],
        "gci_method": method["gci_method"],
        "preset": preset["id"],
        "preset_label": preset["label"],
        "label": str(comparison.get("label") or f"{method['name']} · {preset['label']}"),
        "params": params,
        "params_changed": changed,
        "rollup": rollup,
    }


def _lab_side(low: float, high: float, bound: Optional[str]) -> Tuple[Optional[float], Optional[float], float]:
    """(lower edge, upper edge, reference point) of the promise; an open side is None."""
    side = (bound or "").strip().lower()
    if side == "floor":
        return low, None, low
    if side == "ceiling":
        return None, high, high
    return low, high, (low + high) / 2.0


def lab_tag(metric: str, low: float, high: float, actual: float, bound: Optional[str] = None) -> str:
    """beat | in_line | miss | outside_range (two-sided metrics), set by the metric's direction."""
    lo, hi, _ = _lab_side(low, high, bound)
    if (lo is None or actual >= lo) and (hi is None or actual <= hi):
        return "in_line"
    direction = metric_direction(metric)
    if direction == "two_sided":
        return "outside_range"
    above = hi is not None and actual > hi
    good = above if direction != "lower" else not above
    return "beat" if good else "miss"


def _lab_units(metric: str, ref: float) -> Optional[float]:
    """Multiplier from the metric's own unit to lab units: 1 for rates, 100 / |midpoint| for amounts."""
    from app.data.metric_catalog import metric_is_rate

    if metric_is_rate(metric):
        return 1.0
    return None if ref == 0 else 100.0 / abs(ref)


def lab_row_score(
    method: str,
    params: Dict[str, Any],
    metric: str,
    low: float,
    high: float,
    actual: float,
    *,
    bound: Optional[str] = None,
    prior_value: Optional[float] = None,
) -> Dict[str, Any]:
    """Score one figure under one method; ``{"score": None, "reason": ...}`` when the rule cannot."""
    low, high = (low, high) if low <= high else (high, low)
    lo, hi, ref = _lab_side(low, high, bound)
    if method == "classic":
        o = GuidanceOutcome(period="lab", metric=metric, guided_value=ref, actual_value=actual, guided_text="",
                            guided_low=low, guided_high=high)
        s = _outcome_score_exp(o, float(params["beat_floor"]), alpha=float(params["alpha"]),
                               beta=float(params["beta"]), gamma=float(params["gamma_miss"]), check_policy=False)
        return {"score": None if s is None else round(s, 2), "reason": None}
    if method in ("core", "delivery", "draft"):
        ruleset = CORE_RULESET_LOCKED
        kw: Dict[str, Any] = {"growth_floor_pp": params.get(_GROWTH_FLOOR, 0.0)}
        if method == "core":
            kw.update(reference=params["reference"], favourable_bound_rate=params["favourable_bound_rate"])
        elif method == "draft":
            ruleset = CORE_RULESET_PROPOSAL if params["implied_growth_level"] else CORE_RULESET_LOCKED
            kw.update(reference="max_mid_width", favourable_bound_rate=params["favourable_bound_rate"])
        z, reason = core_vintage_z(metric, low, high, actual, bound=bound, prior_value=prior_value,
                                   ruleset=ruleset, **kw)
        return {"score": None if z is None else _q(core_score_from_z(z), "0.01"), "reason": reason}
    if method == "range":
        terms = r2_vintage_terms(metric, low, high, actual, bound=bound, prior_value=prior_value,
                                 growth_floor_pp=params[_GROWTH_FLOOR],
                                 scale_includes_midpoint=bool(params["scale_includes_midpoint"]),
                                 met_bound_full=bool(params["met_bound_full"]))
        z = terms["z"]
        return {"score": None if z is None else _q(core_score_from_z(z), "0.01"), "reason": terms["reason_code"]}
    if method == "hit_rate":
        tol = abs(ref) * float(params["tolerance_pct"]) / 100.0
        inside = (lo is None or actual >= lo - tol) and (hi is None or actual <= hi + tol)
        beat = lab_tag(metric, low, high, actual, bound) == "beat"
        return {"score": 100.0 if inside or (params["beat_counts"] and beat) else 0.0, "reason": None}
    if method in ("mape", "rubric", "diffusion"):
        scale = abs(ref)
        if method == "diffusion":
            from app.data.metric_catalog import metric_is_growth

            if metric_is_growth(metric):
                scale = max(scale, float(params[_GROWTH_FLOOR]))
        if scale == 0:
            return {"score": None, "reason": "ZERO_MIDPOINT"}
        e = (actual - ref) / scale
        if method == "mape":
            return {"score": round(max(0.0, 100.0 * (1.0 - abs(e) / float(params["full_scale"]))), 2), "reason": None}
        if method == "diffusion":
            if params["use_direction"]:
                direction = metric_direction(metric)
                e = -e if direction == "lower" else -abs(e) if direction == "two_sided" else e
            return {"score": round(50.0 + 50.0 * max(-1.0, min(1.0, e / float(params["full_scale"]))), 2),
                    "reason": None}
        tau, a = float(params["tau"]), float(params["miss_alpha"])
        if abs(e) <= tau:
            s = 100.0
        elif tau < e <= 2.5 * tau:
            s = 90.0 - 10.0 * ((e - tau) / tau)
        elif e > 2.5 * tau:
            s = max(40.0, 75.0 - 15.0 * ((e - 2.5 * tau) / tau))
        else:
            s = max(-100.0, 20.0 - 1.5 * a * ((abs(e) - tau) / tau))
        return {"score": round(s, 2), "reason": None}
    # Unit-based rules: points for rates, per cent of the guided midpoint for amounts.
    unit = _lab_units(metric, ref)
    if unit is None:
        return {"score": None, "reason": "ZERO_MIDPOINT"}
    k = float(params["points_per_unit"])
    if method == "midpoint_pp":
        return {"score": round(max(0.0, 100.0 - k * abs(actual - ref) * unit), 2), "reason": None}
    outside = (max(0.0, lo - actual) if lo is not None else 0.0) + (max(0.0, actual - hi) if hi is not None else 0.0)
    width = (hi - lo) if lo is not None and hi is not None else 0.0
    charge = float(params["width_charge"]) * width * unit + outside * unit
    if method == "interval":
        return {"score": round(max(0.0, 100.0 - k * charge), 2), "reason": None}
    if method == "range_p":
        return {"score": round(max(0.0, min(100.0, 100.0 - k * (charge - float(params["allowance"])))), 2),
                "reason": None}
    raise ValueError(f"unknown lab method {method!r}")


def _lab_band(o: GuidanceOutcome, vintage: str) -> Tuple[float, float]:
    if vintage == "final":
        band = final_band(o)
        if band is not None:
            return band
    return _band(o)


def lab_closed_rows(outcomes: Sequence[GuidanceOutcome]) -> List[GuidanceOutcome]:
    """Rows the published method may score: closed, cited, reviewed and comparable."""
    from app.services.score_policy import excluded_from_score

    return [
        o for o in outcomes
        if not (o.unmapped or o.dropped) and o.actual_value is not None and not excluded_from_score(o)
    ]


def lab_rollup(rows: Sequence[Dict[str, Any]], rollup: Dict[str, Any], *, deduction: float = 0.0) -> Dict[str, Any]:
    """Company level from ``{"period", "metric", "score", "confidence"}`` rows with the roll-up settings,
    less ``deduction`` audit-flag points."""
    from app.services.changes import sort_periods

    scored = [r for r in rows if r.get("score") is not None]
    if not scored:
        return {"level": None, "by_metric": {}, "context_metrics": {}, "weights": {}, "audit_deduction": 0.0}
    rank = {p: i for i, p in enumerate(reversed(sort_periods(list({r["period"] for r in scored}))))}
    hl = float(rollup["half_life_periods"])
    by_conf = bool(rollup.get("weight_by_confidence"))
    by_metric: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}
    for r in scored:
        conf = min(max(float(r.get("confidence") or 1.0), 0.5), 1.0)
        by_metric.setdefault(r["metric"], {}).setdefault(r["period"], []).append((float(r["score"]), conf))
    metric_level: Dict[str, float] = {}
    periods_n: Dict[str, int] = {}
    for metric, per in by_metric.items():
        num = den = 0.0
        for period, vals in per.items():
            w = 0.5 ** (rank[period] / hl) if hl > 0 else 1.0
            if by_conf:
                w *= sum(c for _, c in vals) / len(vals)
            num += w * (sum(s for s, _ in vals) / len(vals))
            den += w
        metric_level[metric] = num / den
        periods_n[metric] = len(per)
    need = int(rollup["min_periods_per_metric"])
    deep = {m for m, n in periods_n.items() if n >= need}
    counted = deep or set(metric_level)
    cap = int(rollup["metric_weight_cap"])
    weights = {m: float(min(periods_n[m], cap)) for m in counted}
    total = sum(weights.values())
    level = sum(metric_level[m] * w for m, w in weights.items()) / total
    if deduction:
        level = max(0.0, min(100.0, level - deduction))
    return {
        "level": round(level, 1),
        "audit_deduction": deduction,
        "by_metric": {m: round(metric_level[m], 1) for m in sorted(counted)},
        "context_metrics": {m: round(v, 1) for m, v in sorted(metric_level.items()) if m not in counted},
        "weights": weights,
    }


def lab_run(
    outcomes: Sequence[GuidanceOutcome],
    comparisons: Sequence[Dict[str, Any]],
    *,
    row_scope: str = "published",
    audit_flags: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Score every closed row under each resolved comparison and roll each up to a level.

    ``row_scope="all_closed"`` also reads closed rows awaiting a guidance citation or review,
    as the Core engine does in shadow. Never a published set.
    """
    from app.services.score_policy import excluded_from_score

    if row_scope not in LAB_ROW_SCOPES:
        raise ValueError(f"row_scope must be one of {list(LAB_ROW_SCOPES)}")
    if row_scope == "published":
        rows = lab_closed_rows(outcomes)
    else:
        rows = [o for o in outcomes if not (o.unmapped or o.dropped) and o.actual_value is not None]
    table: List[Dict[str, Any]] = []
    for o in rows:
        entry: Dict[str, Any] = {"period": o.period, "metric": o.metric, "bound": o.bound,
                                 "actual": o.actual_value, "confidence": o.confidence,
                                 "published_eligible": not excluded_from_score(o),
                                 "scores": {}, "bands": {}, "tags": {}, "reasons": {}}
        for c in comparisons:
            low, high = _lab_band(o, c["rollup"]["vintage"])
            res = lab_row_score(c["method"], c["params"], o.metric, low, high, float(o.actual_value),
                                bound=o.bound, prior_value=o.prior_value)
            entry["scores"][c["id"]] = res["score"]
            entry["bands"][c["id"]] = [low, high]
            entry["tags"][c["id"]] = lab_tag(o.metric, low, high, float(o.actual_value), o.bound)
            if res["reason"]:
                entry["reasons"][c["id"]] = res["reason"]
        opening = _band(o)
        entry.update(low=opening[0], high=opening[1], tag=lab_tag(o.metric, opening[0], opening[1],
                                                                 float(o.actual_value), o.bound),
                     revisions=len(o.revisions))
        table.append(entry)
    levels = {}
    deduction = audit_deduction(outcomes, audit_flags)
    for c in comparisons:
        levels[c["id"]] = lab_rollup(
            [{"period": r["period"], "metric": r["metric"], "score": r["scores"][c["id"]],
              "confidence": r["confidence"]} for r in table],
            c["rollup"],
            deduction=deduction if c["rollup"].get("audit_deduction") else 0.0,
        )
    return {"rows": table, "levels": levels, "rows_scored": len(table), "row_scope": row_scope}


def _lab_expected(method: str, params: Dict[str, Any], low: float, high: float) -> float:
    """Expected row score when the result is normal around the check mean (deterministic quadrature)."""
    n, span = 241, 6.0
    num = den = 0.0
    for i in range(n):
        x = -span + 2 * span * i / (n - 1)
        w = math.exp(-0.5 * x * x)
        s = lab_row_score(method, params, LAB_CHECK_METRIC, low, high, LAB_CHECK_MEAN + LAB_CHECK_SD * x)["score"]
        if s is None:
            continue
        num += w * s
        den += w
    return num / den if den else float("nan")


def lab_behaviour(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """The scan's checks for one resolved comparison, on a growth figure (5% expected, 1.5 pp spread)."""
    m, p = comparison["method"], comparison["params"]
    hw = LAB_CHECK_HONEST_HALF_WIDTH
    honest = _lab_expected(m, p, LAB_CHECK_MEAN - hw, LAB_CHECK_MEAN + hw)
    shifts = [i * 0.25 for i in range(17)]
    lowball = [(s, _lab_expected(m, p, LAB_CHECK_MEAN - hw - s, LAB_CHECK_MEAN + hw - s)) for s in shifts]
    best_shift, best_low = max(lowball, key=lambda t: t[1])
    widths = [0.25 * i for i in range(1, 25)]
    by_width = [(w, _lab_expected(m, p, LAB_CHECK_MEAN - w, LAB_CHECK_MEAN + w)) for w in widths]
    w_best, w_score = max(by_width, key=lambda t: t[1])
    flat = max(s for _, s in by_width) - min(s for _, s in by_width) < 0.05

    def one(low: float, high: float, actual: float) -> Optional[float]:
        return lab_row_score(m, p, LAB_CHECK_METRIC, low, high, actual)["score"]

    alt = [one(4, 6, 2), one(4, 6, 8)]
    steady = [one(4, 6, 5.5), one(4, 6, 4.5)]
    mean = lambda xs: None if any(x is None for x in xs) else round(sum(xs) / len(xs), 1)  # noqa: E731
    return {
        "gain_from_guiding_low": round(best_low - honest, 1),
        "gain_shift_pp": best_shift,
        "best_half_width_pp": None if flat else w_best,
        "honest_half_width_pp": hw,
        "width_ignored": flat,
        "one_pp_miss_at_2": one(1, 3, 0),
        "one_pp_miss_at_20": one(19, 21, 18),
        "alternating_record": mean(alt),
        "steady_record": mean(steady),
        "low_growth_beat": one(0, 3, 3.1),
    }


def lab_catalogue() -> Dict[str, Any]:
    """Every lab method with its parameters, ranges, presets and roll-up defaults; the actor views."""
    return {
        "base_method": LAB_BASE_METHOD,
        "max_comparisons": LAB_MAX_COMPARISONS,
        "row_scopes": [
            {"value": "published", "label": "Rows the published level may score"},
            {"value": "all_closed", "label": "Every closed row, including those awaiting a promise citation or review"},
        ],
        "methods": [dict(m) for m in LAB_METHODS],
        "rollup_params": list(LAB_ROLLUP_PARAMS),
        "actor_views": [
            {**v, "comparisons": [{"method": m, "preset": p} for m, p in v["comparisons"]]} for v in LAB_ACTOR_VIEWS
        ],
        "checks": {
            "metric": LAB_CHECK_METRIC,
            "expected_growth_pct": LAB_CHECK_MEAN,
            "spread_pp": LAB_CHECK_SD,
            "honest_half_width_pp": LAB_CHECK_HONEST_HALF_WIDTH,
            "alternating_record": "Guided 4–6% two years running; reported 2%, then 8%",
            "steady_record": "Guided 4–6% two years running; reported 5.5%, then 4.5%",
            "low_growth_beat": "Guided 0–3%, reported 3.1%",
            "one_pp_miss": "Guided 1–3% (or 19–21%), reported 1 point below the range",
        },
    }
