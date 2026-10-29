"""Platform admin portal — role-based access separate from org admin."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, Header, HTTPException

from app.data.seed import get_data
from app.services import feedback as feedback_svc
from app.services import session_auth
from app.services.auth import lookup_api_key

PLATFORM_ADMIN_ROLES = frozenset({"super", "ops", "compliance", "billing", "support"})

# Platform super is these operator logins. No other email can hold it.
SUPER_EMAILS = frozenset({
    "dk@citealpha.com",
    "admin.team@citealpha.com",
})

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "super": {
        "portal.access",
        "orgs.read",
        "orgs.write",
        "users.read",
        "users.write",
        "feedback.read",
        "feedback.write",
        "legal.read",
        "legal.write",
        "billing.read",
        "billing.write",
        "pilot.manage",
        "audit.read",
        "system.ops",
    },
    "ops": {
        "portal.access",
        "orgs.read",
        "orgs.write",
        "users.read",
        "feedback.read",
        "feedback.write",
        "pilot.manage",
        "audit.read",
    },
    "compliance": {
        "portal.access",
        "legal.read",
        "legal.write",
        "audit.read",
        "orgs.read",
    },
    "billing": {
        "portal.access",
        "billing.read",
        "billing.write",
        "orgs.read",
        "audit.read",
    },
    "support": {
        "portal.access",
        "feedback.read",
        "feedback.write",
        "users.read",
        "orgs.read",
        "audit.read",
    },
}

ALL_PERMISSIONS: Set[str] = set().union(*ROLE_PERMISSIONS.values())


def permissions_for_role(role: Optional[str]) -> Set[str]:
    r = (role or "").strip().lower()
    if r == "super":
        return set(ALL_PERMISSIONS)
    return set(ROLE_PERMISSIONS.get(r, set()))


def effective_platform_role(
    email: Optional[str],
    role: Optional[str],
    *,
    api_key: bool = False,
) -> Optional[str]:
    """Super is an operator login. A stored super on any other email does not count."""
    if not role:
        return None
    cleaned = str(role).strip().lower()
    if cleaned == "super" and not api_key:
        if str(email or "").strip().lower() not in SUPER_EMAILS:
            return None
    return cleaned


def enforce_super_roster(users: List[Dict[str, Any]]) -> List[str]:
    """Give super to the operator emails and take it off every other login."""
    touched: List[str] = []
    for user in users:
        email = str(user.get("email") or "").strip().lower()
        stored = user.get("platform_admin_role")
        changed = False
        if email in SUPER_EMAILS:
            if stored != "super":
                user["platform_admin_role"] = "super"
                changed = True
        elif stored == "super":
            user.pop("platform_admin_role", None)
            changed = True
        if changed:
            touched.append(email or str(user.get("id") or ""))
    return touched


def has_permission(actor: Dict[str, Any], perm: str) -> bool:
    return perm in set(actor.get("permissions") or [])


def _actor_from_user(user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    role = effective_platform_role(user.get("email"), user.get("platform_admin_role"))
    if not role or role not in PLATFORM_ADMIN_ROLES:
        return None
    perms = sorted(permissions_for_role(str(role)))
    return {
        "source": "session",
        "user_id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "org_id": user.get("org_id"),
        "org_role": user.get("role"),
        "platform_admin_role": role,
        "permissions": perms,
    }


def _actor_from_api_key(key_row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    role = effective_platform_role(None, key_row.get("platform_admin_role"), api_key=True)
    if not role or role not in PLATFORM_ADMIN_ROLES:
        return None
    perms = sorted(permissions_for_role(str(role)))
    return {
        "source": "api_key",
        "user_id": None,
        "email": None,
        "name": key_row.get("key"),
        "org_id": key_row.get("org") or key_row.get("org_id"),
        "org_role": key_row.get("role"),
        "platform_admin_role": role,
        "permissions": perms,
        "api_key": key_row.get("key"),
    }


def resolve_platform_admin(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = session_auth.resolve_token(session_auth.extract_bearer(authorization))
    if user:
        actor = _actor_from_user(user)
        if actor:
            return actor
        raise HTTPException(status_code=403, detail="Platform admin access required")
    if x_api_key:
        row = lookup_api_key(x_api_key)
        if row is None:
            raise HTTPException(status_code=403, detail="Invalid API key")
        actor = _actor_from_api_key(row)
        if actor:
            return actor
        raise HTTPException(status_code=403, detail="Platform admin access required")
    raise HTTPException(status_code=401, detail="Authentication required")


def platform_actor_or_none(
    authorization: Optional[str], x_api_key: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Like ``resolve_platform_admin`` but returns None instead of raising."""
    user = session_auth.resolve_token(session_auth.extract_bearer(authorization))
    if user:
        return _actor_from_user(user)
    if x_api_key:
        row = lookup_api_key(x_api_key)
        if row:
            return _actor_from_api_key(row)
    return None


