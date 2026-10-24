"""Commitment Record rules, extraction and store (US-A01, US-A02). Fixture text is a stub, not company data."""

import json

import pytest

from app.services import commitment_extract, commitment_store
from app.services import commitments as rules

STUB_URL = "https://example.invalid/stub-concall.pdf"


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))


def _row(**kw):
    base = {
        "company_id": "infy",
        "type": "capacity",
        "subject": "Stub plant commissioning",
        "outcome": "Stub plant is commissioned",
        "due_period": "Q3 FY26",
        "quote": "We expect the stub plant to be commissioned in Q3 FY26.",
        "source_url": STUB_URL,
        "as_of": "2025-05-01",
    }
    base.update(kw)
    return base


@pytest.mark.parametrize(
    "period,end",
    [
        ("FY26", "2026-03-31"),
        ("FY2027", "2027-03-31"),
        ("Q1 FY26", "2025-06-30"),
        ("Q3 FY26", "2025-12-31"),
        ("Q4 FY26", "2026-03-31"),
        ("H1 FY27", "2026-09-30"),
        ("H2 FY27", "2027-03-31"),
        ("2026-12-31", "2026-12-31"),
        ("soon", None),
        ("2026-02-30", None),
    ],
)
def test_period_end_indian_fiscal(period, end):
    assert rules.period_end(period) == end


def test_validate_requires_quote_source_and_readable_due():
    assert rules.validate_commitment(_row()) == []
    errs = rules.validate_commitment(_row(quote="", due_period="someday", type="vibes"))
    assert {"missing_quote", "unreadable_due_period", "unknown_type"} <= set(errs)


def test_transition_needs_review_proof_and_open_state():
    row = {**_row(), "id": "c1", "state": "open", "review_status": "unreviewed"}
    assert "not_reviewed" in rules.validate_transition(row, "delivered", {})
    row["review_status"] = "accepted"
    assert "proof_missing_quote" in rules.validate_transition(row, "delivered", {})
    proof = {"quote": "The stub plant was commissioned.", "source_url": STUB_URL, "as_of": "2026-01-20"}
    closed = rules.apply_transition(row, "delivered", proof, reviewer="r1", reviewed_at="t")
    assert closed["state"] == "delivered" and closed["history"][0]["reviewer"] == "r1"
    assert row["state"] == "open"
    assert "not_open" in rules.validate_transition(closed, "missed", proof)


def test_quiet_drop_needs_two_cycles():
    row = {**_row(), "id": "c1", "state": "open", "review_status": "accepted"}
    assert "needs_two_cycles" in rules.validate_transition(row, "quietly_dropped", {"cycles_checked": 1})
    assert rules.validate_transition(
        row, "quietly_dropped", {"cycles_checked": 2, "last_mentioned_as_of": "2025-05-01"}
    ) == []


def test_detect_quiet_drops_two_silent_cycles_after_last_mention():
    c = {**_row(), "id": "c1", "state": "open", "review_status": "accepted"}
    cycles = [
        {"as_of": "2025-08-01", "mentions": {"c1"}},
        {"as_of": "2025-11-01", "mentions": set()},
    ]
    assert rules.detect_quiet_drops([c], cycles) == []
    cycles.append({"as_of": "2026-02-01", "mentions": set()})
    [p] = rules.detect_quiet_drops([c], cycles)
    assert p["last_mentioned_as_of"] == "2025-08-01" and p["cycles_checked"] == 2


def test_unreviewed_rows_never_proposed_for_drop_or_counted():
    c = {**_row(), "id": "c1", "state": "open", "review_status": "unreviewed"}
    cycles = [{"as_of": "2025-11-01", "mentions": set()}, {"as_of": "2026-02-01", "mentions": set()}]
    assert rules.detect_quiet_drops([c], cycles) == []
    assert rules.delivery_summary([c], as_of="2026-06-30")["due"] == 0


def test_summary_is_plain_counts_not_an_index_level():
    rows = [
        {**_row(), "state": s, "review_status": "accepted", "due_period": "FY25"}
        for s in ("delivered", "delivered", "delivered_late", "missed", "quietly_dropped", "open")
    ]
    s = rules.delivery_summary(rows, as_of="2025-06-30")
    assert s["due"] == 6 and s["delivered"] == 3
    assert s["sentence"] == (
        "Delivered 3 of 6 dated commitments that have fallen due; 1 late, 1 missed, "
        "1 dropped without explanation, 1 awaiting a result filing."
    )
    assert "gci" not in json.dumps(s).lower()


STUB_TEXT = (
    "Revenue grew last year. We expect the second stub line to be commissioned in Q3 FY26. "
    "Our aim is to be net-debt free by FY27. We remain optimistic about demand. "
    "We plan to launch 12 stub products by March 2026."
)


def test_heuristic_extract_quotes_are_verbatim_and_dated():
    rows = commitment_extract.heuristic_extract(STUB_TEXT)
    got = {(r["type"], r["due_period"]) for r in rows}
    assert ("capacity", "Q3 FY26") in got
    assert ("balance_sheet", "FY27") in got
    assert ("launch", "2026-03-31") in got
    assert all(rules.quote_is_verbatim(r["quote"], STUB_TEXT) for r in rows)
    assert not any("optimistic" in r["quote"] for r in rows)


def test_llm_extract_drops_invented_quotes(monkeypatch):
    from app.services import llm_client

    fake = [
        {"type": "capacity", "subject": "line", "outcome": "x", "due_period": "Q3 FY26",
         "quote": "We expect the second stub line to be commissioned in Q3 FY26."},
        {"type": "capex", "subject": "made up", "outcome": "x", "due_period": "FY27",
         "quote": "We will spend 5,000 crore on stub capex in FY27."},
        {"type": "capacity", "subject": "bad date", "outcome": "x", "due_period": "later",
         "quote": "Our aim is to be net-debt free by FY27."},
    ]
    monkeypatch.setattr(llm_client, "chat_completion", lambda *a, **k: json.dumps(fake))
    rows = commitment_extract.llm_extract(STUB_TEXT)
    assert [r["subject"] for r in rows] == ["line"]


def test_store_propose_review_transition_and_public_view():
    res = commitment_store.propose([_row(), _row(), _row(quote="")], proposed_by="labeler")
    assert len(res["added"]) == 1
    reasons = [s["errors"] for s in res["skipped"]]
    assert ["duplicate"] in reasons and any("missing_quote" in e for e in reasons)
    cid = res["added"][0]
    assert commitment_store.list_commitments("infy") == []
    assert len(commitment_store.list_commitments("infy", include_unreviewed=True)) == 1
    commitment_store.review(cid, decision="accepted", reviewer="rev1")
    with pytest.raises(ValueError):
        commitment_store.review(cid, decision="accepted", reviewer="rev1")
    proof = {"quote": "The stub plant was commissioned.", "source_url": STUB_URL, "as_of": "2026-01-20"}
    row = commitment_store.transition(cid, new_state="delivered", proof=proof, reviewer="rev1")
    assert row["state"] == "delivered"
    view = commitment_store.company_view("infy", include_unreviewed=False, as_of="2026-06-30")
    assert view["summary"]["delivered"] == 1
    assert view["commitments"][0]["state_label"] == "Delivered"
