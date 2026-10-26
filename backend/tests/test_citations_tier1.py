"""Tier 1 citation foundation + Tier 3 gates."""

from __future__ import annotations

from app.services.citation_corpus import ensure_company_citation_corpus, ensure_sensex_citation_corpus
from app.services.citations import (
    assess_citeability,
    citation_id_for,
    enrich_outcome_citation,
    span_offsets,
)
from app.services.granger_analytics import MIN_OBS_BIVARIATE, build_granger_bundle, granger_pairwise
from app.services.provisional_gci import make_provisional_outcomes
from app.services.repository import get_company_gci, period_completeness, search_entities


def test_provisional_outcomes_have_no_invented_quotes():
    rows = make_provisional_outcomes("nse_abdl", "ABDL", "Consumer")
    assert rows
    assert all(o.quote_span is None for o in rows)


def test_provisional_dossier_not_citeable():
    detail = get_company_gci("nse_abdl")
    assert detail.data_quality == "listing_provisional"
    assert detail.status == "not_yet_scored"
    assert detail.gci_score is None
    assert detail.outcomes == []


def test_hand_labeled_infy_citeable():
    detail = get_company_gci("infy")
    assert detail.data_quality == "hand_labeled"
    citeable = [o for o in detail.outcomes if o.citeable]
    assert citeable, "expected at least one citeable INFY outcome"
    for o in citeable:
        assert o.citation_id and o.citation_id.startswith("cite_")
        assert o.source_url
        assert o.quote_span


def test_infy_citation_doc_binding_and_tier1_gate():
    ensure_company_citation_corpus("infy")
    detail = get_company_gci("infy")
    bound = [o for o in detail.outcomes if o.citeable and o.doc_id]
    assert bound, "expected doc_id on citeable INFY outcomes"
    assert any(o.span_start is not None for o in bound)
    pc = period_completeness("infy")
    assert pc["summary"]["accepted_periods"] >= 1
    assert pc["summary"]["citeable_bound_outcomes"] >= 1
    assert pc["summary"]["tier1_gate"] is True


def test_sensex_corpus_batch():
    report = ensure_sensex_citation_corpus(limit=5)
    assert report["ok"]
    assert report["companies"] == 5


def test_assess_citeability_reasons():
    ok, reason = assess_citeability(
        data_quality="hand_labeled",
        source_url="https://example.com/a",
        quote_span="growth 5-7%",
    )
    assert ok and reason == "ok"
    ok, reason = assess_citeability(
        data_quality="listing_provisional", source_url="https://x", quote_span="y"
    )
    assert not ok and reason == "provisional"
    ok, reason = assess_citeability(
        data_quality="demo_structured", source_url="https://x", quote_span="y"
    )
    assert not ok and reason == "demo"
    ok, reason = assess_citeability(
        data_quality="hand_labeled", source_url="", quote_span="y"
    )
    assert not ok and reason == "missing_source"


def test_citation_id_stable():
    a = citation_id_for(
        company_id="infy",
        period="FY25",
        metric="revenue_growth_pct",
        source_url="u",
        quote_span="q",
    )
    b = citation_id_for(
        company_id="infy",
        period="FY25",
        metric="revenue_growth_pct",
        source_url="u",
        quote_span="q",
    )
    assert a == b


def test_span_offsets():
    s, e = span_offsets("hello growth 5-7% world", "growth 5-7%")
    assert s == 6 and e == 17


def test_span_offsets_folds_whitespace_and_quotes():
    text = "We expect “Margins” to\nremain — in a tight band."
    s, e = span_offsets(text, "Margins to remain - in a tight")
    assert s is not None and e is not None
    snippet = text[s:e]
    assert "Margins" in snippet and "tight" in snippet


def test_span_offsets_joins_ellipsis():
    text = "Revenue grew 19.7 percent in constant currency for the full year."
    s, e = span_offsets(text, "Revenue grew … for the full year")
    assert s == 0
    assert "19.7" in text[s:e]
    assert text[s:e].endswith("full year")


def test_documents_url_lookup_miss():
    from app.api.routes import documents_list

    body = documents_list(url="https://example.invalid/no-such-filing.pdf")
    assert body["count"] == 0
    assert body["documents"] == []


def test_enrich_strips_provisional_quote():
    class O:
        period = "FY25"
        metric = "revenue_growth_pct"
        source_url = "https://nseindia.com/x"
        quote_span = "5–7%"
        doc_id = None
        span_start = None
        span_end = None

    cite = enrich_outcome_citation(O(), company_id="nse_x", data_quality="listing_provisional")
    assert cite["citeable"] is False
    assert cite["quote_span"] is None


def test_search_entities_coverage_fields():
    hits = search_entities("INFY", limit=5)
    assert hits
    top = hits[0]
    assert "corpus_status" in top
    assert "doc_count" in top
    assert "citeable_outcomes" in top


def test_period_completeness_shape():
    pc = period_completeness("infy")
    assert pc["company_id"] == "infy"
    assert pc["periods"]
    assert "summary" in pc


def test_granger_gates_small_sample():
    out = granger_pairwise([1, 2, 3], [1, 2, 3])
    assert out["ok"] is False
    assert out["min_required"] == MIN_OBS_BIVARIATE


def test_granger_bundle_disclaimer():
    gci = list(range(20))
    price = [100 + i * 0.5 for i in range(20)]
    bundle = build_granger_bundle(gci_series=gci, price_series=price)
    assert "disclaimer" in bundle
    assert bundle["lasso_selected"]
    assert bundle["enabled"] is True
    assert any(t.get("method") == "granger_f_test" or t.get("ok") is False for t in bundle["granger_tests"])


def test_pit_warehouse_min_obs():
    from app.services.pit_warehouse import ensure_pit_series, TARGET_POINTS

    row = ensure_pit_series("infy")
    assert row["n"] >= TARGET_POINTS
    assert row["citeable"] is False
    assert row["series_kind"] == "demo_pit_extension"


def test_search_facet_filter():
    hits = search_entities("INFY", limit=5, data_quality="hand_labeled")
    assert hits
    assert all(h.get("data_quality") == "hand_labeled" for h in hits)
