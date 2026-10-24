"""GCI coverage status for every listing — a typed cell, never an invented number.

Statuses:
- scored — publishable GCI exists
- open_period — guidance on file, result not yet reported
- filing_in_review — documents or unlabeled promises exist; no number yet
- no_quantified_guidance — lookback completed; no metric+number promise found
- listed_only — on the NSE/BSE master, ingest not yet run
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.data.store_lock import locked

SCORED = "scored"
OPEN_PERIOD = "open_period"
FILING_IN_REVIEW = "filing_in_review"
NO_QUANTIFIED_GUIDANCE = "no_quantified_guidance"
LISTED_ONLY = "listed_only"

COVERAGE_STATUSES = frozenset(
    {SCORED, OPEN_PERIOD, FILING_IN_REVIEW, NO_QUANTIFIED_GUIDANCE, LISTED_ONLY}
)

# Public labels — plain finance English (rule public-copy-voice). A per-company
# sentence from coverage_reason() replaces these wherever one can be built.
COVERAGE_LABELS = {
    SCORED: "Scored",
    OPEN_PERIOD: "Guided year not yet closed",
    FILING_IN_REVIEW: "Filings being checked",
    NO_QUANTIFIED_GUIDANCE: "No numeric guidance found",
    LISTED_ONLY: "Filings not yet read",
}

_CACHE: Optional[Dict[str, Any]] = None


def _store_path() -> Path:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    base = Path(override) if override else Path(__file__).resolve().parents[1] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "coverage_status.json"


@locked
def load_coverage(*, force: bool = False) -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    path = _store_path()
    if path.exists():
        try:
            _CACHE = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _CACHE = {"companies": {}}
    else:
        _CACHE = {"companies": {}}
    _CACHE.setdefault("companies", {})
    return _CACHE


@locked
def save_coverage(data: Optional[Dict[str, Any]] = None) -> None:
    global _CACHE
    blob = data if data is not None else load_coverage()
    _CACHE = blob
    path = _store_path()
    path.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")


def clear_coverage_memory() -> None:
    global _CACHE
    _CACHE = None


@locked
def reset_coverage() -> None:
    """Wipe persisted coverage stamps (tests)."""
    global _CACHE
    _CACHE = {"companies": {}}
    path = _store_path()
    path.write_text('{"companies": {}}\n', encoding="utf-8")


@locked
def stamp_coverage(
    company_id: str,
    status: str,
    *,
    reason: str = "",
    lookback_complete: bool = False,
) -> Dict[str, Any]:
    if status not in COVERAGE_STATUSES:
        raise ValueError(f"unknown coverage status: {status}")
    blob = load_coverage()
    prior = blob["companies"].get(company_id) or {}
    row = {
        "status": status,
        "reason": reason,
        "lookback_complete": lookback_complete,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    for key in ("last_discovery", "lookback_since"):
        if prior.get(key):
            row[key] = prior[key]
    blob["companies"][company_id] = row
    save_coverage(blob)
    return row


@locked
def note_discovery(company_id: str, *, since: Optional[str] = None) -> None:
    """Record that filings were searched today, back to ``since``; keeps any stamped status."""
    blob = load_coverage()
    row = blob["companies"].setdefault(company_id, {"status": LISTED_ONLY})
    row["last_discovery"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if since:
        prior = str(row.get("lookback_since") or "")
        row["lookback_since"] = min(prior, since) if prior else since
    save_coverage(blob)


def persisted_row(company_id: str) -> Dict[str, Any]:
    return dict((load_coverage().get("companies") or {}).get(company_id) or {})


def _has_usable_docs(company_id: str) -> bool:
    try:
        from app.data import doc_store
    except Exception:
        return False
    for doc in doc_store.list_documents(company_id=company_id, hydrate=False):
        text = (doc.get("text") or "").lower()
        if doc.get("source") == "hand_labeled_period_pack":
            continue
        if "auto corpus pack" in text:
            continue
        if not (doc.get("text") or "").strip():
            continue
        return True
    return False


def published_status(company_id: str) -> str:
    """Status using the published score, for callers without a score in hand.

    Companies with outcome rows are scored live (binds land there first); other
    listings use the listing cache.
    """
    row: Dict[str, Any] = {}
    try:
        from app.data.seed import get_data, get_outcomes
        from app.services.gci_scoring import compute_company_gci
        from app.services.score_policy import is_scoreable

        company = next((c for c in get_data()["companies"] if c["id"] == company_id), None)
        if company is not None and is_scoreable(company.get("data_quality")):
            row = {
                "gci_score": compute_company_gci(get_outcomes(company_id)),
                "data_quality": company.get("data_quality"),
            }
        if row.get("gci_score") is None:
            from app.data.gci_score_cache import get_listing_score

            row = get_listing_score(company_id) or {}
    except Exception:
        row = {}
    return coverage_status_for(
        company_id,
        score=row.get("gci_score"),
        data_quality=row.get("data_quality") if row.get("gci_score") is not None else None,
    )


def _outcomes_for(company_id: str, outcomes: Optional[Iterable[Any]]) -> List[Any]:
    if outcomes is not None:
        return list(outcomes)
    try:
        from app.data.seed import get_data

        raw = (get_data().get("outcomes") or {}).get(company_id) or []
        return list(raw)
    except Exception:
        return []


def coverage_status_for(
    company_id: str,
    *,
    score: Optional[float] = None,
    outcomes: Optional[Iterable[Any]] = None,
    data_quality: Optional[str] = None,
) -> str:
    """Live status. A number always wins; persisted no-guidance only after lookback."""
    from app.services.score_policy import is_scoreable

    if score is not None and (data_quality is None or is_scoreable(data_quality)):
        return SCORED

    rows = _outcomes_for(company_id, outcomes)
    persisted = persisted_row(company_id)

    open_period = False
    distinct_unbound = False
    for row in rows:
        g = row.get if isinstance(row, dict) else lambda k, d=None: getattr(row, k, d)
        actual = g("actual_value")
        if actual is None and (
            g("guided_value") is not None
            or str(g("guidance_quote") or "").strip()
            or str(g("guidance_source_url") or "").strip()
        ):
            open_period = True
            continue
        reviewed = bool(str(g("reviewed_by") or "").strip())
        if reviewed:
            continue
        try:
            from app.services.guidance_review import _promise_distinct

            if isinstance(row, dict) and _promise_distinct(row):
                distinct_unbound = True
        except Exception:
            if actual is not None and g("guided_value") is not None:
                try:
                    if abs(float(g("guided_value")) - float(actual)) >= 0.05:
                        distinct_unbound = True
                except (TypeError, ValueError):
                    pass

    if open_period:
        return OPEN_PERIOD
    if distinct_unbound:
        return FILING_IN_REVIEW
    if persisted.get("lookback_complete") and persisted.get("status") == NO_QUANTIFIED_GUIDANCE:
        return NO_QUANTIFIED_GUIDANCE
    if _has_usable_docs(company_id) or rows:
        return FILING_IN_REVIEW
    if persisted.get("status") in COVERAGE_STATUSES and persisted.get("status") != LISTED_ONLY:
        return str(persisted["status"])
    return LISTED_ONLY


def coverage_label(status: Optional[str]) -> str:
    return COVERAGE_LABELS.get(status or "", COVERAGE_LABELS[LISTED_ONLY])


def _month_year(iso: str) -> str:
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return iso


def _is_us(company_id: str) -> bool:
    try:
        from app.data.us_listings import find_us_listing

        return find_us_listing(company_id) is not None
    except Exception:
        return False


def _row_period_end(row: Any, us: bool) -> Optional[str]:
    g = row.get if isinstance(row, dict) else lambda k, d=None: getattr(row, k, d)
    end = str(g("period_end") or "").strip()
    if end:
        return end[:10]
    if us:
        return None
    from app.services.commitments import period_end

    return period_end(str(g("period") or ""))


def _window_start() -> str:
    from app.services.exchange_filings import discovery_since

    return discovery_since()


def coverage_reason(
    company_id: str,
    status: Optional[str],
    *,
    outcomes: Optional[Iterable[Any]] = None,
    today: Optional[str] = None,
) -> Optional[str]:
    """One plain sentence for a company with no number: why, and until when. Never a score."""
    if not status or status == SCORED:
        return None
    us = _is_us(company_id)
    persisted = persisted_row(company_id)
    since = _month_year(str(persisted.get("lookback_since") or _window_start()))
    if status == OPEN_PERIOD:
        now = today or datetime.now(timezone.utc).date().isoformat()
        open_rows = []
        for row in _outcomes_for(company_id, outcomes):
            g = row.get if isinstance(row, dict) else lambda k, d=None, r=row: getattr(r, k, d)
            if g("actual_value") is not None or (g("guided_value") is None and g("guided_low") is None):
                continue
            end = _row_period_end(row, us)
            if end:
                open_rows.append((end, str(g("period") or "")))
        upcoming = sorted(r for r in open_rows if r[0] >= now)
        if upcoming:
            end, period = upcoming[0]
            span = "quarter" if period.upper().startswith("Q") else "year"
            return f"First guided {span} ({period}) closes {_month_year(end)}"
        if open_rows:
            end, period = max(open_rows)
            return f"{period} result not yet matched to a filing"
        return COVERAGE_LABELS[OPEN_PERIOD]
    if status == FILING_IN_REVIEW:
        guided = any(
            (row.get("guided_value") if isinstance(row, dict) else getattr(row, "guided_value", None)) is not None
            for row in _outcomes_for(company_id, outcomes)
        )
        if guided:
            return "Guidance found, being checked against results"
        where = "SEC results releases" if us else "Filings"
        return f"{where} since {since} held, being read"
    if status == NO_QUANTIFIED_GUIDANCE:
        where = "SEC results releases" if us else "exchange filings"
        return f"No numeric guidance in {where} since {since}"
    where = "SEC results releases" if us else "Filings"
    return f"{where} since {_month_year(_window_start())} not yet read"


def coverage_counts(company_ids: Iterable[str]) -> Dict[str, int]:
    tallies = {k: 0 for k in COVERAGE_STATUSES}
    for cid in company_ids:
        status = published_status(cid)
        tallies[status] = tallies.get(status, 0) + 1
    tallies["total"] = sum(tallies[k] for k in COVERAGE_STATUSES)
    return tallies


def universe_coverage_counts(company_ids: Iterable[str], universe_ids: Iterable[str]) -> Dict[str, int]:
    """Tallies over the whole listing universe.

    Listings with no company record and no stamped status have nothing to
    classify and count as listed_only without a per-name walk.
    """
    known = set(company_ids) | set(load_coverage().get("companies") or {})
    universe = set(universe_ids)
    tallies = coverage_counts(sorted(known & universe))
    tallies[LISTED_ONLY] = tallies.get(LISTED_ONLY, 0) + len(universe - known)
    tallies["total"] = sum(tallies[k] for k in COVERAGE_STATUSES)
    return tallies
