"""Inbound pilot evaluation requests — stored, then mailed to the sales inboxes."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.data.seed import get_data, save_data

log = logging.getLogger("intellens.pilot")

_DEFAULT_NOTIFY = "sales@citealpha.com,contact@ocotilloinnovation.com"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store() -> List[Dict[str, Any]]:
    return get_data().setdefault("pilot_requests", [])


def create_request(
    *,
    name: str,
    email: str,
    firm: str,
    role: str = "",
    team_size: str = "",
    message: str = "",
) -> Dict[str, Any]:
    row = {
        "id": f"pr_{uuid4().hex[:12]}",
        "name": name.strip(),
        "email": email.strip(),
        "firm": firm.strip(),
        "role": role.strip(),
        "team_size": team_size.strip(),
        "message": message.strip()[:4000],
        "status": "pending",
        "org_id": None,
        "admin_note": "",
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": _now(),
    }
    _store().append(row)
    save_data()
    _notify(row)
    return row


def pilot_notify_addresses() -> List[str]:
    """Comma-separated PILOT_REQUEST_TO. Unset uses the two sales inboxes."""
    raw = os.environ.get("PILOT_REQUEST_TO")
    if raw is None:
        raw = _DEFAULT_NOTIFY
    seen: List[str] = []
    for part in raw.split(","):
        addr = part.strip()
        if addr and addr not in seen:
            seen.append(addr)
    return seen[:10]


def _notify(row: Dict[str, Any]) -> None:
    """Mail the stored request. A send failure stays on the row and does not unstore it."""
    addresses = pilot_notify_addresses()
    if not addresses:
        return
    from app.services import mailer

    firm = row.get("firm") or row.get("name") or "CiteAlpha"
    subject = f"CiteAlpha pilot request — {firm}"
    body = "\n".join(
        [
            f"Name: {row.get('name') or ''}",
            f"Email: {row.get('email') or ''}",
            f"Firm: {row.get('firm') or ''}",
            f"Role: {row.get('role') or '—'}",
            f"Team: {row.get('team_size') or '—'}",
            "",
            str(row.get("message") or "(no note)"),
            "",
            f"Request {row.get('id')} · {row.get('created_at')}",
        ]
    )
    reply_to = str(row.get("email") or "")
    results: List[Dict[str, Any]] = []
    for addr in addresses:
        try:
            sent = mailer.send_mail(to=addr, subject=subject, body=body, reply_to=reply_to)
        except Exception as exc:  # noqa: BLE001 — intake must survive a mail outage
            log.exception("pilot_notify_failed")
            sent = {"status": "error", "to": addr, "detail": str(exc)}
        results.append({"to": sent.get("to") or addr, "status": sent.get("status") or "error"})
    row["notify"] = results
    save_data()


def list_requests(*, status: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = list(_store())
    if status:
        want = status.strip().lower()
        rows = [r for r in rows if (r.get("status") or "").lower() == want]
    return sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)


def delete_request(request_id: str) -> Dict[str, Any]:
    """Drop the intake row. An organisation already provisioned from it stays."""
    rows = _store()
    for index, row in enumerate(rows):
        if row.get("id") == request_id:
            rows.pop(index)
            save_data()
            return {"deleted": request_id, "org_id": row.get("org_id")}
    raise HTTPException(status_code=404, detail="Pilot request not found")


def _find_request(request_id: str) -> Optional[Dict[str, Any]]:
    for row in _store():
        if row.get("id") == request_id:
            return row
    return None


def review_request(
    request_id: str,
    *,
    action: str,
    actor: Dict[str, Any],
    note: str = "",
    term_days: Optional[int] = None,
) -> Dict[str, Any]:
    row = _find_request(request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pilot request not found")
    act = (action or "").strip().lower()
    if act not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    if row.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Request already {row.get('status')}")

    reviewer = actor.get("email") or actor.get("name") or actor.get("user_id") or "admin"
    row["reviewed_by"] = reviewer
    row["reviewed_at"] = _now()
    row["admin_note"] = (note or "").strip()[:1000]

    if act == "reject":
        row["status"] = "rejected"
        save_data()
        return {"ok": True, "request": row}

    from app.services.pilot_checklist import provision_pilot_org, require_term_days

    days = require_term_days(term_days)
    org_name = row.get("firm") or row.get("name") or "Pilot Desk"
    provisioned = provision_pilot_org(
        name=str(org_name),
        owner_email=row.get("email") or None,
        term_days=days,
    )
    row["status"] = "approved"
    row["term_days"] = days
    row["org_id"] = provisioned.get("org", {}).get("id")
    owner_invite = _invite_owner(str(row["org_id"] or ""), invited_by=str(reviewer), email=str(row.get("email") or ""))
    row["owner_invite"] = {
        "email": owner_invite.get("email") or row.get("email"),
        "mail_status": owner_invite.get("mail_status") or "error",
        "role": "admin",
    }
    if owner_invite.get("detail"):
        row["owner_invite"]["detail"] = owner_invite["detail"]
    save_data()
    response_invite = dict(row["owner_invite"])
    if owner_invite.get("dev_token"):
        response_invite["dev_token"] = owner_invite["dev_token"]
        response_invite["dev_link"] = owner_invite.get("dev_link")
    return {
        "ok": True,
        "request": row,
        "provisioned": provisioned,
        "owner_invite": response_invite,
    }


def _invite_owner(org_id: str, *, invited_by: str, email: str) -> Dict[str, Any]:
    """Seat the recorded owner. A mail or lookup failure leaves the approved desk in place."""
    if not org_id:
        return {"email": email, "mail_status": "error", "detail": "Organisation was not created"}
    from app.services import orgs as org_svc

    try:
        return org_svc.invite_recorded_owner(org_id=org_id, invited_by=invited_by)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Invite was not sent"
        log.warning("owner_invite_refused org=%s detail=%s", org_id, detail)
        return {"email": email, "mail_status": "error", "role": "admin", "detail": detail}
    except Exception:
        log.exception("owner_invite_failed")
        return {"email": email, "mail_status": "error", "role": "admin", "detail": "Invite mail failed"}
