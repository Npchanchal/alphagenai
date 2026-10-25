"""Lightweight session auth: register / login / guest + preferences.

JSON-backed users + sessions. Passwords hashed with PBKDF2-HMAC-SHA256.
Bearer token returned to the frontend (also accepted via Authorization header).
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException

_USERS_PATH = Path(__file__).resolve().parent.parent / "data" / "users.json"
_SESSIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.json"
_TOKENS_PATH = Path(__file__).resolve().parent.parent / "data" / "auth_tokens.json"

_USERS: Optional[Dict[str, Any]] = None
_SESSIONS: Optional[Dict[str, Any]] = None
_TOKENS: Optional[Dict[str, Any]] = None

DEFAULT_PREFS: Dict[str, Any] = {
    "language": "en",
    "default_market": "IN",
    "default_index": "SENSEX",
    "watchlist": [],
    "show_demo_tape": True,
    "density": "comfortable",
    "saved_queries": [],
    "analytics_consent": None,
    "citations_copied": 0,
    "dossier_opens": 0,
}

ALLOWED_ROLES = frozenset(
    {"viewer", "analyst", "labeler", "reviewer", "admin", "owner", "member", "guest"}
)

_PBKDF2_ITERS = 120_000
MIN_PASSWORD_LEN = 12
SESSION_IDLE_SECONDS = 12 * 3600
SESSION_ABSOLUTE_SECONDS = 30 * 24 * 3600


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _auth_event(action: str, *, actor: str = "anon", role: str = "user", detail: Optional[Dict[str, Any]] = None) -> None:
    try:
        from app.data import audit_log

        audit_log.record(action, actor=actor, role=role, detail=detail or {})
    except Exception:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_users() -> Dict[str, Any]:
    global _USERS
    from app.db.auth_db import apply_schema, list_users, use_db_auth

    if _USERS is None:
        if use_db_auth():
            apply_schema()
            _USERS = {"users": list_users()}
        elif _USERS_PATH.exists():
            _USERS = json.loads(_USERS_PATH.read_text())
        else:
            _USERS = {"users": []}
    return _USERS


def _user_by_id(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    return next((u for u in _load_users().get("users", []) if u.get("id") == user_id), None)


def user_watchlist(user_id: Optional[str]) -> List[str]:
    """Company IDs on an active user's watchlist (empty if the user is gone or inactive)."""
    u = _user_by_id(user_id)
    if not u or u.get("active") is False:
        return []
    return [str(c) for c in ((u.get("preferences") or {}).get("watchlist") or [])]


def org_member_emails(org_id: str, roles: Optional[tuple] = None) -> List[str]:
    out = []
    for u in _load_users().get("users", []):
        if u.get("org_id") != org_id or u.get("active") is False or not u.get("email"):
            continue
        if roles and str(u.get("role") or "").lower() not in roles:
            continue
        out.append(str(u["email"]))
    return sorted(set(out))


def _load_sessions() -> Dict[str, Any]:
    global _SESSIONS
    if _SESSIONS is None:
        if _SESSIONS_PATH.exists():
            _SESSIONS = json.loads(_SESSIONS_PATH.read_text())
        else:
            _SESSIONS = {"sessions": {}}
    return _SESSIONS


def _save_users() -> None:
    from app.db.auth_db import apply_schema, replace_all_users, use_db_auth

    store = _load_users()
    if use_db_auth():
        apply_schema()
        replace_all_users(store["users"])
        return
    _USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _USERS_PATH.write_text(json.dumps(store, indent=2))


def _save_sessions() -> None:
    from app.db.auth_db import clear_sessions, put_session, use_db_auth

    store = _load_sessions()
    if use_db_auth():
        clear_sessions()
        for token, row in store.get("sessions", {}).items():
            put_session(token, row["user_id"], row.get("created_at") or _now())
        return
    _SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SESSIONS_PATH.write_text(json.dumps(store, indent=2))


def _load_tokens() -> Dict[str, Any]:
    global _TOKENS
    if _TOKENS is None:
        if _TOKENS_PATH.exists():
            _TOKENS = json.loads(_TOKENS_PATH.read_text())
        else:
            _TOKENS = {"tokens": {}}
    return _TOKENS


