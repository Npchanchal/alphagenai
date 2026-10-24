"""Org plan entitlements + seat metering (multi-tenant B2B + retail B2C)."""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.data.seed import get_data, save_data
from app.services.legal import LEGAL_ENTITY

# Named seats by commercial plan (Package / PRICING.md)
PLAN_SEATS: Dict[str, int] = {
    "pilot": 5,
    "desk": 25,
    "enterprise": 100,
    "onestop": 40,
    "one-stop": 40,
    "one_stop": 40,
    "retail": 1,
}

PLAN_FEATURES: Dict[str, set] = {
    "guest": {"tracker"},
    "pilot": {
        "tracker",
        "analyst_agent",
        "desk",
        "desk_write",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "feedback",
        "ic_export",
        "wordmap",
        "analytics_experimental",
    },
    "desk": {
        "tracker",
        "analyst_agent",
        "desk",
        "desk_write",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "alerts",
        "vernacular",
        "import",
        "ic_export",
        "feedback",
        "labeling",
        "wordmap",
        "analytics_experimental",
        "holdings",
        "ninja",
    },
    "enterprise": {
        "tracker",
        "analyst_agent",
        "desk",
        "desk_write",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "alerts",
        "vernacular",
        "import",
        "em_export",
        "sso",
        "ic_export",
        "feedback",
        "labeling",
        "wordmap",
        "badge",
        "analytics_experimental",
        "holdings",
        "ninja",
    },
    "onestop": {
        "tracker",
        "analyst_agent",
        "desk",
        "desk_write",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "alerts",
        "vernacular",
        "import",
        "em_export",
        "sso",
        "wordmap",
        "badge",
        "labeling",
        "labeling_priority",
        "ic_export",
        "feedback",
        "analytics_experimental",
        "holdings",
        "ninja",
    },
    "retail": {"tracker", "research", "read_api"},
    "one-stop": set(),  # alias filled below
    "one_stop": set(),
}
PLAN_FEATURES["one-stop"] = PLAN_FEATURES["onestop"]
PLAN_FEATURES["one_stop"] = PLAN_FEATURES["onestop"]

ALL_FEATURES: set = set().union(*PLAN_FEATURES.values())


def normalize_plan(plan: Optional[str]) -> str:
    p = (plan or "pilot").strip().lower().replace(" ", "")
    if p in ("one-stop", "one_stop", "onestopplatform"):
        return "onestop"
    if p in ("b2c", "individual", "personal"):
        return "retail"
    if p in PLAN_SEATS:
        return p
    return "pilot"


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "org").lower()).strip("-") or "org"
    return base[:40]


def seat_limit_for(plan: Optional[str], explicit_seats: Optional[int] = None) -> int:
    if explicit_seats is not None and explicit_seats > 0:
        return int(explicit_seats)
    return PLAN_SEATS.get(normalize_plan(plan), 5)


def org_snapshot(org_id: str) -> Dict[str, Any]:
    orgs = get_data().get("orgs", {})
    if org_id not in orgs:
        raise HTTPException(status_code=404, detail="Org not found")
    row = dict(orgs[org_id])
    plan = normalize_plan(row.get("plan"))
    seats = seat_limit_for(plan, row.get("seats"))
    used = int(row.get("seats_used") or 0)
    features = sorted(PLAN_FEATURES.get(plan, PLAN_FEATURES["pilot"]))
    from app.services.pilot_checklist import holdings_feature_open

    if holdings_feature_open(org_id, plan):
        features = sorted(set(features) | {"holdings", "ninja"})
    else:
        features = [f for f in features if f not in ("holdings", "ninja")]
    if row.get("labeling_granted") or row.get("design_partner"):
        extra = set(features)
        extra.add("feedback")
        if row.get("labeling_granted"):
            extra.add("labeling")
        features = sorted(extra)
    from app.services.pilot_checklist import pilot_evaluation_ended

    if pilot_evaluation_ended(org_id):
        features = ["tracker"]
    return {
        "id": org_id,
        **row,
        "plan": plan,
        "seats": seats,
        "seats_used": used,
        "seats_available": max(0, seats - used),
        "features": features,
        "labeling_granted": bool(row.get("labeling_granted")),
        "design_partner": bool(row.get("design_partner") or plan == "pilot"),
        "entitlements": {
            "plan": plan,
            "seat_cap": seats,
            "features": features,
        },
    }


