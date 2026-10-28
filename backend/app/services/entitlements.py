"""Plan × role entitlements — effective access is the intersection, never the union."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from fastapi import Depends, Header, HTTPException

from app.services import orgs
from app.services.session_auth import extract_bearer, resolve_token

# Role may use these features (still intersected with the org plan).
ROLE_FEATURES: Dict[str, Set[str]] = {
    "guest": {"tracker"},
    "member": {"tracker", "research", "read_api", "feedback"},
    "viewer": {"tracker", "research", "read_api", "feedback"},
    "analyst": {
        "tracker",
        "analyst_agent",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "desk",
        "desk_write",
        "alerts",
        "vernacular",
        "import",
        "ic_export",
        "feedback",
        "wordmap",
        "badge",
        "analytics_experimental",
        "holdings",
        "ninja",
    },
    "labeler": {
        "tracker",
        "research",
        "read_api",
        "feedback",
        "labeling",
        "desk",
    },
    "reviewer": {
        "tracker",
        "analyst_agent",
        "research",
        "research_chat",
        "sights_ask",
        "read_api",
        "desk",
        "desk_write",
        "alerts",
        "vernacular",
        "import",
        "ic_export",
        "feedback",
        "labeling",
        "wordmap",
        "badge",
        "analytics_experimental",
        "holdings",
        "ninja",
        "org_audit",
    },
    # Role-only. Not on any plan. Kept after the plan ∩ role cut.
    "pm": {"tracker", "research", "read_api", "feedback", "holdings", "alerts"},
    "data": {"tracker", "research", "read_api", "feedback", "em_export"},
    "oversight": {"tracker", "research", "read_api", "feedback", "org_audit"},
    "ir": {"tracker", "research", "read_api", "feedback", "pack_export"},
    "admin": set(),  # filled below — all plan features
    "owner": set(),
}

# These names are seats, not plan rows. A Pilot admin still audits; a viewer does not.
ROLE_ONLY_FEATURES = frozenset({"org_audit", "pack_export"})

GUEST_FEATURES: Set[str] = {"tracker"}
GUEST_LIMITS: Dict[str, int] = {"companies_viewed": 15, "chat": 0, "searches": 8}

# Paths guests may POST (auth/legal/prefs only).
GUEST_WRITE_ALLOW: tuple[str, ...] = (
    "/api/auth/",
    "/api/legal/",
    "/api/preferences",
    "/api/activity/",
)


def _role_features(role: str) -> Set[str]:
    r = (role or "viewer").strip().lower()
    if r in ("admin", "owner"):
        return set(orgs.ALL_FEATURES) | set(ROLE_ONLY_FEATURES)
    return set(ROLE_FEATURES.get(r, ROLE_FEATURES["viewer"]))


def _effective_features(plan_feats: Set[str], role: str) -> Set[str]:
    """Plan ∩ role, then the two seat-only names the plan does not sell."""
    role_feats = _role_features(role)
    return (set(plan_feats) & role_feats) | (role_feats & set(ROLE_ONLY_FEATURES))


def _with_platform_super(feats: list, actor: Dict[str, Any]) -> list:
    """A platform super operates the product. The desk modules stay open."""
    if str(actor.get("platform_admin_role") or "") != "super":
        return feats
    return sorted(set(feats) | set(orgs.PLAN_FEATURES["desk"]))


def guest_entitlements() -> Dict[str, Any]:
    return {
        "plan": "guest",
        "role": "guest",
        "kind": "guest",
        "org_id": None,
        "features": sorted(GUEST_FEATURES),
        "skus": ["score"],
        "limits": dict(GUEST_LIMITS),
        "labeling_granted": False,
        "design_partner": False,
        "source": "guest",
    }


def resolve_from_user(user: Dict[str, Any]) -> Dict[str, Any]:
    if (user.get("kind") or "") == "guest" or (user.get("role") or "") == "guest":
        out = guest_entitlements()
        out["user_id"] = user.get("id")
        prefs = user.get("preferences") or {}
        out["limits"] = {
            **GUEST_LIMITS,
            "companies_viewed_used": int(prefs.get("dossier_opens") or 0),
            "searches_used": int(prefs.get("reading_searches") or 0),
        }
        return out
    oid = user.get("org_id")
    if not oid:
        return guest_entitlements()
    try:
        snap = orgs.org_snapshot(str(oid))
    except HTTPException:
        return guest_entitlements()
    from app.services.admin_portal import effective_platform_role

    plan_feats = set(snap.get("features") or [])
    role = str(user.get("role") or "viewer")
    platform_role = effective_platform_role(user.get("email"), user.get("platform_admin_role"))
    feats = _with_platform_super(
        sorted(_effective_features(plan_feats, role)),
        {**user, "platform_admin_role": platform_role},
    )
    return {
        "plan": snap.get("plan") or "pilot",
        "role": role,
        "kind": user.get("kind") or "registered",
        "org_id": str(oid),
        "user_id": user.get("id"),
        "email": user.get("email"),
        "features": feats,
        "skus": _skus_for(plan_feats),
        "limits": {},
        "labeling_granted": bool(snap.get("labeling_granted") or "labeling" in plan_feats),
        "design_partner": bool(snap.get("design_partner") or snap.get("plan") == "pilot"),
        "source": "session",
        "account_type": snap.get("account_type") or user.get("account_type"),
        "org": str(oid),
        "key": None,
        "platform_admin_role": platform_role,
    }


def resolve_from_key(key_row: Dict[str, Any]) -> Dict[str, Any]:
    oid = key_row.get("org") or key_row.get("org_id") or "demo"
    try:
        snap = orgs.org_snapshot(str(oid))
    except HTTPException:
        snap = {"plan": "pilot", "features": sorted(orgs.PLAN_FEATURES["pilot"])}
    from app.services.admin_portal import effective_platform_role

    plan_feats = set(snap.get("features") or [])
    role = str(key_row.get("role") or "analyst")
    platform_role = effective_platform_role(
        None, key_row.get("platform_admin_role"), api_key=True
    )
    feats = _with_platform_super(
        sorted(_effective_features(plan_feats, role)),
        {**key_row, "platform_admin_role": platform_role},
    )
    return {
        "plan": snap.get("plan") or "pilot",
        "role": role,
        "kind": "api_key",
        "org_id": str(oid),
        "user_id": None,
        "features": feats,
        "skus": _skus_for(plan_feats),
        "limits": {},
        "labeling_granted": "labeling" in plan_feats,
        "design_partner": bool(snap.get("design_partner") or snap.get("plan") == "pilot"),
        "source": "api_key",
        "key": key_row.get("key"),
        "org": oid,
        "platform_admin_role": platform_role,
    }


def _skus_for(features: Set[str]) -> list[str]:
    skus = ["score"]
    if "research" in features or "research_chat" in features:
        skus.append("cite")
    if "alerts" in features:
        skus.append("radar")
    if "desk" in features:
        skus.append("ledger")
    if "em_export" in features:
        skus.append("data")
    if "holdings" in features:
        skus.append("holdings")
    if "sights_ask" in features or "research" in features:
        skus.append("sights")
    return skus


def has_feature(ent: Dict[str, Any], feature: str) -> bool:
    return feature in set(ent.get("features") or [])


def resolve_actor(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Prefer session (so guest/retail cannot piggyback the demo API key)."""
    user = resolve_token(extract_bearer(authorization))
    if user:
        return resolve_from_user(user)
    if x_api_key:
        from app.services.auth import lookup_api_key

        row = lookup_api_key(x_api_key)
        if row:
            return resolve_from_key(row)
        raise HTTPException(status_code=403, detail="Invalid API key")
    return guest_entitlements()


