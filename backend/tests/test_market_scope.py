"""Market and exchange scope: published GCI stays open, seat tools follow the order form."""

from fastapi.testclient import TestClient

from app.data import markets as markets_data
from app.data.seed import reset_data
from app.main import app
from app.services import market_scope
from app.services.holdings import build_lookthrough
from app.services.session_auth import reset_auth_store

client = TestClient(app)
PILOT = {"X-API-Key": "intellens-demo"}
ONESTOP = {"X-API-Key": "intellens-onestop"}
SUPER = {"X-API-Key": "intellens-admin"}


def setup_function():
    reset_data()
    reset_auth_store()


def _bse_only_company() -> str:
    return next(r["id"] for r in markets_data.list_stocks(market_id="IN") if r.get("exchange") == "BSE")


def _set_scope(org_id: str, grants):
    return client.put(f"/api/admin/portal/orgs/{org_id}/coverage", headers=SUPER, json={"coverage": grants})


def test_grants_normalise_and_collapse():
    assert market_scope.normalize_grants(["in:nse", "IN:BSE"]) == ["IN"]
    assert market_scope.normalize_grants("IN:NSE,US") == ["IN:NSE", "US"]
    assert market_scope.normalize_grants(["*", "IN"]) == ["*"]
    # The US is sold whole; an exchange inside it is not a unit yet.
    assert market_scope.normalize_grants(["US:NYSE", "XX"]) == []
    assert market_scope.describe(["IN:NSE", "US"])["label"] == "India (NSE) · United States"


def test_dual_listed_company_counts_under_either_exchange():
    assert market_scope.company_in_scope(["IN:NSE"], "infy")
    assert market_scope.company_in_scope(["IN:BSE"], "infy")
    assert not market_scope.company_in_scope(["IN:NSE"], _bse_only_company())
    assert not market_scope.company_in_scope(["IN"], "us_aapl")
    assert market_scope.company_in_scope(["US"], "us_aapl")


def test_default_scope_follows_the_plan():
    assert client.get("/api/entitlements/me", headers=PILOT).json()["coverage"]["grants"] == ["IN"]
    assert client.get("/api/entitlements/me", headers=ONESTOP).json()["coverage"]["all"] is True
    assert client.get("/api/entitlements/me").json()["coverage"]["grants"] == []
    assert client.get("/api/entitlements/me", headers=SUPER).json()["coverage"]["all"] is True


def test_published_gci_stays_open_outside_the_plan():
    rows = client.get("/api/companies?market=US&index=SPX&limit=5", headers=PILOT)
    assert rows.status_code == 200
    assert rows.json() and all(r["exchange"] == "US" for r in rows.json())


def test_dossier_carries_its_listing_venue():
    us = client.get("/api/companies/us_aapl/gci", headers=PILOT)
    assert us.status_code == 200
    assert (us.json()["market_id"], us.json()["exchange"]) == ("US", "US")
    infy = client.get("/api/companies/infy/gci").json()
    assert (infy["market_id"], infy["exchange"]) == ("IN", "NSE+BSE")


def test_seat_tool_refuses_a_company_outside_the_plan():
    out = client.post("/api/research/chat", headers=PILOT, json={"question": "revenue guidance", "company_id": "us_aapl"})
    assert out.status_code == 403
    assert out.json()["detail"]["code"] == "market_not_in_plan"
    assert "India" in out.json()["detail"]["message"]

    ok = client.post("/api/research/chat", headers=PILOT, json={"question": "revenue guidance", "company_id": "infy"})
    assert ok.status_code == 200, ok.text

    wide = client.post("/api/research/chat", headers=ONESTOP, json={"question": "revenue guidance", "company_id": "us_aapl"})
    assert wide.status_code == 200, wide.text


def test_exchange_scope_on_filing_search():
    assert _set_scope("demo", ["IN:NSE"]).status_code == 200
    me = client.get("/api/entitlements/me", headers=PILOT).json()["coverage"]
    assert me["grants"] == ["IN:NSE"] and me["label"] == "India (NSE)"

    assert client.get("/api/research/search?q=guidance&company_id=infy", headers=PILOT).status_code == 200
    blocked = client.get(f"/api/research/search?q=guidance&company_id={_bse_only_company()}", headers=PILOT)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "market_not_in_plan"


def test_corpus_search_keeps_only_the_desks_markets():
    assert _set_scope("demo", ["US"]).status_code == 200
    hits = client.get("/api/research/search?q=guidance", headers=PILOT).json()["results"]
    assert all(market_scope.company_in_scope(["US"], h["company_id"]) for h in hits)


def test_only_platform_billing_sets_scope():
    denied = client.put("/api/admin/portal/orgs/demo/coverage", headers=PILOT, json={"coverage": ["*"]})
    assert denied.status_code in (401, 403)
    assert _set_scope("demo", ["nowhere"]).status_code == 400
    snap = _set_scope("demo", ["IN", "US"]).json()
    assert snap["coverage"]["grants"] == ["IN", "US"]
    assert snap["coverage_history"][-1]["before"] == ["IN"]


def test_holdings_outside_the_plan_are_a_gap_not_a_score():
    report = build_lookthrough(
        [
            {"isin": "IN1", "weight": 50, "name": "Infosys"},
            {"isin": "US1", "weight": 50, "name": "Apple"},
        ],
        as_of="2026-10-28",
        resolve_isin=lambda isin: {"id": "infy" if isin == "IN1" else "us_aapl", "name": isin},
        published_score=lambda cid: {"gci_score": 80.0 if cid == "infy" else 40.0},
        in_scope=lambda cid: market_scope.company_in_scope(["IN"], cid),
    )
    assert report["covered_gci"] == 80.0
    assert [g["reason"] for g in report["gaps"]] == ["not_in_plan"]
    assert report["not_in_plan_weight_pct"] == 50.0
    assert report["unscored_weight_pct"] == 0.0
    assert "outside this desk's plan" in report["statement"]