def _save_tokens() -> None:
    from app.db.auth_db import clear_tokens, put_token, use_db_auth

    store = _load_tokens()
    if use_db_auth():
        clear_tokens()
        for token, row in store.get("tokens", {}).items():
            put_token(
                token,
                row["kind"],
                row.get("email") or "",
                {k: v for k, v in row.items() if k not in ("kind", "email", "created_at")},
                row.get("created_at") or _now(),
            )
        return
    _TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKENS_PATH.write_text(json.dumps(store, indent=2))


def reset_auth_store() -> None:
    """Test helper — wipe in-memory + on-disk auth state."""
    global _USERS, _SESSIONS, _TOKENS
    from app.db.auth_db import use_db_auth, wipe_all

    _USERS = None
    _SESSIONS = None
    _TOKENS = None
    for path in (_USERS_PATH, _SESSIONS_PATH, _TOKENS_PATH):
        if path.exists():
            path.unlink()
    if use_db_auth():
        wipe_all()


def reload_users_cache() -> None:
    """Reload users from SQL/JSON after external updates (platform admin roles, etc.)."""
    global _USERS
    _USERS = None
    _load_users()

def _hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    salt_b = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_b, _PBKDF2_ITERS
    )
    return {"salt": salt_b.hex(), "hash": digest.hex(), "iters": str(_PBKDF2_ITERS)}


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    got = _hash_password(password, salt=salt)
    return secrets.compare_digest(got["hash"], expected_hash)


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "id": user["id"],
        "email": user.get("email"),
        "name": user.get("name"),
        "kind": user.get("kind", "registered"),
        "account_type": user.get("account_type", "b2b"),
        "org_id": user.get("org_id"),
        "role": user.get("role", "member"),
        "email_verified": bool(user.get("email_verified")),
        "active": user.get("active", True) is not False,
        "terms_version": user.get("terms_version"),
        "terms_accepted_at": user.get("terms_accepted_at"),
        "privacy_version": user.get("privacy_version"),
        "preferences": {**DEFAULT_PREFS, **(user.get("preferences") or {})},
        "created_at": user.get("created_at"),
        "mfa_enabled": bool(user.get("totp_enabled")),
    }
    from app.services.admin_portal import effective_platform_role

    platform_role = effective_platform_role(user.get("email"), user.get("platform_admin_role"))
    if platform_role:
        out["platform_admin_role"] = platform_role
    from app.services.protected_users import is_protected

    if is_protected(user):
        out["protected"] = True
    return out


def _issue_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    store = _load_sessions()
    store["sessions"][token] = {
        "user_id": user_id,
        "created_at": now,
        "last_seen_at": now,
    }
    _save_sessions()
    return token


def _find_user(user_id: str) -> Optional[Dict[str, Any]]:
    return next((u for u in _load_users()["users"] if u["id"] == user_id), None)


def _find_by_email(email: str) -> Optional[Dict[str, Any]]:
    email_l = email.strip().lower()
    return next(
        (u for u in _load_users()["users"] if (u.get("email") or "").lower() == email_l),
        None,
    )


