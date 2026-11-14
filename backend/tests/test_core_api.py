"""GCI Core API, calculation snapshots, change feed, and the Core Qual branch."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services import score_ledger
from app.services.gci_scoring import compute_company_gci
from app.data.seed import get_outcomes

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
RETAIL = {"X-API-Key": "intellens-retail"}


def setup_function():
    reset_data()


# --- API ----------------------------------------------------------------------


def test_methodology_names_published_and_shadow_methods():
    body = client.get("/api/v1/index/methodology").json()
    assert body["published"]["algorithm_id"] == "gci_scoring_v4"
    assert body["shadow"]["algorithm_id"] == "gci_core_v2_4"
    assert body["shadow"]["approved"] is False
    assert body["shadow"]["ruleset"] == "v2.4"
    assert body["proposals"]["status"] == "change_control"


def test_market_profiles_are_public():
    body = client.get("/api/v1/index/markets").json()
    assert body["count"] == 12
    india = next(m for m in body["markets"] if m["market_id"] == "IN")
    assert india["core_status"] == "publish"


def test_core_preview_is_reviewer_only():
    assert client.get("/api/v1/index/core/infy").status_code in (401, 403)
    assert client.get("/api/v1/index/core/infy", headers=RETAIL).status_code in (401, 403)
    res = client.get("/api/v1/index/core/infy", headers=DEMO)
    assert res.status_code == 200
    body = res.json()
    assert body["algorithm_id"] == "gci_core_v2_4" and body["ruleset"] == "v2.4"
    assert body["publication_status"] == "SHADOW"
    assert client.get("/api/v1/index/core/nope", headers=DEMO).status_code == 404


def test_core_proposal_ruleset_is_opt_in():
    body = client.get("/api/v1/index/core/infy?ruleset=v2.5-proposal", headers=DEMO).json()
    assert body["algorithm_id"] == "gci_core_v2_5_proposal"
    assert client.get("/api/v1/index/core/infy?ruleset=v9", headers=DEMO).status_code == 422


def test_core_shadow_table_reports_both_levels():
    body = client.get("/api/v1/index/core", headers=DEMO).json()
    assert body["gate"] == 8
    assert not body["nondeterministic"]
    infy = next(r for r in body["rows"] if r["company_id"] == "infy")
    assert {"v4_gci", "core_gci", "core_basis", "proposal_gci"} <= set(infy)


def test_published_level_is_not_moved_by_core():
    before = client.get("/api/companies/infy").json()
    client.get("/api/v1/index/core/infy", headers=DEMO)
    after = client.get("/api/companies/infy").json()
    assert before.get("gci_score") == after.get("gci_score")
    assert after.get("algorithm_id", "gci_scoring_v4") == "gci_scoring_v4"


def test_updates_feed_validates_since():
    assert client.get("/api/v1/index/updates?since=yesterday").status_code == 422
    body = client.get("/api/v1/index/updates?since=2000-01-01").json()
    assert body["since"] == "2000-01-01"
    assert isinstance(body["rows"], list) and isinstance(body["changelog"], list)


# --- snapshots ----------------------------------------------------------------


def test_snapshot_written_with_ledger_row_and_replays(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(score_ledger, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(score_ledger, "SNAPSHOT_DIR", tmp_path / "calc_snapshots")
    rows = get_outcomes("infy")
    gci = compute_company_gci(rows, version="v4")
    snap = score_ledger.snapshot_payload(
        "infy", as_of="2026-11-09", algorithm_id="gci_scoring_v4",
        dataset_version="2026-11-09.1", gci=gci, confidence_tier="deep",
    )
    sid = score_ledger.snapshot_id_for(snap)
    row = score_ledger.LedgerRow(
        company_id="infy", as_of="2026-11-09", algorithm_id="gci_scoring_v4",
        dataset_version="2026-11-09.1", gci=gci, prior_gci=None, confidence_tier="deep",
        reason="snapshot", note="t", by="test", snapshot_id=sid, snapshot=snap,
    )
    assert score_ledger.append(row) is True
    stored = score_ledger.read_all()[-1]
    assert stored["snapshot_id"] == sid and "snapshot" not in stored
    replay = score_ledger.replay_snapshot(sid)
    assert replay["content_intact"] is True
    assert replay["replayed_gci"] == replay["recorded_gci"] == gci
    assert replay["matches"] is True
    res = client.get(f"/api/v1/index/snapshots/{sid}")
    assert res.status_code == 200 and res.json()["replay"]["matches"] is True
    assert client.get(f"/api/v1/index/snapshots/{sid}?include_inputs=true").status_code == 401
    full = client.get(f"/api/v1/index/snapshots/{sid}?include_inputs=true", headers=DEMO).json()
    assert full["snapshot"]["inputs"]["outcomes"]
    assert client.get("/api/v1/index/snapshots/sha256:../../etc").status_code == 404


def test_rows_without_snapshot_keep_the_old_ledger_shape():
    row = score_ledger.LedgerRow(
        company_id="x", as_of="2026-01-01", algorithm_id="gci_scoring_v4",
        dataset_version="t", gci=50.0, prior_gci=None, confidence_tier="provisional",
        reason="methodology", note="t", by="test",
    )
    assert "snapshot_id" not in row.to_json() and "snapshot" not in row.to_json()


# --- Qual branch through the API -----------------------------------------------


def test_core_scores_accepted_commitments_as_the_qual_branch(monkeypatch):
    from app.services import commitment_store

    rows = [{"id": "c1", "company_id": "infy", "type": "capacity", "review_status": "accepted",
             "state": "delivered", "due_period": "FY24", "subject": "s", "outcome": "o",
             "quote": "q", "source_url": "u", "as_of": "2023-05-01"}]
    monkeypatch.setattr(commitment_store, "list_commitments", lambda cid, include_unreviewed=False: rows)
    body = client.get("/api/v1/index/core/infy?as_of=2025-01-01", headers=DEMO).json()
    assert body["qual_gci"] == 100.0
    assert body["qual"]["families"][0]["decomposition"] == "INDIVISIBLE"
    if body["quant_gci"] is not None:
        assert body["composite_basis"] == "quant_and_qual"


def test_commitments_never_move_the_published_gci():
    before = client.get("/api/companies/infy").json().get("gci_score")
    client.get("/api/v1/index/core/infy", headers=DEMO)
    assert client.get("/api/companies/infy").json().get("gci_score") == before
    assert client.get("/api/v1/index/cdi/infy", headers=DEMO).status_code == 404


# --- evidence integrity -------------------------------------------------------


def test_raw_bytes_hash_and_public_availability(tmp_path: Path, monkeypatch):
    import hashlib

    from app.data import doc_store

    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(doc_store, "_DOCS", None)
    raw = b"%PDF-1.4 results release body"
    doc = doc_store.upsert_document(
        company_id="x", doc_type="filing", title="t", text="Revenue grew 12% to Rs 1,000 crore. " * 3,
        url="https://example.com/a.pdf", date="2026-01-10", raw_bytes=raw,
        public_available_at="2026-01-10T16:05:00+05:30",
    )
    assert doc["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert doc["public_available_at"] == "2026-01-10T16:05:00+05:30"
    assert (tmp_path / "doc_raw" / doc["raw_sha256"]).read_bytes() == raw
    monkeypatch.setattr(doc_store, "_DOCS", None)


# --- delivery ruleset, companions, drill-down, release gates, publication -------

ADMIN = {"X-API-Key": "intellens-admin"}
LABELER = {"X-API-Key": "intellens-onestop-labeler"}


def _isolate_audit(tmp_path: Path, monkeypatch):
    from app.data import audit_log

    monkeypatch.setattr(audit_log, "_PATH", tmp_path / "audit.json")
    monkeypatch.setattr(audit_log, "_LOG", None)
    monkeypatch.setattr(score_ledger, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(score_ledger, "SNAPSHOT_DIR", tmp_path / "calc_snapshots")
    from app.services import guidance_review

    monkeypatch.setattr(guidance_review, "changelog_write_path", lambda: tmp_path / "score_changelog.json")


def _gates_pass(monkeypatch, **override):
    from app.jobs import validation_gates

    real = validation_gates.core_release_gates
    monkeypatch.setattr(validation_gates, "core_release_gates",
                        lambda cid, **kw: {**real(cid, **kw), "passed": True, "failed": [], **override})


def test_methodology_lists_default_delivery_and_companions():
    body = client.get("/api/v1/index/methodology").json()
    assert body["default_ruleset"] == "v2.4"
    assert body["delivery"]["algorithm_id"] == "gci_core_delivery_v1"
    assert {e["companion"] for e in body["delivery"]["excludes"]} <= {c["id"] for c in body["companions"]}
    assert len(body["companions"]) == 6


def test_delivery_ruleset_through_the_api_is_quant_headline():
    body = client.get("/api/v1/index/core/infy?ruleset=delivery", headers=DEMO).json()
    assert body["algorithm_id"] == "gci_core_delivery_v1" and body["headline"] == "quant"
    assert body["composite_gci"] == body["quant_gci"]
    assert all(f.get("frequency_penalty") in (None, 0.0) for f in body["families"])


def test_r2_ruleset_is_shadow_and_reports_its_terms():
    meth = client.get("/api/v1/index/methodology").json()
    assert meth["default_ruleset"] == "v2.4" and meth["r2"]["status"] == "shadow_pending_owner_ruling"
    assert meth["r2"]["scale_rule"] == "max(width, |midpoint|, floor)"
    body = client.get("/api/v1/index/core/infy?ruleset=v2.4-R2", headers=DEMO).json()
    assert body["algorithm_id"] == "gci_core_v2_4_r2" and body["publication_status"] != "PUBLISHABLE"
    assert body["headline_rule"] == "QUANT_DOMINANT" and body["headline_gci"] == body["quant_gci"]
    scored = [f for f in body["families"] if f["score"] is not None]
    assert scored and all(f["lead_time"]["interpolation_method"] == "LINEAR_NORMALISED" for f in scored)
    assert all("effective_scale" in v for f in scored for v in f["vintages"] if v["eligible"])
    rows = client.get("/api/v1/index/core", headers=DEMO).json()["rows"]
    assert any(r["r2_gci"] is not None for r in rows)


def test_drill_down_parameter_family_vintage():
    core = client.get("/api/v1/index/core/infy", headers=DEMO).json()
    fam = next(f for f in core["families"] if f["calculation_status"] == "COMPUTED")
    p = client.get(f"/api/v1/index/core/infy/parameters/{fam['parameter']}", headers=DEMO).json()
    assert any(f["family_id"] == fam["family_id"] for f in p["families"])
    f = client.get(f"/api/v1/index/core/infy/families/{fam['family_id']}", headers=DEMO).json()
    assert f["family"]["family_id"] == fam["family_id"]
    assert len(f["evidence"]["vintages"]) == len(fam["vintages"])
    vid = fam["vintages"][0]["vintage_id"]
    v = client.get(f"/api/v1/index/core/infy/vintages/{vid}", headers=DEMO).json()
    assert v["family_id"] == fam["family_id"] and v["vintage"]["vintage_id"] == vid
    assert client.get("/api/v1/index/core/infy/families/fam_nope", headers=DEMO).status_code == 404
    assert client.get("/api/v1/index/core/infy/vintages/vin_nope", headers=DEMO).status_code == 404
    assert client.get(f"/api/v1/index/core/infy/families/{fam['family_id']}").status_code in (401, 403)


def test_bulk_core_headline_fields():
    body = client.post("/api/v1/index/core/bulk", json={"company_ids": ["infy", "cipla"], "ruleset": "delivery"},
                       headers=DEMO).json()
    assert [r["company_id"] for r in body["rows"]] == ["infy", "cipla"]
    assert all(r["algorithm_id"] == "gci_core_delivery_v1" and "families" not in r for r in body["rows"])


def test_companions_route_is_reviewer_only_and_preview():
    assert client.get("/api/v1/index/companions/infy").status_code in (401, 403)
    body = client.get("/api/v1/index/companions/infy", headers=DEMO).json()
    assert [i["id"] for i in body["indexes"]][0] == "revision_discipline"
    assert all(i["status"] == "preview" and not i["rankable"] for i in body["indexes"])
    assert "thin_history" in body["diagnostics"]


def test_readiness_blocks_while_engine_unapproved():
    body = client.get("/api/v1/index/core/infy/readiness", headers=DEMO).json()
    assert body["passed"] is False
    assert "G-01" in body["failed"]
    assert {g["id"] for g in body["gates"] if g.get("manual")} == {"G-05", "G-06", "G-07", "G-08"}


def test_publication_needs_a_second_person_and_every_gate(tmp_path: Path, monkeypatch):
    _isolate_audit(tmp_path, monkeypatch)
    req = client.post("/api/v1/index/core/infy/publication-requests", json={}, headers=LABELER).json()
    assert req["status"] == "awaiting_approval" and req["snapshot_id"].startswith("sha256:")
    eid = req["event_id"]
    labeler = client.post(f"/api/v1/index/publication-requests/{eid}/decision", json={"approve": True}, headers=LABELER)
    assert labeler.status_code == 403
    own = client.post("/api/v1/index/core/infy/publication-requests", json={}, headers=ADMIN).json()["event_id"]
    same = client.post(f"/api/v1/index/publication-requests/{own}/decision", json={"approve": True}, headers=ADMIN)
    assert same.status_code == 409 and same.json()["detail"] == "second_person_required"
    blocked = client.post(f"/api/v1/index/publication-requests/{eid}/decision", json={"approve": True}, headers=ADMIN).json()
    assert blocked["status"] == "blocked" and "G-01" in blocked["failed_gates"]
    assert not [r for r in score_ledger.rows_for("infy") if r["algorithm_id"].startswith("gci_core")]
    again = client.post(f"/api/v1/index/publication-requests/{eid}/decision", json={"approve": True}, headers=ADMIN)
    assert again.status_code == 409
    listed = client.get("/api/v1/index/publication-requests?company_id=infy", headers=DEMO).json()
    assert {r["event_id"]: r["status"] for r in listed["rows"]} == {eid: "blocked", own: "awaiting_approval"}


def test_approved_publication_appends_a_replayable_ledger_row(tmp_path: Path, monkeypatch):
    import json

    _isolate_audit(tmp_path, monkeypatch)
    _gates_pass(monkeypatch)
    eid = client.post("/api/v1/index/core/infy/publication-requests", json={"ruleset": "delivery"}, headers=LABELER).json()["event_id"]
    out = client.post(f"/api/v1/index/publication-requests/{eid}/decision", json={"approve": True}, headers=ADMIN).json()
    assert out["status"] == "approved" and out["failed_gates"] == []
    row = score_ledger.rows_for("infy")[-1]
    assert row["algorithm_id"] == "gci_core_delivery_v1" and row["reason"] == "methodology"
    assert score_ledger.replay_snapshot(row["snapshot_id"])["matches"] is True
    entry = json.loads((tmp_path / "score_changelog.json").read_text())["entries"][0]
    assert entry["reason"] == "methodology" and entry["companies"] == ["infy"] and eid in entry["change"]


def test_approval_of_a_level_that_has_since_moved_is_blocked(tmp_path: Path, monkeypatch):
    _isolate_audit(tmp_path, monkeypatch)
    req = client.post("/api/v1/index/core/infy/publication-requests", json={"ruleset": "delivery"}, headers=LABELER).json()
    _gates_pass(monkeypatch, level=req["gci"] + 1)
    out = client.post(f"/api/v1/index/publication-requests/{req['event_id']}/decision", json={"approve": True}, headers=ADMIN).json()
    assert out["status"] == "blocked" and out["failed_gates"] == ["STALE_REQUEST"]
    assert not [r for r in score_ledger.rows_for("infy") if r["algorithm_id"].startswith("gci_core")]
    assert not (tmp_path / "score_changelog.json").exists()


def test_every_gci_method_has_one_stable_name_and_code():
    from app.services import gci_scoring as g

    methods = client.get("/api/v1/index/methodology").json()["methods"]
    assert [(m["code"], m["label"], m["status"]) for m in methods] == [
        ("classic", "GCI Classic (v4)", "published"),
        ("core", "GCI Core (v2.4)", "shadow"),
        ("range", "GCI Range (v2.4-R2)", "pending_ruling"),
        ("delivery", "GCI Delivery (v1)", "alternative"),
        ("draft", "GCI Draft (v2.5)", "change_control"),
    ]
    assert {m["algorithm_id"] for m in methods} == {g.algorithm_id(), *g.CORE_ALGORITHM_IDS.values()}
    assert {m["ruleset"] for m in methods if m["ruleset"]} == set(g.CORE_RULESETS)
    assert g.method_label("gci_scoring_v3") == "GCI Classic (v3)" and g.gci_method("gci_scoring_v3")["status"] == "retired"
    assert g.method_label("unknown") is None


def test_a_customer_selects_a_method_by_its_code():
    by_code = client.get("/api/v1/index/core/infy?ruleset=range", headers=DEMO).json()
    by_id = client.get("/api/v1/index/core/infy?ruleset=v2.4-R2", headers=DEMO).json()
    assert by_code["ruleset"] == "v2.4-R2" and by_code["method_label"] == "GCI Range (v2.4-R2)"
    assert by_code["headline_gci"] == by_id["headline_gci"] and by_code["input_digest"] == by_id["input_digest"]
    assert client.get("/api/v1/index/core/infy", headers=DEMO).json()["method"]["code"] == "core"
    assert client.get("/api/v1/index/core/infy/readiness?ruleset=delivery", headers=DEMO).json()["ruleset"] == "delivery"
    bulk = client.post("/api/v1/index/core/bulk", json={"company_ids": ["infy"], "ruleset": "draft"}, headers=DEMO).json()
    assert bulk["rows"][0]["method_label"] == "GCI Draft (v2.5)"
    for bad in ("classic", "bogus"):
        res = client.get(f"/api/v1/index/core/infy?ruleset={bad}", headers=DEMO)
        assert res.status_code == 422 and "range" in res.json()["detail"]


def test_dossier_names_its_published_method():
    assert client.get("/api/companies/infy/gci").json()["method_label"] == "GCI Classic (v4)"


def test_route_map_keeps_two_scopes_of_one_figure_apart():
    row = {"period": "FY24", "metric": "revenue_cr", "guided_value": 100, "actual_value": 105, "review_status": "accepted"}
    routes = score_ledger._route_map([{**row, "scope": "consolidated"}, {**row, "scope": "segment", "actual_value": None}])
    assert len(routes) == 2 and len(set(routes.values())) == 2


def test_readiness_replays_the_serialised_snapshot():
    body = client.get("/api/v1/index/core/infy/readiness?ruleset=v2.4-R2", headers=DEMO).json()
    g02 = next(g for g in body["gates"] if g["id"] == "G-02")
    assert g02["passed"] is True and f"snapshot replay {body['level']} vs {body['level']}" in g02["detail"]


def test_publication_snapshot_replays_with_its_market_calendar(tmp_path: Path, monkeypatch):
    _isolate_audit(tmp_path, monkeypatch)
    from app.jobs import validation_gates

    held = validation_gates.core_inputs
    monkeypatch.setattr(validation_gates, "core_inputs",
                        lambda cid, *a, **kw: {**held(cid, *a, **kw), "market_id": "US", "fy_end_mmdd": "12-31"})
    _gates_pass(monkeypatch)
    req = client.post("/api/v1/index/core/infy/publication-requests", json={"ruleset": "v2.4-R2"}, headers=LABELER).json()
    snap = score_ledger.read_snapshot(req["snapshot_id"])
    assert snap["inputs"]["market"] == {"market_id": "US", "regime": snap["inputs"]["market"]["regime"], "fy_end_mmdd": "12-31"}
    out = client.post(f"/api/v1/index/publication-requests/{req['event_id']}/decision", json={"approve": True}, headers=ADMIN).json()
    assert out["status"] == "approved" and out["gci"] is not None
    row = score_ledger.rows_for("infy")[-1]
    assert row["algorithm_id"] == "gci_core_v2_4_r2" and row["gci"] == req["gci"]
    replay = score_ledger.replay_snapshot(row["snapshot_id"])
    assert replay["matches"] is True and replay["replayed_gci"] == req["gci"]


def test_core_reviewer_routes_stay_inside_the_desks_markets(tmp_path: Path, monkeypatch):
    from app.services.session_auth import reset_auth_store

    _isolate_audit(tmp_path, monkeypatch)
    eid = client.post("/api/v1/index/core/infy/publication-requests", json={}, headers=ADMIN).json()["event_id"]
    try:
        coverage = client.put("/api/admin/portal/orgs/onestop-demo/coverage", headers=ADMIN, json={"coverage": ["US"]})
        assert coverage.status_code == 200
        shadow = client.get("/api/v1/index/core", headers=LABELER).json()
        assert "infy" not in {r["company_id"] for r in shadow["rows"]}
        assert client.get("/api/v1/index/core/infy", headers=LABELER).status_code == 403
        assert client.post("/api/v1/index/core/bulk", json={"company_ids": ["infy"]}, headers=LABELER).status_code == 403
        assert client.get("/api/v1/index/publication-requests", headers=LABELER).json()["rows"] == []
        out = client.post(f"/api/v1/index/publication-requests/{eid}/decision", json={"approve": False}, headers=LABELER)
        assert out.status_code == 403 and out.json()["detail"]["code"] == "market_not_in_plan", out.text
    finally:
        reset_data()
        reset_auth_store()
    assert "infy" in {r["company_id"] for r in client.get("/api/v1/index/core", headers=LABELER).json()["rows"]}
    assert client.get("/api/v1/index/publication-requests", headers=LABELER).json()["count"] == 1


def test_release_signoff_is_admin_only(tmp_path: Path, monkeypatch):
    _isolate_audit(tmp_path, monkeypatch)
    assert client.post("/api/v1/index/release-signoffs", json={"gate_id": "G-05"}, headers=LABELER).status_code == 403
    assert client.post("/api/v1/index/release-signoffs", json={"gate_id": "G-99"}, headers=ADMIN).status_code == 422
    assert client.post("/api/v1/index/release-signoffs", json={"gate_id": "G-05"}, headers=ADMIN).status_code == 200
    assert score_ledger.signed_off_gates() == ["G-05"]


def test_governance_events_survive_the_audit_trim(tmp_path: Path, monkeypatch):
    _isolate_audit(tmp_path, monkeypatch)
    from app.data import audit_log

    monkeypatch.setattr(audit_log, "save", lambda: None)
    score_ledger.record_signoff("G-06", by="admin@x", role="admin")
    for i in range(2100):
        audit_log.record("extract", detail={"i": i})
    assert score_ledger.signed_off_gates() == ["G-06"]
    assert len(audit_log._load()) < 2000
