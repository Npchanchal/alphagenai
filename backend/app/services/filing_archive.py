"""Stored filings copied to S3, one bucket per exchange, and the platform-admin browser over them.

Buckets: NSE, BSE, and one for every other market (``intl``). Each document lands as
``text/<company>/<doc_type>/<date>_<hash16>.txt`` (the extracted body a model reads)
and, when the file as served was kept, ``raw/<company>/<doc_type>/<date>_<sha16>.<ext>``.

Reads ``doc_store`` only; never fetches an exchange, regulator or issuer host.
Uploads run outside ``store_lock``; the ledger write is the only step inside it.
"""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlparse

from app.data import doc_store
from app.data.store_lock import locked

EXCHANGES = ("nse", "bse", "intl")
EXCHANGE_LABELS = {"nse": "NSE", "bse": "BSE", "intl": "Other markets"}
_ENV = {"nse": "INTELLENS_FILING_S3_NSE", "bse": "INTELLENS_FILING_S3_BSE", "intl": "INTELLENS_FILING_S3_INTL"}

# Seeded outcome text and sample concalls are not filings.
_SKIP_TYPES = frozenset({"guidance", "guidance_outcome"})
_SKIP_SOURCES = frozenset({"sample_transcript", "ir_catalog"})

_LEDGER: Optional[Dict[str, Any]] = None
_RUN_GUARD = threading.Lock()
_STATE: Dict[str, Any] = {"running": False}


def buckets() -> Dict[str, str]:
    """Configured bucket per exchange. Empty when the archive is off."""
    out = {}
    for ex, env in _ENV.items():
        name = os.environ.get(env, "").strip()
        if name:
            out[ex] = name
    return out


def archivable(doc: Dict[str, Any]) -> bool:
    if doc.get("review_status") == "rejected":
        return False
    if doc.get("doc_type") in _SKIP_TYPES or doc.get("source") in _SKIP_SOURCES:
        return False
    return bool(doc.get("url") or doc.get("raw_sha256"))


@lru_cache(maxsize=50000)
def _company(company_id: str) -> Tuple[str, str, str, Optional[str]]:
    """``(market_id, name, ticker, listing exchange)`` for a company id."""
    from app.data.india_listings import find_listing
    from app.data.markets import company_market_id
    from app.data.us_listings import find_world_listing

    market = company_market_id({"id": company_id})
    row = (find_listing(company_id) if market == "IN" else find_world_listing(company_id)) or {}
    if not row and market == "IN":
        from app.data.seed import get_data

        row = next((c for c in get_data().get("companies") or [] if c.get("id") == company_id), {})
    return (
        market,
        str(row.get("name") or company_id),
        str(row.get("ticker") or company_id.upper()),
        row.get("exchange"),
    )


def exchange_for(doc: Dict[str, Any]) -> str:
    """``bse`` for a BSE-hosted file or a BSE-only issuer, ``nse`` for other Indian filings, else ``intl``."""
    host = (urlparse(str(doc.get("url") or "")).hostname or "").lower()
    if host == "bseindia.com" or host.endswith(".bseindia.com"):
        return "bse"
    if host == "nseindia.com" or host.endswith(".nseindia.com"):
        return "nse"
    market, _, _, listed = _company(str(doc.get("company_id") or ""))
    if market != "IN":
        return "intl"
    return "bse" if listed == "BSE" else "nse"


def _sniff(raw: bytes) -> Tuple[str, str]:
    head = raw.lstrip()[:16].lower()
    if head.startswith(b"%pdf-"):
        return "pdf", "application/pdf"
    if head.startswith((b"<!doctype", b"<html", b"<?xml", b"<")):
        return "html", "text/html; charset=utf-8"
    return "bin", "application/octet-stream"


def _stem(doc: Dict[str, Any]) -> str:
    company = str(doc.get("company_id") or "unknown")
    kind = str(doc.get("doc_type") or "filing")
    day = str(doc.get("date") or "")[:10] or "undated"
    return f"{company}/{kind}/{day}"


def text_key(doc: Dict[str, Any]) -> str:
    h = str(doc.get("content_hash") or doc.get("doc_id") or "")[:16]
    return f"text/{_stem(doc)}_{h}.txt"


