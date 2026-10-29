"""Listing masters outside India (cached JSON under app/data/listings/{market}_equity.json).

US: the S&P 500, refreshed by ``python -m app.jobs.refresh_index_lists --us``; each row
carries the SEC CIK, so results releases can be pulled from EDGAR. Other markets
(GB, JP, HK, CN, EU, SG, AU, KR, BR, CA): their headline index lists, refreshed by
``--world``. A GCI is never invented for these rows; a number appears only after
both quotes check out in a filing.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DIR = Path(__file__).with_name("listings")

StockRow = Dict[str, Any]


def listing_id(market_id: str, ticker: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (ticker or "").lower()).strip("_")
    return f"{market_id.lower()}_{slug or 'unknown'}"


def us_id(ticker: str) -> str:
    return listing_id("US", ticker)


def _path(market_id: str) -> Path:
    return _DIR / f"{market_id.lower()}_equity.json"


def _load(market_id: str = "US") -> Dict[str, Any]:
    path = _path(market_id)
    if market_id.upper() == "IN" or not path.exists():
        return {"rows": [], "source": None, "as_of": None}
    return json.loads(path.read_text(encoding="utf-8"))


def world_market_ids() -> List[str]:
    """Markets with a listing file here. India's NSE/BSE masters live in ``india_listings``."""
    return sorted(p.name[:2].upper() for p in _DIR.glob("??_equity.json") if p.name[:2] != "in")


@lru_cache(maxsize=None)
def world_universe(market_id: str) -> Tuple[StockRow, ...]:
    mid = market_id.upper()
    out = []
    for row in _load(mid).get("rows") or []:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        out.append(
            {
                "id": listing_id(mid, ticker),
                "market_id": mid,
                "index_ids": list(row.get("index_ids") or []),
                "name": row.get("name") or ticker,
                "ticker": ticker,
                "sector": row.get("sector") or "Equity",
                "data_quality": "listing_master",
                "cik": str(row.get("cik") or "").zfill(10) if row.get("cik") else None,
                "exchange": row.get("exchange") or mid,
            }
        )
    return tuple(out)


def us_equity_universe() -> Tuple[StockRow, ...]:
    return world_universe("US")


def world_indexes(market_id: str) -> List[str]:
    """Indexes whose full membership is in the file; the rest hold only anchor tags."""
    raw = _load(market_id.upper())
    if raw.get("indexes"):
        return list(raw["indexes"])
    seen: List[str] = []
    for row in raw.get("rows") or []:
        for ix in row.get("index_ids") or []:
            if ix not in seen:
                seen.append(ix)
    return seen


def world_listing_meta(market_id: str) -> Dict[str, Any]:
    raw = _load(market_id.upper())
    return {"count": len(raw.get("rows") or []), "source": raw.get("source"), "as_of": raw.get("as_of")}


def us_listing_meta() -> Dict[str, Any]:
    return world_listing_meta("US")


@lru_cache(maxsize=1)
def _by_id() -> Dict[str, StockRow]:
    return {r["id"]: r for mid in world_market_ids() for r in world_universe(mid)}


def find_world_listing(company_id: str) -> Optional[StockRow]:
    """Any listing outside India, by company id (``us_aapl``, ``gb_azn``, ``jp_7203``)."""
    row = _by_id().get((company_id or "").strip())
    return dict(row) if row else None


def find_us_listing(company_id: str) -> Optional[StockRow]:
    row = find_world_listing(company_id)
    return row if row and row["market_id"] == "US" else None


def clear_us_listing_caches() -> None:
    world_universe.cache_clear()
    _by_id.cache_clear()
