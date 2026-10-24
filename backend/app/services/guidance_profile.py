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
from typing import Any, Dict, List, Optional, Sequence

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


def guidance_profile(outcomes: Sequence[GuidanceOutcome]) -> Dict[str, Any]:
    rows = closed_rows(outcomes)
    return {
        "closed_figures": len(rows),
        "min_for_label": MIN_PROFILE_ROWS,
        "results_vs_range": results_vs_range(rows),
        "in_year_revisions": in_year_revisions(rows),
        "divergences": divergences(rows),
        "note": "Describes the delivery record. Not part of the GCI.",
    }
