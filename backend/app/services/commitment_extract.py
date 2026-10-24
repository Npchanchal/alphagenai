"""Propose commitments from a filing / transcript text.

Two extractors, both proposal-only (rows land ``unreviewed``):

* ``heuristic_v1`` — sentence has a commitment cue *and* a readable time anchor.
* ``llm_v1`` — model returns JSON; every quote must appear verbatim in the text
  and every due period must parse, else the row is dropped.

Neither path can invent a quote: the quote is always a span of the source text.
"""

from __future__ import annotations

import calendar
import json
import re
from typing import Any, Dict, List, Optional

from app.services import commitments as rules

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(₹])")

_TYPE_CUES: List[tuple[str, re.Pattern[str]]] = [
    ("capacity", re.compile(r"\b(commission\w*|capacity|plant|greenfield|brownfield|line\s+\d|tpa|mtpa|mw\b|gw\b)", re.I)),
    ("capex", re.compile(r"\b(capex|capital expenditure|invest(ment)?\s+of|outlay)\b", re.I)),
    ("balance_sheet", re.compile(r"\b(debt[- ]free|net[- ]debt|deleverag\w*|repay\w*|leverage|net cash|gearing)\b", re.I)),
    ("order_book", re.compile(r"\b(order\s*book|order\s+inflow|backlog|executable)\b", re.I)),
    ("corporate_action", re.compile(r"\b(merger|amalgamation|demerger|scheme of arrangement|divest\w*|acquisition|listing of)\b", re.I)),
    ("launch", re.compile(r"\b(launch\w*|roll[- ]?out|new stores|new branches|enter(ing)? (the )?\w+ market|filings? (of|for) \d+)\b", re.I)),
    ("esg", re.compile(r"\b(renewable|net[- ]zero|carbon neutral|emission\w*|water positive)\b", re.I)),
    ("operational", re.compile(r"\b(utili[sz]ation|cost (saving|reduction)|volume of|productivity)\b", re.I)),
]

_FORWARD = re.compile(
    r"\b(will|expect\w*|plan\w*|target\w*|aim\w*|on track|intend\w*|commit\w*|guid\w*|by the end of|should be)\b",
    re.I,
)

_ANCHOR_FY = re.compile(r"\b(?:(Q[1-4]|H[12])\s*)?FY\s*'?(\d{2}|\d{4})\b", re.I)
_ANCHOR_MONTH = re.compile(
    r"\b(?:by|in|before|end of)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b",
    re.I,
)


def _anchor(sentence: str) -> Optional[str]:
    m = _ANCHOR_FY.search(sentence)
    if m:
        part = (m.group(1) or "").upper()
        yy = m.group(2)
        label = f"FY{yy[-2:]}" if len(yy) == 4 else f"FY{yy}"
        return f"{part} {label}".strip()
    m = _ANCHOR_MONTH.search(sentence)
    if m:
        month = list(calendar.month_name).index(m.group(1).capitalize())
        year = int(m.group(2))
        last = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-{last:02d}"
    return None


def _classify(sentence: str) -> Optional[str]:
    for t, pat in _TYPE_CUES:
        if pat.search(sentence):
            return t
    return None


def _subject(sentence: str, max_words: int = 12) -> str:
    words = sentence.split()
    s = " ".join(words[:max_words])
    return s + ("…" if len(words) > max_words else "")


def heuristic_extract(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in _SENTENCE_SPLIT.split(" ".join((text or "").split())):
        s = raw.strip()
        if len(s) < 30 or len(s) > 400:
            continue
        if not _FORWARD.search(s):
            continue
        t = _classify(s)
        due = _anchor(s)
        if not t or not due or rules.period_end(due) is None:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "type": t,
                "subject": _subject(s),
                "outcome": s,
                "due_period": due,
                "quote": s,
                "extractor": "heuristic_v1",
            }
        )
    return out


_LLM_SYSTEM = (
    "You extract dated, checkable commitments made by an Indian listed company from its own "
    "disclosure. A commitment is forward-looking, has a subject, a checkable outcome and a due "
    "period. Ignore numeric revenue/margin/EPS guidance (tracked elsewhere), ignore aspirations "
    "without a date, ignore statements about the past. Types: "
    + ", ".join(rules.COMMITMENT_TYPES)
    + ". Return ONLY a JSON array of objects with keys: type, subject (<= 12 words), outcome "
    "(one plain sentence, what must be true when due), due_period (e.g. 'Q3 FY26', 'FY27', "
    "'H1 FY26' or ISO date), quote (copied word-for-word from the text, one or two sentences), "
    "speaker (if stated). Return [] if none."
)


def llm_extract(text: str, *, wait: bool = True) -> List[Dict[str, Any]]:
    from app.services import llm_client

    raw = llm_client.chat_completion(
        [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": (text or "")[:12000]},
        ],
        max_tokens=3000,
        wait=wait,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise RuntimeError("commitment extract did not return a JSON array")
    out = []
    for row in parsed:
        if not isinstance(row, dict):
            continue
        quote = str(row.get("quote") or "").strip()
        if not rules.quote_is_verbatim(quote, text):
            continue
        due = str(row.get("due_period") or "").strip()
        if rules.period_end(due) is None:
            continue
        if row.get("type") not in rules.COMMITMENT_TYPES:
            continue
        out.append(
            {
                "type": row["type"],
                "subject": str(row.get("subject") or _subject(quote))[:160],
                "outcome": str(row.get("outcome") or quote)[:400],
                "due_period": due,
                "quote": " ".join(quote.split()),
                "speaker": str(row.get("speaker") or "") or None,
                "extractor": "llm_v1",
            }
        )
    return out


def extract_from_document(doc: Dict[str, Any], *, use_llm: Optional[bool] = None) -> Dict[str, Any]:
    """Proposals for one stored document (``doc_store`` shape)."""
    text = doc.get("text") or doc.get("body") or ""
    engine = "heuristic_v1"
    rows: List[Dict[str, Any]] = []
    if use_llm is None:
        from app.services.llm_client import llm_configured

        use_llm = llm_configured()
    if use_llm:
        try:
            rows = llm_extract(text, wait=False)
            engine = "llm_v1"
        except Exception:
            rows = []
            engine = "heuristic_v1"
    if engine == "heuristic_v1":
        rows = heuristic_extract(text)
    base = {
        "company_id": doc.get("company_id"),
        "source_url": doc.get("url") or doc.get("source_url"),
        "as_of": doc.get("date"),
        "doc_id": doc.get("doc_id") or doc.get("id"),
    }
    return {
        "engine": engine,
        "doc_id": base["doc_id"],
        "proposals": [{**base, **r} for r in rows],
    }
