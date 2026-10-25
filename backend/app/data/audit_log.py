"""Phase 5 — audit log for review / ingest / admin actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PATH = Path(__file__).with_name("audit.json")
_LOG: Optional[List[Dict[str, Any]]] = None


def _load() -> List[Dict[str, Any]]:
    global _LOG
    if _LOG is None:
        if _PATH.exists():
            _LOG = json.loads(_PATH.read_text())
        else:
            _LOG = []
    return _LOG


def save() -> None:
    _PATH.write_text(json.dumps(_load(), indent=2))


def record(
    action: str,
    *,
    org: str = "demo",
    actor: str = "system",
    role: str = "analyst",
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "org": org,
        "actor": actor,
        "role": role,
        "detail": detail or {},
    }
    log = _load()
    log.append(row)
    if len(log) > 2000:
        del log[:1000]
    save()
    return row


def list_by_action(action: str) -> List[Dict[str, Any]]:
    return [r for r in _load() if r.get("action") == action]


def has_label_accept(*, company_id: str, period: str, metric: str) -> bool:
    for r in list_by_action("label_accept"):
        d = r.get("detail") or {}
        if (
            d.get("company_id") == company_id
            and d.get("period") == period
            and d.get("metric") == metric
        ):
            return True
    return False


def record_label_accept(
    *,
    company_id: str,
    period: str,
    metric: str,
    submitter_id: Optional[str],
    reviewer_id: Optional[str],
    draft_id: Optional[str] = None,
    org: str = "demo",
    actor: str = "system",
    role: str = "analyst",
) -> Optional[Dict[str, Any]]:
    """Idempotent ``label_accept`` row keyed by company/period/metric."""
    if has_label_accept(company_id=company_id, period=period, metric=metric) and not draft_id:
        return None
    if draft_id:
        for r in list_by_action("label_accept"):
            if (r.get("detail") or {}).get("draft_id") == draft_id:
                return None
    return record(
        "label_accept",
        org=org,
        actor=actor,
        role=role,
        detail={
            "company_id": company_id,
            "period": period,
            "metric": metric,
            "submitter_id": submitter_id,
            "reviewer_id": reviewer_id,
            "draft_id": draft_id,
        },
    )


def seed_hand_labeled_label_accepts() -> int:
    """Backfill ``label_accept`` rows for already-stamped dual-cited outcomes (W2.5)."""
    from app.data.hand_labeled import HAND_LABELED

    n = 0
    for cid, rows in HAND_LABELED.items():
        for r in rows:
            if not (r.get("reviewed_by") and r.get("reviewed_at")):
                continue
            if r.get("actual_value") is None:
                continue
            wrote = record_label_accept(
                company_id=cid,
                period=str(r.get("period") or ""),
                metric=str(r.get("metric") or ""),
                submitter_id="analyst:nv",
                reviewer_id=str(r.get("reviewed_by")),
                org="citealpha",
                actor=str(r.get("reviewed_by")),
                role="analyst",
            )
            if wrote:
                n += 1
    return n


def list_audit(org: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    rows = _load()
    if org:
        rows = [r for r in rows if r.get("org") == org]
    return rows[-limit:]


_SECRET_PARTS = ("password", "token", "secret", "api_key", "authorization", "cookie")


def _scrub(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return None
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _SECRET_PARTS):
                continue
            out[str(key)] = _scrub(item, depth + 1)
        return out
    if isinstance(value, list):
        return [_scrub(item, depth + 1) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)[:200]


def public_events(org: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Newest first. Drops password, token, and key fields."""
    rows = list_audit(org=org, limit=limit)
    events: List[Dict[str, Any]] = []
    for row in reversed(rows):
        events.append(
            {
                "ts": row.get("ts"),
                "action": row.get("action"),
                "org": row.get("org"),
                "actor": row.get("actor"),
                "role": row.get("role"),
                "detail": _scrub(row.get("detail") or {}),
            }
        )
    return events
