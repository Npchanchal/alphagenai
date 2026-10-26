"""Commitment Record persistence (JSON; Postgres later with the rest of the stores).

Proposals land ``unreviewed``. Only a reviewer moves a row to ``accepted`` or
changes its state. Public readers see accepted rows only.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.services import commitments as rules

_PACKAGED = Path(__file__).resolve().parents[1] / "data" / "commitments.json"
_LOCK = threading.Lock()


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "commitments.json" if env else _PACKAGED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"commitments": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def commitment_id(company_id: str, source_url: str, quote: str) -> str:
    key = f"{company_id}|{source_url.strip()}|{' '.join(quote.split()).lower()}"
    return "cmt_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def list_commitments(
    company_id: Optional[str] = None,
    *,
    include_unreviewed: bool = False,
) -> List[Dict[str, Any]]:
    rows = _load().get("commitments", [])
    out = []
    for r in rows:
        if company_id and r.get("company_id") != company_id:
            continue
        if r.get("review_status") == "rejected":
            continue
        if not include_unreviewed and r.get("review_status") != "accepted":
            continue
        out.append(r)
    dated = []
    unknown = []
    for row in out:
        end = rules.period_end(str(row.get("due_period") or "")) or ""
        (dated if end else unknown).append(row)
    dated.sort(
        key=lambda row: (
            rules.period_end(str(row.get("due_period") or "")) or "",
            str(row.get("id") or ""),
        ),
        reverse=True,
    )
    unknown.sort(key=lambda row: str(row.get("id") or ""))
    return dated + unknown


def get_commitment(cid: str) -> Optional[Dict[str, Any]]:
    for r in _load().get("commitments", []):
        if r.get("id") == cid:
            return r
    return None


def propose(rows: Iterable[Dict[str, Any]], *, proposed_by: str) -> Dict[str, Any]:
    """Add valid, new proposals as ``unreviewed``. Returns added ids and rejects."""
    added: List[str] = []
    skipped: List[Dict[str, Any]] = []
    with _LOCK:
        data = _load()
        existing = {r["id"] for r in data.get("commitments", [])}
        for row in rows:
            errs = rules.validate_commitment(row)
            if errs:
                skipped.append({"quote": (row.get("quote") or "")[:120], "errors": errs})
                continue
            cid = commitment_id(row["company_id"], row["source_url"], row["quote"])
            if cid in existing:
                skipped.append({"id": cid, "errors": ["duplicate"]})
                continue
            rec = {
                **{k: row.get(k) for k in (
                    "company_id", "type", "subject", "outcome", "due_period", "quote",
                    "source_url", "as_of", "doc_id", "speaker", "extractor",
                )},
                "id": cid,
                "due_date": rules.period_end(str(row["due_period"])),
                "state": rules.OPEN,
                "review_status": "unreviewed",
                "proposed_by": proposed_by,
                "proposed_at": _now(),
                "history": [],
            }
            data.setdefault("commitments", []).append(rec)
            existing.add(cid)
            added.append(cid)
        if added:
            _save(data)
    return {"added": added, "skipped": skipped}


def review(
    cid: str,
    *,
    decision: str,
    reviewer: str,
    edits: Optional[Dict[str, Any]] = None,
    note: str = "",
) -> Dict[str, Any]:
    """Accept or reject a proposal. Edits are limited to descriptive fields."""
    if decision not in ("accepted", "rejected"):
        raise ValueError("invalid_decision")
    if not reviewer:
        raise ValueError("missing_reviewer")
    allowed = {"type", "subject", "outcome", "due_period"}
    with _LOCK:
        data = _load()
        for r in data.get("commitments", []):
            if r.get("id") != cid:
                continue
            if r.get("review_status") != "unreviewed":
                raise ValueError("already_reviewed")
            candidate = {**r, **{k: v for k, v in (edits or {}).items() if k in allowed}}
            if decision == "accepted":
                errs = rules.validate_commitment(candidate)
                if errs:
                    raise ValueError(",".join(errs))
            candidate["due_date"] = rules.period_end(str(candidate.get("due_period") or ""))
            candidate["review_status"] = decision
            candidate["reviewed_by"] = reviewer
            candidate["reviewed_at"] = _now()
            candidate["review_note"] = note
            r.clear()
            r.update(candidate)
            _save(data)
            return r
    raise KeyError("commitment_not_found")


def transition(
    cid: str, *, new_state: str, proof: Dict[str, Any], reviewer: str
) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        rows = data.get("commitments", [])
        for i, r in enumerate(rows):
            if r.get("id") == cid:
                rows[i] = rules.apply_transition(
                    r, new_state, proof, reviewer=reviewer, reviewed_at=_now()
                )
                _save(data)
                return rows[i]
    raise KeyError("commitment_not_found")


def company_view(company_id: str, *, include_unreviewed: bool, as_of: Optional[str] = None) -> Dict[str, Any]:
    rows = list_commitments(company_id, include_unreviewed=include_unreviewed)
    when = as_of or datetime.now(timezone.utc).date().isoformat()
    return {
        "company_id": company_id,
        "as_of": when,
        "summary": rules.delivery_summary(rows, as_of=when),
        "commitments": [
            {
                **r,
                "type_label": rules.TYPE_LABELS.get(r.get("type", ""), r.get("type")),
                "state_label": rules.STATE_LABELS.get(r.get("state", ""), r.get("state")),
            }
            for r in rows
        ],
        "includes_unreviewed": include_unreviewed,
        "note": (
            "Dated commitments made by the company, each traced to the filing that stated it. "
            "Shown separately from the GCI and not part of it."
        ),
    }
