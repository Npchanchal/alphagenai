"""Commitment monitor: build disclosure cycles from the document store and propose
quiet drops. Proposals only — a reviewer closes a commitment.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List

from app.services import commitments as rules

CYCLE_DOC_TYPES = ("transcript", "investor_presentation", "annual_report", "ir_guidance", "results")
_WORD = re.compile(r"[a-z][a-z0-9\-]{3,}")
_STOP = {"will", "with", "from", "that", "this", "plan", "plans", "expect", "expected", "target",
         "company", "year", "quarter", "by", "end", "the", "and", "our", "have"}
MENTION_SHARE = 0.6


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def mentions(commitment: Dict[str, Any], text: str) -> bool:
    """A document mentions a commitment when most of its subject keywords appear."""
    keys = _keywords(commitment.get("subject") or "")
    if not keys:
        return False
    found = keys & _keywords(text)
    return len(found) / len(keys) >= MENTION_SHARE


def build_cycles(company_id: str, commitments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One cycle per disclosure date (all qualifying documents published that day)."""
    from app.data import doc_store

    by_date: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in doc_store.list_documents(company_id=company_id):
        if d.get("doc_type") not in CYCLE_DOC_TYPES or not d.get("date"):
            continue
        full = doc_store.get_document(d["doc_id"]) or d
        by_date[str(d["date"])].append(full)
    cycles = []
    for as_of in sorted(by_date):
        text = " ".join(doc.get("text") or "" for doc in by_date[as_of])
        cycles.append(
            {
                "as_of": as_of,
                "doc_ids": [doc["doc_id"] for doc in by_date[as_of]],
                "mentions": {c["id"] for c in commitments if mentions(c, text)},
            }
        )
    return cycles


def scan_company(company_id: str) -> Dict[str, Any]:
    from app.services import commitment_store

    rows = commitment_store.list_commitments(company_id)
    cycles = build_cycles(company_id, rows)
    proposals = rules.detect_quiet_drops(rows, cycles)
    return {
        "company_id": company_id,
        "cycles": [{"as_of": c["as_of"], "doc_ids": c["doc_ids"], "mentions": sorted(c["mentions"])} for c in cycles],
        "proposals": proposals,
        "note": "Proposals only. A reviewer confirms each before the commitment is closed.",
    }