def register(
    email: str,
    password: str,
    name: str,
    *,
    merge_preferences: Optional[Dict[str, Any]] = None,
    guest_token: Optional[str] = None,
    org_id: Optional[str] = None,
    account_type: str = "b2b",
    org_name: Optional[str] = None,
    accept_terms: bool = False,
    invite_role: Optional[str] = None,
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services.legal import PRIVACY_VERSION, TERMS_VERSION

    if not accept_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Use and Privacy Notice to register",
        )

    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LEN} characters",
        )
    if _find_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered")

    acct = (account_type or "b2b").strip().lower()
    if acct not in ("retail", "b2b"):
        raise HTTPException(status_code=400, detail="account_type must be retail or b2b")
    if acct == "retail":
        from app.services.legal_attest import sebi_retail_status

        if sebi_retail_status() != "counsel_approved":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Individual accounts are not offered. Register a research desk "
                    "(account_type=b2b) or request a pilot seat."
                ),
            )

    org_svc.ensure_builtin_orgs()

    role = "member"
    if org_id:
        # Explicit org (admin/API invite path) — must exist
        org_svc.org_snapshot(org_id)
        resolved_org = org_id
        if acct == "b2b":
            acct = str(org_svc.org_snapshot(org_id).get("account_type") or "b2b")
    elif acct == "b2b":
        label = (org_name or f"{(name or email.split('@')[0]).strip()} Desk").strip()
        if len(label) < 2:
            raise HTTPException(status_code=400, detail="org_name required for B2B accounts")
        created = org_svc.create_org(
            name=label,
            plan="pilot",
            account_type="b2b",
            owner_email=email,
        )
        resolved_org = created["id"]
        role = "owner"
    else:
        # Retail B2C — personal micro-tenant for isolation
        display = (name or email.split("@")[0]).strip() or "Retail"
        created = org_svc.create_org(
            name=f"{display} (Retail)",
            plan="retail",
            account_type="retail",
            owner_email=email,
        )
        resolved_org = created["id"]
        role = "owner"

    org_svc.consume_seat(resolved_org)

    if invite_role:
        mapped = str(invite_role).strip().lower()
        if mapped in ("member", "partner"):
            mapped = "viewer"
        if mapped not in ALLOWED_ROLES or mapped in ("guest", "owner"):
            mapped = "viewer"
        role = mapped
    elif role == "member":
        role = "viewer"

    prefs = dict(DEFAULT_PREFS)
    if guest_token:
        guest_user = resolve_token(guest_token)
        if guest_user and guest_user.get("kind") == "guest":
            prefs.update(guest_user.get("preferences") or {})
    if merge_preferences:
        prefs.update({k: v for k, v in merge_preferences.items() if k in DEFAULT_PREFS})

    hashed = _hash_password(password)
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": (name or email.split("@")[0]).strip(),
        "kind": "registered",
        "account_type": acct,
        "org_id": resolved_org,
        "role": role,
        "email_verified": False,
        "active": True,
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "terms_accepted_at": _now(),
        "password_salt": hashed["salt"],
        "password_hash": hashed["hash"],
        "preferences": prefs,
        "created_at": _now(),
    }
    store = _load_users()
    store["users"].append(user)
    _save_users()

    if guest_token:
        # Drop guest session after merge
        sessions = _load_sessions()
        sessions["sessions"].pop(guest_token, None)
        _save_sessions()

    token = _issue_session(user["id"])
    verify_info = request_email_verification(email)
    out: Dict[str, Any] = {"token": token, "user": _public_user(user)}
    if verify_info.get("dev_token"):
        out["verify_dev_token"] = verify_info["dev_token"]
    out["verification"] = {
        "email_verified": False,
        "mail_status": verify_info.get("mail_status"),
    }
    return out


def login(email: str, password: str, totp_code: Optional[str] = None) -> Dict[str, Any]:
    user = _find_by_email(email)
    if user is None or user.get("kind") == "guest":
        _auth_event("auth_login_fail", actor=email.strip().lower(), detail={"reason": "unknown"})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("active") is False:
        raise HTTPException(status_code=403, detail="Account revoked — contact your org admin")
    if not _verify_password(password, user["password_salt"], user["password_hash"]):
        _auth_event(
            "auth_login_fail",
            actor=user.get("email") or email,
            role=str(user.get("role") or "user"),
            detail={"reason": "bad_password"},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("totp_enabled"):
        from app.services import totp as totp_svc

        if not totp_code:
            raise HTTPException(status_code=403, detail="mfa_required")
        if not totp_svc.verify(str(user.get("totp_secret") or ""), totp_code):
            _auth_event(
                "auth_login_fail",
                actor=user.get("email") or email,
                role=str(user.get("role") or "user"),
                detail={"reason": "bad_totp"},
            )
            raise HTTPException(status_code=401, detail="Invalid authenticator code")
    token = _issue_session(user["id"])
    _auth_event(
        "auth_login",
        actor=user.get("email") or email,
        role=str(user.get("role") or "user"),
        detail={"user_id": user["id"]},
    )
    return {"token": token, "user": _public_user(user)}


def create_guest(*, accept_terms: bool = False) -> Dict[str, Any]:
    from app.services.legal import PRIVACY_VERSION, TERMS_VERSION

    if not accept_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Use and Privacy Notice to continue as guest",
        )
    user = {
        "id": f"guest-{uuid.uuid4().hex[:12]}",
        "email": None,
        "name": "Guest",
        "kind": "guest",
        "account_type": "guest",
        "org_id": None,
        "role": "guest",
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "terms_accepted_at": _now(),
        "preferences": dict(DEFAULT_PREFS),
        "created_at": _now(),
    }
    store = _load_users()
    store["users"].append(user)
    _save_users()
    token = _issue_session(user["id"])
    return {"token": token, "user": _public_user(user)}


