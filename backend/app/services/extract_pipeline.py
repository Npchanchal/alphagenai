"""Extract guidance from accepted filings and persist outcome shells.

Never invents an actual. A number publishes only after dual citation + bind
gates, and only when company quality is scoreable (hand_labeled or
extracted_verified).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.data import doc_store
from app.data.seed import get_data, save_data
from app.data.store_lock import locked
from app.services.matching import match_actuals
from app.services.score_policy import EXTRACTED_VERIFIED, is_dual_cited, is_scoreable

# The model reads one chunk per call; a transcript's Q&A and an annual
# report's outlook sit far past the first chunk.
CHUNK_CHARS = 12000
CHUNK_OVERLAP = 1000
MAX_CHUNKS_PER_DOC = 30
EXTRACT_ENGINE = "llm_v1"

# Daily call count and the chunks already read, persisted so a restart neither
# resets the cap nor re-sends a chunk.
_LEDGER: Optional[Dict[str, Any]] = None


def llm_daily_cap() -> int:
    return int(os.environ.get("INTELLENS_EXTRACT_LLM_DAILY_CAP", "50"))


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ledger_path() -> Optional[Path]:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(override) / "llm_extract_ledger.json" if override else None


def _ledger() -> Dict[str, Any]:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = {"day": "", "used": 0, "seen": {}}
        path = _ledger_path()
        if path is not None and path.exists():
            try:
                _LEDGER.update(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
    if _LEDGER.get("day") != _today():
        _LEDGER["day"] = _today()
        _LEDGER["used"] = 0
    return _LEDGER


@locked
def _save_ledger() -> None:
    path = _ledger_path()
    if path is None or _LEDGER is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_LEDGER), encoding="utf-8")
    os.replace(tmp, path)


def _llm_budget_ok() -> bool:
    return int(_ledger()["used"]) < llm_daily_cap()


@locked
def note_llm_use() -> None:
    _ledger()["used"] = int(_ledger()["used"]) + 1
    _save_ledger()


def llm_budget_used() -> int:
    return int(_ledger()["used"])


def reset_llm_budget() -> None:
    global _LEDGER
    _LEDGER = None


def text_chunks(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text or ""
    if len(text) <= size:
        return [text] if text.strip() else []
    step = size - overlap
    return [text[i : i + size] for i in range(0, len(text) - overlap, step)][:MAX_CHUNKS_PER_DOC]


def _chunk_key(company_id: str, chunk: str) -> str:
    return hashlib.sha1(f"{EXTRACT_ENGINE}|{company_id}|{chunk}".encode("utf-8")).hexdigest()[:20]


def _extract_doc(text: str, *, company_id: str, period: str, source_ref: str) -> tuple:
    """Rows from one document, chunk by chunk. Returns (rows, llm_calls, chunks_skipped)."""
    from app.services import llm_client
    from app.services.extraction import extract_auto, extract_guidance
    from app.services.feature_flags import llm_extract_enabled

    if not (llm_extract_enabled() and llm_client.llm_configured()):
        return extract_auto(text, company_id=company_id, period=period, source_ref=source_ref), 0, 0
    seen = _ledger()["seen"]
    rows: List[Dict[str, Any]] = []
    calls = skipped = 0
    for chunk in text_chunks(text):
        key = _chunk_key(company_id, chunk)
        if key in seen:
            skipped += 1
            continue
        if _llm_budget_ok():
            calls += 1
            note_llm_use()
            try:
                rows.extend(
                    llm_client.extract_guidance_via_llm(
                        chunk, company_id=company_id, period=period, source_ref=source_ref
                    )
                )
                seen[key] = _today()
                _save_ledger()
                continue
            except Exception:  # noqa: BLE001 — a failed call is retried on a later run
                pass
        for row in extract_guidance(chunk, company_id=company_id, period=period, source_ref=source_ref):
            row["extract_engine"] = "llm_fallback_heuristic"
            row["needs_review"] = True
            row["confidence"] = min(float(row.get("confidence", 0.7)), 0.75)
            rows.append(row)
    return rows, calls, skipped


def _overlay_path() -> Optional[Path]:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    if not override:
        return None
    base = Path(override)
    base.mkdir(parents=True, exist_ok=True)
    return base / "extracted_outcomes.json"


def apply_extracted_outcomes(data: Dict[str, Any]) -> None:
    path = _overlay_path()
    if path is None or not path.exists() or not isinstance(data, dict):
        return
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    outcomes = data.setdefault("outcomes", {})
    companies = data.setdefault("companies", [])
    have = {c.get("id") for c in companies}
    for company_id, rows in (blob.get("outcomes") or {}).items():
        if isinstance(rows, list):
            outcomes[company_id] = rows
    for row in blob.get("companies") or []:
        if row.get("id") and row["id"] not in have:
            companies.append(row)
            have.add(row["id"])


@locked
def _save_overlay(company_ids: List[str]) -> None:
    path = _overlay_path()
    if path is None or not company_ids:
        return
    blob: Dict[str, Any] = {"outcomes": {}, "companies": []}
    if path.exists():
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blob = {"outcomes": {}, "companies": []}
    stored = get_data()
    outcomes = blob.setdefault("outcomes", {})
    for company_id in company_ids:
        outcomes[company_id] = (stored.get("outcomes") or {}).get(company_id) or []
    have = {c.get("id") for c in blob.setdefault("companies", [])}
    for c in stored.get("companies") or []:
        if c.get("id") in company_ids and c["id"] not in have:
            blob["companies"].append(c)
            have.add(c["id"])
    path.write_text(json.dumps(blob) + "\n", encoding="utf-8")


@locked
def ensure_company_record(company_id: str) -> Optional[Dict[str, Any]]:
    data = get_data()
    for c in data["companies"]:
        if c["id"] == company_id:
            return c
    from app.data.india_listings import find_listing
    from app.data.us_listings import find_world_listing

    listing = find_listing(company_id) or find_world_listing(company_id)
    if listing is None:
        return None
    row = {
        "id": listing["id"],
        "name": listing["name"],
        "ticker": listing["ticker"],
        "sector": listing.get("sector") or "Equity",
        "data_quality": "listing_provisional",
    }
    if listing.get("market_id") and listing["market_id"] != "IN":
        row["market_id"] = listing["market_id"]
        row["cik"] = listing.get("cik")
    data["companies"].append(row)
    data.setdefault("outcomes", {}).setdefault(company_id, [])
    save_data()
    return row


def _accepted_docs(company_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for doc in doc_store.list_documents(company_id=company_id):
        if doc.get("review_status") not in (None, "accepted"):
            continue
        text = doc.get("text") or ""
        if doc.get("source") == "hand_labeled_period_pack":
            continue
        if "auto corpus pack" in text.lower():
            continue
        if len(text.strip()) < 40:
            continue
        out.append(doc)
    return out


def _row_key(row: Dict[str, Any]) -> tuple:
    return (str(row.get("period") or ""), str(row.get("metric") or ""))


@locked
def upsert_guidance_rows(company_id: str, statements: List[Dict[str, Any]]) -> int:
    """Append extracted guidance shells. Does not write an actual."""
    if not statements:
        return 0
    data = get_data()
    existing = data.setdefault("outcomes", {}).setdefault(company_id, [])
    have = {_row_key(r) for r in existing}
    added = 0
    for stmt in statements:
        row = dict(stmt)
        row["actual_value"] = None
        row.setdefault("period", "FY26")
        row.setdefault("company_id", company_id)
        key = _row_key(row)
        if key in have:
            continue
        existing.append(row)
        have.add(key)
        added += 1
    if added:
        save_data()
        _save_overlay([company_id])
    return added


def extract_company(
    company_id: str,
    *,
    period: str = "FY26",
    persist: bool = True,
) -> Dict[str, Any]:
    ensure_company_record(company_id)
    docs = _accepted_docs(company_id)
    found: List[Dict[str, Any]] = []
    llm_calls = chunks_skipped = 0
    for doc in docs:
        rows, calls, skipped = _extract_doc(
            doc.get("text") or "",
            company_id=company_id,
            period=doc.get("period") or period,
            source_ref=doc.get("source") or "exchange_filing",
        )
        llm_calls += calls
        chunks_skipped += skipped
        for row in rows:
            row["guidance_source_url"] = doc.get("url")
            row["guidance_quote"] = row.get("guided_text") or row.get("quote_span")
            row["guidance_as_of"] = doc.get("date")
            row["guidance_source_ref"] = doc.get("title")
            found.append(row)
    added = upsert_guidance_rows(company_id, found) if persist else 0
    return {
        "company_id": company_id,
        "docs": len(docs),
        "extracted": len(found),
        "added": added,
        "llm": llm_calls > 0,
        "llm_calls": llm_calls,
        "chunks_already_read": chunks_skipped,
    }


@locked
def match_company_actuals(company_id: str, actuals: List[Dict[str, Any]]) -> int:
    """Fill actuals only from caller-supplied reported figures (never invented)."""
    data = get_data()
    existing = data.setdefault("outcomes", {}).setdefault(company_id, [])
    matched = match_actuals(existing, actuals)
    changed = 0
    for i, row in enumerate(matched):
        if row.get("match_status") == "matched" and existing[i].get("actual_value") is None:
            existing[i]["actual_value"] = row["actual_value"]
            changed += 1
    if changed:
        save_data()
        _save_overlay([company_id])
    return changed


@locked
def relabel_copied_guidance(company_id: str) -> int:
    """Replace guided==actual copies when a later-or-prior filing has a distinct band."""
    from app.services.guidance_review import _promise_distinct, bind_from_documents

    data = get_data()
    rows = data.setdefault("outcomes", {}).setdefault(company_id, [])
    docs = _accepted_docs(company_id)
    if not docs:
        return 0
    from app.services.extraction import extract_guidance

    company = next((c for c in data.get("companies") or [] if c["id"] == company_id), None)
    joined = " ".join(d.get("text") or "" for d in docs)
    by_period: Dict[str, List[Dict[str, Any]]] = {}
    changed = 0
    for row in rows:
        if row.get("actual_value") is None:
            continue
        if _promise_distinct(row):
            continue
        period = str(row.get("period") or "FY26")
        # Rule-based on purpose: a probe per copied row would otherwise be one
        # uncapped model call each, every run. The band is re-bound to filing text below.
        if period not in by_period:
            by_period[period] = extract_guidance(
                joined, company_id=company_id, period=period, source_ref="relabel"
            )
        for stmt in by_period[period]:
            if stmt.get("metric") != row.get("metric"):
                continue
            probe = dict(row)
            probe["guided_value"] = stmt.get("guided_value")
            probe["guided_low"] = stmt.get("guided_low")
            probe["guided_high"] = stmt.get("guided_high")
            if not _promise_distinct(probe):
                continue
            row["guided_value"] = probe["guided_value"]
            row["guided_low"] = probe["guided_low"]
            row["guided_high"] = probe["guided_high"]
            row["guided_text"] = stmt.get("guided_text") or row.get("guided_text")
            bind_from_documents(row, docs, company=company, outcomes=rows)
            changed += 1
            break
    if changed:
        save_data()
        _save_overlay([company_id])
    return changed


@locked
def maybe_promote_extracted(company_id: str) -> Optional[str]:
    """Promote listing_provisional → extracted_verified when a dual-cited row exists."""
    data = get_data()
    company = next((c for c in data.get("companies") or [] if c["id"] == company_id), None)
    if company is None:
        return None
    quality = company.get("data_quality") or ""
    if quality == "hand_labeled":
        return quality
    rows = (data.get("outcomes") or {}).get(company_id) or []
    ok = False
    for row in rows:
        if not is_dual_cited(row):
            continue
        if not str(row.get("reviewed_by") or "").strip():
            continue
        if row.get("source_verified") is False:
            continue
        ok = True
        break
    if not ok:
        return quality
    if quality != EXTRACTED_VERIFIED:
        company["data_quality"] = EXTRACTED_VERIFIED
        save_data()
        _save_overlay([company_id])
    return EXTRACTED_VERIFIED


def run_extract_cohort(
    company_ids: List[str],
    *,
    persist: bool = True,
    relabel: bool = True,
    bind: bool = True,
) -> Dict[str, Any]:
    from app.services.guidance_review import bind_from_documents

    reports = []
    added = 0
    relabeled = 0
    bound = 0
    promoted = 0
    data = get_data()
    for cid in company_ids:
        ensure_company_record(cid)
        report = extract_company(cid, persist=persist)
        added += int(report.get("added") or 0)
        if relabel:
            relabeled += relabel_copied_guidance(cid)
        if bind:
            company = next((c for c in data.get("companies") or [] if c["id"] == cid), None)
            rows = (get_data().get("outcomes") or {}).get(cid) or []
            docs = _accepted_docs(cid)
            for row in rows:
                if bind_from_documents(row, docs, company=company, outcomes=rows):
                    bound += 1
            if persist and bound:
                save_data()
                _save_overlay([cid])
        if maybe_promote_extracted(cid) == EXTRACTED_VERIFIED:
            promoted += 1
        reports.append(report)
    return {
        "ok": True,
        "companies": len(company_ids),
        "added": added,
        "relabeled": relabeled,
        "bound": bound,
        "promoted": promoted,
        "results": reports,
    }


def is_extracted_scoreable(data_quality: Optional[str]) -> bool:
    return is_scoreable(data_quality)
