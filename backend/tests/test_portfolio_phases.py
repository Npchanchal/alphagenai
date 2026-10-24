"""Portfolio phases P2–P5 tests."""

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
DEMO_KEY = {"X-API-Key": "intellens-demo"}


def setup_function():
    from app.data.seed import reset_data

    reset_data()


def _first_company_id() -> str:
    companies = client.get("/api/companies").json()
    assert companies
    return companies[0]["id"]


# --- P2 Radar ---


def test_p21_radar_diff_brief():
    cid = _first_company_id()
    r = client.get(f"/api/radar/diff/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body["feature"] == "guidance_diff_brief"
    assert body["company_id"] == cid
    assert "diffs" in body


def test_p22_radar_calendar():
    r = client.get("/api/radar/calendar", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["feature"] == "result_calendar"
    assert "windows" in body


def test_radar_digest_and_webhooks_moved_to_analyst():
    r = client.get("/api/radar/digest/preview")
    assert r.status_code == 410 and r.json()["moved_to"] == "/api/analyst/digest"
    r = client.post("/api/radar/digest/send", json={"to": "desk@example.com"}, headers=DEMO_KEY)
    assert r.status_code == 410 and r.json()["moved_to"] == "/api/analyst/digest"
    r = client.post("/api/radar/webhooks", json={"url": "https://example.com/hook"}, headers=DEMO_KEY)
    assert r.status_code == 410 and r.json()["moved_to"] == "/api/analyst/destinations"


# --- P3 Ledger ---


def test_p31_ledger_pdf():
    cid = _first_company_id()
    r = client.get(f"/api/ledger/{cid}/pdf", headers=DEMO_KEY)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_p32_ledger_mirror_requires_flag():
    cid = _first_company_id()
    r = client.get(f"/api/ledger/mirror/{cid}")
    assert r.status_code == 403


def test_p32_ledger_mirror_when_enabled(monkeypatch):
    from app.services import feature_flags

    monkeypatch.setattr(feature_flags, "ir_mirror_enabled", lambda: True)
    cid = _first_company_id()
    r = client.get(f"/api/ledger/mirror/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("mode") == "ir_mirror"
    assert "mirror_note" in body


def test_p33_ledger_credit_filter():
    cid = _first_company_id()
    r = client.get(f"/api/ledger/{cid}", params={"credit_only": "true"})
    assert r.status_code == 200
    assert r.json().get("filter") == "credit_adjacent"


# --- P4 Cite / Data ---


def test_p41_cite_tiers():
    r = client.get("/api/cite/tiers")
    assert r.status_code == 200
    assert len(r.json()["tiers"]) >= 2


def test_p41_cite_usage():
    r = client.get("/api/cite/usage", headers=DEMO_KEY)
    assert r.status_code == 200
    assert "tier" in r.json()


def test_p42_data_export_json():
    r = client.get("/api/data/export/outcomes", params={"format": "json", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["export"] == "outcomes_bulk"
    assert len(body["rows"]) <= 5


def test_p42_data_export_csv_requires_key():
    r = client.get("/api/data/export/outcomes", params={"format": "csv"})
    assert r.status_code == 401


def test_p42_data_export_csv_with_key():
    r = client.get(
        "/api/data/export/outcomes",
        params={"format": "csv", "limit": 3},
        headers={"X-API-Key": "intellens-onestop"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_p43_vernacular_digest():
    cid = _first_company_id()
    r = client.get(f"/api/digest/vernacular/{cid}", params={"lang": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["feature"] == "vernacular_digest"
    assert body["text_hi"]


def test_p43_kpi_dictionary():
    r = client.get("/api/data/kpi-dictionary")
    assert r.status_code == 200
    assert r.json()["metric_count"] > 0


# --- P5 Stretch ---


def test_p51_narrative_consistency():
    cid = _first_company_id()
    r = client.get(f"/api/score/narrative-consistency/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert "nci_score" in body
    assert body["status"] == "beta"


def test_p52_workbench_extraction():
    r = client.get("/api/workbench/extraction", headers=DEMO_KEY)
    assert r.status_code == 200
    assert r.json()["product"] == "Extraction Workbench"


def test_p53_trust_badge_channel():
    companies = client.get("/api/companies").json()
    ticker = companies[0]["ticker"]
    r = client.get(f"/api/channel/trust-badge/{ticker}")
    assert r.status_code == 200
    assert r.json()["channel"] == "white_label"


def test_p53_trust_badge_channel_listing_ticker():
    r = client.get("/api/channel/trust-badge/20MICRONS")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") != "not_found"
    assert body["channel"] == "white_label"
    assert body["ticker"] == "20MICRONS"
    assert body["company_id"] == "nse_20microns"
