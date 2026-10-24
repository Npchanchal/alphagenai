"""S&P 500 walk: SEC results releases since 2022 → read → reconcile → classify.

Same rules as India: a number only when both quotes are in the filings; a
company whose releases carry no numeric guidance says so in plain words.
Names whose last search did not reach back to the window start go first.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.data.store_lock import locked
from app.data.us_listings import find_us_listing, us_equity_universe
from app.services import disclosures, sec_filings
from app.services.coverage import (
    NO_QUANTIFIED_GUIDANCE,
    coverage_counts,
    load_coverage,
    note_discovery,
    published_status,
    stamp_coverage,
)

US_NO_GUIDANCE_REASON = "results_releases_no_metric_number"


def us_since() -> str:
    from app.services.exchange_filings import discovery_since

    return discovery_since()


@locked
def ensure_us_company(company_id: str, *, fiscal_year_end: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from app.data.seed import get_data, save_data
    from app.services.extract_pipeline import _save_overlay

    listing = find_us_listing(company_id)
    if listing is None:
        return None
    data = get_data()
    company = next((c for c in data["companies"] if c["id"] == company_id), None)
    changed = False
    if company is None:
        company = {
            "id": company_id,
            "name": listing["name"],
            "ticker": listing["ticker"],
            "sector": listing.get("sector") or "Equity",
            "data_quality": "listing_provisional",
            "market_id": "US",
            "cik": listing.get("cik"),
        }
        data["companies"].append(company)
        data.setdefault("outcomes", {}).setdefault(company_id, [])
        changed = True
    if fiscal_year_end and company.get("fiscal_year_end") != fiscal_year_end:
        company["fiscal_year_end"] = fiscal_year_end
        changed = True
    if changed:
        save_data()
        _save_overlay([company_id])
    return company


def _has_guidance(company_id: str) -> bool:
    from app.data.seed import get_data

    rows = (get_data().get("outcomes") or {}).get(company_id) or []
    return any(r.get("guided_value") is not None or r.get("guided_low") is not None for r in rows)


def process_company(
    company_id: str,
    *,
    extractor: Optional[disclosures.Extractor] = None,
    listing: Optional[Dict[str, Any]] = None,
    fetch: Any = None,
) -> Dict[str, Any]:
    row = find_us_listing(company_id)
    if row is None or not row.get("cik"):
        return {"company_id": company_id, "skipped": "no_cik"}
    since = us_since()
    ingest = sec_filings.ingest_company(
        company_id, row["cik"], ticker=row["ticker"], since=since, listing=listing, fetch=fetch
    )
    company = ensure_us_company(company_id, fiscal_year_end=ingest.get("fiscal_year_end"))
    read = disclosures.process_company(
        company_id,
        market_id="US",
        company_name=(company or row)["name"],
        fy_end_mmdd=(company or {}).get("fiscal_year_end") or ingest.get("fiscal_year_end"),
        extractor=extractor,
    )
    # "No numeric guidance" needs a full model read; the rule reader alone is too narrow to say so.
    complete = (
        bool(read.get("model_used"))
        and not read.get("budget_out")
        and not read.get("failed")
        and ingest.get("results_filings", 0) > 0
        and not ingest.get("failed")
    )
    if complete and not _has_guidance(company_id):
        stamp_coverage(company_id, NO_QUANTIFIED_GUIDANCE, reason=US_NO_GUIDANCE_REASON, lookback_complete=True)
        status = NO_QUANTIFIED_GUIDANCE
    else:
        status = published_status(company_id)
        stamp_coverage(company_id, status, lookback_complete=complete)
    reached = complete or (ingest.get("results_filings", 0) == 0 and not ingest.get("failed"))
    note_discovery(company_id, since=since if reached else None)
    return {"company_id": company_id, "ingest": ingest, "read": read, "coverage_status": status}


_PROGRESS: Dict[str, Any] = {"running": False, "recent": []}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def roll_daily(*, max_companies: Optional[int] = None) -> Dict[str, Any]:
    seen = load_coverage().get("companies") or {}
    since = us_since()
    ids = [r["id"] for r in us_equity_universe() if r.get("cik")]
    order = {cid: i for i, cid in enumerate(ids)}

    def walk_key(cid: str) -> tuple:
        row = seen.get(cid) or {}
        reached = str(row.get("lookback_since") or "9999") <= since
        return (reached, str(row.get("last_discovery") or ""), order[cid])

    ids.sort(key=walk_key)
    processed: List[Dict[str, Any]] = []
    stopped = "walked_all"
    _PROGRESS.update(running=True, started_at=_now(), total=len(ids), done=0, recent=[])
    try:
        for cid in ids:
            if max_companies is not None and len(processed) >= max_companies:
                stopped = "max_companies"
                break
            try:
                out = process_company(cid)
            except Exception as exc:  # noqa: BLE001 — one issuer must not stop the walk
                out = {"company_id": cid, "error": type(exc).__name__}
            step = {
                "company_id": cid,
                "coverage_status": out.get("coverage_status"),
                "new_filings": (out.get("ingest") or {}).get("added", 0),
                "llm_calls": (out.get("read") or {}).get("llm_calls", 0),
                "closed": (out.get("read") or {}).get("closed", 0),
                "error": out.get("error"),
            }
            processed.append(step)
            _PROGRESS["done"] = len(processed)
            _PROGRESS["recent"] = ([step] + _PROGRESS["recent"])[:10]
            print(json.dumps({"us_coverage_step": {**step, "n": len(processed), "of": len(ids)}}), flush=True)
    finally:
        _PROGRESS.update(running=False, finished_at=_now(), stopped=stopped)
    ledger_rows = disclosures.log_moves(
        [p["company_id"] for p in processed],
        lead="Filing walk read SEC results releases since 2022 and matched promises to reported results.",
    )
    return {
        "ok": True,
        "market": "US",
        "processed": len(processed),
        "stopped": stopped,
        "ledger_rows": ledger_rows,
        "coverage": coverage_counts([p["company_id"] for p in processed]),
        "as_of": _now(),
        "results": processed,
    }


def coverage_progress() -> Dict[str, Any]:
    return {"as_of": _now(), "roll": dict(_PROGRESS), "cohort_size": len(us_equity_universe())}


def run_daily_from_env() -> Optional[Dict[str, Any]]:
    """Daily S&P 500 walk, gated by INTELLENS_US_COVERAGE (live SEC fetch)."""
    if os.environ.get("INTELLENS_US_COVERAGE", "").strip().lower() not in ("1", "true", "yes"):
        return None
    raw = os.environ.get("INTELLENS_US_COVERAGE_LIMIT", "").strip()
    report = roll_daily(max_companies=int(raw) if raw else None)
    return {k: v for k, v in report.items() if k != "results"}
