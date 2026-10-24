"""GCI scorers — v4 (v3 engine + beat floor), v3 (exp δ / γ / recency), v2 (legacy heuristic).

Toggle with ``INTELLENS_GCI_VERSION=v2|v3|v4`` (default ``v4``).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field, replace
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
    from app.services.score_policy import is_basis_mismatch

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


def _outcome_score_exp(outcome: GuidanceOutcome, beat_floor: float) -> Optional[float]:
    from app.services.score_policy import excluded_from_score

    if outcome.unmapped or outcome.dropped or outcome.actual_value is None:
        return None
    if excluded_from_score(outcome):
        return None
    gmin, gmax, gmid, w = effective_band(outcome)
    actual = float(outcome.actual_value)
    if gmin <= actual <= gmax:
        return 100.0
    delta = (abs(actual - gmid) - w) / (w + GCI_EPS)
    # Guard negative base for fractional β on tiny float noise
    delta = max(0.0, delta)
    decay = math.exp(-GCI_ALPHA * (delta**GCI_BETA))
    if _is_favorable(outcome.metric, actual, gmin, gmax):
        return beat_floor + (100.0 - beat_floor) * decay
    return max(0.0, 100.0 - GCI_GAMMA_MISS * (100.0 - 100.0 * decay))


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
    if counts.get(OutcomeLabel.BASIS_MISMATCH.value) == 0:
        counts.pop(OutcomeLabel.BASIS_MISMATCH.value, None)
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
