"""Four seats, audit gate, and the accept split. Plan ∩ role, plus two seat-only names."""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.data.seed import get_data, reset_data
from app.main import app
from app.services.entitlements import _effective_features
from app.services.holdings import since_last_open
from app.services.orgs import PLAN_FEATURES
from app.services.session_auth import reset_auth_store, seat_role_for_actor

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    os.environ["INTELLENS_AUTH_DEV_TOKENS"] = "1"
    reset_auth_store()
    reset_data()


def test_pm_desk_includes_holdings_and_excludes_desk_write():
    feats = _effective_features(set(PLAN_FEATURES["desk"]), "pm")
    assert "holdings" in feats
    assert "alerts" in feats
    assert "desk_write" not in feats


def test_pm_pilot_excludes_holdings():
    feats = _effective_features(set(PLAN_FEATURES["pilot"]), "pm")
    assert "holdings" not in feats
    assert "tracker" in feats


def test_data_enterprise_includes_em_export():
    feats = _effective_features(set(PLAN_FEATURES["enterprise"]), "data")
    assert "em_export" in feats
    assert "desk_write" not in feats


def test_data_pilot_excludes_em_export():
    feats = _effective_features(set(PLAN_FEATURES["pilot"]), "data")
    assert "em_export" not in feats


def test_oversight_includes_org_audit():
    feats = _effective_features(set(PLAN_FEATURES["pilot"]), "oversight")
    assert "org_audit" in feats
    assert "desk_write" not in feats


def test_ir_includes_pack_export():
    feats = _effective_features(set(PLAN_FEATURES["pilot"]), "ir")
    assert "pack_export" in feats
    assert "em_export" not in feats
    assert "desk_write" not in feats


def test_unknown_role_matches_viewer():
    assert _effective_features(set(PLAN_FEATURES["desk"]), "no-such-seat") == _effective_features(
        set(PLAN_FEATURES["desk"]), "viewer"
    )


def test_admin_on_pilot_keeps_audit_and_pack_without_em_export():
    feats = _effective_features(set(PLAN_FEATURES["pilot"]), "admin")
    assert "org_audit" in feats
    assert "pack_export" in feats
    assert "em_export" not in feats


def _register(email: str, org_name: str) -> dict:
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "secret99pass!",
            "name": org_name,
            "accept_terms": True,
            "account_type": "b2b",
            "org_name": org_name,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _invite(owner: dict, email: str, role: str, scope: list | None = None) -> dict:
    org_id = owner["user"]["org_id"]
    body: dict = {"email": email, "role": role}
    invited = client.post(
        f"/api/orgs/{org_id}/invites",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json=body,
    )
    assert invited.status_code == 200, invited.text
    accepted = client.post(
        "/api/auth/accept-invite",
        json={
            "token": invited.json()["dev_token"],
            "password": "secret99pass!",
            "name": email.split("@")[0],
            "accept_terms": True,
        },
    )
    assert accepted.status_code == 200, accepted.text
    if scope is not None:
        seated = client.post(
            f"/api/orgs/{org_id}/members/{accepted.json()['user']['id']}/role",
            headers={"Authorization": f"Bearer {owner['token']}"},
            json={"role": role, "company_scope": scope},
        )
        assert seated.status_code == 200, seated.text
        return seated.json()["user"] | {"token": accepted.json()["token"]}
    return accepted.json()["user"] | {"token": accepted.json()["token"]}


def test_owner_can_invite_the_four_seats_and_not_a_made_up_one():
    owner = _register("owner.seats@desk.test", "Seat Desk")
    org_id = owner["user"]["org_id"]
    for role, email in (
        ("pm", "pm.seats@desk.test"),
        ("data", "data.seats@desk.test"),
        ("oversight", "oversight.seats@desk.test"),
        ("ir", "ir.seats@desk.test"),
    ):
        invited = client.post(
            f"/api/orgs/{org_id}/invites",
            headers={"Authorization": f"Bearer {owner['token']}"},
            json={"email": email, "role": role},
        )
        assert invited.status_code == 200, invited.text
    refused = client.post(
        f"/api/orgs/{org_id}/invites",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"email": "nope.seats@desk.test", "role": "journalist"},
    )
    assert refused.status_code == 400


