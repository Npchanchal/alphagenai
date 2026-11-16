"""A promise cite that is not earlier than the result stays out of the score and the met count."""

from app.services.gci_scoring import GuidanceOutcome, classify_outcome, label_counts, outcome_score_v4
from app.services.score_policy import is_not_prior_promise


def _row(**kw) -> GuidanceOutcome:
    base = dict(
        period="FY25",
        metric="operating_margin_pct",
        guided_value=21.0,
        actual_value=21.1,
        guided_text="20-22",
        guided_low=20.0,
        guided_high=22.0,
        source_url="https://www.sec.gov/Archives/edgar/data/1/result.htm",
        quote_span="margin 21.1%",
        as_of="2025-04-17",
        guidance_source_url="https://www.sec.gov/Archives/edgar/data/1/guide.htm",
        guidance_quote="margin 20% to 22%",
        guidance_as_of="2024-04-18",
        reviewed_by="analyst:nv",
        reviewed_at="2026-09-29",
    )
    base.update(kw)
    return GuidanceOutcome(**base)


def test_promise_after_result_is_not_a_met():
    late = _row(guidance_as_of="2026-07-28")
    assert is_not_prior_promise(late)
    assert classify_outcome(late).value == "not_prior_promise"
    assert outcome_score_v4(late) is None
    counts = label_counts([late, _row()])
    assert counts.get("met") == 1
    assert counts.get("not_prior_promise") == 1


def test_same_filing_is_not_a_prior_promise():
    same = _row(
        guidance_source_url="https://www.sec.gov/Archives/edgar/data/1/result.htm#page",
        guidance_as_of="2025-04-17",
    )
    assert is_not_prior_promise(same)
    assert classify_outcome(same).value == "not_prior_promise"
    assert outcome_score_v4(same) is None


def test_india_alerts_stay_on_india_companies():
    from app.data.seed import list_companies
    from app.services.repository import list_alerts

    markets = {c["id"]: str(c.get("market_id") or "IN").upper() for c in list_companies()}
    alerts = list_alerts(market="IN")
    assert alerts
    assert all(markets.get(a.company_id, "IN") == "IN" for a in alerts)


def test_reading_room_lists_every_published_india_score():
    from app.services.repository import list_published_companies

    rows = list_published_companies()
    ids = {r.id for r in rows}
    assert "infy" in ids and "cipla" in ids
    assert all((r.market_id or "IN") == "IN" for r in rows)
    assert all(r.gci_score is not None for r in rows)


def test_distinct_earlier_filing_still_scores():
    row = _row()
    assert not is_not_prior_promise(row)
    assert classify_outcome(row).value == "met"
    assert outcome_score_v4(row) == 100
