"""India NSE/BSE listing masters + GCI v2 coverage."""

from fastapi.testclient import TestClient

from app.data.gci_score_cache import build_india_gci_cache, clear_memory_cache, get_listing_score
from app.data.india_listings import find_listing, find_listing_by_ticker, listing_counts
from app.data.markets import constituents_readonly, list_constituents, list_indexes
from app.data.seed import get_data, get_outcomes, outcome_from_dict, reset_data
from app.main import app
from app.services.gci_scoring import compute_company_gci
from app.services.provisional_gci import (
    make_provisional_outcomes,
    score_provisional,
    score_provisional_internal,
)

client = TestClient(app)


def test_nse_bse_listing_counts():
    counts = listing_counts()
    assert counts["nse"] >= 2000
    assert counts["bse"] >= 2000
    assert counts["merged"] >= counts["nse"]


def test_nse_all_and_bse_all_indexes():
    indexes = {i["id"]: i for i in list_indexes("IN")}
    assert "NSE_ALL" in indexes
    assert "BSE_ALL" in indexes
    nse = list_constituents("NSE_ALL")
    bse = list_constituents("BSE_ALL")
    assert len(nse) >= 2000
    assert len(bse) >= 2000


def test_provisional_listing_is_not_yet_scored():
    rep = score_provisional("nse_demo", "DEMOCO", "Equity")
    assert rep["gci_score"] is None
    assert rep["status"] == "not_yet_scored"
    assert rep["data_quality"] == "listing_provisional"
    assert rep["trend"] == [] and rep["by_metric"] == {}


def test_provisional_internal_still_runs_production_scorer():
    rep = score_provisional_internal("nse_demo", "DEMOCO", "Equity")
    outcomes = make_provisional_outcomes("nse_demo", "DEMOCO", "Equity")
    assert rep["gci_score"] is not None
    assert compute_company_gci(outcomes) == rep["gci_score"]


def test_score_universe_cache_subset():
    clear_memory_cache()
    report = build_india_gci_cache(limit=80)
    assert report["algorithm"] == "gci_scoring_v4"
    for row in report["scores"].values():
        if row["data_quality"] not in ("hand_labeled", "extracted_verified"):
            assert row["gci_score"] is None
            assert row["yoy_pct"] is None


def test_sensex_still_scored():
    """W2.1: only dual-cited closed rows score. Infosys revenue years remain."""
    reset_data()
    data = get_data()
    assert len(data["companies"]) >= 40
    scored = [
        c
        for c in data["companies"]
        if compute_company_gci(
            [outcome_from_dict(o) for o in data["outcomes"][c["id"]]]
        )
        is not None
    ]
    ids = {c["id"] for c in scored}
    assert "infy" in ids
    # Promise citations are backfilled in W2.2; do not require a Sensex-wide score.
    assert len(scored) >= 1


