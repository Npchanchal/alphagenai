"""Daily guidance-quote and later-filing review. One market per day. No invented scores."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from app.data.seed import get_outcomes, reset_data
from app.services.guidance_review import (
    REVIEWER,
    bind_from_documents,
    market_for_day,
    market_ids,
    parameters_for_company,
    row_gaps,
    run_daily,
    seconds_until_next_run,
)


def _guidance_doc() -> dict:
    return {
        "period": "FY25",
        "doc_id": "doc-fy25",
        "text": "we are up by about 2.5% on volume terms",
        "url": "https://example.test/guidance.pdf",
        "date": "2024-05-08",
        "source": "bse",
        "review_status": "accepted",
    }


def test_daily_run_is_0230_ist():
    morning = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    assert seconds_until_next_run(morning) == 11 * 3600
    after = datetime(2026, 10, 1, 21, 30, tzinfo=timezone.utc)
    assert seconds_until_next_run(after) == 23 * 3600 + 30 * 60


def test_rotation_covers_every_market_once_per_cycle():
    start = date(2026, 10, 1)
    seen = [market_for_day(date.fromordinal(start.toordinal() + i)) for i in range(len(market_ids()))]
    assert seen == market_ids() or set(seen) == set(market_ids())
    assert len(seen) == len(set(seen)) == len(market_ids())


def test_row_gaps_name_the_missing_side():
    assert row_gaps(
        {
            "actual_value": 4.2,
            "source_url": "https://example.test/filing.pdf",
            "quote_span": "revenue growth of 4.2%",
            "as_of": "2025-04-17",
        }
    ) == ["missing_guidance_cite"]
    assert "awaiting_later_filing" in row_gaps(
        {
            "actual_value": None,
            "guided_value": 3.5,
            "guidance_source_url": "https://example.test/guidance.pdf",
            "guidance_quote": "growth of 2% to 5%",
            "guidance_as_of": "2025-04-17",
            "source_url": "https://example.test/guidance.pdf",
            "quote_span": "growth of 2% to 5%",
            "as_of": "2025-04-17",
        }
    )
    assert "source_unverified" in row_gaps(
        {
            "actual_value": 4.6,
            "source_url": "https://example.test/press",
            "quote_span": "growth of 4.6%",
            "as_of": "2025-04-25",
            "source_verified": False,
        }
    )


def test_bind_copies_the_filing_sentence_when_the_number_is_in_it():
    row = {
        "period": "FY25",
        "metric": "volume_growth_pct",
        "guided_value": 2.5,
        "actual_value": 2.4,
        "source_url": "https://example.test/results.pdf",
        "quote_span": "volume growth was 2.4 percent for the year",
        "as_of": "2025-05-08",
    }
    doc = _guidance_doc()
    results = {
        "period": "FY25",
        "text": "volume growth was 2.4 percent for the year",
        "url": "https://example.test/results.pdf",
        "date": "2025-05-08",
        "review_status": "accepted",
    }
    assert bind_from_documents(row, [doc, results]) is True
    assert row["guidance_quote"] == doc["text"]
    assert row["guidance_source_url"] == doc["url"]
    assert row["guidance_as_of"] == "2024-05-08"
    assert row["reviewed_by"] == REVIEWER
    assert row["actual_value"] == 2.4


def test_bind_refuses_a_filing_that_names_a_different_metric():
    row = {
        "period": "FY25",
        "metric": "revenue_growth_pct",
        "guided_value": 2.5,
        "actual_value": None,
    }
    assert bind_from_documents(row, [_guidance_doc()]) is False
    assert "guidance_quote" not in row


def test_bind_requires_both_ends_of_a_recorded_band():
    row = {
        "period": "FY25",
        "metric": "revenue_growth_cc_pct",
        "guided_low": 12.0,
        "guided_high": 14.0,
        "actual_value": None,
    }
    one_end = {
        "period": "FY25",
        "text": "revenue growth of 12% in constant currency",
        "url": "https://example.test/guidance.pdf",
        "date": "2024-04-13",
    }
    assert bind_from_documents(row, [one_end]) is False
    both = {
        **one_end,
        "text": "revenue growth guidance of 12% to 14% in constant currency",
    }
    assert bind_from_documents(row, [both]) is True
    assert row["guidance_quote"] == both["text"]
    assert "reviewed_by" not in row


def test_capex_requires_a_currency_unit():
    row = {
        "period": "FY25",
        "metric": "capex_guidance",
        "guided_value": 2500,
        "actual_value": None,
    }
    bare = {
        "period": "FY25",
        "text": "capex of about 2500 for the year",
        "url": "https://example.test/capex.pdf",
        "date": "2024-05-08",
    }
    assert bind_from_documents(row, [bare]) is False
    crore = {**bare, "text": "capex of about 2500 crore for the year"}
    assert bind_from_documents(row, [crore]) is True
    assert row["guidance_quote"] == crore["text"]


def _margin_row(**kw) -> dict:
    return {
        "period": "FY25",
        "metric": "ebitda_margin_pct",
        "guided_low": 24.5,
        "guided_high": 25.5,
        "actual_value": None,
        **kw,
    }


def test_bind_never_confirms_a_number_from_our_own_labelling_note():
    note = "FY25 EBITDA margin guidance 24.5%–25.5%; year printed 25.9% (beat / exceeded band)."
    row = _margin_row(guided_text=note)
    excerpt = {
        "period": "FY25",
        "text": f"{note}\nmanagement remains confident on margins\nSource: CIPLA-Q4FY24-FY25-guide",
        "url": "https://example.test/guide.pdf",
        "date": "2024-05-10",
        "source": "CIPLA-Q4FY24-FY25-guide",
    }
    assert bind_from_documents(row, [excerpt]) is False
    assert "guidance_quote" not in row
    verbatim = {**excerpt, "text": f"{note}\n24.5% to 25.5% to EBITDA margin\nSource: CIPLA-Q4FY24-FY25-guide"}
    assert bind_from_documents(row, [verbatim]) is True
    assert row["guidance_quote"] == "24.5% to 25.5% to EBITDA margin"


def test_bind_refuses_a_promise_dated_late_in_or_after_the_period():
    for when in ("2025-01-28", "2025-05-13"):  # Q3 reaffirmation; after FY25 closed
        row = _margin_row()
        doc = {"period": "FY25", "text": "EBITDA margin of 24.5% to 25.5%", "url": "https://example.test/g.pdf",
               "date": when}
        assert bind_from_documents(row, [doc]) is False, when
        assert "guidance_quote" not in row


def test_bind_refuses_a_result_dated_before_the_period_ends():
    row = _margin_row(actual_value=25.9, guidance_source_url="https://example.test/g.pdf",
                      guidance_quote="EBITDA margin of 24.5% to 25.5%", guidance_as_of="2024-05-10")
    early = {"period": "FY25", "text": "EBITDA margin was 25.9%", "url": "https://example.test/r.pdf",
             "date": "2025-01-28"}
    assert bind_from_documents(row, [early]) is False
    assert "quote_span" not in row


def test_bind_files_one_promise_per_period_and_metric():
    doc = {"period": "FY25", "text": "EBITDA margin of 24.5% to 25.5%", "url": "https://example.test/g.pdf",
           "date": "2024-05-10"}
    first, second = _margin_row(), _margin_row()
    rows = [first, second]
    assert bind_from_documents(first, [doc], outcomes=rows) is True
    assert bind_from_documents(second, [doc], outcomes=rows) is False
    assert "guidance_quote" not in second


def test_a_bank_metric_is_not_filed_for_an_it_company():
    row = {
        "period": "FY25",
        "metric": "nim_pct",
        "guided_low": 3.4,
        "guided_high": 3.6,
        "actual_value": None,
    }
    doc = {
        "period": "FY25",
        "text": "NIM guided at 3.4% to 3.6%",
        "url": "https://example.test/nim.pdf",
        "date": "2024-04-20",
    }
    assert bind_from_documents(row, [doc], company={"id": "infy", "sector": "IT Services"}) is False
    assert bind_from_documents(row, [doc], company={"id": "hdfcbank", "sector": "Banks"}) is True


def test_parameters_follow_the_stock():
    bank = {row["id"] for row in parameters_for_company({"sector": "Banks"}, [])}
    it = {row["id"] for row in parameters_for_company({"sector": "IT Services"}, [])}
    assert "nim_pct" in bank
    assert "loan_growth_pct" in bank
    assert "nim_pct" not in it
    assert "revenue_growth_cc_pct" in it
    assert "rd_spend_pct_of_revenue" in it
    extra = parameters_for_company(
        {"sector": "IT Services"},
        [{"metric": "nim_pct"}],
    )
    assert "nim_pct" in {row["id"] for row in extra}


def test_bind_does_not_file_the_reported_actual_as_the_promise():
    row = {
        "period": "FY25",
        "metric": "revenue_growth_pct",
        "guided_value": 15.3,
        "actual_value": 15.3,
        "source_url": "https://example.test/results.pdf",
        "quote_span": "revenue grew 15.3 percent year on year",
        "as_of": "2025-05-08",
    }
    doc = {
        "period": "FY25",
        "text": "revenue grew 15.3 percent year on year",
        "url": "https://example.test/guidance.pdf",
        "date": "2025-04-01",
    }
    assert bind_from_documents(row, [doc]) is False
    assert "guidance_quote" not in row
    assert "reviewed_by" not in row


def test_bind_leaves_the_row_when_the_number_is_absent():
    row = {"period": "FY25", "guided_value": 9.0, "actual_value": None}
    assert bind_from_documents(row, [_guidance_doc()]) is False
    assert "guidance_quote" not in row
    assert row["actual_value"] is None


def test_bind_does_not_invent_an_actual_for_an_open_period():
    doc = _guidance_doc()
    row = {
        "period": "FY25",
        "guided_value": 2.5,
        "actual_value": None,
        "guidance_source_url": doc["url"],
        "guidance_quote": doc["text"],
        "guidance_as_of": "2025-05-08",
    }
    assert bind_from_documents(row, [doc]) is False
    assert row["actual_value"] is None
    assert "quote_span" not in row


def test_bind_keeps_an_unverified_quote_until_a_filing_contains_it():
    row = {
        "period": "FY25",
        "guided_value": 2.5,
        "actual_value": 4.6,
        "guidance_source_url": "https://example.test/guidance.pdf",
        "guidance_quote": "we are up by about 2.5% on volume terms",
        "guidance_as_of": "2025-05-08",
        "source_url": "https://example.test/press",
        "quote_span": "growth of 4.6% was reported in the press note",
        "as_of": "2025-05-09",
        "source_verified": False,
    }
    assert bind_from_documents(row, [_guidance_doc()]) is False
    assert row["source_verified"] is False
    assert row["source_url"] == "https://example.test/press"
    assert "reviewed_by" not in row


def test_dry_run_does_not_persist_or_queue(monkeypatch, tmp_path):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    reset_data()
    before = json.dumps(get_outcomes("asianpaints"), sort_keys=True, default=str)
    report = run_daily(day=date(2026, 10, 1), market_id="IN", dry_run=True)
    after = json.dumps(get_outcomes("asianpaints"), sort_keys=True, default=str)
    assert before == after
    assert report["ok"] is True
    assert report["dry_run"] is True
    assert "queued" not in report
    assert report["hand_labeled"] > 0


def test_same_day_without_force_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    reset_data()
    run_daily(day=date(2026, 10, 2), market_id="JP")
    again = run_daily(day=date(2026, 10, 2), market_id="US")
    assert again["skipped"] is True
    assert again["reason"] == "already_ran"


def test_other_markets_bind_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    reset_data()
    report = run_daily(day=date(2026, 10, 3), market_id="US", dry_run=True)
    assert report["ok"] is True
    assert report["hand_labeled"] == 0
    assert report["bound_rows"] == 0
    assert report["dry_run"] is True


def test_unknown_market_is_rejected():
    assert run_daily(market_id="XX", dry_run=True)["ok"] is False
