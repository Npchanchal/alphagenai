"""Financial Ninja worksheets, layer notes, and delivery counts.

None of these routes write a published GCI.
"""

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app

client = TestClient(app)
ONESTOP = {"X-API-Key": "intellens-onestop"}
DEMO = {"X-API-Key": "intellens-demo"}


def setup_function():
    reset_data()


def test_worksheets_are_the_arithmetic_of_the_inputs():
    denied = client.post("/api/ninja/worksheets/dcf", headers=DEMO, json={"cash_flows": [100], "discount_rate_pct": 10, "terminal_value": 0})
    assert denied.status_code == 403

    dcf = client.post(
        "/api/ninja/worksheets/dcf",
        headers=ONESTOP,
        json={"cash_flows": [100], "discount_rate_pct": 10, "terminal_value": 0},
    )
    assert dcf.status_code == 200, dcf.text
    assert round(dcf.json()["figure"], 4) == round(100 / 1.1, 4)
    assert "not the Guidance Credibility Index" in dcf.json()["statement"]

    relative = client.post(
        "/api/ninja/worksheets/relative",
        headers=ONESTOP,
        json={"metric": 10, "multiple": 15},
    )
    assert relative.json()["figure"] == 150

    residual = client.post(
        "/api/ninja/worksheets/residual_income",
        headers=ONESTOP,
        json={"book_value": 100, "roe_pct": 10, "cost_of_equity_pct": 10, "payout_pct": 0, "years": 1},
    )
    assert residual.json()["figure"] == 100

    reverse = client.post(
        "/api/ninja/worksheets/reverse_dcf",
        headers=ONESTOP,
        json={"price": 100, "cash_flow": 5, "discount_rate_pct": 10},
    )
    assert round(reverse.json()["figure"], 4) == round(100 * (10 - 5) / 105, 4)

    asset = client.post(
        "/api/ninja/worksheets/asset_value",
        headers=ONESTOP,
        json={"items": [{"name": "Cash", "amount": 10}, {"name": "Debt", "amount": -4}]},
    )
    assert asset.json()["figure"] == 6

    missing = client.post("/api/ninja/worksheets/dcf", headers=ONESTOP, json={})
    assert missing.status_code == 400


def test_layer_index_stays_unpublished_until_three_quotes(tmp_path, monkeypatch):
    import app.services.ninja as ninja

    monkeypatch.setattr(ninja, "_root", lambda: tmp_path)
    quote = {
        "company_id": "infy",
        "layer": "accounting",
        "stance": "supported",
        "quote": "Operating margin was within the guided band.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1067491/000106749124000016/exv99w01.htm",
        "as_of": "2024-04-18",
    }
    for _ in range(2):
        saved = client.post("/api/ninja/observations", headers=ONESTOP, json=quote)
        assert saved.status_code == 200, saved.text
    thin = client.get("/api/ninja/indices/infy", headers=ONESTOP)
    accounting = next(row for row in thin.json()["layers"] if row["layer"] == "accounting")
    assert accounting["published"] is False
    assert accounting["level"] is None

    quote["stance"] = "contradicted"
    assert client.post("/api/ninja/observations", headers=ONESTOP, json=quote).status_code == 200
    thick = client.get("/api/ninja/indices/infy", headers=ONESTOP).json()
    accounting = next(row for row in thick["layers"] if row["layer"] == "accounting")
    assert accounting["published"] is True
    assert accounting["level"] == 66.7

    profile = client.get("/api/ninja/profile/infy", headers=ONESTOP).json()
    assert "level" not in profile["layers"]["accounting"][0]
    guest = client.get("/api/ninja/profile/infy")
    assert guest.json()["layers"]["accounting"] == []
    assert guest.json()["notes"] == []


def test_delivery_tests_count_the_published_record_only():
    body = client.get("/api/ninja/tests", headers=ONESTOP)
    assert body.status_code == 200, body.text
    payload = body.json()
    assert "forecast" in payload["statement"].lower()
    assert "price" in payload["statement"].lower()
    assert payload["downward_revision"]["with_revision"]["n"] >= 0


def test_taxonomy_uses_the_stored_sector():
    body = client.get("/api/ninja/taxonomy", headers=ONESTOP)
    assert body.status_code == 200, body.text
    assert "second sector" in body.json()["note"]
    assert body.json()["sectors"]


def test_a_project_model_does_not_publish_a_gci(tmp_path, monkeypatch):
    from app.services.agent import projects
    from app.services.repository import get_company_gci

    before = get_company_gci("infy").gci_score
    monkeypatch.setattr(projects, "_path", lambda: tmp_path / "projects.json")
    created = client.post(
        "/api/analyst/projects",
        headers=ONESTOP,
        json={"name": "Drivers", "company_ids": ["infy"]},
    )
    assert created.status_code == 200, created.text
    saved = client.post(
        f"/api/analyst/projects/{created.json()['project_id']}/models",
        headers=ONESTOP,
        json={
            "company_id": "infy",
            "name": "Revenue bridge",
            "figure": 12.5,
            "unit": "percent",
            "as_of": "2026-10-24",
            "assumptions": "Volume up, price flat.",
            "sources": "Analyst model, not a filing.",
            "not_found": "No filed bridge for the quarter.",
        },
    )
    assert saved.status_code == 200, saved.text
    assert "not a published GCI" in saved.json()["statement"]
    assert get_company_gci("infy").gci_score == before


def test_note_skills_load():
    from app.services.agent.skills import get_skill

    for skill_id in ("company_note", "thematic_note", "sector_note"):
        spec = get_skill(skill_id)
        assert spec["sections"]


def test_dossier_profile_includes_the_latest_cited_analyst_note(tmp_path, monkeypatch):
    from app.services.agent import run_store

    monkeypatch.setattr(run_store, "_path", lambda: tmp_path / "runs.json")
    run_store.save_run(
        "onestop-demo",
        "desk",
        {
            "run_id": "run_note",
            "company_id": "infy",
            "as_of": "2026-10-24",
            "generated_at": "2026-10-24T00:00:00Z",
            "skill": {"id": "company_note", "title": "Company note"},
            "sections": [{"id": "record", "title": "Record", "claims": [{"text": "Margin held.", "cites": [1]}]}],
            "citations": [
                {
                    "n": 1,
                    "quote": "operating margin of 20.7%",
                    "source_url": "https://www.sec.gov/Archives/edgar/data/example.htm",
                    "date": "2024-04-18",
                }
            ],
        },
    )
    profile = client.get("/api/ninja/profile/infy", headers=ONESTOP)
    assert profile.status_code == 200, profile.text
    notes = profile.json()["notes"]
    assert notes[0]["skill_id"] == "company_note"
    assert notes[0]["claims"][0]["quote"] == "operating margin of 20.7%"
    assert "level" not in notes[0]


def test_refresh_listing_score_keeps_the_composite(tmp_path, monkeypatch):
    import app.data.gci_score_cache as cache

    path = tmp_path / "gci_listing_scores.json"
    path.write_text(
        '{"version":2,"scores":{"infy":{"gci_score":76.5,"confidence_tier":"provisional","metrics_scored":1}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cache, "_PATH", path)
    cache.clear_memory_cache()
    try:
        row = cache.refresh_listing_score("infy")
        assert row["gci_score"] == 76.5
        assert row["confidence_tier"] == "deep"
        assert row["metrics_scored"] == 2
        cache.clear_memory_cache()
        assert cache.get_listing_score("infy")["confidence_tier"] == "deep"
    finally:
        cache.clear_memory_cache()
