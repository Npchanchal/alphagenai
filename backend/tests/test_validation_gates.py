"""Validation gates job, point-in-time checks and the as-of / evidence routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.data import doc_store
from app.jobs import validation_gates as vg
from app.main import app
from app.services import gci_scoring
from app.services.gci_scoring import GuidanceOutcome

client = TestClient(app)


def _row(**kw) -> GuidanceOutcome:
    base = dict(
        period="FY25", metric="revenue_growth_pct", guided_value=6.0, actual_value=6.5,
        guided_text="t", guided_low=5.0, guided_high=7.0,
        source_url="https://example.com/a", quote_span="q", as_of="2025-04-20",
        guidance_source_url="https://example.com/g", guidance_quote="g", guidance_as_of="2024-04-20",
        reviewed_by="analyst:t", reviewed_at="2026-10-18",
    )
    base.update(kw)
    return GuidanceOutcome(**base)


def test_shipped_data_has_no_point_in_time_violations():
    gate = vg.gate_point_in_time(vg._scored_companies())
    assert gate["passed"], gate


def test_pit_catches_promise_after_result_and_early_review():
    bad = _row(guidance_as_of="2025-05-01", reviewed_at="2025-01-01")
    problems = vg.pit_violations([bad])
    assert any("after the result filing" in p for p in problems)
    assert any("reviewed" in p for p in problems)


def test_pit_catches_revision_outside_window():
    rev = ({"as_of": "2025-06-01", "guided_low": 6.0, "guided_high": 8.0},)
    assert vg.pit_violations([_row(revisions=rev)])


def test_sensitivity_restores_floors():
    before = (gci_scoring.RATE_FLOOR_PP, gci_scoring.LEVEL_FLOOR_FRAC)
    report = vg.gate_floor_sensitivity({"x": [_row(guided_low=None, guided_high=None, actual_value=6.15)]})
    assert (gci_scoring.RATE_FLOOR_PP, gci_scoring.LEVEL_FLOOR_FRAC) == before
    assert report["max_swing"]["x"] > 0


def test_extraction_gate_not_run_without_file(tmp_path):
    gate = vg.gate_extraction_audit(tmp_path / "missing.json")
    assert gate["not_run"] and gate["passed"] is None


def test_ledger_as_of_filters_and_validates():
    rows = client.get("/api/v1/index/ledger", params={"as_of": "2026-09-27"}).json()["rows"]
    assert rows and all(r["as_of"] <= "2026-09-27" for r in rows)
    assert client.get("/api/v1/index/ledger", params={"as_of": "27-09-2026"}).status_code == 422


def test_levels_rebuilt_from_ledger():
    early = client.get("/api/v1/index/levels", params={"as_of": "2026-09-28"}).json()
    assert early["as_of"] == "2026-09-28"
    assert all(r["as_of"] <= "2026-09-28" and r["gci"] is not None for r in early["levels"])
    ids = {r["company_id"] for r in early["levels"]}
    assert "infy" in ids


def test_evidence_lookup_by_hash():
    doc = next(d for d in doc_store.list_documents(include_rejected=True) if d.get("content_hash"))
    body = client.get("/api/v1/index/evidence", params={"checksum": doc["content_hash"]}).json()
    assert body["doc_id"] == doc["doc_id"]
    assert "text" not in body
    assert client.get("/api/v1/index/evidence", params={"checksum": "0" * 64}).status_code == 404


def test_outcome_views_carry_quote_hashes():
    body = client.get("/api/companies/infy/gci").json()
    hashed = [o for o in body["outcomes"] if o.get("evidence_hashes", {}).get("guidance_quote_sha256")]
    assert hashed
    assert all(len(o["evidence_hashes"]["guidance_quote_sha256"]) == 64 for o in hashed)
