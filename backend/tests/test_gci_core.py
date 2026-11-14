"""GCI Core v2.4 shadow engine (docs/PLAN_GCI_CORE.md).

Golden values are the locked methodology v2.4 worked examples (§24), with the
v2.4.1 erratum for §24.10, checked to four decimals with Decimal arithmetic. The
v2.5 change-control proposals are tested separately under ``ruleset=PROPOSAL``.
"""

from __future__ import annotations

import random
from dataclasses import replace
from decimal import Decimal

import pytest

from app.data.markets import (
    GCI_CORE_PROFILES,
    MARKETS,
    company_market_id,
    core_publication_status,
    gci_core_profile,
)
from app.data.metric_catalog import metric_is_growth
from app.data.seed import get_outcomes, outcome_from_dict, reset_data
from app.services import gci_scoring as g
from app.services.gci_scoring import GuidanceOutcome
from app.services.score_policy import CORE_REASON_CODES, core_route

PROPOSAL = g.CORE_RULESET_PROPOSAL
FY24 = dict(period_end="2024-03-31", period_start="2023-04-01")


def setup_function():
    reset_data()


def _score(metric, low, high, actual, **kw):
    z, reason = g.core_vintage_z(metric, low, high, actual, **kw)
    assert reason is None
    return round(float(g.core_score_from_z(z)), 4)


def _row(**kw) -> GuidanceOutcome:
    base = dict(period="FY24", metric="revenue_cr", guided_value=100.0, actual_value=None, guided_text="",
                guidance_as_of="2023-04-15", as_of="2024-04-20")
    base.update(kw)
    return GuidanceOutcome(**base)


# --- locked v2.4: single vintage (§9, §24) ------------------------------------


@pytest.mark.parametrize(
    "metric,low,high,actual,expected",
    [
        ("revenue_cr", 100, 110, 100, 95.2381),  # §24.1
        ("ebitda_margin_pct", 5, 6, 5, 90.9091),  # §24.2
        ("revenue_cr", -10, 10.02, 0.10, 99.1009),  # §24.3
        ("revenue_cr", 0, 10, 0, 0.0),  # §9.1 table
        ("revenue_cr", 0, 10, 5, 100.0),
        ("revenue_cr", -10, 0, 0, 0.0),
        ("revenue_cr", -10, 0, 10, 0.0),
        ("revenue_cr", 100, 100, 102.5, 97.5),  # point target
        ("revenue_growth_pct", 10, 10, 12, 80.0),  # §9: a percentage is scored as stated
    ],
)
def test_locked_worked_examples(metric, low, high, actual, expected):
    assert _score(metric, low, high, actual) == expected


def test_locked_zero_references():
    assert _score("revenue_cr", 0, 0, 0.03) == 97.0  # §24.4: one presentation unit
    assert _score("ebitda_margin_pct", 0, 0, -2, prior_value=10) == 80.0  # §24.5
    assert g.core_vintage_z("ebitda_margin_pct", 0, 0, 1) == (None, "ZERO_REFERENCE_UNAVAILABLE")


def test_locked_one_sided_bounds_are_symmetric():
    # §24.6
    assert _score("revenue_cr", 100, 100, 120, bound="floor") == 80.0
    assert _score("revenue_cr", 100, 100, 102.5, bound="floor") == 97.5
    assert _score("revenue_cr", 100, 100, 80, bound="floor") == 80.0
    assert _score("revenue_cr", 100, 100, 80, bound="ceiling") == 80.0
    assert _score("revenue_cr", 100, 100, 102.5, bound="ceiling") == 97.5
    assert _score("revenue_cr", 100, 100, 120, bound="ceiling") == 80.0


def test_score_is_bounded_and_monotone_in_distance():
    rng = random.Random(7)
    for rs in g.CORE_RULESETS:
        for _ in range(300):
            low = rng.uniform(-50, 200)
            high = low + rng.uniform(0, 40)
            a1 = rng.uniform(-100, 300)
            mid = (low + high) / 2
            a2 = mid + (a1 - mid) * rng.uniform(1.0, 2.0)  # same side, further away
            s1 = _score("revenue_cr", low, high, a1, ruleset=rs)
            s2 = _score("revenue_cr", low, high, a2, ruleset=rs)
            assert 0.0 <= s2 <= s1 <= 100.0


# --- locked v2.4: frequency, lead time, revisions (§11–§14, §24.9–§24.10) ------


@pytest.mark.parametrize(
    "n,cadence,expected",
    [(0, "FY", 0), (1, "FY", 0.2), (2, "FY", 0.275), (5, "FY", 0.5), (6, "FY", 0.58), (10, "FY", 0.9),
     (20, "FY", 0.9), (1, "Q", 0.2), (2, "Q", 0.5), (3, "Q", 0.58), (2, "H", 0.275)],
)
def test_locked_frequency_schedule(n, cadence, expected):
    assert float(g.core_frequency_penalty(n, cadence)) == pytest.approx(expected)


@pytest.mark.parametrize(
    "days,factor", [(-1, 0.8), (0, 0.8), (29, 0.8), (30, 0.9), (89, 0.9), (90, 1.0), (179, 1.0), (180, 1.1), (400, 1.1)]
)
def test_lead_time_factor_schedule(days, factor):
    assert float(g.core_lead_time_factor(days)) == factor


def test_ten_revisions_retain_ten_percent():
    # §24.9: every vintage scores 100; ten revisions cost the 90% cap.
    assert float(Decimal("100") * (1 - g.core_frequency_penalty(10))) == 10.0


