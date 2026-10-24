"""Scheduled GCI data refresh — live IR crawl, extract queue, optional FMP warm.

Runs every INTELLENS_REFRESH_HOURS (default 6). Does NOT auto-commit into GCI;
new docs/statements stay pending for analyst review.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.data import doc_store
from app.services.crawl import load_state, run_sensex_ir_crawl, save_state
from app.services.extraction import extract_auto
from app.services.repository import save_pending_extract


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on")


def refresh_interval_hours() -> float:
    try:
        return max(0.25, float(os.environ.get("INTELLENS_REFRESH_HOURS", "6")))
    except ValueError:
        return 6.0


def run_gci_refresh(
    *,
    limit: int = 30,
    live: Optional[bool] = None,
    auto_extract: Optional[bool] = None,
    warm_fmp: Optional[bool] = None,
) -> Dict[str, Any]:
    live_run = _flag("INTELLENS_CRAWL_LIVE", True) if live is None else live
    do_extract = (
        _flag("INTELLENS_AUTO_EXTRACT_ON_REFRESH", True)
        if auto_extract is None
        else auto_extract
    )
    do_fmp = _flag("INTELLENS_WARM_FMP_ON_REFRESH", True) if warm_fmp is None else warm_fmp

    crawl = run_sensex_ir_crawl(limit=limit, dry_run=False, live=live_run)

    extract_report: List[Dict[str, Any]] = []
    extracted_batches = 0
    if do_extract:
        # Prefer newly crawled company_ids; else any with pending docs
        new_ids = [
            r["company_id"]
            for r in crawl.get("results", [])
            if not r.get("deduped") and r.get("doc_id") and r.get("action") != "failed"
        ]
        if not new_ids:
            new_ids = list((crawl.get("pending_by_company") or {}).keys())[:limit]

        for cid in new_ids:
            docs = [
                d
                for d in doc_store.list_documents(company_id=cid)
                if d.get("review_status") == "pending"
            ]
            if not docs:
                continue
            # Newest pending doc by date / order
            doc = docs[-1]
            text = (doc.get("text") or "").strip()
            if len(text) < 40:
                continue
            stmts = extract_auto(text, company_id=cid, period="FY26")
            if not stmts:
                extract_report.append(
                    {"company_id": cid, "doc_id": doc["doc_id"], "statements": 0}
                )
                continue
            batch = save_pending_extract(cid, stmts)
            extracted_batches += 1
            extract_report.append(
                {
                    "company_id": cid,
                    "doc_id": doc["doc_id"],
                    "statements": len(stmts),
                    "extract_id": batch.get("id"),
                }
            )

    fmp_report: Dict[str, Any] = {"warmed": 0, "skipped": True}
    if do_fmp:
        fmp_report = _warm_fmp_cache()

    report: Dict[str, Any] = {
        "ok": True,
        "live": live_run,
        "interval_hours": refresh_interval_hours(),
        "crawl": {
            "targets": crawl.get("targets"),
            "pending_new": crawl.get("pending_new"),
            "pending_total": crawl.get("pending_total"),
            "fetched": crawl.get("fetched"),
            "catalog": crawl.get("catalog"),
            "failed": crawl.get("failed"),
            "as_of": crawl.get("as_of"),
        },
        "extract": {
            "enabled": do_extract,
            "batches": extracted_batches,
            "details": extract_report[:30],
        },
        "fmp": fmp_report,
        "note": (
            "Refresh keeps IR + extract queue fresh. "
            "Analysts must Accept in Desk before statements enter GCI."
        ),
    }

    try:
        from app.services.score_sla import record_filings_from_crawl

        report["filings_recorded"] = record_filings_from_crawl(crawl)
    except Exception as exc:  # noqa: BLE001 — refresh must not die on SLA log
        report["filings_recorded"] = {"ok": False, "error": type(exc).__name__}

    try:
        from app.services.source_verify import maybe_run_nightly_verify

        verify_report = maybe_run_nightly_verify(write=True, live=live_run)
        if verify_report:
            report["source_verification"] = {
                "checked": verify_report.get("checked"),
                "verified": verify_report.get("verified"),
                "failed": verify_report.get("failed"),
                "as_of": verify_report.get("as_of"),
            }
    except Exception as exc:  # noqa: BLE001 — refresh must not die on verify
        report["source_verification"] = {"ok": False, "error": type(exc).__name__}

    try:
        from app.services import event_filings

        if event_filings.enabled():
            from app.services.agent import monitors as _mon

            covered: list = []
            for m in _mon.list_monitors():
                covered += [c for c in _mon.companies_for(m) if c not in covered]
            done = [event_filings.ingest_events(c) for c in covered[:15]]
            report["analyst_event_filings"] = {
                "companies": len(done),
                "ingested": sum(1 for d in done for r in d["results"] if r.get("action") == "upserted"),
            }
    except Exception as exc:  # noqa: BLE001 — refresh must not die on event discovery
        report["analyst_event_filings"] = {"ok": False, "error": type(exc).__name__}

    try:
        from app.services.feature_flags import analyst_monitors_enabled

        if analyst_monitors_enabled():
            from app.services.agent.monitors import process_new_documents

            mon = process_new_documents()
            report["analyst_monitors"] = {
                k: mon.get(k) for k in ("baselined", "processed", "pending")
            } | {"runs": len(mon.get("runs") or [])}
    except Exception as exc:  # noqa: BLE001 — refresh must not die on monitors
        report["analyst_monitors"] = {"ok": False, "error": type(exc).__name__}

    try:
        from app.services.feature_flags import analyst_monitors_enabled

        if analyst_monitors_enabled():
            from app.services.agent.digest import send_due_digests

            report["analyst_digest"] = send_due_digests()
    except Exception as exc:  # noqa: BLE001 — refresh must not die on digests
        report["analyst_digest"] = {"ok": False, "error": type(exc).__name__}

    state = load_state()
    state["last_refresh"] = {
        "as_of": crawl.get("as_of"),
        "live": live_run,
        "pending_new": crawl.get("pending_new"),
        "extract_batches": extracted_batches,
        "interval_hours": refresh_interval_hours(),
    }
    save_state(state)
    return report


def _warm_fmp_cache() -> Dict[str, Any]:
    from app.data.market_history import get_index_history, get_stock_history
    from app.services import fmp_client

    if not fmp_client.enabled():
        return {"warmed": 0, "skipped": True, "reason": "no_api_key"}

    warmed = 0
    errors: List[str] = []
    for ix in ("SPX", "DJI", "NDX", "SENSEX", "NIFTY50"):
        try:
            row = get_index_history(ix, years=5)
            if row and row.get("kind") == "fmp_eod":
                warmed += 1
        except Exception as e:
            errors.append(f"{ix}:{e}"[:120])
    for sid in ("us_aapl", "us_msft", "infy"):
        try:
            row = get_stock_history(sid, years=5)
            if row and row.get("kind") == "fmp_eod":
                warmed += 1
        except Exception as e:
            errors.append(f"{sid}:{e}"[:120])
    return {"warmed": warmed, "skipped": False, "errors": errors[:5]}