def logout(token: Optional[str]) -> Dict[str, str]:
    if token:
        sessions = _load_sessions()
        row = sessions["sessions"].pop(token, None)
        _save_sessions()
        if row:
            user = _find_user(row["user_id"])
            _auth_event(
                "auth_logout",
                actor=(user or {}).get("email") or row["user_id"],
                role=str((user or {}).get("role") or "user"),
                detail={"user_id": row["user_id"]},
            )
    return {"status": "ok"}


def resolve_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    sessions = _load_sessions()
    row = sessions["sessions"].get(token)
    if not row:
        return None
    now = datetime.now(timezone.utc)
    created = _parse_ts(row.get("created_at")) or now
    last = _parse_ts(row.get("last_seen_at")) or created
    if (now - created).total_seconds() > SESSION_ABSOLUTE_SECONDS:
        sessions["sessions"].pop(token, None)
        _save_sessions()
        return None
    if (now - last).total_seconds() > SESSION_IDLE_SECONDS:
        sessions["sessions"].pop(token, None)
        _save_sessions()
        return None
    row["last_seen_at"] = _now()
    _save_sessions()
    user = _find_user(row["user_id"])
    if not user:
        return None
    return _public_user(user)


def get_preferences(token: Optional[str]) -> Dict[str, Any]:
    user = require_session(token)
    return user["preferences"]


def update_preferences(token: Optional[str], patch: Dict[str, Any]) -> Dict[str, Any]:
    public = require_session(token)
    user = _find_user(public["id"])
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    prefs = {**DEFAULT_PREFS, **(user.get("preferences") or {})}
    patch = dict(patch)
    for key in DEFAULT_PREFS:
        if key in patch:
            prefs[key] = patch[key]
    user["preferences"] = prefs
    _save_users()
    return prefs