def test_late_walk_down_erratum_v2_4_1():
    # §24.10 erratum: original floor 100, revised floor 80, actual 80. The published
    # D_f = 84.7492 and C_f = 67.7993 hold when the revision comes 11/12 of the horizon later.
    z0, _ = g.core_vintage_z("revenue_cr", 100, 100, 80, bound="floor")
    z1, _ = g.core_vintage_z("revenue_cr", 80, 80, 80, bound="floor")
    m = g.core_revision_magnitude("revenue_cr", (Decimal(100), Decimal(100)), (Decimal(80), Decimal(80)))
    assert m == Decimal(1) / Decimal(6)
    w1 = g.core_weight_exponent(Decimal(11) / Decimal(12), m, -1).exp()
    d_f = (g.core_score_from_z(z0) + w1 * g.core_score_from_z(z1)) / (1 + w1)
    c_f = d_f * (1 - g.core_frequency_penalty(1)) * Decimal("1.0")
    assert round(float(d_f), 4) == 84.7492
    assert round(float(c_f), 4) == 67.7993


def test_family_score_applies_lead_time_and_caps_at_100():
    for as_of, days, factor, score in (
        ("2024-03-15", 16, 0.8, 80.0),
        ("2024-01-15", 76, 0.9, 90.0),
        ("2023-11-01", 151, 1.0, 100.0),
        ("2023-09-30", 183, 1.1, 100.0),
    ):
        f = g.core_family_detail(_row(guided_low=100, guided_high=100, actual_value=100, guidance_as_of=as_of), **FY24)
        assert (f["lead_time_days"], f["lead_time_factor"], f["score"]) == (days, factor, score)
    late = g.core_family_detail(_row(guided_low=100, guided_high=100, actual_value=100, guidance_as_of="2024-03-15"), **FY24)
    assert "LATE_GUIDANCE_FLAG" in late["flags"]
    early = g.core_family_detail(_row(guided_low=100, guided_high=100, actual_value=90, guidance_as_of="2023-09-30"), **FY24)
    assert early["score"] == 99.0  # 90 × 1.1


def test_lead_time_needs_an_issuance_date_and_a_period_end():
    undated = _row(guided_low=100, guided_high=100, actual_value=100, guidance_as_of=None)
    assert g.core_family_detail(undated, **FY24)["reason_code"] == "ISSUANCE_TIME_UNKNOWN"
    assert g.core_family_detail(_row(guided_low=100, guided_high=100, actual_value=100))["reason_code"] == "PERIOD_END_UNKNOWN"
    after = _row(guided_low=100, guided_high=100, actual_value=100, guidance_as_of="2024-04-05")
    f = g.core_family_detail(after, **FY24)
    assert f["score"] is None and f["reason_code"] == "GUIDANCE_AFTER_PERIOD_END"


def _two_vintage(g1, actual, metric="revenue_cr"):
    return _row(
        metric=metric, guided_value=100, guided_low=100, guided_high=100, actual_value=actual,
        revisions=({"as_of": "2023-07-14", "guided_low": g1, "guided_high": g1},),
    )


def test_locked_counts_every_revision_with_numerical_sign():
    walk = g.core_family_detail(_two_vintage(80, 80), **FY24)
    silent_miss = g.core_family_detail(_two_vintage(100, 80), **FY24)
    raise_ = g.core_family_detail(_two_vintage(120, 120), **FY24)
    assert walk["score"] == 77.0589 and walk["revisions_counted"] == 1
    assert silent_miss["score"] == 88.0 and silent_miss["revisions_counted"] == 0
    assert raise_["score"] == 77.7614 and raise_["revisions_counted"] == 1
    cost_cut = g.core_family_detail(_two_vintage(80, 80, "wc_days"), **FY24)
    assert cost_cut["revisions_counted"] == 1 and cost_cut["vintages"][1]["direction"] == -1


def test_locked_frequency_window_is_the_target_period():
    after = _row(guided_low=100, guided_high=100, actual_value=80,
                 revisions=({"as_of": "2024-04-10", "guided_low": 80, "guided_high": 80},))
    f = g.core_family_detail(after, **FY24)
    assert f["revisions_counted"] == 0
    assert [v["eligible"] for v in f["vintages"]] == [True, False]
    assert f["score"] == 88.0  # 80 × 1.1, no frequency penalty
    before = _row(guided_low=100, guided_high=100, actual_value=80, guidance_as_of="2023-02-15",
                  revisions=({"as_of": "2023-03-10", "guided_low": 90, "guided_high": 90},))
    assert g.core_family_detail(before, **FY24)["revisions_counted"] == 0


def test_earlier_vintages_always_weigh_more():
    rng = random.Random(11)
    for rs in g.CORE_RULESETS:
        for _ in range(150):
            revs, low, day = [], 100.0, 0
            for _ in range(rng.randint(1, 5)):
                low += rng.uniform(-15, 15)
                day += rng.randint(0, 80)
                revs.append({"as_of": f"2023-{4 + day // 30:02d}-{1 + day % 28:02d}", "guided_low": low, "guided_high": low + 5})
            row = _row(guided_low=100, guided_high=105, actual_value=rng.uniform(80, 130),
                       guidance_as_of="2023-04-01", revisions=tuple(revs))
            f = g.core_family_detail(row, ruleset=rs, **FY24)
            weights = [v["weight"] for v in f["vintages"] if v.get("eligible") and "weight" in v]
            assert all(a >= b for a, b in zip(weights, weights[1:]))
            assert 0 <= f["score"] <= 100


def test_infosys_fy22_revision_trail_scores_on_the_original_promise():
    rows = [o for o in get_outcomes("infy") if o.period == "FY22" and o.metric == "revenue_growth_cc_pct"]
    if not rows or not rows[0].revisions:
        pytest.skip("Infosys FY22 revision trail not in this dataset")
    f = g.core_family_detail(rows[0], period_end="2022-03-31", period_start="2021-04-01")
    opening = f["vintages"][0]
    assert opening["weight"] == max(v["weight"] for v in f["vintages"] if "weight" in v)
    assert 0 < f["score"] <= 100


# --- v2.5 change-control proposals (never the default) --------------------------


