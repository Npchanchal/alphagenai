"""Skill specs — versioned JSON under ``backend/app/skills/``.

A Skill is a declarative workflow: ordered sections, each rendered by a named
builder over read-only tools, plus queries for the disproof pass. Desks can add
their own spec without code as long as it uses known builders.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

KNOWN_BUILDERS = {
    "delivery_record",
    "open_guidance",
    "commitments_open",
    "commitments_closed",
    "filing_quotes",
    "peers",
    "questions",
    "recent_filings",
    "peer_grid",
    "diligence_claims",
    "diligence_gaps",
    "model_drivers",
    "language_shift",
    "passages",
    "linked_commitments",
    "debate_map",
}


def validate_spec(spec: Dict[str, Any]) -> List[str]:
    errors = [f"missing_{k}" for k in ("id", "version", "title", "sections") if not spec.get(k)]
    for s in spec.get("sections") or []:
        if s.get("builder") not in KNOWN_BUILDERS:
            errors.append(f"unknown_builder:{s.get('builder')}")
        if not s.get("id") or not s.get("title"):
            errors.append("section_missing_id_or_title")
    return errors


@lru_cache(maxsize=1)
def load_skills() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for p in sorted(SKILLS_DIR.glob("*.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        errs = validate_spec(spec)
        if errs:
            raise ValueError(f"{p.name}: {','.join(errs)}")
        out[spec["id"]] = spec
    return out


def get_skill(skill_id: str) -> Dict[str, Any]:
    skills = load_skills()
    if skill_id not in skills:
        raise KeyError(skill_id)
    return skills[skill_id]


def list_skills() -> List[Dict[str, Any]]:
    return [
        {**{k: s.get(k) for k in ("id", "version", "title", "audience", "description", "inputs")},
         "requires_project": bool(s.get("requires_project"))}
        for s in load_skills().values()
    ]
