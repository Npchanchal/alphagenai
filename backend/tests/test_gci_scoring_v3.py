"""GCI scorer v3 — exp δ, γ asymmetry, recency, audit deductions."""

from __future__ import annotations

import math

import pytest

from app.services.gci_scoring import (
    GCI_ALPHA,
    GCI_BETA,
    GCI_GAMMA_MISS,
    GCI_LAMBDA,
    GuidanceOutcome,
    OutcomeLabel,
    algorithm_id,
    audit_deduction,
    classify_outcome,
    compute_company_gci,
    compute_company_gci_v3,
    compute_gci_v3_detail,
    effective_band,
    normalized_deviation,
    outcome_score,
    outcome_score_v3,
    scorer_version,
)


def _o(
    period: str,
    metric: str,
    guided: float,
    actual: float | None,
    *,
    low: float | None = None,
    high: float | None = None,
    dropped: bool = False,
    unmapped: bool = False,
    confidence: float = 1.0,
) -> GuidanceOutcome:
    return GuidanceOutcome(
        period,
        metric,
        guided,
        actual,
        "t",
        confidence,
        guided_low=low,
        guided_high=high,
        dropped=dropped,
        unmapped=unmapped,
    )


def test_version_flag_defaults_v4(monkeypatch):
    monkeypatch.delenv("INTELLENS_GCI_VERSION", raising=False)
    assert scorer_version() == "v4"
    assert algorithm_id() == "gci_scoring_v4"


def test_version_flag_v2_legacy(monkeypatch):
    monkeypatch.setenv("INTELLENS_GCI_VERSION", "v2")
    assert scorer_version() == "v2"
    assert algorithm_id() == "gci_scoring_v2"
    beat = _o("FY24", "revenue_growth_pct", 10.0, 12.0)
    assert outcome_score(beat) >= 85.0


def test_version_flag_v3_explicit(monkeypatch):
    monkeypatch.setenv("INTELLENS_GCI_VERSION", "v3")
    assert scorer_version() == "v3"
    assert algorithm_id() == "gci_scoring_v3"
    o = _o("FY24", "revenue_growth_pct", 6.0, 5.5, low=5.0, high=7.0)
    assert outcome_score(o) == 100.0
    assert compute_company_gci([o]) == 100.0


def test_v3_in_band_is_100():
    o = _o("FY24", "revenue_growth_pct", 6.0, 5.5, low=5.0, high=7.0)
    assert normalized_deviation(o) == 0.0
    assert outcome_score_v3(o) == 100.0


def test_v3_point_estimate_synthetic_band():
    o = _o("FY24", "revenue_growth_pct", 10.0, 10.1)
    gmin, gmax, gmid, w = effective_band(o)
    assert abs(gmid - 10.0) < 1e-9
    assert abs(w - 0.2) < 1e-9
    assert gmin <= 10.1 <= gmax
    assert outcome_score_v3(o) == 100.0


def test_level_metric_point_band_stays_two_percent():
    o = _o("FY24", "production_volume_mmt", 460.0, 465.0)
    _gmin, _gmax, _gmid, w = effective_band(o)
    assert abs(w - 9.2) < 1e-9


def test_v3_miss_uses_gamma_and_exp():
    o = _o("FY24", "revenue_growth_pct", 6.0, 4.0, low=5.0, high=7.0)
    delta = normalized_deviation(o)
    assert delta is not None and abs(delta - 1.0) < 1e-6
    s = 100.0 * math.exp(-GCI_ALPHA * (delta**GCI_BETA))
    expected = max(0.0, 100.0 - GCI_GAMMA_MISS * (100.0 - s))
    assert outcome_score_v3(o) == pytest.approx(expected, rel=1e-6)
    beat = _o("FY24", "revenue_growth_pct", 6.0, 8.0, low=5.0, high=7.0)
    assert outcome_score_v3(beat) > outcome_score_v3(o)


def test_v3_beat_no_gamma_but_exp_decay():
    o = _o("FY24", "revenue_growth_pct", 6.0, 8.0, low=5.0, high=7.0)
    delta = normalized_deviation(o)
    assert delta is not None and abs(delta - 1.0) < 1e-6
    s = 100.0 * math.exp(-GCI_ALPHA * (delta**GCI_BETA))
    assert outcome_score_v3(o) == pytest.approx(s, rel=1e-6)


