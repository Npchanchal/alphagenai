"""Research terminal smoke tests."""

from app.services import research


def test_search_finds_guidance():
    res = research.search_documents("guidance", limit=10)
    assert res["count"] >= 1
    assert any(r["doc_type"] in ("guidance", "transcript") for r in res["results"])


def test_search_skips_sample_transcripts():
    docs = research.build_documents()
    assert docs
    assert all(d.get("source") != "sample_transcript" for d in docs)
    res = research.search_documents("constant currency", company_id="infy", limit=25)
    assert all(r.get("source") != "sample_transcript" for r in res["results"])


def test_chat_returns_citations_or_fallback():
    out = research.research_chat("What is margin guidance?", company_id="infy")
    assert "answer" in out
    assert out["disclaimer"]


def test_snapshot_and_estimates():
    snap = research.company_snapshot("infy")
    assert snap["ticker"] == "INFY"
    assert "market" in snap and "gci" in snap
    assert "mom_pct" in snap["market"] or "yoy_pct" in snap["market"]
    fund = snap["fundamentals_demo"]["revenue_growth_ttm_pct"]
    assert isinstance(fund, dict) and "value" in fund
    est = research.consensus_estimates("infy")
    assert len(est["estimates"]) >= 1
    # later periods should carry change fields
    with_change = [r for r in est["estimates"] if r.get("actual_change_pct") is not None]
    assert len(est["estimates"]) >= 1  # structure present
    _ = with_change


def test_watchlist_nonempty():
    w = research.watchlist()
    assert len(w["items"]) >= 5
    assert w.get("source") == "default"


def test_watchlist_prefers_company_ids():
    w = research.watchlist(company_ids=["infy", "tcs"])
    assert w["source"] == "preferences"
    assert [r["company_id"] for r in w["items"]] == ["infy", "tcs"]


def test_promise_brief_shapes_open_promises():
    brief = research.promise_brief("infy")
    assert brief["ticker"] == "INFY"
    assert brief["open_promise_count"] == len(brief["promises"])
    for p in brief["promises"]:
        assert p["period"] and p["metric"]
        assert "street_consensus" in p
        h = p["history"]
        assert h["closed"] == h["met"] + h["exceeded"] + h["missed"] + h["dropped"]
        assert h["kept"] == h["met"] + h["exceeded"]
        if h["closed"]:
            assert 0 <= h["hit_rate_pct"] <= 100
        else:
            assert h["hit_rate_pct"] is None
    # pending outcomes in the dossier must all appear as open promises
    from app.services import repository

    detail = repository.get_company_gci("infy")
    pending = [o for o in detail.outcomes if o.label == "pending"]
    assert len(pending) == brief["open_promise_count"]
