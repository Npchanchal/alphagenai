"""Which companies may carry a public GCI number, and how confident that number is.

Analyst-reviewed ``hand_labeled`` rows and machine-extracted rows that passed
quote-in-document verification (``extracted_verified``) may carry a number.
Demo seed and provisional listing outcomes are placeholders; companies built on
them show a coverage status instead of a number.

Confidence tiers (plan W1.3, rule `index-integrity`) — every published score
carries one, and only *established* / *deep* scores are ranked publicly:

- ``provisional``  — < 3 closed periods, or only 1 metric
- ``established``  — ≥ 3 closed periods and ≥ 2 metrics
- ``deep``         — ≥ 5 closed periods and ≥ 2 metrics

``metrics`` here means metrics with at least one closed, analyst-reviewed result
— composite *and* context-only metrics (decision D-tier, 2026-09-29). Breadth of
evidence is what the tier measures; whether a metric moves the composite is a
separate question answered by ``MIN_CLOSED_PERIODS_PER_METRIC``.
"""

from __future__ import annotations

from typing import Iterable, Optional

HAND_LABELED = "hand_labeled"
EXTRACTED_VERIFIED = "extracted_verified"
SCOREABLE_QUALITIES = frozenset({HAND_LABELED, EXTRACTED_VERIFIED})
NOT_SCORED_STATUS = "not_yet_scored"

TIER_PROVISIONAL = "provisional"
TIER_ESTABLISHED = "established"
TIER_DEEP = "deep"
RANKABLE_TIERS = frozenset({TIER_ESTABLISHED, TIER_DEEP})
# A sector average needs this many published company scores before it is shown.
SECTOR_AVG_MIN_NAMES = 3

ESTABLISHED_MIN_PERIODS = 3
DEEP_MIN_PERIODS = 5
MIN_METRICS_FOR_ESTABLISHED = 2

#: A metric with fewer closed periods than this is shown as context but does
#: not enter the composite (plan W1.4 — evidence-weighted composite).
MIN_CLOSED_PERIODS_PER_METRIC = 2
#: Evidence weight of a metric = min(closed periods, this cap).
METRIC_WEIGHT_CAP = 5


def is_scoreable(data_quality: Optional[str]) -> bool:
    return (data_quality or "").strip().lower() in SCOREABLE_QUALITIES


def publishable_score(score: Optional[float], data_quality: Optional[str]) -> Optional[float]:
    return score if is_scoreable(data_quality) else None


def confidence_tier(
    *,
    closed_periods: int,
    metrics_scored: int,
    data_quality: Optional[str] = None,
) -> Optional[str]:
    """Tier for a published score; ``None`` when there is nothing to score.

    Machine-extracted (``extracted_verified``) names stay provisional so they
    cannot enter the Public Snapshot until a human upgrades the quality flag.
    """
    if closed_periods <= 0 or metrics_scored <= 0:
        return None
    if (data_quality or "").strip().lower() == EXTRACTED_VERIFIED:
        return TIER_PROVISIONAL
    if metrics_scored < MIN_METRICS_FOR_ESTABLISHED or closed_periods < ESTABLISHED_MIN_PERIODS:
        return TIER_PROVISIONAL
    if closed_periods >= DEEP_MIN_PERIODS:
        return TIER_DEEP
    return TIER_ESTABLISHED


def is_rankable(tier: Optional[str]) -> bool:
    return tier in RANKABLE_TIERS


PENDING_GUIDANCE_CITE = "pending_guidance_cite"


def _filled(*vals: object) -> bool:
    return all(bool(str(v or "").strip()) for v in vals)


def is_dual_cited(outcome: object) -> bool:
    """Promise citation + actual citation, each with URL, quote, and as-of date."""
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    return _filled(
        g("guidance_source_url"),
        g("guidance_quote"),
        g("guidance_as_of"),
        g("source_url"),
        g("quote_span"),
        g("as_of"),
    )


def is_pending_guidance_cite(outcome: object) -> bool:
    """Closed row that has an actual citation but no promise citation — cannot score.

    Math-only fixtures with no ``source_url`` are not production rows and still score.
    """
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    if g("unmapped") or g("dropped"):
        return False
    if g("actual_value") is None:
        return False
    has_actual = _filled(g("source_url"), g("quote_span"), g("as_of"))
    has_guidance = _filled(g("guidance_source_url"), g("guidance_quote"), g("guidance_as_of"))
    return bool(has_actual and not has_guidance)


def is_source_verify_fail(outcome: object) -> bool:
    """Quote was checked against the filing and is not on the page (W2.7)."""
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    if g("source_verified") is False:
        return True
    return g("citeable") is False and bool(g("source_verify_fail"))


def is_unreviewed(outcome: object) -> bool:
    """Dual-cited closed row with no reviewer stamp (W2.5) — cannot score."""
    if is_pending_guidance_cite(outcome):
        return False
    if not is_dual_cited(outcome):
        return False
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    return not _filled(g("reviewed_by"), g("reviewed_at"))


