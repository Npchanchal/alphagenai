"""A5 India event Skills: three golden cases each with expected citations, plus event classification."""

import json
from pathlib import Path

import pytest

from app.data import doc_store
from app.data.seed import reset_data
from app.services import event_filings
from app.services.agent import projects, runtime, uploads

CASES = json.loads((Path(__file__).parent / "golden" / "a5_cases.json").read_text())["cases"]
A5_SKILLS = {"corporate_action_brief", "drhp_reader", "usfda_watch", "rating_tracker", "debate_map"}


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(doc_store, "_DOCS", None)
    reset_data()
    yield
    doc_store._DOCS = None


def test_three_golden_cases_per_skill():
    counts = {}
    for c in CASES:
        counts[c["skill"]] = counts.get(c["skill"], 0) + 1
    assert set(counts) == A5_SKILLS and all(n >= 3 for n in counts.values())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_case(case):
    for i, d in enumerate(case["docs"]):
        doc_store.upsert_document(company_id=case["company_id"], source="exchange_filing",
                                  url=f"https://example.invalid/{case['id']}-{i}.pdf", **d)
    kwargs = {}
    if case.get("upload"):
        p = projects.create_project(org_id="o1", created_by="u", name="Stub IPO", company_ids=[case["company_id"]])
        uploads.add_upload(org_id="o1", project_id=p["project_id"], filename=case["upload"]["filename"],
                           data=case["upload"]["text"].encode(), uploaded_by="u")
        kwargs = {"org_id": "o1", "project": projects.get_project("o1", p["project_id"])}
    out = runtime.run_skill(case["skill"], case["company_id"], use_llm=False, **kwargs)

    by_n = {c["n"]: c for c in out["citations"]}
    sections = {s["id"]: s for s in out["sections"]}
    for exp in case["expect"]:
        claims = sections[exp["section"]]["claims"]
        hit = [c for c in claims if any(exp["quote"] in str(by_n[n].get("quote") or "") for n in c["cites"])]
        assert hit, f"{case['id']}: no cited passage with {exp['quote']!r} in {exp['section']}"
        if exp.get("voice"):
            assert any(f"— {exp['voice']}:" in c["text"] for c in hit)
    for nf in case["not_found"]:
        assert any(nf in line for line in out["not_found"]), out["not_found"]
    assert not out["refused"]
    stub_removed = [r for r in out["verifier"]["removed_claims"] if "Stub" in r["text"]]
    assert stub_removed == [], stub_removed


def test_classify_event_kinds():
    assert event_filings.classify_event("Credit Rating", "CRISIL reaffirmed") == "credit_rating"
    assert event_filings.classify_event("Updates", "Receipt of warning letter from USFDA") == "usfda"
    assert event_filings.classify_event("Scheme of Arrangement", "") == "corporate_action"
    assert event_filings.classify_event("Draft Red Herring Prospectus", "") == "offer_document"
    assert event_filings.classify_event("Financial Results", "Q2 results") is None


def test_ingest_events_from_announcement_payload():
    url = "https://nsearchives.nseindia.com/corporate/STUB_rating.pdf"
    payload = [
        {"attchmntFile": url, "desc": "Credit Rating", "attchmntText": "Stub CRISIL rating reaffirmed",
         "an_dt": "18-Sep-2026 10:00:00"},
        {"attchmntFile": "https://nsearchives.nseindia.com/corporate/STUB_results.pdf", "desc": "Financial Results",
         "attchmntText": "Q1 results", "an_dt": "01-Aug-2026 10:00:00"},
    ]
    text = "Stub rating intimation for tests. CRISIL has reaffirmed the long-term rating of AA with a Stable outlook."
    res = event_filings.ingest_events("tatasteel", payload=payload, texts={url: text})
    assert [r["category"] for r in res["results"]] == ["credit_rating"] and res["results"][0]["ok"]
    doc = next(d for d in doc_store.list_documents(company_id="tatasteel") if d.get("url") == url)
    assert doc["doc_type"] == "credit_rating" and doc["date"] == "2026-09-18" and doc["source"] == "exchange_filing"
    again = event_filings.ingest_events("tatasteel", payload=payload, texts={url: text})
    assert again["results"][0]["action"] == "already_held"
