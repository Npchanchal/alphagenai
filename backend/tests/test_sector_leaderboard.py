"""Sector leaderboard counts published GCI only, and agrees with the published count."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import repository
from app.services.score_policy import SECTOR_AVG_MIN_NAMES

client = TestClient(app)


def test_leaderboard_counts_the_same_names_as_meta():
    meta = client.get("/api/meta").json()
    board = client.get("/api/sectors/leaderboard?market=IN").json()
    assert board["published_count"] == meta["published_gci_count"]
    assert board["min_names"] == SECTOR_AVG_MIN_NAMES
    names = [n["id"] for s in board["sectors"] for n in s["names"]]
    assert len(names) == len(set(names)) == board["published_count"]


def test_average_withheld_below_minimum_and_best_needs_rankable_tier():
    board = client.get("/api/sectors/leaderboard?market=IN").json()
    for s in board["sectors"]:
        if s["count"] < SECTOR_AVG_MIN_NAMES:
            assert s["avg"] is None and s["best"] is None
        tiers = {n["confidence_tier"] for n in s["names"]}
        if s["best"] is not None:
            assert tiers & {"established", "deep"}


def test_index_filter_keeps_only_members():
    from app.data import markets as markets_data

    members = {s["id"] for s in markets_data.constituents_readonly("SENSEX")}
    board = client.get("/api/sectors/leaderboard?market=IN&index=SENSEX").json()
    assert all(n["id"] in members for s in board["sectors"] for n in s["names"])


def test_average_and_best_once_enough_names(monkeypatch):
    companies = [
        {"id": f"c{i}", "ticker": f"C{i}", "name": f"Co {i}", "sector": "Banks", "market_id": "IN", "data_quality": "hand_labeled"}
        for i in range(3)
    ]
    scores = {"c0": (80.0, "provisional"), "c1": (70.0, "established"), "c2": (60.0, "deep")}
    monkeypatch.setattr(repository, "list_companies", lambda: companies)
    monkeypatch.setattr(repository, "get_outcomes", lambda cid: [cid])
    monkeypatch.setattr(
        repository,
        "score_meta",
        lambda outcomes, **_: {"gci_score": scores[outcomes[0]][0], "confidence_tier": scores[outcomes[0]][1]},
    )
    [banks] = repository.sector_leaderboard(market="IN")
    assert banks["avg"] == 70.0
    assert banks["count"] == 3
    assert banks["best"]["id"] == "c1"