def test_proposal_rules_only_run_when_asked():
    assert _score("revenue_cr", -10, 10.02, 0.10, ruleset=PROPOSAL) == 99.5504  # D-03
    assert _score("revenue_cr", 0, 10, 0, ruleset=PROPOSAL) == 50.0
    assert _score("revenue_cr", 100, 100, 120, bound="floor", ruleset=PROPOSAL) == 90.0  # D-01
    assert metric_is_growth("revenue_growth_pct") and not metric_is_growth("ebitda_margin_pct")
    assert _score("revenue_growth_pct", 10, 10, 12, ruleset=PROPOSAL) == 98.1818  # D-02
    assert g.core_vintage_z("revenue_cr", 0, 0, 5, ruleset=PROPOSAL) == (None, "ZERO_REFERENCE_UNAVAILABLE")  # D-04
    assert _score("revenue_cr", 0, 0, 5, zero_reference=100, ruleset=PROPOSAL) == 95.0
    assert float(g.core_frequency_penalty(3, "Q", PROPOSAL)) == pytest.approx(0.7)  # D-08
    assert float(g.core_frequency_penalty(2, "H", PROPOSAL)) == pytest.approx(0.35)
    with pytest.raises(ValueError):
        g.core_vintage_z("revenue_cr", 1, 2, 1, ruleset="v9")


def test_proposal_direction_aware_revisions():
    kw = dict(ruleset=PROPOSAL, **FY24)
    walk = g.core_family_detail(_two_vintage(80, 80), **kw)
    silent = g.core_family_detail(_two_vintage(100, 80), **kw)
    raise_ = g.core_family_detail(_two_vintage(120, 120), **kw)
    assert (walk["score"], silent["score"], raise_["score"]) == (70.0535, 80.0, 88.3653)
    assert walk["lead_time_factor"] is None  # D-07: diagnostic only
    assert g.core_family_detail(_two_vintage(80, 80, "wc_days"), **kw)["revisions_counted"] == 0  # D-31
    after = _row(guided_low=100, guided_high=100, actual_value=80,
                 revisions=({"as_of": "2024-04-10", "guided_low": 80, "guided_high": 80},))
    assert g.core_family_detail(after, **kw)["score"] == 64.0  # counted to the result date


# --- routes and reasons -------------------------------------------------------


def test_routes_name_a_reason():
    assert core_route(_row(unmapped=True)) == ("COMMITMENT_RECORD", "NO_ELIGIBLE_PROMISE")
    assert core_route(_row(dropped=True)) == ("WITHDRAWN", "WITHDRAWN")
    assert core_route(_row()) == ("NOT_DUE", "OUTCOME_NOT_DUE")
    assert core_route(_row(actual_value=1, condition_state="not_activated"))[1] == "CONDITION_NOT_ACTIVATED"
    assert core_route(_row(actual_value=1, guidance_as_of="2024-05-01", as_of="2024-04-01"))[1] == "FUTURE_SOURCE"
    assert core_route(_row(actual_value=1, source_url="u", quote_span="q", as_of="2024-04-01"))[1] == "PENDING_GUIDANCE_CITE"
    assert core_route(_row(actual_value=1, unit="inr_cr", actual_unit="usd_mn"))[1] == "UNIT_CONVERSION_ERROR"
    assert core_route(_row(actual_value=1, bound="about"))[1] == "AMBIGUOUS_DIRECTION"
    assert core_route(_row(actual_value=1)) == ("QUANT", None)


def test_every_emitted_reason_is_in_the_vocabulary():
    from app.data.seed import list_companies

    for c in list_companies():
        for rs in g.CORE_RULESETS:
            detail = g.compute_core_detail(get_outcomes(c["id"]), ruleset=rs)
            for code in detail["reason_counts"]:
                assert code in CORE_REASON_CODES, code


# --- company aggregation, Qual branch, Composite (§15–§17) -----------------------


def _company_rows():
    lead = dict(guidance_as_of="2023-11-01")  # 151 days before FY24 end → factor 1.0
    return [
        _row(period="FY24", metric="revenue_cr", guided_low=100, guided_high=110, actual_value=100, **lead),
        _row(period="FY24", metric="ebitda_margin_pct", guided_low=5, guided_high=6, actual_value=5, **lead),
        _row(period="FY24", metric="capex_cr", guided_low=100, guided_high=100, actual_value=120, bound="floor", **lead),
    ]


def test_equal_parameter_weights_locked():
    d = g.compute_core_detail(_company_rows())
    assert [p["included"] for p in d["parameters"]] == [True, True, True]
    assert d["quant_gci_exact"].startswith("88.7157")  # §24.8 Quant: 95.2381, 90.9091, 80
    assert d["composite_basis"] == "quant_only" and d["composite_gci"] == d["quant_gci"]


def test_proposal_drops_thin_parameters_d10():
    rows = [
        _row(period="FY23", metric="revenue_cr", guided_low=100, guided_high=100, actual_value=100,
             guidance_as_of="2022-04-15", as_of="2023-04-20"),
        _row(period="FY24", metric="revenue_cr", guided_low=100, guided_high=100, actual_value=90),
        _row(period="FY24", metric="capex_cr", guided_low=100, guided_high=100, actual_value=0),
    ]
    d = g.compute_core_detail(rows, ruleset=PROPOSAL)
    params = {p["parameter"]: p for p in d["parameters"]}
    assert params["capex_cr"]["included"] is False
    assert d["algorithm_id"] == g.CORE_PROPOSAL_ALGORITHM_ID


def _c(state, due="FY24", **kw):
    return {"id": f"c{state}{due}{kw.get('type', '')}", "company_id": "x", "type": kw.pop("type", "capacity"),
            "review_status": "accepted", "state": state, "due_period": due, "subject": "s", "outcome": "o",
            "quote": "q", "source_url": "u", "as_of": "2023-05-01", **kw}


def test_company_hierarchy_and_composite_24_8():
    comps = [{"weight": 23, "fulfilled": True}, {"weight": 2, "fulfilled": False}]
    qual = [
        _c("partially_delivered", proof={"components": comps}),  # 23 of 25 → 92 (§24.7)
        _c("partially_delivered", type="capex", proof={"fulfilled_fraction": 0.9}),  # 90
    ]
    d = g.compute_core_detail(_company_rows(), commitments=qual, as_of="2025-01-01")
    assert d["qual_gci"] == 91.0
    assert d["composite_basis"] == "quant_and_qual"
    assert d["composite_exact"].startswith("89.1725")  # 0.8 × 88.7157 + 0.2 × 91
    assert d["composite_gci"] == 89.2


