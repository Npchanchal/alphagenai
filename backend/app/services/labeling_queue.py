"""One-Stop labeling priority queue (process SLA + product backlog)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.data.seed import get_data, save_data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_queue(*, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = list(get_data().get("labeling_queue") or [])
    if org_id:
        rows = [r for r in rows if r.get("org_id") == org_id]
    return sorted(rows, key=lambda r: (0 if r.get("priority") == "high" else 1, r.get("created_at") or ""))


def enqueue(
    *,
    company_id: str,
    org_id: str = "demo",
    priority: str = "normal",
    note: str = "",
    requested_by: str = "api",
    kind: str = "label",
    flag: Optional[str] = None,
    period: Optional[str] = None,
    metric: Optional[str] = None,
) -> Dict[str, Any]:
    from app.services import repository

    try:
        detail = repository.get_company_gci(company_id)
        name = detail.name
        quality = detail.data_quality
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Unknown company: {company_id}") from e

    item = {
        "id": f"lq_{uuid4().hex[:10]}",
        "company_id": company_id,
        "company_name": name,
        "data_quality": quality,
        "org_id": org_id,
        "priority": "high" if priority == "high" else "normal",
        "note": note or "",
        "requested_by": requested_by,
        "status": "queued",
        "created_at": _now(),
        "kind": kind or "label",
        "flag": flag,
        "period": period,
        "metric": metric,
    }
    data = get_data()
    q = data.setdefault("labeling_queue", [])
    q.append(item)
    save_data()
    return item


def _open_suggestion(company_id: str, flag: str) -> bool:
    for row in list_queue():
        if (
            row.get("company_id") == company_id
            and row.get("flag") == flag
            and row.get("kind") == "audit_flag_suggestion"
            and row.get("status") in ("queued", "in_progress")
        ):
            return True
    return False


def enqueue_flag_suggestions(
    company_id: str,
    *,
    org_id: str = "demo",
    requested_by: str = "heuristic",
) -> List[Dict[str, Any]]:
    """Keyword heuristics → review queue only. Never applies a GCI deduction (W2.6)."""
    from app.data.seed import get_outcomes
    from app.services.guidance_flags import applied_audit_flags, suggest_audit_flags

    suggested = suggest_audit_flags(get_outcomes(company_id))
    applied = set(applied_audit_flags(company_id))
    created: List[Dict[str, Any]] = []
    for flag in suggested:
        if flag in applied or _open_suggestion(company_id, flag):
            continue
        created.append(
            enqueue(
                company_id=company_id,
                org_id=org_id,
                priority="high" if flag == "guidance_withdrawal" else "normal",
                note=(
                    f"Suggested audit flag `{flag}` (keyword heuristic). "
                    "Not applied to GCI until an analyst sets it with a source."
                ),
                requested_by=requested_by,
                kind="audit_flag_suggestion",
                flag=flag,
            )
        )
    return created


def _open_finding(company_id: str, kind: str, period: str, metric: str) -> bool:
    for row in list_queue():
        if (
            row.get("company_id") == company_id
            and row.get("kind") == kind
            and row.get("period") == period
            and row.get("metric") == metric
            and row.get("status") in ("queued", "in_progress")
        ):
            return True
    return False


def sync_reconcile_findings(company_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Queue metric/unit conflicts and numeric quiet-drop proposals. Does not change GCI.

    A second run does not stack an open item. A metric that is guided again cancels
    its open quiet-drop proposal.
    """
    from app.services import repository

    try:
        repository.get_company_gci(company_id)
    except Exception:
        return {"enqueued": 0, "cleared": 0, "skipped": "unknown_company"}

    conflicts = list(result.get("conflicts") or [])
    drops = list(result.get("quiet_drops") or [])
    want_drops = {(str(d.get("period")), str(d.get("metric"))) for d in drops}
    cleared = 0
    for row in list_queue():
        if (
            row.get("company_id") == company_id
            and row.get("kind") == "guidance_drop_suggestion"
            and row.get("status") in ("queued", "in_progress")
            and (str(row.get("period")), str(row.get("metric"))) not in want_drops
        ):
            update_status(row["id"], "cancelled")
            cleared += 1

    enqueued = 0
    for item in conflicts:
        period, metric = str(item.get("period") or ""), str(item.get("promise_metric") or "")
        if _open_finding(company_id, "match_conflict", period, metric):
            continue
        enqueue(
            company_id=company_id,
            kind="match_conflict",
            period=period,
            metric=metric,
            priority="high",
            requested_by="job:disclosure_reconcile",
            note=(
                f"{period} {metric} vs {item.get('result_metric')} ({item.get('reason')}). "
                f"Promise: {item.get('promise_quote')} "
                f"Result: {item.get('result_quote')}"
            ),
        )
        enqueued += 1
    for item in drops:
        period, metric = str(item.get("period") or ""), str(item.get("metric") or "")
        if _open_finding(company_id, "guidance_drop_suggestion", period, metric):
            continue
        docs = ", ".join(str(d) for d in (item.get("doc_ids") or []))
        enqueue(
            company_id=company_id,
            kind="guidance_drop_suggestion",
            period=period,
            metric=metric,
            priority="normal",
            requested_by="job:disclosure_reconcile",
            note=(
                f"{period} {metric} was absent from the next two guidance filings ({docs}). "
                "Not applied to the score until a reviewer sets the withdrawal flag."
            ),
        )
        enqueued += 1
    return {"enqueued": enqueued, "cleared": cleared}


def update_status(item_id: str, status: str, *, org_id: Optional[str] = None) -> Dict[str, Any]:
    """Set item status. When ``org_id`` is given, items owned by other orgs are treated as missing."""
    allowed = {"queued", "in_progress", "done", "cancelled"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    data = get_data()
    for row in data.get("labeling_queue") or []:
        if row.get("id") == item_id and (org_id is None or row.get("org_id") == org_id):
            row["status"] = status
            row["updated_at"] = _now()
            save_data()
            return row
    raise HTTPException(status_code=404, detail="Queue item not found")