def require_platform_perm(perm: str):
    def _dep(actor: Dict[str, Any] = Depends(resolve_platform_admin)) -> Dict[str, Any]:
        if not has_permission(actor, perm):
            raise HTTPException(
                status_code=403,
                detail=f"Platform role {actor.get('platform_admin_role')} lacks {perm}",
            )
        return actor

    return _dep


def portal_me(actor: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "platform_admin_role": actor.get("platform_admin_role"),
        "permissions": actor.get("permissions") or [],
        "source": actor.get("source"),
        "email": actor.get("email"),
        "name": actor.get("name"),
        "sections": _sections_for(actor),
    }


def _sections_for(actor: Dict[str, Any]) -> List[Dict[str, str]]:
    perms = set(actor.get("permissions") or [])
    sections: List[Dict[str, str]] = [{"id": "overview", "label": "Overview"}]
    if "orgs.read" in perms:
        sections.append({"id": "orgs", "label": "Organizations"})
    if "users.read" in perms:
        sections.append({"id": "users", "label": "Users"})
    if "feedback.read" in perms:
        sections.append({"id": "feedback", "label": "Feedback"})
    if "legal.read" in perms:
        sections.append({"id": "legal", "label": "Legal"})
    if "billing.read" in perms:
        sections.append({"id": "billing", "label": "Billing"})
    if "audit.read" in perms:
        sections.append({"id": "audit", "label": "Audit"})
        sections.append({"id": "labeling", "label": "Labeling"})
        sections.append({"id": "commitments", "label": "Commitments"})
    if "audit.read" in perms or "billing.read" in perms or "legal.read" in perms:
        sections.append({"id": "reports", "label": "Reports"})
    if "pilot.manage" in perms:
        sections.append({"id": "pilot-requests", "label": "Pilot requests"})
    if "system.ops" in perms:
        sections.append({"id": "system", "label": "System"})
    return sections


_BUILTIN_ORG_IDS = frozenset({"demo", "retail", "onestop-demo", "citealpha-team"})


def _seat_holders(org_id: str) -> List[Dict[str, Any]]:
    """Logins on this organisation. Guests are not seats."""
    rows: List[Dict[str, Any]] = []
    for user in session_auth._load_users().get("users", []):
        if user.get("org_id") != org_id or (user.get("kind") or "") == "guest":
            continue
        rows.append(
            {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "role": user.get("role"),
                "active": user.get("active", True) is not False,
                "protected": bool(user.get("protected")),
                "platform_admin_role": effective_platform_role(
                    user.get("email"), user.get("platform_admin_role")
                ),
            }
        )
    return sorted(rows, key=lambda r: (str(r.get("email") or ""), str(r.get("id") or "")))


def _org_delete_block(org_id: str, row: Dict[str, Any]) -> Optional[str]:
    if org_id in _BUILTIN_ORG_IDS or row.get("protected"):
        return "Standing organisation"
    if row.get("members"):
        return "Remove the seat holders before deleting this organisation"
    return None


def list_orgs() -> List[Dict[str, Any]]:
    from app.services import orgs as org_svc

    data = get_data()
    out: List[Dict[str, Any]] = []
    for oid, row in (data.get("orgs") or {}).items():
        try:
            snap = org_svc.org_snapshot(str(oid))
        except HTTPException:
            snap = dict(row or {})
            snap["id"] = oid
        snap["members"] = _seat_holders(str(oid))
        snap["delete_block"] = _org_delete_block(str(oid), snap)
        snap["deletable"] = snap["delete_block"] is None
        out.append(snap)
    return sorted(out, key=lambda r: str(r.get("id") or r.get("name") or ""))


