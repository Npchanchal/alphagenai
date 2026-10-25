"""Tests for MoM / QoQ / YoY change helpers."""

from app.services.changes import (
    change_bundle,
    enrich_metric_rows,
    enrich_value_series,
    infer_horizon,
    pct_change,
    period_rank,
    sort_document_listing,
    sort_evidence_listing,
)


def test_evidence_listing_is_latest_first():
    assert period_rank("FY26") > period_rank("Q1FY26") > period_rank("FY22")
    assert period_rank("not-a-period") is None
    rows = sort_evidence_listing(
        [
            {"period": "FY22", "metric": "revenue", "as_of": "2022-04-13"},
            {"period": "FY26", "metric": "margin", "as_of": "2026-04-01"},
            {"period": "FY26", "metric": "revenue", "as_of": "2026-04-16"},
            {"period": "FY26", "metric": "revenue", "as_of": "2026-01-15"},
            {"period": "n/a", "metric": "revenue", "as_of": "2026-04-16"},
        ]
    )
    assert [(r["period"], r["metric"], r["as_of"]) for r in rows] == [
        ("FY26", "revenue", "2026-04-16"),
        ("FY26", "margin", "2026-04-01"),
        ("FY26", "revenue", "2026-01-15"),
        ("FY22", "revenue", "2022-04-13"),
        ("n/a", "revenue", "2026-04-16"),
    ]
    docs = sort_document_listing(
        [
            {"period": "FY24", "date": "2024-04-01"},
            {"period": "FY26", "date": ""},
            {"period": "FY22", "date": "2026-05-01"},
        ]
    )
    assert [d["date"] or d["period"] for d in docs] == ["2026-05-01", "2024-04-01", "FY26"]


def test_pct_change():
    assert pct_change(110, 100) == 10.0
    assert pct_change(90, 100) == -10.0
    assert pct_change(None, 100) is None


def test_infer_horizon_fy_yoy():
    assert infer_horizon("FY24", "FY25") == "YoY"


def test_infer_horizon_qoq():
    assert infer_horizon("Q1FY25", "Q2FY25") == "QoQ"


def test_infer_horizon_mom():
    assert infer_horizon("2025-01", "2025-02") == "MoM"


def test_enrich_series_attaches_change():
    rows = enrich_value_series(
        [
            {"period": "FY23", "value": 50},
            {"period": "FY24", "value": 55},
            {"period": "FY25", "value": 60},
        ]
    )
    assert rows[0]["change_pct"] is None
    assert rows[1]["change_horizon"] == "YoY"
    assert rows[1]["change_pct"] == 10.0
    assert rows[2]["change_pct"] == round(100 * 5 / 55, 2)


def test_enrich_metric_rows():
    rows = enrich_metric_rows(
        [
            {"period": "FY24", "metric": "rev", "actual": 10, "management_guidance": 9, "street_consensus": 9.5},
            {"period": "FY25", "metric": "rev", "actual": 12, "management_guidance": 11, "street_consensus": 11.2},
        ]
    )
    fy25 = next(r for r in rows if r["period"] == "FY25")
    assert fy25["actual_change_horizon"] == "YoY"
    assert fy25["actual_change_pct"] == 20.0


def test_change_bundle_has_yoy():
    b = change_bundle(12.0, [("FY23", 10.0), ("FY24", 11.0), ("FY25", 12.0)])
    assert b["value"] == 12.0
    assert b["yoy_pct"] == round(100 * 1 / 11, 2)


def test_change_bundle_calendar_wow_mom_qoq_yoy():
    from app.services.changes import multi_horizon_gci_series

    series = multi_horizon_gci_series("testco", 80.0, weeks=56)
    b = change_bundle(80.0, series)
    assert b["value"] == 80.0
    assert b["wow_pct"] is not None
    assert b["mom_pct"] is not None
    assert b["qoq_pct"] is not None
    assert b["yoy_pct"] is not None


def test_multi_horizon_series_ends_at_anchor():
    from app.services.changes import multi_horizon_gci_series

    s = multi_horizon_gci_series("infy", 72.5, weeks=20)
    assert s[-1][1] == 72.5
    assert len(s) == 20