def test_qual_branch_ranges_and_exclusions():
    from app.services import commitments

    comps = [{"weight": 2, "fulfilled": True}, {"weight": 1, "fulfilled": None}, {"weight": 1, "fulfilled": False}]
    rows = [
        _c("partially_delivered", proof={"components": comps}),
        _c("withdrawn_with_reason"),
        _c("superseded"),
        _c("delivered", condition_state="not_activated"),
        _c("delivered", due="FY30"),
        {**_c("delivered"), "review_status": "unreviewed"},
    ]
    q = g.core_qual_branch(rows, as_of="2025-01-01")
    assert q["qual_gci"] is None and (q["qual_low"], q["qual_high"]) == (50.0, 75.0)
    assert q["reason_counts"] == {"WITHDRAWN": 1, "SUPERSEDED": 1, "CONDITION_NOT_ACTIVATED": 1, "OUTCOME_NOT_DUE": 1}
    assert commitments.commitment_fulfilment(_c("delivered_late"))["low"] == 0.0  # §10.3: by the deadline
    assert commitments.qual_family(_c("open"), as_of="2025-01-01")["reason"] == "OUTCOME_UNRESOLVED"
    d = g.compute_core_detail(_company_rows(), commitments=[_c("delivered"), _c("open", type="capex")], as_of="2025-01-01")
    assert d["composite_gci"] is None and d["composite_low"] < d["composite_high"]
    with pytest.raises(ValueError):
        g.compute_core_detail([], commitments=[_c("delivered")])


def test_qual_only_company_is_labelled():
    d = g.compute_core_detail([], commitments=[_c("delivered")], as_of="2025-01-01")
    assert d["quant_gci"] is None and d["composite_basis"] == "qual_only" and d["composite_gci"] == 100.0


def test_core_is_deterministic_and_never_published_while_unapproved():
    rows = get_outcomes("infy")
    a, b = g.compute_core_detail(rows), g.compute_core_detail(list(reversed(rows)))
    assert a["input_digest"] == b["input_digest"]
    assert a["quant_gci_exact"] == b["quant_gci_exact"]
    assert a["ruleset"] == g.CORE_RULESET_LOCKED and a["algorithm_id"] == g.CORE_ALGORITHM_ID
    assert g.CORE_ENGINE_APPROVED is False
    assert a["publication_status"] == "SHADOW"
    assert g.scorer_version("core") == "v4"  # Core can never be selected as the published scorer


def test_new_outcome_fields_round_trip():
    o = outcome_from_dict({"period": "FY24", "metric": "revenue_cr", "guided_value": 0, "bound": "floor",
                           "zero_reference": 50, "prior_value": 3, "condition_state": "satisfied",
                           "restated_actual_value": 99})
    assert (o.bound, o.zero_reference, o.prior_value, o.condition_state, o.restated_actual_value) == (
        "floor", 50.0, 3.0, "satisfied", 99.0)


# --- markets ------------------------------------------------------------------


def test_every_market_has_a_core_profile():
    assert set(GCI_CORE_PROFILES) == {m["id"] for m in MARKETS}
    for mid in GCI_CORE_PROFILES:
        p = gci_core_profile(mid)
        assert p["core_status"] in ("publish", "shadow", "diagnostic_only")
        assert p["reporting_cadence"] in ("Q", "H")
        assert p["modifications"] and p["practice"]


def test_market_status_follows_data_availability():
    assert core_publication_status("IN") == ("PUBLISHABLE", None)
    assert core_publication_status("US") == ("SHADOW", "UNAPPROVED_ENGINE")
    assert core_publication_status("JP") == ("NOT_ELIGIBLE", "REGIME_ADAPTER_PENDING")  # J-GAAP default
    assert core_publication_status("JP", "IFRS") == ("SHADOW", "UNAPPROVED_ENGINE")
    assert core_publication_status("CN") == ("NOT_ELIGIBLE", "REGIME_ADAPTER_PENDING")
    assert core_publication_status("HK") == ("NOT_ELIGIBLE", "MARKET_DIAGNOSTIC_ONLY")
    assert [p for p, s in GCI_CORE_PROFILES.items() if s["core_status"] == "publish"] == ["IN"]


def test_company_market_inference():
    assert company_market_id({"id": "infy"}) == "IN"
    assert company_market_id({"id": "us_aapl"}) == "US"
    assert company_market_id({"id": "x", "market_id": "au"}) == "AU"


def test_half_year_market_uses_half_year_period_end():
    from app.services.disclosures import period_end

    assert period_end("H1 FY2025", "AU", "0630") == "2024-12-31"
    assert period_end("H2 FY2025", "GB", "1231") == "2025-12-31"
    assert period_end("H1 FY25", "IN") == "2024-09-30"
    assert g.core_cadence("H1 FY2025") == "H"


# --- delivery ruleset: locked measurement without frequency, lead time or Qual -----

DELIVERY = g.CORE_RULESET_DELIVERY


def test_default_ruleset_is_locked_and_delivery_has_its_own_id():
    assert g.CORE_DEFAULT_RULESET == g.CORE_RULESET_LOCKED
    assert g.core_algorithm_id() == "gci_core_v2_4"
    assert g.core_algorithm_id(DELIVERY) == "gci_core_delivery_v1"
    for rs in g.CORE_RULESETS:
        assert g.core_ruleset_for(g.core_algorithm_id(rs)) == rs
    with pytest.raises(ValueError):
        g.core_ruleset_for("gci_scoring_v4")


def test_delivery_matches_locked_on_a_single_amount_vintage():
    for metric, low, high, actual in (("revenue_cr", 100, 110, 100), ("ebitda_margin_pct", 5, 6, 5)):
        assert _score(metric, low, high, actual, ruleset=DELIVERY) == _score(metric, low, high, actual)


