"""Simple API-key auth for write/pilot endpoints."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from app.data.seed import get_data


def _env_admin_key_row() -> Optional[Dict[str, Any]]:
    """Rotated production admin key — survives redeploy via ECS env / Secrets Manager."""
    key = (os.environ.get("INTELLENS_API_KEY") or "").strip()
    if not key:
        return None
    return {
        "key": key,
        "org": "platform",
        "role": "admin",
        "platform_admin_role": "super",
    }


def lookup_api_key(x_api_key: str) -> Optional[Dict[str, Any]]:
    """Resolve a key row. Once a rotated admin key is configured, seeded platform-admin keys stop working."""
    env_row = _env_admin_key_row()
    if env_row and x_api_key == env_row["key"]:
        return env_row
    if x_api_key.startswith("ca_live_"):
        from app.services.agent.org_keys import lookup

        return lookup(x_api_key)
    for row in get_data().get("api_keys", []):
        if row["key"] == x_api_key:
            if env_row and row.get("platform_admin_role"):
                return None
            return row
    return None


def resolve_api_key(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    row = lookup_api_key(x_api_key)
    if row and row.get("org_key"):
        raise HTTPException(status_code=403, detail="Organisation API keys work on /api/v1/analyst and /api/mcp only")
    if row:
        return row
    raise HTTPException(status_code=403, detail="Invalid API key")


def optional_api_key(x_api_key: Optional[str] = Header(default=None)) -> Optional[Dict[str, Any]]:
    if not x_api_key:
        return None
    row = lookup_api_key(x_api_key)
    if row:
        return row
    raise HTTPException(status_code=403, detail="Invalid API key")
