"""Per-organisation API keys for the CiteAlpha public API and MCP server (A6).

Keys look like ``ca_live_<random>``. Only a SHA-256 hash and a short prefix are
stored; the full key is shown once, at creation. A key acts for its organisation
with a read-and-run role (``analyst`` or ``viewer``), never as an admin.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PREFIX = "ca_live_"
ROLES = ("analyst", "viewer")
MAX_KEYS_PER_ORG = 10

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_org_keys.json"
_LOCK = threading.Lock()


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_org_keys.json" if env else _PACKAGED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    p = _path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"keys": []}


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(p)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _public(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: row.get(k) for k in ("key_id", "label", "role", "prefix", "created_at", "created_by", "last_used_at")}


def list_keys(org_id: str) -> List[Dict[str, Any]]:
    return [_public(r) for r in _load()["keys"] if r["org_id"] == org_id and not r.get("revoked_at")]


def create_key(org_id: str, *, label: str, created_by: str, role: str = "analyst") -> Tuple[Dict[str, Any], str]:
    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")
    label = (label or "").strip()[:80] or "API key"
    plain = PREFIX + secrets.token_urlsafe(24)
    with _LOCK:
        data = _load()
        live = [r for r in data["keys"] if r["org_id"] == org_id and not r.get("revoked_at")]
        if len(live) >= MAX_KEYS_PER_ORG:
            raise OverflowError(f"key limit reached ({MAX_KEYS_PER_ORG} per organisation)")
        row = {"key_id": "key_" + uuid.uuid4().hex[:12], "org_id": org_id, "label": label, "role": role,
               "prefix": plain[: len(PREFIX) + 6], "sha256": _hash(plain), "created_at": _now(),
               "created_by": created_by, "revoked_at": None, "last_used_at": None}
        data["keys"].append(row)
        _save(data)
    return _public(row), plain


def revoke_key(org_id: str, key_id: str) -> bool:
    with _LOCK:
        data = _load()
        for r in data["keys"]:
            if r["org_id"] == org_id and r["key_id"] == key_id and not r.get("revoked_at"):
                r["revoked_at"] = _now()
                _save(data)
                return True
    return False


def lookup(plain: str) -> Optional[Dict[str, Any]]:
    """Key row in the shape ``auth.lookup_api_key`` returns, or None."""
    if not plain or not plain.startswith(PREFIX):
        return None
    digest = _hash(plain)
    data = _load()
    for r in data["keys"]:
        if secrets.compare_digest(r["sha256"], digest) and not r.get("revoked_at"):
            today = _now()[:10]
            if (r.get("last_used_at") or "")[:10] != today:
                with _LOCK:
                    fresh = _load()
                    for f in fresh["keys"]:
                        if f["key_id"] == r["key_id"]:
                            f["last_used_at"] = _now()
                    _save(fresh)
            return {"key": plain, "org": r["org_id"], "role": r["role"], "key_id": r["key_id"], "org_key": True}
    return None