def test_delivery_reads_low_base_growth_against_a_points_floor():
    # Guided 1–3%, reported 4.2%: locked v2.4 scores a 1.2-point beat as a total miss.
    assert _score("revenue_growth_cc_pct", 1, 3, 4.2) == 0.0
    assert _score("revenue_growth_cc_pct", 1, 3, 4.2, ruleset=DELIVERY) == 78.0
    # A high base is above the floor, so the reading is unchanged.
    assert _score("revenue_growth_pct", 20, 24, 25, ruleset=DELIVERY) == _score("revenue_growth_pct", 20, 24, 25)


def test_delivery_drops_frequency_penalty_and_lead_factor():
    row = _row(metric="revenue_cr", guided_low=100, guided_high=110, actual_value=105,
               guidance_as_of="2024-03-15",
               revisions=({"as_of": "2023-06-01", "guided_low": 98, "guided_high": 108},
                          {"as_of": "2023-09-01", "guided_low": 102, "guided_high": 112}))
    row = replace(row, guidance_as_of="2023-04-15")
    locked = g.core_family_detail(row, **FY24)
    delivery = g.core_family_detail(row, ruleset=DELIVERY, **FY24)
    assert locked["frequency_penalty"] > 0 and locked["lead_time_factor"] == 1.1
    assert delivery["frequency_penalty"] == 0 and delivery["lead_time_factor"] is None
    assert delivery["revisions_counted"] == locked["revisions_counted"] == 2
    assert delivery["delivery_score"] == locked["delivery_score"]
    assert delivery["score"] == delivery["delivery_score"]


def test_delivery_scores_undated_guidance_that_locked_cannot():
    row = _row(guided_low=100, guided_high=110, actual_value=100, guidance_as_of=None)
    assert g.core_family_detail(row, **FY24)["reason_code"] == "ISSUANCE_TIME_UNKNOWN"
    assert g.core_family_detail(row, ruleset=DELIVERY, **FY24)["score"] == 95.2381


def test_delivery_headline_is_quant_only():
    rows = [_row(guided_low=100, guided_high=110, actual_value=100)]
    commitments = [{"id": "c1", "review_status": "accepted", "type": "capex", "due_period": "FY23",
                    "state": "missed", "subject": "x", "outcome": "y"}]
    locked = g.compute_core_detail(rows, commitments=commitments, as_of="2024-06-01")
    delivery = g.compute_core_detail(rows, commitments=commitments, as_of="2024-06-01", ruleset=DELIVERY)
    assert locked["composite_basis"] == "quant_and_qual"
    assert delivery["composite_basis"] == "quant_only" and delivery["headline"] == "quant"
    assert delivery["composite_gci"] == delivery["quant_gci"] == 95.2
    assert delivery["qual_low"] == locked["qual_low"]
    assert {e["companion"] for e in delivery["excluded_elements"]} == {
        "revision_discipline", "guidance_visibility", "commitment_delivery", "growth_accuracy_pp",
    }


# --- ids, issuance, idempotency, conflicts, basis switches, thin history ----------


def test_family_and_vintage_ids_are_stable_and_basis_aware():
    row = _row(guided_low=100, guided_high=110, actual_value=100,
               revisions=({"as_of": "2023-09-01", "guided_low": 102, "guided_high": 112},))
    a = g.core_family_detail(row, company_id="acme", **FY24)
    b = g.core_family_detail(row, company_id="acme", **FY24)
    assert a["family_id"] == b["family_id"] and a["family_id"].startswith("fam_")
    assert [v["vintage_id"] for v in a["vintages"]] == [v["vintage_id"] for v in b["vintages"]]
    assert len({v["vintage_id"] for v in a["vintages"]}) == 2
    other = g.core_family_detail(replace(row, reporting_basis="reported"), company_id="acme", **FY24)
    assert other["family_id"] != a["family_id"]
    assert g.core_family_detail(row, company_id="other", **FY24)["family_id"] != a["family_id"]


def test_rerun_duplicates_do_not_add_revisions():
    rev = {"as_of": "2023-09-01", "guided_low": 102, "guided_high": 112}
    back = {"as_of": "2023-10-01", "guided_low": 100, "guided_high": 110}
    once = _row(guided_low=100, guided_high=110, actual_value=105, revisions=(rev, back))
    twice = replace(once, revisions=(rev, back, rev, back))
    assert g.core_family_detail(twice, **FY24)["revisions_counted"] == g.core_family_detail(once, **FY24)["revisions_counted"] == 2
    assert g.core_family_detail(twice, **FY24)["score"] == g.core_family_detail(once, **FY24)["score"]


def test_same_day_conflicting_revision_is_flagged_not_counted():
    row = _row(guided_low=100, guided_high=110, actual_value=105,
               revisions=({"as_of": "2023-09-01", "guided_low": 102, "guided_high": 112},
                          {"as_of": "2023-09-01", "guided_low": 90, "guided_high": 95}))
    d = g.core_family_detail(row, **FY24)
    assert "SAME_DAY_CONFLICT" in d["flags"]
    assert d["revisions_counted"] == 1
    assert d["vintages"][1]["same_day_conflicts"] == 1


def test_stored_public_availability_sets_vintage_time():
    row = _row(guided_low=100, guided_high=110, actual_value=100, guidance_source_url="https://x/a.pdf",
               guidance_as_of="2023-04-15")
    d = g.core_family_detail(row, issuance={"https://x/a.pdf": "2023-04-20T10:00:00"}, **FY24)
    v = d["vintages"][0]
    assert v["as_of"] == "2023-04-20" and v["stated_as_of"] == "2023-04-15"
    assert v["time_basis"] == "public_available_at"
    assert d["lead_time_days"] == 346