def test_analyst_cannot_accept_and_reviewer_can():
    owner = _register("owner.accept@desk.test", "Accept Desk")
    analyst = _invite(owner, "analyst.accept@desk.test", "analyst")
    reviewer = _invite(owner, "reviewer.accept@desk.test", "reviewer")
    body = {"company_id": "infy", "outcome_index": 0, "action": "accept"}
    blocked = client.post(
        "/api/review",
        headers={"Authorization": f"Bearer {analyst['token']}"},
        json=body,
    )
    assert blocked.status_code == 403
    assert "reviewer" in blocked.text.lower()
    accepted = client.post(
        "/api/review",
        headers={"Authorization": f"Bearer {reviewer['token']}"},
        json=body,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["review"]["reviewer"] != owner["user"]["org_id"]


def test_analyst_loses_audit_and_oversight_keeps_it():
    owner = _register("owner.trail@desk.test", "Trail Desk")
    analyst = _invite(owner, "analyst.trail@desk.test", "analyst")
    oversight = _invite(owner, "oversight.trail@desk.test", "oversight")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {analyst['token']}"}).status_code == 403
    trail = client.get("/api/audit", headers={"Authorization": f"Bearer {oversight['token']}"})
    assert trail.status_code == 200, trail.text


def test_ir_pack_is_limited_to_the_allow_list():
    owner = _register("owner.ir@desk.test", "IR Desk")
    ir = _invite(owner, "ir.pack@desk.test", "ir", scope=["infy"])
    headers = {"Authorization": f"Bearer {ir['token']}"}
    outside = client.post(
        "/api/analyst/run",
        headers=headers,
        json={"skill_id": "board_scorecard", "company_id": "tcs"},
    )
    assert outside.status_code == 403
    other_skill = client.post(
        "/api/analyst/run",
        headers=headers,
        json={"skill_id": "results_prep", "company_id": "infy"},
    )
    assert other_skill.status_code == 403
    packed = client.post(
        "/api/analyst/run",
        headers=headers,
        json={"skill_id": "board_scorecard", "company_id": "infy"},
    )
    assert packed.status_code == 200, packed.text
    run_id = packed.json()["run_id"]
    exported = client.get(f"/api/analyst/runs/{run_id}/export?format=md", headers=headers)
    assert exported.status_code == 200, exported.text
    trail = client.get("/api/audit", headers={"Authorization": f"Bearer {owner['token']}"}).json()
    packs = [e for e in trail["events"] if e["action"] == "pack_export"]
    assert packs and packs[0]["actor"] == "ir.pack@desk.test"


def test_ir_with_no_company_named_is_told_so():
    owner = _register("owner.irempty@desk.test", "IR Empty Desk")
    ir = _invite(owner, "ir.empty@desk.test", "ir", scope=[])
    res = client.post(
        "/api/analyst/run",
        headers={"Authorization": f"Bearer {ir['token']}"},
        json={"skill_id": "board_scorecard", "company_id": "infy"},
    )
    assert res.status_code == 403
    assert "not named a company" in res.text


def test_scope_on_another_seat_is_dropped_and_unknown_company_refused():
    owner = _register("owner.scope@desk.test", "Scope Desk")
    org_id = owner["user"]["org_id"]
    pm = _invite(owner, "pm.scope@desk.test", "pm")
    auth = {"Authorization": f"Bearer {owner['token']}"}
    kept = client.post(
        f"/api/orgs/{org_id}/members/{pm['id']}/role",
        headers=auth,
        json={"role": "pm", "company_scope": ["infy"]},
    )
    assert kept.status_code == 200, kept.text
    assert kept.json()["user"]["company_scope"] == []
    unknown = client.post(
        f"/api/orgs/{org_id}/members/{pm['id']}/role",
        headers=auth,
        json={"role": "ir", "company_scope": ["no-such-co"]},
    )
    assert unknown.status_code == 400


def test_ir_cannot_run_a_project():
    owner = _register("owner.irproj@desk.test", "IR Project Desk")
    ir = _invite(owner, "ir.proj@desk.test", "ir", scope=["infy"])
    res = client.post(
        "/api/analyst/run",
        headers={"Authorization": f"Bearer {ir['token']}"},
        json={"skill_id": "board_scorecard", "company_id": "infy", "project_id": "p1"},
    )
    assert res.status_code == 403


def test_appointing_seats_follows_owner_and_admin_rules():
    assert seat_role_for_actor("admin", "pm") == "pm"
    assert seat_role_for_actor("admin", "oversight") == "oversight"
    assert seat_role_for_actor("owner", "admin") == "admin"
    assert seat_role_for_actor("admin", "member") == "viewer"
    with pytest.raises(HTTPException) as no_admin:
        seat_role_for_actor("admin", "admin")
    assert no_admin.value.status_code == 403
    with pytest.raises(HTTPException) as unknown:
        seat_role_for_actor("owner", "journalist")
    assert unknown.value.status_code == 400
    with pytest.raises(HTTPException) as no_owner:
        seat_role_for_actor("owner", "owner")
    assert no_owner.value.status_code == 400


@pytest.mark.parametrize("seat", ["labeler", "pm", "data", "ir", "oversight", "viewer"])
def test_seats_without_accept_are_refused_and_the_row_is_unchanged(seat):
    owner = _register(f"owner.{seat}.no@desk.test", f"No Accept {seat}")
    member = _invite(owner, f"{seat}.no@desk.test", seat)
    before = dict(get_data()["outcomes"]["infy"][0])
    res = client.post(
        "/api/review",
        headers={"Authorization": f"Bearer {member['token']}"},
        json={"company_id": "infy", "outcome_index": 0, "action": "accept"},
    )
    assert res.status_code == 403
    assert get_data()["outcomes"]["infy"][0] == before


def test_analyst_refusal_leaves_the_row_and_reviewer_accept_is_audited():
    owner = _register("owner.audit@desk.test", "Audit Accept Desk")
    analyst = _invite(owner, "analyst.audit@desk.test", "analyst")
    reviewer = _invite(owner, "reviewer.audit@desk.test", "reviewer")
    before = dict(get_data()["outcomes"]["infy"][0])
    body = {"company_id": "infy", "outcome_index": 0, "action": "reject"}
    refused = client.post("/api/review", headers={"Authorization": f"Bearer {analyst['token']}"}, json=body)
    assert refused.status_code == 403
    assert get_data()["outcomes"]["infy"][0] == before
    ok = client.post(
        "/api/review",
        headers={"Authorization": f"Bearer {reviewer['token']}"},
        json={"company_id": "infy", "outcome_index": 0, "action": "accept"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["review"]["reviewer"] == "reviewer.audit@desk.test"
    trail = client.get("/api/audit", headers={"Authorization": f"Bearer {reviewer['token']}"}).json()
    accepts = [e for e in trail["events"] if e["action"] == "review_accept"]
    assert accepts and accepts[0]["actor"] == "reviewer.audit@desk.test"


def test_oversight_cannot_read_another_org_trail():
    owner = _register("owner.cross@desk.test", "Cross Desk")
    other = _register("owner.cross2@desk.test", "Other Cross Desk")
    oversight = _invite(owner, "oversight.cross@desk.test", "oversight")
    res = client.get(
        f"/api/audit?org={other['user']['org_id']}",
        headers={"Authorization": f"Bearer {oversight['token']}"},
    )
    assert res.status_code == 403


def test_seat_change_is_on_the_trail():
    owner = _register("owner.seat@desk.test", "Seat Trail Desk")
    _invite(owner, "ir.seat@desk.test", "ir", scope=["infy"])
    trail = client.get("/api/audit", headers={"Authorization": f"Bearer {owner['token']}"}).json()
    changes = [e for e in trail["events"] if e["action"] == "seat_change"]
    assert changes and changes[0]["detail"]["to"] == "ir"
    assert changes[0]["detail"]["company_scope"] == ["infy"]


def test_since_last_open_counts_only_newer_records():
    rows = [
        {"company_id": "infy", "name": "Infosys", "open_commitments": 2},
        {"company_id": "tcs", "name": "TCS", "open_commitments": 0},
        {"company_id": "infy", "name": "Infosys duplicate", "open_commitments": 2},
    ]
    filings = {
        "infy": [
            {"doc_id": "old", "title": "Q1", "ingested_at": "2026-10-01T00:00:00+00:00"},
            {"doc_id": "new", "title": "Q2", "ingested_at": "2026-10-20T00:00:00+00:00"},
        ],
        "tcs": [{"doc_id": "t", "title": "Q2", "ingested_at": "2026-09-01T00:00:00+00:00"}],
    }
    misses = {"infy": [{"period": "FY25", "metric": "revenue_growth_pct", "as_of": "2026-10-15"}], "tcs": []}
    out = since_last_open(
        rows,
        since="2026-10-10T00:00:00Z",
        filings_for=lambda cid: filings.get(cid, []),
        missed_for=lambda cid: misses.get(cid, []),
    )
    kinds = [(r["company_id"], r["kind"]) for r in out]
    assert ("infy", "filing") in kinds
    assert [r["doc_id"] for r in out if r["kind"] == "filing"] == ["new"]
    assert ("infy", "open_guidance") in kinds
    assert ("infy", "missed") in kinds
    assert all(cid != "tcs" for cid, _ in kinds)


def test_since_last_open_first_visit_caps_filings_per_name():
    filings = [{"doc_id": str(i), "ingested_at": f"2026-10-{i + 10:02d}T00:00:00+00:00"} for i in range(6)]
    out = since_last_open(
        [{"company_id": "infy", "name": "Infosys"}],
        since=None,
        filings_for=lambda _cid: filings,
        missed_for=lambda _cid: [],
    )
    assert [r["doc_id"] for r in out] == ["5", "4", "3"]


def test_published_count_matches_the_india_rows_the_screener_shows():
    meta = client.get("/api/meta").json()
    rows = client.get("/api/companies").json()
    shown = [r for r in rows if r.get("market_id", "IN") == "IN" and r.get("gci_score") is not None]
    assert meta["published_gci_count"] == len(shown)
    ranked = [r for r in shown if r.get("confidence_tier") in ("established", "deep")]
    assert meta["published_ranked_count"] == len(ranked)