def raw_key(doc: Dict[str, Any], ext: str) -> str:
    return f"raw/{_stem(doc)}_{str(doc.get('raw_sha256') or '')[:16]}.{ext}"


def _s3_metadata(doc: Dict[str, Any]) -> Dict[str, str]:
    """S3 user metadata is ASCII; the URL and title are percent-encoded."""
    fields = {
        "doc-id": doc.get("doc_id"),
        "company-id": doc.get("company_id"),
        "doc-type": doc.get("doc_type"),
        "period": doc.get("period"),
        "filing-date": doc.get("date"),
        "public-available-at": doc.get("public_available_at"),
        "content-sha256": doc.get("content_hash"),
        "raw-sha256": doc.get("raw_sha256"),
        "source-url": doc.get("url"),
        "title": str(doc.get("title") or "")[:300],
    }
    return {k: quote(str(v), safe=":/?=&.-_ ") for k, v in fields.items() if v}


# --- ledger -----------------------------------------------------------------


def _ledger_path() -> Optional[Path]:
    base = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(base) / "filing_archive.json" if base else None


@locked
def _ledger() -> Dict[str, Any]:
    global _LEDGER
    if _LEDGER is None:
        path = _ledger_path()
        if path is not None and path.exists():
            _LEDGER = json.loads(path.read_text(encoding="utf-8"))
        else:
            _LEDGER = {"docs": {}, "runs": []}
    return _LEDGER


