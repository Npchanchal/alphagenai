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


# --- companion indexes (preview; never part of the GCI) -------------------------

from dataclasses import replace as _replace  # noqa: E402

from app.services.guidance_profile import (  # noqa: E402
    COMPANION_IDS,
    COMPANION_MIN_ROWS,
    companion_indexes,
    growth_accuracy_pp,
    guidance_bias,
    guidance_diagnostics,
    guidance_setting,
    guidance_visibility,
    revision_discipline,
    setting_reference,
)


def _growth(period: str, low: float, high: float, actual: float, **kw) -> GuidanceOutcome:
    return _row(period, "revenue_growth_cc_pct", low, high, actual, **kw)


def test_companions_are_preview_unranked_and_cover_every_relocated_element():
    rows = [_growth(p, 1, 3, a) for p, a in (("FY22", 2), ("FY23", 4.2), ("FY24", 0.5))]
    body = companion_indexes(rows, as_of="2026-01-01")
    assert [i["id"] for i in body["indexes"]] == list(COMPANION_IDS)
    for i in body["indexes"]:
        assert i["status"] == "preview" and i["part_of_gci"] is False and i["rankable"] is False
        assert i["algorithm_id"] == f"companion_{i['id']}_v1"


def test_growth_accuracy_reads_percentage_points_outside_the_range():
    rows = [_growth("FY22", 1, 3, 2), _growth("FY23", 1, 3, 4.2), _growth("FY24", 4, 7, 1.4)]
    idx = growth_accuracy_pp(rows)
    assert [i["pp_outside"] for i in idx["items"]] == [0.0, 1.2, 2.6]
    assert [i["side"] for i in idx["items"]] == ["inside", "above", "below"]
    assert idx["value"] == round((100 + 88 + 74) / 3, 1)
    assert "1.2 percentage points" in idx["sentence"]


def test_guidance_bias_is_50_centred_with_growth_floor_and_tags():
    # Infosys revenue growth, opening ranges: FY24 4–7% → 1.4%, FY25 1–3% → 4.2%, FY26 0–3% → 3.1%.
    rows = [_growth("FY24", 4, 7, 1.4), _growth("FY25", 1, 3, 4.2), _growth("FY26", 0, 3, 3.1)]
    idx = guidance_bias(rows)
    assert [i["tag"] for i in idx["items"]] == ["miss", "beat", "beat"]
    # 5-point growth floor: FY26 overshoot of 1.6 points reads 66, not the full-scale 100 of the owner note.
    assert [i["score"] for i in idx["items"]] == [12.73, 72.0, 66.0]
    assert idx["value"] == round((12.73 + 72.0 + 66.0) / 3, 1)
    assert idx["tags"] == {"beat": 2, "in_line": 0, "miss": 1, "outside_range": 0}
    assert idx["part_of_gci"] is False and idx["rankable"] is False
    assert "2 beat the opening guidance" in idx["sentence"] and "50 is the guided midpoint" in idx["sentence"]


def test_guidance_bias_follows_metric_direction_and_needs_three_rows():
    cost_overrun = _row("FY24", "wc_days", 40, 50, 55)  # lower is better: above the range is a miss
    exact = _row("FY25", "wc_days", 40, 50, 45)
    idx = guidance_bias([cost_overrun, exact])
    assert [i["tag"] for i in idx["items"]] == ["miss", "in_line"]
    assert idx["items"][0]["score"] < 50 and idx["items"][1]["score"] == 50.0
    assert idx["value"] is None  # two rows < COMPANION_MIN_ROWS


def test_revision_discipline_separates_walk_downs_from_honest_raises():
    rows = [
        _row("FY22", "revenue_cr", 100, 110, 105, revised_to=(90, 100)),  # walked down
        _row("FY23", "revenue_cr", 100, 110, 115, revised_to=(110, 120)),  # raised
        _row("FY24", "revenue_cr", 100, 110, 105),
    ]
    idx = revision_discipline(rows)
    assert idx["value"] == round(100 * 2 / 3, 1)
    assert [i["toward_weaker"] for i in idx["items"]] == [1, 0, 0]
    assert idx["updates_per_figure"] == round(2 / 3, 2)


def test_guidance_visibility_is_smooth_and_cadence_aware():
    fy = _row("FY25", "revenue_cr", 100, 110, 105)
    early = _replace(fy, guidance_as_of="2024-03-25")
    late = _replace(fy, guidance_as_of="2025-01-30")
    after = _replace(fy, guidance_as_of="2025-04-05")
    idx = guidance_visibility([early, late, after])
    assert [i["score"] for i in idx["items"]] == [100.0, round(100 * 60 / 365, 1)]
    assert idx["after_period_end"] == 1
    assert idx["value"] is None  # two dated rows < COMPANION_MIN_ROWS
    assert COMPANION_MIN_ROWS == 3


def test_guidance_setting_flags_wide_ranges_and_easy_beats():
    ref = setting_reference({
        "a": [_growth("FY22", 10, 12, 11), _growth("FY23", 10, 12, 11), _growth("FY24", 10, 12, 11)],
    })
    assert ref == {"revenue_growth_cc_pct": 2.0}
    rows = [
        _growth("FY22", 0, 10, 5),  # width 10 > 2 × 2
        _growth("FY23", 10, 12, 15),  # cleared top by 3 > width 2
        _growth("FY24", 10, 12, 11),
    ]
    idx = guidance_setting(rows, reference=ref)
    assert [(i["wide_range"], i["cleared_by_wide_margin"]) for i in idx["items"]] == [
        (True, False), (False, True), (False, False),
    ]
    assert idx["value"] == round(100 / 3, 1)


def test_diagnostics_find_withdrawals_reinstatements_basis_switches_and_extensions():
    rows = [
        _replace(_row("FY22", "revenue_cr", 100, 110, 105), reporting_basis="reported"),
        _replace(_row("FY23", "revenue_cr", 100, 110, 105), dropped=True),
        _replace(_row("FY24", "revenue_cr", 100, 110, 105), reporting_basis="constant_currency"),
    ]
    commitments = [
        {"id": "c1", "review_status": "accepted", "type": "capacity", "subject": "Plant A",
         "state": "superseded", "due_date": "2024-03-31", "as_of": "2023-01-01"},
        {"id": "c2", "review_status": "accepted", "type": "capacity", "subject": "plant a",
         "state": "open", "due_date": "2025-03-31", "as_of": "2024-02-01"},
    ]
    d = guidance_diagnostics(rows, commitments=commitments)
    assert d["withdrawals"] == [{"parameter": "revenue_cr", "period": "FY23", "source_url": rows[1].guidance_source_url}]
    assert d["reinstatements"] == [{"parameter": "revenue_cr", "withdrawn": "FY23", "reinstated": "FY24"}]
    assert d["basis_switches"][0]["from_basis"] == "reported" and d["basis_switches"][0]["to_basis"] == "constant_currency"
    assert d["deadline_extensions"][0]["new_deadline"] == "2025-03-31"
    assert d["thin_history"]["closed_periods"] == 2 and d["thin_history"]["thin"] is False


def test_companions_do_not_move_gci():
    rows = [_growth(p, 1, 3, a) for p, a in (("FY22", 2), ("FY23", 4.2), ("FY24", 0.5))]
    before = compute_gci_v3_detail(rows, version="v4").gci
    companion_indexes(rows, as_of="2026-01-01")
    guidance_diagnostics(rows)
    assert compute_gci_v3_detail(rows, version="v4").gci == before
