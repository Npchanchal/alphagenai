"""One test per product gap ID — fix/verify gaps one by one."""

from fastapi.testclient import TestClient

from app.data.hand_labeled import HAND_LABELED_COMPANY_IDS
from app.data.seed import reset_data
from app.main import app
from app.services.extraction import extract_guidance
from app.services.gci_scoring import GuidanceOutcome, OutcomeLabel, classify_outcome, outcome_score
from app.services.matching import match_actuals

client = TestClient(app)


def setup_function():
    reset_data()


def test_g01_hand_labeled_cohort():
    companies = client.get("/api/companies").json()
    labeled = [c for c in companies if c["data_quality"] == "hand_labeled"]
    assert len(labeled) >= 8
    assert "infy" in HAND_LABELED_COMPANY_IDS
    infy = client.get("/api/companies/infy/gci").json()
    assert infy["data_quality"] == "hand_labeled"
    assert len(infy["outcomes"]) >= 7
    assert not any(o["dropped"] for o in infy["outcomes"])
    rev = [o for o in infy["outcomes"] if o.get("thread_id") == "infy-rev-cc"]
    assert len(rev) == 5
    for o in rev:
        assert o["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/1067491/")
        assert o["guidance_source_url"].startswith("https://www.sec.gov/Archives/edgar/data/1067491/")
        assert o["guidance_source_url"] != o["source_url"]
        assert o["guidance_quote"] and o["quote_span"]
        assert o["guidance_as_of"] < o["as_of"]
    fy22 = next(o for o in rev if o["period"] == "FY22")
    assert (fy22["guided_low"], fy22["guided_high"]) == (12.0, 14.0)