@locked
def _record(entries: Dict[str, Dict[str, Any]], run: Optional[Dict[str, Any]] = None) -> None:
    led = _ledger()
    led["docs"].update(entries)
    if run is not None:
        led["runs"] = (led.get("runs") or [])[-19:] + [run]
    path = _ledger_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(led, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def reset_ledger() -> None:
    global _LEDGER
    _LEDGER = None


def archived(doc_id: str) -> Optional[Dict[str, Any]]:
    return _ledger()["docs"].get(doc_id)


# --- upload pass --------------------------------------------------------------


def _s3_client() -> Any:
    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-south-1"
    return boto3.client("s3", region_name=region)


def _upload_one(client: Any, bucket: str, exchange: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    meta = _s3_metadata(doc)
    body = doc_store.document_text(doc).encode("utf-8")
    tkey = text_key(doc)
    client.put_object(
        Bucket=bucket, Key=tkey, Body=body, ContentType="text/plain; charset=utf-8", Metadata=meta
    )
    entry: Dict[str, Any] = {
        "bucket": bucket,
        "exchange": exchange,
        "text_key": tkey,
        "text_bytes": len(body),
        "raw_key": None,
        "content_hash": doc.get("content_hash"),
        "archived_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    raw = doc_store.raw_file(doc.get("raw_sha256"))
    if raw:
        ext, ctype = _sniff(raw)
        rkey = raw_key(doc, ext)
        client.put_object(Bucket=bucket, Key=rkey, Body=raw, ContentType=ctype, Metadata=meta)
        entry.update(raw_key=rkey, raw_bytes=len(raw), raw_content_type=ctype)
    return entry


def pending(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Archivable documents with no ledger entry, newest filing first."""
    held = _ledger()["docs"]
    rows = [
        d for d in doc_store.list_documents(hydrate=False)
        if d.get("doc_id") not in held and archivable(d)
    ]
    rows.sort(key=lambda d: str(d.get("date") or ""), reverse=True)
    return rows[:limit] if limit else rows


def archive_pending(
    *,
    limit: Optional[int] = None,
    dry_run: bool = False,
    client: Any = None,
    workers: int = 8,
    batch: int = 200,
) -> Dict[str, Any]:
    """Copy every stored filing not yet in S3. One pass at a time per process."""
    targets = buckets()
    if not targets:
        return {"status": "off", "reason": "no bucket configured"}
    if not _RUN_GUARD.acquire(blocking=False):
        return {"status": "already_running"}
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _STATE.update(running=True, started_at=started, uploaded=0, failed=0)
    try:
        todo = pending(limit)
        plan: List[Tuple[str, Dict[str, Any]]] = []
        skipped = 0
        for d in todo:
            ex = exchange_for(d)
            if ex in targets:
                plan.append((ex, d))
            else:
                skipped += 1
        if dry_run:
            by_ex: Dict[str, int] = {}
            for ex, _ in plan:
                by_ex[ex] = by_ex.get(ex, 0) + 1
            return {"status": "dry_run", "pending": len(plan), "by_exchange": by_ex, "no_bucket": skipped}
        s3 = client or _s3_client()
        uploaded = failed = 0
        errors: List[str] = []

        def one(item: Tuple[str, Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
            ex, doc = item
            try:
                return str(doc["doc_id"]), _upload_one(s3, targets[ex], ex, doc), None
            except Exception as exc:  # noqa: BLE001 — one bad object must not stop the pass
                return str(doc["doc_id"]), None, f"{type(exc).__name__}: {str(exc)[:160]}"

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            for start in range(0, len(plan), batch):
                done: Dict[str, Dict[str, Any]] = {}
                for doc_id, entry, err in pool.map(one, plan[start : start + batch]):
                    if entry is not None:
                        done[doc_id] = entry
                    else:
                        failed += 1
                        if len(errors) < 10:
                            errors.append(f"{doc_id}: {err}")
                uploaded += len(done)
                _record(done)
                _STATE.update(uploaded=uploaded, failed=failed)
        run = {
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "uploaded": uploaded,
            "failed": failed,
            "no_bucket": skipped,
        }
        _record({}, run)
        return {"status": "ok", **run, "errors": errors}
    finally:
        _STATE.update(running=False)
        _RUN_GUARD.release()


def start_background(limit: Optional[int] = None) -> Dict[str, Any]:
    if not buckets():
        return {"status": "off", "reason": "no bucket configured"}
    if _STATE.get("running"):
        return {"status": "already_running", **_STATE}
    threading.Thread(
        target=archive_pending, kwargs={"limit": limit}, name="filing-archive", daemon=True
    ).start()
    return {"status": "started"}


def _coverage_snapshot() -> Dict[str, Any]:
    """India walk progress for the admin archive page (lookback, budgets, last roll)."""
    try:
        from app.services.india_coverage import coverage_progress

        p = coverage_progress()
        roll = p.get("roll") or {}
        return {
            "cohort": p.get("cohort"),
            "cohort_size": p.get("cohort_size"),
            "nse_count": p.get("nse_count"),
            "bse_only_count": p.get("bse_only_count"),
            "discovery_since": p.get("discovery_since"),
            "lookback_reached": p.get("lookback_reached"),
            "lookback_remaining": p.get("lookback_remaining"),
            "extract_enabled": p.get("extract_enabled"),
            "searched_today": p.get("searched_today"),
            "roll_running": bool(roll.get("running")),
            "roll_done": roll.get("done"),
            "roll_total": roll.get("total"),
            "roll_current": roll.get("current"),
            "roll_finished_at": roll.get("finished_at"),
            "roll_stopped": roll.get("stopped"),
            "roll_started_at": roll.get("started_at"),
            "budgets_today": p.get("budgets_today"),
        }
    except Exception:
        return {}


def status() -> Dict[str, Any]:
    led = _ledger()
    runs = led.get("runs") or []
    interval = 7200
    try:
        interval = max(300, int(os.environ.get("INTELLENS_FILING_ARCHIVE_INTERVAL_SEC", "7200")))
    except ValueError:
        pass
    return {
        "configured": bool(buckets()),
        "buckets": [
            {"exchange": ex, "label": EXCHANGE_LABELS[ex], "bucket": buckets().get(ex)} for ex in EXCHANGES
        ],
        "archived": len(led["docs"]),
        "pending": len(pending()),
        "running": bool(_STATE.get("running")),
        "progress": {k: _STATE.get(k) for k in ("started_at", "uploaded", "failed")} if _STATE.get("running") else None,
        "last_run": runs[-1] if runs else None,
        "cron_interval_sec": interval,
        "coverage": _coverage_snapshot(),
    }


# --- admin browse ---------------------------------------------------------------


def _row(doc: Dict[str, Any], entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    market, name, ticker, _ = _company(str(doc.get("company_id") or ""))
    return {
        "doc_id": doc.get("doc_id"),
        "company_id": doc.get("company_id"),
        "name": name,
        "ticker": ticker,
        "market_id": market,
        "exchange": exchange_for(doc),
        "doc_type": doc.get("doc_type"),
        "title": doc.get("title"),
        "date": doc.get("date") or None,
        "period": doc.get("period"),
        "url": doc.get("url"),
        "source_type": doc.get("source_type"),
        "review_status": doc.get("review_status"),
        "chars": doc.get("text_chars") or len(str(doc.get("text") or "")),
        "has_original": bool(doc.get("raw_sha256")),
        "archived": entry is not None,
        "s3_text": f"s3://{entry['bucket']}/{entry['text_key']}" if entry else None,
        "s3_original": f"s3://{entry['bucket']}/{entry['raw_key']}" if entry and entry.get("raw_key") else None,
    }


def _matches(doc: Dict[str, Any], tokens: Iterable[str]) -> bool:
    _, name, ticker, _ = _company(str(doc.get("company_id") or ""))
    blob = " ".join(
        str(x or "")
        for x in (
            doc.get("company_id"), name, ticker, doc.get("title"), doc.get("url"),
            doc.get("period"), doc.get("doc_type"), doc.get("text"),
        )
    ).lower()
    return all(t in blob for t in tokens)


def browse(
    *,
    q: str = "",
    exchange: Optional[str] = None,
    doc_type: Optional[str] = None,
    company_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    in_s3: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Filter stored filings by company, exchange, type, date and words in the title or opening text."""
    tokens = [t for t in (q or "").lower().split() if t]
    held = _ledger()["docs"]
    base: List[Tuple[Dict[str, Any], str, bool]] = []
    for d in doc_store.list_documents(hydrate=False):
        if not archivable(d):
            continue
        if company_id and d.get("company_id") != company_id:
            continue
        day = str(d.get("date") or "")[:10]
        if date_from and (not day or day < date_from):
            continue
        if date_to and (not day or day > date_to):
            continue
        if tokens and not _matches(d, tokens):
            continue
        base.append((d, exchange_for(d), d.get("doc_id") in held))

    facets: Dict[str, Dict[str, int]] = {"exchange": {}, "doc_type": {}, "in_s3": {"yes": 0, "no": 0}}
    rows: List[Dict[str, Any]] = []
    for d, ex, is_held in base:
        kind = str(d.get("doc_type") or "")
        if (exchange is None or ex == exchange) and (in_s3 is None or is_held == in_s3):
            facets["doc_type"][kind] = facets["doc_type"].get(kind, 0) + 1
        if (doc_type is None or kind == doc_type) and (in_s3 is None or is_held == in_s3):
            facets["exchange"][ex] = facets["exchange"].get(ex, 0) + 1
        if (exchange is None or ex == exchange) and (doc_type is None or kind == doc_type):
            facets["in_s3"]["yes" if is_held else "no"] += 1
            if in_s3 is None or is_held == in_s3:
                rows.append(d)

    rows.sort(key=lambda d: (str(d.get("date") or ""), str(d.get("ingested_at") or "")), reverse=True)
    cap = max(1, min(int(limit or 50), 200))
    start = max(0, int(offset or 0))
    page = rows[start : start + cap]
    return {
        "total": len(rows),
        "offset": start,
        "limit": cap,
        "facets": facets,
        "documents": [_row(d, held.get(str(d.get("doc_id")))) for d in page],
        "archive": status(),
    }


def detail(doc_id: str) -> Optional[Dict[str, Any]]:
    doc = doc_store.get_document(doc_id)
    if doc is None:
        return None
    return {**_row(doc, archived(doc_id)), "text": doc.get("text") or "", "public_available_at": doc.get("public_available_at"), "ingested_at": doc.get("ingested_at")}


def original_file(
    doc_id: str, *, client_factory: Callable[[], Any] = _s3_client
) -> Optional[Tuple[bytes, str, str]]:
    """``(bytes, content type, file name)`` from the data volume, else from S3, else None."""
    meta = doc_store.document_meta(doc_id)
    if meta is None:
        return None
    raw = doc_store.raw_file(meta.get("raw_sha256"))
    entry = archived(doc_id)
    if raw is None and entry and entry.get("raw_key"):
        obj = client_factory().get_object(Bucket=entry["bucket"], Key=entry["raw_key"])
        raw = obj["Body"].read()
    if not raw:
        return None
    ext, ctype = _sniff(raw)
    name = f"{meta.get('company_id')}_{meta.get('doc_type')}_{(meta.get('date') or 'undated')[:10]}.{ext}"
    return raw, ctype, name
