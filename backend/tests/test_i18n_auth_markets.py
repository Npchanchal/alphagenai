"""Auth sessions + multi-market scaffolding."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.session_auth import reset_auth_store

client = TestClient(app)
SEAT = {"X-API-Key": "intellens-demo"}


def setup_function() -> None:
    reset_auth_store()


def test_markets_list_and_indexes():
    r = client.get("/api/markets")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 8
    assert "IN" in body["gci_deep_markets"]
    ids = {m["id"] for m in body["markets"]}
    assert {"IN", "US", "JP", "GB"}.issubset(ids)

    indexes = client.get("/api/markets/IN/indexes").json()
    assert indexes["count"] >= 1
    assert indexes["gci_deep"] is True
    assert any(i["id"] == "SENSEX" for i in indexes["indexes"])

    us = client.get("/api/markets/US/indexes").json()
    assert us["count"] >= 1
    assert us["gci_deep"] is False


def test_index_constituents_and_companies_filter():
    sensex = client.get("/api/indexes/SENSEX/constituents").json()
    assert sensex["count"] == 30
    assert sensex["gci_deep"] is True

    spx = client.get("/api/indexes/SPX/constituents").json()
    assert 495 <= spx["count"] <= 510
    assert spx["constituents"][0]["data_quality"] in ("market_scaffold", "demo_structured", "listing_master")

    # pagination
    page = client.get("/api/indexes/SPX/constituents?limit=50&offset=0").json()
    assert page["count"] == spx["count"]
    assert page["returned"] == 50

    rows = client.get("/api/companies?market=US&index=SPX&limit=100").json()
    assert len(rows) == 100
    assert all(r.get("gci_score") is None for r in rows)

    full = client.get("/api/companies/count?market=US&index=SPX").json()
    assert full["count"] == spx["count"]

    # US: the S&P 500 listing master (SEC CIKs). Other markets: deterministic top-1000 scaffold.
    us = client.get("/api/companies/count?market=US").json()["count"]
    assert us == spx["count"]
    for mid in ["GB", "JP", "HK", "CN", "EU", "SG", "AU", "KR", "BR", "CA"]:
        n = client.get(f"/api/companies/count?market={mid}").json()["count"]
        assert n == 1000, mid

    # India: full NSE + BSE equity masters (not the scaffold cap)
    in_all = client.get("/api/companies/count?market=IN").json()["count"]
    assert in_all >= 2000

    india = client.get("/api/companies?market=IN&index=SENSEX").json()
    assert len(india) == 30
    assert any(r["id"] == "infy" and r["gci_score"] is not None for r in india)

    in1000 = client.get("/api/companies/count?market=IN&index=IN1000").json()
    assert in1000["count"] == 1000


def test_meta_gci_deep_markets():
    meta = client.get("/api/meta").json()
    assert meta["gci_deep_markets"] == ["IN"]
    assert meta["markets_count"] >= 8
    assert meta["indexes_count"] >= 8
    assert meta["market_universe_size"] == 1000


def test_register_login_guest_preferences_roundtrip():
    guest = client.post("/api/auth/guest", json={"accept_terms": True}).json()
    assert guest["user"]["kind"] == "guest"
    gtoken = guest["token"]

    prefs = client.put(
        "/api/auth/preferences",
        headers={"Authorization": f"Bearer {gtoken}"},
        json={"language": "hi", "default_market": "US", "default_index": "SPX"},
    ).json()["preferences"]
    assert prefs["language"] == "hi"
    assert prefs["default_market"] == "US"

    reg = client.post(
        "/api/auth/register",
        json={
            "email": "desk@intellens.test",
            "password": "secret99pass!",
            "name": "Desk User",
            "guest_token": gtoken,
            "accept_terms": True,
            "account_type": "b2b",
            "org_name": "CiteAlpha Test Desk",
        },
    ).json()
    assert reg["user"]["email"] == "desk@intellens.test"
    assert reg["user"]["preferences"]["language"] == "hi"
    assert reg["user"]["org_id"]
    token = reg["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["user"]["name"] == "Desk User"

    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert (
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )

    login = client.post(
        "/api/auth/login",
        json={"email": "desk@intellens.test", "password": "secret99pass!"},
    ).json()
    assert login["user"]["preferences"]["default_index"] == "SPX"

    bad = client.post(
        "/api/auth/login",
        json={"email": "desk@intellens.test", "password": "wrong"},
    )
    assert bad.status_code == 401


def test_vernacular_fallback_flag():
    hi = client.get("/api/vernacular/infy?lang=hi").json()
    assert hi["fallback"] is False
    assert "GCI" in hi["text"] or "स्कोर" in hi["text"]

    # unknown code falls back to en
    xx = client.get("/api/vernacular/infy?lang=xx").json()
    assert xx["fallback"] is True
    assert xx["lang"] == "en"


def test_five_year_market_and_stock_history():
    meta = client.get("/api/meta").json()
    assert meta["history_years"] == 5
    # FMP when keyed; otherwise pure demo fallback (see test_fmp.py)
    assert meta["history_kind"] in ("demo_deterministic", "fmp_eod_with_demo_fallback")
    assert meta["fmp_configured"] == (meta["history_kind"] == "fmp_eod_with_demo_fallback")

    markets = client.get("/api/markets").json()["markets"]
    for m in markets:
        hist = client.get(f"/api/markets/{m['id']}/history?years=5").json()
        assert hist["market_id"] == m["id"]
        assert hist["index"]["point_count"] >= 50
        assert hist["index"]["kind"] in ("demo_deterministic", "fmp_eod")

    sensex = client.get("/api/indexes/SENSEX/history").json()
    sensex2 = client.get("/api/indexes/SENSEX/history").json()
    assert sensex["points"] == sensex2["points"]  # deterministic

    constituents = client.get("/api/indexes/SPX/constituents").json()["constituents"]
    assert len(constituents) >= 5
    for row in constituents[:5]:
        sh = client.get(f"/api/stocks/{row['id']}/history?years=5", headers=SEAT).json()
        assert sh["stock_id"] == row["id"]
        assert sh["point_count"] >= 50
        assert len(sh["fundamentals"]) == 5

    # India Sensex name also has history
    # Price tape is Workbench-only (W1.2): guests get 401
    assert client.get("/api/stocks/infy/history").status_code == 401
    infy = client.get("/api/stocks/infy/history", headers=SEAT).json()
    assert infy["ticker"] == "INFY"
    assert infy["last"] is not None
