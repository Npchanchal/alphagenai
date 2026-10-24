"""India event filings for CiteAlpha Analyst Skills (A5).

Classifies exchange announcements that the GCI pipeline does not collect — credit
rating actions, USFDA inspection outcomes, open offers / delisting / schemes, and
offer documents — and ingests them as dated, linked filings. Kept apart from the
guidance discovery budget in ``exchange_filings`` so GCI coverage is unaffected.
Nothing here writes to the GCI or the Commitment Record.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

EVENT_RULES = (
    ("corporate_action", ("open offer", "delisting", "scheme of arrangement", "scheme of amalgamation",
                          "amalgamation", "demerger", "swap ratio", "buyback", "buy-back", "nclt")),
    ("credit_rating", ("credit rating", "rating action", "rating rationale", "crisil", "icra", "care ratings",
                       "careedge", "india ratings", "brickwork", "acuite", "infomerics")),
    ("usfda", ("usfda", "us fda", "u.s. fda", "food and drug administration", "form 483", "warning letter",
               "import alert", "establishment inspection report", "voluntary action indicated",
               "official action indicated")),
    ("offer_document", ("draft red herring", "red herring prospectus", "drhp", "letter of offer",
                        "placement document", "offer document")),
)
EVENT_KINDS = tuple(k for k, _ in EVENT_RULES)


def classify_event(desc: str, text: str = "") -> Optional[str]:
    blob = f"{desc} {text}".lower()
    for kind, cues in EVENT_RULES:
        if any(c in blob for c in cues):
            return kind
    return None


def event_kind(doc: Dict[str, Any]) -> Optional[str]:
    if doc.get("doc_type") in EVENT_KINDS:
        return doc["doc_type"]
    return classify_event(str(doc.get("title") or ""), str(doc.get("text") or "")[:3000])


def enabled() -> bool:
    return os.environ.get("ANALYST_EVENT_FILINGS", "").strip().lower() in ("1", "true", "yes")


def discover_nse_events(
    company_id: str,
    *,
    months: int = 12,
    max_docs: int = 4,
    payload: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Event announcements (PDF links) for one company, newest first. ``payload``: NSE JSON (tests)."""
    from app.services import exchange_filings as ef

    if payload is None:
        symbol = ef.nse_symbol_for(company_id)
        if not symbol:
            return []
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=int(months * 30.5))
        url = ef.NSE_ANNOUNCEMENTS.format(symbol=quote(symbol, safe=""), start=start.strftime("%d-%m-%Y"),
                                          end=end.strftime("%d-%m-%Y"))
        raw = ef.fetch_bytes(url, company_id, bucket="discovery", accept="application/json")
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "[]")
    picked: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for ann in payload if isinstance(payload, list) else []:
        link = str(ann.get("attchmntFile") or "").strip()
        if not link.lower().endswith(".pdf") or link in seen or not ef.is_exchange_host(link):
            continue
        desc, text = str(ann.get("desc") or ""), str(ann.get("attchmntText") or "")
        kind = classify_event(desc, text)
        if not kind:
            continue
        seen.add(link)
        picked.append({"url": link, "category": kind, "title": (text or desc)[:200],
                       "date": ef._ann_date(str(ann.get("an_dt") or ann.get("sort_date") or ""))})
    picked.sort(key=lambda r: str(r["date"] or ""), reverse=True)
    return picked[:max_docs]


def ingest_events(
    company_id: str,
    *,
    payload: Optional[List[Dict[str, Any]]] = None,
    texts: Optional[Dict[str, str]] = None,
    max_docs: int = 4,
) -> Dict[str, Any]:
    """Discover and ingest event filings. ``texts`` maps URL → text (tests skip the network)."""
    from app.data import doc_store
    from app.services import exchange_filings as ef

    have = {d.get("url") for d in doc_store.list_documents(company_id=company_id, hydrate=False)}
    results = []
    for row in discover_nse_events(company_id, payload=payload, max_docs=max_docs):
        if row["url"] in have:
            results.append({"url": row["url"], "ok": True, "action": "already_held"})
            continue
        try:
            res = ef.ingest_url(company_id, row["url"], title=row["title"], date=row["date"],
                                category=row["category"], text=(texts or {}).get(row["url"]))
        except Exception as exc:  # one bad filing must not stop the batch
            res = {"ok": False, "url": row["url"], "reason": type(exc).__name__}
        results.append({**res, "category": row["category"]})
    return {"company_id": company_id, "results": results}