def _token(value: object) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text or None


def _day(value: object) -> str:
    text = str(value or "").strip()
    return text[:10] if len(text) >= 10 else ""


def _filing_key(value: object) -> str:
    """Same document after scheme, www, query, and fragment are ignored."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.split("#", 1)[0].split("?", 1)[0]
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if text.startswith("www."):
        text = text[4:]
    return text.rstrip("/")


def is_promise_after_result(outcome: object) -> bool:
    """Promise date is later than the result date — the cite is not a prior promise."""
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    promise, result = _day(g("guidance_as_of")), _day(g("as_of"))
    return bool(promise and result and promise > result)


def is_same_filing_promise(outcome: object) -> bool:
    """Promise and result cite the same document. That document is the result, not an earlier promise."""
    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    promise, result = _filing_key(g("guidance_source_url")), _filing_key(g("source_url"))
    return bool(promise and result and promise == result)


def is_not_prior_promise(outcome: object) -> bool:
    return is_promise_after_result(outcome) or is_same_filing_promise(outcome)


def is_basis_mismatch(outcome: object) -> bool:
    """Promise and actual both name a basis, unit, or scope, and they differ.

    A blank side is unknown. Existing rows with no basis still score.
    """
    from app.data.metric_catalog import normalize_basis

    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    promise_basis = normalize_basis(g("reporting_basis"))
    actual_basis = normalize_basis(g("actual_reporting_basis"))
    if promise_basis and actual_basis and promise_basis != actual_basis:
        return True
    unit_promise, unit_actual = _token(g("unit")), _token(g("actual_unit"))
    if unit_promise and unit_actual and unit_promise != unit_actual:
        return True
    scope_promise, scope_actual = _token(g("scope")), _token(g("actual_scope"))
    return bool(scope_promise and scope_actual and scope_promise != scope_actual)


def excluded_from_score(outcome: object) -> bool:
    """Production-shaped closed row that must not enter the composite."""
    return (
        is_pending_guidance_cite(outcome)
        or is_not_prior_promise(outcome)
        or is_unreviewed(outcome)
        or is_source_verify_fail(outcome)
        or is_basis_mismatch(outcome)
    )


# ── GCI Core v2.4 vocabulary (methodology §4, §10; plan docs/PLAN_GCI_CORE.md) ──

ROUTE_QUANT = "QUANT"
ROUTE_QUANT_PENDING = "QUANT_PENDING"
ROUTE_UNSCORABLE = "UNSCORABLE"
ROUTE_WITHDRAWN = "WITHDRAWN"
ROUTE_NOT_DUE = "NOT_DUE"
#: A guidance row with no eligible numeric promise. Qualitative promises are
#: commitments, scored by the Core Qual branch (``commitments.qual_family``).
ROUTE_COMMITMENT_RECORD = "COMMITMENT_RECORD"
CORE_ROUTES = (
    ROUTE_QUANT,
    ROUTE_QUANT_PENDING,
    ROUTE_UNSCORABLE,
    ROUTE_WITHDRAWN,
    ROUTE_NOT_DUE,
    ROUTE_COMMITMENT_RECORD,
)

CALCULATION_COMPUTED = "COMPUTED"
CALCULATION_PARTIAL = "PARTIAL"
CALCULATION_NOT_COMPUTABLE = "NOT_COMPUTABLE"

PUBLICATION_PUBLISHABLE = "PUBLISHABLE"
PUBLICATION_SHADOW = "SHADOW"
PUBLICATION_NOT_ELIGIBLE = "NOT_ELIGIBLE"

#: Methodology v2.4 reason codes, then CiteAlpha extensions (marked in the plan).
CORE_REASON_CODES = (
    "NO_ELIGIBLE_PROMISE",
    "FUTURE_SOURCE",
    "QUOTE_OFFSET_MISMATCH",
    "DOCUMENT_HASH_MISMATCH",
    "AMBIGUOUS_DIRECTION",
    "RELATIVE_TO_CONSENSUS",
    "CONDITION_NOT_ACTIVATED",
    "CONDITION_UNKNOWN",
    "ACTUAL_UNAVAILABLE",
    "OUTCOME_NOT_DUE",
    "UNIT_CONVERSION_ERROR",
    "SCOPE_MISMATCH",
    "ACCOUNTING_BASIS_MISMATCH",
    "DEFINITION_CHANGED",
    "ZERO_REFERENCE_UNAVAILABLE",
    "REVISION_MAGNITUDE_UNAVAILABLE",
    "WITHDRAWN",
    "UNAPPROVED_ENGINE",
    "LATE_GUIDANCE_FLAG",
    "GUIDANCE_AFTER_PERIOD_END",
    "AMBIGUOUS_ACCEPTANCE_EVENT",
    # CiteAlpha extensions
    "PENDING_GUIDANCE_CITE",
    "UNREVIEWED",
    "REGIME_ADAPTER_PENDING",
    "MARKET_DIAGNOSTIC_ONLY",
    "ISSUANCE_TIME_UNKNOWN",
    "PERIOD_END_UNKNOWN",
    "OUTCOME_UNRESOLVED",
    "SUPERSEDED",
    "SAME_DAY_CONFLICT",
    "BASIS_SWITCH",
    "THIN_HISTORY",
    # v2.4-R2
    "SCALE_FLOOR_APPLIED",
    "PRE_PERIOD_GUIDANCE",
)

#: HC-03: furthest stage a guidance record has reached; each stage implies the earlier ones.
RECORD_DOCUMENT_AVAILABLE = "DOCUMENT_AVAILABLE"
RECORD_EXTRACTED = "EXTRACTED"
RECORD_REVIEWER_ACCEPTED = "REVIEWER_ACCEPTED"
RECORD_SCORE_COMPUTED = "SCORE_COMPUTED"
RECORD_PUBLISHED = "PUBLISHED"
RECORD_STATES = (
    RECORD_DOCUMENT_AVAILABLE,
    RECORD_EXTRACTED,
    RECORD_REVIEWER_ACCEPTED,
    RECORD_SCORE_COMPUTED,
    RECORD_PUBLISHED,
)
_BEFORE_REVIEW = {"UNREVIEWED", "PENDING_GUIDANCE_CITE", "QUOTE_OFFSET_MISMATCH", "NO_ELIGIBLE_PROMISE"}


def core_record_state(reason_code: Optional[str], calculation_status: str, *, published: bool) -> str:
    if reason_code in _BEFORE_REVIEW:
        return RECORD_EXTRACTED
    if calculation_status == CALCULATION_COMPUTED:
        return RECORD_PUBLISHED if published else RECORD_SCORE_COMPUTED
    return RECORD_REVIEWER_ACCEPTED

_CONDITION_BLOCKS = {"not_activated": "CONDITION_NOT_ACTIVATED", "unknown": "CONDITION_UNKNOWN"}


def core_route(outcome: object) -> tuple:
    """``(route, reason_code | None)`` for one guidance row under GCI Core.

    Only ``QUANT`` rows are scored. Every other route carries the reason a
    reviewer sees next to the row. Same governance as v4: a row v4 excludes,
    Core excludes too, with a named reason instead of a silent drop.
    """
    from app.data.metric_catalog import normalize_basis

    g = outcome.get if isinstance(outcome, dict) else lambda k, d=None: getattr(outcome, k, d)
    if g("unmapped"):
        return ROUTE_COMMITMENT_RECORD, "NO_ELIGIBLE_PROMISE"
    if g("dropped"):
        return ROUTE_WITHDRAWN, "WITHDRAWN"
    condition = _CONDITION_BLOCKS.get(str(g("condition_state") or "").strip().lower())
    if condition:
        return ROUTE_UNSCORABLE, condition
    if g("actual_value") is None:
        return ROUTE_NOT_DUE, "OUTCOME_NOT_DUE"
    promised, delivered = str(g("guidance_as_of") or ""), str(g("as_of") or "")
    if promised and delivered and promised > delivered:
        return ROUTE_UNSCORABLE, "FUTURE_SOURCE"
    if is_pending_guidance_cite(outcome):
        return ROUTE_QUANT_PENDING, "PENDING_GUIDANCE_CITE"
    if is_source_verify_fail(outcome):
        return ROUTE_QUANT_PENDING, "QUOTE_OFFSET_MISMATCH"
    if is_unreviewed(outcome):
        return ROUTE_QUANT_PENDING, "UNREVIEWED"
    pb, ab = normalize_basis(g("reporting_basis")), normalize_basis(g("actual_reporting_basis"))
    if pb and ab and pb != ab:
        return ROUTE_UNSCORABLE, "ACCOUNTING_BASIS_MISMATCH"
    if _token(g("unit")) and _token(g("actual_unit")) and _token(g("unit")) != _token(g("actual_unit")):
        return ROUTE_UNSCORABLE, "UNIT_CONVERSION_ERROR"
    if _token(g("scope")) and _token(g("actual_scope")) and _token(g("scope")) != _token(g("actual_scope")):
        return ROUTE_UNSCORABLE, "SCOPE_MISMATCH"
    bound = str(g("bound") or "").strip().lower()
    if bound and bound not in ("floor", "ceiling"):
        return ROUTE_UNSCORABLE, "AMBIGUOUS_DIRECTION"
    return ROUTE_QUANT, None


def closed_period_count(outcomes: Iterable) -> int:
    """Distinct reporting periods with a closed (non-pending) outcome."""
    periods = set()
    for o in outcomes:
        status = getattr(o, "status", None) or (o.get("status") if isinstance(o, dict) else None)
        period = getattr(o, "period", None) or (o.get("period") if isinstance(o, dict) else None)
        if status and status != "pending" and period:
            periods.add(period)
    return len(periods)
