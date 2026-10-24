"""Cite-or-drop verifier for CiteAlpha Analyst outputs (pure, no I/O, no LLM).

Every claim must point at one or more numbered citations. A ``quoted`` claim
must also have every number it states present in a cited quote, and share at
least one content word with it. A ``computed`` claim (a count or rate derived by
code from cited rows) or a ``record`` claim (a reviewed dataset row rendered by
code) needs its source citations but skips the number check. Model-written text
is always ``quoted``.
Claims that fail are removed and reported — outputs fail closed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence

_MARKER = re.compile(r"\[(\d+)\]")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z₹\"'(])")
_NUM_TOKEN = re.compile(r"[A-Za-z₹]*\d[\d,]*(?:\.\d+)?%?")
_WORD = re.compile(r"[a-z][a-z\-]{3,}")

_STOP = {
    "this", "that", "with", "from", "have", "were", "will", "been", "their", "they",
    "which", "into", "than", "over", "also", "said", "says", "company", "management",
    "year", "quarter", "guided", "guidance", "reported", "about", "when", "what",
}

ADVICE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"\b(buy|sell|accumulate|avoid|reduce)\s+(this|the|these)\s+(stock|stocks|share|shares|name)\b",
        r"\b(strong\s+)?(buy|sell|hold)\s+(rating|signal|call|recommendation)s?\b",
        r"\btarget\s+price\b",
        r"\bprice\s+target\b",
        r"\b(over|under)weight\b",
        r"\bundervalued\b|\bovervalued\b",
        r"\b(out|under)perform\w*\s+the\s+(market|index|sensex|nifty|peers)\b",
        r"\bmulti-?bagger\b",
        r"\btop\s+picks?\b",
        r"\bsignal\b",
        r"\bwe\s+recommend\b",
    )
)


def _norm_num(tok: str) -> str:
    t = tok.lower().replace(",", "").replace("₹", "").rstrip("%")
    if re.fullmatch(r"\d+\.0+", t):
        t = t.split(".")[0]
    return t


def number_tokens(text: str) -> set[str]:
    clean = _MARKER.sub(" ", text or "")
    return {_norm_num(m.group(0)) for m in _NUM_TOKEN.finditer(clean)}


def content_words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def has_advice_wording(text: str) -> bool:
    return any(p.search(text or "") for p in ADVICE_PATTERNS)


def split_sentences(text: str) -> List[str]:
    out = []
    for block in (text or "").splitlines():
        block = block.strip()
        if not block:
            continue
        out.extend(s.strip() for s in _SENT_SPLIT.split(block) if s.strip())
    return out


def _cited_text(citations: Sequence[Dict[str, Any]], ns: Iterable[int]) -> str:
    by_n = {int(c.get("n")): c for c in citations if c.get("n") is not None}
    parts = []
    for n in ns:
        c = by_n.get(int(n))
        if c:
            parts.append(" ".join(str(c.get(k) or "") for k in ("quote", "title", "date", "period")))
    return " ".join(parts)


def verify_claims(
    claims: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """``claims``: ``{"text", "cites": [n,...], "kind": "quoted"|"computed"|"record"}``."""
    valid_ns = {int(c["n"]) for c in citations if c.get("n") is not None}
    kept: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for claim in claims:
        text = str(claim.get("text") or "").strip()
        cites = [int(n) for n in claim.get("cites") or []]
        kind = claim.get("kind") or "quoted"
        reason = None
        if not text:
            reason = "empty"
        elif has_advice_wording(text):
            reason = "advice_wording"
        elif not cites:
            reason = "no_citation"
        elif any(n not in valid_ns for n in cites):
            reason = "unknown_citation"
        elif kind == "quoted":
            src = _cited_text(citations, cites)
            src_nums = number_tokens(src)
            missing = sorted(t for t in number_tokens(text) if t not in src_nums)
            if missing:
                reason = "number_not_in_source:" + ",".join(missing[:5])
            elif not (content_words(text) & content_words(src)):
                reason = "no_overlap_with_source"
        if reason:
            removed.append({**claim, "reason": reason})
        else:
            kept.append(claim)
    return {"kept": kept, "removed": removed, "ok": bool(kept)}


def verify_text(text: str, citations: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Free text (for example a model-written summary) → sentence claims → verify."""
    claims = [
        {"text": s, "cites": [int(n) for n in _MARKER.findall(s)], "kind": "quoted"}
        for s in split_sentences(text)
    ]
    return verify_claims(claims, citations)
