"""Alert generation — original kinds plus credibility drift / stale threads."""

from app.data.seed import get_data, reset_data, save_data
from app.services.repository import list_alerts


def setup_function():
    reset_data()


def teardown_module():
    reset_data()


def _outcome(**kw):
    base = {
        "period": "FY27",
        "metric": "revenue_growth_pct",
        "guided_value": 10.0,
        "guided_low": 9.0,
        "guided_high": 11.0,
        "actual_value": None,
        "guided_text": "synthetic guidance for alert tests",
        "confidence": 0.9,
        "speaker": "CFO",
        "thread_id": None,
        "dropped": False,
        "source_url": None,
        "source_ref": "test",
        "quote_span": None,
        "as_of": None,
    }
    base.update(kw)
    return base


def test_credibility_drift_fires_on_consecutive_gci_declines():
    data = get_data()
    rows = data["outcomes"]["infy"]
    # Two later periods with heavy misses drag cumulative GCI down twice in a row
    rows.append(_outcome(period="FY27", actual_value=4.0, as_of="2026-05-01"))
    rows.append(_outcome(period="FY28", actual_value=3.0, as_of="2027-05-01"))
    save_data()

    alerts = list_alerts()
    drift = [a for a in alerts if a.kind == "credibility_drift" and a.ticker == "INFY"]
    assert drift, "expected credibility_drift alert for INFY"
    assert "consecutive" in drift[0].message or "periods" in drift[0].message
    assert drift[0].severity in ("medium", "high")


def test_revision_alert_ignores_round_trip_to_the_same_band():
    data = get_data()
    data["outcomes"]["infy"] = [
        _outcome(
            period="FY24",
            thread_id="infy-roundtrip",
            guided_low=13.0,
            guided_high=15.0,
            guided_value=14.0,
            as_of="2024-04-01",
        ),
        _outcome(
            period="FY25",
            thread_id="infy-roundtrip",
            guided_low=16.0,
            guided_high=18.0,
            guided_value=17.0,
            as_of="2025-04-01",
        ),
        _outcome(
            period="FY26",
            thread_id="infy-roundtrip",
            guided_low=13.0,
            guided_high=15.0,
            guided_value=14.0,
            as_of="2026-04-01",
        ),
    ]
    save_data()
    revised = [a for a in list_alerts() if a.kind == "guidance_revised" and a.ticker == "INFY"]
    assert revised == []


def test_revision_alert_reports_a_net_raise():
    data = get_data()
    data["outcomes"]["infy"] = [
        _outcome(
            period="FY24",
            thread_id="infy-raise",
            guided_low=9.0,
            guided_high=11.0,
            guided_value=10.0,
            as_of="2024-04-01",
        ),
        _outcome(
            period="FY26",
            thread_id="infy-raise",
            guided_low=15.0,
            guided_high=17.0,
            guided_value=16.0,
            as_of="2026-04-01",
        ),
    ]
    save_data()
    revised = [a for a in list_alerts() if a.kind == "guidance_revised" and a.ticker == "INFY"]
    assert len(revised) == 1
    assert "raised" in revised[0].message
    assert "from 10" in revised[0].message and "to 16" in revised[0].message


def test_thread_stale_fires_for_unreiterated_pending_promise():
    data = get_data()
    rows = data["outcomes"]["infy"]
    # Pending promise last stated well before the company's latest disclosure
    rows.append(
        _outcome(
            period="FY26",
            metric="capex_inr_cr",
            guided_value=500.0,
            guided_low=450.0,
            guided_high=550.0,
            thread_id="infy-capex-stale",
            as_of="2024-06-01",
        )
    )
    save_data()

    alerts = list_alerts()
    stale = [a for a in alerts if a.kind == "thread_stale" and a.ticker == "INFY"]
    assert stale, "expected thread_stale alert for INFY"
    assert "has not reiterated its FY26" in stale[0].message
    assert "?" not in stale[0].message
    assert stale[0].severity == "medium"


def test_resolved_threads_do_not_raise_stale_alerts():
    alerts = list_alerts()
    # Seed data has older threads that resolved (met/dropped) — those must not flag
    stale_tickers = {a.ticker for a in alerts if a.kind == "thread_stale"}
    assert "ASIANPAINT" not in stale_tickers
