"""Pilot org template + conversion checklist (in-product)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.data.seed import get_data, save_data
from app.services import orgs

TERM_CHOICES = (30, 45, 60)
PAID_HOLDINGS_PLANS = frozenset({"desk", "enterprise", "onestop"})


def require_term_days(value: object) -> int:
    """Admin-chosen evaluation length. Anything else is refused."""
    try:
        days = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="term_days must be 30, 45, or 60")
    if days not in TERM_CHOICES:
        raise HTTPException(status_code=400, detail="term_days must be 30, 45, or 60")
    return days


def pilot_term_open(org_id: str, *, today: Optional[datetime] = None) -> bool:
    """True only for an admin-approved pilot still inside its 30/45/60 day term."""
    row = (get_data().get("pilot_checklists") or {}).get(org_id) or {}
    if not row.get("approved"):
        return False
    days = row.get("term_days")
    if days not in TERM_CHOICES:
        return False
    started = str(row.get("created_at") or "")
    try:
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
    except ValueError:
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = today or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.date() < (start.date() + timedelta(days=int(days)))


def holdings_feature_open(org_id: str, plan: str) -> bool:
    """Paid desks keep Holdings. A pilot has it only while the approved term is open."""
    if plan in PAID_HOLDINGS_PLANS:
        return True
    if plan != "pilot":
        return False
    return pilot_term_open(org_id)


def pilot_evaluation_ended(org_id: str) -> bool:
    """An approved evaluation that is past its 30, 45, or 60 days.

    A pilot org that was never approved is unchanged. That is the standing
    desk key, not an evaluation whose clock has run out.
    """
    row = (get_data().get("pilot_checklists") or {}).get(org_id) or {}
    if not row.get("approved"):
        return False
    return not pilot_term_open(org_id)


CHECKLIST_ITEMS: List[Dict[str, str]] = [
    {
        "id": "access",
        "phase": "day0",
        "label": "Named users can open Tracker + open Infosys evidence trail",
    },
    {
        "id": "workshop",
        "phase": "day0",
        "label": "2-hour onboarding workshop completed",
    },
    {
        "id": "habit_stars",
        "phase": "week1",
        "label": "Each analyst starred 3–5 coverage names",
    },
    {
        "id": "habit_alerts",
        "phase": "week1",
        "label": "Alerts reviewed at least once this week",
    },
    {
        "id": "habit_review",
        "phase": "week1",
        "label": "Practiced Accept/Reject on one extract or doc",
    },
    {
        "id": "habit_cite",
        "phase": "week1",
        "label": "Cited ≥1 evidence row in an internal draft / IC note",
    },
    {
        "id": "quality_feedback",
        "phase": "week2",
        "label": "Logged disagreements (band / period / label)",
    },
    {
        "id": "hand_labeled_only",
        "phase": "week2",
        "label": "External citations limited to hand_labeled / citeable rows",
    },
    {
        "id": "stakeholder_review",
        "phase": "week4",
        "label": "Stakeholder review: score usefulness vs noise",
    },
    {
        "id": "sku_decision",
        "phase": "week4",
        "label": "Decide Desk seat vs Enterprise API",
    },
    {
        "id": "order_form",
        "phase": "week4",
        "label": "Order form / MSA path started",
    },
    {
        "id": "convert_intent",
        "phase": "week4",
        "label": "Explicit yes/no on willingness to convert",
    },
]


def _activity_counts(org_id: str) -> Dict[str, int]:
    """Evidence-based checklist signals — does not invent GCI."""
    from app.services import activity as activity_svc
    from app.services import feedback as fb_svc

    counts = fb_svc.counts_for_org(org_id)
    act = activity_svc.counts(org_id)
    notes_n = 0
    try:
        from app.services import analyst_notes

        notes_n = len((analyst_notes._load() or {}).get("notes") or [])
    except Exception:
        notes_n = 0
    return {
        "feedback_logged": int(counts.get("total") or 0),
        "quality_feedback": int(counts.get("quality") or 0),
        "convert_intent": int(counts.get("convert_intent") or 0),
        "citations_in_notes": notes_n,
        "citations_copied": int(act.get("cite_copies") or 0),
        "dossier_opens": int(act.get("dossier_opens") or 0),
    }


def provision_pilot_org(
    *,
    name: str,
    owner_email: Optional[str] = None,
    seats: int = 5,
    term_days: object = None,
) -> Dict[str, Any]:
    """Create a B2B pilot tenant with conversion checklist initialized."""
    snap = orgs.create_org(
        name=name,
        plan="pilot",
        account_type="b2b",
        owner_email=owner_email,
        seats=min(5, max(1, seats)),
    )
    days = require_term_days(term_days)
    oid = snap["id"]
    data = get_data()
    checklists = data.setdefault("pilot_checklists", {})
    started = datetime.now(timezone.utc).isoformat()
    checklists[oid] = {
        "org_id": oid,
        "created_at": started,
        "status": "active",
        "approved": True,
        "term_days": days,
        "items": {item["id"]: False for item in CHECKLIST_ITEMS},
        "notes": "",
        "convert_intent": None,
        "target_sku": None,
    }
    orgs_row = data.setdefault("orgs", {}).get(oid) or {}
    orgs_row["pilot_template"] = True
    orgs_row["pilot_started_at"] = started
    orgs_row["pilot_term_days"] = days
    data["orgs"][oid] = orgs_row
    save_data()
    return {
        "org": snap,
        "checklist": get_pilot_checklist(oid),
        "note": f"Pilot: Sensex coverage · ≤5 seats · {days}-day evaluation, started on approval.",
    }


def get_pilot_checklist(org_id: str) -> Dict[str, Any]:
    data = get_data()
    row = (data.get("pilot_checklists") or {}).get(org_id)
    if not row:
        # Lazy-init for demo/pilot orgs
        checklists = data.setdefault("pilot_checklists", {})
        checklists[org_id] = {
            "org_id": org_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "term_days": None,
            "approved": False,
            "items": {item["id"]: False for item in CHECKLIST_ITEMS},
            "notes": "",
            "convert_intent": None,
            "target_sku": None,
        }
        save_data()
        row = checklists[org_id]

    items_state = dict(row.get("items") or {})
    activity = _activity_counts(org_id)
    if activity.get("quality_feedback", 0) > 0:
        items_state["quality_feedback"] = True
    if activity.get("convert_intent", 0) > 0:
        items_state["convert_intent"] = True
        row["convert_intent"] = row.get("convert_intent") or "yes"
    if activity.get("dossier_opens", 0) > 0:
        items_state["access"] = True
    if activity.get("citations_copied", 0) > 0 or activity.get("citations_in_notes", 0) > 0:
        items_state["habit_cite"] = True
    row["items"] = items_state
    items_out = []
    done = 0
    for spec in CHECKLIST_ITEMS:
        checked = bool(items_state.get(spec["id"]))
        if checked:
            done += 1
        items_out.append({**spec, "done": checked})

    total = len(CHECKLIST_ITEMS)
    ready = done >= 8 and row.get("convert_intent") in ("yes", True, "y")
    return {
        "org_id": org_id,
        "status": row.get("status") or "active",
        "term_days": row.get("term_days"),
        "approved": bool(row.get("approved")),
        "term_open": pilot_term_open(org_id),
        "created_at": row.get("created_at"),
        "progress": {"done": done, "total": total, "pct": round(100.0 * done / total, 1)},
        "items": items_out,
        "notes": row.get("notes") or "",
        "convert_intent": row.get("convert_intent"),
        "target_sku": row.get("target_sku"),
        "conversion_ready": ready,
        "next_step": (
            "Start MSA / Desk checkout on /billing"
            if ready
            else "Complete Week-1 habit items (cite evidence in a note)"
        ),
        "success_metrics": {
            "active_analysts_per_week": "≥3",
            "evidence_citations_in_notes": "≥1",
            "open_critical_bugs_gt_5d": 0,
        },
        "activity": activity,
    }


def patch_pilot_checklist(
    org_id: str,
    *,
    item_id: Optional[str] = None,
    done: Optional[bool] = None,
    notes: Optional[str] = None,
    convert_intent: Optional[str] = None,
    target_sku: Optional[str] = None,
) -> Dict[str, Any]:
    data = get_data()
    # Ensure exists
    get_pilot_checklist(org_id)
    row = data["pilot_checklists"][org_id]
    if item_id is not None:
        if item_id not in {x["id"] for x in CHECKLIST_ITEMS}:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=f"Unknown checklist item: {item_id}")
        if done is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="done required when setting item_id")
        row.setdefault("items", {})[item_id] = bool(done)
    if notes is not None:
        row["notes"] = notes
    if convert_intent is not None:
        row["convert_intent"] = convert_intent
    if target_sku is not None:
        row["target_sku"] = target_sku
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_data()
    return get_pilot_checklist(org_id)
