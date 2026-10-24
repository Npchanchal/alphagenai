"""CiteAlpha Analyst: verifier, skills, runtime, routes, tenant isolation (US-A03..A06, A08)."""

import json
import re

import pytest
from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.agent import runtime, skills
from app.services.agent.verifier import verify_claims, verify_text

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
ONESTOP_ADMIN = {"X-API-Key": "intellens-onestop"}
ONESTOP_LABELER = {"X-API-Key": "intellens-onestop-labeler"}
RETAIL = {"X-API-Key": "intellens-retail"}
STUB_URL = "https://example.invalid/stub-deck.pdf"

CITES = [
    {"n": 1, "quote": "Revenue growth guidance of 12%-14% in constant currency", "title": "FY22 guidance", "date": "2021-04-14"},
    {"n": 2, "quote": "Revenues in CC terms grew by 19.7% YoY", "title": "FY22 results", "date": "2022-04-13"},
]


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    reset_data()


# ── Verifier (US-A05) ────────────────────────────────────────────────────────


def test_verifier_drops_uncited_and_unknown_citations():
    res = verify_claims(
        [
            {"text": "Revenue grew 19.7% in constant currency.", "cites": [2], "kind": "quoted"},
            {"text": "Revenue grew strongly.", "cites": [], "kind": "quoted"},
            {"text": "Revenue grew 19.7%.", "cites": [9], "kind": "quoted"},
        ],
        CITES,
    )
    assert [c["text"] for c in res["kept"]] == ["Revenue grew 19.7% in constant currency."]
    assert [r["reason"] for r in res["removed"]] == ["no_citation", "unknown_citation"]


def test_verifier_drops_numbers_not_in_source():
    res = verify_text("Revenues grew 21% in constant currency [2].", CITES)
    assert res["kept"] == [] and res["removed"][0]["reason"].startswith("number_not_in_source")
    assert verify_text("Revenues in CC terms grew by 19.7% [2].", CITES)["ok"]


def test_verifier_drops_advice_wording_even_with_citation():
    res = verify_text("Revenues grew 19.7%, so we recommend you buy the stock [2].", CITES)
    assert res["kept"] == [] and res["removed"][0]["reason"] == "advice_wording"


def test_verifier_record_claims_skip_number_check_but_need_cites():
    ok = verify_claims([{"text": "FY22: guided 12–14%, reported 19.7% (beat).", "cites": [1, 2], "kind": "record"}], CITES)
    assert ok["ok"]
    bad = verify_claims([{"text": "FY22: beat.", "cites": [], "kind": "record"}], CITES)
    assert not bad["ok"]


# ── Skills ───────────────────────────────────────────────────────────────────


def test_all_skill_specs_valid_and_use_known_builders():
    specs = skills.load_skills()
    assert {"results_prep", "company_ramp", "concall_questions", "board_scorecard"} <= set(specs)
    for spec in specs.values():
        assert skills.validate_spec(spec) == []


SKILL_COPY_BANNED = [r"\bsignal\b", r"\btarget\s+price\b", r"\b(buy|sell|hold)\b(?!-side)", r"\boutperform", r"Promoter\s*(/\s*Management\s*)?Trust", r"Trust Score", r"intellens"]


def test_skill_copy_is_factual():
    for p in skills.SKILLS_DIR.glob("*.json"):
        text = p.read_text(encoding="utf-8")
        hits = [m.group(0) for pat in SKILL_COPY_BANNED for m in re.finditer(pat, text, re.I)]
        assert not hits, f"{p.name}: {hits}"


# ── Runtime (US-A03, US-A08) ─────────────────────────────────────────────────


@pytest.mark.parametrize("skill_id", sorted(skills.load_skills()))
def test_every_claim_cites_an_existing_source(skill_id):
    out = runtime.run_skill(skill_id, "infy", use_llm=False)
    ns = {c["n"] for c in out["citations"]}
    assert ns == set(range(1, len(ns) + 1))
    for s in out["sections"]:
        for claim in s["claims"]:
            assert claim["cites"] and set(claim["cites"]) <= ns
    for c in out["citations"]:
        assert c["quote"] and c["source_url"]
    assert len(out["evidence_receipt"]["sources"]) == len(out["citations"])
    assert out["evidence_receipt"]["skill_version"] == skills.get_skill(skill_id)["version"]
    assert "Not investment advice" in out["markdown"]


def test_board_scorecard_states_record_in_plain_sentence():
    out = runtime.run_skill("board_scorecard", "infy", use_llm=False)
    record = next(s for s in out["sections"] if s["id"] == "record")
    assert any("met or beat guidance in" in c["text"] for c in record["claims"])
    assert not any(re.search(r"\b(buy|sell|target price)\b", c["text"], re.I)
                   for s in out["sections"] for c in s["claims"])


