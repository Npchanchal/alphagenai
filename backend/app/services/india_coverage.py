"""Priority walk of NSE/BSE listings: ingest → extract → classify.

Order: flagship (Sensex ∪ Nifty 50 ∪ Nifty Bank ∪ seeded deep names) → rest of
Nifty 500 → rest of India Top 1000 → rest of NSE → BSE-only. Cohorts are disjoint slices of the one
listing master, so a scrip in several indexes is walked once. A lookback without
a metric+number promise stamps ``no_quantified_guidance``. Unsearched names stay
``listed_only``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.data.india_listings import india_equity_universe
from app.data.universe import NIFTY50_BEYOND_SENSEX, SENSEX_30
from app.services.coverage import (
    LISTED_ONLY,
    NO_QUANTIFIED_GUIDANCE,
    OPEN_PERIOD,
    SCORED,
    coverage_counts,
    load_coverage,
    note_discovery,
    published_status,
    stamp_coverage,
)
from app.services.exchange_filings import (
    GUIDANCE_DOC_TYPES,
    budget_remaining,
    discovery_since,
    ingest_company_urls,
)
from app.services import disclosures
from app.services.extract_pipeline import (
    _accepted_docs,
    ensure_company_record,
    llm_budget_used,
    maybe_promote_extracted,
)

COHORTS = ("nifty50", "nifty500", "in1000", "nse_all", "bse_only")

_FLAGSHIP_INDEXES = frozenset({"SENSEX", "NIFTY50", "NIFTYBANK"})


def _cohort_of(row: Dict[str, Any], deep_ids: frozenset) -> str:
    ix = set(row.get("index_ids") or [])
    if row["id"] in deep_ids or ix & _FLAGSHIP_INDEXES:
        return "nifty50"
    if "NIFTY500" in ix:
        return "nifty500"
    if "IN1000" in ix:
        return "in1000"
    if "NSE_ALL" in ix:
        return "nse_all"
    return "bse_only"


def cohort_partition() -> Dict[str, List[str]]:
    """Every listing id in exactly one cohort, in universe order."""
    deep_ids = frozenset(cid for cid, *_ in list(SENSEX_30) + list(NIFTY50_BEYOND_SENSEX))
    out: Dict[str, List[str]] = {name: [] for name in COHORTS}
    for row in india_equity_universe():
        out[_cohort_of(row, deep_ids)].append(row["id"])
    return out


def cohort_ids(cohort: str) -> List[str]:
    """One cohort, ``all``, or a comma list such as ``nifty50,nifty500``."""
    parts = cohort_partition()
    if cohort == "all":
        return [cid for name in COHORTS for cid in parts[name]]
    names = [c.strip() for c in cohort.split(",") if c.strip()]
    unknown = [c for c in names if c not in parts]
    if unknown or not names:
        raise ValueError(f"unknown cohort: {cohort}")
    return [cid for name in names for cid in parts[name]]


def _has_rows(company_id: str) -> bool:
    from app.data.seed import get_data

    return bool((get_data().get("outcomes") or {}).get(company_id))


def _has_exchange_filing(company_id: str) -> bool:
    from app.data import doc_store

    return any(
        d.get("source") == "exchange_filing"
        and d.get("doc_type") in GUIDANCE_DOC_TYPES
        and (d.get("text") or "").strip()
        for d in doc_store.list_documents(company_id=company_id, hydrate=False)
    )


def _has_promise(company_id: str) -> bool:
    from app.data.seed import get_data
    from app.services.guidance_review import _promise_distinct

    rows = (get_data().get("outcomes") or {}).get(company_id) or []
    for row in rows:
        if row.get("actual_value") is None and row.get("guided_value") is not None:
            return True
        if _promise_distinct(row):
            return True
    return False


def classify_company(
    company_id: str,
    *,
    lookback_complete: bool = False,
) -> str:
    status = published_status(company_id)
    if (
        lookback_complete
        and status not in (SCORED, OPEN_PERIOD)
        and not _has_rows(company_id)
        and not _has_promise(company_id)
    ):
        stamp_coverage(
            company_id,
            NO_QUANTIFIED_GUIDANCE,
            reason="lookback_no_metric_number",
            lookback_complete=True,
        )
        return NO_QUANTIFIED_GUIDANCE
    if status != LISTED_ONLY:
        stamp_coverage(company_id, status, lookback_complete=lookback_complete)
    return status


def process_company(
    company_id: str,
    *,
    live: bool = False,
    extract: bool = True,
    classify: bool = True,
    fixture_text: Optional[str] = None,
    discover: Optional[bool] = None,
) -> Dict[str, Any]:
    ingest = ingest_company_urls(
        company_id,
        live=live,
        fixture_text=fixture_text,
        discover=live if discover is None else discover,
    )
    fetched = any(r.get("ok") for r in ingest.get("results") or [])
    has_docs = fetched or bool(_accepted_docs(company_id))
    extracted: Dict[str, Any] = {}
    if extract and has_docs:
        if disclosures.enabled():
            company = ensure_company_record(company_id) or {}
            extracted = disclosures.process_company(
                company_id, market_id="IN", company_name=str(company.get("name") or company_id)
            )
        else:
            # Paused or unconfigured: leave the filings unread. The shell extractor
            # does not match a later actual, so it is not a second writer.
            extracted = {"budget_out": True, "model_unavailable": True}
    if has_docs:
        maybe_promote_extracted(company_id)
    # A lookback is complete only when a con-call or presentation filing was searched
    # and every chunk of it was read.
    read_all = not extracted.get("budget_out") and not extracted.get("failed")
    status = (
        classify_company(
            company_id, lookback_complete=_has_exchange_filing(company_id) and read_all
        )
        if classify
        else published_status(company_id)
    )
    return {
        "company_id": company_id,
        "ingest": ingest,
        "extract": extracted,
        "coverage_status": status,
    }


def roll_cohort(
    cohort: str = "nifty50",
    *,
    limit: Optional[int] = None,
    live: bool = False,
    extract: bool = True,
    fixture_text: Optional[str] = None,
    company_ids: Optional[Sequence[str]] = None,
    discover: Optional[bool] = None,
) -> Dict[str, Any]:
    ids = list(company_ids) if company_ids is not None else cohort_ids(cohort)
    if limit is not None and limit > 0:
        ids = ids[:limit]
    results = [
        process_company(
            cid, live=live, extract=extract, fixture_text=fixture_text, discover=discover
        )
        for cid in ids
    ]
    counts = coverage_counts(ids)
    return {
        "ok": True,
        "cohort": cohort,
        "processed": len(ids),
        "live": live,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": counts,
        "listed_only": counts.get(LISTED_ONLY, 0),
        "results": results,
    }


def _nse_ids(cohort: str) -> List[str]:
    nse = {
        r["id"]
        for r in india_equity_universe()
        if "NSE_ALL" in (r.get("index_ids") or []) and r.get("ticker")
    }
    return [cid for cid in cohort_ids(cohort) if cid in nse]


def roll_daily(
    cohort: str = "all",
    *,
    max_companies: Optional[int] = None,
    extract: bool = True,
) -> Dict[str, Any]:
    """Search NSE filings for the least recently searched names until today's budget is spent.

    Only names with an NSE symbol are walked; BSE-only names have no discovery
    source yet and stay ``listed_only``.
    """
    seen = load_coverage().get("companies") or {}
    ids = _nse_ids(cohort)
    order = {cid: i for i, cid in enumerate(ids)}
    since = discovery_since()

    def walk_key(cid: str) -> tuple:
        row = seen.get(cid) or {}
        reached = str(row.get("lookback_since") or "9999") <= since
        return (reached, str(row.get("last_discovery") or ""), order[cid])

    ids.sort(key=walk_key)
    processed: List[Dict[str, Any]] = []
    stopped = "walked_all"
    _PROGRESS.update(
        running=True, cohort=cohort, started_at=_now(), total=len(ids), done=0,
        current=None, current_started_at=None, recent=[],
    )
    try:
        for cid in ids:
            if max_companies is not None and len(processed) >= max_companies:
                stopped = "max_companies"
                break
            if budget_remaining("fetch") <= 0 or budget_remaining("discovery") <= 0:
                stopped = "daily_budget"
                break
            _PROGRESS.update(current=cid, current_started_at=_now())
            out = process_company(cid, live=True, extract=extract, discover=True)
            read = out.get("extract") or {}
            budget_out = bool(read.get("budget_out"))
            note_discovery(cid, since=None if budget_out or read.get("failed") else since)
            row = {
                "company_id": cid,
                "coverage_status": out["coverage_status"],
                "new_filings": sum(
                    1 for r in out["ingest"].get("results") or [] if r.get("action") == "upserted"
                ),
            }
            processed.append(row)
            step = {**row, "llm_calls": int(read.get("llm_calls") or 0), "finished_at": _now()}
            _PROGRESS["done"] = len(processed)
            _PROGRESS["recent"] = ([step] + _PROGRESS["recent"])[:10]
            print(json.dumps({"india_coverage_step": {**step, "n": len(processed), "of": len(ids)}}), flush=True)
    finally:
        _PROGRESS.update(running=False, current=None, current_started_at=None, finished_at=_now(),
                         stopped=stopped)
    ledger_rows = disclosures.log_moves(
        [p["company_id"] for p in processed],
        lead="Filing walk read exchange filings since 2022 and matched promises to reported results.",
    )
    counts = coverage_counts([p["company_id"] for p in processed])
    return {
        "ok": True,
        "cohort": cohort,
        "processed": len(processed),
        "new_filings": sum(p["new_filings"] for p in processed),
        "stopped": stopped,
        "ledger_rows": ledger_rows,
        "coverage": counts,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": processed,
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_PROGRESS: Dict[str, Any] = {"running": False, "recent": []}


def coverage_progress() -> Dict[str, Any]:
    """Where today's roll is, and how much of each daily budget is spent."""
    import os

    from app.services import exchange_filings as ef
    from app.services import ir_discovery
    from app.services.extract_pipeline import llm_daily_cap
    from app.services.llm_client import llm_rate_per_min

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cohort = _PROGRESS.get("cohort") or os.environ.get("INTELLENS_INDIA_COVERAGE_COHORT", "all")
    ids = _nse_ids(cohort)
    seen = load_coverage().get("companies") or {}
    searched_today = sum(1 for cid in ids if (seen.get(cid) or {}).get("last_discovery") == today)

    def spent(cap: int, remaining: int) -> Dict[str, int]:
        return {"used": cap - remaining, "cap": cap}

    return {
        "as_of": _now(),
        "roll": {k: v for k, v in _PROGRESS.items()},
        "cohort": cohort,
        "cohort_size": len(ids),
        "searched_today": searched_today,
        "budgets_today": {
            "filing_fetch": spent(ef.daily_fetch_cap(), budget_remaining("fetch")),
            "filing_discovery": spent(ef.daily_discovery_cap(), budget_remaining("discovery")),
            "ai_extraction_calls": {"used": llm_budget_used(), "cap": llm_daily_cap()},
            "web_searches": {"used": int(ef._web_ledger()["used"]), "cap": ef.web_search_daily_cap()},
            "issuer_site_crawls": {"used": int(ir_discovery._ledger()["used"]), "cap": ir_discovery.ir_crawl_daily_cap()},
        },
        "ai_rate_per_min": llm_rate_per_min(),
    }


def run_daily_from_env() -> Optional[Dict[str, Any]]:
    """Daily roll gated by INTELLENS_INDIA_COVERAGE; live fetch needs INTELLENS_FILING_LIVE."""
    import os

    def _on(name: str) -> bool:
        return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")

    if not _on("INTELLENS_INDIA_COVERAGE"):
        return None
    cohort = os.environ.get("INTELLENS_INDIA_COVERAGE_COHORT", "all")
    raw_limit = os.environ.get("INTELLENS_INDIA_COVERAGE_LIMIT", "").strip()
    limit = int(raw_limit) if raw_limit else None
    if not _on("INTELLENS_FILING_LIVE"):
        report = roll_cohort(cohort, limit=limit, live=False)
        return {k: v for k, v in report.items() if k != "results"}
    report = roll_daily(cohort, max_companies=limit)
    return {k: v for k, v in report.items() if k != "results"}


def universe_coverage(ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    if ids is None:
        ids = [r["id"] for r in india_equity_universe()]
    listed = list(ids)
    counts = coverage_counts(listed)
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts,
        "listed_only": counts.get(LISTED_ONLY, 0),
    }
