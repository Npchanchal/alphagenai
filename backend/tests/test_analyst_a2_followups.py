"""A2 follow-ups: say-now-versus-last-call, Monitors on watchlists and Projects, weekly digest."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.data import doc_store
from app.data.seed import reset_data
from app.main import app
from app.services import mailer, session_auth
from app.services.agent import digest, monitors, projects, run_store, runtime, tools
from tests.test_analyst_monitors import _new_filing

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
OTHER = {"X-API-Key": "intellens-onestop"}


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(doc_store, "_DOCS", None)
    reset_data()
    yield
    doc_store._DOCS = None


# ── what management says now versus the last call ──


def test_language_shift_quotes_both_dates_and_survives_verifier():
    res = tools.language_shift("infy")
    assert res["data"]["previous"] and res["data"]["latest"] > res["data"]["previous"]
    assert res["data"]["rows"]
    out = runtime.run_skill("concall_questions", "infy", use_llm=False)
    shift = next(s for s in out["sections"] if s["id"] == "shift")
    assert shift["claims"]
    assert not [r for r in out["verifier"]["removed_claims"] if r["section"] == "shift"]
    by_n = {c["n"]: c for c in out["citations"]}
    for c in shift["claims"]:
        for n in c["cites"]:
            assert by_n[n]["quote"] in c["text"]


def test_language_shift_needs_two_dates(monkeypatch):
    one = [{"doc_id": "d1", "company_id": "x", "doc_type": "transcript", "title": "Stub call", "url": "https://example.invalid/a",
            "date": "2026-01-10", "source": "exchange_filing", "text": "We expect revenue growth of 9% next year in stub markets."}]
    monkeypatch.setattr(tools, "_list_documents", lambda cid: one)
    assert tools.language_shift("x")["data"]["previous"] is None


def test_language_shift_ignores_unchanged_figures(monkeypatch):
    s = "We expect revenue growth of 9% next year across stub markets."
    docs = [{"doc_id": f"d{i}", "company_id": "x", "doc_type": "transcript", "title": "Stub call", "date": d,
             "url": "https://example.invalid/a", "source": "exchange_filing", "text": s} for i, d in enumerate(("2026-01-10", "2026-04-10"))]
    monkeypatch.setattr(tools, "_list_documents", lambda cid: docs)
    assert tools.language_shift("x")["data"]["rows"] == []


# ── Monitors on watchlists and Projects ──


def test_watchlist_monitor_follows_owner_watchlist(monkeypatch):
    watch = {"u1": ["infy"]}
    monkeypatch.setattr(session_auth, "user_watchlist", lambda uid: watch.get(uid, []))
    mon = monitors.create_monitor(org_id="o1", created_by="u1", skill_id="coverage_monitor", scope="watchlist", user_id="u1")
    monitors.process_new_documents(deliver=False)
    _new_filing()
    res = monitors.process_new_documents(deliver=False, use_llm=False)
    assert [r["monitor_id"] for r in res["runs"]] == [mon["monitor_id"]]

    watch["u1"] = ["tcs"]
    _new_filing(text="Stub second call. We expect stub margin of 21% next year.", company_id="infy")
    doc_store._DOCS = None
    assert monitors.process_new_documents(deliver=False, use_llm=False)["runs"] == []


def test_project_monitor_runs_with_project_context():
    p = projects.create_project(org_id="o1", created_by="u", name="Stub coverage", company_ids=["infy"])
    seen = {}

    def runner(skill, company, **kw):
        seen.update(kw, skill=skill, company=company)
        return runtime.run_skill(skill, company, use_llm=False, **kw)

    monitors.create_monitor(org_id="o1", created_by="u", skill_id="weekly_driver_review", scope="project",
                            project_id=p["project_id"])
    monitors.process_new_documents(deliver=False)
    _new_filing()
    res = monitors.process_new_documents(deliver=False, use_llm=False, runner=runner)
    assert len(res["runs"]) == 1 and seen["project"]["project_id"] == p["project_id"] and seen["org_id"] == "o1"
    saved = run_store.get_run("o1", res["runs"][0]["run_id"])
    assert saved["project"]["project_id"] == p["project_id"]

    assert monitors.delete_project_monitors("o1", p["project_id"]) == 1


def test_monitor_scope_api_rules():
    r = client.post("/api/analyst/monitors", json={"skill_id": "coverage_monitor", "scope": "watchlist"}, headers=DEMO)
    assert r.status_code == 422 and "Sign in" in r.json()["detail"]
    r = client.post("/api/analyst/monitors", json={"skill_id": "weekly_driver_review", "company_id": "infy"}, headers=DEMO)
    assert r.status_code == 422
    pid = client.post("/api/analyst/projects", json={"name": "Stub", "company_ids": ["infy"]}, headers=DEMO).json()["project_id"]
    r = client.post("/api/analyst/monitors", json={"skill_id": "weekly_driver_review", "scope": "project", "project_id": pid}, headers=DEMO)
    assert r.status_code == 200 and r.json()["scope"] == "project"
    r = client.post("/api/analyst/monitors", json={"skill_id": "weekly_driver_review", "scope": "project", "project_id": pid}, headers=OTHER)
    assert r.status_code == 404
    assert client.delete(f"/api/analyst/projects/{pid}", headers=DEMO).status_code == 200
    assert monitors.list_monitors() == [] or all(m.get("project_id") != pid for m in monitors.list_monitors())


# ── weekly digest ──


def test_digest_settings_validate():
    assert client.put("/api/analyst/digest", json={"enabled": True, "emails": ["not-an-email"]}, headers=DEMO).status_code == 422
    r = client.put("/api/analyst/digest", json={"enabled": True, "emails": ["PM@example.invalid"]}, headers=DEMO)
    assert r.status_code == 200 and r.json()["emails"] == ["pm@example.invalid"]
    g = client.get("/api/analyst/digest", headers=DEMO).json()
    assert g["settings"]["enabled"] and "Not investment advice" in g["text"]


def test_digest_sends_weekly_and_skips_empty(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send_mail", lambda **kw: sent.append(kw) or {"sent": True})
    digest.set_settings("o1", enabled=True, emails=["pm@example.invalid"])
    now = datetime.now(timezone.utc) - timedelta(days=1)

    assert digest.send_due_digests(now=now)["skipped_empty"] == ["o1"]  # no Monitors yet
    assert sent == []

    monitors.create_monitor(org_id="o1", created_by="u", company_id="infy", skill_id="coverage_monitor")
    monitors.process_new_documents(deliver=False)
    day1 = now + timedelta(days=1)
    _new_filing(date=day1.date().isoformat())
    monitors.process_new_documents(deliver=False, use_llm=False)

    d = digest.build_digest("o1", today=day1.date())
    assert d["filings"] and d["filings"][0]["title"] == "Stub Q2 FY27 earnings call"
    assert d["runs"] and "/analyst?run=" in d["runs"][0]["link"]
    assert digest.send_due_digests(now=day1) == {"sent": [], "skipped_empty": []}  # within seven days
    res = digest.send_due_digests(now=day1, force=True)
    assert res["sent"] == ["o1"] and sent[-1]["to"] == "pm@example.invalid"
    assert "Stub Q2 FY27 earnings call" in sent[-1]["body"] and "Not investment advice" in sent[-1]["body"]
    assert digest.send_due_digests(now=day1 + timedelta(days=6))["sent"] == []
    assert digest.send_due_digests(now=day1 + timedelta(days=7, hours=1))["sent"] == ["o1"]


def test_digest_carries_each_guidance_change_once(monkeypatch):
    from app.services import portfolio

    item = {"company_id": "infy", "kind": "guidance_cut", "metric": "revenue_growth", "period": "FY27",
            "message": "INFY cut revenue_growth guidance (FY27)", "severity": "high",
            "source_url": "https://www.bseindia.com/example"}
    monkeypatch.setattr(portfolio, "radar_feed", lambda limit=50: {"items": [item, {**item, "company_id": "tcs"}]})
    sent = []
    monkeypatch.setattr(mailer, "send_mail", lambda **kw: sent.append(kw) or {"sent": True})
    digest.set_settings("o2", enabled=True, emails=["pm@example.invalid"])
    monitors.create_monitor(org_id="o2", created_by="u", company_id="infy", skill_id="coverage_monitor")

    d = digest.build_digest("o2")
    assert [c["company_id"] for c in d["changes"]] == ["infy"]
    assert "Guidance changes" in digest.render_text(d) and "bseindia.com/example" in digest.render_text(d)
    now = datetime.now(timezone.utc)
    assert digest.send_due_digests(now=now, force=True)["sent"] == ["o2"]
    assert "INFY cut revenue_growth" in sent[-1]["body"]
    assert digest.build_digest("o2")["changes"] == []
