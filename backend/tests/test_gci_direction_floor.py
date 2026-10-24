"""v4.2: metric direction (σ) and the width floor on narrow bands."""

from __future__ import annotations

import pytest

from app.services.gci_scoring import (
    RATE_FLOOR_PP,
    GuidanceOutcome,
    OutcomeLabel,
    band_floor,
    classify_outcome,
    effective_band,
    metric_direction,
    normalized_surprise,
    outcome_score_v2,
    outcome_score_v4,
)


def _o(metric: str, actual: float, low: float, high: float) -> GuidanceOutcome:
    return GuidanceOutcome(
        "FY25", metric, (low + high) / 2.0, actual, "t", guided_low=low, guided_high=high
    )


def test_directions_from_catalog():
    assert metric_direction("revenue_growth_pct") == "higher"
    assert metric_direction("wc_days") == "lower"
    assert metric_direction("capex_guidance") == "two_sided"
    assert metric_direction("rd_spend_pct_of_revenue") == "two_sided"
    assert metric_direction("something_custom") == "higher"


def test_lower_is_better_metric_flips_beat_and_miss():
    under = _o("wc_days", 50.0, 58.0, 62.0)
    over = _o("wc_days", 70.0, 58.0, 62.0)
    assert classify_outcome(under) == OutcomeLabel.EXCEEDED
    assert classify_outcome(over) == OutcomeLabel.MISSED
    assert outcome_score_v4(under) >= 60.0
    assert outcome_score_v4(over) < outcome_score_v4(under)
    assert outcome_score_v2(under) >= 85.0


def test_two_sided_metric_misses_either_way():
    under = _o("capex_guidance", 8000.0, 9500.0, 10500.0)
    over = _o("capex_guidance", 12000.0, 9500.0, 10500.0)
    assert classify_outcome(under) == OutcomeLabel.MISSED
    assert classify_outcome(over) == OutcomeLabel.MISSED
    assert outcome_score_v4(under) < 60.0
    assert outcome_score_v4(over) < 60.0


def test_higher_metric_unchanged():
    beat = _o("revenue_growth_pct", 9.0, 5.0, 7.0)
    miss = _o("revenue_growth_pct", 3.0, 5.0, 7.0)
    assert classify_outcome(beat) == OutcomeLabel.EXCEEDED
    assert classify_outcome(miss) == OutcomeLabel.MISSED


def test_rate_floor_widens_narrow_band_only():
    narrow = _o("nim_pct", 3.88, 3.75, 3.85)
    _lo, _hi, mid, w = effective_band(narrow)
    assert mid == pytest.approx(3.8)
    assert w == pytest.approx(RATE_FLOOR_PP)
    assert outcome_score_v4(narrow) == 100.0
    wide = _o("revenue_growth_pct", 6.0, 5.0, 7.0)
    assert effective_band(wide)[3] == pytest.approx(1.0)


def test_floor_is_relative_for_large_rates():
    assert band_floor("ebitda_margin_pct", 25.0) == pytest.approx(0.5)
    assert band_floor("nim_pct", 3.8) == pytest.approx(RATE_FLOOR_PP)
    assert band_floor("production_volume_mmt", 460.0) == pytest.approx(9.2)


def test_label_and_score_agree_inside_rate_floor():
    point = GuidanceOutcome("FY25", "nim_pct", 3.80, 3.88, "t")
    assert classify_outcome(point) == OutcomeLabel.MET
    assert outcome_score_v4(point) == 100.0


def test_small_rate_beat_beyond_floor_still_a_beat():
    point = GuidanceOutcome("FY25", "nim_pct", 3.80, 3.98, "t")
    assert classify_outcome(point) == OutcomeLabel.EXCEEDED
    assert 60.0 < outcome_score_v4(point) < 100.0


def test_normalized_surprise_sign():
    assert normalized_surprise(_o("revenue_growth_pct", 8.0, 5.0, 7.0)) == pytest.approx(2.0, abs=1e-4)
    assert normalized_surprise(_o("wc_days", 56.0, 58.0, 62.0)) == pytest.approx(2.0, abs=1e-4)
    assert normalized_surprise(_o("capex_guidance", 9000.0, 9500.0, 10500.0)) < 0
    assert normalized_surprise(_o("capex_guidance", 11000.0, 9500.0, 10500.0)) < 0
