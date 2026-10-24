"""Filing walk v2: periods, strict quotes, promise-to-result reconciliation, coverage reasons.

Rows come only from text in stored filings; nothing here invents an actual.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.data.seed import get_data, reset_data
from app.services import disclosures
from app.services.coverage import (
    LISTED_ONLY,
    NO_QUANTIFIED_GUIDANCE,
    OPEN_PERIOD,
    SCORED,
    coverage_reason,
    note_discovery,
    reset_coverage,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    from app.data import doc_store as store

    store._DOCS = None
    reset_data()
    reset_coverage()
    yield
    store._DOCS = None
    reset_data()


# ── periods ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,market,want",
    [
        ("Q3FY25", "IN", "Q3 FY25"),
        ("FY2024-25", "IN", "FY25"),
        ("FY 2025", "US", "FY2025"),
        ("Q1 FY24", "US", "Q1 FY2024"),
        ("next year", "IN", None),
        ("", "US", None),
    ],
)
def test_canonical_period(raw, market, want):
    assert disclosures.canonical_period(raw, market) == want


def test_period_bounds_india_april_to_march():
    assert disclosures.period_bounds("FY25", "IN") == (date(2024, 4, 1), date(2025, 3, 31))
    assert disclosures.period_bounds("Q3 FY25", "IN") == (date(2024, 10, 1), date(2024, 12, 31))


def test_period_bounds_us_follow_fiscal_year_end():
    assert disclosures.period_bounds("FY2025", "US", "0131") == (date(2024, 2, 1), date(2025, 1, 31))
    assert disclosures.period_bounds("Q1 FY2024", "US", "0131") == (date(2023, 2, 1), date(2023, 4, 30))
    assert disclosures.period_bounds("Q4 FY2024", "US", "1231") == (date(2024, 10, 1), date(2024, 12, 31))


def test_quote_must_be_whole_sentence_in_filing():
    text = "We expect revenue growth of 10% to 12% in FY25, led by exports."
    assert disclosures.quote_verbatim("We expect revenue growth of 10% to 12% in FY25", text)
    assert not disclosures.quote_verbatim("We expect revenue growth of 10% to 14% in FY25", text)
    assert not disclosures.quote_verbatim("short", text)


# ── reconciliation ──────────────────────────────────────────────────────────

G1 = "We expect revenue growth of 10% to 12% for FY25."
G2 = "We now expect revenue growth of 12% to 14% for FY25."
R_EARLY = "Revenue growth for FY25 so far was 11.0% in the first half."
R1 = "For FY25, revenue growth was 13.1% on a reported basis."


def _india_docs():
    return [
        {"doc_id": "d1", "url": "https://nse/1", "title": "Q4 FY24 call", "date": "2024-05-10", "text": G1},
        {"doc_id": "d2", "url": "https://nse/2", "title": "Q2 FY25 call", "date": "2024-11-01",
         "text": G2 + " " + R_EARLY},
        {"doc_id": "d3", "url": "https://nse/3", "title": "Q4 FY25 call", "date": "2025-05-15", "text": R1},
    ]


def _blob():
    m = "revenue_growth_pct"
    return {
        "docs": {
            "d1": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
                {"metric": m, "period": "FY25", "low": 10, "high": 12, "quote": G1}], "results": []}}},
            "d2": {"date": "2024-11-01", "chunks": {"a": {
                "guidance": [{"metric": m, "period": "FY25", "low": 12, "high": 14, "quote": G2}],
                "results": [{"metric": m, "period": "FY25", "value": 11.0, "quote": R_EARLY}]}}},
            "d3": {"date": "2025-05-15", "chunks": {"a": {"guidance": [], "results": [
                {"metric": m, "period": "FY25", "value": 13.1, "quote": R1}]}}},
        }
    }


def test_opening_band_revision_and_actual_after_period_end():
    out = disclosures.reconcile("acme", _india_docs(), _blob(), market_id="IN", today="2025-06-01")
    assert out["closed"] == 1
    (row,) = out["rows"]
    assert (row["guided_low"], row["guided_high"]) == (10, 12)
    assert row["guidance_quote"] == G1 and row["guidance_as_of"] == "2024-05-10"
    assert [(r["guided_low"], r["guided_high"], r["as_of"]) for r in row["revisions"]] == [(12, 14, "2024-11-01")]
    # The half-year figure was filed before FY25 closed, so the full-year result is the actual.
    assert row["actual_value"] == 13.1 and row["quote_span"] == R1 and row["as_of"] == "2025-05-15"
    assert row["reviewed_by"] == disclosures.REVIEWER and row["review_status"] == "accepted"
    assert row["period_end"] == "2025-03-31"


def test_guidance_after_period_end_is_ignored():
    blob = _blob()
    blob["docs"]["d3"]["chunks"]["a"]["guidance"] = [
        {"metric": "revenue_growth_pct", "period": "FY25", "low": 13, "high": 13.5, "quote": R1}
    ]
    out = disclosures.reconcile("acme", _india_docs(), blob, market_id="IN")
    assert out["rows"][0]["guided_low"] == 10


def test_paraphrased_quote_and_missing_number_are_dropped():
    blob = {"docs": {"d1": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
        {"metric": "revenue_growth_pct", "period": "FY25", "low": 10, "high": 12,
         "quote": "Management guided revenue growth of 10-12% for the year."},
        {"metric": "revenue_growth_pct", "period": "FY25", "low": 15, "high": 18, "quote": G1},
        {"metric": "made_up_metric", "period": "FY25", "low": 1, "high": 2, "quote": G1},
    ], "results": []}}}}}
    out = disclosures.reconcile("acme", _india_docs(), blob, market_id="IN")
    assert out["rows"] == []
    assert out["dropped"]["not_verbatim"] == 1
    assert out["dropped"]["number_not_in_quote"] == 1
    assert out["dropped"]["unknown_metric"] == 1


def test_plus_minus_band_only_when_quote_says_so():
    q = "Revenue is expected to be $8.10 billion, plus or minus 2%."
    docs = [{"doc_id": "u1", "url": "https://sec/1", "title": "8-K", "date": "2022-05-25", "text": q}]
    blob = {"docs": {"u1": {"date": "2022-05-25", "chunks": {"a": {"guidance": [
        {"metric": "revenue_usd_mn", "period": "Q2 FY2023", "low": 8100, "high": 8100, "pm_pct": 2, "quote": q}
    ], "results": []}}}}}
    (row,) = disclosures.reconcile("us_x", docs, blob, market_id="US", fy_end_mmdd="0131")["rows"]
    assert (row["guided_low"], row["guided_high"]) == (7938.0, 8262.0)
    blob["docs"]["u1"]["chunks"]["a"]["guidance"][0]["pm_pct"] = 3
    (row,) = disclosures.reconcile("us_x", docs, blob, market_id="US", fy_end_mmdd="0131")["rows"]
    assert (row["guided_low"], row["guided_high"]) == (8100, 8100)


def test_apply_rows_never_touches_hand_labeled_company():
    data = get_data()
    labeled = next(c for c in data["companies"] if c.get("data_quality") == "hand_labeled")
    before = list(data["outcomes"].get(labeled["id"]) or [])
    out = disclosures.apply_rows(labeled["id"], [{"period": "FY25", "metric": "revenue_growth_pct"}])
    assert out == {"applied": False, "reason": "hand_labeled"}
    assert (get_data()["outcomes"].get(labeled["id"]) or []) == before


# ── model reads ─────────────────────────────────────────────────────────────


def _doc(text, doc_id="d1"):
    return {"doc_id": doc_id, "url": f"https://nse/{doc_id}", "title": "call", "date": "2024-05-10", "text": text}


BODY = "Revenue grew 12% in FY24 and we expect 10% to 12% in FY25 with margins of 20% to 22%. " * 3


def test_chunks_read_once_and_cached():
    calls = []

    def stub(chunk, **kw):
        calls.append(kw["market_id"])
        return {"guidance": [], "results": []}

    first = disclosures.read_documents("acme", [_doc(BODY)], company_name="Acme", market_id="IN", extractor=stub)
    again = disclosures.read_documents("acme", [_doc(BODY)], company_name="Acme", market_id="IN", extractor=stub)
    assert first["llm_calls"] == len(calls) >= 1
    assert again["llm_calls"] == 0 and again["chunks_already_read"] == first["llm_calls"]


def test_failure_streak_stops_the_walk():
    def broken(chunk, **kw):
        raise RuntimeError("quota")

    docs = [_doc(BODY + f" doc {i}", doc_id=f"d{i}") for i in range(6)]
    out = disclosures.read_documents("acme", docs, company_name="Acme", market_id="IN", extractor=broken)
    assert out["failed"] == disclosures.MAX_FAILURE_STREAK
    assert out["model_unavailable"] and out["budget_out"]


def test_long_filing_is_read_in_48k_pieces():
    seen = []

    def stub(chunk, **kw):
        seen.append(len(chunk))
        return {"guidance": [], "results": []}

    text = ("Revenue rose 12% to 4,210 crore; EBITDA margin 21.5% in Q3 FY25. " * 1600)[:100000]
    out = disclosures.read_documents("long", [_doc(text, doc_id="L")], company_name="L", market_id="IN", extractor=stub)
    assert out["llm_calls"] == 3
    assert max(seen) == disclosures.READ_CHUNK_CHARS


def test_filing_fully_read_at_old_size_is_not_read_again():
    from app.services.extract_pipeline import text_chunks

    text = ("Revenue rose 12% to 4,210 crore; EBITDA margin 21.5% in Q3 FY25. " * 1600)[:100000]
    doc = _doc(text, doc_id="old")
    blob = disclosures.load_extracts("legacy")
    old = text_chunks(text, size=disclosures.LEGACY_CHUNK_CHARS)
    blob["docs"]["old"] = {
        "url": doc["url"], "date": "2024-05-10", "title": "call",
        "chunks": {disclosures._chunk_key(c): {"guidance": [], "results": []} for c in old},
    }
    disclosures.save_extracts("legacy", blob)

    def never(chunk, **kw):
        raise AssertionError("filing already read")

    out = disclosures.read_documents("legacy", [doc], company_name="L", market_id="IN", extractor=never)
    assert out["llm_calls"] == 0 and out["chunks_already_read"] == len(old)

    partial = disclosures.load_extracts("legacy")
    partial["docs"]["old"]["chunks"].pop(disclosures._chunk_key(old[-1]))
    disclosures.save_extracts("legacy", partial)
    calls = []
    disclosures.read_documents(
        "legacy", [doc], company_name="L", market_id="IN",
        extractor=lambda c, **kw: calls.append(c) or {"guidance": [], "results": []},
    )
    assert len(calls) == 3


def test_filings_before_the_start_date_are_not_read(monkeypatch):
    from app.data import doc_store

    monkeypatch.setenv("INTELLENS_FILING_DISCOVERY_SINCE", "2025-01-01")
    for date in ("2024-11-05", "2025-05-12"):
        doc_store.upsert_document(
            company_id="acme_since", doc_type="concall", title=f"call {date}",
            text=BODY + date, url=f"https://nse/acme/{date}", date=date, source="exchange_filing",
            review_status="accepted",
        )
    read_dates = []

    def stub(chunk, **kw):
        read_dates.append(kw["doc_date"])
        return {"guidance": [], "results": []}

    out = disclosures.process_company("acme_since", market_id="IN", company_name="Acme", extractor=stub)
    assert read_dates == ["2025-05-12"]
    assert out["docs"] == 2


def test_parallel_reads_overlap_and_cache_every_chunk(monkeypatch):
    import threading
    import time

    lock = threading.Lock()
    live = {"now": 0, "peak": 0}

    def slow(chunk, **kw):
        with lock:
            live["now"] += 1
            live["peak"] = max(live["peak"], live["now"])
        time.sleep(0.05)
        with lock:
            live["now"] -= 1
        return {"guidance": [], "results": []}

    docs = [_doc(BODY + f" doc {i}", doc_id=f"p{i}") for i in range(8)]
    monkeypatch.setenv("INTELLENS_DISCLOSURE_READ_WORKERS", "4")
    out = disclosures.read_documents("para", docs, company_name="Para", market_id="IN", extractor=slow)
    assert out["llm_calls"] >= 8 and out["failed"] == 0
    assert live["peak"] > 1
    again = disclosures.read_documents("para", docs, company_name="Para", market_id="IN", extractor=slow)
    assert again["llm_calls"] == 0 and again["chunks_already_read"] == out["llm_calls"]


def test_rate_limit_429_is_retried_then_read(monkeypatch):
    from app.services import llm_client

    replies = [RuntimeError('LLM HTTP 429: {"error": "per minute"}'), '{"guidance": [], "results": []}']

    def fake(messages, **kw):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    waits = []
    monkeypatch.setattr(llm_client, "chat_completion", fake)
    monkeypatch.setattr(disclosures, "_sleep", waits.append)
    assert disclosures.llm_extract("chunk", company_name="A", market_id="US", doc_date="2024-05-01") == {
        "guidance": [],
        "results": [],
    }
    assert waits == [disclosures.RETRY_WAITS[0]]


def test_flex_reads_fall_back_to_standard_on_the_last_try(monkeypatch):
    from app.services import llm_client

    tiers = []

    def shed(messages, **kw):
        tiers.append((kw.get("service_tier"), kw.get("timeout")))
        if kw.get("service_tier") == "flex":
            raise RuntimeError("LLM HTTP 503: flex capacity")
        return '{"guidance": [], "results": []}'

    monkeypatch.setenv("INTELLENS_DISCLOSURE_SERVICE_TIER", "flex")
    monkeypatch.setattr(llm_client, "chat_completion", shed)
    monkeypatch.setattr(disclosures, "_sleep", lambda s: None)
    disclosures.llm_extract("chunk", company_name="A", market_id="US", doc_date="2024-05-01")
    assert [t for t, _ in tiers] == ["flex"] * len(disclosures.RETRY_WAITS) + [None]
    assert all(timeout == disclosures.FLEX_TIMEOUT_S for _, timeout in tiers)


def test_persistent_429_still_fails_and_other_errors_are_not_retried(monkeypatch):
    from app.services import llm_client

    calls = []

    def quota(messages, **kw):
        calls.append(1)
        raise RuntimeError("LLM HTTP 429: daily quota")

    monkeypatch.setattr(llm_client, "chat_completion", quota)
    monkeypatch.setattr(disclosures, "_sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        disclosures.llm_extract("chunk", company_name="A", market_id="US", doc_date="2024-05-01")
    assert len(calls) == len(disclosures.RETRY_WAITS) + 1

    calls.clear()

    def bad_key(messages, **kw):
        calls.append(1)
        raise RuntimeError("LLM HTTP 401: bad key")

    monkeypatch.setattr(llm_client, "chat_completion", bad_key)
    with pytest.raises(RuntimeError):
        disclosures.llm_extract("chunk", company_name="A", market_id="US", doc_date="2024-05-01")
    assert len(calls) == 1


# ── coverage reasons ────────────────────────────────────────────────────────


def test_scored_company_has_no_reason():
    assert coverage_reason("anything", SCORED) is None


def test_listed_only_reason_names_the_source():
    assert coverage_reason("reliance", LISTED_ONLY).endswith("not yet read")
    assert coverage_reason("us_aapl", LISTED_ONLY).startswith("SEC results releases since")


def test_no_guidance_reason_states_the_window():
    note_discovery("acme", since="2022-01-01")
    assert coverage_reason("acme", NO_QUANTIFIED_GUIDANCE) == "No numeric guidance in exchange filings since Jan 2022"


def test_open_period_reason_gives_closing_month():
    rows = [{"period": "FY27", "metric": "revenue_growth_pct", "guided_low": 10, "guided_high": 12,
             "guided_value": 11, "actual_value": None}]
    assert coverage_reason("acme", OPEN_PERIOD, outcomes=rows, today="2026-10-18") == (
        "First guided year (FY27) closes Mar 2027"
    )
    assert coverage_reason("acme", OPEN_PERIOD, outcomes=rows, today="2027-06-01") == (
        "FY27 result not yet matched to a filing"
    )


def test_filing_in_review_says_guidance_only_when_there_is_some():
    from app.services.coverage import FILING_IN_REVIEW

    guided = [{"period": "FY26", "metric": "revenue_growth_pct", "guided_value": 11, "actual_value": None}]
    assert coverage_reason("acme", FILING_IN_REVIEW, outcomes=guided) == (
        "Guidance found, being checked against results"
    )
    assert coverage_reason("us_aapl", FILING_IN_REVIEW, outcomes=[]).startswith("SEC results releases since")
    assert coverage_reason("us_aapl", FILING_IN_REVIEW, outcomes=[]).endswith("held, being read")


def test_reason_never_contains_a_score():
    for status in (OPEN_PERIOD, NO_QUANTIFIED_GUIDANCE, LISTED_ONLY):
        text = coverage_reason("acme", status) or ""
        assert "GCI" not in text and "/100" not in text


# ── whitespace golden extract and match guards ──────────────────────────────


def _load_cases():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent / "golden" / "whitespace_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_whitespace_extract_cases_keep_or_drop():
    from app.data.metric_catalog import metrics_for_market

    allowed = {m["id"] for m in metrics_for_market("IN")}
    for case in _load_cases()["extract"]:
        checked, why = disclosures._check_item(
            "guidance", case["item"], case["text"], "IN", None, allowed
        )
        if case["keep"]:
            assert checked is not None, case["id"]
            assert disclosures.quote_verbatim(case["item"]["quote"], case["text"])
            if "band" in case:
                assert [checked["low"], checked["high"]] == case["band"]
        else:
            assert checked is None and why == case["reason"], case["id"]


def _pair(doc_id, day, text):
    return {"doc_id": doc_id, "url": f"https://nse/{doc_id}", "title": doc_id, "date": day, "text": text}


def test_constant_currency_is_not_filled_from_reported_growth():
    g = "We expect constant currency revenue growth of 4% to 6% for FY25."
    r = "Reported revenue growth for FY25 was 5.5%."
    docs = [_pair("g", "2024-05-10", g), _pair("r", "2025-05-15", r)]
    blob = {"docs": {
        "g": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
            {"metric": "revenue_growth_cc_pct", "period": "FY25", "low": 4, "high": 6, "quote": g}
        ], "results": []}}},
        "r": {"date": "2025-05-15", "chunks": {"a": {"guidance": [], "results": [
            {"metric": "revenue_growth_pct", "period": "FY25", "value": 5.5, "quote": r}
        ]}}},
    }}
    out = disclosures.reconcile("acme", docs, blob, market_id="IN", today="2025-06-01")
    (row,) = out["rows"]
    assert row["actual_value"] is None
    assert row["metric"] == "revenue_growth_cc_pct"
    assert out["conflicts"]
    assert out["conflicts"][0]["promise_metric"] == "revenue_growth_cc_pct"
    assert out["conflicts"][0]["result_metric"] == "revenue_growth_pct"
    assert out["conflicts"][0]["reason"] == "metric"


def test_basis_points_do_not_match_a_percent_actual():
    g = "We expect operating margin of 15.0% (150 basis points of expansion) for FY25."
    r = "Operating margin for FY25 was 15.0%."
    docs = [_pair("g", "2024-05-10", g), _pair("r", "2025-05-15", r)]
    blob = {"docs": {
        "g": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
            {"metric": "operating_margin_pct", "period": "FY25", "low": 15, "high": 15, "quote": g}
        ], "results": []}}},
        "r": {"date": "2025-05-15", "chunks": {"a": {"guidance": [], "results": [
            {"metric": "operating_margin_pct", "period": "FY25", "value": 15.0, "quote": r}
        ]}}},
    }}
    out = disclosures.reconcile("acme", docs, blob, market_id="IN", today="2025-06-01")
    (row,) = out["rows"]
    assert row["actual_value"] is None
    assert row["review_status"] == "pending"
    assert any(c["reason"] == "unit" for c in out["conflicts"])


def test_crore_guidance_does_not_match_a_million_actual():
    g = "We guide capex of 400 crore for FY25."
    r = "Capex was Rs 400 million for FY25."
    docs = [_pair("g", "2024-05-10", g), _pair("r", "2025-05-15", r)]
    blob = {"docs": {
        "g": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
            {"metric": "capex_guidance", "period": "FY25", "low": 400, "high": 400, "quote": g}
        ], "results": []}}},
        "r": {"date": "2025-05-15", "chunks": {"a": {"guidance": [], "results": [
            {"metric": "capex_guidance", "period": "FY25", "value": 400, "quote": r}
        ]}}},
    }}
    out = disclosures.reconcile("acme", docs, blob, market_id="IN", today="2025-06-01")
    assert out["rows"][0]["actual_value"] is None
    assert any(c["reason"] == "unit" for c in out["conflicts"])


def _quiet_blob(third_metric):
    g1 = "We expect revenue growth of 10% to 12% for FY25."
    g2 = "We expect operating margin of 21.0% to 22.0% for FY25."
    g3 = (
        g1
        if third_metric == "revenue_growth_pct"
        else "We expect operating margin of 20.0% to 21.0% for FY26."
    )
    third_period = "FY25" if third_metric == "revenue_growth_pct" else "FY26"
    docs = [
        _pair("d1", "2024-05-10", g1),
        _pair("d2", "2024-08-01", g2),
        _pair("d3", "2024-11-01", g3),
    ]
    blob = {"docs": {
        "d1": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
            {"metric": "revenue_growth_pct", "period": "FY25", "low": 10, "high": 12, "quote": g1}
        ], "results": []}}},
        "d2": {"date": "2024-08-01", "chunks": {"a": {"guidance": [
            {"metric": "operating_margin_pct", "period": "FY25", "low": 21, "high": 22, "quote": g2}
        ], "results": []}}},
        "d3": {"date": "2024-11-01", "chunks": {"a": {"guidance": [
            {"metric": third_metric, "period": third_period, "low": 10, "high": 12, "quote": g3}
            if third_metric == "revenue_growth_pct"
            else {"metric": "operating_margin_pct", "period": "FY26", "low": 20, "high": 21, "quote": g3}
        ], "results": []}}},
    }}
    return docs, blob


def test_two_silent_filings_propose_a_drop_and_one_does_not():
    docs, blob = _quiet_blob("operating_margin_pct")
    out = disclosures.reconcile("acme", docs, blob, market_id="IN")
    drops = [d for d in out["quiet_drops"] if d["metric"] == "revenue_growth_pct"]
    assert len(drops) == 1
    assert drops[0]["doc_ids"] == ["d2", "d3"]
    assert all(row["dropped"] is False for row in out["rows"])

    short = disclosures.reconcile("acme", docs[:2], {"docs": {k: blob["docs"][k] for k in ("d1", "d2")}}, market_id="IN")
    assert [d for d in short["quiet_drops"] if d["metric"] == "revenue_growth_pct"] == []


def test_reiteration_clears_the_quiet_drop():
    docs, blob = _quiet_blob("revenue_growth_pct")
    out = disclosures.reconcile("acme", docs, blob, market_id="IN")
    assert [d for d in out["quiet_drops"] if d["metric"] == "revenue_growth_pct"] == []


def test_quiet_drop_queue_does_not_move_gci():
    from app.data.seed import get_outcomes
    from app.services.gci_scoring import compute_company_gci
    from app.services.labeling_queue import sync_reconcile_findings

    before = compute_company_gci(get_outcomes("infy"))
    docs, blob = _quiet_blob("operating_margin_pct")
    out = disclosures.reconcile("acme", docs, blob, market_id="IN")
    first = sync_reconcile_findings("infy", out)
    second = sync_reconcile_findings("infy", out)
    assert first["enqueued"] >= 1
    assert second["enqueued"] == 0
    assert compute_company_gci(get_outcomes("infy")) == before

    cleared = sync_reconcile_findings("infy", {"conflicts": [], "quiet_drops": []})
    assert cleared["cleared"] >= 1
    assert compute_company_gci(get_outcomes("infy")) == before


def test_match_conflict_is_queued_once():
    from app.services.labeling_queue import sync_reconcile_findings

    g = "We expect constant currency revenue growth of 4% to 6% for FY25."
    r = "Reported revenue growth for FY25 was 5.5%."
    docs = [_pair("g", "2024-05-10", g), _pair("r", "2025-05-15", r)]
    blob = {"docs": {
        "g": {"date": "2024-05-10", "chunks": {"a": {"guidance": [
            {"metric": "revenue_growth_cc_pct", "period": "FY25", "low": 4, "high": 6, "quote": g}
        ], "results": []}}},
        "r": {"date": "2025-05-15", "chunks": {"a": {"guidance": [], "results": [
            {"metric": "revenue_growth_pct", "period": "FY25", "value": 5.5, "quote": r}
        ]}}},
    }}
    out = disclosures.reconcile("acme", docs, blob, market_id="IN")
    assert sync_reconcile_findings("infy", out)["enqueued"] == 1
    assert sync_reconcile_findings("infy", out)["enqueued"] == 0
