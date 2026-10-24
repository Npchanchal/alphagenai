"""CiteAlpha Analyst Monitors: baseline, new-filing trigger, commitment queue, feed, delivery (US-A04)."""

import pytest
from fastapi.testclient import TestClient

from app.data import doc_store
from app.data.seed import reset_data
from app.main import app
from app.services import commitment_store, mailer
from app.services.agent import monitors, runtime

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
ONESTOP_ADMIN = {"X-API-Key": "intellens-onestop"}
RETAIL = {"X-API-Key": "intellens-retail"}
STUB_URL = "https://example.invalid/stub-q2-call.pdf"
STUB_TEXT = (
    "Stub transcript for tests. We expect the stub Mysuru campus expansion to be commissioned in Q3 FY27. "
    "Demand was steady this quarter. We will continue to invest in stub automation platforms next year."
)


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(doc_store, "_DOCS", None)
    reset_data()
    yield
    doc_store._DOCS = None


def _new_filing(text: str = STUB_TEXT, company_id: str = "infy", date: str = "2026-10-15") -> dict:
    return doc_store.upsert_document(
        company_id=company_id, doc_type="transcript", title="Stub Q2 FY27 earnings call",
        text=text, url=STUB_URL, date=date, source="exchange_filing",
    )


def test_first_run_only_baselines():
    monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    res = monitors.process_new_documents(deliver=False)
    assert res["baselined"] > 0 and res["processed"] == 0 and res["runs"] == []
    again = monitors.process_new_documents(deliver=False)
    assert again["baselined"] == 0 and again["processed"] == 0


def test_new_filing_triggers_monitor_and_queues_unreviewed_commitments():
    mon = monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    monitors.create_monitor(org_id="o2", created_by="u", company_id="tcs", skill_id="coverage_monitor")
    monitors.process_new_documents(deliver=False)
    doc = _new_filing()

    res = monitors.process_new_documents(deliver=False, use_llm=False)
    assert res["processed"] == 1
    assert res["events"][0]["proposed"] == 1
    assert [r["monitor_id"] for r in res["runs"]] == [mon["monitor_id"]]

    rows = commitment_store.list_commitments("infy", include_unreviewed=True)
    assert rows[0]["review_status"] == "unreviewed" and rows[0]["proposed_by"] == monitors.AUTO_PROPOSER
    assert commitment_store.list_commitments("infy") == []

    from app.services.agent import run_store

    out = run_store.get_run("o1", res["runs"][0]["run_id"])
    trig = out["sections"][0]
    assert trig["id"] == "trigger" and "Stub Q2 FY27 earnings call" in trig["title"]
    assert any("Mysuru campus" in c["text"] for c in trig["claims"])
    assert out["evidence_receipt"]["trigger_doc_id"] == doc["doc_id"]
    assert run_store.get_run("o2", res["runs"][0]["run_id"]) is None
    assert monitors.process_new_documents(deliver=False)["processed"] == 0


def test_derived_and_demo_documents_never_trigger():
    monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    monitors.process_new_documents(deliver=False)
    for source in ("hand_labeled_period_pack", "sample_transcript", "bootstrap", "INFY-FY25-results-press"):
        doc_store.upsert_document(company_id="infy", doc_type="transcript", title=f"{source} doc",
                                  text=STUB_TEXT + source, url=STUB_URL, date="2026-10-16", source=source)
    res = monitors.process_new_documents(deliver=False, use_llm=False)
    assert res["processed"] == 0 and res["runs"] == []
    assert commitment_store.list_commitments("infy", include_unreviewed=True) == []


def test_trigger_section_quotes_only_that_company_filing():
    monitors.process_new_documents(deliver=False)
    doc = _new_filing(company_id="tcs")
    out = runtime.run_skill("coverage_monitor", "infy", use_llm=False, trigger={"doc_id": doc["doc_id"], "title": "x"})
    assert out["sections"][0]["claims"] == []


def test_monitor_emails_owner(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send_mail", lambda **kw: sent.append(kw) or {"sent": True})
    monitors.create_monitor(org_id="o1", created_by="u", company_id="infy",
                            skill_id="coverage_monitor", email="pm@example.invalid")
    monitors.process_new_documents()
    _new_filing()
    res = monitors.process_new_documents(use_llm=False)
    assert res["runs"][0]["emailed"] is True
    assert sent[0]["to"] == "pm@example.invalid"
    assert f"/analyst?run={res['runs'][0]['run_id']}" in sent[0]["body"]
    assert "Not investment advice" in sent[0]["body"]


def test_monitor_failure_does_not_stop_batch():
    monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    monitors.process_new_documents(deliver=False)
    _new_filing()

    def boom(*a, **k):
        raise RuntimeError("x")

    res = monitors.process_new_documents(deliver=False, use_llm=False, runner=boom)
    assert res["processed"] == 1 and res["runs"][0]["error"] == "RuntimeError"


def test_monitor_limit_and_dedupe(monkeypatch):
    monkeypatch.setattr(monitors, "MAX_MONITORS_PER_ORG", 1)
    a = monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    assert monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor") == a
    with pytest.raises(ValueError):
        monitors.create_monitor(org_id="o1", created_by="u", company_id="tcs", skill_id="coverage_monitor")


# ── Routes ───────────────────────────────────────────────────────────────────


def test_monitor_routes_are_org_scoped():
    assert client.get("/api/analyst/monitors").status_code == 401
    assert client.get("/api/analyst/monitors", headers=RETAIL).status_code == 403
    body = {"skill_id": "coverage_monitor", "company_id": "infy"}
    r = client.post("/api/analyst/monitors", json=body, headers=DEMO)
    assert r.status_code == 200
    mid = r.json()["monitor_id"]
    assert [m["monitor_id"] for m in client.get("/api/analyst/monitors", headers=DEMO).json()["monitors"]] == [mid]
    assert client.get("/api/analyst/monitors", headers=ONESTOP_ADMIN).json()["monitors"] == []
    assert client.delete(f"/api/analyst/monitors/{mid}", headers=ONESTOP_ADMIN).status_code == 404
    assert client.delete(f"/api/analyst/monitors/{mid}", headers=DEMO).status_code == 200


def test_monitor_route_validation():
    assert client.post("/api/analyst/monitors", json={"skill_id": "nope", "company_id": "infy"}, headers=DEMO).status_code == 404
    assert client.post("/api/analyst/monitors", json={"skill_id": "coverage_monitor", "company_id": "zzz"}, headers=DEMO).status_code == 404
    bad = {"skill_id": "coverage_monitor", "company_id": "infy", "email": "not an email"}
    assert client.post("/api/analyst/monitors", json=bad, headers=DEMO).status_code == 422


def test_feed_lists_triggered_runs_only():
    client.post("/api/analyst/monitors", json={"skill_id": "coverage_monitor", "company_id": "infy"}, headers=DEMO)
    client.post("/api/analyst/run", json={"skill_id": "board_scorecard", "company_id": "infy"}, headers=DEMO)
    assert client.post("/api/ops/analyst/monitors/process").status_code == 401
    assert client.post("/api/ops/analyst/monitors/process", headers=DEMO).json()["baselined"] > 0
    _new_filing()
    res = client.post("/api/ops/analyst/monitors/process", headers=DEMO).json()
    assert res["processed"] == 1
    feed = client.get("/api/analyst/feed", headers=DEMO).json()["runs"]
    assert len(feed) == 1 and feed[0]["trigger"]["title"] == "Stub Q2 FY27 earnings call"
    assert len(client.get("/api/analyst/runs", headers=DEMO).json()["runs"]) == 2
