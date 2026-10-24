"""Read-only tools for CiteAlpha Analyst.

Every tool returns ``{"evidence": [...], "data": {...}}``. An evidence item is a
quotable fact with its own source link and date; the runtime numbers them into
citations. Tools never write to the GCI, the score ledger or the Commitment
Record — changes to those go through the review queue.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from app.data.metric_catalog import display_name_for

CLOSED_LABELS = ("exceeded", "met", "missed", "dropped")
_TOKEN = re.compile(r"[a-z0-9]{3,}")
_SENT = re.compile(r"(?<=[.!?])\s+")


def _gci(company_id: str):
    from app.services import repository

    return repository.get_company_gci(company_id)


def _num(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def _with_unit(text: str, metric_id: str) -> str:
    from app.data.metric_catalog import get_metric

    if text == "n/a":
        return text
    unit = (get_metric(metric_id) or {}).get("unit")
    if unit == "pct":
        return f"{text}%"
    if unit == "inr_cr":
        return f"₹{text} cr"
    if unit in ("days", "mmt"):
        return f"{text} {'days' if unit == 'days' else 'MMT'}"
    return text


def _band(o) -> str:
    lo, hi = o.guided_low, o.guided_high
    if lo is not None and hi is not None and lo != hi:
        return _with_unit(f"{_num(lo)}–{_num(hi)}", o.metric)
    return _with_unit(_num(o.guided_value), o.metric)


def _permalink(citation_id: Optional[str]) -> Optional[str]:
    return f"/c/{citation_id}" if citation_id else None


def _has_guidance_cite(o) -> bool:
    return bool(o.guidance_quote and o.guidance_source_url)


def profile(company_id: str) -> Dict[str, Any]:
    d = _gci(company_id)
    published = d.data_quality == "hand_labeled" and d.gci_score is not None
    evidence = []
    if published:
        evidence.append(
            {
                "kind": "dossier",
                "company_id": d.id,
                "title": f"{d.name} — GCI dossier",
                "quote": f"GCI {_num(d.gci_score)} ({d.confidence_tier or 'provisional'}) as of {d.as_of or 'n/a'}",
                "source_url": f"/companies/{d.id}",
                "date": d.as_of,
            }
        )
    return {
        "evidence": evidence,
        "data": {
            "company_id": d.id,
            "name": d.name,
            "ticker": d.ticker,
            "sector": d.sector,
            "gci_score": d.gci_score if published else None,
            "confidence_tier": d.confidence_tier if published else None,
            "as_of": d.as_of,
            "closed_periods": d.closed_periods,
            "published": published,
        },
    }


def guidance_record(company_id: str) -> Dict[str, Any]:
    """Closed guidance rows that carry both citations (promise + actual)."""
    d = _gci(company_id)
    evidence: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    for o in d.outcomes:
        if o.label not in CLOSED_LABELS or not _has_guidance_cite(o):
            continue
        if o.label != "dropped" and not (o.quote_span and o.source_url):
            continue
        g_idx = len(evidence)
        evidence.append(
            {
                "kind": "guidance",
                "company_id": d.id,
                "title": f"{d.name} — {display_name_for(o.metric)} guidance for {o.period}",
                "quote": o.guidance_quote,
                "source_url": o.guidance_source_url,
                "date": o.guidance_as_of,
                "period": o.period,
                "permalink": _permalink(o.citation_id),
            }
        )
        a_idx = None
        if o.quote_span and o.source_url:
            a_idx = len(evidence)
            evidence.append(
                {
                    "kind": "actual",
                    "company_id": d.id,
                    "title": f"{d.name} — reported {display_name_for(o.metric)} for {o.period}",
                    "quote": o.quote_span,
                    "source_url": o.source_url,
                    "date": o.as_of,
                    "period": o.period,
                    "permalink": _permalink(o.citation_id),
                }
            )
        rows.append(
            {
                "period": o.period,
                "metric": o.metric,
                "metric_name": display_name_for(o.metric),
                "label": o.label,
                "guided": _band(o),
                "actual": _with_unit(_num(o.actual_value), o.metric),
                "guidance_ev": g_idx,
                "actual_ev": a_idx,
            }
        )
    return {"evidence": evidence, "data": {"rows": rows, "name": d.name}}


def open_guidance(company_id: str) -> Dict[str, Any]:
    d = _gci(company_id)
    evidence: List[Dict[str, Any]] = []
    rows = []
    for o in d.outcomes:
        if o.label != "pending" or not _has_guidance_cite(o):
            continue
        rows.append(
            {
                "period": o.period,
                "metric_name": display_name_for(o.metric),
                "guided": _band(o),
                "guidance_ev": len(evidence),
            }
        )
        evidence.append(
            {
                "kind": "guidance",
                "company_id": d.id,
                "title": f"{d.name} — {display_name_for(o.metric)} guidance for {o.period}",
                "quote": o.guidance_quote,
                "source_url": o.guidance_source_url,
                "date": o.guidance_as_of,
                "period": o.period,
                "permalink": _permalink(o.citation_id),
            }
        )
    return {"evidence": evidence, "data": {"rows": rows, "name": d.name}}


def commitments(company_id: str, include_unreviewed: bool = False) -> Dict[str, Any]:
    from app.services import commitment_store

    view = commitment_store.company_view(company_id, include_unreviewed=include_unreviewed)
    evidence = []
    rows = []
    for c in view["commitments"]:
        rows.append({**c, "ev": len(evidence)})
        evidence.append(
            {
                "kind": "commitment",
                "company_id": company_id,
                "title": f"Commitment: {c.get('subject')}",
                "quote": c.get("quote"),
                "source_url": c.get("source_url"),
                "date": c.get("as_of"),
                "period": c.get("due_period"),
            }
        )
        proof = c.get("proof") or {}
        if proof.get("quote") and proof.get("source_url"):
            rows[-1]["proof_ev"] = len(evidence)
            evidence.append(
                {
                    "kind": "proof",
                    "company_id": company_id,
                    "title": f"Result: {c.get('subject')}",
                    "quote": proof["quote"],
                    "source_url": proof["source_url"],
                    "date": proof.get("as_of"),
                }
            )
    return {"evidence": evidence, "data": {"rows": rows, "summary": view["summary"]}}


def _best_sentence(body: str, query: str) -> str:
    q = set(_TOKEN.findall(query.lower()))
    best, best_score = "", 0
    for s in _SENT.split(" ".join((body or "").split())):
        if len(s) < 25:
            continue
        score = len(q & set(_TOKEN.findall(s.lower())))
        if score > best_score:
            best, best_score = s, score
    return best[:400] if best_score else ""


def filing_search(company_id: str, query: str, limit: int = 3) -> Dict[str, Any]:
    from app.services.research import search_documents

    res = search_documents(query, company_id=company_id, limit=limit * 3)
    evidence = []
    for h in res.get("results") or []:
        quote = _best_sentence(h.get("body") or "", query)
        if not quote or not h.get("url"):
            continue
        evidence.append(
            {
                "kind": "document",
                "company_id": h.get("company_id"),
                "title": h.get("title"),
                "quote": quote,
                "source_url": h.get("url"),
                "date": h.get("date"),
                "doc_id": h.get("id"),
                "doc_type": h.get("doc_type"),
                "permalink": _permalink(h.get("id")),
            }
        )
        if len(evidence) >= limit:
            break
    return {"evidence": evidence, "data": {"query": query, "found": len(evidence)}}


FILING_DOC_TYPES = ("transcript", "results", "ir_guidance", "investor_presentation", "annual_report", "announcement")
# Generated inside CiteAlpha (corpus packs, demo transcripts) — never quoted as a company filing.
INTERNAL_SOURCES = frozenset({"hand_labeled_period_pack", "sample_transcript", "bootstrap"})
# Ingestion paths that bring a new document in from outside; only these can trigger a Monitor.
INGEST_SOURCES = frozenset({"exchange_filing", "ir_catalog", "paste", "plain_text", "html_fetch", "ingest"})


def is_company_filing(doc: Dict[str, Any]) -> bool:
    return bool(doc.get("url")) and doc.get("source") not in INTERNAL_SOURCES


def is_ingested_filing(doc: Dict[str, Any]) -> bool:
    return bool(doc.get("url")) and doc.get("source") in INGEST_SOURCES


def _list_documents(company_id: str) -> List[Dict[str, Any]]:
    from app.data import doc_store

    return doc_store.list_documents(company_id=company_id)


def _get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    from app.data import doc_store

    return doc_store.get_document(doc_id)


def _forward_passages(text: str, limit: int) -> List[str]:
    from app.services.commitment_extract import _FORWARD

    out: List[str] = []
    for s in _SENT.split(" ".join((text or "").split())):
        if 30 <= len(s) <= 400 and _FORWARD.search(s) and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _doc_evidence(doc: Dict[str, Any], quote: str) -> Dict[str, Any]:
    return {
        "kind": "document",
        "company_id": doc.get("company_id"),
        "title": doc.get("title"),
        "quote": quote,
        "source_url": doc.get("url"),
        "date": doc.get("date"),
        "doc_id": doc.get("doc_id"),
        "doc_type": doc.get("doc_type"),
        "permalink": _permalink(doc.get("doc_id")),
    }


def document_passages(company_id: str, doc_id: str, limit: int = 5) -> Dict[str, Any]:
    """Forward-looking sentences quoted from one filing of this company."""
    doc = _get_document(doc_id)
    if not doc or doc.get("company_id") != company_id or not is_company_filing(doc):
        return {"evidence": [], "data": {"doc_id": doc_id, "found": 0}}
    evidence = [_doc_evidence(doc, q) for q in _forward_passages(doc.get("text") or "", limit)]
    return {"evidence": evidence, "data": {"doc_id": doc_id, "found": len(evidence)}}


def recent_filings(company_id: str, limit: int = 5) -> Dict[str, Any]:
    """Latest filings with one forward-looking passage each."""
    docs = [d for d in _list_documents(company_id) if d.get("doc_type") in FILING_DOC_TYPES and is_company_filing(d)]
    docs.sort(key=lambda d: str(d.get("date") or ""), reverse=True)
    evidence = []
    for d in docs:
        passages = _forward_passages(d.get("text") or "", 1)
        if passages:
            evidence.append(_doc_evidence(d, passages[0]))
        if len(evidence) >= limit:
            break
    return {"evidence": evidence, "data": {"found": len(evidence)}}


SHIFT_TOPICS: Dict[str, tuple] = {
    "Revenue": ("revenue", "sales", "top line", "topline"),
    "Margin": ("margin", "ebitda"),
    "Capex": ("capex", "capital expenditure"),
    "Debt": ("debt", "leverage", "borrowing", "deleverag"),
    "Order book": ("order book", "order inflow", "orderbook"),
    "Volume": ("volume", "tonnage", "units sold"),
    "Demand": ("demand",),
    "Pricing": ("pricing", "price increase", "realisation", "realization"),
    "Capacity": ("capacity", "utilisation", "utilization", "commissioning"),
}
_DIGITS = re.compile(r"\d+(?:\.\d+)?")


def _topic_sentence(text: str, terms: tuple) -> str:
    from app.services.commitment_extract import _FORWARD

    best = ""
    for s in _SENT.split(" ".join((text or "").split())):
        low = s.lower()
        if not (30 <= len(s) <= 400) or not any(t in low for t in terms):
            continue
        if _DIGITS.search(s) or _FORWARD.search(s):
            if not best or (_DIGITS.search(s) and not _DIGITS.search(best)):
                best = s
    return best


def language_shift(company_id: str, limit: int = 6) -> Dict[str, Any]:
    """What management says in its latest filings versus the previous disclosure date, by topic."""
    docs = [d for d in _list_documents(company_id)
            if d.get("doc_type") in FILING_DOC_TYPES + ("guidance",) and is_company_filing(d) and d.get("date")]
    dates = sorted({str(d["date"]) for d in docs}, reverse=True)
    if len(dates) < 2:
        return {"evidence": [], "data": {"rows": [], "latest": dates[0] if dates else None, "previous": None}}
    latest = [d for d in docs if str(d["date"]) == dates[0]]
    previous = [d for d in docs if str(d["date"]) == dates[1]]
    evidence: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    for topic, terms in SHIFT_TOPICS.items():
        def pick(group):
            for d in group:
                s = _topic_sentence(d.get("text") or "", terms)
                if s:
                    return d, s
            return None, ""

        pd, ps = pick(previous)
        if not ps:
            continue
        ld, ls = pick(latest)
        p_idx = len(evidence)
        evidence.append(_doc_evidence(pd, ps))
        if not ls:
            rows.append({"topic": topic, "change": "not_repeated", "previous_ev": p_idx, "latest_ev": None})
        else:
            if set(_DIGITS.findall(ps)) == set(_DIGITS.findall(ls)):
                evidence.pop()
                continue
            evidence.append(_doc_evidence(ld, ls))
            rows.append({"topic": topic, "change": "figures_changed", "previous_ev": p_idx, "latest_ev": p_idx + 1})
        if len(rows) >= limit:
            break
    return {"evidence": evidence, "data": {"rows": rows, "latest": dates[0], "previous": dates[1]}}


AGENCY_TERMS = ("crisil", "icra", "care ratings", "careedge", "india ratings", "brickwork", "acuite", "infomerics")
REGULATOR_TERMS = ("sebi", "reserve bank", "rbi ", "nclt", "tribunal", "usfda", "us fda", "food and drug administration",
                   "competition commission", "ministry of", "directorate general")


def event_passages(
    company_id: str,
    terms: tuple,
    limit: int = 5,
    figures: bool = False,
    kinds: tuple = (),
    org_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Sentences mentioning the given terms in this company's filings (newest first), then the Project's uploads."""
    from app.services.event_filings import event_kind

    low_terms = tuple(t.lower() for t in terms)
    docs = sorted((d for d in _list_documents(company_id) if is_company_filing(d)),
                  key=lambda d: str(d.get("date") or ""), reverse=True)
    evidence: List[Dict[str, Any]] = []
    seen: set = set()

    def ok(s: str) -> bool:
        low = s.lower()
        return (25 <= len(s) <= 400 and s not in seen and any(t in low for t in low_terms)
                and (not figures or bool(_DIGITS.search(s))))

    for d in docs:
        kind = event_kind(d)
        if kinds and kind not in kinds:
            continue
        per_doc = 0
        for s in _SENT.split(" ".join((d.get("text") or "").split())):
            if ok(s):
                seen.add(s)
                evidence.append({**_doc_evidence(d, s), "event_kind": kind})
                per_doc += 1
            if per_doc >= 2 or len(evidence) >= limit:
                break
        if len(evidence) >= limit:
            break
    if org_id and project_id and len(evidence) < limit:
        from app.services.agent import uploads

        for p in uploads.passages(org_id, project_id):
            if ok(p["text"]):
                seen.add(p["text"])
                evidence.append(_upload_evidence(p, company_id))
            if len(evidence) >= limit:
                break
    return {"evidence": evidence, "data": {"found": len(evidence)}}


