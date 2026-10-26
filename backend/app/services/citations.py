"""Citation / citeability helpers for GCI outcomes (Tier 1 foundation)."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote as urlquote, urlsplit, urlunsplit

# Dual-cited rows on a scoreable quality may be presented as citeable.
# extracted_verified stays provisional and is not ranked.
CITEABLE_QUALITIES = frozenset({"hand_labeled", "extracted_verified"})


def citation_id_for(
    *,
    company_id: str,
    period: str,
    metric: str,
    source_url: Optional[str] = None,
    quote_span: Optional[str] = None,
    doc_id: Optional[str] = None,
) -> str:
    """Stable citation id from company + period + metric + source fingerprint."""
    raw = "|".join(
        [
            company_id or "",
            period or "",
            metric or "",
            (doc_id or "").strip(),
            (source_url or "").strip(),
            (quote_span or "").strip()[:80],
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"cite_{digest}"


_FOLD_CHARS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
    "\u00a0": " ",
}


def _fold_map(text: str) -> Tuple[str, List[int]]:
    """Lower-case, straight quotes, collapsed whitespace, and original indexes."""
    chars: List[str] = []
    index: List[int] = []
    prev_space = False
    for i, raw in enumerate(text):
        ch = unicodedata.normalize("NFKC", raw)
        ch = _FOLD_CHARS.get(ch, ch)
        if ch.isspace():
            if prev_space or not chars:
                continue
            chars.append(" ")
            index.append(i)
            prev_space = True
            continue
        prev_space = False
        for c in ch.lower():
            chars.append(c)
            index.append(i)
    while chars and chars[-1] == " ":
        chars.pop()
        index.pop()
    return "".join(chars), index


def _range_from_fold(index: List[int], at: int, length: int) -> Tuple[Optional[int], Optional[int]]:
    if at < 0 or length <= 0 or at + length > len(index):
        return None, None
    start = index[at]
    end = index[at + length - 1] + 1
    if end <= start:
        return None, None
    return start, end


def span_offsets(text: str, quote: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Return (start, end) char offsets of quote in text, if found.

    Exact match first, then whitespace, quote marks, and dashes folded away.
    """
    if not text or not quote:
        return None, None
    q = quote.strip().strip("\"'“”‘’")
    if not q:
        return None, None
    idx = text.find(q)
    if idx >= 0:
        return idx, idx + len(q)
    folded, index = _fold_map(text)
    needle, _ = _fold_map(q)
    if not folded or not needle:
        return None, None
    at = folded.find(needle)
    if at >= 0:
        return _range_from_fold(index, at, len(needle))
    parts = [part.strip() for part in needle.replace("…", "...").split("...")]
    parts = [part for part in parts if len(part) >= 8]
    if len(parts) >= 2:
        a = folded.find(parts[0])
        b = folded.find(parts[-1], a + len(parts[0])) if a >= 0 else -1
        if a >= 0 and b >= 0 and b - a < 800:
            return _range_from_fold(index, a, b + len(parts[-1]) - a)
    words = [word for word in needle.split(" ") if len(word) >= 4][:8]
    if len(words) >= 3:
        frm = 0
        start_at = -1
        end_at = -1
        matched = 0
        for word in words:
            hit = folded.find(word, frm)
            if hit < 0 or (start_at >= 0 and hit - end_at > 240):
                break
            if start_at < 0:
                start_at = hit
            end_at = hit + len(word)
            frm = end_at
            matched += 1
        if matched >= 3 and start_at >= 0 and end_at > start_at:
            return _range_from_fold(index, start_at, end_at - start_at)
    short = needle[:40]
    if len(short) >= 8:
        return _range_from_fold(index, folded.find(short), len(short))
    return None, None


def _span_holds(text: str, start: Any, end: Any, quote: str) -> bool:
    try:
        s, e = int(start), int(end)
    except (TypeError, ValueError):
        return False
    if s < 0 or e > len(text) or e <= s:
        return False
    snippet = text[s:e]
    q = (quote or "").strip()
    if not q:
        return True
    if q in snippet or snippet in q:
        return True
    left, _ = _fold_map(snippet)
    right, _ = _fold_map(q)
    return bool(left and right and (right in left or left in right))


