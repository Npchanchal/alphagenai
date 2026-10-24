"""SEC results releases: submissions filter, index parse, ingest and the US walk — no network."""

from __future__ import annotations

import pytest

from app.data import doc_store
from app.data.seed import get_data, reset_data
from app.services import sec_filings, us_coverage
from app.services.coverage import reset_coverage

PAD = " NVIDIA is the world leader in accelerated computing. Forward-looking statements are subject to risk." * 3

INDEX = """
<table>
<tr><td>1</td><td>8-K</td><td><a href="/ix?doc=/Archives/edgar/data/1045810/000104581023000017/nvda-20230222.htm">nvda-20230222.htm</a></td><td>8-K</td></tr>
<tr><td>2</td><td>Press release</td><td><a href="/Archives/edgar/data/1045810/000104581023000017/q4fy23pr.htm">q4fy23pr.htm</a></td><td>EX-99.1</td></tr>
<tr><td>3</td><td>CFO Commentary</td><td><a href="/Archives/edgar/data/1045810/000104581023000017/q4fy23cfo.htm">q4fy23cfo.htm</a></td><td>EX-99.2</td></tr>
<tr><td>4</td><td>Graphic</td><td><a href="/Archives/edgar/data/1045810/000104581023000017/logo.jpg">logo.jpg</a></td><td>EX-99.3</td></tr>
</table>
"""


def _payload():
    return {
        "name": "NVIDIA CORP",
        "fiscalYearEnd": "0131",
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q", "8-K", "8-K"],
                "items": ["2.02,9.01", "", "5.02", "2.02,9.01"],
                "filingDate": ["2023-05-24", "2023-05-26", "2023-03-01", "2021-11-17"],
                "accessionNumber": ["0001045810-23-000035", "x", "y", "0001045810-21-000163"],
                "reportDate": ["2023-05-24", "", "", "2021-11-17"],
            }
        },
    }


def test_results_filings_keeps_item_202_since_date():
    out = sec_filings.results_filings("1045810", since="2022-01-01", payload=_payload())
    assert out["fiscal_year_end"] == "0131"
    assert [f["accession"] for f in out["filings"]] == ["0001045810-23-000035"]


def test_index_parse_picks_release_and_commentary_only():
    exhibits = sec_filings.exhibits_from_index(INDEX)
    assert [e["type"] for e in exhibits] == ["EX-99.1", "EX-99.2"]
    assert exhibits[0]["url"].startswith("https://www.sec.gov/Archives/")
    assert [e["type"] for e in sec_filings.pick_exhibits(exhibits)] == ["EX-99.1", "EX-99.2"]


def test_only_sec_hosts():
    assert sec_filings.is_sec_host("https://www.sec.gov/Archives/x.htm")
    assert not sec_filings.is_sec_host("https://example.com/sec.gov")


@pytest.fixture()
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    doc_store._DOCS = None
    reset_data()
    reset_coverage()
    yield
    doc_store._DOCS = None
    reset_data()


GUIDE = (
    "<html><body><p>NVIDIA Announces Financial Results for Fourth Quarter and Fiscal 2023.</p>"
    "<p>Outlook NVIDIA's outlook for the first quarter of fiscal 2024 is as follows:</p>"
    "<p>Revenue is expected to be $6.50 billion, plus or minus 2%.</p>" + PAD + "</body></html>"
)
RESULT = (
    "<html><body><p>NVIDIA (NASDAQ: NVDA) today reported revenue for the first quarter ended April 30, 2023, "
    "of $7.19 billion, down 13% from a year ago and up 19% from the previous quarter.</p>" + PAD + "</body></html>"
)


def _fake_fetch(url: str) -> bytes:
    if url.endswith("-index.htm"):
        acc = "000104581023000017" if "000104581023000017" in url else "000104581023000035"
        return INDEX.replace("000104581023000017", acc).encode()
    if "000104581023000017" in url and url.endswith("pr.htm"):
        return GUIDE.encode()
    if "000104581023000035" in url and url.endswith("pr.htm"):
        return RESULT.encode()
    return f"<html><body>{url}{PAD}</body></html>".encode()


LISTING = {
    "fiscal_year_end": "0131",
    "name": "NVIDIA CORP",
    "filings": [
        {"accession": "0001045810-23-000035", "date": "2023-05-24", "form": "8-K", "report_date": ""},
        {"accession": "0001045810-23-000017", "date": "2023-02-22", "form": "8-K", "report_date": ""},
    ],
}


def test_ingest_is_idempotent(_isolated):
    first = sec_filings.ingest_company("us_nvda", "1045810", ticker="NVDA", listing=LISTING, fetch=_fake_fetch)
    again = sec_filings.ingest_company("us_nvda", "1045810", ticker="NVDA", listing=LISTING, fetch=_fake_fetch)
    assert first["added"] == 4 and first["failed"] == 0
    assert again["added"] == 0 and again["already_stored"] == 4
    docs = doc_store.list_documents(company_id="us_nvda")
    assert {d["source"] for d in docs} == {"sec_filing"}


def test_us_walk_matches_promise_to_reported_quarter(_isolated):
    out = us_coverage.process_company(
        "us_nvda", extractor=lambda chunk, **kw: {"guidance": [], "results": []}, listing=LISTING, fetch=_fake_fetch
    )
    assert out["read"]["closed"] == 1
    company = next(c for c in get_data()["companies"] if c["id"] == "us_nvda")
    assert company["market_id"] == "US" and company["fiscal_year_end"] == "0131"
    (row,) = [r for r in get_data()["outcomes"]["us_nvda"] if r["actual_value"] is not None]
    assert (row["period"], row["guided_low"], row["guided_high"], row["actual_value"]) == (
        "Q1 FY2024", 6370.0, 6630.0, 7190.0
    )
    assert row["guidance_source_url"].endswith("pr.htm") and row["source_url"].endswith("pr.htm")
    assert row["guidance_source_url"] != row["source_url"]


def test_incomplete_read_is_dated_so_the_walk_moves_on(_isolated):
    from app.services.coverage import persisted_row

    us_coverage.process_company("us_nvda", extractor=None, listing=LISTING, fetch=_fake_fetch)
    row = persisted_row("us_nvda")
    assert row.get("last_discovery")
    assert not row.get("lookback_since")
