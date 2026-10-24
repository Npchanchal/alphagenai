"""Org-scoped CiteAlpha Analyst Projects: a coverage list, explicit memory and uploads.

Memory is what the analyst asked the agent to keep in mind ("focus on Dahej plant
ramp-up"). It is shown in full, editable and deletable, and is never cited as a
source: Skills cite filings and uploads only.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_projects.json"
_LOCK = threading.Lock()
MAX_PROJECTS_PER_ORG = 50
MAX_COMPANIES = 30
MAX_MEMORY = 100
MAX_MEMORY_CHARS = 500


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_projects.json" if env else _PACKAGED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"projects": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _find(data: Dict[str, Any], org_id: str, project_id: str) -> Dict[str, Any]:
    for p in data["projects"]:
        if p["org_id"] == org_id and p["project_id"] == project_id:
            return p
    raise KeyError(project_id)


def list_projects(org_id: str) -> List[Dict[str, Any]]:
    return [p for p in _load()["projects"] if p["org_id"] == org_id]


def get_project(org_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    try:
        return _find(_load(), org_id, project_id)
    except KeyError:
        return None


def _clean_companies(company_ids: List[str]) -> List[str]:
    out: List[str] = []
    for c in company_ids:
        c = str(c).strip()
        if c and c not in out:
            out.append(c)
    if len(out) > MAX_COMPANIES:
        raise ValueError(f"At most {MAX_COMPANIES} companies per Project")
    return out


def create_project(*, org_id: str, created_by: str, name: str, company_ids: List[str]) -> Dict[str, Any]:
    name = (name or "").strip()[:120]
    if not name:
        raise ValueError("Project name required")
    with _LOCK:
        data = _load()
        if sum(1 for p in data["projects"] if p["org_id"] == org_id) >= MAX_PROJECTS_PER_ORG:
            raise ValueError(f"Project limit reached ({MAX_PROJECTS_PER_ORG} per organisation)")
        proj = {
            "project_id": "prj_" + uuid.uuid4().hex[:12],
            "org_id": org_id,
            "name": name,
            "company_ids": _clean_companies(company_ids),
            "memory": [],
            "created_by": created_by,
            "created_at": _now(),
            "updated_at": _now(),
            "models": [],
        }
        data["projects"].append(proj)
        _save(data)
        return proj


def update_project(org_id: str, project_id: str, *, name: Optional[str] = None,
                   company_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        proj = _find(data, org_id, project_id)
        if name is not None:
            if not name.strip():
                raise ValueError("Project name required")
            proj["name"] = name.strip()[:120]
        if company_ids is not None:
            proj["company_ids"] = _clean_companies(company_ids)
        proj["updated_at"] = _now()
        _save(data)
        return proj


def delete_project(org_id: str, project_id: str) -> bool:
    from app.services.agent import uploads

    with _LOCK:
        data = _load()
        before = len(data["projects"])
        data["projects"] = [p for p in data["projects"]
                            if not (p["org_id"] == org_id and p["project_id"] == project_id)]
        if len(data["projects"]) == before:
            return False
        _save(data)
    uploads.delete_project_uploads(org_id, project_id)
    return True


def add_memory(org_id: str, project_id: str, *, text: str, created_by: str) -> Dict[str, Any]:
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("Memory text required")
    if len(text) > MAX_MEMORY_CHARS:
        raise ValueError(f"Keep each memory under {MAX_MEMORY_CHARS} characters")
    with _LOCK:
        data = _load()
        proj = _find(data, org_id, project_id)
        if len(proj["memory"]) >= MAX_MEMORY:
            raise ValueError(f"Memory limit reached ({MAX_MEMORY} items)")
        item = {"id": "mem_" + uuid.uuid4().hex[:10], "text": text, "created_by": created_by, "created_at": _now()}
        proj["memory"].append(item)
        proj["updated_at"] = _now()
        _save(data)
        return item


def delete_memory(org_id: str, project_id: str, memory_id: str) -> bool:
    with _LOCK:
        data = _load()
        proj = _find(data, org_id, project_id)
        before = len(proj["memory"])
        proj["memory"] = [m for m in proj["memory"] if m["id"] != memory_id]
        if len(proj["memory"]) == before:
            return False
        proj["updated_at"] = _now()
        _save(data)
        return True


def add_model(
    org_id: str,
    project_id: str,
    *,
    name: str,
    figure: object,
    unit: str,
    as_of: str,
    assumptions: str,
    sources: str,
    not_found: str,
    company_id: str,
    created_by: str,
) -> Dict[str, Any]:
    """The analyst's own figure. Stored on the project. Never written into a GCI."""
    name = (name or "").strip()[:120]
    unit = (unit or "").strip()[:40]
    assumptions = " ".join((assumptions or "").split())[:2000]
    sources = " ".join((sources or "").split())[:2000]
    not_found = " ".join((not_found or "").split())[:500]
    company_id = (company_id or "").strip()
    if not name or not unit or not assumptions or not sources or not company_id:
        raise ValueError("A model needs a name, unit, assumptions, sources, and a company")
    if not not_found:
        raise ValueError("Say what the model did not find, or write that nothing was missing")
    try:
        datetime.strptime(str(as_of or "").strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError("as_of must be YYYY-MM-DD")
    try:
        number = float(figure)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError("The figure must be a number you enter")
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("The figure must be a finite number")
    with _LOCK:
        data = _load()
        proj = _find(data, org_id, project_id)
        models = list(proj.get("models") or [])
        if len(models) >= 40:
            raise ValueError("Model limit reached (40 per project)")
        item = {
            "model_id": "mdl_" + uuid.uuid4().hex[:10],
            "name": name,
            "company_id": company_id,
            "figure": round(number, 4),
            "unit": unit,
            "as_of": str(as_of).strip(),
            "assumptions": assumptions,
            "sources": sources,
            "not_found": not_found,
            "created_by": created_by,
            "created_at": _now(),
            "statement": "This figure belongs to the analyst who entered it. It is not a published GCI.",
        }
        models.append(item)
        proj["models"] = models
        proj["updated_at"] = _now()
        _save(data)
        return item