def test_basis_switch_and_thin_history_are_flagged_without_moving_the_level():
    a = _row(period="FY23", guided_low=100, guided_high=110, actual_value=100, reporting_basis="reported",
             guidance_as_of="2022-04-15", as_of="2023-04-20")
    b = _row(period="FY24", guided_low=100, guided_high=110, actual_value=100, reporting_basis="constant_currency")
    d = g.compute_core_detail([a, b])
    fy24 = next(f for f in d["families"] if f["period"] == "FY24")
    assert "BASIS_SWITCH" in fy24["flags"] and d["reason_counts"]["BASIS_SWITCH"] == 1
    assert fy24["score"] == g.compute_core_detail([b])["families"][0]["score"]
    assert d["company_flags"] == []
    thin = g.compute_core_detail([b])
    assert thin["company_flags"] == ["THIN_HISTORY"]


def test_coverage_units_uncertainty_and_record_states():
    scored = _row(metric="capex_guidance", guided_low=100, guided_high=110, actual_value=100)
    open_row = _row(metric="capex_guidance", period="FY25", guided_low=100, guided_high=110)
    d = g.compute_core_detail([scored, open_row])
    assert d["coverage"]["families_total"] == 2 and d["coverage"]["families_computable"] == 1
    assert d["coverage"]["computable_share"] == 1.0
    assert d["uncertainty"]["width"] == 0.0
    fam = next(f for f in d["families"] if f["period"] == "FY24")
    assert fam["unit"] == "inr_cr" and fam["currency"] == "INR"
    assert fam["record_state"] == "SCORE_COMPUTED"
    assert next(f for f in d["families"] if f["period"] == "FY25")["record_state"] == "REVIEWER_ACCEPTED"
    from app.services.score_policy import RECORD_STATES, core_record_state

    assert core_record_state("UNREVIEWED", "NOT_COMPUTABLE", published=False) == "EXTRACTED"
    assert core_record_state(None, "COMPUTED", published=True) == "PUBLISHED"
    assert RECORD_STATES[-1] == "PUBLISHED"


def test_missing_actual_past_results_deadline_is_unavailable_not_due():
    def reason(period: str, as_of: str) -> str:
        return g.compute_core_detail([_row(period=period)], as_of=as_of)["families"][0]["reason_code"]

    assert reason("FY24", "2024-05-30") == "OUTCOME_NOT_DUE"
    assert reason("FY24", "2024-06-01") == "ACTUAL_UNAVAILABLE"
    assert reason("Q1 FY25", "2024-08-14") == "OUTCOME_NOT_DUE"
    assert reason("Q1 FY25", "2024-08-15") == "ACTUAL_UNAVAILABLE"
    assert g.compute_core_detail([_row()])["families"][0]["reason_code"] == "OUTCOME_NOT_DUE"


R2 = g.CORE_RULESET_R2
GROWTH, LEVEL = "revenue_growth_pct", "operating_margin_pct"


def _r2_score(metric, low, high, actual, bound=None):
    return float(g.core_score_from_z(g.r2_vintage_terms(metric, low, high, actual, bound=bound)["z"]))


def test_r2_frequency_uses_weighted_count_on_the_existing_curve():
    assert g.core_frequency_penalty(Decimal("0.9"), "FY", R2) == Decimal("0.18")
    assert g.core_frequency_penalty(Decimal("3.0"), "FY", R2) == Decimal("0.35")
    assert g.core_frequency_penalty(Decimal("0"), "FY", R2) == 0
    for n in range(0, 8):
        assert g.core_frequency_penalty(n, "FY", R2) == g.core_frequency_penalty(n, "FY")


def test_r2_revision_kinds_are_economic():
    d = Decimal
    kind = lambda m, a, b, bound=None: g.r2_revision_kind(m, (d(a[0]), d(a[1])), (d(b[0]), d(b[1])), bound)  # noqa: E731
    assert kind(GROWTH, (4, 6), (5, 7)) == "raise"
    assert kind(GROWTH, (4, 6), (3, 5)) == "walk_down"
    assert kind(GROWTH, (4, 6), (4.5, 5.5)) == "narrower"
    assert kind(GROWTH, (4, 6), (3, 7)) == "wider"
    assert kind(GROWTH, (4, 6), (3.5, 7)) == "mixed"
    assert kind("wc_days", (60, 70), (65, 75)) == "walk_down"
    assert kind("wc_days", (60, 70), (55, 65)) == "raise"
    assert kind("wc_days", (60, 70), (50, 72)) == "mixed"
    assert kind("wc_days", (60, 70), (63, 72)) == "walk_down"
    assert kind("capex_guidance", (100, 110), (120, 130)) == "undirected"
    assert kind("capex_guidance", (100, 100), (120, 120), "ceiling") == "walk_down"
    assert kind("capex_guidance", (100, 100), (120, 120), "floor") == "raise"


def test_r2_range_and_growth_fixtures_as_written(monkeypatch):
    monkeypatch.setattr(g, "R2_SCALE_INCLUDES_MIDPOINT", False)
    monkeypatch.setattr(g, "R2_MET_BOUND_SCORES_FULL", False)
    assert _r2_score(LEVEL, 0, 3, 3.1) == pytest.approx(96.6667, abs=1e-3)
    assert _r2_score(LEVEL, 0, 10, 7) == 100
    assert _r2_score(LEVEL, 4, 6, 6.5) == pytest.approx(75)
    assert _r2_score(LEVEL, 4, 6, 4.1) == 100
    assert _r2_score(LEVEL, 0, 10, 9.9) == 100
    assert _r2_score(GROWTH, 1, 1, 4.2) == pytest.approx(36)
    assert _r2_score(GROWTH, 1, 3, 4.2) == pytest.approx(76)
    assert _r2_score(GROWTH, 15, 15, 18) == pytest.approx(80)
    assert _r2_score(GROWTH, 6, 10, 9) == 100
    assert _r2_score(GROWTH, 10, 10, 15, bound="floor") == pytest.approx(50)
    assert _r2_score(LEVEL, 21.5, 22.5, 24.5) == 0