def require_actor(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    ent = resolve_actor(authorization=authorization, x_api_key=x_api_key)
    if ent.get("source") == "guest" and not x_api_key:
        # unauthenticated — still a guest snapshot; callers that need a key will 401 below
        pass
    if ent.get("source") not in ("session", "api_key", "guest"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return ent


def require_session_or_key(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Session wins over a demo key. Guests are not a desk."""
    ent = resolve_actor(authorization=authorization, x_api_key=x_api_key)
    if ent.get("source") not in ("session", "api_key"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return ent


def _deny_feature(ent: Dict[str, Any], feature: str) -> None:
    if ent.get("plan") == "pilot":
        from app.services.pilot_checklist import pilot_evaluation_ended

        if pilot_evaluation_ended(str(ent.get("org_id") or "")):
            raise HTTPException(
                status_code=403,
                detail="This evaluation has ended. A paid desk keeps this module.",
            )
    raise HTTPException(
        status_code=403,
        detail=f"Plan {ent.get('plan')} / role {ent.get('role')} lacks {feature}",
    )


def _deny_guest(ent: Dict[str, Any]) -> None:
    if ent.get("user_id"):
        raise HTTPException(
            status_code=403,
            detail="Guest sessions are read-only — register for Desk, chat, and labeling",
        )
    raise HTTPException(status_code=401, detail="Authentication required")


def require_feature(feature: str, *, allow_guest: bool = False):
    def _dep(ent: Dict[str, Any] = Depends(resolve_actor)) -> Dict[str, Any]:
        if ent.get("kind") == "guest" and not allow_guest:
            _deny_guest(ent)
        if not has_feature(ent, feature):
            _deny_feature(ent, feature)
        return ent

    return _dep


def require_any_feature(*features: str):
    """Pass when the seat has at least one of these features."""

    def _dep(ent: Dict[str, Any] = Depends(resolve_actor)) -> Dict[str, Any]:
        if ent.get("kind") == "guest":
            _deny_guest(ent)
        if any(has_feature(ent, feature) for feature in features):
            return ent
        _deny_feature(ent, " or ".join(features))
        return ent

    return _dep


def guest_write_blocked(path: str) -> bool:
    p = path or ""
    return not any(p.startswith(a) for a in GUEST_WRITE_ALLOW)