def is_indexed_excerpt_source(
    *, source_url: Optional[str] = None, source_ref: Optional[str] = None
) -> bool:
    """True when the quote is stored in CiteAlpha corpus, not verbatim on the external URL."""
    ref = (source_ref or "").lower()
    if "-ir-curated" in ref or ref.endswith("-curated"):
        return True
    href = (source_url or "").lower()
    if "bseindia.com/stock-share-price/" in href:
        return True
    return False


def resolve_outcome_source_url(
    company_id: str,
    source_url: Optional[str],
    source_ref: Optional[str],
) -> Optional[str]:
    """Prefer company IR portal over exchange ticker pages for curated excerpts."""
    href = (source_url or "").strip() or None
    if not is_indexed_excerpt_source(source_url=href, source_ref=source_ref):
        return href
    from app.data.ir_sources import target_for

    ir = target_for(company_id)
    if ir and (ir.get("url") or "").strip():
        return str(ir["url"]).strip()
    return href


def external_highlight_url(
    *,
    source_url: Optional[str],
    source_ref: Optional[str],
    quote: Optional[str],
    source_verified: Optional[bool] = None,
) -> Optional[str]:
    """Text-fragment URL only when the external page is expected to contain the quote."""
    if is_indexed_excerpt_source(source_url=source_url, source_ref=source_ref):
        return None
    if source_verified is False:
        return None
    return highlight_url(source_url, quote)


def highlight_url(url: Optional[str], quote: Optional[str]) -> Optional[str]:
    """Append a browser highlight fragment so the original filing opens on the quote.

    HTML: Chromium text fragments (`#:~:text=`). PDF: Chrome viewer `#search=`.
    """
    href = (url or "").strip()
    if not href:
        return None
    q = " ".join((quote or "").strip().split())
    parts = urlsplit(href)
    path_q = f"{parts.path}?{parts.query}".lower()
    is_pdf = parts.path.lower().endswith(".pdf") or ".pdf?" in path_q or "/pdf" in path_q
    if not q:
        return href
    snippet = q[:80]
    if is_pdf:
        frag = f"search={urlquote(snippet, safe='')}"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, frag))

    def _frag(s: str) -> str:
        return urlquote(s, safe="").replace("-", "%2D")

    if len(q) > 90:
        frag = f":~:text={_frag(q[:40])},{_frag(q[-40:])}"
    else:
        frag = f":~:text={_frag(snippet)}"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, frag))


