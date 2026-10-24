"""Phase-1 monetization hooks: IC dossier, rankings, pilot checklist, PIT v1."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
KEY = {"X-API-Key": "intellens-demo"}


def test_ic_audit_json_dossier():
    r = client.post(
        "/api/reports/generate",
        headers=KEY,
        json={"company_id": "infy", "template_id": "ic_audit", "format": "json"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["template_id"] == "ic_audit"
    assert body["format"] == "json"
    assert "dossier" in body
    assert body["dossier"]["schema"] == "ic_audit_dossier.v1"
    assert "guidance_vs_delivery" in body["dossier"]
    assert "citation_appendix" in body["dossier"]


def test_ic_audit_pdf_bytes():
    r = client.post(
        "/api/reports/generate",
        headers=KEY,
        json={"company_id": "infy", "template_id": "ic_audit", "format": "pdf"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_ops_throughput():
    r = client.get("/api/ops/throughput", headers=KEY)
    assert r.status_code == 200
    body = r.json()
    assert "universe" in body
    assert "backlog" in body
    assert "citeable_outcomes" in body["universe"]


def test_pilot_checklist_flow():
    r = client.get("/api/orgs/demo/pilot-checklist", headers=KEY)
    assert r.status_code == 200
    assert r.json()["progress"]["total"] >= 10

    patch = client.patch(
        "/api/orgs/demo/pilot-checklist",
        headers=KEY,
        json={"item_id": "access", "done": True},
    )
    assert patch.status_code == 200
    assert any(i["id"] == "access" and i["done"] for i in patch.json()["items"])

    created = client.post(
        "/api/orgs/pilot",
        headers=KEY,
        json={"name": "Test Pilot Desk", "seats": 5, "term_days": 45},
    )
    assert created.status_code == 200
    assert created.json()["org"]["plan"] == "pilot"
    assert "checklist" in created.json()


def test_public_gci_rankings_citeable_only():
    # W1.3: only established/deep tiers are ranked — use the index that has one.
    r = client.get("/api/public/gci-rankings?limit=5&index=NIFTY50")
    assert r.status_code == 200
    body = r.json()
    assert body["citeable_only"] is True
    assert "top" in body and "bottom" in body
    for row in body["top"]:
        assert row["data_quality"] == "hand_labeled"
        assert row["confidence_tier"] in ("established", "deep")
    rows = {r["company_id"]: r for r in body["top"] + body["bottom"]}
    if not rows:
        assert body["mode"] == "record"
        assert body["universe_n"] < body["ranked_threshold"]
        return
    for cid, row in rows.items():
        dossier = client.get(f"/api/companies/{cid}/gci").json()
        expected = sum(1 for o in dossier["outcomes"] if o["citeable"])
        assert row["citeable_outcomes"] == expected
        assert row["gci_score"] == dossier["gci_score"]
    assert any(r["citeable_outcomes"] > 0 for r in rows.values())


def test_pit_v1_contract_and_history():
    c = client.get("/api/v1/pit/contract")
    assert c.status_code == 200
    assert c.json()["contract_version"] == "pit.v1"

    h = client.get("/api/v1/pit/companies/infy/history")
    assert h.status_code == 200
    body = h.json()
    assert body["contract_version"] == "pit.v1"
    assert "series_kind" in body
    assert "points" in body
    assert "citeable" in body


def test_em_factor_honest_series_kind():
    r = client.get("/api/export/em-factor/infy")
    assert r.status_code == 200
    body = r.json()
    assert body["series_kind"] != ""  # must not hard-code silently
    assert "contract_version" in body
    assert isinstance(body["citeable"], bool)
