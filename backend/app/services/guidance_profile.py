"""Guidance profile: how results land against guidance and how guidance moves in-year.

Describes the record next to the GCI. It never feeds the GCI
(``test_profile_does_not_move_gci``). Only rows that could enter the GCI count:
dual-cited, reviewed, closed. Below ``MIN_PROFILE_ROWS`` closed figures we give
counts and no label.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.gci_scoring import (
    GuidanceOutcome,
    OutcomeLabel,
    classify_outcome,
    metric_direction,
    normalized_surprise,
    revision_direction,
)

MIN_PROFILE_ROWS = 6
BIAS_CUTOFF = 20.0
WALK_SHARE = 0.30
MIXED_SHARE = 0.25
STABLE_SHARE = 0.20
#: Pilot only. Neither spec version calibrates it on Indian data.
SPREAD_CUTOFF = 1.25

RESULT_LABELS = {
    "usually_above": "Results tend to land above the guided range",
    "balanced": "No consistent lean above or below the guided range",
    "usually_below": "Results tend to land below the guided range",
}
PATH_LABELS = {
    "walk_down": "Guidance is often revised toward a weaker figure during the year",
    "walk_up": "Guidance is often revised toward a stronger figure during the year",
    "mixed": "In-year revisions go both ways",
    "stable": "Opening guidance usually stands until results",
}

_CLOSED = (OutcomeLabel.EXCEEDED, OutcomeLabel.MET, OutcomeLabel.MISSED)
_REVENUE_PREFIX = "revenue_growth"
_MARGIN_IDS = ("ebitda_margin_pct", "operating_margin_pct", "net_margin_pct")
_UNIT_SUFFIX = {"pct": "%", "mmt": " MMT", "days": " days", "inr_cr": " cr", "units": " units", "usd_mn": "m"}
_UNIT_PREFIX = {"inr_cr": "₹", "usd_mn": "$", "usd": "$"}


def closed_rows(outcomes: Sequence[GuidanceOutcome]) -> List[GuidanceOutcome]:
    from app.services.score_policy import excluded_from_score

    return [
        o
        for o in outcomes
        if not o.unmapped
        and not excluded_from_score(o)
        and classify_outcome(o) in _CLOSED
    ]


def _join(parts: List[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _results_sentence(n: int, above: int, inside: int, below: int) -> str:
    if not n:
        return ""
    counts = [(side, c) for side, c in (("above", above), ("within", inside), ("below", below)) if c]
    if len(counts) == 1:
        subject = "The one closed guidance figure" if n == 1 else f"All {n} closed guidance figures"
        return f"{subject} came in {counts[0][0]} the guided range."
    (first_side, first), rest = counts[0], counts[1:]
    parts = [f"{first} came in {first_side} the range"] + [f"{c} {side} it" for side, c in rest]
    return f"Of {n} closed guidance figures, {_join(parts)}."


def _revision_sentence(n: int, revised: int, weaker: int, stronger: int) -> str:
    if not n:
        return ""
    if n == 1:
        if not revised:
            return "Guidance for the one closed figure was not revised during the year."
        side = "stronger" if stronger else "weaker" if weaker else ""
        return "Guidance for the one closed figure was revised during the year" + (
            f", toward a {side} figure." if side else "."
        )
    if not revised:
        return f"None of the {n} closed figures had guidance revised during the year."
    scope = f"all {n}" if revised == n else f"{revised} of {n}"
    head = f"Guidance was revised during the year for {scope} closed figures"
    if stronger and weaker:
        return f"{head}: {stronger} toward a stronger figure and {weaker} toward a weaker one."
    if stronger or weaker:
        side, count = ("stronger", stronger) if stronger else ("weaker", weaker)
        if count == revised:
            return f"{head}, each time toward a {side} figure."
        return f"{head}, {count} of them toward a {side} figure."
    return f"{head}."


def results_vs_range(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    labels = [classify_outcome(o) for o in rows]
    above = labels.count(OutcomeLabel.EXCEEDED)
    inside = labels.count(OutcomeLabel.MET)
    below = labels.count(OutcomeLabel.MISSED)
    n = len(labels)
    bias = round(100.0 * (above - below) / n, 1) if n >= MIN_PROFILE_ROWS else None
    label: Optional[str] = None
    if bias is not None:
        if bias >= BIAS_CUTOFF:
            label = "usually_above"
        elif bias <= -BIAS_CUTOFF:
            label = "usually_below"
        else:
            label = "balanced"
    sentence = _results_sentence(n, above, inside, below)
    return {
        "above": above,
        "inside": inside,
        "below": below,
        "bias_index": bias,
        "label": label,
        "label_text": RESULT_LABELS.get(label or ""),
        "sentence": sentence,
    }


def in_year_revisions(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    weaker = stronger = revised = 0
    for o in rows:
        move = revision_direction(o)
        if move in (None, "unchanged"):
            continue
        revised += 1
        direction = metric_direction(o.metric)
        if direction == "two_sided":
            continue
        up_is_good = direction == "higher"
        if (move == "raised") == up_is_good:
            stronger += 1
        else:
            weaker += 1
    n = len(rows)
    label: Optional[str] = None
    if n >= MIN_PROFILE_ROWS:
        if weaker / n >= MIXED_SHARE and stronger / n >= MIXED_SHARE:
            label = "mixed"
        elif weaker / n >= WALK_SHARE:
            label = "walk_down"
        elif stronger / n >= WALK_SHARE:
            label = "walk_up"
        elif revised / n < STABLE_SHARE:
            label = "stable"
    sentence = _revision_sentence(n, revised, weaker, stronger)
    return {
        "revised": revised,
        "toward_weaker": weaker,
        "toward_stronger": stronger,
        "label": label,
        "label_text": PATH_LABELS.get(label or ""),
        "sentence": sentence,
    }


def surprise_spread(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    """Robust spread of s* (1.4826 × median absolute deviation). Pilot seats only."""
    values = [s for s in (normalized_surprise(o) for o in rows) if s is not None]
    if len(values) < MIN_PROFILE_ROWS:
        return {"value": None, "label": None, "pilot": True}
    mid = statistics.median(values)
    spread = round(1.4826 * statistics.median(abs(v - mid) for v in values), 2)
    return {
        "value": spread,
        "label": "precise" if spread <= SPREAD_CUTOFF else "variable",
        "pilot": True,
    }


def metric_phrase(metric: str, *, start: bool = False) -> str:
    """'revenue growth (constant currency)', 'EBITDA margin'. Capitalised when ``start``."""
    from app.data.metric_catalog import display_name_for

    name = display_name_for(metric).replace(" % of ", " as a share of ").replace(" %", "")
    name = re.sub(r"\s*\((MMT|units)\)$", "", name).replace(" / ", " or ")
    name = re.sub(r"\s+guidance$", "", name, flags=re.IGNORECASE).strip()
    if start:
        return name[:1].upper() + name[1:]
    if len(name) > 1 and name[1].islower():
        name = name[0].lower() + name[1:]
    return name


def _num(v: float) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def human_date(iso: Optional[str]) -> str:
    """'2025-02-12' → '12 Feb 2025'. Anything else is returned unchanged."""
    from datetime import date

    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso or "")
    return f"{d.day} {d.strftime('%b %Y')}"


def _unit(metric: str) -> str:
    from app.data.metric_catalog import get_metric

    return str((get_metric(metric) or {}).get("unit"))


def value_text(metric: str, value: float) -> str:
    unit = _unit(metric)
    if unit == "usd":
        return f"${float(value):.2f}"
    return f"{_UNIT_PREFIX.get(unit, '')}{_num(float(value))}{_UNIT_SUFFIX.get(unit, '')}"


def range_text(metric: str, low: Optional[float], high: Optional[float], point: float) -> str:
    lo = point if low is None else low
    hi = point if high is None else high
    if lo == hi:
        return value_text(metric, lo)
    lo, hi = min(lo, hi), max(lo, hi)
    unit = _unit(metric)
    prefix = _UNIT_PREFIX.get(unit, "")
    low_text = f"{lo:.2f}" if unit == "usd" else _num(lo)
    return f"{prefix}{low_text}–{value_text(metric, hi)[len(prefix):]}"


def guided_text(o: GuidanceOutcome) -> str:
    return range_text(o.metric, o.guided_low, o.guided_high, o.guided_value)


def _figure(o: GuidanceOutcome) -> str:
    return f"guided {guided_text(o)}, reported {value_text(o.metric, float(o.actual_value))}"


def divergences(rows: Sequence[GuidanceOutcome]) -> List[Dict[str, Any]]:
    """Same-period revenue and margin landing on opposite sides of their ranges."""
    by_period: Dict[str, Dict[str, List[GuidanceOutcome]]] = defaultdict(
        lambda: {"revenue": [], "margin": []}
    )
    for o in rows:
        if o.metric.startswith(_REVENUE_PREFIX):
            by_period[o.period]["revenue"].append(o)
        elif o.metric in _MARGIN_IDS:
            by_period[o.period]["margin"].append(o)
    found: List[Dict[str, Any]] = []
    for period in sorted(by_period):
        for rev in by_period[period]["revenue"]:
            for mar in by_period[period]["margin"]:
                r, m = classify_outcome(rev), classify_outcome(mar)
                if r == OutcomeLabel.EXCEEDED and m == OutcomeLabel.MISSED:
                    kind, high, low = "revenue_above_margin_below", rev, mar
                elif r == OutcomeLabel.MISSED and m == OutcomeLabel.EXCEEDED:
                    kind, high, low = "margin_above_revenue_below", mar, rev
                else:
                    continue
                found.append(
                    {
                        "period": period,
                        "kind": kind,
                        "metrics": [rev.metric, mar.metric],
                        "sentence": (
                            f"{period}: {metric_phrase(high.metric)} came in above its guided range "
                            f"({_figure(high)}) while {metric_phrase(low.metric)} came in below it "
                            f"({_figure(low)})."
                        ),
                        "sources": [
                            u for u in (rev.source_url, mar.source_url) if u
                        ],
                    }
                )
    return found


def lead_time(rows: Sequence[GuidanceOutcome], *, market_id: str = "IN", fy_end_mmdd: Optional[str] = None) -> Dict[str, Any]:
    """How far ahead of period end guidance was first given (decision D-07: shown, never scored)."""
    from datetime import date

    from app.services.disclosures import period_end
    from app.services.gci_scoring import CORE_LATE_GUIDANCE_DAYS

    days: List[int] = []
    after_close = 0
    for o in rows:
        end = period_end(o.period, market_id, fy_end_mmdd)
        if not end or not o.guidance_as_of:
            continue
        try:
            gap = (date.fromisoformat(end) - date.fromisoformat(str(o.guidance_as_of)[:10])).days
        except ValueError:
            continue
        if gap < 0:
            after_close += 1
        else:
            days.append(gap)
    late = sum(1 for d in days if d < CORE_LATE_GUIDANCE_DAYS)
    median = int(statistics.median(days)) if days else None
    if median is None:
        sentence = "No dated opening guidance yet."
    else:
        sentence = f"Guidance was first given a median {median} days before the period ended"
        if late:
            sentence += f"; {late} of {len(days)} within {CORE_LATE_GUIDANCE_DAYS} days of period end"
        sentence += "."
    return {
        "dated": len(days),
        "median_days": median,
        "late": late,
        "after_period_end": after_close,
        "late_cutoff_days": CORE_LATE_GUIDANCE_DAYS,
        "sentence": sentence,
    }


# ── Companion indexes ───────────────────────────────────────────────────────
# Each answers one question a delivery score should not blend in. Preview only:
# never ranked, never part of the GCI, and no value below COMPANION_MIN_ROWS rows.

COMPANION_MIN_ROWS = 3
#: Growth Accuracy: points lost per percentage point outside the guided range. Uncalibrated.
GROWTH_POINTS_PER_PP = 10.0
#: Guidance Setting: a range wider than this multiple of the median width for the metric.
WIDE_RANGE_MULTIPLE = 2.0
#: Guidance Setting: a point or one-sided promise cleared by more than this (rate in points, amount as a share).
CLEARED_POINT_PP = 1.0
CLEARED_POINT_SHARE = 0.10
#: Guidance Bias: the method lab's diffusion preset (metric direction on, growth floor).
GUIDANCE_BIAS_PRESET = "guidance_bias"
COMPANION_IDS = (
    "revision_discipline",
    "guidance_visibility",
    "commitment_delivery",
    "guidance_setting",
    "growth_accuracy_pp",
    "guidance_bias",
)


def _companion(
    cid: str,
    name: str,
    question: str,
    replaces: str,
    value: Optional[float],
    rows: int,
    sentence: str,
    parameters: Dict[str, Any],
    items: List[Dict[str, Any]],
    **extra: Any,
) -> Dict[str, Any]:
    return {
        "id": cid,
        "algorithm_id": f"companion_{cid}_v1",
        "name": name,
        "question": question,
        "replaces": replaces,
        "value": value if rows >= COMPANION_MIN_ROWS else None,
        "rows": rows,
        "min_rows": COMPANION_MIN_ROWS,
        "status": "preview",
        "part_of_gci": False,
        "rankable": False,
        "sentence": sentence,
        "parameters": parameters,
        "items": items,
        **extra,
    }


def _mean(values: Sequence[float]) -> Optional[float]:
    return round(statistics.fmean(values), 1) if values else None


def revision_discipline(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    """Share of closed figures never revised toward a weaker figure before results."""
    from decimal import Decimal

    from app.services.gci_scoring import _econ_sign, _step_direction, _vintages

    items: List[Dict[str, Any]] = []
    for o in rows:
        vs = [v for v in _vintages(o) if v["index"] == 0 or not o.as_of or str(v["as_of"] or "") <= str(o.as_of)]
        weaker = stronger = unsigned = 0
        for prev, cur in zip(vs, vs[1:]):
            step = _econ_sign(
                o.metric,
                _step_direction(
                    (Decimal(str(prev["low"])), Decimal(str(prev["high"]))),
                    (Decimal(str(cur["low"])), Decimal(str(cur["high"]))),
                ),
                o.bound,
            )
            if step < 0:
                weaker += 1
            elif step > 0:
                stronger += 1
            else:
                unsigned += 1
        items.append({
            "period": o.period,
            "parameter": o.metric,
            "updates": len(vs) - 1,
            "toward_weaker": weaker,
            "toward_stronger": stronger,
            "mixed_or_two_sided": unsigned,
        })
    n = len(items)
    kept = sum(1 for i in items if not i["toward_weaker"])
    updates = sum(i["updates"] for i in items)
    weaker = sum(i["toward_weaker"] for i in items)
    if not n:
        sentence = "No closed guidance figures yet."
    else:
        sentence = (
            f"In {kept} of {n} closed figure{'' if n == 1 else 's'} guidance was never revised toward a weaker figure before results "
            f"({updates} in-year updates in all, {weaker} toward a weaker figure)."
        )
    return _companion(
        "revision_discipline",
        "Revision Discipline",
        "Does management walk guidance down during the year?",
        "GCI Core §14 revision-frequency penalty (v2.4 penalises every revision, including honest raises)",
        round(100.0 * kept / n, 1) if n else None,
        n,
        sentence,
        {"counts": "revisions dated on or before the result date"},
        items,
        updates_per_figure=round(updates / n, 2) if n else None,
    )


def guidance_visibility(
    rows: Sequence[GuidanceOutcome], *, market_id: str = "IN", fy_end_mmdd: Optional[str] = None
) -> Dict[str, Any]:
    """How much of the period guidance covered: lead time over the period length, capped at 100."""
    from app.services.disclosures import period_end
    from app.services.gci_scoring import CORE_HORIZON_DAYS, _days, core_cadence

    items: List[Dict[str, Any]] = []
    after_close = undated = 0
    for o in rows:
        end = period_end(o.period, market_id, fy_end_mmdd)
        lead = _days(o.guidance_as_of, end) if end else None
        if lead is None:
            undated += 1
            continue
        if lead < 0:
            after_close += 1
            continue
        horizon = CORE_HORIZON_DAYS[core_cadence(o.period)]
        items.append({
            "period": o.period,
            "parameter": o.metric,
            "lead_days": lead,
            "horizon_days": horizon,
            "score": round(100.0 * min(1.0, lead / horizon), 1),
        })
    n = len(items)
    if not n:
        sentence = "No dated opening guidance yet."
    else:
        median = int(statistics.median(i["lead_days"] for i in items))
        sentence = f"Opening guidance came a median {median} days before the period ended, across {n} dated figure{'' if n == 1 else 's'}."
        if undated:
            sentence += f" {undated} closed figures have no guidance date."
    return _companion(
        "guidance_visibility",
        "Guidance Visibility",
        "How early in the period does management commit to a number?",
        "GCI Core §13.3 lead-time factor (a 0.8–1.1 multiplier on the delivery score in v2.4)",
        _mean([i["score"] for i in items]),
        n,
        sentence,
        {"horizon_days": dict(CORE_HORIZON_DAYS), "scale": "lead days ÷ period days, capped at 1"},
        items,
        undated=undated,
        after_period_end=after_close,
    )


def commitment_delivery(commitments: Sequence[Dict[str, Any]], *, as_of: str) -> Dict[str, Any]:
    """Accepted commitments scored as in GCI Core §10 — the Qual branch, standalone."""
    from app.services.gci_scoring import core_qual_branch

    qual = core_qual_branch(commitments, as_of=as_of)
    scored = [f for f in qual["families"] if f["low"] is not None]
    due = len(scored)
    if not qual["families"]:
        sentence = "No reviewed commitments on file."
    elif not due:
        sentence = "No reviewed commitments have fallen due yet."
    elif qual["qual_gci"] is None:
        sentence = (
            f"{due} commitments have fallen due; some outcomes are not yet confirmed, "
            f"so the reading is a range of {qual['qual_low']} to {qual['qual_high']}."
        )
    else:
        sentence = f"{due} commitments have fallen due; delivery reads {qual['qual_gci']} on a 0–100 scale."
    return _companion(
        "commitment_delivery",
        "Commitment Delivery",
        "Does management deliver dated non-financial commitments on time?",
        "GCI Core §17 Qual weight (20% of the v2.4 composite)",
        qual["qual_gci"],
        due,
        sentence,
        {"method": "GCI Core §10, §15.2, §16"},
        qual["families"],
        low=qual["qual_low"] if due >= COMPANION_MIN_ROWS else None,
        high=qual["qual_high"] if due >= COMPANION_MIN_ROWS else None,
    )


def _width(o: GuidanceOutcome) -> Optional[float]:
    """Range width: points for a rate, percent of the midpoint for an amount; None if unmeasurable."""
    from app.data.metric_catalog import metric_is_rate

    lo, hi = sorted((float(o.guided_low if o.guided_low is not None else o.guided_value),
                     float(o.guided_high if o.guided_high is not None else o.guided_value)))
    if metric_is_rate(o.metric):
        return hi - lo
    mid = abs((lo + hi) / 2)
    return None if mid == 0 else 100.0 * (hi - lo) / mid


def setting_reference(rows_by_company: Dict[str, Sequence[GuidanceOutcome]]) -> Dict[str, float]:
    """Median non-zero range width per metric across covered companies (three ranges or more)."""
    widths: Dict[str, List[float]] = defaultdict(list)
    for rows in rows_by_company.values():
        for o in closed_rows(rows):
            if o.bound:
                continue
            w = _width(o)
            if w:
                widths[o.metric].append(w)
    return {m: round(statistics.median(v), 4) for m, v in widths.items() if len(v) >= 3}


def _clearance(o: GuidanceOutcome) -> Optional[bool]:
    """True when the result cleared the favourable edge by more than the range is wide."""
    from app.data.metric_catalog import metric_is_rate

    direction = metric_direction(o.metric)
    side = (o.bound or "").strip().lower()
    if direction == "two_sided" and not side:
        return None
    lo, hi = sorted((float(o.guided_low if o.guided_low is not None else o.guided_value),
                     float(o.guided_high if o.guided_high is not None else o.guided_value)))
    actual = float(o.actual_value)
    up = direction != "lower" if not side else side == "floor"
    edge = (lo if side == "floor" else hi) if up else (hi if side == "ceiling" else lo)
    gap = actual - edge if up else edge - actual
    if gap <= 0:
        return False
    if hi > lo and not side:
        return gap > hi - lo
    margin = CLEARED_POINT_PP if metric_is_rate(o.metric) else CLEARED_POINT_SHARE * abs(edge)
    return gap > margin


def guidance_setting(rows: Sequence[GuidanceOutcome], *, reference: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """GAP-18: share of figures guided with an informative range that was not cleared by a wide margin."""
    ref = reference or {}
    items: List[Dict[str, Any]] = []
    for o in rows:
        w = None if o.bound else _width(o)
        typical = ref.get(o.metric)
        wide = bool(w and typical and w > WIDE_RANGE_MULTIPLE * typical)
        cleared = _clearance(o)
        items.append({
            "period": o.period,
            "parameter": o.metric,
            "width": None if w is None else round(w, 4),
            "typical_width": typical,
            "wide_range": wide,
            "cleared_by_wide_margin": bool(cleared),
        })
    n = len(items)
    wide = sum(1 for i in items if i["wide_range"])
    cleared = sum(1 for i in items if i["cleared_by_wide_margin"])
    flagged = sum(1 for i in items if i["wide_range"] or i["cleared_by_wide_margin"])
    if not n:
        sentence = "No closed guidance figures yet."
    elif not flagged:
        sentence = f"None of the {n} closed figures used an unusually wide range or was beaten by a wide margin."
    else:
        sentence = (
            f"Of {n} closed figure{'' if n == 1 else 's'}, {wide} used a range more than twice the typical width for that metric "
            f"across covered companies and {cleared} were beaten by more than the range's own width."
        )
    return _companion(
        "guidance_setting",
        "Guidance Setting",
        "Are ranges informative, or set wide or low enough to be easy to meet?",
        "Not in GCI v2.4: a wide range or a low floor scores as met (GAP-18)",
        round(100.0 * (n - flagged) / n, 1) if n else None,
        n,
        sentence,
        {
            "wide_range_multiple": WIDE_RANGE_MULTIPLE,
            "point_margin_pp": CLEARED_POINT_PP,
            "point_margin_share": CLEARED_POINT_SHARE,
            "reference": "median width per metric across covered companies, three ranges or more",
        },
        items,
        wide_ranges=wide,
        beaten_by_wide_margin=cleared,
    )


def growth_accuracy_pp(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    """Growth figures read in percentage points outside the opening range (inside = 0)."""
    from app.data.metric_catalog import metric_is_growth

    items: List[Dict[str, Any]] = []
    for o in rows:
        if not metric_is_growth(o.metric):
            continue
        lo, hi = sorted((float(o.guided_low if o.guided_low is not None else o.guided_value),
                         float(o.guided_high if o.guided_high is not None else o.guided_value)))
        actual = float(o.actual_value)
        side = (o.bound or "").strip().lower()
        below = max(0.0, lo - actual) if side != "ceiling" else 0.0
        above = max(0.0, actual - hi) if side != "floor" else 0.0
        pp = below or above
        items.append({
            "period": o.period,
            "parameter": o.metric,
            "guided_low": lo,
            "guided_high": hi,
            "actual": actual,
            "pp_outside": round(pp, 2),
            "side": "below" if below else "above" if above else "inside",
            "score": round(max(0.0, 100.0 - GROWTH_POINTS_PER_PP * pp), 1),
        })
    n = len(items)
    if not n:
        sentence = "No closed growth guidance yet."
    else:
        inside = sum(1 for i in items if i["side"] == "inside")
        above = sum(1 for i in items if i["side"] == "above")
        below = sum(1 for i in items if i["side"] == "below")
        median = statistics.median(i["pp_outside"] for i in items)
        sentence = (
            f"Across {n} closed growth figure{'' if n == 1 else 's'}, {inside} landed inside the guided range, {above} above and "
            f"{below} below; the median distance outside the range was {_num(median)} percentage points."
        )
    return _companion(
        "growth_accuracy_pp",
        "Growth Accuracy",
        "How far, in percentage points, did reported growth land from the guided range?",
        "GCI v2.4 §9 relative deviation on growth (a 1-point beat on 1–3% guidance scores as a total miss)",
        _mean([i["score"] for i in items]),
        n,
        sentence,
        {"points_per_pp": GROWTH_POINTS_PER_PP, "band": "opening guidance"},
        items,
    )


_BIAS_TAGS = ("beat", "in_line", "miss", "outside_range")


def guidance_bias(rows: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    """Which side of the opening guidance results land on: 50 is the midpoint, above 50 the better side."""
    from app.services.gci_scoring import lab_resolve, lab_row_score, lab_tag

    resolved = lab_resolve({"method": "diffusion", "preset": GUIDANCE_BIAS_PRESET})
    items: List[Dict[str, Any]] = []
    for o in rows:
        lo, hi = sorted((float(o.guided_low if o.guided_low is not None else o.guided_value),
                         float(o.guided_high if o.guided_high is not None else o.guided_value)))
        actual = float(o.actual_value)
        scored = lab_row_score("diffusion", resolved["params"], o.metric, lo, hi, actual, bound=o.bound)
        items.append({
            "period": o.period,
            "parameter": o.metric,
            "guided_low": lo,
            "guided_high": hi,
            "actual": actual,
            "tag": lab_tag(o.metric, lo, hi, actual, o.bound),
            "score": scored["score"],
            "reason": scored["reason"],
        })
    counts = {t: sum(1 for i in items if i["tag"] == t) for t in _BIAS_TAGS}
    scores = [i["score"] for i in items if i["score"] is not None]
    n = len(items)
    value = _mean(scores)
    if not n:
        sentence = "No closed guidance figures yet."
    else:
        phrases = {
            "beat": "beat the opening guidance",
            "in_line": "landed inside the opening range",
            "miss": "missed the opening guidance",
            "outside_range": "fell outside a two-sided range",
        }
        parts = [f"{counts[t]} {phrases[t]}" for t in _BIAS_TAGS if counts[t]]
        sentence = f"Of {n} closed figure{'' if n == 1 else 's'}, {_join(parts)}."
        if value is not None and len(scores) >= COMPANION_MIN_ROWS:
            sentence += f" Average reading {_num(value)}, where 50 is the guided midpoint and above 50 the better side."
    return _companion(
        "guidance_bias",
        "Guidance Bias",
        "Do results land on the better or the worse side of the guided midpoint?",
        "Proposed 50-centred headline (v2.5 Diffusion note); a signed level pays for guiding low, so direction is read here",
        value,
        len(scores),
        sentence,
        {
            "formula": "50 + 50 × clamp(signed deviation from the opening midpoint ÷ scale, −1, 1)",
            "method": resolved["method"],
            "preset": resolved["preset"],
            **resolved["params"],
            "tags": "against the range as guided; two-sided metrics read in range or outside range",
        },
        items,
        tags=counts,
    )


def companion_indexes(
    outcomes: Sequence[GuidanceOutcome],
    *,
    market_id: str = "IN",
    fy_end_mmdd: Optional[str] = None,
    commitments: Sequence[Dict[str, Any]] = (),
    as_of: str,
    setting_ref: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    rows = closed_rows(outcomes)
    indexes = [
        revision_discipline(rows),
        guidance_visibility(rows, market_id=market_id, fy_end_mmdd=fy_end_mmdd),
        commitment_delivery(commitments, as_of=as_of),
        guidance_setting(rows, reference=setting_ref),
        growth_accuracy_pp(rows),
        guidance_bias(rows),
    ]
    return {
        "as_of": as_of,
        "closed_figures": len(rows),
        "indexes": indexes,
        "note": (
            "Companion indexes measure what the GCI should not blend into a delivery score. "
            "Preview: not ranked and not part of any published GCI."
        ),
    }


# ── Record diagnostics (GAP-19, GAP-20, GAP-21) ─────────────────────────────


def guidance_diagnostics(
    outcomes: Sequence[GuidanceOutcome],
    *,
    commitments: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    """Withdrawals, reinstatements, deadline extensions, basis switches and thin history.

    Shown beside the score; none of them moves it.
    """
    from app.data.metric_catalog import normalize_basis
    from app.services.changes import sort_periods
    from app.services.gci_scoring import CORE_THIN_HISTORY_PERIODS

    by_metric: Dict[str, List[GuidanceOutcome]] = defaultdict(list)
    for o in outcomes:
        by_metric[o.metric].append(o)
    withdrawals: List[Dict[str, Any]] = []
    reinstatements: List[Dict[str, Any]] = []
    basis_switches: List[Dict[str, Any]] = []
    for metric, rows in sorted(by_metric.items()):
        order = {p: i for i, p in enumerate(sort_periods([o.period for o in rows]))}
        rows = sorted(rows, key=lambda o: order[o.period])
        dropped_at: Optional[str] = None
        last_basis: Optional[Tuple[str, str]] = None
        for o in rows:
            if o.dropped:
                withdrawals.append({"parameter": metric, "period": o.period, "source_url": o.guidance_source_url})
                dropped_at = o.period
                continue
            if dropped_at:
                reinstatements.append({"parameter": metric, "withdrawn": dropped_at, "reinstated": o.period})
                dropped_at = None
            basis = normalize_basis(o.reporting_basis)
            if basis and last_basis and last_basis[1] != basis:
                basis_switches.append({
                    "parameter": metric,
                    "from_period": last_basis[0],
                    "from_basis": last_basis[1],
                    "to_period": o.period,
                    "to_basis": basis,
                })
            if basis:
                last_basis = (o.period, basis)

    extensions: List[Dict[str, Any]] = []
    accepted = [c for c in commitments if c.get("review_status") == "accepted"]
    for old in accepted:
        if old.get("state") != "superseded":
            continue
        key = (old.get("type"), str(old.get("subject") or "").strip().lower())
        for new in accepted:
            if new is old or (new.get("type"), str(new.get("subject") or "").strip().lower()) != key:
                continue
            if str(new.get("due_date") or "") > str(old.get("due_date") or "") and str(new.get("as_of") or "") >= str(old.get("as_of") or ""):
                extensions.append({
                    "commitment_id": old.get("id"),
                    "replaced_by": new.get("id"),
                    "subject": old.get("subject"),
                    "old_deadline": old.get("due_date"),
                    "new_deadline": new.get("due_date"),
                })
                break

    rows = closed_rows(outcomes)
    periods = len({o.period for o in rows})
    per_param: Dict[str, int] = defaultdict(int)
    for o in rows:
        per_param[o.metric] += 1
    thin = periods < CORE_THIN_HISTORY_PERIODS
    return {
        "withdrawals": withdrawals,
        "reinstatements": reinstatements,
        "deadline_extensions": extensions,
        "basis_switches": basis_switches,
        "thin_history": {
            "closed_periods": periods,
            "threshold": CORE_THIN_HISTORY_PERIODS,
            "thin": thin,
            "single_family_parameters": sorted(m for m, n in per_param.items() if n == 1),
            "policy": (
                "Fewer closed periods than the threshold: the level is shown with THIN_HISTORY and its "
                "confidence tier, and is never ranked. A growth miss on a low base is read against the "
                "delivery ruleset's points floor and the Growth Accuracy index."
            ),
        },
        "note": "Diagnostics are shown beside the score and never move it.",
    }


def guidance_profile(outcomes: Sequence[GuidanceOutcome], *, market_id: str = "IN") -> Dict[str, Any]:
    rows = closed_rows(outcomes)
    return {
        "closed_figures": len(rows),
        "min_for_label": MIN_PROFILE_ROWS,
        "results_vs_range": results_vs_range(rows),
        "in_year_revisions": in_year_revisions(rows),
        "lead_time": lead_time(rows, market_id=market_id),
        "divergences": divergences(rows),
        "note": "Describes the delivery record. Not part of the GCI.",
    }