def _upload_evidence(p: Dict[str, Any], company_id: str) -> Dict[str, Any]:
    return {
        "kind": "upload",
        "company_id": company_id,
        "title": f"{p['filename']} ({p['loc']}) — your upload",
        "quote": p["text"],
        "source_url": f"upload://{p['upload_id']}#{p['loc']}",
        "date": (p.get("uploaded_at") or "")[:10] or None,
        "doc_id": p["upload_id"],
        "loc": p["loc"],
        "file_kind": p.get("kind"),
    }


def project_uploads(company_id: str, org_id: str, project_id: str, query: str = "", limit: int = 0) -> Dict[str, Any]:
    """Passages from the Project's own uploads (same organisation only)."""
    from app.services.agent import uploads

    if not org_id or not project_id:
        return {"evidence": [], "data": {"found": 0}}
    rows = uploads.search(org_id, project_id, query, limit or 5) if query else uploads.passages(org_id, project_id)
    if limit and not query:
        rows = rows[:limit]
    evidence = [_upload_evidence(p, company_id) for p in rows]
    return {"evidence": evidence, "data": {"found": len(evidence)}}


def peers(company_id: str, limit: int = 5) -> Dict[str, Any]:
    from app.data.seed import list_companies

    focus = _gci(company_id)
    evidence = []
    rows = []
    for c in list_companies():
        if c.get("sector") != focus.sector or c["id"] == company_id:
            continue
        try:
            d = _gci(c["id"])
        except Exception:
            continue
        if d.data_quality != "hand_labeled" or d.gci_score is None:
            continue
        rows.append({"company_id": d.id, "name": d.name, "gci": d.gci_score,
                     "tier": d.confidence_tier, "ev": len(evidence)})
        evidence.append(
            {
                "kind": "dossier",
                "company_id": d.id,
                "title": f"{d.name} — GCI dossier",
                "quote": f"GCI {_num(d.gci_score)} ({d.confidence_tier or 'provisional'}) as of {d.as_of or 'n/a'}",
                "source_url": f"/companies/{d.id}",
                "date": d.as_of,
            }
        )
        if len(rows) >= limit:
            break
    return {"evidence": evidence, "data": {"rows": rows, "sector": focus.sector}}


REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "profile": profile,
    "guidance_record": guidance_record,
    "open_guidance": open_guidance,
    "commitments": commitments,
    "filing_search": filing_search,
    "peers": peers,
    "recent_filings": recent_filings,
    "document_passages": document_passages,
    "project_uploads": project_uploads,
    "language_shift": language_shift,
    "event_passages": event_passages,
}


def describe() -> List[Dict[str, str]]:
    return [{"name": k, "doc": (v.__doc__ or "").strip().splitlines()[0] if v.__doc__ else k}
            for k, v in REGISTRY.items()]
