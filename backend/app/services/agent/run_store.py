"""Org-scoped store of CiteAlpha Analyst runs (JSON; Postgres with the other stores later)."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "agent_runs.json"
_LOCK = threading.Lock()
MAX_RUNS_PER_ORG = 200


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "agent_runs.json" if env else _PACKAGED


def _load() -> Dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"runs": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def save_run(org_id: str, actor: str, output: Dict[str, Any]) -> None:
    with _LOCK:
        data = _load()
        runs = data.setdefault("runs", [])
        runs.append({"org_id": org_id, "actor": actor, "output": output})
        mine = [r for r in runs if r["org_id"] == org_id]
        if len(mine) > MAX_RUNS_PER_ORG:
            drop = {id(r) for r in mine[: len(mine) - MAX_RUNS_PER_ORG]}
            data["runs"] = [r for r in runs if id(r) not in drop]
        _save(data)


def list_runs(
    org_id: str, *, company_id: Optional[str] = None, limit: int = 50, triggered_only: bool = False
) -> List[Dict[str, Any]]:
    rows = []
    for r in reversed(_load().get("runs", [])):
        if r.get("org_id") != org_id:
            continue
        o = r["output"]
        if company_id and o.get("company_id") != company_id:
            continue
        trigger = o.get("trigger") or None
        if triggered_only and not trigger:
            continue
        rows.append(
            {
                "run_id": o.get("run_id"),
                "skill_id": o.get("skill", {}).get("id"),
                "skill_title": o.get("skill", {}).get("title"),
                "company_id": o.get("company_id"),
                "company_name": o.get("company_name"),
                "generated_at": o.get("generated_at"),
                "claims_kept": o.get("verifier", {}).get("kept"),
                "claims_removed": o.get("verifier", {}).get("removed"),
                "actor": r.get("actor"),
                "monitor_id": o.get("monitor_id"),
                "trigger": {k: trigger.get(k) for k in ("doc_id", "title", "date", "doc_type")} if trigger else None,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def run_counts(*, since_days: int = 7) -> Dict[str, int]:
    """Skill runs per org in the window. Counts only — no output text."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    counts: Dict[str, int] = {}
    for row in _load().get("runs", []):
        generated = str((row.get("output") or {}).get("generated_at") or "")
        try:
            when = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when < cutoff:
            continue
        oid = str(row.get("org_id") or "")
        if oid:
            counts[oid] = counts.get(oid, 0) + 1
    return counts


def latest_skill_notes(
    org_id: str,
    company_id: str,
    skill_ids: tuple,
) -> List[Dict[str, Any]]:
    """Latest cited claims from each named skill. A claim without a source quote is left out."""
    found: Dict[str, Dict[str, Any]] = {}
    wanted = set(skill_ids)
    for row in reversed(_load().get("runs", [])):
        if row.get("org_id") != org_id:
            continue
        output = row.get("output") or {}
        if output.get("company_id") != company_id:
            continue
        skill = output.get("skill") or {}
        skill_id = skill.get("id")
        if skill_id not in wanted or skill_id in found:
            continue
        citations = {item.get("n"): item for item in output.get("citations") or []}
        claims = []
        for section in output.get("sections") or []:
            for claim in section.get("claims") or []:
                cites = claim.get("cites") or []
                source = citations.get(cites[0]) if cites else None
                quote = str((source or {}).get("quote") or "").strip()
                url = str((source or {}).get("source_url") or "").strip()
                if not quote or not url.startswith("http"):
                    continue
                claims.append(
                    {
                        "text": claim.get("text"),
                        "quote": quote,
                        "source_url": url,
                        "as_of": (source or {}).get("date") or output.get("as_of"),
                    }
                )
                if len(claims) >= 8:
                    break
            if len(claims) >= 8:
                break
        found[skill_id] = {
            "skill_id": skill_id,
            "title": skill.get("title") or skill_id,
            "generated_at": output.get("generated_at"),
            "claims": claims,
        }
        if len(found) == len(wanted):
            break
    return [found[skill_id] for skill_id in skill_ids if skill_id in found]


def get_run(org_id: str, run_id: str) -> Optional[Dict[str, Any]]:
    for r in _load().get("runs", []):
        if r.get("org_id") == org_id and r["output"].get("run_id") == run_id:
            return r["output"]
    return None
