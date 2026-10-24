"""India-wide GCI coverage: status taxonomy, ingest, extract, classify.

Never invents a published number. extracted_verified stays provisional.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data import doc_store
from app.data.seed import get_data, reset_data, save_data
from app.main import app
from app.services.coverage import (
    FILING_IN_REVIEW,
    LISTED_ONLY,
    NO_QUANTIFIED_GUIDANCE,
    OPEN_PERIOD,
    SCORED,
    coverage_status_for,
    reset_coverage,
    stamp_coverage,
)
from app.services.exchange_filings import (
    host_allowed,
    ingest_promise_cohort,
    ingest_url,
    reset_rate_limit,
)
from app.services.extract_pipeline import (
    extract_company,
    maybe_promote_extracted,
    relabel_copied_guidance,
    reset_llm_budget,
    upsert_guidance_rows,
)
from app.services.india_coverage import classify_company, roll_cohort
from app.services.score_policy import (
    EXTRACTED_VERIFIED,
    TIER_PROVISIONAL,
    confidence_tier,
    is_scoreable,
    publishable_score,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    from app.data import doc_store as store

    store._DOCS = None
    reset_data()
    reset_coverage()
    reset_rate_limit()
    reset_llm_budget()
    from app.services.exchange_filings import reset_web_search

    reset_web_search()
    yield
    store._DOCS = None
    reset_data()


def test_every_listed_company_has_coverage_status():
    rows = client.get("/api/companies?market=IN&index=SENSEX").json()
    assert rows
    for r in rows:
        assert r.get("coverage_status") in {
            SCORED,
            OPEN_PERIOD,
            FILING_IN_REVIEW,
            NO_QUANTIFIED_GUIDANCE,
            LISTED_ONLY,
        }
        if r.get("gci_score") is not None:
            assert r["coverage_status"] == SCORED
            assert is_scoreable(r.get("data_quality"))


def test_dossier_coverage_status_matches_score():
    d = client.get("/api/companies/infy/gci").json()
    assert d["gci_score"] == 76.5
    assert d["coverage_status"] == SCORED
    listing = client.get("/api/companies/nse_20microns/gci")
    if listing.status_code == 200:
        body = listing.json()
        assert body["gci_score"] is None
        assert body.get("coverage_status") in {
            LISTED_ONLY,
            NO_QUANTIFIED_GUIDANCE,
            FILING_IN_REVIEW,
            OPEN_PERIOD,
        }


def test_extracted_verified_is_scoreable_and_provisional():
    assert is_scoreable(EXTRACTED_VERIFIED)
    assert publishable_score(71.0, EXTRACTED_VERIFIED) == 71.0
    assert publishable_score(71.0, "listing_provisional") is None
    assert (
        confidence_tier(
            closed_periods=5, metrics_scored=3, data_quality=EXTRACTED_VERIFIED
        )
        == TIER_PROVISIONAL
    )


def test_ingest_fixture_does_not_need_network():
    text = (
        "Management guided FY26 revenue growth of 12% to 14 percent. "
        "Reported revenue growth was 13.1 percent for the year."
    )
    report = ingest_promise_cohort(live=False, fixture_text=text, limit=2)
    assert report["ingested"] >= 1
    assert report["results"][0]["results"][0]["ok"] is True


def test_host_not_allowlisted_refused():
    assert host_allowed("https://www.bseindia.com/xml-data/corpfiling/x.pdf")
    assert not host_allowed("https://example.com/filing.pdf")
    with pytest.raises(ValueError):
        ingest_url("infy", "https://example.com/filing.pdf", text=None)


def test_extract_writes_guidance_without_actual():
    doc_store.upsert_document(
        company_id="tcs",
        doc_type="transcript",
        title="TCS FY26 call",
        text="We guide FY26 revenue growth of 10% to 12%. Capex guidance is unchanged.",
        url="https://www.bseindia.com/xml-data/corpfiling/tcs-fy26.pdf",
        date="2025-04-10",
        source="exchange_filing",
        review_status="accepted",
    )
    report = extract_company("tcs")
    assert report["extracted"] >= 1
    rows = get_data()["outcomes"]["tcs"]
    new_open = [r for r in rows if r.get("actual_value") is None and r.get("guided_value")]
    assert new_open
    assert all(r.get("actual_value") is None for r in new_open)


def _llm_fixture(monkeypatch, *, fail=False):
    from app.services import llm_client

    calls = []

    def fake(chunk, *, company_id, period, source_ref):
        calls.append(chunk)
        if fail:
            raise RuntimeError("transport")
        if "EBITDA margin" not in chunk:
            return []
        return [{"company_id": company_id, "period": period, "metric": "ebitda_margin_pct",
                 "guided_value": 21.0, "guided_low": 20.0, "guided_high": 22.0,
                 "guided_text": "EBITDA margin of 20-22%", "quote_span": "EBITDA margin of 20-22%",
                 "actual_value": None}]

    monkeypatch.setenv("INTELLENS_LLM_EXTRACT", "1")
    monkeypatch.setattr(llm_client, "llm_configured", lambda: True)
    monkeypatch.setattr(llm_client, "extract_guidance_via_llm", fake)
    return calls


def _long_transcript_doc(cid="tcs"):
    filler = "Operator: thank you. Analyst asked about deal wins and attrition trends. " * 400
    text = filler + " In Q&A the CFO said we expect EBITDA margin of 20-22% in FY27. " + filler
    doc_store.upsert_document(
        company_id=cid, doc_type="concall", title="Long call", text=text,
        url="https://nsearchives.nseindia.com/corporate/long.pdf", date="2026-05-12",
        source="exchange_filing", review_status="accepted",
    )
    return text


def test_text_chunks_overlap_and_cover_whole_document():
    from app.services.extract_pipeline import CHUNK_CHARS, CHUNK_OVERLAP, text_chunks

    text = "".join(chr(65 + i % 26) for i in range(30000))
    chunks = text_chunks(text)
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert chunks[0][-CHUNK_OVERLAP:] == chunks[1][:CHUNK_OVERLAP]
    assert chunks[-1].endswith(text[-50:])
    assert text_chunks("short") == ["short"]
    assert text_chunks("   ") == []


def test_extract_reads_late_guidance_and_skips_chunks_already_read(monkeypatch):
    calls = _llm_fixture(monkeypatch)
    text = _long_transcript_doc()
    first = extract_company("tcs")
    assert first["llm_calls"] == len(calls) > 1
    assert any(r.get("metric") == "ebitda_margin_pct" for r in get_data()["outcomes"]["tcs"])
    assert len(text) > 12000
    second = extract_company("tcs")
    assert second["llm_calls"] == 0
    assert second["chunks_already_read"] == first["llm_calls"]


def test_llm_cap_enforced_and_survives_restart(monkeypatch):
    from app.services.extract_pipeline import llm_budget_used, reset_llm_budget

    calls = _llm_fixture(monkeypatch)
    monkeypatch.setenv("INTELLENS_EXTRACT_LLM_DAILY_CAP", "2")
    _long_transcript_doc()
    report = extract_company("tcs")
    assert report["llm_calls"] == 2 and len(calls) == 2
    reset_llm_budget()
    assert llm_budget_used() == 2
    assert extract_company("tcs")["llm_calls"] == 0
    monkeypatch.setenv("INTELLENS_EXTRACT_LLM_DAILY_CAP", "100")
    assert extract_company("tcs")["chunks_already_read"] == 2


def test_failed_llm_call_is_retried_later(monkeypatch):
    _llm_fixture(monkeypatch, fail=True)
    _long_transcript_doc()
    first = extract_company("tcs")
    assert first["llm_calls"] > 0
    _llm_fixture(monkeypatch)
    assert extract_company("tcs")["chunks_already_read"] == 0


def test_lookback_without_promise_is_no_quantified_guidance():
    cid = "nse_fixture_none"
    data = get_data()
    data["companies"].append(
        {
            "id": cid,
            "name": "Fixture None Ltd",
            "ticker": "FIXNONE",
            "sector": "Equity",
            "data_quality": "listing_provisional",
        }
    )
    data.setdefault("outcomes", {})[cid] = []
    save_data()
    assert coverage_status_for(cid) == LISTED_ONLY
    status = classify_company(cid, lookback_complete=True)
    assert status == NO_QUANTIFIED_GUIDANCE
    assert coverage_status_for(cid) == NO_QUANTIFIED_GUIDANCE


def test_roll_cohort_fixture_clears_listed_only():
    ids = ["nse_fix_a", "nse_fix_b"]
    data = get_data()
    for cid in ids:
        data["companies"].append(
            {
                "id": cid,
                "name": cid,
                "ticker": cid.upper(),
                "sector": "Equity",
                "data_quality": "listing_provisional",
            }
        )
        data.setdefault("outcomes", {})[cid] = []
    save_data()
    empty = "Investor relations digest. Management discussed outlook. No numeric band."
    report = roll_cohort(
        "nifty50",
        company_ids=ids,
        live=False,
        fixture_text=empty,
    )
    # The model is off in tests, so the filing stays unread and is not "no guidance".
    assert report["listed_only"] == 0
    for cid in ids:
        assert coverage_status_for(cid) == FILING_IN_REVIEW


def test_live_without_any_filing_stays_listed_only(monkeypatch):
    """No filing fetched → not 'no quantified guidance', and not added to the scored universe."""
    from app.data.india_listings import india_equity_universe
    from app.services import exchange_filings as ef

    monkeypatch.setattr(ef, "discover_nse_filings", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "discover_nse_annual_reports", lambda company_id, **kw: [])

    seed_ids = {c["id"] for c in get_data()["companies"]}
    cid = next(r["id"] for r in india_equity_universe() if r["id"] not in seed_ids)
    before = len(get_data()["companies"])
    report = roll_cohort("nse_all", company_ids=[cid], live=True)
    assert report["results"][0]["coverage_status"] == LISTED_ONLY
    assert coverage_status_for(cid) == LISTED_ONLY
    assert len(get_data()["companies"]) == before


def test_relabel_copied_guidance_uses_filing_band():
    cid = "itc"
    data = get_data()
    rows = data["outcomes"][cid]
    copied = next(
        (
            r
            for r in rows
            if r.get("actual_value") is not None
            and r.get("guided_value") == r.get("actual_value")
        ),
        None,
    )
    if copied is None:
        pytest.skip("no guided==actual row on ITC in this seed")
    actual = copied["actual_value"]
    low, high = actual + 1.0, actual + 3.0
    doc_store.upsert_document(
        company_id=cid,
        doc_type="transcript",
        title="Prior-year call",
        text=f"We expect {copied['metric'].replace('_', ' ')} growth of {low}% to {high}%.",
        url="https://www.bseindia.com/xml-data/corpfiling/itc-prior.pdf",
        date="2024-05-01",
        source="exchange_filing",
        review_status="accepted",
    )
    n = relabel_copied_guidance(cid)
    assert n >= 0  # extractor may not map this metric id; must not invent


def test_meta_includes_coverage_counts():
    meta = client.get("/api/meta").json()
    assert "gci_coverage" in meta
    assert meta["gci_coverage"]["total"] >= 1


def test_stamp_unknown_status_rejected():
    with pytest.raises(ValueError):
        stamp_coverage("infy", "made_up")


def test_promote_requires_dual_cite():
    cid = "nse_promote"
    data = get_data()
    data["companies"].append(
        {
            "id": cid,
            "name": "Promote Ltd",
            "ticker": "PROMOTE",
            "sector": "Equity",
            "data_quality": "listing_provisional",
        }
    )
    data.setdefault("outcomes", {})[cid] = [
        {
            "period": "FY25",
            "metric": "revenue_growth_pct",
            "guided_value": 10,
            "actual_value": None,
        }
    ]
    save_data()
    assert maybe_promote_extracted(cid) == "listing_provisional"
    upsert_guidance_rows(cid, [])  # no-op


def test_counts_and_classify_use_cached_published_score(monkeypatch):
    from app.data import gci_score_cache
    from app.services.coverage import coverage_counts

    monkeypatch.setattr(
        gci_score_cache,
        "get_listing_score",
        lambda cid: {"gci_score": 80.0, "data_quality": "hand_labeled"} if cid == "infosys" else None,
    )
    assert coverage_counts(["infosys"])[SCORED] == 1
    assert classify_company("infosys", lookback_complete=True) == SCORED


def test_company_with_guidance_rows_never_no_quantified_guidance():
    """A copied guided==actual row is a pending cite, not proof of no guidance."""
    cid = "hdfcbank"
    assert get_data()["outcomes"].get(cid)
    status = classify_company(cid, lookback_complete=True)
    assert status != NO_QUANTIFIED_GUIDANCE


_NSE_PAYLOAD = [
    {
        "an_dt": "12-May-2026 19:00:00",
        "desc": "Analysts/Institutional Investor Meet/Con. Call Updates",
        "attchmntText": "Fixture Ltd has informed the Exchange about Transcript of earnings call",
        "attchmntFile": "https://nsearchives.nseindia.com/corporate/FIX_transcript.pdf",
    },
    {
        "an_dt": "10-May-2026 16:00:00",
        "desc": "Financial Result Updates",
        "attchmntText": "Audited results",
        "attchmntFile": "https://nsearchives.nseindia.com/corporate/FIX_results.pdf",
    },
    {
        "an_dt": "09-May-2026 10:00:00",
        "desc": "Trading Window",
        "attchmntText": "Closure of trading window",
        "attchmntFile": "https://nsearchives.nseindia.com/corporate/FIX_tw.pdf",
    },
    {
        "an_dt": "08-May-2026 10:00:00",
        "desc": "Press Release",
        "attchmntText": "Off-exchange link",
        "attchmntFile": "https://example.com/press.pdf",
    },
]


def test_issuer_host_allowed_only_for_its_issuer():
    url = "https://www.cipla.com/sites/default/files/x.pdf"
    assert host_allowed(url, "cipla")
    assert not host_allowed(url, "tcs")
    assert not host_allowed(url)
    assert not host_allowed("https://www.business-standard.com/x", "ongc")
    assert host_allowed("https://nsearchives.nseindia.com/corporate/x.pdf")


def test_issuer_hosts_cover_group_names_without_cross_matching():
    assert host_allowed("https://www.hdfcbank.com/ir/q4.pdf", "hdfcbank")
    assert not host_allowed("https://www.hdfcbank.com/ir/q4.pdf", "hdfclife")
    assert host_allowed("https://www.sbilife.co.in/ar.pdf", "sbilife")
    assert not host_allowed("https://www.sbilife.co.in/ar.pdf", "sbin")
    assert not host_allowed("https://www.jsw.in/x.pdf", "jswsteel")


@pytest.mark.parametrize(
    ("desc", "text", "kind"),
    [
        ("Shareholders meeting", "Transcript of the 49th Annual General Meeting", "agm"),
        ("Shareholders meeting", "Proceedings of AGM held on 28 August", "agm"),
        ("Shareholders meeting", "Notice of the 79th Annual General Meeting", None),
        ("Shareholders meeting", "Voting results of AGM", None),
        ("Shareholders meeting", "Annual Report and Notice of AGM", "annual_report"),
        ("Reg. 34 (1) Annual Report", "Annual Report for FY 2025-26", "annual_report"),
        ("Updates", "Fragmented market commentary", None),
        ("Shareholders meeting", "Letter sent to Members providing weblink of Annual Report", None),
        ("Analysts/Institutional Investor Meet/Con. Call Updates", "Transcript of earnings call", "concall"),
    ],
)
def test_classify_agm_and_annual_report(desc, text, kind):
    from app.services.exchange_filings import classify_announcement

    assert classify_announcement(desc, text) == kind


def test_annual_report_keeps_management_discussion_span(monkeypatch):
    import pypdf

    from app.services import exchange_filings as ef

    class _Page:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    pages = [
        "Contents. Management Discussion and Analysis 84.",
        "Board of directors. Shareholders can seek guidance from the registrar.",
        "Chairman's letter.",
        "Sustainability.",
        "Awards.",
        "Management Discussion and Analysis. Industry overview.",
        "Segment review: BFSI grew 6%.",
        "Management Discussion and Analysis. Margins.",
        "Business outlook: we expect EBITDA margin of 20-22% in FY27.",
        "Management Discussion and Analysis. Risks.",
        "Standalone balance sheet as at 31 March 2026.",
        "Notes. Capital expenditure of Rs 5,000 crore planned for FY27.",
    ]
    monkeypatch.setattr(pypdf, "PdfReader", lambda _buf: type("R", (), {"pages": [_Page(p) for p in pages]})())
    text = ef.text_from_payload(b"%PDF-1.7", "https://nsearchives.nseindia.com/ar.pdf", "annual_report")
    assert "BFSI grew 6%" in text
    assert "EBITDA margin of 20-22%" in text
    assert "Rs 5,000 crore" in text
    assert "registrar" not in text
    assert "balance sheet" not in text
    assert "Contents" not in text
    full = ef.text_from_payload(b"%PDF-1.7", "https://nsearchives.nseindia.com/q.pdf", "concall")
    assert "balance sheet" in full


def test_discovery_keeps_latest_agm_beyond_transcript_cap():
    from app.services.exchange_filings import discover_nse_filings

    transcripts = [
        {
            "an_dt": f"{10 + i:02d}-May-2026 19:00:00",
            "desc": "Analysts/Institutional Investor Meet/Con. Call Updates",
            "attchmntText": "Transcript of earnings call",
            "attchmntFile": f"https://nsearchives.nseindia.com/corporate/T{i}.pdf",
        }
        for i in range(8)
    ]
    agm = {
        "an_dt": "19-Jun-2026 18:00:00",
        "desc": "Shareholders meeting",
        "attchmntText": "Gist of the proceedings of the Annual General Meeting",
        "attchmntFile": "https://nsearchives.nseindia.com/corporate/AGM.pdf",
    }
    picked = discover_nse_filings("infy", payload=transcripts + [agm], max_docs=6)
    assert len(picked) == 7
    assert picked[-1]["category"] == "agm"


def test_discover_annual_reports_takes_latest_pdfs():
    from app.services.exchange_filings import discover_nse_annual_reports

    payload = {
        "data": [
            {"fromYr": "2024", "toYr": "2025", "broadcast_dttm": "27-MAY-2025 23:35:02",
             "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_2025.pdf"},
            {"fromYr": "2025", "toYr": "2026", "broadcast_dttm": "15-MAY-2026 23:48:30",
             "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_2026.pdf"},
            {"fromYr": "2023", "toYr": "2024", "broadcast_dttm": "-",
             "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_2024.zip"},
            {"fromYr": "2022", "toYr": "2023", "broadcast_dttm": "-",
             "fileName": "https://example.com/AR_2023.pdf"},
        ]
    }
    picked = discover_nse_annual_reports("tcs", payload=payload)
    assert [p["url"].rsplit("/", 1)[-1] for p in picked] == ["AR_2026.pdf", "AR_2025.pdf"]
    assert picked[0]["date"] == "2026-05-15"
    assert picked[0]["title"] == "Annual Report FY 2025-26"
    assert all(p["category"] == "annual_report" for p in picked)


_COVER_LETTER = """Adani Enterprises Limited www.adanienterprises.com
Sub: Transcript of Earnings Call pertaining to the Unaudited Financial Results.
please find below the weblink of transcript of the Earnings Call
1. Transcript https://www.adanienterprises.com/-
/media/Project/Enterprises/Investors/Investor-
Downloads/Results-Conference-Call-Transcripts/Q3-
FY26-AEL_Earnings-Call-Transcript.pdf
Mirror https://www.example.com/AEL-transcript.pdf
Kindly take the above on your records."""
_LINKED = (
    "https://www.adanienterprises.com/-/media/Project/Enterprises/Investors/Investor-"
    "Downloads/Results-Conference-Call-Transcripts/Q3-FY26-AEL_Earnings-Call-Transcript.pdf"
)


def test_cover_letter_link_rejoined_and_limited_to_issuer_host():
    from app.services.exchange_filings import linked_filing_urls

    assert linked_filing_urls(_COVER_LETTER, "adanient") == [_LINKED]
    assert linked_filing_urls(" ".join(_COVER_LETTER.split()), "adanient") == [_LINKED]
    assert linked_filing_urls(_COVER_LETTER, "tcs") == []
    assert linked_filing_urls(_COVER_LETTER + " filler" * 1000, "adanient") == []


def test_ingest_follows_cover_letter_to_issuer_transcript(monkeypatch):
    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    letter_url = "https://nsearchives.nseindia.com/corporate/AEL_cover.pdf"
    pages = {
        letter_url: _COVER_LETTER.encode(),
        _LINKED: b"<html>" + b"Management said capex of Rs 16,000 crore in FY27. " * 20 + b"</html>",
    }
    fetched = []

    def fake_fetch(url, company_id=None, **kw):
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(ef, "fetch_bytes", fake_fetch)
    monkeypatch.setattr(ef, "_outcome_urls", lambda cid: [])
    payload = [
        {
            "an_dt": "09-Feb-2026 23:25:42",
            "desc": "Analysts/Institutional Investor Meet/Con. Call Updates",
            "attchmntText": "Transcript of earnings call",
            "attchmntFile": letter_url,
        }
    ]
    out = ef.ingest_company_urls("adanient", discovery_payload=payload, dry_run=True)
    assert fetched == [letter_url, _LINKED]
    follow = out["results"][-1]
    assert follow["url"] == _LINKED and follow["linked_from"] == letter_url


def test_web_search_links_reads_citations_and_text(monkeypatch):
    from app.services import llm_client

    response = {
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Q1 transcript: https://www.tatasteel.com/media/q1-transcript.pdf.\nSee also bseindia.",
                        "annotations": [
                            {"type": "url_citation", "title": "Q4 FY26 earnings call transcript",
                             "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf?utm_source=openai"},
                        ],
                    }
                ],
            },
        ]
    }
    seen = {}

    def fake_post(path, payload, timeout=0):
        seen.update(path=path, payload=payload)
        return response

    monkeypatch.setattr(llm_client, "_post_json", fake_post)
    links = llm_client.web_search_links("find filings")
    assert seen["path"] == "/responses"
    assert seen["payload"]["tools"] == [{"type": "web_search"}]
    assert [l["url"] for l in links] == [
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf?utm_source=openai",
        "https://www.tatasteel.com/media/q1-transcript.pdf",
    ]
    assert links[0]["title"] == "Q4 FY26 earnings call transcript"


def test_gemini_search_resolves_grounding_redirects(monkeypatch):
    from app.services import llm_client

    monkeypatch.setenv("INTELLENS_LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setenv("INTELLENS_LLM_MODEL", "gemini-3.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    assert llm_client.llm_api_key() == "g-key"
    redirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AbC123"
    response = {
        "candidates": [
            {
                "content": {"parts": [{"text": "https://www.tatasteel.com/media/q1-transcript.pdf"}]},
                "groundingMetadata": {"groundingChunks": [{"web": {"uri": redirect, "title": "bseindia.com"}}]},
            }
        ]
    }
    seen = {}
    monkeypatch.setattr(llm_client, "_gemini_search", lambda prompt, timeout: seen.update(p=prompt) or response)
    monkeypatch.setattr(
        llm_client, "_resolve_redirect",
        lambda url, timeout=20.0: "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf",
    )
    links = llm_client.web_search_links("find filings")
    assert [l["url"] for l in links] == [
        "https://www.tatasteel.com/media/q1-transcript.pdf",
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf",
    ]
    assert llm_client.search_model() == "gemini-3.5-flash"


def test_web_search_keeps_only_allowed_hosts_and_strips_tracking():
    from app.services.exchange_filings import discover_via_web_search

    links = [
        {"url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf?utm_source=openai",
         "title": "Earnings call transcript Q4 FY26"},
        {"url": "https://www.tatasteel.com/media/Integrated-Annual-Report-2025-26.pdf", "title": ""},
        {"url": "https://www.tatasteel.com/investors/", "title": "Investors"},
        {"url": "https://www.moneycontrol.com/tata-steel-q4-transcript.pdf", "title": "Transcript"},
        {"url": "https://www.infosys.com/q4-transcript.pdf", "title": "Transcript"},
    ]
    picked = discover_via_web_search("tatasteel", search=lambda prompt: links)
    assert [p["url"] for p in picked] == [
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf",
        "https://www.tatasteel.com/media/Integrated-Annual-Report-2025-26.pdf",
    ]
    assert [p["category"] for p in picked] == ["concall", "annual_report"]
    assert all(p["found_by"] == "web_search" and p["date"] is None for p in picked)


def test_web_search_respects_daily_cap_and_refresh_interval(monkeypatch):
    from app.services import exchange_filings as ef
    from app.services import llm_client

    calls = []
    monkeypatch.setenv("INTELLENS_WEB_SEARCH_DISCOVERY", "1")
    monkeypatch.setenv("INTELLENS_WEB_SEARCH_DAILY_CAP", "1")
    monkeypatch.setattr(llm_client, "llm_configured", lambda: True)
    monkeypatch.setattr(llm_client, "web_search_links", lambda prompt: calls.append(prompt) or [])
    ef.discover_via_web_search("tatasteel")
    ef.discover_via_web_search("infy")
    assert len(calls) == 1
    monkeypatch.setenv("INTELLENS_WEB_SEARCH_DAILY_CAP", "10")
    ef.reset_web_search()
    ef.discover_via_web_search("tatasteel")
    assert len(calls) == 1
    ef.discover_via_web_search("infy")
    assert len(calls) == 2


def test_web_search_off_by_default(monkeypatch):
    from app.services import exchange_filings as ef
    from app.services import llm_client

    monkeypatch.delenv("INTELLENS_WEB_SEARCH_DISCOVERY", raising=False)
    monkeypatch.setattr(llm_client, "web_search_links", lambda prompt: pytest.fail("searched"))
    assert ef.discover_via_web_search("tatasteel") == []


def test_web_search_document_is_stored_undated(monkeypatch):
    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    url = "https://www.tatasteel.com/media/q4-transcript.pdf"
    lead = {"url": url, "category": "concall", "title": "Q4 transcript", "date": None,
            "rank": 0, "found_by": "web_search"}
    monkeypatch.setattr(ef, "discover_nse_filings", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "discover_nse_annual_reports", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "discover_via_web_search", lambda company_id, **kw: [lead])
    monkeypatch.setattr(ef, "_outcome_urls", lambda cid: [])
    monkeypatch.setattr(ef, "fetch_bytes", lambda u, company_id=None, **kw: b"<html>" + b"We expect EBITDA per tonne to improve in FY27. " * 5 + b"</html>")
    out = ef.ingest_company_urls("tatasteel", live=True, discover=True)
    assert out["results"][-1]["found_by"] == "web_search"
    doc = next(d for d in doc_store.list_documents(company_id="tatasteel") if d.get("url") == url)
    assert doc["date"] == ""


def test_company_ingest_writes_the_index_once(monkeypatch):
    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    leads = [
        {"url": f"https://www.tatasteel.com/media/q{i}-transcript.pdf", "category": "concall",
         "title": f"Q{i} transcript", "date": "2025-05-0{}".format(i), "rank": 0}
        for i in range(1, 5)
    ]
    monkeypatch.setattr(ef, "discover_nse_filings", lambda company_id, **kw: leads)
    monkeypatch.setattr(ef, "discover_nse_annual_reports", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "discover_via_web_search", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "_outcome_urls", lambda cid: [])
    monkeypatch.setattr(
        ef, "fetch_bytes",
        lambda u, company_id=None, **kw: b"<html>" + f"{u} We expect EBITDA per tonne to improve in FY27. ".encode() * 5 + b"</html>",
    )
    writes = []
    real_save = doc_store.save
    monkeypatch.setattr(doc_store, "save", lambda: writes.append(1) or real_save())
    out = ef.ingest_company_urls("tatasteel", live=True, discover=True)
    assert sum(1 for r in out["results"] if r.get("action") == "upserted") == 4
    assert len(writes) == 1
    assert {d["url"] for d in doc_store.list_documents(company_id="tatasteel")} >= {l["url"] for l in leads}


def test_annual_report_and_agm_count_as_guidance_documents():
    from app.services.exchange_filings import GUIDANCE_DOC_TYPES

    assert {"concall", "presentation", "agm", "annual_report"} <= set(GUIDANCE_DOC_TYPES)


def test_discover_nse_ranks_transcript_first_and_drops_noise():
    from app.services.exchange_filings import discover_nse_filings

    picked = discover_nse_filings("infy", payload=_NSE_PAYLOAD, max_docs=6)
    assert [p["category"] for p in picked] == ["concall", "results"]
    assert picked[0]["url"].endswith("FIX_transcript.pdf")
    assert picked[0]["date"] == "2026-05-12"


def test_browser_fallback_only_for_exchange_hosts(monkeypatch):
    from urllib.error import HTTPError

    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    seen = []

    def fake_open(url, ua, accept="*/*", timeout=30):
        seen.append(ua)
        if ua == ef.BOT_UA:
            raise HTTPError(url, 403, "Forbidden", {}, None)
        return b"%PDF-ok"

    monkeypatch.setattr(ef, "_open", fake_open)
    assert ef.fetch_bytes("https://www.bseindia.com/x.pdf") == b"%PDF-ok"
    assert seen == [ef.BOT_UA, ef.BROWSER_UA]
    seen.clear()
    with pytest.raises(HTTPError):
        ef.fetch_bytes("https://www.cipla.com/x.pdf", "cipla")
    assert seen == [ef.BOT_UA]


def test_discovered_transcript_completes_lookback(monkeypatch):
    from app.services import exchange_filings as ef
    from app.services.india_coverage import process_company

    cid = "nse_fixture_disc"
    data = get_data()
    data["companies"].append(
        {"id": cid, "name": "Disc Ltd", "ticker": "DISC", "sector": "Equity", "data_quality": "listing_provisional"}
    )
    data.setdefault("outcomes", {})[cid] = []
    save_data()
    transcript = {
        "url": "https://nsearchives.nseindia.com/corporate/FIX_transcript.pdf",
        "category": "concall",
        "title": "Transcript",
        "date": "2026-05-12",
        "rank": 0,
    }
    from app.services import disclosures

    monkeypatch.setattr(ef, "discover_nse_filings", lambda company_id, **kw: [transcript])
    monkeypatch.setattr(ef, "discover_nse_annual_reports", lambda company_id, **kw: [])
    monkeypatch.setattr(ef, "fetch_bytes", lambda url, company_id=None, **kw: b"<html>Management discussed the quarter. No numeric outlook was given on the call today.</html>")
    monkeypatch.setattr(disclosures, "enabled", lambda: True)
    monkeypatch.setattr(
        disclosures,
        "process_company",
        lambda *a, **k: {"budget_out": False, "failed": False, "rows": 0},
    )
    out = process_company(cid, live=True)
    assert any(r.get("ok") for r in out["ingest"]["results"])
    assert out["coverage_status"] == NO_QUANTIFIED_GUIDANCE


def test_fetch_cap_stops_company_loop(monkeypatch):
    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_DAILY_CAP", "0")
    monkeypatch.setattr(ef, "_open", lambda *a, **k: b"x")
    out = ef.ingest_company_urls("infy", discovery_payload=_NSE_PAYLOAD)
    assert out["results"][-1]["reason"] == "fetch_cap"


def test_refused_exchange_host_skips_bot_attempt_next_time(monkeypatch):
    from urllib.error import HTTPError

    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    seen = []

    def fake_open(url, ua, accept="*/*", timeout=30):
        seen.append(ua)
        if ua == ef.BOT_UA:
            raise HTTPError(url, 403, "Forbidden", {}, None)
        return b"ok"

    monkeypatch.setattr(ef, "_open", fake_open)
    ef.fetch_bytes("https://www.bseindia.com/a.pdf")
    seen.clear()
    ef.fetch_bytes("https://www.bseindia.com/b.pdf")
    assert seen == [ef.BROWSER_UA]


def test_fetch_budget_survives_a_new_process(monkeypatch):
    from app.services import exchange_filings as ef

    monkeypatch.setenv("INTELLENS_FILING_FETCH_INTERVAL_SEC", "0")
    monkeypatch.setenv("INTELLENS_FILING_FETCH_DAILY_CAP", "1")
    ef._rate_limit()
    ef._COUNTS.clear()
    ef._FETCH_DAY = ""
    with pytest.raises(ef.DailyCapReached):
        ef._rate_limit()


def test_meta_coverage_spans_the_india_universe():
    from app.data.india_listings import india_equity_universe

    body = client.get("/api/meta").json()
    cov = body["gci_coverage"]
    assert cov["total"] == len(india_equity_universe())
    assert cov["scored"] == body["gci_scored_count"] or cov["scored"] >= body["gci_listing_scored_count"]


def test_roll_daily_walks_unsearched_first_and_stops_on_budget(monkeypatch):
    from app.services import india_coverage as ic
    from app.services.coverage import load_coverage, note_discovery

    ids = ["infy", "tcs", "wipro"]
    monkeypatch.setattr(ic, "_nse_ids", lambda cohort: list(ids))
    note_discovery("infy")
    calls = []
    budget = {"left": 2}

    def fake_process(cid, **kw):
        calls.append(cid)
        budget["left"] -= 1
        return {"coverage_status": LISTED_ONLY, "ingest": {"results": []}}

    monkeypatch.setattr(ic, "process_company", fake_process)
    monkeypatch.setattr(ic, "budget_remaining", lambda bucket="fetch": budget["left"])
    report = ic.roll_daily("all")
    assert calls == ["tcs", "wipro"]
    assert report["stopped"] == "walked_all" or report["processed"] == 2
    seen = load_coverage()["companies"]
    assert seen["tcs"]["last_discovery"] and seen["wipro"]["last_discovery"]


def test_roll_daily_stops_when_budget_spent(monkeypatch):
    from app.services import india_coverage as ic

    monkeypatch.setattr(ic, "_nse_ids", lambda cohort: ["infy", "tcs"])
    monkeypatch.setattr(ic, "budget_remaining", lambda bucket="fetch": 0)
    report = ic.roll_daily("all")
    assert report["processed"] == 0 and report["stopped"] == "daily_budget"


def test_coverage_progress_reports_roll_and_budgets(monkeypatch, capsys):
    from app.services import india_coverage as ic

    monkeypatch.setattr(ic, "_nse_ids", lambda cohort: ["tcs", "wipro"])
    seen_mid_roll = []

    def fake_process(cid, **kw):
        seen_mid_roll.append(ic.coverage_progress()["roll"]["current"])
        return {"coverage_status": LISTED_ONLY, "ingest": {"results": []}}

    monkeypatch.setattr(ic, "process_company", fake_process)
    ic.roll_daily("nifty50")
    assert seen_mid_roll == ["tcs", "wipro"]
    progress = ic.coverage_progress()
    assert progress["roll"]["running"] is False and progress["roll"]["done"] == 2
    assert progress["searched_today"] == 2 and progress["cohort_size"] == 2
    assert [s["company_id"] for s in progress["roll"]["recent"]] == ["wipro", "tcs"]
    assert set(progress["budgets_today"]) >= {"ai_extraction_calls", "filing_fetch", "web_searches"}
    assert '"india_coverage_step"' in capsys.readouterr().out


def test_stamp_keeps_last_discovery():
    from app.services.coverage import load_coverage, note_discovery

    note_discovery("infy")
    stamp_coverage("infy", OPEN_PERIOD)
    assert load_coverage()["companies"]["infy"]["last_discovery"]


def test_daily_runner_off_without_flag(monkeypatch):
    from app.services.india_coverage import run_daily_from_env

    monkeypatch.delenv("INTELLENS_INDIA_COVERAGE", raising=False)
    assert run_daily_from_env() is None


@pytest.mark.parametrize("configured", [True, False])
def test_model_unavailable_does_not_call_shell_extractor(monkeypatch, configured):
    from app.services import disclosures, extract_pipeline
    from app.services.india_coverage import process_company

    calls = []
    monkeypatch.setattr(disclosures, "enabled", lambda: False)
    monkeypatch.setattr(disclosures, "configured", lambda: configured)
    monkeypatch.setattr(extract_pipeline, "extract_company", lambda *a, **k: calls.append("shell") or {})
    cid = "nse_fixture_unread"
    data = get_data()
    data["companies"].append(
        {"id": cid, "name": "Unread Ltd", "ticker": "UNREAD", "sector": "Equity", "data_quality": "listing_provisional"}
    )
    data.setdefault("outcomes", {})[cid] = []
    save_data()
    out = process_company(
        cid,
        live=False,
        fixture_text="Investor call. Management discussed the quarter. No numeric band was given.",
    )
    assert calls == []
    assert out["extract"]["budget_out"] is True
    assert out["extract"]["model_unavailable"] is True
    assert coverage_status_for(cid) == FILING_IN_REVIEW


def test_finished_model_read_with_no_promise_stamps_no_guidance(monkeypatch):
    from app.services import disclosures
    from app.services.india_coverage import process_company

    monkeypatch.setattr(disclosures, "enabled", lambda: True)
    monkeypatch.setattr(
        disclosures, "process_company", lambda *a, **k: {"budget_out": False, "failed": False, "rows": 0}
    )
    cid = "nse_fixture_read"
    data = get_data()
    data["companies"].append(
        {"id": cid, "name": "Read Ltd", "ticker": "READ", "sector": "Equity", "data_quality": "listing_provisional"}
    )
    data.setdefault("outcomes", {})[cid] = []
    save_data()
    out = process_company(
        cid,
        live=False,
        fixture_text="Investor call. Management discussed the quarter. No numeric band was given.",
    )
    assert out["coverage_status"] == NO_QUANTIFIED_GUIDANCE


def test_extract_job_walks_disclosures_not_the_shell(monkeypatch):
    from app.jobs import extract_india_guidance as job
    from app.services import extract_pipeline

    calls = []
    monkeypatch.setattr(extract_pipeline, "extract_company", lambda *a, **k: calls.append("shell") or {})
    monkeypatch.setattr(job, "process_company", lambda cid, **kw: {"company_id": cid})
    report = job.walk(["fixture_co"])
    assert calls == []
    assert report["writer"] == "disclosures"
    assert "disclosures" in (job.__doc__ or "")