def test_llm_summary_is_verified(monkeypatch):
    from app.services import llm_client

    def fake(*a, **k):
        return ("Infosys guided 12%-14% in constant currency for FY22 [2]. "
                "Revenues in CC terms grew by 19.7% [3]. Shares will double [1].")

    monkeypatch.setattr(llm_client, "chat_completion", fake)
    out = runtime.run_skill("results_prep", "infy", use_llm=True)
    summary = next(s for s in out["sections"] if s["id"] == "summary")
    assert all("double" not in c["text"] for c in summary["claims"])
    assert out["llm"]["used"] is True and out["llm"]["removed"] >= 1


def test_commitments_flow_into_skill_output():
    from app.services import commitment_store

    res = commitment_store.propose(
        [{
            "company_id": "infy", "type": "capacity", "subject": "Stub campus phase 2",
            "outcome": "Phase 2 operational", "due_period": "Q1 FY25",
            "quote": "Stub campus phase 2 will be operational by Q1 FY25.",
            "source_url": STUB_URL, "as_of": "2024-01-10",
        }],
        proposed_by="t",
    )
    cid = res["added"][0]
    out = runtime.run_skill("concall_questions", "infy", use_llm=False)
    assert not any("Stub campus" in c["text"] for s in out["sections"] for c in s["claims"])
    commitment_store.review(cid, decision="accepted", reviewer="rev")
    out = runtime.run_skill("concall_questions", "infy", use_llm=False)
    qs = next(s for s in out["sections"] if s["id"] == "questions")
    assert any("Stub campus phase 2 was due Q1 FY25" in c["text"] for c in qs["claims"])


# ── Routes, entitlements, tenant isolation (US-A04, US-A06) ──────────────────


def test_guest_and_retail_cannot_run():
    assert client.get("/api/analyst/skills").status_code == 401
    assert client.post("/api/analyst/run", json={"skill_id": "results_prep", "company_id": "infy"}, headers=RETAIL).status_code == 403


def test_run_unknown_skill_or_company_404():
    assert client.post("/api/analyst/run", json={"skill_id": "nope", "company_id": "infy"}, headers=DEMO).status_code == 404
    assert client.post("/api/analyst/run", json={"skill_id": "results_prep", "company_id": "zzz-nope"}, headers=DEMO).status_code == 404


def test_runs_are_org_scoped():
    r = client.post("/api/analyst/run", json={"skill_id": "board_scorecard", "company_id": "infy"}, headers=DEMO)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    assert any(x["run_id"] == run_id for x in client.get("/api/analyst/runs", headers=DEMO).json()["runs"])
    assert client.get(f"/api/analyst/runs/{run_id}", headers=DEMO).status_code == 200
    assert not any(x["run_id"] == run_id for x in client.get("/api/analyst/runs", headers=ONESTOP_ADMIN).json()["runs"])
    assert client.get(f"/api/analyst/runs/{run_id}", headers=ONESTOP_ADMIN).status_code == 404


def test_commitment_review_requires_reviewer_and_public_sees_accepted_only():
    body = {"commitments": [{
        "company_id": "infy", "type": "launch", "subject": "Stub product launches",
        "outcome": "Ten stub products launched", "due_period": "FY26",
        "quote": "We plan to launch ten stub products in FY26.", "source_url": STUB_URL, "as_of": "2025-04-20",
    }]}
    assert client.post("/api/commitments/propose", json=body, headers=DEMO).status_code == 403
    r = client.post("/api/commitments/propose", json=body, headers=ONESTOP_LABELER)
    assert r.status_code == 200
    cid = r.json()["added"][0]
    assert client.get("/api/companies/infy/commitments").json()["commitments"] == []
    assert client.post(f"/api/commitments/{cid}/review", json={"decision": "accepted"}, headers=ONESTOP_LABELER).status_code == 403
    r = client.post(f"/api/commitments/{cid}/review", json={"decision": "accepted"}, headers=ONESTOP_ADMIN)
    assert r.status_code == 200 and r.json()["reviewed_by"]
    rows = client.get("/api/companies/infy/commitments").json()["commitments"]
    assert [x["id"] for x in rows] == [cid]
    bad = client.post(f"/api/commitments/{cid}/transition", json={"new_state": "delivered", "proof": {}}, headers=ONESTOP_ADMIN)
    assert bad.status_code == 422


def test_extract_endpoint_proposes_unreviewed_rows():
    r = client.post(
        "/api/commitments/extract",
        json={"company_id": "infy", "text": "We expect the stub data centre to be commissioned in Q2 FY27.",
              "source_url": STUB_URL, "as_of": "2026-05-01", "use_llm": False},
        headers=ONESTOP_LABELER,
    )
    assert r.status_code == 200 and len(r.json()["added"]) == 1
    rows = client.get("/api/companies/infy/commitments?include_unreviewed=true", headers=ONESTOP_ADMIN).json()["commitments"]
    assert rows[0]["review_status"] == "unreviewed"
    assert client.get("/api/companies/infy/commitments?include_unreviewed=true").json()["commitments"] == []


def test_commitments_do_not_change_gci():
    before = client.get("/api/companies/infy/gci").json()["gci_score"]
    test_commitment_review_requires_reviewer_and_public_sees_accepted_only()
    assert client.get("/api/companies/infy/gci").json()["gci_score"] == before
