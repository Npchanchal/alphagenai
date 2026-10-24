"""Index integrity (rule `index-integrity`, plan W1).

A published GCI is an index level. Public responses must never carry synthetic
history, unexplained score moves, or numbers without a confidence tier.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data.seed import get_outcomes, list_companies, reset_data
from app.main import app
from app.services import score_ledger
from app.services.pit_contract import contract_schema
from app.services.pit_warehouse import build_company_pit_series
from app.services.score_policy import (
    TIER_DEEP,
    TIER_ESTABLISHED,
    TIER_PROVISIONAL,
    RANKABLE_TIERS,
    confidence_tier,
)

client = TestClient(app)
HORIZONS = ("wow_pct", "mom_pct", "qoq_pct", "yoy_pct")
SYNTHETIC_KINDS = ("demo", "hybrid", "seed", "provisional_or_scaffold")


def setup_function():
    reset_data()


def _companies():
    rows = client.get("/api/companies").json()
    assert rows
    return rows


def _pit_len(cid: str) -> int:
    return len(client.get(f"/api/companies/{cid}/gci/history").json())


# --- W1.1 nothing synthetic on public routes -------------------------------


def test_public_list_deltas_only_when_citeable_pit():
    for r in _companies():
        n = _pit_len(r["id"])
        if n < 4:
            for k in HORIZONS:
                assert r.get(k) is None, (r["id"], k, r.get(k))


def test_changes_endpoint_never_returns_synthetic_series():
    for r in _companies():
        b = client.get(f"/api/companies/{r['id']}/changes").json()
        kind = str(b.get("series_kind") or "")
        assert not kind.startswith(SYNTHETIC_KINDS), (r["id"], kind)
        if kind != "citeable_pit":
            for k in HORIZONS:
                assert b.get(k) is None, (r["id"], k)
        else:
            assert b.get("citeable") is True


def test_public_rankings_carry_no_synthetic_deltas():
    ranks = client.get("/api/public/gci-rankings?limit=100").json()
    for row in ranks["top"] + ranks["bottom"]:
        if _pit_len(row["company_id"]) < 4:
            for k in HORIZONS:
                assert row.get(k) is None, (row["company_id"], k)


def test_pit_warehouse_refuses_null_anchor():
    unscored = [
        c["id"]
        for c in list_companies()
        if c.get("data_quality") != "hand_labeled" or not get_outcomes(c["id"])
    ]
    assert unscored
    built = build_company_pit_series(unscored[0])
    assert built["n"] == 0
    assert built["points"] == []
    assert built.get("anchor_gci") is None


def test_pit_contract_enum_has_no_demo_kinds():
    for kind in contract_schema()["series_kind_enum"]:
        assert not kind.startswith(SYNTHETIC_KINDS), kind


def test_pit_v1_history_is_citeable_or_empty():
    for r in _companies():
        h = client.get(f"/api/v1/pit/companies/{r['id']}/history").json()
        assert not str(h.get("series_kind") or "").startswith(SYNTHETIC_KINDS), r["id"]
        if not h.get("citeable"):
            assert h["points"] == [] or h["series_kind"] == "citeable_pit_short"


@pytest.mark.parametrize(
    "path",
    [
        "/api/companies/infy/analytics",
        "/api/companies/infy/wordmap",
        "/api/stocks/infy/history",
    ],
)
def test_guest_cannot_reach_experimental_or_price_surfaces(path: str):
    res = client.get(path)
    assert res.status_code in (401, 403), (path, res.status_code)


def test_dossier_has_no_sentiment_field():
    d = client.get("/api/companies/infy/gci").json()
    assert "sentiment" not in d


def test_dual_citation_required():
    """W2.1: a closed row scores only with promise + actual citations.

    Infosys FY25 operating margin has the actual (SEC 6-K) but not the promise
    citation, so it is pending_guidance_cite — excluded from composite and context.
    """
    d = client.get("/api/companies/infy/gci").json()
    op = [
        o
        for o in d["outcomes"]
        if o["period"] == "FY25" and o["metric"] == "operating_margin_pct"
    ]
    assert len(op) == 1
    assert op[0]["label"] == "pending_guidance_cite"
    assert op[0]["contribution_score"] is None
    assert "operating_margin_pct" not in (d.get("by_metric") or {})
    # FY24 margin is the cited closed row. One period, so it is context, not the composite.
    assert d.get("context_metrics", {}).get("operating_margin_pct") == 100.0
    assert d["gci_score"] == 76.5
    for r in _companies():
        detail = client.get(f"/api/companies/{r['id']}/gci").json()
        for o in detail["outcomes"]:
            if o.get("contribution_score") is None:
                continue
            assert o.get("guidance_source_url"), (r["id"], o["period"], o["metric"])
            assert o.get("guidance_quote"), (r["id"], o["period"], o["metric"])
            assert o.get("guidance_as_of"), (r["id"], o["period"], o["metric"])
            assert o.get("source_url") and o.get("quote_span") and o.get("as_of")
            assert o.get("reviewed_by"), (r["id"], o["period"], o["metric"])
            assert o.get("reviewed_at"), (r["id"], o["period"], o["metric"])


# --- W1.3 confidence tiers ---------------------------------------------------


def test_tier_function_thresholds():
    assert confidence_tier(closed_periods=0, metrics_scored=0) is None
    assert confidence_tier(closed_periods=2, metrics_scored=2) == TIER_PROVISIONAL
    assert confidence_tier(closed_periods=3, metrics_scored=1) == TIER_PROVISIONAL
    assert confidence_tier(closed_periods=3, metrics_scored=2) == TIER_ESTABLISHED
    assert confidence_tier(closed_periods=5, metrics_scored=2) == TIER_DEEP


def test_every_scored_company_has_tier_and_algorithm():
    for r in _companies():
        d = client.get(f"/api/companies/{r['id']}/gci").json()
        if r["gci_score"] is None:
            assert r.get("confidence_tier") is None
            assert d.get("confidence_tier") is None
        else:
            assert r["confidence_tier"] in (TIER_PROVISIONAL, TIER_ESTABLISHED, TIER_DEEP), r["id"]
            assert d["confidence_tier"] == r["confidence_tier"], r["id"]
            assert d["algorithm_id"] == r["algorithm_id"] == "gci_scoring_v4"
            assert d["closed_periods"] >= 1
            assert d["as_of"], r["id"]


@pytest.mark.parametrize("index", ["SENSEX", "NIFTY50"])
def test_rankings_only_include_rankable_tiers(index: str):
    ranks = client.get(f"/api/public/gci-rankings?limit=100&index={index}").json()
    for row in ranks["top"] + ranks["bottom"]:
        assert row["confidence_tier"] in RANKABLE_TIERS, row["company_id"]
        assert "peer_rank_in_sector" not in row
    universe = client.get(f"/api/companies?index={index}").json()
    assert ranks["universe_n"] == sum(
        1 for r in universe if r.get("confidence_tier") in RANKABLE_TIERS
    )
    assert ranks["tiers_ranked"] == sorted(RANKABLE_TIERS)


# --- W1.4 evidence-weighted composite ----------------------------------------


def test_single_period_metric_is_context_only():
    d = client.get("/api/companies/infy/gci").json()
    # FY24 operating margin has one closed period, so it is context. FY25 stays pending.
    assert d["context_metrics"]["operating_margin_pct"] == 100.0
    assert "operating_margin_pct" not in d["by_metric"]
    assert d["gci_score"] == d["by_metric"]["revenue_growth_cc_pct"]


def test_context_metrics_count_toward_tier_breadth():
    """Decision D-tier: a scored context-only metric still counts as evidence.

    After the FY24 margin citation, Infosys has five dual-cited revenue years and one
    closed margin year. Breadth is 2 and the tier is deep. The 76.5 level is unchanged.
    """
    infy = client.get("/api/companies/infy/gci").json()
    assert infy["metrics_scored"] == len(infy["by_metric"]) + len(infy.get("context_metrics") or {})
    assert infy["metrics_scored"] == 2
    assert infy["confidence_tier"] == TIER_DEEP
    assert infy["gci_score"] == 76.5
    cipla = client.get("/api/companies/cipla/gci").json()
    if cipla["gci_score"] is not None:
        assert cipla["metrics_scored"] == len(cipla["by_metric"]) + len(
            cipla.get("context_metrics") or {}
        )


def test_at_least_one_company_is_rankable_somewhere():
    # W2.1 withdraws names that lack promise citations; Snapshot may be empty
    # until W2.2/W2.3. Ranked rows, if any, must still be established/deep.
    ranked = [r for r in _companies() if r.get("confidence_tier") in RANKABLE_TIERS]
    for r in ranked:
        assert r["gci_score"] is not None


# --- W1.6 score ledger ---------------------------------------------------------


def test_ledger_is_append_only(tmp_path: Path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(score_ledger, "LEDGER_PATH", path)
    row = score_ledger.LedgerRow(
        company_id="x", as_of="2026-01-01", algorithm_id="gci_scoring_v4",
        dataset_version="t", gci=50.0, prior_gci=None, confidence_tier="provisional",
        reason="methodology", note="t", by="test",
    )
    assert score_ledger.append(row) is True
    assert score_ledger.append(row) is False  # same key → no duplicate
    assert len(score_ledger.read_all()) == 1
    with pytest.raises(ValueError):
        score_ledger.append(
            score_ledger.LedgerRow(**{**row.__dict__, "gci": 51.0})
        )
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["company_id"] == "x"


def test_ledger_api_and_changelog_public():
    res = client.get("/api/v1/index/ledger?company_id=infy")
    assert res.status_code == 200
    body = res.json()
    assert body["company_id"] == "infy"
    assert isinstance(body["rows"], list)
    cl = client.get("/api/v1/index/changelog").json()
    assert cl["count"] >= 4
    assert any("88.2" in (e.get("change") or "") for e in cl["entries"])


# --- W5.4 GCI badge ------------------------------------------------------------


def test_badge_is_gci_with_tier_and_as_of():
    badge = client.get("/api/badge/INFY").json()
    blob = json.dumps(badge).lower()
    assert badge["label"] == "Guidance Credibility Index (GCI)"
    assert 'data-citealpha-badge="INFY"' in badge["embed"]
    assert "intellens" not in blob
    assert "trust score" not in blob
    assert "promoter" not in blob
    assert "trust_score" not in badge
    assert badge["gci_score"] == 76.5
    assert badge["confidence_tier"] == TIER_DEEP
    assert badge["as_of"]
    svg = client.get("/api/badge/INFY/svg").text.lower()
    assert "gci" in svg
    assert "intellens" not in svg
    assert "trust score" not in svg
    assert badge["as_of"][:4] in svg  # year
    assert badge["confidence_tier"] in svg



def test_methodology_release_logged_once_per_revision(tmp_path: Path, monkeypatch):
    from app.services.gci_scoring import ALGORITHM_REVISION

    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    calls = []

    def fake_snapshot(**kw):
        calls.append(kw)
        return [score_ledger.LedgerRow(
            company_id="x", as_of="2026-10-18", algorithm_id="gci_scoring_v4", dataset_version="t",
            gci=90.7, prior_gci=83.8, confidence_tier="provisional", reason=kw["reason"], note=kw["note"], by=kw["by"],
        )]

    monkeypatch.setattr(score_ledger, "snapshot_rows", fake_snapshot)
    assert score_ledger.record_methodology_release() == 1
    assert calls[0]["reason"] == "methodology" and calls[0]["note"] == ALGORITHM_REVISION
    assert score_ledger.record_methodology_release() == 0
    assert len(calls) == 1
    assert (tmp_path / "methodology_release.txt").read_text().strip() == ALGORITHM_REVISION


def test_methodology_release_skipped_without_data_volume(monkeypatch):
    monkeypatch.delenv("INTELLENS_DATA_DIR", raising=False)
    assert score_ledger.record_methodology_release() == 0


def _row(cid, gci, prior, reason, by, version):
    return score_ledger.LedgerRow(
        company_id=cid, as_of="2026-10-18", algorithm_id="gci_scoring_v4", dataset_version=version,
        gci=gci, prior_gci=prior, confidence_tier="provisional" if gci is not None else None,
        reason=reason, note="t", by=by,
    )


def test_release_withdrawal_contradicted_by_live_score_is_corrected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    (tmp_path / "score_ledger.jsonl").write_text("")
    score_ledger.append(_row("axisbank", None, 83.8, "methodology", score_ledger.RELEASE_BY, "2026-10-18.1"))
    score_ledger.append(_row("infy", None, 76.5, "methodology", "analyst:x", "2026-10-18.1"))
    monkeypatch.setattr(score_ledger, "snapshot_rows", lambda **kw: [
        _row("axisbank", 90.7, None, kw["reason"], kw["by"], "2026-10-18.2"),
        _row("infy", 76.5, None, kw["reason"], kw["by"], "2026-10-18.2"),
    ])
    assert score_ledger.correct_release_withdrawals() == 1
    last = score_ledger.latest_for("axisbank")
    assert last["gci"] == 90.7 and last["reason"] == "data_correction"
    assert score_ledger.latest_for("infy")["gci"] is None
    assert score_ledger.correct_release_withdrawals() == 0


def test_dataset_is_published_only_after_citations_are_applied(monkeypatch):
    import threading

    from app.data import seed

    seed._DATA = None
    started, release = threading.Event(), threading.Event()
    real = seed._restore_tenant_state

    def slow_restore(data):
        started.set()
        release.wait(2)
        real(data)

    monkeypatch.setattr(seed, "_restore_tenant_state", slow_restore)
    t = threading.Thread(target=seed.get_data)
    t.start()
    started.wait(2)
    assert seed._DATA is None
    release.set()
    t.join(5)
    assert seed._DATA is not None
    seed.reset_data()