def test_r2_amendments_scale_and_met_bounds():
    assert _r2_score(LEVEL, 21.5, 22.5, 24.5) == pytest.approx(90.9091, abs=1e-3)
    assert _r2_score(GROWTH, 12, 14, 19.7) == pytest.approx(56.1538, abs=1e-3)
    assert _r2_score(LEVEL, 0, 3, 3.1) == pytest.approx(96.6667, abs=1e-3)
    assert _r2_score(GROWTH, 1, 3, 4.2) == pytest.approx(76)
    assert _r2_score(GROWTH, 10, 10, 15, bound="floor") == 100
    assert _r2_score(GROWTH, 10, 10, 8, bound="floor") == pytest.approx(80)
    assert _r2_score("wc_days", 60, 60, 55, bound="ceiling") == 100
    # A point is a zero-width range: same miss, same scale.
    assert _r2_score(GROWTH, 41, 41, 45) == pytest.approx(100 * (1 - 4 / 41), abs=1e-3)
    assert _r2_score(GROWTH, 40, 42, 45) == pytest.approx(100 * (1 - 3 / 41), abs=1e-3)


def test_r2_lead_time_is_continuous_and_normalised():
    f = lambda l, h: float(g.r2_lead_time_factor(l, h))  # noqa: E731
    assert (f(0, 90), f(45, 90), f(90, 90)) == pytest.approx((0.80, 0.95, 1.10))
    assert (f(0, 365), f(365, 365), f(400, 365)) == pytest.approx((0.80, 1.10, 1.10))
    assert f(182, 365) == pytest.approx(0.9496, abs=1e-4)
    assert f(91, 365) - f(90, 365) < 0.001
    lead = lambda as_of: g.compute_core_detail(  # noqa: E731
        [_row(guided_low=100, guided_high=110, actual_value=105, guidance_as_of=as_of)], ruleset=R2)["families"][0]
    first_day, day_before, last_day = lead("2023-04-01"), lead("2023-03-31"), lead("2024-03-31")
    assert (first_day["lead_time"]["l_days"], first_day["lead_time"]["h_days"]) == (366, 366)
    assert first_day["lead_time"]["factor"] == 1.1 and "PRE_PERIOD_GUIDANCE" not in first_day["flags"]
    assert day_before["lead_time"]["l_days"] == 367 and "PRE_PERIOD_GUIDANCE" in day_before["flags"]
    assert last_day["lead_time"]["l_days"] == 1 and float(last_day["lead_time"]["factor"]) == pytest.approx(0.8008, abs=1e-4)


def test_r2_headline_is_quant_until_qual_coverage():
    rule = g.r2_headline_rule
    assert rule({"qual_commitment_count": 0, "expected_family_count": 0, "unresolved": 0}) == "QUANT_DOMINANT"
    assert rule({"qual_commitment_count": 2, "expected_family_count": 2, "unresolved": 0}) == "QUANT_DOMINANT"
    assert rule({"qual_commitment_count": 3, "expected_family_count": 8, "unresolved": 0}) == "QUANT_DOMINANT"
    assert rule({"qual_commitment_count": 3, "expected_family_count": 6, "unresolved": 0}) == "COMPOSITE_PUBLISHED"
    d = g.compute_core_detail([_row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=5)],
                              commitments=[_c("delivered")], as_of="2025-01-01", ruleset=R2)
    assert d["headline_rule"] == "QUANT_DOMINANT" and d["headline_gci"] == d["quant_gci"]
    assert d["composite_gci"] is not None and d["qual"]["coverage"]["qual_commitment_count"] == 1
    thin = g.compute_core_detail([_row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=5)],
                                 commitments=[_c("open")], as_of="2025-01-01", ruleset=R2)
    assert thin["composite_gci"] is None and thin["composite_low"] != thin["composite_high"]
    assert thin["headline_gci"] == thin["quant_gci"] and thin["headline_exact"] == thin["quant_gci_exact"]
    assert thin["uncertainty"]["width"] == 0 and thin["uncertainty"]["source"] is None
    assert thin["qual"]["families"][0]["evidence_status"] == "UNAVAILABLE"
    assert thin["qual"]["coverage"] == {"qual_commitment_count": 0, "expected_family_count": 1,
                                        "coverage_ratio": 0.0, "unresolved": 1, "pending": 0}
    locked = g.compute_core_detail([_row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=5)],
                                   commitments=[_c("open")], as_of="2025-01-01")
    assert locked["headline_gci"] is None and locked["uncertainty"]["width"] > 0


def test_r2_more_evidence_never_removes_the_headline():
    quant = [_row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=5)]
    run = lambda cs: g.compute_core_detail(quant, commitments=cs, as_of="2025-01-01", ruleset=R2)  # noqa: E731
    done = [_c("delivered", type=t) for t in ("capacity", "capex", "launch")]
    full = run(done)
    assert full["headline_rule"] == "COMPOSITE_PUBLISHED" and full["headline_gci"] == full["composite_gci"] == 100.0
    partial = run(done + [_c("open", type="order_book")])
    assert partial["qual"]["coverage"]["coverage_ratio"] == 0.75 and partial["qual"]["coverage"]["unresolved"] == 1
    assert partial["composite_gci"] is None and partial["composite_low"] < partial["composite_high"]
    assert partial["headline_rule"] == "QUANT_DOMINANT" and partial["headline_gci"] == partial["quant_gci"] == 100.0
    two = run(done[:2])
    assert two["headline_gci"] is not None
    rule = g.r2_headline_rule
    assert rule({"qual_commitment_count": 999, "expected_family_count": 1999, "unresolved": 0}) == "QUANT_DOMINANT"
    assert rule({"qual_commitment_count": 3, "expected_family_count": 3, "unresolved": 0}) == "COMPOSITE_PUBLISHED"
    assert rule({"qual_commitment_count": 3, "expected_family_count": 4, "unresolved": 1}) == "QUANT_DOMINANT"


