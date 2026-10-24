"""Reporting-basis control and Holdings look-through.

Infosys FY24 constant-currency revenue stays a miss. Reported INR growth of 4.7%
cannot close that row. A pilot term starts only when an admin sets 30, 45, or 60 days.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.data.hand_labeled import INFY
from app.data.seed import get_data, outcome_from_dict, reset_data, save_data
from app.main import app
from app.services.gci_scoring import (
    GuidanceOutcome,
    OutcomeLabel,
    classify_outcome,
    compute_company_gci,
    final_band_label,
    outcome_score,
)
from dataclasses import replace

client = TestClient(app)
ADMIN = {"X-API-Key": "intellens-admin"}
ONESTOP = {"X-API-Key": "intellens-onestop"}
DEMO = {"X-API-Key": "intellens-demo"}


def setup_function():
    reset_data()


def _fy24():
    row = next(
        r for r in INFY if r["period"] == "FY24" and r["metric"] == "revenue_growth_cc_pct"
    )
    return outcome_from_dict(row)


def test_infosys_fy24_constant_currency_stays_a_miss_and_score_is_unchanged():
    fy24 = _fy24()
    assert fy24.guided_low == 4.0 and fy24.guided_high == 7.0
    assert fy24.actual_value == 1.4
    assert fy24.reporting_basis == "constant_currency"
    assert classify_outcome(fy24) == OutcomeLabel.MISSED
    assert final_band_label(fy24) == OutcomeLabel.MISSED
    bare = replace(
        fy24,
        reporting_basis=None,
        actual_reporting_basis=None,
        unit=None,
        actual_unit=None,
        scope=None,
        actual_scope=None,
    )
    assert outcome_score(fy24) == outcome_score(bare)
    band = fy24.revisions[-1]
    assert band["guided_low"] == 1.5 and band["guided_high"] == 2.0

    live = [outcome_from_dict(r) for r in INFY]
    stripped = [
        replace(
            o,
            reporting_basis=None,
            actual_reporting_basis=None,
            unit=None,
            actual_unit=None,
            scope=None,
            actual_scope=None,
        )
        for o in live
    ]
    assert compute_company_gci(live) == compute_company_gci(stripped)


def test_reported_inr_growth_cannot_close_constant_currency_guidance():
    fy24 = _fy24()
    reported = replace(
        fy24,
        actual_value=4.7,
        actual_reporting_basis="reported",
        quote_span="Reported INR revenue growth was 4.7%",
    )
    assert classify_outcome(reported) == OutcomeLabel.BASIS_MISMATCH
    assert outcome_score(reported) is None


def test_same_basis_margin_lands_inside_the_band():
    margin = GuidanceOutcome(
        period="FY24",
        metric="operating_margin_pct",
        guided_value=21.0,
        guided_low=20.0,
        guided_high=22.0,
        actual_value=20.7,
        guided_text="FY24 operating margin guidance 20–22%; actual 20.7%.",
        reporting_basis="reported",
        actual_reporting_basis="reported",
        unit="pct",
        actual_unit="pct",
    )
    assert classify_outcome(margin) == OutcomeLabel.MET
    assert outcome_score(margin) == 100.0


def test_blank_basis_still_scores_and_a_unit_clash_does_not():
    plain = GuidanceOutcome(
        period="FY24",
        metric="operating_margin_pct",
        guided_value=21.0,
        actual_value=20.7,
        guided_text="band",
        guided_low=20.0,
        guided_high=22.0,
    )
    assert classify_outcome(plain) == OutcomeLabel.MET
    clash = replace(plain, unit="pct", actual_unit="inr_cr")
    assert classify_outcome(clash) == OutcomeLabel.BASIS_MISMATCH
    assert outcome_score(clash) is None


def test_approve_requires_a_term_and_starts_that_clock():
    created = client.post(
        "/api/pilot-request",
        json={"name": "Asha", "email": "asha@desk.test", "firm": "North Desk", "website": ""},
    )
    assert created.status_code == 200, created.text
    request_id = created.json()["request_id"]
    missing = client.patch(
        f"/api/admin/portal/pilot-requests/{request_id}",
        headers=ADMIN,
        json={"action": "approve"},
    )
    assert missing.status_code == 400

    approved = client.patch(
        f"/api/admin/portal/pilot-requests/{request_id}",
        headers=ADMIN,
        json={"action": "approve", "term_days": 30},
    )
    assert approved.status_code == 200, approved.text
    org_id = approved.json()["request"]["org_id"]
    checklist = client.get(f"/api/orgs/{org_id}/pilot-checklist", headers=ADMIN)
    assert checklist.status_code == 200
    body = checklist.json()
    assert body["term_days"] == 30
    assert body["approved"] is True
    assert body["term_open"] is True

    odd = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "Odd Term", "term_days": 90},
    )
    assert odd.status_code == 400


def test_reject_does_not_open_a_desk():
    created = client.post(
        "/api/pilot-request",
        json={"name": "Reject", "email": "nope@desk.test", "firm": "No Desk", "website": ""},
    ).json()
    rejected = client.patch(
        f"/api/admin/portal/pilot-requests/{created['request_id']}",
        headers=ADMIN,
        json={"action": "reject", "term_days": 60},
    )
    assert rejected.status_code == 200
    assert rejected.json()["request"]["status"] == "rejected"
    assert not rejected.json()["request"].get("org_id")


def _pilot_key(term_days: int, *, started_days_ago: int = 0) -> str:
    opened = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "Holdings Desk", "term_days": term_days},
    )
    assert opened.status_code == 200, opened.text
    org_id = opened.json()["org"]["id"]
    if started_days_ago:
        row = get_data()["pilot_checklists"][org_id]
        start = datetime.now(timezone.utc) - timedelta(days=started_days_ago)
        row["created_at"] = start.isoformat()
        save_data()
    key = f"holdings-{org_id}"
    get_data()["api_keys"].append({"key": key, "org": org_id, "role": "analyst"})
    save_data()
    return key


def _lines():
    return {
        "as_of": "2026-10-24",
        "lines": [
            {"isin": "INE009A01021", "weight": 50, "name": "Infosys"},
            {"isin": "INE000A00000", "weight": 50, "name": "Unscored Co"},
            {"isin": "INE999Z99999", "weight": 10, "name": "Unknown"},
            {"residual": "cash", "weight": 20, "name": "Cash"},
        ],
    }


def test_missing_score_stays_out_of_the_weighted_figure(monkeypatch, tmp_path):
    import app.services.holdings as holdings

    monkeypatch.setattr(holdings, "_root", lambda: tmp_path)

    def resolve(isin: str):
        if isin == "INE009A01021":
            return {"id": "infy", "name": "Infosys Ltd.", "ticker": "INFY"}
        if isin == "INE000A00000":
            return {"id": "blank", "name": "Unscored Co", "ticker": "BLANK"}
        return None

    def published(company_id: str):
        if company_id == "infy":
            return {"gci_score": 80.0, "confidence_tier": "established", "as_of": "2026-04-18"}
        return {"gci_score": None, "confidence_tier": None, "as_of": None}

    monkeypatch.setattr(holdings, "_resolve_isin", resolve)
    monkeypatch.setattr(holdings, "_published", published)
    monkeypatch.setattr(holdings, "_open_commitments", lambda _cid: 0)

    denied = client.post("/api/holdings/lookthrough", headers=DEMO, json=_lines())
    assert denied.status_code == 403

    key = _pilot_key(30)
    first = client.post(
        "/api/holdings/lookthrough",
        headers={"X-API-Key": key},
        json=_lines(),
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["covered_gci"] == 80.0
    assert body["covered_gci"] != 40.0
    assert any(g["reason"] == "unscored" for g in body["gaps"])
    assert any(g["reason"] == "unresolved" for g in body["gaps"])
    assert body["residual"][0]["kind"] == "cash"
    assert body["diff"] is None

    second_lines = _lines()
    second_lines["as_of"] = "2026-11-24"
    second_lines["lines"][0]["weight"] = 40
    second = client.post(
        "/api/holdings/lookthrough",
        headers={"X-API-Key": key},
        json=second_lines,
    )
    assert second.status_code == 200, second.text
    assert second.json()["diff"]["prior_as_of"] == "2026-10-24"
    assert second.json()["diff"]["weight_changes"]

    other = _pilot_key(45)
    empty = client.get("/api/holdings/latest", headers={"X-API-Key": other})
    assert empty.status_code == 404

    paid = client.post("/api/holdings/lookthrough", headers=ONESTOP, json=_lines())
    assert paid.status_code == 200, paid.text

    expired = _pilot_key(30, started_days_ago=31)
    closed = client.post(
        "/api/holdings/lookthrough",
        headers={"X-API-Key": expired},
        json=_lines(),
    )
    assert closed.status_code == 403


def test_infosys_fy24_margin_is_on_the_record():
    row = next(item for item in INFY if item["period"] == "FY24" and item["metric"] == "operating_margin_pct")
    outcome = outcome_from_dict(row)
    assert outcome.guided_low == 20.0
    assert outcome.guided_high == 22.0
    assert outcome.actual_value == 20.7
    assert classify_outcome(outcome) == OutcomeLabel.MET
    assert "operating margin of 20.7%" in (outcome.quote_span or "")
    assert "20%-22%" in (outcome.guidance_quote or "")


def test_a_paid_desk_keeps_holdings_after_an_expired_checklist():
    from app.services.orgs import org_snapshot

    get_data().setdefault("pilot_checklists", {})["onestop-demo"] = {
        "approved": True,
        "term_days": 30,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
    }
    save_data()
    features = set(org_snapshot("onestop-demo")["features"])
    assert {"holdings", "ninja", "desk"} <= features


def test_expired_evaluation_closes_the_desk():
    expired = _pilot_key(30, started_days_ago=31)
    closed = client.get("/api/analyst/skills", headers={"X-API-Key": expired})
    assert closed.status_code == 403
    assert "ended" in closed.json()["detail"].lower()
    open_key = _pilot_key(45)
    opened = client.get("/api/analyst/skills", headers={"X-API-Key": open_key})
    assert opened.status_code == 200, opened.text


def test_manager_tilt_and_scheme_use_only_entered_values():
    from app.services.holdings import build_lookthrough

    report = build_lookthrough(
        [{"isin": "A", "weight": 80}, {"isin": "B", "weight": 20}],
        as_of="2026-10-24",
        resolve_isin=lambda isin: {"id": isin, "name": isin, "ticker": isin},
        published_score=lambda company_id: {
            "gci_score": 80.0 if company_id == "A" else 40.0,
            "confidence_tier": "established",
        },
        universe_gci=50.0,
        scheme=[{"as_of": "2025-03-31", "value": 100}, {"as_of": "2026-03-31", "value": 110}],
    )
    assert report["covered_gci"] == 72.0
    assert report["manager"]["equal_weight_gci"] == 60.0
    assert report["manager"]["delivery_tilt"] == 12.0
    assert report["manager"]["versus_universe"] == 22.0
    assert report["scheme"]["change_pct"] == 10.0
    assert "alpha" not in report["manager"]["statement"].lower()


def test_reopening_the_file_keeps_manager_and_scheme(monkeypatch, tmp_path):
    import app.services.holdings as holdings

    monkeypatch.setattr(holdings, "_root", lambda: tmp_path)

    def resolve(isin: str):
        if isin == "INE009A01021":
            return {"id": "infy", "name": "Infosys Ltd.", "ticker": "INFY"}
        if isin == "INE000A00000":
            return {"id": "blank", "name": "Unscored Co", "ticker": "BLANK"}
        return None

    monkeypatch.setattr(holdings, "_resolve_isin", resolve)
    monkeypatch.setattr(
        holdings,
        "_published",
        lambda company_id: {
            "gci_score": 80.0 if company_id == "infy" else None,
            "confidence_tier": "deep" if company_id == "infy" else None,
            "as_of": "2026-04-18",
        },
    )
    monkeypatch.setattr(holdings, "_open_commitments", lambda _cid: 0)
    body = _lines()
    body["scheme"] = [
        {"as_of": "2025-03-31", "value": 100},
        {"as_of": "2026-03-31", "value": 110},
    ]
    posted = client.post("/api/holdings/lookthrough", headers=ONESTOP, json=body)
    assert posted.status_code == 200, posted.text
    latest = client.get("/api/holdings/latest", headers=ONESTOP)
    assert latest.status_code == 200, latest.text
    saved = latest.json()
    assert saved["manager"]["delivery_tilt"] == posted.json()["manager"]["delivery_tilt"]
    assert saved["scheme"]["change_pct"] == 10.0
    assert saved["covered_gci"] == 80.0
    assert len(saved["lines"]) == len(body["lines"])
    assert saved["scheme"]["points"][0]["as_of"] == "2025-03-31"

