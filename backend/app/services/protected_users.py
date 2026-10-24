"""Standing team accounts that survive deployments.

``ensure_protected_users`` runs on every API start. For each account in
``data/protected_users.json`` it creates the user when missing, and otherwise puts
back its org, role and active status. It never overwrites a password the user has
changed. Org admins cannot revoke these accounts or change their roles
(``session_auth.revoke_org_member`` / ``set_member_role``).

The manifest's ``universe`` (India by default) is applied once per ``version``:
bumping the version resets every team account's market and index on the next
start; a market a user picks afterwards is kept.

An email already registered to someone else outside the manifest is left alone.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger(__name__)

MANIFEST = Path(__file__).resolve().parent.parent / "data" / "protected_users.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def is_protected(user: Dict[str, Any]) -> bool:
    return bool(user.get("protected"))


def _ensure_org(spec: Dict[str, Any], members: int) -> bool:
    from app.data.seed import get_data
    from app.services import orgs as org_svc
    from app.services.legal import LEGAL_ENTITY

    data = get_data()
    all_orgs = data.setdefault("orgs", {})
    oid = spec["id"]
    plan = org_svc.normalize_plan(spec.get("plan"))
    row = all_orgs.get(oid)
    if row is None:
        all_orgs[oid] = {
            "name": spec.get("name") or oid,
            "plan": plan,
            "account_type": spec.get("account_type") or "b2b",
            "seats": max(org_svc.seat_limit_for(plan), members),
            "seats_used": 0,
            "csm": "CiteAlpha team",
            "owner_email": None,
            "legal_entity": LEGAL_ENTITY,
            "api_key_hint": None,
            "design_partner": False,
            "labeling_granted": True,
            "protected": True,
        }
        return True
    changed = False
    for key, want in (("plan", plan), ("labeling_granted", True), ("protected", True)):
        if row.get(key) != want:
            row[key] = want
            changed = True
    if int(row.get("seats") or 0) < members:
        row["seats"] = members
        changed = True
    return changed


def _apply_universe(user: Dict[str, Any], universe: Dict[str, Any]) -> bool:
    version = int(universe.get("version") or 0)
    if not version or int(user.get("protected_universe_version") or 0) >= version:
        return False
    prefs = dict(user.get("preferences") or {})
    prefs.update({k: universe[k] for k in ("default_market", "default_index") if universe.get(k)})
    user["preferences"] = prefs
    user["protected_universe_version"] = version
    return True


def ensure_protected_users() -> Dict[str, Any]:
    from app.data.seed import get_data, save_data
    from app.services import orgs as org_svc
    from app.services import session_auth
    from app.services.legal import PRIVACY_VERSION, TERMS_VERSION

    manifest = load_manifest()
    org = manifest["org"]
    specs: List[Dict[str, Any]] = manifest["users"]
    universe: Dict[str, Any] = manifest.get("universe") or {}
    org_svc.ensure_builtin_orgs()
    org_changed = _ensure_org(org, len(specs))

    session_auth.reload_users_cache()
    store = session_auth._load_users()
    created, repaired, skipped = [], [], []
    for spec in specs:
        email = spec["email"].strip().lower()
        user = session_auth._find_by_email(email)
        if user is None:
            store["users"].append({
                "id": str(uuid.uuid4()),
                "email": email,
                "name": spec.get("name") or email.split("@")[0],
                "kind": "registered",
                "account_type": org.get("account_type") or "b2b",
                "org_id": org["id"],
                "role": spec["role"],
                "email_verified": True,
                "active": True,
                "terms_version": TERMS_VERSION,
                "privacy_version": PRIVACY_VERSION,
                "terms_accepted_at": _now(),
                "password_salt": spec["password_salt"],
                "password_hash": spec["password_hash"],
                "preferences": dict(session_auth.DEFAULT_PREFS),
                "created_at": _now(),
                "protected": True,
            })
            if spec.get("platform_admin_role"):
                store["users"][-1]["platform_admin_role"] = spec["platform_admin_role"]
            _apply_universe(store["users"][-1], universe)
            created.append(email)
            continue
        if not user.get("protected") and user.get("org_id") not in (None, org["id"]):
            skipped.append(email)
            continue
        want = {
            "org_id": org["id"],
            "role": spec["role"],
            "active": True,
            "kind": "registered",
            "email_verified": True,
            "protected": True,
        }
        if spec.get("platform_admin_role"):
            want["platform_admin_role"] = spec["platform_admin_role"]
        diff = {k: v for k, v in want.items() if user.get(k) != v}
        if not user.get("password_hash"):
            diff.update(password_salt=spec["password_salt"], password_hash=spec["password_hash"])
        if diff:
            user.update(diff)
        if _apply_universe(user, universe) or diff:
            repaired.append(email)

    if created or repaired:
        session_auth._save_users()
    members = sum(1 for u in store["users"] if u.get("org_id") == org["id"] and u.get("active") is not False)
    row = get_data()["orgs"][org["id"]]
    if int(row.get("seats_used") or 0) != members:
        row["seats_used"] = members
        org_changed = True
    if org_changed:
        save_data()
    if skipped:
        log.warning("protected_users_skipped emails=%s (registered to another org)", skipped)
    return {"org_id": org["id"], "created": created, "repaired": repaired, "skipped": skipped}