def find_source_document(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the indexed document for a citation (doc_id, then quote, then URL)."""
    from app.data import doc_store

    if not doc_store.list_documents():
        doc_store.seed_from_outcomes_and_transcripts()
    doc_id = str(record.get("doc_id") or "").strip()
    if doc_id:
        found = doc_store.get_document(doc_id)
        if found:
            return found
    quote = (record.get("quote_span") or record.get("quote") or record.get("snippet") or "").strip()
    url = (record.get("source_url") or record.get("url") or "").strip()
    company_id = (record.get("company_id") or "").strip() or None
    rows = doc_store.list_documents(company_id=company_id)
    if quote:
        for d in rows:
            text = d.get("text") or ""
            if quote in text or quote[:40] in text:
                return d
    if url:
        for d in rows:
            if (d.get("url") or "").strip() == url:
                return d
    return None


def attach_source_document(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add document_text + resolved span so the UI can highlight the cited quote."""
    rec = dict(record)
    q = (rec.get("quote_span") or rec.get("quote") or rec.get("snippet") or "").strip()
    href = (rec.get("source_url") or rec.get("url") or "").strip() or None
    source_ref = rec.get("source_ref")
    rec["indexed_excerpt"] = is_indexed_excerpt_source(source_url=href, source_ref=source_ref)
    verified: Optional[bool] = rec.get("source_verified")
    if verified is None and href and q and not rec["indexed_excerpt"]:
        try:
            from app.services.source_verify import verify_source_binding

            verified = verify_source_binding(href, q)
            if verified is not None:
                rec["source_verified"] = verified
        except Exception:
            verified = None
    rec["highlight_url"] = external_highlight_url(
        source_url=href, source_ref=source_ref, quote=q, source_verified=verified
    )
    doc = find_source_document(rec)
    text = ""
    if doc:
        text = doc.get("text") or ""
        rec["doc_id"] = rec.get("doc_id") or doc.get("doc_id")
        rec["document_title"] = doc.get("title") or rec.get("title")
        if not href:
            href = (doc.get("url") or "").strip() or None
            rec["source_url"] = href
            rec["url"] = href
        rec["indexed_excerpt"] = is_indexed_excerpt_source(
            source_url=href, source_ref=source_ref or doc.get("source")
        )
        verified = rec.get("source_verified")
        if verified is None and href and q and not rec["indexed_excerpt"]:
            try:
                from app.services.source_verify import verify_source_binding

                verified = verify_source_binding(href, q)
                rec["source_verified"] = verified
            except Exception:
                verified = None
        rec["highlight_url"] = external_highlight_url(
            source_url=href,
            source_ref=source_ref or doc.get("source"),
            quote=q,
            source_verified=verified,
        )
    start, end = rec.get("span_start"), rec.get("span_end")
    if text and q:
        found_s, found_e = span_offsets(text, q)
        if found_s is not None and found_e is not None:
            start, end = found_s, found_e
        elif not _span_holds(text, start, end, q):
            start, end = None, None
    if text and start is not None and end is not None:
        rec["span_start"] = start
        rec["span_end"] = end
        rec["document_text"] = text
        rec["excerpt_only"] = False
    elif text:
        rec["document_text"] = text
        rec["excerpt_only"] = False
    elif q:
        rec["document_text"] = q
        rec["span_start"] = 0
        rec["span_end"] = len(q)
        rec["excerpt_only"] = True
    else:
        rec["document_text"] = None
        rec["excerpt_only"] = True
    return rec


def assess_citeability(
    *,
    data_quality: str,
    source_url: Optional[str] = None,
    quote_span: Optional[str] = None,
    review_status: Optional[str] = None,
    doc_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Return (citeable, reason).

    Reasons: ok | provisional | demo | missing_source | pending_review | rejected | quality_not_citeable
    """
    q = (data_quality or "").strip().lower()
    if q == "listing_provisional" or q.startswith("listing_"):
        return False, "provisional"
    if q == "demo_structured":
        return False, "demo"
    if review_status == "pending":
        return False, "pending_review"
    if review_status == "rejected":
        return False, "rejected"
    if q not in CITEABLE_QUALITIES:
        return False, "quality_not_citeable"
    url = (source_url or "").strip()
    quote = (quote_span or "").strip()
    if not url or not quote:
        return False, "missing_source"
    # doc_id preferred but not required for hand_labeled with URL+quote
    _ = doc_id
    return True, "ok"


def enrich_outcome_citation(
    outcome: Any,
    *,
    company_id: str,
    data_quality: str,
    doc_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build citation fields for OutcomeView serialization."""

    def _get(key: str) -> Any:
        if isinstance(outcome, dict):
            return outcome.get(key)
        return getattr(outcome, key, None)

    source_url = _get("source_url")
    quote_span = _get("quote_span")
    period = _get("period") or ""
    metric = _get("metric") or ""
    bound_doc = doc_id or _get("doc_id")
    span_start = _get("span_start")
    span_end = _get("span_end")
    if _get("source_verified") is False or _get("citeable") is False:
        citeable, reason = False, "source_unverified"
    else:
        citeable, reason = assess_citeability(
            data_quality=data_quality,
            source_url=source_url,
            quote_span=quote_span,
            review_status=_get("review_status"),
            doc_id=bound_doc,
        )
    out_quote = None if reason == "provisional" else quote_span
    cid = None
    if citeable:
        cid = citation_id_for(
            company_id=company_id,
            period=str(period),
            metric=str(metric),
            source_url=source_url,
            quote_span=quote_span,
            doc_id=bound_doc,
        )
    return {
        "citation_id": cid,
        "doc_id": bound_doc,
        "citeable": citeable,
        "cite_reason": reason,
        "quote_span": out_quote,
        "span_start": span_start,
        "span_end": span_end,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def locator_for(
    *,
    period: Optional[str] = None,
    metric: Optional[str] = None,
    span_start: Optional[int] = None,
    span_end: Optional[int] = None,
    doc_id: Optional[str] = None,
) -> str:
    """Human locator: period · metric · char span · short doc id."""
    parts: List[str] = []
    if period:
        parts.append(str(period))
    if metric:
        parts.append(str(metric).replace("_", " "))
    if span_start is not None and span_end is not None:
        parts.append(f"chars {span_start}–{span_end}")
    elif doc_id:
        parts.append(f"doc {str(doc_id)[:8]}")
    return " · ".join(parts) if parts else "unlocated"


def bibliographic_line(record: Dict[str, Any]) -> str:
    """Chicago-style note for IC memos (company, title, date, URL, id)."""
    who = record.get("name") or record.get("ticker") or record.get("company_id") or "Source"
    title = (record.get("title") or "Primary source").strip()
    date = record.get("date") or record.get("as_of") or ""
    url = (record.get("source_url") or record.get("url") or "").strip()
    cid = record.get("citation_id") or ""
    quote = (record.get("quote_span") or record.get("quote") or "").strip()
    locator = record.get("locator") or ""
    bits = [str(who)]
    if title:
        bits.append(f"“{title}.”")
    if date:
        bits.append(str(date) + ".")
    if locator:
        bits.append(locator + ".")
    indexed = is_indexed_excerpt_source(
        source_url=url, source_ref=record.get("source_ref")
    )
    if url:
        bits.append(url)
    if indexed:
        bits.append("(CiteAlpha indexed excerpt — verify in company filings)")
    elif record.get("source_verified") is False:
        bits.append("(quote not verified on external page — see indexed document)")
    if cid:
        bits.append(f"({cid})")
    line = " ".join(bits)
    if quote:
        return f"{line} Quote: “{quote}”"
    return line


def format_markdown(record: Dict[str, Any]) -> str:
    n = record.get("n")
    prefix = f"[{n}] " if n is not None else ""
    title = record.get("title") or "Source"
    url = record.get("source_url") or record.get("url") or ""
    cid = record.get("citation_id") or ""
    quote = (record.get("quote_span") or record.get("quote") or "").strip()
    loc = record.get("locator") or ""
    date = record.get("date") or ""
    ticker = record.get("ticker") or ""
    link = f"[{title}]({url})" if url else title
    extra = " · ".join(x for x in (ticker, date, loc, cid) if x)
    md = f"{prefix}{link}"
    if extra:
        md += f" — {extra}"
    if quote:
        md += f"\n> {quote}"
    return md


def format_ic_footnote(record: Dict[str, Any]) -> str:
    """Short IC footnote: ticker, period/metric, citation id, URL."""
    ticker = record.get("ticker") or record.get("company_id") or ""
    loc = record.get("locator") or ""
    cid = record.get("citation_id") or ""
    url = record.get("source_url") or record.get("url") or ""
    n = record.get("n")
    head = f"[{n}] " if n is not None else ""
    return f"{head}{ticker} {loc} {cid} {url}".strip()


def citation_record(
    *,
    citation_id: Optional[str],
    company_id: Optional[str] = None,
    ticker: Optional[str] = None,
    name: Optional[str] = None,
    title: Optional[str] = None,
    date: Optional[str] = None,
    source_url: Optional[str] = None,
    url: Optional[str] = None,
    quote: Optional[str] = None,
    quote_span: Optional[str] = None,
    speaker: Optional[str] = None,
    doc_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    period: Optional[str] = None,
    metric: Optional[str] = None,
    span_start: Optional[int] = None,
    span_end: Optional[int] = None,
    citeable: bool = False,
    cite_reason: Optional[str] = None,
    n: Optional[int] = None,
    kind: str = "outcome",
    snippet: Optional[str] = None,
    score: Optional[float] = None,
    guided_value: Optional[float] = None,
    guided_low: Optional[float] = None,
    guided_high: Optional[float] = None,
    actual_value: Optional[float] = None,
    label: Optional[str] = None,
    delta_pct: Optional[float] = None,
    source_ref: Optional[str] = None,
    as_of: Optional[str] = None,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """Canonical citation object for API + UI."""
    href = (source_url or url or "").strip() or None
    q = (quote_span or quote or snippet or "").strip() or None
    locator = locator_for(
        period=period, metric=metric, span_start=span_start, span_end=span_end, doc_id=doc_id
    )
    rec: Dict[str, Any] = {
        "citation_id": citation_id,
        "kind": kind,
        "n": n,
        "company_id": company_id,
        "ticker": ticker,
        "name": name,
        "title": title,
        "date": date or as_of,
        "as_of": as_of or date,
        "source_url": href,
        "url": href,
        "source_ref": source_ref,
        "quote": q,
        "quote_span": q,
        "speaker": speaker,
        "doc_id": doc_id,
        "doc_type": doc_type,
        "period": period,
        "metric": metric,
        "span_start": span_start,
        "span_end": span_end,
        "locator": locator,
        "citeable": bool(citeable),
        "cite_reason": cite_reason,
        "data_quality": data_quality,
        "retrieved_at": _utc_now(),
        "score": score,
        "guided_value": guided_value,
        "guided_low": guided_low,
        "guided_high": guided_high,
        "actual_value": actual_value,
        "label": label,
        "delta_pct": delta_pct,
        "permalink": f"/c/{citation_id}" if citation_id else None,
        "indexed_excerpt": is_indexed_excerpt_source(source_url=href, source_ref=source_ref),
        "highlight_url": external_highlight_url(
            source_url=href, source_ref=source_ref, quote=q
        ),
    }
    rec["bibliographic"] = bibliographic_line(rec)
    rec["markdown"] = format_markdown(rec)
    rec["ic_footnote"] = format_ic_footnote(rec)
    # Comprehensive evidence paragraph for dossiers / exports
    band = ""
    if guided_low is not None and guided_high is not None:
        band = f" guided band {guided_low}–{guided_high}"
    elif guided_value is not None:
        band = f" guided {guided_value}"
    act = f" actual {actual_value}" if actual_value is not None else ""
    lab = f" ({label})" if label else ""
    rec["evidence_summary"] = (
        f"{ticker or company_id} {period} {metric}{band}{act}{lab}. "
        f"{'Citeable.' if citeable else f'Not externally citeable ({cite_reason}).'}"
    ).strip()
    return rec


def outcome_to_citation(
    outcome: Any,
    *,
    company_id: str,
    ticker: Optional[str] = None,
    name: Optional[str] = None,
    data_quality: str = "hand_labeled",
    n: Optional[int] = None,
) -> Dict[str, Any]:
    def _get(key: str) -> Any:
        if isinstance(outcome, dict):
            return outcome.get(key)
        return getattr(outcome, key, None)

    cite = enrich_outcome_citation(outcome, company_id=company_id, data_quality=data_quality)
    period = str(_get("period") or "")
    metric = str(_get("metric") or "")
    title = f"{ticker or company_id} {period} {metric.replace('_', ' ')}".strip()
    label = _get("label")
    delta = _get("delta_pct")
    try:
        from app.services.gci_scoring import GuidanceOutcome, classify_outcome, delta_pct as gci_delta

        if not isinstance(outcome, dict):
            if label is None:
                label = classify_outcome(outcome)
            if delta is None:
                gv = _get("guided_value")
                av = _get("actual_value")
                if gv is not None:
                    delta = gci_delta(float(gv), None if av is None else float(av))
        elif label is None:
            # dict path — best-effort via GuidanceOutcome if fields allow
            pass
    except Exception:
        pass
    lab_s = label
    if hasattr(label, "value"):
        lab_s = label.value
    elif label is not None:
        lab_s = str(label)
    resolved_url = resolve_outcome_source_url(
        company_id, _get("source_url"), _get("source_ref")
    )
    return citation_record(
        citation_id=cite.get("citation_id"),
        company_id=company_id,
        ticker=ticker,
        name=name,
        title=title,
        date=_get("as_of"),
        as_of=_get("as_of"),
        source_url=resolved_url,
        source_ref=_get("source_ref"),
        quote_span=cite.get("quote_span") or _get("quote_span"),
        speaker=_get("speaker"),
        doc_id=cite.get("doc_id"),
        doc_type="guidance_outcome",
        period=period,
        metric=metric,
        span_start=cite.get("span_start"),
        span_end=cite.get("span_end"),
        citeable=bool(cite.get("citeable")),
        cite_reason=cite.get("cite_reason"),
        data_quality=data_quality,
        n=n,
        kind="outcome",
        guided_value=_get("guided_value"),
        guided_low=_get("guided_low"),
        guided_high=_get("guided_high"),
        actual_value=_get("actual_value"),
        label=lab_s,
        delta_pct=delta,
    )


def document_to_citation(doc: Dict[str, Any], *, n: Optional[int] = None) -> Dict[str, Any]:
    company_id = str(doc.get("company_id") or "")
    doc_id = str(doc.get("id") or doc.get("doc_id") or "")
    url = doc.get("url") or doc.get("source_url")
    snippet = doc.get("snippet") or (doc.get("body") or "")[:280]
    title = doc.get("title") or "Document"
    date = doc.get("date")
    cid = citation_id_for(
        company_id=company_id,
        period=str(date or ""),
        metric=str(doc.get("doc_type") or "document"),
        source_url=url,
        quote_span=snippet[:80] if snippet else None,
        doc_id=doc_id,
    )
    s, e = span_offsets(doc.get("body") or "", snippet)
    return citation_record(
        citation_id=cid,
        company_id=company_id,
        ticker=doc.get("ticker"),
        name=doc.get("name"),
        title=title,
        date=date,
        source_url=url,
        quote=snippet,
        speaker=doc.get("source"),
        doc_id=doc_id,
        doc_type=doc.get("doc_type"),
        period=date,
        metric=doc.get("doc_type"),
        span_start=s,
        span_end=e,
        citeable=bool(url and snippet),
        cite_reason="ok" if (url and snippet) else "missing_source",
        n=n,
        kind="document",
        snippet=snippet,
        score=doc.get("score"),
    )


def lookup_citation(citation_id: str) -> Optional[Dict[str, Any]]:
    """Resolve a cite_* id against GCI outcomes, then document store."""
    cid = (citation_id or "").strip()
    if not cid:
        return None
    from app.data.seed import get_data
    from app.services import repository
    from app.services.research import build_documents

    for c in get_data().get("companies", []):
        quality = str(c.get("data_quality") or "")
        if quality not in ("hand_labeled", "demo_structured"):
            continue
        try:
            detail = repository.get_company_gci(c["id"])
        except Exception:
            continue
        for o in detail.outcomes:
            if o.citation_id == cid:
                rec = outcome_to_citation(
                    o,
                    company_id=detail.id,
                    ticker=detail.ticker,
                    name=detail.name,
                    data_quality=detail.data_quality,
                )
                rec["found"] = True
                return attach_source_document(rec)
    for d in build_documents():
        rec = document_to_citation(d)
        if rec.get("citation_id") == cid or rec.get("doc_id") == cid:
            rec["found"] = True
            return attach_source_document(rec)
    return None


def list_company_citations(company_id: str, *, citeable_only: bool = True) -> List[Dict[str, Any]]:
    from app.services import repository

    detail = repository.get_company_gci(company_id)
    rows: List[Dict[str, Any]] = []
    n = 0
    for o in detail.outcomes:
        if citeable_only and not o.citeable:
            continue
        n += 1
        rows.append(
            outcome_to_citation(
                o,
                company_id=detail.id,
                ticker=detail.ticker,
                name=detail.name,
                data_quality=detail.data_quality,
                n=n,
            )
        )
    return rows


def outcome_is_citeable(row: Dict[str, Any]) -> bool:
    if "citeable" in row:
        return bool(row["citeable"])
    citeable, _ = assess_citeability(
        data_quality=str(row.get("data_quality") or ""),
        source_url=row.get("source_url"),
        quote_span=row.get("quote_span"),
        doc_id=row.get("doc_id"),
    )
    return citeable