def list_users() -> List[Dict[str, Any]]:
    rows = session_auth._load_users().get("users", [])
    out = []
    for u in rows:
        out.append(
            {
                "id": u.get("id"),
                "email": u.get("email"),
                "name": u.get("name"),
                "kind": u.get("kind"),
                "account_type": u.get("account_type"),
                "org_id": u.get("org_id"),
                "role": u.get("role"),
                "platform_admin_role": effective_platform_role(
                    u.get("email"), u.get("platform_admin_role")
                ),
                "email_verified": bool(u.get("email_verified")),
                "active": u.get("active", True) is not False,
                "protected": bool(u.get("protected")),
                "created_at": u.get("created_at"),
            }
        )
    return sorted(out, key=lambda r: str(r.get("email") or r.get("id") or ""))


def assign_platform_admin_role(
    user_id: str,
    role: Optional[str],
    *,
    actor: Dict[str, Any],
) -> Dict[str, Any]:
    if not has_permission(actor, "users.write"):
        raise HTTPException(status_code=403, detail="users.write required")
    if role and role not in PLATFORM_ADMIN_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"platform_admin_role must be one of {sorted(PLATFORM_ADMIN_ROLES)} or null",
        )
    user = session_auth._find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    email = str(user.get("email") or "").strip().lower()
    if email in SUPER_EMAILS and role != "super":
        raise HTTPException(status_code=400, detail="This operator account keeps platform super")
    if role == "super" and email not in SUPER_EMAILS:
        raise HTTPException(
            status_code=400,
            detail="Platform super is limited to the CiteAlpha operator accounts",
        )
    if role:
        user["platform_admin_role"] = role
    else:
        user.pop("platform_admin_role", None)
    session_auth._save_users()
    session_auth.reload_users_cache()
    user = session_auth._find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "email": user.get("email"),
        "platform_admin_role": user.get("platform_admin_role"),
    }


def audit_summary() -> Dict[str, Any]:
    data = get_data()
    feedback_rows = feedback_svc.list_feedback()
    from app.services import pilot_request as pr_svc

    pilot_rows = pr_svc.list_requests()
    return {
        "orgs": len(data.get("orgs") or {}),
        "users": len(session_auth._load_users().get("users", [])),
        "feedback_open": sum(1 for r in feedback_rows if r.get("status") == "open"),
        "feedback_total": len(feedback_rows),
        "pilot_requests_pending": sum(1 for r in pilot_rows if r.get("status") == "pending"),
        "pilot_requests_total": len(pilot_rows),
        "reviews": len(data.get("reviews") or []),
        "pending_extracts": len(data.get("pending_extracts") or []),
    }


def _sync_seats(org_id: str) -> None:
    data = get_data()
    orgs = data.get("orgs") or {}
    if org_id not in orgs:
        return
    used = sum(
        1
        for user in session_auth._load_users().get("users", [])
        if user.get("org_id") == org_id
        and (user.get("kind") or "") != "guest"
        and user.get("active", True) is not False
    )
    orgs[org_id]["seats_used"] = used
    from app.data.seed import save_data

    save_data()


