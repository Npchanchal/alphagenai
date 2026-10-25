"""Phase 2 — document store (JSON-backed) with content-hash dedupe.

With ``INTELLENS_DATA_DIR`` set, long filing text lives in one file per
document under ``doc_text/``; ``documents.json`` keeps metadata and a preview.
Per-company and single-document reads return the full text; corpus-wide
listings return the preview so memory stays bounded.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.data.store_lock import locked

_PACKAGED = Path(__file__).with_name("documents.json")
_PATH = _PACKAGED
_DOCS: Optional[Dict[str, Any]] = None


def _overlay_path() -> Optional[Path]:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "documents.json" if env else None


def _write_path() -> Path:
    return _overlay_path() or _PACKAGED


EXTERNAL_TEXT_MIN = 4000
PREVIEW_CHARS = 4000
_TEXT_CACHE: "OrderedDict[str, str]" = OrderedDict()
_TEXT_CACHE_MAX = 64


def _text_dir() -> Optional[Path]:
    overlay = _overlay_path()
    return overlay.parent / "doc_text" if overlay else None


def _externalise(doc: Dict[str, Any]) -> bool:
    """Move long inline text to its own file. Returns True when the doc changed."""
    root = _text_dir()
    text = doc.get("text") or ""
    if root is None or doc.get("text_file") or len(text) <= EXTERNAL_TEXT_MIN:
        return False
    root.mkdir(parents=True, exist_ok=True)
    name = f"{doc.get('content_hash') or content_hash(text)}.txt"
    target = root / name
    if not target.exists():
        tmp = target.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    doc["text_file"] = name
    doc["text_chars"] = len(text)
    doc["text"] = text[:PREVIEW_CHARS]
    return True


def _read_text(name: str) -> Optional[str]:
    if name in _TEXT_CACHE:
        _TEXT_CACHE.move_to_end(name)
        return _TEXT_CACHE[name]
    root = _text_dir()
    if root is None or not (root / name).exists():
        return None
    text = (root / name).read_text(encoding="utf-8")
    _TEXT_CACHE[name] = text
    while len(_TEXT_CACHE) > _TEXT_CACHE_MAX:
        _TEXT_CACHE.popitem(last=False)
    return text


def _hydrate(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc or not doc.get("text_file"):
        return doc
    full = _read_text(str(doc["text_file"]))
    if full is None:
        return doc
    out = dict(doc)
    out["text"] = full
    return out


@locked
def _load() -> Dict[str, Any]:
    global _DOCS
    if _DOCS is None:
        overlay = _overlay_path()
        path = overlay if overlay and overlay.exists() else _PACKAGED
        if path.exists():
            _DOCS = json.loads(path.read_text())
        else:
            _DOCS = {"documents": [], "versions": []}
        if overlay is not None:
            moved = [_externalise(d) for d in _DOCS.get("documents") or []]
            if any(moved):
                save()
    return _DOCS


@locked
def save() -> None:
    data = _load()
    path = _write_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if _overlay_path() is not None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, separators=(",", ":")))
        os.replace(tmp, path)
    else:
        path.write_text(json.dumps(data, indent=2))


@locked
def reset_docs() -> None:
    global _DOCS
    _DOCS = {"documents": [], "versions": []}
    _TEXT_CACHE.clear()
    save()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


@locked
def upsert_document(
    *,
    company_id: str,
    doc_type: str,
    title: str,
    text: str,
    url: Optional[str] = None,
    date: str = "2025-01-01",
    source: str = "ingest",
    review_status: str = "pending",
    source_type: Optional[str] = None,
    period: Optional[str] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """``persist=False`` defers the index write; the caller must call ``save()``."""
    from app.data.source_policy import resolve_source_type

    store = _load()
    h = content_hash(text)
    for d in store["documents"]:
        if d.get("content_hash") == h and d.get("company_id") == company_id:
            return _hydrate(d)  # dedupe
    st = source_type or resolve_source_type(doc_type=doc_type, source=source)
    doc = {
        "doc_id": str(uuid4()),
        "company_id": company_id,
        "doc_type": doc_type,
        "title": title,
        "text": text,
        "url": url,
        "date": date,
        "source": source,
        "source_type": st,
        "period": period,
        "content_hash": h,
        "review_status": review_status,  # pending | accepted | rejected
        "version": 1,
        # Knowledge time. ``date`` is the filing date; a score may only use a
        # document from the moment we held it.
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    store["documents"].append(doc)
    store["versions"].append({"doc_id": doc["doc_id"], "version": 1, "hash": h})
    if _externalise(doc):
        _TEXT_CACHE[doc["text_file"]] = text
    if persist:
        save()
    return _hydrate(doc)


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Return one document by id, or None."""
    want = (doc_id or "").strip()
    if not want:
        return None
    for d in _load()["documents"]:
        if d.get("doc_id") == want:
            return _hydrate(d)
    return None


_META_KEYS = (
    "doc_id", "company_id", "doc_type", "title", "url", "date", "source_type",
    "period", "content_hash", "review_status", "version", "ingested_at",
)


def _meta(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: d.get(k) for k in _META_KEYS}


