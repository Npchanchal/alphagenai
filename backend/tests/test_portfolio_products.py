"""Portfolio SKU catalog + Radar / Ledger / Data compositions (US-P01…)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_function():
    from app.data.seed import reset_data

    reset_data()


def test_us_p01_products_catalog():
    r = client.get("/api/products")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Portfolio"
    ids = {p["id"] for p in body["products"]}
    assert ids == {"score", "cite", "radar", "ledger", "data", "sights", "holdings"}
    assert "Not investment advice" in body["disclaimer"]


def test_us_p02_radar_feed():
    r = client.get("/api/radar/feed", params={"limit": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Radar"
    assert "items" in body
    assert body["count"] == len(body["items"])
    assert body["count"] <= 20
    for item in body["items"]:
        assert item["company_id"]
        assert item["kind"]
        assert item["severity"] in ("high", "medium", "low")


def test_us_p02_radar_feed_company_filter():
    companies = client.get("/api/companies").json()
    assert companies
    cid = companies[0]["id"]
    r = client.get("/api/radar/feed", params={"company_id": cid, "limit": 10})
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["company_id"] == cid


def test_us_p03_ledger():
    companies = client.get("/api/companies").json()
    cid = companies[0]["id"]
    r = client.get(f"/api/ledger/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Ledger"
    assert body["company_id"] == cid
    assert "closed_promises" in body
    assert "open_promises" in body
    assert "summary" in body
    assert "Not investment advice" in body["disclaimer"]


def test_us_p03_ledger_missing():
    r = client.get("/api/ledger/does-not-exist-xyz")
    assert r.status_code == 404


def test_us_p04_data_catalog():
    r = client.get("/api/data/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Data"
    export_ids = {e["id"] for e in body["exports"]}
    assert "pit_history" in export_ids
    assert "em_factor" in export_ids
    assert "ledger" in export_ids