def test_v3_pending_and_unmapped_excluded():
    assert outcome_score_v3(_o("FY24", "revenue_growth_pct", 10.0, None)) is None
    u = _o("FY24", "revenue_growth_pct", 10.0, 10.0, unmapped=True)
    assert classify_outcome(u) == OutcomeLabel.UNMAPPED
    assert outcome_score_v3(u) is None
    assert compute_company_gci_v3([u]) is None


def test_v3_dropped_excluded_without_analyst_flag():
    met = _o("FY24", "revenue_growth_pct", 10.0, 10.0)
    dropped = _o("FY25", "capex_guidance", 100.0, None, dropped=True)
    assert audit_deduction([met, dropped]) == 0.0
    detail = compute_gci_v3_detail([met, dropped])
    assert detail.gci == 100.0
    assert detail.shenanigans_deduction == 0.0
    flagged = compute_gci_v3_detail([met, dropped], audit_flags=["guidance_withdrawal"])
    assert flagged.gci == 85.0
    assert flagged.shenanigans_deduction == 15.0
    assert audit_deduction([met, dropped], ["guidance_withdrawal"]) == 15.0


def test_v3_definition_shift_flag():
    met = _o("FY24", "revenue_growth_pct", 10.0, 10.0)
    detail = compute_gci_v3_detail([met], audit_flags=["definition_shift"])
    assert detail.gci == 90.0
    assert detail.shenanigans_deduction == 10.0


def test_v3_recency_weights_recent_higher():
    older_miss = _o("FY23", "revenue_growth_pct", 6.0, 4.0, low=5.0, high=7.0)
    recent_met = _o("FY24", "revenue_growth_pct", 6.0, 6.0, low=5.0, high=7.0)
    gci = compute_company_gci_v3([older_miss, recent_met])
    assert gci is not None
    miss_s = outcome_score_v3(older_miss)
    assert miss_s is not None
    equal = (miss_s + 100.0) / 2.0
    assert gci > equal
    w1 = 1.0
    w2 = math.exp(-GCI_LAMBDA)
    expected = (w1 * 100.0 + w2 * miss_s) / (w1 + w2)
    assert gci == pytest.approx(round(expected, 1), abs=0.05)


def test_v3_metric_importance_weights():
    good = _o("FY24", "revenue_growth_pct", 10.0, 10.0)
    bad = _o("FY24", "ebitda_margin_pct", 20.0, 10.0, low=19.0, high=21.0)
    equal = compute_company_gci_v3([good, bad])
    rev_heavy = compute_company_gci_v3(
        [good, bad],
        metric_weights={"revenue_growth_pct": 3.0, "ebitda_margin_pct": 1.0},
    )
    assert equal is not None and rev_heavy is not None
    assert rev_heavy > equal


def test_v3_insufficient_history_is_low_confidence_not_shrunk():
    # W1.5 (decision D5): sector shrinkage removed — sector_mean is ignored.
    only = _o("FY24", "revenue_growth_pct", 10.0, 10.0)
    detail = compute_gci_v3_detail([only], sector_mean=60.0)
    assert detail.low_confidence is True
    assert detail.periods_used == 1
    assert detail.gci == 100.0


def test_v3_four_periods_full_confidence():
    rows = [_o(f"FY{20 + i}", "revenue_growth_pct", 10.0, 10.0) for i in range(4)]
    detail = compute_gci_v3_detail(rows, sector_mean=50.0)
    assert detail.low_confidence is False
    assert detail.gci == 100.0


def test_v2_unchanged_when_pinned():
    beat = _o("FY24", "revenue_growth_pct", 10.0, 12.0)
    miss = _o("FY24", "revenue_growth_pct", 10.0, 8.0)
    assert outcome_score(beat, version="v2") >= 85.0
    assert outcome_score(miss, version="v2") == 60.0
    dropped = _o("FY24", "capex_guidance", 100.0, None, dropped=True)
    assert outcome_score(dropped, version="v2") == 35.0
