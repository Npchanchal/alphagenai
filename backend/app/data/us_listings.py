"""S&P 500 listing master (cached JSON under app/data/listings/us_equity.json).

Refreshed by ``python -m app.jobs.refresh_index_lists --us``. Each row carries the
SEC CIK, so results releases can be pulled from EDGAR. A GCI is never invented
for these rows; a number appears only after both quotes check out in a filing.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_PATH = Path(__file__).with_name("listings") / "us_equity.json"

StockRow = Dict[str, Any]


def us_id(ticker: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (ticker or "").lower()).strip("_")
    return f"us_{slug or 'unknown'}"


def _load() -> Dict[str, Any]:
    if not _PATH.exists():
        return {"rows": [], "source": None, "as_of": None}
    return json.loads(_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def us_equity_universe() -> Tuple[StockRow, ...]:
    out = []
    for row in _load().get("rows") or []:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        out.append(
            {
                "id": us_id(ticker),
                "market_id": "US",
                "index_ids": list(row.get("index_ids") or ["SPX"]),
                "name": row.get("name") or ticker,
                "ticker": ticker,
                "sector": row.get("sector") or "Equity",
                "data_quality": "listing_master",
                "cik": str(row.get("cik") or "").zfill(10) if row.get("cik") else None,
                "exchange": "US",
            }
        )
    return tuple(out)


def us_listing_meta() -> Dict[str, Any]:
    raw = _load()
    return {"count": len(raw.get("rows") or []), "source": raw.get("source"), "as_of": raw.get("as_of")}


@lru_cache(maxsize=1)
def _by_id() -> Dict[str, StockRow]:
    return {r["id"]: r for r in us_equity_universe()}


def find_us_listing(company_id: str) -> Optional[StockRow]:
    row = _by_id().get((company_id or "").strip())
    return dict(row) if row else None


def clear_us_listing_caches() -> None:
    us_equity_universe.cache_clear()
    _by_id.cache_clear()