def test_companies_api_nse_all_scores_only_hand_labeled():
    clear_memory_cache()
    build_india_gci_cache(limit=None)
    r = client.get("/api/companies/count", params={"market": "IN", "index": "NSE_ALL"})
    assert r.status_code == 200
    assert r.json()["count"] >= 2000
    r2 = client.get(
        "/api/companies",
        params={"market": "IN", "index": "NSE_ALL", "limit": 20},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert len(body) == 20
    for row in body:
        if row["data_quality"] != "hand_labeled":
            assert row["gci_score"] is None


def test_nifty_bank_index_is_not_empty():
    rows = list_constituents("NIFTYBANK")
    tickers = {r["ticker"] for r in rows}
    assert {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"} <= tickers
    count = next(i["constituent_count"] for i in list_indexes("IN") if i["id"] == "NIFTYBANK")
    assert count == len(rows)
    r = client.get("/api/companies", params={"market": "IN", "index": "NIFTYBANK", "limit": 50})
    assert r.status_code == 200
    assert {row["ticker"] for row in r.json()} == tickers


def test_index_quality_tags_match_company_records():
    reset_data()
    seeded = {c["id"]: c["data_quality"] for c in get_data()["companies"]}
    for ix in ("SENSEX", "NIFTY50", "NIFTYBANK", "NSE_ALL", "BSE_ALL", "IN1000"):
        for row in list_constituents(ix):
            if row["id"] in seeded:
                assert row["data_quality"] == seeded[row["id"]], (ix, row["id"])


def test_india_indexes_filter_one_record_per_scrip():
    from app.data.india_listings import india_equity_universe

    universe = india_equity_universe()
    by_id = {r["id"]: r for r in universe}
    assert len(by_id) == len(universe)
    isins = [r["isin"] for r in universe if r.get("isin")]
    assert len(isins) == len(set(isins))
    for ix in ("SENSEX", "NIFTY50", "NIFTYBANK", "NSE_ALL", "BSE_ALL", "IN1000"):
        rows = constituents_readonly(ix)
        assert rows, ix
        assert len({r["id"] for r in rows}) == len(rows), ix
        for r in rows:
            assert r is by_id[r["id"]], (ix, r["id"])
            assert ix in r["index_ids"]
    in1000 = constituents_readonly("IN1000")
    assert len(in1000) == 1000
    assert {r["id"] for r in in1000} == {r["id"] for r in universe[:1000]}
    assert sum("IN1000" in r["index_ids"] for r in universe) == 1000
    assert {r["id"] for r in constituents_readonly("SENSEX")} <= {r["id"] for r in in1000}


def test_dual_listed_scrip_in_both_exchange_filters_once():
    hdfc = find_listing("hdfcbank")
    assert {"SENSEX", "NIFTY50", "NIFTYBANK", "NSE_ALL", "BSE_ALL", "IN1000"} <= set(hdfc["index_ids"])
    for ix in ("NSE_ALL", "BSE_ALL"):
        assert [r["id"] for r in constituents_readonly(ix)].count("hdfcbank") == 1


def test_coverage_cohorts_are_disjoint_and_complete():
    from app.data.india_listings import india_equity_universe
    from app.services.india_coverage import COHORTS, cohort_ids, cohort_partition

    parts = cohort_partition()
    flat = [cid for name in COHORTS for cid in parts[name]]
    assert len(flat) == len(set(flat)) == len(india_equity_universe())
    assert cohort_ids("all") == flat
    flagship = set(parts["nifty50"])
    for ix in ("SENSEX", "NIFTY50", "NIFTYBANK"):
        assert {r["id"] for r in constituents_readonly(ix)} <= flagship


def test_full_bse_equity_and_in1000_by_size():
    import json
    from pathlib import Path

    from app.data.india_listings import BSE_SME_GROUPS, amfi_rank_by_isin, india_equity_universe, listing_counts

    universe = india_equity_universe()
    counts = listing_counts()
    assert counts["nse"] >= 2500
    assert counts["bse"] >= 4000
    bse_only = [r for r in universe if r.get("exchange") == "BSE"]
    bse_rows = json.loads((Path(__file__).parents[1] / "app/data/listings/bse_equity.json").read_text())["rows"]
    sme_isins = {
        r.get("isin")
        for r in bse_rows
        if r.get("group") in BSE_SME_GROUPS and str(r.get("isin") or "").startswith("INE")
    }
    assert sme_isins and any(r.get("isin") in sme_isins for r in bse_only)
    ranks = amfi_rank_by_isin()
    assert ranks, "amfi_mcap.json is part of the listing set"
    for row in bse_only:
        assert str(row.get("isin") or "").startswith("INE")
    in1000 = [r for r in universe if "IN1000" in r["index_ids"]]
    outside = [r.get("amfi_rank") for r in universe if "IN1000" not in r["index_ids"] and r.get("amfi_rank")]
    ranked_in = sorted(r["amfi_rank"] for r in in1000 if r.get("amfi_rank"))
    assert len(in1000) == 1000 and ranked_in[-1] < min(outside)


def test_renamed_nse_symbol_keeps_its_company_id():
    row = find_listing("nse_heg")
    assert row is not None and row["ticker"] == "HEGAM"
    assert find_listing_by_ticker("HEGAM")["id"] == "nse_heg"


def test_find_listing_by_ticker_numeric_symbol():
    row = find_listing_by_ticker("20MICRONS")
    assert row is not None
    assert row["ticker"] == "20MICRONS"
    assert row["id"] == "nse_20microns"


def test_listing_dossier_is_not_yet_scored():
    listing = next(
        r
        for r in list_constituents("NSE_ALL")
        if r["data_quality"] == "listing_master"
    )
    assert find_listing(listing["id"]) is not None
    r = client.get(f"/api/companies/{listing['id']}/gci")
    assert r.status_code == 200
    body = r.json()
    assert body["gci_score"] is None
    assert body["status"] == "not_yet_scored"
    assert body["data_quality"] == "listing_provisional"
    assert body["outcomes"] == []
    assert body["trend"] == []
    assert get_outcomes(listing["id"]) == []  # not in seed store


def test_demo_structured_company_is_not_yet_scored():
    reset_data()
    demo = next(c for c in get_data()["companies"] if c["data_quality"] == "demo_structured")
    body = client.get(f"/api/companies/{demo['id']}/gci").json()
    assert body["gci_score"] is None
    assert body["status"] == "not_yet_scored"
    assert all(o["contribution_score"] is None for o in body["outcomes"])
    listed = {r["id"]: r for r in client.get("/api/companies").json()}
    assert listed[demo["id"]]["gci_score"] is None
    from app.services.repository import pit_history

    assert pit_history(demo["id"]) == []


def test_meta_counts_only_hand_labeled_scores():
    meta = client.get("/api/meta").json()
    assert meta["gci_scored_count"] <= meta["hand_labeled_count"]
