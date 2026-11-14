"""Cross-universe citation credibility audit for India index tabs.

Runs in CI to ensure:
- hand_labeled outcomes are citeable with resolvable lookups and quote binding
- listing_provisional / demo_structured outcomes are never citeable
- list_company_citations matches outcome citeable counts
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

import pytest

from app.data.markets import constituent_count, list_constituents
from app.services.citations import assess_citeability, lookup_citation, list_company_citations
from app.services.repository import get_company_gci

INDIA_INDEXES = ("SENSEX", "NIFTY50", "NSE_ALL", "BSE_ALL", "IN1000")

_company_audit_cache: Dict[str, Dict[str, Any]] = {}


def _quote_in_document(rec: Dict[str, Any], quote: str) -> bool:
    doc = rec.get("document_text") or ""
    if not quote or not doc:
        return bool(rec.get("excerpt_only"))
    if quote in doc:
        return True
    span_start, span_end = rec.get("span_start"), rec.get("span_end")
    if span_start is not None and span_end is not None:
        snippet = doc[span_start:span_end]
        return quote in snippet or snippet in quote
    return bool(rec.get("excerpt_only"))


def _audit_outcome(company_id: str, data_quality: str, outcome: Any) -> List[str]:
    issues: List[str] = []
    # HTML press pages are stored source_unverified until re-cited to a filing PDF.
    if getattr(outcome, "cite_reason", None) == "source_unverified":
        citeable, reason = False, "source_unverified"
    else:
        citeable, reason = assess_citeability(
            data_quality=data_quality,
            source_url=outcome.source_url,
            quote_span=outcome.quote_span,
            review_status=getattr(outcome, "review_status", None),
            doc_id=outcome.doc_id,
        )
    if outcome.citeable != citeable:
        issues.append(
            f"{company_id}: citeable flag mismatch (flag={outcome.citeable}, assess={citeable}, reason={reason})"
        )
    non_citeable_qualities = {
        "listing_provisional",
        "demo_structured",
        "market_scaffold",
        "listing_master",
    }
    if data_quality in non_citeable_qualities and outcome.citeable:
        issues.append(f"{company_id}: {data_quality} outcome marked citeable")
    if data_quality == "listing_provisional" and outcome.quote_span:
        issues.append(f"{company_id}: provisional outcome exposes quote_span")
    if outcome.citeable and not outcome.citation_id:
        issues.append(f"{company_id}: citeable outcome missing citation_id")
    if outcome.citeable and outcome.citation_id:
        rec = lookup_citation(outcome.citation_id)
        if not rec:
            issues.append(f"{company_id}: lookup failed for {outcome.citation_id}")
        else:
            quote = rec.get("quote_span") or rec.get("quote") or outcome.quote_span or ""
            if quote and not _quote_in_document(rec, quote):
                issues.append(f"{company_id}: quote not bound in document for {outcome.citation_id}")
            if not (rec.get("source_url") or rec.get("url")):
                issues.append(f"{company_id}: lookup missing source_url for {outcome.citation_id}")
    return issues


def _audit_company(company_id: str) -> Dict[str, Any]:
    if company_id in _company_audit_cache:
        return _company_audit_cache[company_id]

    detail = get_company_gci(company_id)
    issues: List[str] = []
    citeable_n = 0
    for outcome in detail.outcomes:
        if outcome.citeable:
            citeable_n += 1
        issues.extend(_audit_outcome(detail.id, detail.data_quality, outcome))

    listed = list_company_citations(company_id, citeable_only=True)
    if citeable_n != len(listed):
        issues.append(
            f"{company_id}: list_company_citations mismatch (outcomes={citeable_n}, listed={len(listed)})"
        )

    result = {
        "id": detail.id,
        "ticker": detail.ticker,
        "data_quality": detail.data_quality,
        "citeable_outcomes": citeable_n,
        "issues": issues,
    }
    _company_audit_cache[company_id] = result
    return result


def _summarize_index(index_id: str) -> Tuple[Dict[str, int], List[str]]:
    rows = list_constituents(index_id)
    expected = constituent_count(index_id)
    assert len(rows) == expected, f"{index_id}: materialized {len(rows)} != count {expected}"

    quality_counts: Dict[str, int] = defaultdict(int)
    issues: List[str] = []
    citeable_companies = 0
    total_citeable_outcomes = 0

    for row in rows:
        audit = _audit_company(row["id"])
        quality_counts[audit["data_quality"]] += 1
        if audit["citeable_outcomes"]:
            citeable_companies += 1
            total_citeable_outcomes += audit["citeable_outcomes"]
        issues.extend(audit["issues"])

    summary = {
        "companies": len(rows),
        "hand_labeled": quality_counts.get("hand_labeled", 0),
        "provisional": quality_counts.get("listing_provisional", 0),
        "demo": quality_counts.get("demo_structured", 0),
        "citeable_companies": citeable_companies,
        "citeable_outcomes": total_citeable_outcomes,
    }
    return summary, issues


@pytest.mark.parametrize("index_id", INDIA_INDEXES)
def test_index_citation_integrity(index_id: str) -> None:
    summary, issues = _summarize_index(index_id)
    assert not issues, f"{index_id} citation issues ({summary}): " + "; ".join(issues[:5])


def test_sensex_fully_hand_labeled_and_citeable() -> None:
    summary, _ = _summarize_index("SENSEX")
    assert summary["companies"] == 30
    assert summary["hand_labeled"] == 30
    assert summary["provisional"] == 0
    # maruti and jswsteel have only an unverified HTML press page, so they are
    # hand-labeled and not citeable until that page is re-cited to a filing PDF.
    assert summary["citeable_companies"] == 28
    assert summary["citeable_outcomes"] >= 28


def test_nifty50_membership_and_citeable_depth() -> None:
    summary, _ = _summarize_index("NIFTY50")
    assert summary["companies"] == 50
    # Membership is NSE's published list; a new entrant without a seeded record is a listing row.
    assert summary["hand_labeled"] + summary["demo"] + summary["provisional"] == 50
    assert summary["hand_labeled"] >= 35
    # maruti and jswsteel are hand-labeled but not citeable (unverified press pages).
    assert summary["citeable_companies"] == summary["hand_labeled"] - 2
    assert summary["citeable_outcomes"] >= summary["citeable_companies"]


def test_bulk_indexes_provisional_majority_not_citeable() -> None:
    for index_id in ("NSE_ALL", "BSE_ALL", "IN1000"):
        summary, issues = _summarize_index(index_id)
        assert not issues
        assert summary["provisional"] > summary["hand_labeled"]
        # Hand-labeled names in bulk lists must still cite cleanly.
        if summary["hand_labeled"]:
            # Same two press-page names are inside every India bulk list.
            assert summary["citeable_companies"] == summary["hand_labeled"] - 2
