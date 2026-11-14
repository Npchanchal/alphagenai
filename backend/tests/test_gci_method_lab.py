"""GCI method lab: configurable research calculator beside the published and shadow methods."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data.seed import get_outcomes, reset_data
from app.main import app
from app.services import gci_scoring as g
from app.services import score_ledger

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
RETAIL = {"X-API-Key": "intellens-retail"}
GROWTH = "revenue_growth_cc_pct"


def setup_function():
    reset_data()


def _defaults(code: str):
    return g.lab_resolve({"method": code})["params"]


def _all_closed():
    return [o for cid in ("infy", "cipla") for o in get_outcomes(cid) if o.actual_value is not None]


# --- Defaults reproduce the engine ------------------------------------------------


def test_classic_defaults_match_the_published_row_score():
    p = _defaults("classic")
    for o in g.lab_closed_rows(_all_closed()):
        low, high = g._band(o)
        assert g.lab_row_score("classic", p, o.metric, low, high, o.actual_value)["score"] == pytest.approx(
            g.outcome_score_v4(o), abs=0.01
        )


@pytest.mark.parametrize(
    "code,ruleset",
    [("core", g.CORE_RULESET_LOCKED), ("delivery", g.CORE_RULESET_DELIVERY), ("draft", g.CORE_RULESET_PROPOSAL)],
)
def test_core_family_defaults_match_the_engine_vintage(code, ruleset):
    p = _defaults(code)
    for o in _all_closed():
        low, high = g._band(o)
        z, _ = g.core_vintage_z(o.metric, low, high, o.actual_value, bound=o.bound, ruleset=ruleset)
        got = g.lab_row_score(code, p, o.metric, low, high, o.actual_value, bound=o.bound)["score"]
        assert got == (None if z is None else pytest.approx(float(g.core_score_from_z(z)), abs=0.01))


def test_range_defaults_match_r2_with_amendments():
    p = _defaults("range")
    for o in _all_closed():
        low, high = g._band(o)
        z = g.r2_vintage_terms(o.metric, low, high, o.actual_value, bound=o.bound)["z"]
        got = g.lab_row_score("range", p, o.metric, low, high, o.actual_value, bound=o.bound)["score"]
        assert got == pytest.approx(float(g.core_score_from_z(z)), abs=0.01)


@pytest.mark.parametrize("flags", [(), ("definition_shift",), ("guidance_withdrawal", "restatement")])
def test_classic_default_level_is_the_published_level(flags):
    c = g.lab_resolve({"method": "classic"})
    for cid in ("infy", "cipla"):
        rows = get_outcomes(cid)
        published = g.compute_gci_v3_detail(rows, version="v4", audit_flags=flags).gci
        level = g.lab_run(rows, [c], audit_flags=flags)["levels"][c["id"]]
        assert level["level"] == published
        assert level["audit_deduction"] == g.audit_deduction(rows, flags)


def test_audit_deduction_is_classic_only_by_default():
    rows = get_outcomes("infy")
    core = g.lab_resolve({"method": "core"})
    plain = g.lab_run(rows, [core])["levels"][core["id"]]["level"]
    assert g.lab_run(rows, [core], audit_flags=("restatement",))["levels"][core["id"]]["level"] == plain


def test_overrides_leave_engine_constants_alone():
    before = g.r2_vintage_terms(GROWTH, 0, 3, 3.1)["z"]
    g.lab_row_score("range", {**_defaults("range"), "growth_floor_pp": 0.0}, GROWTH, 0, 3, 3.1)
    assert g.r2_vintage_terms(GROWTH, 0, 3, 3.1)["z"] == before
    assert g.R2_GROWTH_FLOOR_PP == g.Decimal("5")


# --- Configuration ------------------------------------------------------------------


def test_preset_then_explicit_values_then_clamp():
    c = g.lab_resolve({"method": "classic", "preset": "v3", "params": {"gamma_miss": 99}})
    assert c["params"]["beat_floor"] == 0.0
    assert c["params"]["gamma_miss"] == 3.0  # clamped to the range maximum
    assert c["params_changed"] == ["beat_floor", "gamma_miss"]
    assert c["id"] == "classic:v3"
    assert c["rollup"]["weight_by_confidence"] is True


@pytest.mark.parametrize(
    "bad",
    [
        {"method": "nope"},
        {"method": "classic", "preset": "nope"},
        {"method": "classic", "params": {"nope": 1}},
        {"method": "core", "params": {"reference": "nope"}},
        {"method": "classic", "rollup": {"nope": 1}},
        {"method": "classic", "params": {"beat_floor": "x"}},
    ],
)
def test_invalid_configuration_is_refused(bad):
    with pytest.raises(ValueError):
        g.lab_resolve(bad)


def test_every_method_has_ranges_and_a_first_preset_that_resolves():
    for m in g.LAB_METHODS:
        for spec in m["params"]:
            if spec["kind"] == "number":
                assert spec["min"] <= spec["default"] <= spec["max"]
        for preset in m["presets"]:
            g.lab_resolve({"method": m["code"], "preset": preset["id"]})
    for view in g.LAB_ACTOR_VIEWS:
        for code, preset in view["comparisons"]:
            g.lab_resolve({"method": code, "preset": preset})


def test_recency_and_vintage_settings_move_the_level():
    rows = get_outcomes("infy")
    flat = g.lab_resolve({"method": "range_p", "rollup": {"half_life_periods": 0}})
    final = g.lab_resolve({"id": "final", "method": "range_p", "rollup": {"vintage": "final"}})
    run = g.lab_run(rows, [flat, final])
    fy22 = next(r for r in run["rows"] if r["period"] == "FY22" and r["metric"] == GROWTH)
    assert fy22["bands"]["final"] != fy22["bands"][flat["id"]]
    assert fy22["scores"]["final"] > fy22["scores"][flat["id"]]


# --- Behaviour checks reproduce the 12 Nov scan -----------------------------------


def test_behaviour_checks_match_the_algorithm_scan():
    diffusion = g.lab_behaviour(g.lab_resolve({"method": "diffusion"}))
    assert diffusion["gain_from_guiding_low"] == pytest.approx(49.4, abs=0.2)
    assert diffusion["alternating_record"] == diffusion["steady_record"] == 50.0
    assert diffusion["low_growth_beat"] == 100.0
    range_p = g.lab_behaviour(g.lab_resolve({"method": "range_p"}))
    assert range_p["gain_from_guiding_low"] == 0.0
    assert range_p["best_half_width_pp"] == 2.0
    assert range_p["one_pp_miss_at_2"] == range_p["one_pp_miss_at_20"] == 87.5
    core = g.lab_behaviour(g.lab_resolve({"method": "core"}))
    assert (core["one_pp_miss_at_2"], core["one_pp_miss_at_20"]) == (0.0, 90.0)
    classic = g.lab_behaviour(g.lab_resolve({"method": "classic"}))
    assert classic["gain_from_guiding_low"] == pytest.approx(0.4, abs=0.1)


def test_diffusion_direction_and_tags():
    bias = g.lab_resolve({"method": "diffusion", "preset": "guidance_bias"})["params"]
    owner = _defaults("diffusion")
    assert g.lab_row_score("diffusion", owner, "wc_days", 40, 50, 55)["score"] > 50
    assert g.lab_row_score("diffusion", bias, "wc_days", 40, 50, 55)["score"] < 50
    assert g.lab_tag("wc_days", 40, 50, 55) == "miss"
    assert g.lab_tag(GROWTH, 4, 6, 7) == "beat"
    assert g.lab_tag(GROWTH, 4, 6, 5) == "in_line"


# --- API ------------------------------------------------------------------------------


def test_lab_is_seat_only():
    assert client.get("/api/v1/index/lab").status_code in (401, 403)
    assert client.get("/api/v1/index/lab", headers=RETAIL).status_code in (401, 403)
    body = client.get("/api/v1/index/lab", headers=DEMO).json()
    assert body["base_method"] == "classic"
    assert {m["code"] for m in body["methods"]} >= {"classic", "core", "range", "range_p", "diffusion", "hit_rate"}
    payload = {"comparisons": [{"method": "classic"}]}
    assert client.post("/api/v1/index/lab/run", json=payload).status_code in (401, 403)


def test_lab_run_compares_and_writes_nothing():
    ledger_before = len(score_ledger.read_all())
    res = client.post(
        "/api/v1/index/lab/run",
        headers=DEMO,
        json={
            "company_ids": ["infy"],
            "comparisons": [
                {"method": "classic"},
                {"method": "range_p", "params": {"points_per_unit": 20}},
                {"method": "diffusion", "preset": "guidance_bias"},
            ],
            "hypothetical_rows": [{"metric": GROWTH, "low": 0, "high": 3, "actual": 3.1}],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "research"
    infy = body["companies"][0]
    levels = infy["levels"]
    assert levels["classic:published"]["level"] == levels["classic:published"]["engine_level"]
    assert levels["range_p:scan"]["engine_level"] is None
    assert body["comparisons"][1]["params"]["points_per_unit"] == 20.0
    assert body["hypothetical"]["rows"][0]["scores"]["diffusion:guidance_bias"] is not None
    assert set(body["behaviour"]) == {c["id"] for c in body["comparisons"]}
    assert len(score_ledger.read_all()) == ledger_before


def test_lab_run_refuses_bad_input():
    bad_method = {"comparisons": [{"method": "nope"}]}
    assert client.post("/api/v1/index/lab/run", headers=DEMO, json=bad_method).status_code == 422
    dup = {"comparisons": [{"method": "classic"}, {"method": "classic"}]}
    assert client.post("/api/v1/index/lab/run", headers=DEMO, json=dup).status_code == 422
    unknown = {"company_ids": ["nope"], "comparisons": [{"method": "classic"}]}
    assert client.post("/api/v1/index/lab/run", headers=DEMO, json=unknown).status_code in (403, 404)
    many = {"comparisons": [{"id": str(i), "method": "classic"} for i in range(9)]}
    assert client.post("/api/v1/index/lab/run", headers=DEMO, json=many).status_code == 422
