from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.extraction import extract_guidance
from app.services.matching import match_actuals

client = TestClient(app)


def setup_function():
    reset_data()


def test_us005_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_us001_list_companies_sensex30():
    r = client.get("/api/companies")
    assert r.status_code == 200
    data = r.json()
    # Seed GCI cohort: Sensex-30 + a growing Nifty-extra tail (demo until promoted)
    assert len(data) >= 40
    sensex = client.get("/api/companies", params={"market": "IN", "index": "SENSEX"}).json()
    assert len(sensex) == 30
    row = data[0]
    assert {"id", "name", "ticker", "gci_score", "peer_rank_in_sector"} <= set(row.keys())


def test_us002_company_gci_detail():
    r = client.get("/api/companies/infy/gci")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "infy"
    assert data["status"] == "ok"
    assert data["gci_score"] is not None
    assert len(data["outcomes"]) >= 7
    assert "trend" in data and len(data["trend"]) >= 1
    assert "label_counts" in data
    # W1.2: no sentiment stub on the public dossier payload
    assert "sentiment" not in data
    assert data["confidence_tier"] in ("provisional", "established", "deep")
    assert data["algorithm_id"] == "gci_scoring_v4"


def test_evidence_listing_latest_period_first():
    from app.data.seed import get_data
    from app.services.changes import period_rank

    r = client.get("/api/companies/infy/gci")
    rows = r.json()["outcomes"]
    assert rows
    ranks = [period_rank(o["period"]) for o in rows]
    assert all(rank is not None for rank in ranks)
    assert ranks == sorted(ranks, reverse=True)
    stored = get_data()["outcomes"]["infy"]
    for row in rows:
        src = stored[row["outcome_index"]]
        assert src["period"] == row["period"]
        assert src["metric"] == row["metric"]
    docs = client.get("/api/companies/infy/docs").json()
    periods = [p["period"] for p in docs["completeness"]["periods"]]
    period_ranks = [period_rank(p) for p in periods]
    assert period_ranks == sorted(period_ranks, reverse=True)


def test_us003_evidence_trail_fields():
    r = client.get("/api/companies/infy/gci")
    outcome = r.json()["outcomes"][0]
    for key in (
        "period",
        "metric",
        "guided_value",
        "actual_value",
        "delta_pct",
        "guided_text",
        "label",
        "source_url",
        "thread_id",
    ):
        assert key in outcome


def test_pit_history():
    r = client.get("/api/companies/infy/gci/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_alerts():
    r = client.get("/api/alerts")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_alert_kinds_include_drift_and_stale_threads():
    rows = client.get("/api/alerts").json()
    kinds = {a["kind"] for a in rows}
    # Original alert kinds still present
    assert kinds & {"large_miss", "guidance_dropped", "guidance_revised"}
    for a in rows:
        if a["kind"] == "credibility_drift":
            assert "reporting periods" in a["message"]
            assert a["severity"] in ("medium", "high")
        if a["kind"] == "thread_stale":
            assert "reiterated" in a["message"]
            assert a["severity"] == "medium"


def test_extract_requires_auth():
    r = client.post("/api/extract", json={"company_id": "infy"})
    assert r.status_code == 401


def test_extract_and_match():
    r = client.post(
        "/api/extract",
        json={"company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    statements = r.json()["statements"]
    assert len(statements) >= 1
    actuals = [
        {
            "company_id": "infy",
            "period": "FY26",
            "metric": statements[0]["metric"],
            "actual_value": statements[0]["guided_value"],
        }
    ]
    matched = match_actuals(statements, actuals)
    assert matched[0]["match_status"] == "matched"


def test_review_loop():
    detail = client.get("/api/companies/infy/gci").json()
    assert len(detail["outcomes"]) > 0
    r = client.post(
        "/api/review",
        json={
            "company_id": "infy",
            "outcome_index": 0,
            "action": "accept",
            "comment": "looks good",
        },
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_alphahunter_import():
    r = client.post(
        "/api/import/alphahunter",
        json={
            "merge_into_company": "infy",
            "facts": [
                {
                    "company_id": "infy",
                    "fiscal_period": "FY24",
                    "metric": "revenue_growth_pct",
                    "guided_value": 12,
                    "actual_value": 11,
                    "guidance_change": "Guided ~12%",
                    "source_ref": "facts",
                }
            ],
        },
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    assert r.json()["merged"] >= 1


def test_extraction_unit():
    text = "CFO: We expect revenue growth of 5–7% for FY26. Operating margin around 21%."
    rows = extract_guidance(text, company_id="infy", period="FY26")
    assert any(r["metric"] == "revenue_growth_pct" for r in rows)


def test_unknown_company_404():
    r = client.get("/api/companies/does-not-exist/gci")
    assert r.status_code == 404


def test_meta_gaps():
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert "G14-review" in r.json()["gaps_closed"]
