"""Guidance audit flags, red alerts, and revision / restatement timeline.

On-wedge only: withdrawal, restatement, definition shift, miss, revise.
Not a Beneish / forensic shenanigans engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException

from app.services.gci_scoring import (
    AUDIT_PENALTY_PTS,
    GuidanceOutcome,
    audit_deduction,
    classify_outcome,
    compute_company_gci,
    revision_direction,
)

# Human labels for UI chips
AUDIT_LABELS: Dict[str, str] = {
    "guidance_withdrawal": "Guidance withdrawn",
    "restatement": "Results restatement",
    "definition_shift": "Definition / basis shift",
}

AUDIT_SEVERITY: Dict[str, str] = {
    "guidance_withdrawal": "high",
    "restatement": "high",
    "definition_shift": "medium",
}


def _mid(o: GuidanceOutcome) -> float:
    if o.guided_low is not None and o.guided_high is not None:
        return (float(o.guided_low) + float(o.guided_high)) / 2.0
    return float(o.guided_value)


def _event_detail(kind: str, o: GuidanceOutcome, prev: Optional[GuidanceOutcome] = None) -> str:
    """One plain sentence per timeline event, with display names and units."""
    from app.services.gci_scoring import metric_direction
    from app.services.guidance_profile import guided_text, metric_phrase, value_text

    name = metric_phrase(o.metric, start=True)
    guide = guided_text(o)
    if kind == "withdrawn":
        return f"{name} guidance for {o.period} was withdrawn."
    if kind == "restatement":
        return f"{name} for {o.period}: the filing refers to a restatement."
    if kind.startswith("resolved_") and o.actual_value is not None:
        actual = value_text(o.metric, o.actual_value)
        direction = metric_direction(o.metric)
        if kind == "resolved_met":
            side = "within"
        elif kind == "resolved_exceeded":
            side = "below" if direction == "lower" else "above"
        else:
            side = {"lower": "above", "two_sided": "outside"}.get(direction, "below")
        return f"{name} for {o.period} came in at {actual}, {side} guidance of {guide}."
    if prev is not None and prev.period != o.period and kind in ("revised_up", "revised_down", "reiterated"):
        return f"{name} guided at {guide} for {o.period}, against {guided_text(prev)} for {prev.period}."
    if kind in ("revised_up", "revised_down") and prev is not None:
        return f"{name} guidance for {o.period} moved from {guided_text(prev)} to {guide}."
    if kind == "reiterated":
        return f"{name} guidance for {o.period} repeated at {guide}."
    return f"{name} guided at {guide} for {o.period}."


def _text_blob(o: GuidanceOutcome) -> str:
    return f"{o.source_ref or ''} {o.guided_text or ''} {o.quote_span or ''}".lower()


def suggest_audit_flags(outcomes: Sequence[GuidanceOutcome]) -> List[str]:
    """Keyword heuristics — enqueue review only; never apply to GCI (W2.6)."""
    flags: set[str] = set()
    if any(o.dropped for o in outcomes):
        flags.add("guidance_withdrawal")

    for o in outcomes:
        blob = _text_blob(o)
        if "restat" in blob:
            flags.add("restatement")
        if "definition" in blob or "basis change" in blob or "reclassif" in blob:
            flags.add("definition_shift")

    # Two rows for the same thread and period whose bands disagree materially →
    # definition_shift candidate. Guidance for different years, and in-year revisions
    # recorded on ``revisions``, are expected to move and are not flagged.
    by_thread: Dict[Tuple[str, str], List[GuidanceOutcome]] = {}
    for o in outcomes:
        if o.thread_id and not o.dropped:
            by_thread.setdefault((o.thread_id, o.period), []).append(o)
    for rows in by_thread.values():
        ordered = sorted(rows, key=lambda r: (r.as_of or "", r.period))
        if len(ordered) < 2:
            continue
        for prev, cur in zip(ordered, ordered[1:]):
            if abs(_mid(cur) - _mid(prev)) >= 2.0:
                flags.add("definition_shift")
                break

    return sorted(flags)


def list_audit_flag_records(company_id: Optional[str]) -> List[Dict[str, Any]]:
    """Persisted analyst flags that carry ``set_by`` (and a source)."""
    if not company_id:
        return []
    from app.data.seed import get_data

    rows = list((get_data().get("company_audit_flags") or {}).get(company_id) or [])
    out: List[Dict[str, Any]] = []
    for r in rows:
        flag = r.get("flag")
        if flag not in AUDIT_LABELS:
            continue
        if not str(r.get("set_by") or "").strip():
            continue
        if not str(r.get("source_url") or "").strip():
            continue
        out.append(dict(r))
    out.sort(key=lambda r: str(r.get("flag") or ""))
    return out


def applied_audit_flags(company_id: Optional[str] = None) -> List[str]:
    return sorted({str(r["flag"]) for r in list_audit_flag_records(company_id)})


def collect_audit_flags(
    outcomes: Sequence[GuidanceOutcome],
    *,
    company_id: Optional[str] = None,
) -> List[str]:
    """Flags that affect GCI: analyst-set with ``set_by`` + source only (W2.6).

    ``outcomes`` is unused; heuristic candidates live on :func:`suggest_audit_flags`.
    """
    del outcomes
    return applied_audit_flags(company_id)


def set_audit_flag(
    company_id: str,
    flag: str,
    *,
    set_by: str,
    source_url: str = "",
    note: str = "",
) -> Dict[str, Any]:
    from app.data.seed import get_data, list_companies, save_data

    if flag not in AUDIT_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown audit flag: {flag}")
    who = (set_by or "").strip()
    if not who:
        raise HTTPException(status_code=400, detail="set_by required")
    src = (source_url or "").strip()
    if not src:
        raise HTTPException(status_code=400, detail="source_url required")
    if not any(c["id"] == company_id for c in list_companies()):
        raise HTTPException(status_code=404, detail="Company not found")
    rec = {
        "flag": flag,
        "set_by": who,
        "source_url": src,
        "note": (note or "").strip(),
        "set_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    data = get_data()
    store = data.setdefault("company_audit_flags", {})
    rows = [r for r in (store.get(company_id) or []) if r.get("flag") != flag]
    rows.append(rec)
    store[company_id] = rows
    save_data()
    return rec


def clear_audit_flag(company_id: str, flag: str) -> None:
    from app.data.seed import get_data, save_data

    data = get_data()
    store = data.setdefault("company_audit_flags", {})
    rows = [r for r in (store.get(company_id) or []) if r.get("flag") != flag]
    if rows:
        store[company_id] = rows
    else:
        store.pop(company_id, None)
    save_data()


def audited_company_gci(
    outcomes: Sequence[GuidanceOutcome],
    *,
    company_id: Optional[str] = None,
    audit_flags: Optional[Sequence[str]] = None,
    **kwargs: Any,
) -> Optional[float]:
    """Company GCI after analyst-set audit deductions — the number every surface must show."""
    rows = list(outcomes)
    flags = list(audit_flags) if audit_flags is not None else applied_audit_flags(company_id)
    return compute_company_gci(rows, audit_flags=flags, **kwargs)


def score_meta(
    outcomes: Sequence[GuidanceOutcome],
    *,
    scoreable: bool = True,
    company_id: Optional[str] = None,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """Published-score provenance (W1.3/W1.4): tier, depth, as-of, composite parts.

    ``gci_score`` here equals :func:`audited_company_gci` for the same rows.
    """
    from app.services.gci_scoring import algorithm_id, compute_gci_v3_detail, scorer_version
    from app.services.score_policy import confidence_tier, excluded_from_score, is_pending_guidance_cite

    rows = list(outcomes)
    flags = applied_audit_flags(company_id)
    empty = {
        "gci_score": None,
        "by_metric": {},
        "context_metrics": {},
        "periods_by_metric": {},
        "composite_weights": {},
        "confidence_tier": None,
        "closed_periods": 0,
        "metrics_scored": 0,
        "as_of": None,
        "reviewed_at": None,
        "algorithm_id": algorithm_id(),
    }
    if not scoreable or not rows:
        return empty
    ver = scorer_version()
    if ver == "v2":
        score = audited_company_gci(rows, company_id=company_id, audit_flags=flags)
        return {**empty, "gci_score": score}
    res = compute_gci_v3_detail(rows, audit_flags=flags, version=ver)
    if res.gci is None:
        return empty
    as_of_dates = sorted(
        {
            o.as_of
            for o in rows
            if o.as_of
            and o.actual_value is not None
            and not o.unmapped
            and not is_pending_guidance_cite(o)
            and not excluded_from_score(o)
        }
    )
    review_dates = sorted(
        {
            o.reviewed_at
            for o in rows
            if o.reviewed_at and o.actual_value is not None and not excluded_from_score(o)
        }
    )
    # Decision D-tier (2026-09-29): a metric counts toward evidence breadth as soon
    # as it has one closed, analyst-reviewed result — whether it enters the
    # composite or is shown as context. The composite weighting is unchanged.
    metrics_scored = len(res.by_metric) + len(
        [m for m in res.context_metrics if m not in res.by_metric]
    )
    return {
        "gci_score": res.gci,
        "by_metric": res.by_metric,
        "context_metrics": res.context_metrics,
        "periods_by_metric": res.periods_by_metric,
        "composite_weights": {k: round(v, 2) for k, v in res.weights_used.items()},
        "confidence_tier": confidence_tier(
            closed_periods=res.periods_used,
            metrics_scored=metrics_scored,
            data_quality=data_quality,
        ),
        "closed_periods": res.periods_used,
        "metrics_scored": metrics_scored,
        "as_of": as_of_dates[-1] if as_of_dates else None,
        "reviewed_at": review_dates[-1] if review_dates else None,
        "algorithm_id": algorithm_id(),
    }


def audit_summary(
    outcomes: Sequence[GuidanceOutcome],
    *,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    records = list_audit_flag_records(company_id)
    flags = sorted({str(r["flag"]) for r in records})
    deduction = audit_deduction(outcomes, flags)
    badges = [
        {
            "flag": r["flag"],
            "label": AUDIT_LABELS.get(r["flag"], str(r["flag"]).replace("_", " ").title()),
            "points": AUDIT_PENALTY_PTS.get(r["flag"], 0.0),
            "severity": AUDIT_SEVERITY.get(r["flag"], "medium"),
            "set_by": r.get("set_by"),
            "source_url": r.get("source_url"),
            "set_at": r.get("set_at"),
            "note": r.get("note") or "",
        }
        for r in records
    ]
    return {
        "flags": flags,
        "deduction": round(float(deduction), 1),
        "badges": badges,
        "note": (
            "A deduction applies only when an analyst records the flag with a source filing. "
            "Keyword matches never move the GCI."
        ),
    }


def revision_summaries(outcomes: Sequence[GuidanceOutcome]) -> List[Dict[str, Any]]:
    """Count, direction, and average size of in-year revisions. Not a second index."""
    rows: List[Dict[str, Any]] = []
    for o in outcomes:
        revs = list(o.revisions or ())
        if not revs:
            continue
        low = o.guided_low if o.guided_low is not None else o.guided_value
        high = o.guided_high if o.guided_high is not None else o.guided_value
        prev = (float(low) + float(high)) / 2.0
        moves: List[float] = []
        for rev in revs:
            try:
                lo = float(rev["guided_low"])
                hi = float(rev["guided_high"])
            except (KeyError, TypeError, ValueError):
                continue
            mid = (lo + hi) / 2.0
            moves.append(abs(mid - prev))
            prev = mid
        if not moves:
            continue
        rows.append(
            {
                "period": o.period,
                "metric": o.metric,
                "count": len(moves),
                "direction": revision_direction(o) or "unchanged",
                "average_abs_move": round(sum(moves) / len(moves), 2),
            }
        )
    return rows


def revision_timeline(
    outcomes: Sequence[GuidanceOutcome],
    *,
    company_id: str = "",
    ticker: str = "",
) -> List[Dict[str, Any]]:
    """Chronological guidance → revise → actual → drop/restatement events."""
    events: List[Dict[str, Any]] = []

    by_thread: Dict[str, List[GuidanceOutcome]] = {}
    singles: List[GuidanceOutcome] = []
    for o in outcomes:
        if o.thread_id:
            by_thread.setdefault(o.thread_id, []).append(o)
        else:
            singles.append(o)

    def _sort_key(o: GuidanceOutcome) -> Tuple:
        return (o.as_of or "9999", o.period, o.metric)

    for tid, rows in by_thread.items():
        ordered = sorted(rows, key=_sort_key)
        prev: Optional[GuidanceOutcome] = None
        for o in ordered:
            label = classify_outcome(o).value
            kind = "stated"
            if prev is not None:
                d = _mid(o) - _mid(prev)
                if abs(d) >= 0.5:
                    kind = "revised_up" if d > 0 else "revised_down"
                else:
                    kind = "reiterated"
            if o.dropped or label == "dropped":
                kind = "withdrawn"
            elif label in ("met", "exceeded", "missed") and o.actual_value is not None:
                kind = f"resolved_{label}"
            if "restat" in _text_blob(o):
                kind = "restatement"
            detail = _event_detail(kind, o, prev)

            severity = "low"
            if kind in ("withdrawn", "restatement", "resolved_missed"):
                severity = "high"
            elif kind.startswith("revised"):
                severity = "medium"

            events.append(
                {
                    "as_of": o.as_of or o.period,
                    "period": o.period,
                    "metric": o.metric,
                    "thread_id": tid,
                    "kind": kind,
                    "label": label,
                    "detail": detail,
                    "guided_value": o.guided_value,
                    "guided_low": o.guided_low,
                    "guided_high": o.guided_high,
                    "actual_value": o.actual_value,
                    "source_url": o.source_url,
                    "quote_span": o.quote_span,
                    "severity": severity,
                    "company_id": company_id,
                    "ticker": ticker,
                }
            )
            prev = o

    for o in sorted(singles, key=_sort_key):
        label = classify_outcome(o).value
        kind = "stated"
        if o.dropped or label == "dropped":
            kind = "withdrawn"
        elif label in ("met", "exceeded", "missed") and o.actual_value is not None:
            kind = f"resolved_{label}"
        if "restat" in _text_blob(o):
            kind = "restatement"
        events.append(
            {
                "as_of": o.as_of or o.period,
                "period": o.period,
                "metric": o.metric,
                "thread_id": None,
                "kind": kind,
                "label": label,
                "detail": _event_detail(kind, o),
                "guided_value": o.guided_value,
                "guided_low": o.guided_low,
                "guided_high": o.guided_high,
                "actual_value": o.actual_value,
                "source_url": o.source_url,
                "quote_span": o.quote_span,
                "severity": "high" if kind in ("withdrawn", "restatement", "resolved_missed") else "low",
                "company_id": company_id,
                "ticker": ticker,
            }
        )

    # Sort oldest → newest by as_of / period
    def _ek(e: Dict[str, Any]) -> Tuple:
        return (str(e.get("as_of") or ""), str(e.get("period") or ""), str(e.get("metric") or ""))

    return sorted(events, key=_ek)


def company_red_alerts(
    outcomes: Sequence[GuidanceOutcome],
    *,
    company_id: str,
    ticker: str,
) -> List[Dict[str, Any]]:
    """Per-company red alert cards for dossier (subset of global alert rail)."""
    alerts: List[Dict[str, Any]] = []
    summary = audit_summary(outcomes, company_id=company_id)
    for b in summary["badges"]:
        alerts.append(
            {
                "company_id": company_id,
                "ticker": ticker,
                "kind": b["flag"],
                "message": f"{b['label']}, {b['points']:.0f} points deducted from the GCI.",
                "severity": b["severity"],
                "audit_flag": b["flag"],
                "deduction_pts": b["points"],
            }
        )
    for o in outcomes:
        label = classify_outcome(o).value
        if label == "missed":
            alerts.append(
                {
                    "company_id": company_id,
                    "ticker": ticker,
                    "kind": "large_miss",
                    "message": _event_detail("resolved_missed", o),
                    "severity": "high",
                    "period": o.period,
                    "metric": o.metric,
                    "source_url": o.source_url,
                }
            )
        if label == "dropped":
            alerts.append(
                {
                    "company_id": company_id,
                    "ticker": ticker,
                    "kind": "guidance_dropped",
                    "message": _event_detail("withdrawn", o),
                    "severity": "high",
                    "period": o.period,
                    "metric": o.metric,
                    "source_url": o.source_url,
                }
            )
    return alerts
