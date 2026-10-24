"""Public Snapshot record vs ranked mode (plan W4.3)."""

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.gci_rankings import RANKED_THRESHOLD, gci_rankings

client = TestClient(app)


def test_snapshot_record_mode_while_under_threshold():
    reset_data()
    body = client.get("/api/public/gci-rankings?limit=30&index=NIFTY50").json()
    assert body["mode"] == "record"
    assert body["universe_n"] < RANKED_THRESHOLD
    assert body["top"] == []
    assert body["bottom"] == []
    assert body["records"]
    infy = next(r for r in body["records"] if r["company_id"] == "infy")
    assert infy["confidence_tier"] == "deep"
    assert infy["met"] + infy["exceeded"] + infy["missed"] >= 1
    md = gci_rankings(index="NIFTY50")
    from app.services.gci_rankings import rankings_markdown

    text = rankings_markdown(md)
    assert "Top management delivery" not in text
    assert "Delivery record" in text


def test_rankings_function_record_mode():
    reset_data()
    payload = gci_rankings(index="NIFTY50", limit=30)
    assert payload["mode"] == "record"
    assert payload["ranked_threshold"] == 20
