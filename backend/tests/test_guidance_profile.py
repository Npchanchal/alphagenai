"""Guidance profile: counts, labels from 6 closed figures, divergences. Never moves GCI."""

from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.main import app
from app.services.gci_scoring import GuidanceOutcome, compute_gci_v3_detail
from app.services.guidance_profile import (
    MIN_PROFILE_ROWS,
    divergences,
    guidance_profile,
    in_year_revisions,
    results_vs_range,
    surprise_spread,
)


def _row(
    period: str,
    metric: str,
    low: float,
    high: float,
    actual: float,
    *,
    revised_to: Optional[tuple] = None,
) -> GuidanceOutcome:
    revisions = ()
    if revised_to:
        revisions = ({"as_of": "2024-10-01", "guided_low": revised_to[0], "guided_high": revised_to[1]},)
    return GuidanceOutcome(
        period,
        metric,
        (low + high) / 2.0,
        actual,
        "t",
        guided_low=low,
        guided_high=high,
        source_url=f"https://example.com/{period}/{metric}/actual",
        quote_span="q",
        as_of="2025-04-20",
        guidance_source_url=f"https://example.com/{period}/{metric}/guide",
        guidance_quote="g",
        guidance_as_of="2024-04-20",
        reviewed_by="analyst:t",
        reviewed_at="2026-10-18",
        revisions=revisions,
    )


def _beats(n: int):
    return [_row(f"FY{18 + i}", "revenue_growth_pct", 5.0, 7.0, 9.0) for i in range(n)]


def test_counts_without_label_below_minimum():
    out = results_vs_range(_beats(MIN_PROFILE_ROWS - 1))
    assert out["above"] == MIN_PROFILE_ROWS - 1
    assert out["label"] is None and out["bias_index"] is None
    assert out["sentence"] == "All 5 closed guidance figures came in above the guided range."


def test_sentences_skip_zero_counts():
    mixed = _beats(4) + [_row("FY40", "revenue_growth_pct", 5.0, 7.0, 2.0)]
    assert results_vs_range(mixed)["sentence"] == (
        "Of 5 closed guidance figures, 4 came in above the range and 1 below it."
    )
    one = [_row("FY25", "revenue_growth_pct", 5.0, 7.0, 6.0, revised_to=(6.0, 8.0))]
    assert results_vs_range(one)["sentence"] == "The one closed guidance figure came in within the guided range."
    assert in_year_revisions(one)["sentence"] == (
        "Guidance for the one closed figure was revised during the year, toward a stronger figure."
    )


def test_label_at_minimum():
    out = results_vs_range(_beats(MIN_PROFILE_ROWS))
    assert out["bias_index"] == 100.0
    assert out["label"] == "usually_above"


def test_balanced_and_below():
    rows = _beats(1) + [_row(f"FY{30 + i}", "revenue_growth_pct", 5.0, 7.0, 6.0) for i in range(5)]
    assert results_vs_range(rows)["label"] == "balanced"
    misses = [_row(f"FY{18 + i}", "revenue_growth_pct", 5.0, 7.0, 2.0) for i in range(6)]
    assert results_vs_range(misses)["label"] == "usually_below"


def test_walk_down_uses_metric_direction():
    cut = [_row(f"FY{18 + i}", "revenue_growth_pct", 5.0, 7.0, 6.0, revised_to=(4.0, 6.0)) for i in range(2)]
    flat = [_row(f"FY{30 + i}", "revenue_growth_pct", 5.0, 7.0, 6.0) for i in range(4)]
    out = in_year_revisions(cut + flat)
    assert out["toward_weaker"] == 2 and out["label"] == "walk_down"
    # For working-capital days, raising the guided figure is the weaker direction.
    days = [_row(f"FY{18 + i}", "wc_days", 58.0, 62.0, 60.0, revised_to=(63.0, 67.0)) for i in range(6)]
    assert in_year_revisions(days)["label"] == "walk_down"


def test_stable_path():
    rows = [_row(f"FY{18 + i}", "revenue_growth_pct", 5.0, 7.0, 6.0) for i in range(6)]
    out = in_year_revisions(rows)
    assert out["label"] == "stable"
    assert out["sentence"].startswith("None of the 6 closed figures")


def test_divergence_flag_is_factual():
    rows = [
        _row("FY25", "revenue_growth_pct", 13.0, 16.0, 18.0),
        _row("FY25", "ebitda_margin_pct", 24.0, 25.0, 23.0),
    ]
    flags = divergences(rows)
    assert len(flags) == 1
    flag = flags[0]
    assert flag["kind"] == "revenue_above_margin_below"
    assert "guided 13–16%, reported 18%" in flag["sentence"]
    assert "EBITDA margin came in below it" in flag["sentence"]
    assert len(flag["sources"]) == 2
    banned = ("engineering", "aggressive", "strain", "unprofitable")
    assert not any(w in flag["sentence"].lower() for w in banned)


def test_unreviewed_rows_do_not_count():
    rows = _beats(6)
    no_promise_cite = GuidanceOutcome(
        "FY99", "revenue_growth_pct", 6.0, 9.0, "t", guided_low=5.0, guided_high=7.0,
        source_url="https://example.com/a", quote_span="q", as_of="2025-04-20",
    )
    assert guidance_profile(rows + [no_promise_cite])["closed_figures"] == 6


def test_profile_does_not_move_gci():
    rows = _beats(3) + [_row("FY30", "revenue_growth_pct", 5.0, 7.0, 6.0, revised_to=(4.0, 6.0))]
    before = compute_gci_v3_detail(rows, version="v4").gci
    guidance_profile(rows)
    assert compute_gci_v3_detail(rows, version="v4").gci == before


def test_spread_is_pilot_and_needs_minimum():
    assert surprise_spread(_beats(3))["value"] is None
    assert surprise_spread(_beats(6))["pilot"] is True
    assert "surprise_spread" not in guidance_profile(_beats(6))


def test_dossier_carries_profile():
    client = TestClient(app)
    body = client.get("/api/companies/infy/gci").json()
    profile = body.get("guidance_profile")
    assert profile is not None
    assert profile["closed_figures"] >= 1
    assert profile["note"] == "Describes the delivery record. Not part of the GCI."