def delete_user(user_id: str, *, actor: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a login and free its seat. Standing team accounts stay."""
    user = session_auth._find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("protected"):
        raise HTTPException(status_code=400, detail="Standing team account cannot be deleted")
    actor_id = actor.get("user_id")
    actor_email = str(actor.get("email") or "").strip().lower()
    user_email = str(user.get("email") or "").strip().lower()
    if (actor_id and actor_id == user.get("id")) or (
        actor_email and user_email and actor_email == user_email
    ):
        raise HTTPException(status_code=400, detail="Cannot delete the account you are signed in with")

    org_id = user.get("org_id")
    store = session_auth._load_users()
    store["users"] = [row for row in store.get("users", []) if row.get("id") != user_id]
    sessions = session_auth._load_sessions()
    for token, row in list((sessions.get("sessions") or {}).items()):
        if row.get("user_id") == user_id:
            sessions["sessions"].pop(token, None)
    session_auth._save_users()
    session_auth._save_sessions()
    session_auth.reload_users_cache()
    if org_id:
        _sync_seats(str(org_id))
    return {"deleted": user_id, "email": user.get("email"), "org_id": org_id}


def delete_org(org_id: str) -> Dict[str, Any]:
    """Remove an empty organisation. Standing desks and occupied seats stay."""
    data = get_data()
    orgs = data.setdefault("orgs", {})
    row = orgs.get(org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Organisation not found")
    holders = _seat_holders(org_id)
    block = _org_delete_block(org_id, {**row, "members": holders})
    if block:
        status = 409 if holders and org_id not in _BUILTIN_ORG_IDS and not row.get("protected") else 400
        raise HTTPException(status_code=status, detail=block)

    name = row.get("name")
    orgs.pop(org_id, None)
    checks = data.get("pilot_checklists") or {}
    if isinstance(checks, dict):
        checks.pop(org_id, None)
    keys = data.get("api_keys") or []
    if isinstance(keys, list):
        data["api_keys"] = [k for k in keys if str(k.get("org_id") or "") != org_id]
    tokens = session_auth._load_tokens()
    bag = tokens.setdefault("tokens", {})
    for token, trow in list(bag.items()):
        if trow.get("kind") == "org_invite" and trow.get("org_id") == org_id:
            bag.pop(token, None)
    session_auth._save_tokens()
    from app.data.seed import save_data

    save_data()
    return {"deleted": org_id, "name": name}


def _disposable_email(email: Optional[str]) -> bool:
    return str(email or "").strip().lower().endswith("@ocotillo.test")


def _disposable_org(org_id: str, name: str) -> bool:
    oid = str(org_id or "").strip().lower()
    label = str(name or "").strip().lower()
    return oid.startswith("e2e-") or label.startswith("e2e ")


def _keep_user(user: Dict[str, Any]) -> bool:
    """Approved and standing accounts stay. Only synthetic test rows and guests go."""
    if user.get("protected") or user.get("platform_admin_role"):
        return True
    email = str(user.get("email") or "").strip().lower()
    if email.endswith("@citealpha.com"):
        return True
    if _disposable_email(email):
        return False
    if (user.get("kind") or "") == "guest" and not email:
        return False
    return True


def cleanup_test_tenants(*, dry_run: bool = True) -> Dict[str, Any]:
    """Drop end-to-end tenants and anonymous guests. Real desks and approved pilots stay."""
    from app.services import pilot_request as pr_svc

    data = get_data()
    approved_orgs = {
        str(row.get("org_id"))
        for row in pr_svc.list_requests()
        if (row.get("status") or "") == "approved" and row.get("org_id")
    }
    users = session_auth._load_users().setdefault("users", [])
    drop_users = [u for u in users if not _keep_user(u)]
    drop_ids = {u.get("id") for u in drop_users}
    kept = [u for u in users if u.get("id") not in drop_ids]
    kept_orgs = {u.get("org_id") for u in kept if u.get("org_id")}

    drop_org_ids = []
    for oid, row in list((data.get("orgs") or {}).items()):
        if oid in _BUILTIN_ORG_IDS or oid in approved_orgs or oid in kept_orgs:
            continue
        if _disposable_org(str(oid), str((row or {}).get("name") or "")):
            drop_org_ids.append(str(oid))

    report = {
        "dry_run": dry_run,
        "users_removed": sorted(str(u.get("email") or u.get("id")) for u in drop_users),
        "orgs_removed": sorted(drop_org_ids),
        "users_kept": len(kept),
        "orgs_kept": len(data.get("orgs") or {}) - len(drop_org_ids),
    }
    if dry_run:
        return report

    session_auth._load_users()["users"] = kept
    sessions = session_auth._load_sessions()
    for token, row in list((sessions.get("sessions") or {}).items()):
        if row.get("user_id") in drop_ids:
            sessions["sessions"].pop(token, None)
    session_auth._save_users()
    session_auth._save_sessions()
    session_auth.reload_users_cache()

    orgs = data.setdefault("orgs", {})
    checks = data.setdefault("pilot_checklists", {})
    for oid in drop_org_ids:
        orgs.pop(oid, None)
        checks.pop(oid, None)
    keys = data.get("api_keys") or []
    if isinstance(keys, list):
        data["api_keys"] = [k for k in keys if str(k.get("org_id") or "") not in set(drop_org_ids)]
    from app.data.seed import save_data

    save_data()
    return report


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_days(created_at: Optional[str]) -> Optional[int]:
    if not created_at:
        return None
    try:
        when = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - when).days)


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


def portal_board(actor: Dict[str, Any]) -> Dict[str, Any]:
    """Work waiting on an operator. Each row is omitted when the role cannot open it."""
    perms = set(actor.get("permissions") or [])
    rows: List[Dict[str, Any]] = []
    if "pilot.manage" in perms:
        from app.services import pilot_request as pr_svc

        waiting = sum(1 for row in pr_svc.list_requests() if row.get("status") == "pending")
        rows.append(
            {"id": "pilots", "label": "Pilot requests waiting", "count": waiting, "section": "pilot-requests"}
        )
    if "feedback.read" in perms:
        open_feedback = sum(1 for row in feedback_svc.list_feedback() if row.get("status") == "open")
        rows.append({"id": "feedback", "label": "Feedback still open", "count": open_feedback, "section": "feedback"})
    if "audit.read" in perms:
        from app.services import labeling_queue, repository
        from app.services import commitment_store
        from app.services.source_verify import load_report

        extracts = repository.list_pending_extracts()
        labeling = [
            row
            for row in labeling_queue.list_queue()
            if row.get("status") in ("queued", "in_progress")
        ]
        unreviewed = [
            row
            for row in commitment_store.list_commitments(include_unreviewed=True)
            if row.get("review_status") == "unreviewed"
        ]
        report = load_report()
        rows.append(
            {
                "id": "extracts",
                "label": "Extracts waiting",
                "count": len(extracts),
                "section": "labeling",
            }
        )
        rows.append(
            {
                "id": "labeling",
                "label": "Labeling items",
                "count": len(labeling),
                "section": "labeling",
            }
        )
        rows.append(
            {
                "id": "commitments",
                "label": "Commitments unreviewed",
                "count": len(unreviewed),
                "section": "commitments",
            }
        )
        rows.append(
            {
                "id": "source_checks",
                "label": "Source checks failed",
                "count": int(report.get("failed") or 0),
                "section": "labeling",
            }
        )
    if "system.ops" in perms:
        from app.services.india_coverage import coverage_progress as india_progress
        from app.services.us_coverage import coverage_progress as us_progress

        india = india_progress()
        us = us_progress()
        india_roll = india.get("roll") or {}
        us_roll = us.get("roll") or {}
        running = bool(india_roll.get("running") or us_roll.get("running"))
        rows.append(
            {
                "id": "coverage",
                "label": "Coverage roll",
                "count": int(india.get("searched_today") or 0),
                "running": running,
                "section": "system",
            }
        )
    return {"as_of": _now(), "rows": rows}


def labeling_queue_view() -> Dict[str, Any]:
    """Open labeling rows across desks, plus source-check failures. No accept action."""
    from app.services import labeling_queue, repository
    from app.services.source_verify import load_report

    items = []
    for row in labeling_queue.list_queue():
        if row.get("status") not in ("queued", "in_progress"):
            continue
        items.append(
            {
                "id": row.get("id"),
                "company_id": row.get("company_id"),
                "company_name": row.get("company_name"),
                "org_id": row.get("org_id"),
                "kind": row.get("kind"),
                "status": row.get("status"),
                "priority": row.get("priority"),
                "created_at": row.get("created_at"),
                "age_days": _age_days(row.get("created_at")),
            }
        )
    extracts = []
    for batch in repository.list_pending_extracts():
        extracts.append(
            {
                "id": batch.get("id"),
                "company_id": batch.get("company_id"),
                "status": batch.get("status") or "pending",
                "statements": len(batch.get("statements") or []),
            }
        )
    report = load_report()
    failures = [
        {
            "company_id": row.get("company_id"),
            "period": row.get("period"),
            "metric": row.get("metric"),
            "kind": row.get("kind"),
        }
        for row in (report.get("failures") or [])[:200]
        if isinstance(row, dict)
    ]
    return {
        "as_of": _now(),
        "items": items,
        "extracts": extracts,
        "source_checks": {
            "as_of": report.get("as_of"),
            "checked": int(report.get("checked") or 0),
            "verified": int(report.get("verified") or 0),
            "failed": int(report.get("failed") or 0),
            "fetch_failed": int(report.get("fetch_failed") or 0),
            "note": report.get("note") or "",
            "failures": failures,
        },
        "note": "Accept or reject a row in the Analyst Workbench. This portal does not accept a label.",
    }


def unreviewed_commitments() -> Dict[str, Any]:
    from app.services import commitment_store

    items = []
    for row in commitment_store.list_commitments(include_unreviewed=True):
        if row.get("review_status") != "unreviewed":
            continue
        quote = str(row.get("quote") or "")
        items.append(
            {
                "id": row.get("id"),
                "company_id": row.get("company_id"),
                "type": row.get("type"),
                "subject": row.get("subject"),
                "due_period": row.get("due_period"),
                "proposed_at": row.get("proposed_at"),
                "quote": quote[:240],
            }
        )
    return {
        "as_of": _now(),
        "items": items,
        "note": "A reviewer accepts these in CiteAlpha Analyst. This portal does not change a commitment.",
    }


def _coverage_brief(progress: Dict[str, Any]) -> Dict[str, Any]:
    roll = progress.get("roll") or {}
    brief = {
        "as_of": progress.get("as_of"),
        "running": bool(roll.get("running")),
        "cohort_size": progress.get("cohort_size"),
        "searched_today": progress.get("searched_today"),
        "finished_at": roll.get("finished_at"),
    }
    budgets = progress.get("budgets_today")
    if isinstance(budgets, dict):
        brief["budgets_today"] = budgets
    return brief


def system_status() -> Dict[str, Any]:
    from app.services import guidance_review
    from app.services.agent import monitors as monitor_svc
    from app.services.feature_flags import operator_flags
    from app.services.india_coverage import coverage_progress as india_progress
    from app.services.source_verify import load_report
    from app.services.us_coverage import coverage_progress as us_progress

    report = load_report()
    return {
        "as_of": _now(),
        "guidance_review": guidance_review.last_stamp(),
        "monitors": monitor_svc.status(),
        "india_coverage": _coverage_brief(india_progress()),
        "us_coverage": _coverage_brief(us_progress()),
        "source_verification": {
            "as_of": report.get("as_of"),
            "checked": int(report.get("checked") or 0),
            "verified": int(report.get("verified") or 0),
            "failed": int(report.get("failed") or 0),
            "fetch_failed": int(report.get("fetch_failed") or 0),
            "note": report.get("note") or "",
        },
        "flags": operator_flags(),
        "note": "Flags are shown here. Changing one is an environment change. Demo reset stays off this page.",
    }


def create_msa(body: Dict[str, Any]) -> Dict[str, Any]:
    from app.services import billing

    org_id = str(body.get("org_id") or "").strip()
    if not org_id or org_id not in (get_data().get("orgs") or {}):
        raise HTTPException(status_code=404, detail="Organisation not found")
    seats = body.get("seats", 1)
    try:
        seats_n = int(seats)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="seats must be a number") from None
    amount = body.get("amount_inr")
    amount_n: Optional[float] = None
    if amount is not None and amount != "":
        try:
            amount_n = float(amount)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="amount_inr must be a number") from None
    invoice = billing.create_msa_invoice(
        org_id=org_id,
        plan=str(body.get("plan") or "desk"),
        seats=seats_n,
        amount_inr=amount_n,
        po_number=(str(body["po_number"]).strip() if body.get("po_number") else None),
        coverage=body.get("coverage"),
    )
    signer = str(body.get("signer_email") or "").strip()
    if signer:
        invoice = billing.sign_msa(invoice["id"], signer_email=signer, org_id=org_id)
    return invoice


_REPORTS = (
    {"id": "index", "label": "Index health", "permission": "audit.read"},
    {"id": "coverage", "label": "Coverage", "permission": "audit.read"},
    {"id": "sla", "label": "Filing to score", "permission": "audit.read"},
    {"id": "usage", "label": "Seat and agent use", "permission": "billing.read"},
    {"id": "trust", "label": "Trust", "permission": "legal.read"},
    {"id": "audit-events", "label": "Auth and ops events", "permission": "audit.read"},
)


def report_catalog(actor: Dict[str, Any]) -> Dict[str, Any]:
    perms = set(actor.get("permissions") or [])
    return {"reports": [row for row in _REPORTS if row["permission"] in perms]}


def _report_index() -> Dict[str, Any]:
    from app.data.gci_score_cache import cache_path, load_cache
    from app.services.score_policy import is_pending_guidance_cite

    cache = load_cache()
    scores = cache.get("scores") or {}
    published = [row for row in scores.values() if isinstance(row, dict) and row.get("gci_score") is not None]
    tiers: Dict[str, int] = {}
    for row in published:
        tier = str(row.get("confidence_tier") or "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
    pending = 0
    for rows in (get_data().get("outcomes") or {}).values():
        for outcome in rows or []:
            if is_pending_guidance_cite(outcome):
                pending += 1
    as_of = None
    path = cache_path()
    if path.exists():
        as_of = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": "index",
        "as_of": as_of,
        "published_companies": len(published),
        "tiers": tiers,
        "pending_guidance_cite": pending,
        "note": "Counts from the published score cache. No score was recalculated.",
    }


def _report_coverage() -> Dict[str, Any]:
    from app.services.coverage import COVERAGE_STATUSES, load_coverage

    companies = (load_coverage().get("companies") or {})
    india: Dict[str, int] = {status: 0 for status in sorted(COVERAGE_STATUSES)}
    us: Dict[str, int] = {status: 0 for status in sorted(COVERAGE_STATUSES)}
    dates: List[str] = []
    for company_id, row in companies.items():
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "listed_only")
        bucket = us if str(company_id).startswith("us_") else india
        bucket[status] = bucket.get(status, 0) + 1
        if row.get("as_of"):
            dates.append(str(row["as_of"]))
    return {
        "id": "coverage",
        "as_of": max(dates) if dates else None,
        "india": india,
        "us": us,
        "note": "Counts from the coverage file. No exchange was contacted.",
    }


def _report_sla() -> Dict[str, Any]:
    from app.services.score_sla import sla_summary

    summary = sla_summary()
    if int(summary.get("scored_rows") or 0) == 0 and int(summary.get("pipeline_events") or 0) == 0:
        empty = "no filings in the window"
    elif int((summary.get("live") or {}).get("n") or 0) == 0:
        empty = str((summary.get("live") or {}).get("note") or "no filings in the window")
    else:
        empty = None
    summary["id"] = "sla"
    summary["as_of"] = _now()
    summary["empty_note"] = empty
    return summary


def _report_usage() -> Dict[str, Any]:
    from app.services.agent import monitors as monitor_svc
    from app.services.agent.run_store import run_counts

    monitors_by_org = monitor_svc.status().get("by_org") or {}
    runs = run_counts(since_days=7)
    orgs = []
    for org in list_orgs():
        oid = str(org.get("id") or "")
        orgs.append(
            {
                "org_id": oid,
                "name": org.get("name"),
                "plan": org.get("plan"),
                "seats": org.get("seats"),
                "seats_used": org.get("seats_used"),
                "monitors": int(monitors_by_org.get(oid) or 0),
                "skill_runs_7d": int(runs.get(oid) or 0),
            }
        )
    return {"id": "usage", "as_of": _now(), "orgs": orgs}


def _report_trust() -> Dict[str, Any]:
    from app.services import legal_attest
    from app.services.rbac import sso_status

    snap = legal_attest.snapshot()
    return {
        "id": "trust",
        "as_of": _now(),
        "counsel_status": snap.get("counsel_status"),
        "sso": sso_status(),
        "attestations": snap.get("attestations") or snap.get("records") or [],
        "snapshot": snap,
    }


def _report_audit_events() -> Dict[str, Any]:
    from app.data import audit_log

    events = []
    for row in reversed(audit_log.list_audit(limit=200)):
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
    return {"id": "audit-events", "as_of": _now(), "events": events}


def portal_report(actor: Dict[str, Any], report_id: str) -> Dict[str, Any]:
    spec = next((row for row in _REPORTS if row["id"] == report_id), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown report")
    if not has_permission(actor, spec["permission"]):
        raise HTTPException(
            status_code=403,
            detail=f"Platform role {actor.get('platform_admin_role')} lacks {spec['permission']}",
        )
    builders = {
        "index": _report_index,
        "coverage": _report_coverage,
        "sla": _report_sla,
        "usage": _report_usage,
        "trust": _report_trust,
        "audit-events": _report_audit_events,
    }
    return builders[report_id]()


def audit_events_csv(report: Dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["ts", "action", "org", "actor", "role", "detail"])
    writer.writeheader()
    for row in report.get("events") or []:
        writer.writerow(
            {
                "ts": row.get("ts") or "",
                "action": row.get("action") or "",
                "org": row.get("org") or "",
                "actor": row.get("actor") or "",
                "role": row.get("role") or "",
                "detail": row.get("detail") if isinstance(row.get("detail"), str) else str(row.get("detail") or ""),
            }
        )
    return buffer.getvalue()
