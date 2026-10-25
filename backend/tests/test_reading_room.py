"""Public reading room: recent filing metadata, and search limited to scored companies."""

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.session_auth import reset_auth_store

client = TestClient(app)


def setup_function():
    reset_data()
    reset_auth_store()


def test_recent_filings_are_metadata_only():
    response = client.get("/api/filings/recent", params={"limit": 6})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["filings"])
    assert body["count"] <= 6
    urls = []
    for row in body["filings"]:
        assert "text" not in row
        assert "preview" not in row
        assert row.get("title")
        assert row.get("doc_id")
        assert row["doc_type"] in {"results", "transcript", "ir_guidance", "filing"}
        assert "revenue_growth_pct" not in row["title"]
        if row.get("url"):
            urls.append(row["url"])
    assert len(urls) == len(set(urls))


def test_published_companies_include_infosys_and_cipla():
    response = client.get("/api/companies", params={"scored": "true"})
    assert response.status_code == 200
    rows = response.json()
    ids = {row["id"] for row in rows}
    assert {"infy", "cipla"} <= ids
    assert all(row["gci_score"] is not None for row in rows)
    assert "apollohosp" not in ids


def test_reading_room_rejects_a_company_that_is_not_scored():
    response = client.get(
        "/api/research/search",
        params={"q": "revenue", "company_id": "not-a-listed-company"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "reading_room_scope"
    unlabeled = client.get(
        "/api/research/search",
        params={"q": "revenue", "company_id": "apollohosp"},
    )
    assert unlabeled.status_code == 403
    assert unlabeled.json()["detail"]["code"] == "reading_room_scope"


def test_reading_room_searches_a_scored_company():
    response = client.get(
        "/api/research/search",
        params={"q": "revenue", "company_id": "infy"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "results" in body
    assert body["reading_room"]["remaining"] == 7
    cipla = client.get("/api/research/search", params={"q": "margin", "company_id": "cipla"})
    assert cipla.status_code == 200, cipla.text


def test_research_seat_still_searches_every_company():
    response = client.get(
        "/api/research/search",
        params={"q": "revenue guidance", "limit": 5},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert response.status_code == 200
    assert "reading_room" not in response.json()


def test_anonymous_browser_stops_after_eight_searches():
    local = TestClient(app)
    for n in range(8):
        ok = local.get("/api/research/search", params={"q": "margin", "company_id": "infy"})
        assert ok.status_code == 200, ok.text
        assert ok.json()["reading_room"]["remaining"] == 7 - n
    blocked = local.get("/api/research/search", params={"q": "margin", "company_id": "infy"})
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "reading_room_cap"
    status = local.get("/api/research/reading-room")
    assert status.status_code == 200
    assert status.json()["remaining"] == 0
    fresh = TestClient(app)
    again = fresh.get("/api/research/search", params={"q": "margin", "company_id": "cipla"})
    assert again.status_code == 200, again.text


def test_guest_reading_room_stops_after_eight_searches():
    guest = client.post("/api/auth/guest", json={"accept_terms": True})
    assert guest.status_code == 200
    token = guest.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(8):
        ok = client.get(
            "/api/research/search",
            params={"q": "margin", "company_id": "infy"},
            headers=headers,
        )
        assert ok.status_code == 200, ok.text
    blocked = client.get(
        "/api/research/search",
        params={"q": "margin", "company_id": "infy"},
        headers=headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "reading_room_cap"