def require_session(token: Optional[str]) -> Dict[str, Any]:
    user = resolve_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def extract_bearer(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def optional_session(
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    return resolve_token(extract_bearer(authorization))


def _issue_one_time(*, kind: str, email: str, extra: Optional[Dict[str, Any]] = None) -> str:
    token = secrets.token_urlsafe(24)
    store = _load_tokens()
    store["tokens"][token] = {
        "kind": kind,
        "email": email.strip().lower(),
        "created_at": _now(),
        **(extra or {}),
    }
    _save_tokens()
    return token


def _consume_token(token: str, *, kind: str) -> Dict[str, Any]:
    store = _load_tokens()
    row = store["tokens"].pop(token, None)
    _save_tokens()
    if not row or row.get("kind") != kind:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    expires = row.get("expires_at")
    if expires:
        try:
            exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(status_code=400, detail="Invalid or expired token")
        except ValueError:
            pass
    return row


def request_email_verification(email: str) -> Dict[str, Any]:
    from app.services import mailer

    email = email.strip().lower()
    user = _find_by_email(email)
    if user is None or user.get("kind") == "guest":
        return {"status": "ok", "mail_status": "skipped"}
    if user.get("email_verified"):
        return {"status": "ok", "already_verified": True}
    token = _issue_one_time(kind="verify_email", email=email, extra={"user_id": user["id"]})
    link = f"{mailer.public_base_url()}/verify-email?token={token}"
    mail = mailer.send_mail(
        to=email,
        subject="Verify your CiteAlpha email",
        body=(
            f"Verify your email for CiteAlpha (Ocotillo Innovation Private Limited):\n\n"
            f"{link}\n\nIf you did not register, ignore this message."
        ),
    )
    out: Dict[str, Any] = {"status": "ok", "mail_status": mail.get("status")}
    if mailer.auth_dev_tokens_enabled():
        out["dev_token"] = token
        out["dev_link"] = link
    return out


def confirm_email_verification(token: str) -> Dict[str, Any]:
    row = _consume_token(token, kind="verify_email")
    user = _find_user(row.get("user_id") or "") or _find_by_email(row["email"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user["email_verified"] = True
    _save_users()
    return {"status": "ok", "user": _public_user(user)}


def request_password_reset(email: str) -> Dict[str, Any]:
    from app.services import mailer

    email = email.strip().lower()
    user = _find_by_email(email)
    if user is None or user.get("kind") == "guest" or user.get("active") is False:
        return {"status": "ok", "mail_status": "skipped"}
    token = _issue_one_time(kind="reset_password", email=email, extra={"user_id": user["id"]})
    link = f"{mailer.public_base_url()}/reset-password?token={token}"
    mail = mailer.send_mail(
        to=email,
        subject="Reset your CiteAlpha password",
        body=(
            f"Reset your CiteAlpha password:\n\n{link}\n\n"
            "If you did not request this, ignore this message."
        ),
    )
    out: Dict[str, Any] = {"status": "ok", "mail_status": mail.get("status")}
    if mailer.auth_dev_tokens_enabled():
        out["dev_token"] = token
        out["dev_link"] = link
    return out


def confirm_password_reset(token: str, new_password: str) -> Dict[str, Any]:
    if not new_password or len(new_password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LEN} characters",
        )
    row = _consume_token(token, kind="reset_password")
    user = _find_user(row.get("user_id") or "") or _find_by_email(row["email"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    hashed = _hash_password(new_password)
    user["password_salt"] = hashed["salt"]
    user["password_hash"] = hashed["hash"]
    _save_users()
    sessions = _load_sessions()
    drop = [t for t, s in sessions["sessions"].items() if s.get("user_id") == user["id"]]
    for t in drop:
        sessions["sessions"].pop(t, None)
    _save_sessions()
    return {"status": "ok"}


def list_org_members(org_id: str) -> List[Dict[str, Any]]:
    return [
        _public_user(u)
        for u in _load_users()["users"]
        if u.get("org_id") == org_id and u.get("kind") != "guest"
    ]


def _refuse_if_protected(user: Dict[str, Any]) -> None:
    from app.services.protected_users import is_protected

    if is_protected(user):
        raise HTTPException(status_code=400, detail="This account is kept for the CiteAlpha team.")


def revoke_org_member(*, org_id: str, user_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    from app.services import orgs as org_svc

    if actor.get("org_id") != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if actor.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")

    user = _find_user(user_id)
    if user is None or user.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if user.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot revoke org owner")
    if user.get("role") == "admin" and actor.get("role") != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the organisation owner can remove an admin",
        )
    _refuse_if_protected(user)
    if user.get("id") == actor.get("id"):
        raise HTTPException(status_code=400, detail="Cannot revoke yourself")
    user["active"] = False
    _save_users()
    org_svc.release_seat(org_id)
    sessions = _load_sessions()
    drop = [t for t, s in sessions["sessions"].items() if s.get("user_id") == user_id]
    for t in drop:
        sessions["sessions"].pop(t, None)
    _save_sessions()
    return {"status": "ok", "user": _public_user(user)}


def accept_org_invite(
    *,
    invite_token: str,
    password: str,
    name: str = "",
    accept_terms: bool = False,
) -> Dict[str, Any]:
    if not accept_terms:
        raise HTTPException(status_code=400, detail="You must accept Terms to join")
    row = _consume_token(invite_token, kind="org_invite")
    email = row["email"]
    org_id = row["org_id"]
    if _find_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered — log in instead")
    return register(
        email,
        password,
        name or email.split("@")[0],
        org_id=org_id,
        account_type="b2b",
        accept_terms=True,
        invite_role=str(row.get("role") or "viewer"),
    )


_DESK_ASSIGNABLE = frozenset({"viewer", "analyst", "labeler", "reviewer"})


def seat_role_for_actor(actor_role: str, requested: str) -> str:
    """Owner may appoint an admin. An admin may appoint the working seats only."""
    mapped = (requested or "viewer").strip().lower()
    if mapped in ("member", "partner"):
        mapped = "viewer"
    if mapped == "admin" and actor_role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the organisation owner can appoint an admin",
        )
    allowed = set(_DESK_ASSIGNABLE)
    if actor_role == "owner":
        allowed.add("admin")
    if mapped not in allowed:
        raise HTTPException(status_code=400, detail="Invalid role")
    return mapped


def set_member_role(*, org_id: str, user_id: str, role: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    if actor.get("org_id") != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if actor.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    mapped = seat_role_for_actor(str(actor.get("role") or ""), role)
    user = _find_user(user_id)
    if user is None or user.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if user.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner role")
    if user.get("role") == "admin" and actor.get("role") != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the organisation owner can change an admin",
        )
    _refuse_if_protected(user)
    user["role"] = mapped
    _save_users()
    return {"ok": True, "user": _public_user(user)}


def bump_dossier_open(token: Optional[str]) -> Dict[str, Any]:
    """Count dossier opens. Guests hard-cap at 15; registered users are uncapped."""
    from app.services import activity as activity_svc
    from app.services.legal import copyright_meta

    public = resolve_token(token)
    if not public:
        return {"ok": True, "capped": False}
    user = _find_user(public["id"])
    if user is None:
        return {"ok": True, "capped": False}
    prefs = {**DEFAULT_PREFS, **(user.get("preferences") or {})}
    used = int(prefs.get("dossier_opens") or 0) + 1
    prefs["dossier_opens"] = used
    user["preferences"] = prefs
    _save_users()
    oid = user.get("org_id")
    if oid and user.get("kind") != "guest":
        activity_svc.bump(str(oid), "dossier_opens")
    cap = 15
    if user.get("kind") == "guest" and used > cap:
        meta = copyright_meta()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "guest_dossier_cap",
                "message": "Guest preview limit reached — register to keep reading dossiers",
                "cap": cap,
                "retail_marketing_allowed": bool(meta.get("retail_marketing_allowed")),
            },
        )
    return {"ok": True, "capped": False, "dossier_opens": used, "cap": cap}


def record_cite_copy(token: Optional[str], *, company_id: Optional[str] = None) -> Dict[str, Any]:
    """Habit ping — no quote text stored."""
    from app.services import activity as activity_svc

    public = resolve_token(token)
    if not public:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = _find_user(public["id"])
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    prefs = {**DEFAULT_PREFS, **(user.get("preferences") or {})}
    prefs["citations_copied"] = int(prefs.get("citations_copied") or 0) + 1
    user["preferences"] = prefs
    _save_users()
    oid = user.get("org_id")
    if oid and user.get("kind") != "guest":
        activity_svc.bump(str(oid), "cite_copies")
    _ = company_id
    return {"ok": True, "citations_copied": prefs["citations_copied"]}


def bump_guest_dossier(token: Optional[str]) -> Dict[str, Any]:
    return bump_dossier_open(token)


READING_ROOM_CAP = 8
READING_ROOM_COOKIE = "citealpha_reading"
_BROWSER_ID = re.compile(r"^[A-Za-z0-9_-]{20,80}$")


def _reading_allowance(used: int, *, blocked: bool = False) -> Dict[str, Any]:
    used = max(0, min(int(used), READING_ROOM_CAP))
    return {
        "limited": True,
        "blocked": blocked,
        "cap": READING_ROOM_CAP,
        "used": used,
        "remaining": READING_ROOM_CAP - used,
    }


def _reading_user(token: Optional[str], browser_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """The signed-in caller, or the browser record that holds this cookie's count."""
    public = resolve_token(token) if token else None
    if public:
        user = _find_user(public["id"])
        if user is not None:
            return user
    if browser_id and _BROWSER_ID.match(browser_id):
        return _find_user(f"reading-{browser_id}")
    return None


def _ensure_reading_browser(browser_id: str) -> Dict[str, Any]:
    user_id = f"reading-{browser_id}"
    held = _find_user(user_id)
    if held is not None:
        return held
    user = {
        "id": user_id,
        "email": None,
        "name": "Guest",
        "kind": "guest",
        "account_type": "guest",
        "org_id": None,
        "role": "guest",
        "preferences": dict(DEFAULT_PREFS),
        "created_at": _now(),
    }
    store = _load_users()
    store["users"].append(user)
    _save_users()
    return user


def reading_room_status(token: Optional[str], browser_id: Optional[str]) -> Dict[str, Any]:
    """Searches already used. Does not count a new search."""
    user = _reading_user(token, browser_id)
    used = int(((user or {}).get("preferences") or {}).get("reading_searches") or 0)
    return _reading_allowance(used)


def consume_reading_search(
    token: Optional[str], browser_id: Optional[str] = None
) -> tuple[Dict[str, Any], Optional[str]]:
    """Count one reading-room search. Returns the allowance and the browser id to set.

    A signed-in caller is counted on that account. A visitor is counted on an
    HttpOnly cookie, so omitting the query flag or clearing site storage does
    not open a new allowance until the cookie is gone.
    """
    public = resolve_token(token) if token else None
    user = _find_user(public["id"]) if public else None
    cookie_id: Optional[str] = None
    if user is None:
        cookie_id = browser_id if browser_id and _BROWSER_ID.match(browser_id) else secrets.token_urlsafe(24)
        user = _ensure_reading_browser(cookie_id)
    prefs = {**DEFAULT_PREFS, **(user.get("preferences") or {})}
    used = int(prefs.get("reading_searches") or 0)
    if used >= READING_ROOM_CAP:
        return _reading_allowance(used, blocked=True), cookie_id
    used += 1
    prefs["reading_searches"] = used
    user["preferences"] = prefs
    _save_users()
    return _reading_allowance(used), cookie_id


def _require_mfa_role(user: Dict[str, Any]) -> None:
    if user.get("kind") == "guest":
        raise HTTPException(status_code=403, detail="Register to enable two-factor authentication")
    if str(user.get("role") or "") not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Two-factor authentication is for owner and admin")


def mfa_enroll_start(token: Optional[str]) -> Dict[str, Any]:
    from app.services import totp as totp_svc

    public = require_session(token)
    user = _find_user(public["id"])
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    _require_mfa_role(user)
    secret = totp_svc.new_secret()
    user["totp_pending_secret"] = secret
    _save_users()
    email = str(user.get("email") or "desk@citealpha.com")
    _auth_event("auth_mfa_enroll_start", actor=email, role=str(user.get("role") or "user"))
    return {
        "secret": secret,
        "otpauth_uri": totp_svc.otpauth_uri(secret, email),
        "mfa_enabled": bool(user.get("totp_enabled")),
    }


def mfa_enroll_confirm(token: Optional[str], code: str) -> Dict[str, Any]:
    from app.services import totp as totp_svc

    public = require_session(token)
    user = _find_user(public["id"])
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    _require_mfa_role(user)
    secret = str(user.get("totp_pending_secret") or "")
    if not totp_svc.verify(secret, code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    user["totp_secret"] = secret
    user["totp_enabled"] = True
    user.pop("totp_pending_secret", None)
    _save_users()
    _auth_event(
        "auth_mfa_enable",
        actor=str(user.get("email") or user["id"]),
        role=str(user.get("role") or "user"),
    )
    return {"mfa_enabled": True, "user": _public_user(user)}


def mfa_disable(token: Optional[str], code: str) -> Dict[str, Any]:
    from app.services import totp as totp_svc

    public = require_session(token)
    user = _find_user(public["id"])
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired")
    _require_mfa_role(user)
    if not totp_svc.verify(str(user.get("totp_secret") or ""), code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    user["totp_enabled"] = False
    user.pop("totp_secret", None)
    user.pop("totp_pending_secret", None)
    _save_users()
    _auth_event(
        "auth_mfa_disable",
        actor=str(user.get("email") or user["id"]),
        role=str(user.get("role") or "user"),
    )
    return {"mfa_enabled": False, "user": _public_user(user)}