def consume_seat(org_id: str = "demo") -> Dict[str, Any]:
    """Increment seats_used; raise 403 if at capacity."""
    data = get_data()
    orgs = data.setdefault("orgs", {})
    if org_id not in orgs:
        orgs[org_id] = {
            "name": "CiteAlpha Pilot Desk",
            "plan": "pilot",
            "seats": 5,
            "seats_used": 0,
            "csm": "Assigned at convert",
        }
    snap = org_snapshot(org_id)
    if snap["seats_used"] >= snap["seats"]:
        raise HTTPException(
            status_code=403,
            detail=f"Seat limit reached for plan={snap['plan']} ({snap['seats']} seats)",
        )
    orgs[org_id]["seats_used"] = int(orgs[org_id].get("seats_used") or 0) + 1
    orgs[org_id]["seats"] = snap["seats"]
    orgs[org_id]["plan"] = snap["plan"]
    save_data()
    return org_snapshot(org_id)


def plan_allows(org_id: str, feature: str) -> bool:
    snap = org_snapshot(org_id)
    return feature in snap["features"]


def create_org(
    *,
    name: str,
    plan: str = "pilot",
    account_type: str = "b2b",
    owner_email: Optional[str] = None,
    seats: Optional[int] = None,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an isolated tenant org (B2B workspace or retail individual)."""
    data = get_data()
    orgs = data.setdefault("orgs", {})
    plan_n = normalize_plan(plan if account_type != "retail" else "retail")
    if account_type == "retail":
        plan_n = "retail"
    oid = org_id or f"{_slugify(name)}-{uuid.uuid4().hex[:8]}"
    if oid in orgs:
        raise HTTPException(status_code=409, detail="Org id already exists")
    seat_cap = seat_limit_for(plan_n, seats)
    orgs[oid] = {
        "name": (name or oid).strip(),
        "plan": plan_n,
        "account_type": account_type if account_type in ("b2b", "retail") else "b2b",
        "seats": seat_cap,
        "seats_used": 0,
        "csm": "Self-serve" if account_type == "retail" else "Assigned at convert",
        "owner_email": owner_email,
        "legal_entity": LEGAL_ENTITY,
        "api_key_hint": None,
        "design_partner": plan_n == "pilot",
        "labeling_granted": plan_n in ("onestop", "desk", "enterprise"),
    }
    save_data()
    return org_snapshot(oid)


def restore_missing_orgs() -> List[str]:
    """Recreate orgs for registered users whose org record was lost before tenant state was persisted.

    Plan upgrades from before the loss cannot be recovered: B2B orgs come back on pilot, retail on retail.
    """
    from app.services import session_auth

    orgs = get_data().setdefault("orgs", {})
    orphans: Dict[str, List[Dict[str, Any]]] = {}
    for user in session_auth._load_users()["users"]:
        oid = user.get("org_id")
        if oid and user.get("kind") != "guest" and oid not in orgs:
            orphans.setdefault(str(oid), []).append(user)
    for oid, members in orphans.items():
        owner = next((u for u in members if u.get("role") == "owner"), members[0])
        retail = owner.get("account_type") == "retail"
        plan = "retail" if retail else "pilot"
        display = (owner.get("name") or (owner.get("email") or "").split("@")[0] or "Restored").strip()
        orgs[oid] = {
            "name": f"{display} (Retail)" if retail else f"{display} Desk",
            "plan": plan,
            "account_type": "retail" if retail else "b2b",
            "seats": max(seat_limit_for(plan), len(members)),
            "seats_used": len(members),
            "csm": "Self-serve" if retail else "Assigned at convert",
            "owner_email": owner.get("email"),
            "legal_entity": LEGAL_ENTITY,
            "api_key_hint": None,
            "design_partner": plan == "pilot",
            "labeling_granted": False,
            "restored": True,
        }
    if orphans:
        save_data()
    return sorted(orphans)


def ensure_builtin_orgs() -> None:
    """Ensure demo + retail pool orgs exist after seed/reset."""
    data = get_data()
    orgs = data.setdefault("orgs", {})
    changed = False
    if "demo" not in orgs:
        orgs["demo"] = {
            "name": "CiteAlpha Pilot Desk",
            "plan": "pilot",
            "account_type": "b2b",
            "seats": 5,
            "seats_used": 0,
            "csm": "Assigned at convert",
            "legal_entity": LEGAL_ENTITY,
            "api_key_hint": "intellens-demo",
        }
        changed = True
    if "retail" not in orgs:
        orgs["retail"] = {
            "name": "CiteAlpha Retail (B2C)",
            "plan": "retail",
            "account_type": "retail",
            "seats": 10_000,
            "seats_used": 0,
            "csm": "Self-serve retail",
            "legal_entity": LEGAL_ENTITY,
            "api_key_hint": None,
            "note": "Shared retail plan pool; individual users get personal orgs on register.",
        }
        changed = True
    for row in orgs.values():
        if "legal_entity" not in row:
            row["legal_entity"] = LEGAL_ENTITY
            changed = True
        if "account_type" not in row:
            row["account_type"] = "retail" if row.get("plan") == "retail" else "b2b"
            changed = True
    if changed:
        save_data()


def assert_org_access(auth: Dict[str, Any], org_id: str) -> None:
    """A desk key stays on its own organisation. A platform operator may cross desks."""
    if auth.get("platform_admin_role"):
        return
    caller = str(auth.get("org_id") or auth.get("org") or "")
    if caller != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")


def release_seat(org_id: str) -> Dict[str, Any]:
    data = get_data()
    orgs = data.setdefault("orgs", {})
    if org_id not in orgs:
        raise HTTPException(status_code=404, detail="Org not found")
    used = max(0, int(orgs[org_id].get("seats_used") or 0) - 1)
    orgs[org_id]["seats_used"] = used
    save_data()
    return org_snapshot(org_id)


def create_invite(
    *,
    org_id: str,
    email: str,
    invited_by: str,
    role: str = "member",
    subject: Optional[str] = None,
    intro: Optional[str] = None,
    actor_role: str = "owner",
) -> Dict[str, Any]:
    """Create a one-time invite token (does not consume seat until accept)."""
    from app.services import mailer
    from app.services import session_auth

    role = session_auth.seat_role_for_actor(actor_role, role)
    snap = org_snapshot(org_id)
    if snap["seats_available"] < 1:
        raise HTTPException(
            status_code=403,
            detail=f"No seats available ({snap['seats_used']}/{snap['seats']})",
        )
    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    token = session_auth._issue_one_time(
        kind="org_invite",
        email=email,
        extra={"org_id": org_id, "role": role, "invited_by": invited_by},
    )
    link = f"{mailer.public_base_url()}/accept-invite?token={token}"
    mail_subject = subject or f"Join {snap['name']} on CiteAlpha"
    if intro:
        mail_body = f"{intro.strip()}\n\nAccept: {link}\n"
    else:
        mail_body = (
            f"You were invited to {snap['name']} on CiteAlpha "
            f"(Ocotillo Innovation Private Limited).\n\nAccept: {link}\n"
        )
    mail = mailer.send_mail(
        to=email,
        subject=mail_subject,
        body=mail_body,
    )
    out: Dict[str, Any] = {
        "status": "ok",
        "org_id": org_id,
        "email": email,
        "mail_status": mail.get("status"),
    }
    if mailer.auth_dev_tokens_enabled():
        out["dev_token"] = token
        out["dev_link"] = link
    return out


def invite_recorded_owner(*, org_id: str, invited_by: str) -> Dict[str, Any]:
    """Mail the address stored on the org a one-time link to join as desk admin.

    The seat is taken when they accept. An address that already has a login is refused.
    """
    from app.services import session_auth

    snap = org_snapshot(org_id)
    email = str(snap.get("owner_email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="This organisation has no recorded owner email")
    existing = session_auth._find_by_email(email)
    if existing and existing.get("kind") != "guest":
        if str(existing.get("org_id") or "") == org_id:
            raise HTTPException(
                status_code=409,
                detail="Recorded owner already has a login on this desk",
            )
        raise HTTPException(
            status_code=409,
            detail="This email already has a CiteAlpha login on another desk",
        )
    name = str(snap.get("name") or "Your desk").strip() or "Your desk"
    sent = create_invite(
        org_id=org_id,
        email=email,
        invited_by=invited_by,
        role="admin",
        subject=f"{name} on CiteAlpha",
        intro=(
            f"{name} is open on CiteAlpha.\n\n"
            "Set a password to join as desk admin. You can then invite the rest of your desk "
            "from Seat administration. A pilot has five seats.\n\n"
            f"CiteAlpha is a product of {LEGAL_ENTITY}. It reports whether management "
            "delivered the guidance it published. It is not investment advice."
        ),
    )
    record = {
        "email": email,
        "mail_status": sent.get("mail_status") or "error",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "invited_by": invited_by,
        "role": "admin",
    }
    data = get_data()
    row = data.setdefault("orgs", {}).get(org_id)
    if isinstance(row, dict):
        row["owner_invite"] = record
        save_data()
    return {**sent, "role": "admin"}


def create_partner_invite(*, org_id: str, email: str, invited_by: str) -> Dict[str, Any]:
    """Design-partner viewer invite — feedback without Desk write; 60-day expiry."""
    from app.services import mailer
    from app.services import session_auth

    snap = org_snapshot(org_id)
    if snap["seats_available"] < 1:
        raise HTTPException(
            status_code=403,
            detail=f"No seats available ({snap['seats_used']}/{snap['seats']})",
        )
    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    expires = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    token = session_auth._issue_one_time(
        kind="org_invite",
        email=email,
        extra={
            "org_id": org_id,
            "role": "viewer",
            "invited_by": invited_by,
            "partner": True,
            "expires_at": expires,
        },
    )
    link = f"{mailer.public_base_url()}/accept-invite?token={token}"
    mail = mailer.send_mail(
        to=email,
        subject=f"Review {snap['name']} on CiteAlpha (design partner)",
        body=(
            f"You were invited as a design partner (viewer) on {snap['name']}.\n"
            f"You can flag evidence rows; this does not change GCI scores.\n\n"
            f"Accept (expires in 60 days): {link}\n"
        ),
    )
    out: Dict[str, Any] = {
        "status": "ok",
        "org_id": org_id,
        "email": email,
        "role": "viewer",
        "expires_at": expires,
        "mail_status": mail.get("status"),
    }
    if mailer.auth_dev_tokens_enabled():
        out["dev_token"] = token
        out["dev_link"] = link
    return out


def mint_api_key(*, org_id: str, label: str = "desk") -> Dict[str, Any]:
    data = get_data()
    org_snapshot(org_id)
    key = f"il-{org_id[:12]}-{secrets.token_hex(8)}"
    # secrets imported at module level — add import
    row = {"key": key, "org": org_id, "role": "analyst", "label": label}
    data.setdefault("api_keys", []).append(row)
    orgs = data.setdefault("orgs", {})
    if org_id in orgs:
        orgs[org_id]["api_key_hint"] = key[:16] + "…"
    save_data()
    return {"api_key": key, "org_id": org_id, "role": "analyst", "label": label}


def set_org_oidc(
    org_id: str,
    *,
    oidc_issuer: Optional[str] = None,
    oidc_client_id: Optional[str] = None,
    email_domain: Optional[str] = None,
) -> Dict[str, Any]:
    data = get_data()
    orgs = data.setdefault("orgs", {})
    if org_id not in orgs:
        raise HTTPException(status_code=404, detail="Org not found")
    if oidc_issuer is not None:
        orgs[org_id]["oidc_issuer"] = oidc_issuer.strip() or None
    if oidc_client_id is not None:
        orgs[org_id]["oidc_client_id"] = oidc_client_id.strip() or None
    if email_domain is not None:
        orgs[org_id]["email_domain"] = email_domain.strip().lower() or None
    save_data()
    return org_snapshot(org_id)


def resolve_org_for_sso_email(email: str) -> str:
    """Map SSO email domain to a configured B2B org; else demo."""
    ensure_builtin_orgs()
    domain = email.strip().lower().split("@")[-1] if "@" in email else ""
    orgs = get_data().get("orgs", {})
    for oid, row in orgs.items():
        ed = (row.get("email_domain") or "").lower()
        if ed and ed == domain:
            return oid
    return "demo"