def test_g02_extract():
    r = client.post(
        "/api/extract",
        json={"company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_g03_match():
    stmts = extract_guidance(
        "CFO: revenue growth of 5–7%.", company_id="infy", period="FY26"
    )
    matched = match_actuals(
        stmts,
        [{"company_id": "infy", "period": "FY26", "metric": stmts[0]["metric"], "actual_value": 6.0}],
    )
    assert matched[0]["match_status"] == "matched"


def test_g04_sensex30():
    # Gap G04: Sensex-30 deep GCI coverage (seed also carries a growing Nifty tail)
    assert len(client.get("/api/companies").json()) >= 40
    sensex = client.get("/api/companies", params={"market": "IN", "index": "SENSEX"}).json()
    assert len(sensex) == 30
    assert client.get("/api/indexes/SENSEX/constituents").json()["count"] == 30


def test_g05_sources():
    o = client.get("/api/companies/infy/gci").json()["outcomes"][0]
    assert o.get("source_url") or o.get("source_ref")


def test_g06_asymmetric_beats():
    beat = GuidanceOutcome("FY", "m", 10.0, 12.0, "b", 1.0)
    miss = GuidanceOutcome("FY", "m", 10.0, 8.0, "m", 1.0)
    assert outcome_score(beat) > outcome_score(miss)


def test_g07_ranges():
    o = GuidanceOutcome("FY", "m", 6.0, 5.5, "t", 1.0, guided_low=5.0, guided_high=7.0)
    assert classify_outcome(o) == OutcomeLabel.MET


def test_g08_labels():
    detail = client.get("/api/companies/infy/gci").json()
    assert set(detail["label_counts"]) >= {"met", "missed", "exceeded", "dropped", "pending"}


def test_g09_threads():
    detail = client.get("/api/companies/infy/gci").json()
    assert detail["threads"]
    assert any(len(v) >= 2 for v in detail["threads"].values())


def test_g10_trend():
    detail = client.get("/api/companies/infy/gci").json()
    assert len(detail["trend"]) >= 2


def test_g11_peers():
    row = next(c for c in client.get("/api/companies").json() if c["id"] == "infy")
    assert row["peer_rank_in_sector"] is not None
    assert row["sector_avg_gci"] is not None


def test_g12_dropped():
    o = GuidanceOutcome("FY", "m", 1.0, None, "d", 1.0, dropped=True)
    assert classify_outcome(o) == OutcomeLabel.DROPPED
    # v3/v4: dropped excluded from the period score; −15 only if an analyst sets
    # guidance_withdrawal. v2 legacy = 35.
    assert outcome_score(o) is None
    assert outcome_score(o, version="v2") == 35.0


def test_g13_wordmap_sentiment():
    # Wordmap is Workbench-only (seat feature); guests get 401.
    assert client.get("/api/companies/infy/wordmap").status_code == 401
    r = client.get("/api/companies/infy/wordmap", headers={"X-API-Key": "intellens-demo"})
    assert r.status_code == 200
    assert "entity" in r.json() and "industry" in r.json()


def test_g14_review():
    r = client.post(
        "/api/review",
        json={"company_id": "infy", "outcome_index": 0, "action": "accept"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.json()["ok"] is True


def test_g15_alphahunter_import():
    r = client.post(
        "/api/import/alphahunter",
        json={
            "merge_into_company": "infy",
            "facts": [
                {
                    "company_id": "infy",
                    "fiscal_period": "FY23",
                    "metric": "revenue_growth_pct",
                    "guided_value": 14,
                    "actual_value": 15,
                    "guidance_change": "guided mid-teens",
                }
            ],
        },
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.json()["merged"] >= 1


def test_g16_auth_and_org():
    assert client.post("/api/extract", json={"company_id": "infy"}).status_code == 401
    org = client.get("/api/orgs/demo", headers={"X-API-Key": "intellens-demo"})
    assert org.status_code == 200
    assert org.json()["seats"] >= 1


def test_g17_pit_history():
    hist = client.get("/api/companies/infy/gci/history").json()
    assert len(hist) >= 1
    assert "as_of" in hist[0]


def test_g18_alerts():
    assert len(client.get("/api/alerts").json()) >= 1


def test_g19_vernacular():
    hi = client.get(
        "/api/vernacular/infy?lang=hi",
        headers={"X-API-Key": "intellens-admin"},
    ).json()
    assert hi["lang"] == "hi" and "GCI" in hi["text"] or "स्कोर" in hi["text"]
    ta = client.get(
        "/api/vernacular/infy?lang=ta",
        headers={"X-API-Key": "intellens-admin"},
    ).json()
    assert ta["lang"] == "ta"


def test_g20_badge():
    badge = client.get("/api/badge/INFY").json()
    assert badge["gci_score"] is not None
    assert badge["label"] == "Guidance Credibility Index (GCI)"
    assert "data-citealpha-badge" in badge["embed"]
    svg = client.get("/api/badge/INFY/svg")
    assert svg.status_code == 200
    assert "svg" in svg.text.lower()


def test_g20_badge_listing_ticker():
    """NSE_ALL names like 20MICRONS are not in the Sensex seed list."""
    from app.data.markets import list_constituents

    listing = next(
        r for r in list_constituents("NSE_ALL") if r.get("ticker") == "20MICRONS"
    )
    badge = client.get(f"/api/badge/{listing['ticker']}")
    assert badge.status_code == 200, badge.text
    body = badge.json()
    assert body["ticker"] == "20MICRONS"
    assert body["gci_score"] is None
    svg = client.get("/api/badge/20MICRONS/svg")
    assert svg.status_code == 200
    assert "20MICRONS" in svg.text
    assert "not yet scored" in svg.text.lower()


def test_g21_sebi():
    note = client.get("/api/compliance/sebi-note").json()
    assert "buy" in note["avoid_without_ra"]


def test_g22_em_factor():
    feed = client.get("/api/export/em-factor/infy").json()
    assert feed["factor"] == "india_gci"
    assert "point_in_time" in feed


def test_g23_japan():
    ja = client.get(
        "/api/vernacular/infy?lang=ja",
        headers={"X-API-Key": "intellens-admin"},
    ).json()
    assert "GCI" in ja["text"] or "スコア" in ja["text"]


def test_meta_g01_closed():
    meta = client.get("/api/meta").json()
    assert "G01-hand-labeled-cohort" in meta["gaps_closed"]
    assert meta.get("open_gaps") == [] or "G01" not in str(meta.get("open_gaps"))
