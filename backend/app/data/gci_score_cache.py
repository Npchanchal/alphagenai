"""Cached GCI scores for full India NSE/BSE listing universe."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_PATH = Path(__file__).with_name("gci_listing_scores.json")
_CACHE: Optional[Dict[str, Any]] = None


def cache_path() -> Path:
    return _PATH


_SCORE_FIELDS = (
    "gci_score",
    "gci_change_pct",
    "gci_change_horizon",
    "wow_pct",
    "mom_pct",
    "qoq_pct",
    "yoy_pct",
    "series_kind",
    "confidence_tier",
    "as_of",
)


def _strip_unscoreable(data: Dict[str, Any]) -> Dict[str, Any]:
    """Blank score fields for rows not backed by hand-labeled evidence (older cache files)."""
    from app.services.score_policy import is_scoreable

    scores = data.get("scores") or {}
    for row in scores.values():
        if is_scoreable(row.get("data_quality")):
            continue
        for key in _SCORE_FIELDS:
            row[key] = None
        row["by_metric"] = {}
        row["label_counts"] = {}
    data["scored_count"] = sum(1 for r in scores.values() if r.get("gci_score") is not None)
    return data


def load_cache(*, force: bool = False) -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    if _PATH.exists():
        _CACHE = _strip_unscoreable(json.loads(_PATH.read_text(encoding="utf-8")))
    else:
        from app.services.gci_scoring import algorithm_id

        _CACHE = {"version": 1, "algorithm": algorithm_id(), "scores": {}}
    return _CACHE


def save_cache(data: Dict[str, Any]) -> None:
    global _CACHE
    _CACHE = data
    _PATH.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def get_listing_score(company_id: str) -> Optional[Dict[str, Any]]:
    scores = load_cache().get("scores") or {}
    row = scores.get(company_id)
    return dict(row) if row else None


def refresh_listing_score(company_id: str) -> Dict[str, Any]:
    """Rewrite one listing row from the current outcomes. The composite is whatever the scorer returns."""
    from app.data.india_listings import india_equity_universe
    from app.data.seed import get_outcomes, list_companies
    from app.data.us_listings import us_equity_universe
    from app.services.coverage import coverage_status_for
    from app.services.gci_scoring import gci_trend_series, label_counts
    from app.services.guidance_flags import score_meta
    from app.services.score_policy import is_scoreable

    stock = next(
        (row for row in list(india_equity_universe()) + list(us_equity_universe()) if row["id"] == company_id),
        None,
    )
    seeded = next((row for row in list_companies() if row["id"] == company_id), None)
    if stock is None or seeded is None:
        raise KeyError(company_id)
    outcomes = get_outcomes(company_id)
    meta = score_meta(
        outcomes,
        scoreable=is_scoreable(seeded.get("data_quality")),
        company_id=company_id,
        data_quality=seeded.get("data_quality"),
    )
    gci = meta["gci_score"]
    trend = gci_trend_series(outcomes)
    change_pct = trend[-1].get("change_pct") if trend else None
    change_horizon = trend[-1].get("change_horizon") if trend else None
    from app.services.repository import gci_change_bundle_for

    bundle = gci_change_bundle_for(company_id) if gci is not None else {}
    horizons = {
        "wow_pct": None,
        "mom_pct": None,
        "qoq_pct": None,
        "yoy_pct": None,
        "series_kind": bundle.get("series_kind"),
    }
    if bundle.get("series_kind") == "citeable_pit":
        horizons = {key: bundle.get(key) for key in ("wow_pct", "mom_pct", "qoq_pct", "yoy_pct", "series_kind")}
    row = {
        "gci_score": gci,
        "coverage_status": coverage_status_for(
            company_id,
            score=gci,
            outcomes=outcomes,
            data_quality=seeded.get("data_quality"),
        ),
        "data_quality": seeded.get("data_quality", "demo_structured"),
        "ticker": stock.get("ticker") or company_id,
        "sector": stock.get("sector") or "Equity",
        "by_metric": meta["by_metric"],
        "context_metrics": meta["context_metrics"],
        "label_counts": label_counts(outcomes),
        "gci_change_pct": change_pct,
        "gci_change_horizon": change_horizon,
        "source": "seed",
        "confidence_tier": meta["confidence_tier"],
        "closed_periods": meta["closed_periods"],
        "metrics_scored": meta["metrics_scored"],
        "as_of": meta["as_of"],
        "algorithm_id": meta["algorithm_id"],
        **horizons,
    }
    from datetime import datetime, timezone

    data = load_cache(force=True)
    scores = data.setdefault("scores", {})
    scores[company_id] = row
    data["scored_count"] = sum(1 for item in scores.values() if item.get("gci_score") is not None)
    data["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_cache(data)
    return row


def clear_memory_cache() -> None:
    global _CACHE
    _CACHE = None


def build_india_gci_cache(*, limit: Optional[int] = None) -> Dict[str, Any]:
    """Score every India and S&P 500 listing with the active gci_scoring version.

    Each row includes calendar-aligned WoW / MoM / QoQ / YoY on the GCI level
    **only** when the company has a citeable outcome-as-of PIT series deep enough
    for deltas (rule `index-integrity`); otherwise horizons are ``None``.
    """
    from datetime import datetime, timezone

    from app.data.india_listings import india_equity_universe
    from app.data.seed import get_outcomes, list_companies
    from app.data.us_listings import us_equity_universe
    from app.services.gci_scoring import (
        algorithm_id,
        gci_trend_series,
        label_counts,
    )
    from app.services.guidance_flags import score_meta
    from app.services.coverage import coverage_status_for
    from app.services.provisional_gci import QUALITY, score_provisional
    from app.services.score_policy import is_scoreable

    algo = algorithm_id()

    seed_by_id = {c["id"]: c for c in list_companies()}
    scores: Dict[str, Any] = {}
    universe = list(india_equity_universe()) + list(us_equity_universe())
    if limit is not None and limit > 0:
        universe = universe[:limit]

    def _trend_change(trend: List[Dict[str, Any]]):
        if not trend:
            return None, None
        last = trend[-1]
        return last.get("change_pct"), last.get("change_horizon")

    def _horizon_fields(cid: str, gci: Optional[float], seeded: bool) -> Dict[str, Any]:
        empty = {
            "wow_pct": None,
            "mom_pct": None,
            "qoq_pct": None,
            "yoy_pct": None,
            "series_kind": None,
        }
        if gci is None or not seeded:
            return empty
        from app.services.repository import gci_change_bundle_for

        bundle = gci_change_bundle_for(cid)
        if bundle.get("series_kind") != "citeable_pit":
            return {**empty, "series_kind": bundle.get("series_kind")}
        return {
            "wow_pct": bundle.get("wow_pct"),
            "mom_pct": bundle.get("mom_pct"),
            "qoq_pct": bundle.get("qoq_pct"),
            "yoy_pct": bundle.get("yoy_pct"),
            "series_kind": "citeable_pit",
        }

    for stock in universe:
        cid = stock["id"]
        ticker = stock.get("ticker") or cid
        sector = stock.get("sector") or "Equity"
        seeded = seed_by_id.get(cid)
        if seeded is not None:
            outcomes = get_outcomes(cid)
            meta = score_meta(
                outcomes,
                scoreable=is_scoreable(seeded.get("data_quality")),
                company_id=cid,
                data_quality=seeded.get("data_quality"),
            )
            gci = meta["gci_score"]
            trend = gci_trend_series(outcomes)
            ch_pct, ch_h = _trend_change(trend)
            horizons = _horizon_fields(cid, gci, True)
            scores[cid] = {
                "gci_score": gci,
                "coverage_status": coverage_status_for(
                    cid,
                    score=gci,
                    outcomes=outcomes,
                    data_quality=seeded.get("data_quality"),
                ),
                "data_quality": seeded.get("data_quality", "demo_structured"),
                "ticker": ticker,
                "sector": sector,
                "by_metric": meta["by_metric"],
                "context_metrics": meta["context_metrics"],
                "label_counts": label_counts(outcomes),
                "gci_change_pct": ch_pct,
                "gci_change_horizon": ch_h,
                "source": "seed",
                "confidence_tier": meta["confidence_tier"],
                "closed_periods": meta["closed_periods"],
                "metrics_scored": meta["metrics_scored"],
                "as_of": meta["as_of"],
                "algorithm_id": meta["algorithm_id"],
                **horizons,
            }
        else:
            rep = score_provisional(cid, ticker, sector)
            ch_pct, ch_h = _trend_change(rep.get("trend") or [])
            gci = rep.get("gci_score")
            horizons = _horizon_fields(cid, gci, False)
            scores[cid] = {
                "gci_score": gci,
                "coverage_status": coverage_status_for(
                    cid, score=gci, data_quality=QUALITY
                ),
                "data_quality": QUALITY,
                "ticker": ticker,
                "sector": sector,
                "by_metric": rep.get("by_metric") or {},
                "label_counts": rep.get("label_counts") or {},
                "gci_change_pct": ch_pct,
                "gci_change_horizon": ch_h,
                "source": "provisional",
                "outcome_count": rep.get("outcome_count"),
                **horizons,
            }

    _strip_unscoreable({"scores": scores})
    scored_n = sum(1 for s in scores.values() if s.get("gci_score") is not None)
    with_yoy = sum(1 for s in scores.values() if s.get("yoy_pct") is not None)
    with_all = sum(
        1
        for s in scores.values()
        if all(s.get(k) is not None for k in ("wow_pct", "mom_pct", "qoq_pct", "yoy_pct"))
    )
    payload = {
        "version": 2,
        "algorithm": algo,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(scores),
        "scored_count": scored_n,
        "horizons_yoy_count": with_yoy,
        "horizons_full_count": with_all,
        "note": (
            f"A {algo} score needs both quotes on the cited filings (hand-labeled, or "
            "extracted and checked word for word). Other listings carry the reason they have no number."
        ),
        "scores": scores,
    }
    if os.environ.get("INTELLENS_SKIP_SCORE_CACHE_WRITE") != "1":
        save_cache(payload)
    else:
        global _CACHE
        _CACHE = payload
    return payload