def document_meta(doc_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Metadata only (hash, dates, URL). No filing text is read."""
    want = (doc_id or "").strip()
    if not want:
        return None
    return next((_meta(d) for d in _load()["documents"] if d.get("doc_id") == want), None)


def find_by_hash(content_hash: str) -> Optional[Dict[str, Any]]:
    want = (content_hash or "").strip().lower()
    if len(want) != 64:
        return None
    return next((_meta(d) for d in _load()["documents"] if d.get("content_hash") == want), None)


_HOST_ALIASES = {
    "nsearchives.nseindia.com": "archives.nseindia.com",
    "beta.bseindia.com": "bseindia.com",
}


def url_key(url: Optional[str]) -> str:
    """One key per document: ignores scheme, www., archive-host aliases, #fragments, utm_ params."""
    from urllib.parse import urlparse

    raw = (url or "").strip()
    if not raw:
        return ""
    parts = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parts.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    host = _HOST_ALIASES.get(host, host)
    query = "&".join(
        sorted(q for q in parts.query.split("&") if q and not q.lower().startswith("utm_"))
    )
    path = parts.path.rstrip("/") or "/"
    return f"{host}{path}" + (f"?{query}" if query else "")


def find_by_url(url: Optional[str]) -> Optional[Dict[str, Any]]:
    """The stored document for this URL (any company), with full text, or None."""
    key = url_key(url)
    if not key:
        return None
    for d in _load()["documents"]:
        if d.get("url") and url_key(d["url"]) == key:
            return _hydrate(d)
    return None


_FILING_RANK = {"results": 0, "filing": 1, "ir_guidance": 2, "transcript": 3}


def recent_filings(limit: int = 8) -> List[Dict[str, Any]]:
    """Newest accepted filings, one row per source URL. Metric extracts are left out."""
    cap = max(1, min(int(limit or 8), 20))
    grouped: Dict[str, Dict[str, Any]] = {}
    for doc in _load()["documents"]:
        kind = str(doc.get("doc_type") or "")
        if doc.get("review_status") != "accepted" or kind not in _FILING_RANK:
            continue
        key = url_key(doc.get("url")) or str(doc.get("doc_id") or "")
        if not key:
            continue
        held = grouped.get(key)
        if held is None or _FILING_RANK[kind] < _FILING_RANK[str(held.get("doc_type") or "")]:
            grouped[key] = doc
    rows = list(grouped.values())
    rows.sort(key=lambda d: str(d.get("date") or d.get("ingested_at") or ""), reverse=True)
    return [_meta(d) for d in rows[:cap]]


def list_documents(
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    include_rejected: bool = False,
    hydrate: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Per-company lists carry full text; corpus-wide lists carry the preview."""
    if hydrate is None:
        hydrate = company_id is not None
    rows = _load()["documents"]
    out = []
    for d in rows:
        if not include_rejected and d.get("review_status") == "rejected":
            continue
        if company_id and d["company_id"] != company_id:
            continue
        if doc_type and d["doc_type"] != doc_type:
            continue
        out.append(_hydrate(d) if hydrate else d)
    return out


@locked
def set_review_status(doc_id: str, status: str) -> Dict[str, Any]:
    store = _load()
    for d in store["documents"]:
        if d["doc_id"] == doc_id:
            d["review_status"] = status
            save()
            return _hydrate(d)
    raise KeyError(doc_id)


@locked
def patch_document(doc_id: str, **fields: Any) -> Dict[str, Any]:
    """Update selected fields on an existing document (period, url, review_status…)."""
    store = _load()
    for d in store["documents"]:
        if d["doc_id"] == doc_id:
            for k, v in fields.items():
                if v is not None:
                    d[k] = v
            save()
            return _hydrate(d)
    raise KeyError(doc_id)


def seed_from_outcomes_and_transcripts() -> int:
    """Bootstrap store from GCI outcomes + sample transcripts (idempotent by hash)."""
    from app.data.seed import get_data
    from app.services.citations import span_offsets

    data = get_data()
    n = 0
    cos = {c["id"]: c for c in data["companies"]}
    for cid, rows in data.get("outcomes", {}).items():
        c = cos.get(cid, {})
        quality = c.get("data_quality") or "demo_structured"
        for o in rows:
            text = " ".join(
                filter(None, [o.get("guided_text"), o.get("quote_span"), o.get("source_ref")])
            )
            if not text.strip():
                continue
            status = "accepted" if quality == "hand_labeled" else "pending"
            doc = upsert_document(
                company_id=cid,
                doc_type="guidance",
                title=f"{o.get('period')} {o.get('metric')}",
                text=text,
                url=o.get("source_url"),
                date=o.get("as_of") or "2024-01-01",
                source=o.get("source_ref") or "outcome",
                review_status=status,
                period=o.get("period"),
            )
            if status == "accepted" and doc.get("review_status") != "accepted":
                doc = set_review_status(doc["doc_id"], "accepted")
            if not doc.get("period") and o.get("period"):
                doc = patch_document(doc["doc_id"], period=o.get("period"))
            start, end = span_offsets(doc.get("text") or text, o.get("quote_span"))
            if quality == "hand_labeled":
                o["doc_id"] = doc["doc_id"]
                if start is not None:
                    o["span_start"] = start
                    o["span_end"] = end
            n += 1
    for cid, text in data.get("sample_transcripts", {}).items():
        c = cos.get(cid, {})
        upsert_document(
            company_id=cid,
            doc_type="transcript",
            title=f"{c.get('ticker', cid)} sample concall",
            text=text,
            date="2025-04-18",
            source="sample_transcript",
            review_status="accepted" if c.get("data_quality") == "hand_labeled" else "pending",
            period="FY26",
        )
        n += 1
    from app.data.seed import save_data

    save_data()
    return n