def test_core_as_of_sees_only_what_was_public_then():
    row = _row(guided_low=100, guided_high=110, actual_value=105, guidance_as_of="2023-04-15", as_of="2024-04-20",
               revisions=[{"as_of": "2023-10-15", "guided_low": 90, "guided_high": 95, "source_url": "u"}])
    for rs in g.CORE_RULESETS:
        before_guidance = g.compute_core_detail([row], as_of="2023-01-01", ruleset=rs)["families"][0]
        assert (before_guidance["reason_code"], before_guidance["score"]) == ("FUTURE_SOURCE", None)
        mid_year = g.compute_core_detail([row], as_of="2023-08-01", ruleset=rs)["families"][0]
        assert (mid_year["reason_code"], mid_year["actual_value"]) == ("OUTCOME_NOT_DUE", None)
        deadline_passed = g.compute_core_detail([row], as_of="2024-06-15", ruleset=rs)["families"][0]
        assert deadline_passed["calculation_status"] == "COMPUTED"
        late = _row(guided_low=100, guided_high=110, actual_value=105, as_of="2024-07-01")
        assert g.compute_core_detail([late], as_of="2024-06-15", ruleset=rs)["families"][0]["reason_code"] == "ACTUAL_UNAVAILABLE"
    revised = g.compute_core_detail([row], as_of="2024-06-15", ruleset=R2)["families"][0]
    assert [v["eligible"] for v in revised["vintages"]] == [True, True]
    pit = g.compute_core_detail([_row(guided_low=100, guided_high=110, actual_value=105, as_of="2024-04-20",
                                      revisions=[{"as_of": "2024-05-01", "guided_low": 90, "guided_high": 95, "source_url": "u"}])],
                                as_of="2024-04-25", ruleset=R2)["families"][0]
    assert [v["reason_code"] for v in pit["vintages"]] == [None, "FUTURE_SOURCE"]


def test_core_digest_names_every_input_that_moves_the_level(monkeypatch):
    rows = [_row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=8),
            _row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=8, scope="segment")]
    d = lambda **kw: g.compute_core_detail(rows, ruleset=R2, **kw)["input_digest"]  # noqa: E731
    base = d()
    assert g.compute_core_detail(list(reversed(rows)), ruleset=R2)["input_digest"] == base
    assert d(fy_end_mmdd="12-31") != base and d(regime="IFRS") != base and d(audit_flags=["x"]) != base
    monkeypatch.setattr(g, "R2_SCALE_INCLUDES_MIDPOINT", False)
    assert d() != base

def test_r2_regression_properties():
    rng = random.Random(24)
    for _ in range(400):
        metric = rng.choice((GROWTH, LEVEL))
        lo = round(rng.uniform(-20, 30), 2)
        hi = round(lo + rng.choice((0, rng.uniform(0, 10))), 2)
        a = round(rng.uniform(-40, 50), 2)
        t = g.r2_vintage_terms(metric, lo, hi, a)
        if t["z"] is None:
            assert lo == hi == 0 and t["reason_code"]
            continue
        s = float(g.core_score_from_z(t["z"]))
        assert 0 <= s <= 100
        if lo <= a <= hi:
            assert s == 100
        further = a + (1 if a > hi else -1)
        if not lo <= a <= hi:
            assert g.r2_vintage_terms(metric, lo, hi, further)["z"] >= t["z"]
        assert t["effective_scale"] == g.r2_vintage_terms(metric, lo, hi, a + 7)["effective_scale"]
        if metric == LEVEL and (lo, hi) != (0, 0):
            assert float(g.r2_vintage_terms(metric, lo * 10, hi * 10, a * 10)["z"]) == pytest.approx(float(t["z"]))
    assert g.r2_vintage_terms(LEVEL, -2, 8, 5)["z"] == 0
    for _ in range(400):
        metric, side = rng.choice((GROWTH, LEVEL)), rng.choice(("floor", "ceiling"))
        b = round(rng.uniform(-20, 30), 2)
        a = round(rng.uniform(-40, 50), 2)
        t = g.r2_vintage_terms(metric, b, b, a, bound=side)
        if t["z"] is None:
            assert b == 0 and t["reason_code"]
            continue
        met = a >= b if side == "floor" else a <= b
        assert t["target_met"] is met and (t["z"] == 0) is met
        assert t["side"] == (None if met else "under" if side == "floor" else "over")
        worse = a - 1 if side == "floor" else a + 1
        assert g.r2_vintage_terms(metric, b, b, worse, bound=side)["z"] >= t["z"]
        if metric == LEVEL and b != 0:
            scaled = g.r2_vintage_terms(metric, b * 10, b * 10, a * 10, bound=side)["z"]
            assert float(scaled) == pytest.approx(float(t["z"]))


def test_r2_family_detail_and_determinism():
    row = _row(metric=GROWTH, guided_low=4, guided_high=6, actual_value=6.5, guidance_as_of="2023-04-15",
               revisions=[{"as_of": "2023-07-15", "guided_low": 5, "guided_high": 7, "source_url": "u"},
                          {"as_of": "2023-10-15", "guided_low": 4, "guided_high": 6, "source_url": "u"}])
    d = g.compute_core_detail([row], ruleset=R2)
    fam = d["families"][0]
    assert fam["revisions_counted"] == 2 and fam["revisions_weighted"] == "1.3"
    assert [v.get("revision_kind") for v in fam["vintages"]] == [None, "raise", "walk_down"]
    assert fam["lead_time"]["interpolation_method"] == "LINEAR_NORMALISED" and fam["lead_time"]["h_days"] == 366
    assert d["algorithm_id"] == g.CORE_R2_ALGORITHM_ID and d["constants"]["r2"]["growth_floor_pp"] == "5"
    assert g.core_ruleset_for(g.CORE_R2_ALGORITHM_ID) == R2
    again = g.compute_core_detail([row], ruleset=R2)
    assert d["input_digest"] == again["input_digest"] and d["composite_exact"] == again["composite_exact"]
    assert g.compute_core_detail([row])["composite_gci"] != d["composite_gci"]


def test_new_reason_codes_are_registered():
    for code in ("SAME_DAY_CONFLICT", "BASIS_SWITCH", "THIN_HISTORY"):
        assert code in CORE_REASON_CODES
