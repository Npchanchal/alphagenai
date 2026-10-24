"""Real NSE / BSE equity masters (cached JSON under app/data/listings/).

GCI is NOT invented for these rows — only Sensex/Nifty seed outcomes score.

One row per scrip. Every India index (SENSEX, NIFTY50, NIFTYBANK, NIFTY500,
NSE_ALL, BSE_ALL, IN1000) is a membership tag on that row, never a separate record, so a
dual-listed or multi-index name is stored, scored and walked exactly once.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.data.universe import (
    NIFTY50_BEYOND_SENSEX,
    OFFICIAL_NIFTY50_TICKERS,
    SENSEX_30,
    deep_data_quality,
)

_LISTINGS = Path(__file__).with_name("listings")

StockRow = Dict[str, Any]

IN1000_CAP = 1000
INDIA_INDEX_IDS = ("SENSEX", "NIFTY50", "NIFTYBANK", "NIFTY500", "NSE_ALL", "BSE_ALL", "IN1000")
NIFTYBANK_TICKERS = frozenset(
    {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN", "INDUSINDBK"}
)


def _slug(ticker: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (ticker or "").lower()).strip("_")
    return s or "unknown"


@lru_cache(maxsize=1)
def _sensex_by_ticker() -> Dict[str, Tuple[str, str, str, str]]:
    return {t.upper(): (cid, name, t, sector) for cid, name, t, sector in SENSEX_30}


@lru_cache(maxsize=1)
def _nifty_extra_by_ticker() -> Dict[str, Tuple[str, str, str, str]]:
    return {t.upper(): (cid, name, t, sector) for cid, name, t, sector in NIFTY50_BEYOND_SENSEX}


def _load_json(name: str) -> Dict[str, Any]:
    path = _LISTINGS / name
    if not path.exists():
        return {"count": 0, "rows": [], "source": None}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def nse_meta() -> Dict[str, Any]:
    raw = _load_json("nse_equity.json")
    return {"count": int(raw.get("count") or len(raw.get("rows") or [])), "source": raw.get("source")}


@lru_cache(maxsize=1)
def nifty500_by_symbol() -> Dict[str, Dict[str, Any]]:
    rows = _load_json("nifty500.json").get("rows") or []
    return {str(r.get("symbol") or "").upper(): r for r in rows if r.get("symbol")}


@lru_cache(maxsize=1)
def bse_meta() -> Dict[str, Any]:
    raw = _load_json("bse_equity.json")
    return {"count": int(raw.get("count") or len(raw.get("rows") or [])), "source": raw.get("source")}


def _resolve_id_name_sector(symbol: str, name: str) -> Tuple[str, str, str, str]:
    """Return (id, name, ticker, sector) preferring Sensex / Nifty seed ids."""
    sym = (symbol or "").upper()
    if sym in _sensex_by_ticker():
        return _sensex_by_ticker()[sym]
    if sym in _nifty_extra_by_ticker():
        return _nifty_extra_by_ticker()[sym]
    return (f"nse_{_slug(sym)}", name or sym, sym, "Equity")


@lru_cache(maxsize=1)
def india_equity_universe() -> Tuple[StockRow, ...]:
    """Merged NSE + BSE equities; dual-listed share one id via ISIN/ticker."""
    nse_raw = _load_json("nse_equity.json").get("rows") or []
    bse_raw = _load_json("bse_equity.json").get("rows") or []

    by_id: Dict[str, StockRow] = {}
    isin_to_id: Dict[str, str] = {}
    ticker_to_id: Dict[str, str] = {}

    for row in nse_raw:
        symbol = (row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        cid, name, ticker, sector = _resolve_id_name_sector(symbol, row.get("name") or symbol)
        quality = (
            deep_data_quality(cid)
            if cid in {x[0] for x in SENSEX_30} or cid in {x[0] for x in NIFTY50_BEYOND_SENSEX}
            else "listing_master"
        )
        isin = (row.get("isin") or "").strip().upper()
        if cid in by_id or (isin and isin in isin_to_id):
            continue
        entry: StockRow = {
            "id": cid,
            "market_id": "IN",
            "index_ids": ["NSE_ALL"],
            "name": name,
            "ticker": ticker,
            "sector": sector,
            "data_quality": quality,
            "exchange": "NSE",
            "isin": isin or None,
        }
        by_id[cid] = entry
        ticker_to_id.setdefault(ticker.upper(), cid)
        if isin:
            isin_to_id[isin] = cid

    for row in bse_raw:
        isin = (row.get("isin") or "").strip().upper()
        symbol = (row.get("symbol") or "").strip().upper()
        name = (row.get("name") or symbol or row.get("scrip_code") or "").strip()
        code = str(row.get("scrip_code") or "").strip()

        existing_id: Optional[str] = None
        if isin and isin in isin_to_id:
            existing_id = isin_to_id[isin]
        elif symbol:
            existing_id = ticker_to_id.get(symbol)

        if existing_id and existing_id in by_id:
            ids = list(by_id[existing_id].get("index_ids") or [])
            if "BSE_ALL" not in ids:
                ids.append("BSE_ALL")
            by_id[existing_id]["index_ids"] = ids
            if by_id[existing_id].get("exchange") == "NSE":
                by_id[existing_id]["exchange"] = "NSE+BSE"
            continue

        cid = f"bse_{code or _slug(symbol)}"
        if cid in by_id:
            continue
        by_id[cid] = {
            "id": cid,
            "market_id": "IN",
            "index_ids": ["BSE_ALL"],
            "name": name,
            "ticker": symbol or code,
            "sector": "Equity",
            "data_quality": "listing_master",
            "exchange": "BSE",
            "isin": isin or None,
            "bse_scrip_code": code or None,
        }
        if symbol:
            ticker_to_id.setdefault(symbol, cid)
        if isin:
            isin_to_id[isin] = cid

    # Seeded deep names absent from the exchange files (renamed / demerged symbols)
    # keep their single record so Sensex / Nifty filters never fall back to a copy.
    for cid, name, ticker, sector in list(SENSEX_30) + list(NIFTY50_BEYOND_SENSEX):
        if cid in by_id:
            continue
        by_id[cid] = {
            "id": cid,
            "market_id": "IN",
            "index_ids": [],
            "name": name,
            "ticker": ticker,
            "sector": sector,
            "data_quality": deep_data_quality(cid),
            "exchange": None,
            "isin": None,
        }

    sensex_ids = {cid for cid, *_ in SENSEX_30}
    nifty500 = nifty500_by_symbol()
    nifty500_isins = {str(r.get("isin") or "") for r in nifty500.values()} - {""}
    for cid, entry in by_id.items():
        ids = list(entry.get("index_ids") or [])
        ticker = (entry.get("ticker") or "").upper()
        if cid in sensex_ids:
            ids.append("SENSEX")
        if ticker in OFFICIAL_NIFTY50_TICKERS:
            ids.append("NIFTY50")
        if ticker in NIFTYBANK_TICKERS:
            ids.append("NIFTYBANK")
        member = nifty500.get(ticker) if "NSE_ALL" in ids or cid in sensex_ids else None
        if member is None and entry.get("isin") in nifty500_isins:
            member = next(r for r in nifty500.values() if r.get("isin") == entry["isin"])
        if member is not None:
            ids.append("NIFTY500")
            if entry.get("sector") in (None, "", "Equity") and member.get("industry"):
                entry["sector"] = member["industry"]
        entry["index_ids"] = ids

    # Stable order: deep GCI first, then NSE ticker, then BSE-only
    deep = [by_id[c] for c, *_ in SENSEX_30]
    deep += [by_id[c] for c, *_ in NIFTY50_BEYOND_SENSEX if c not in sensex_ids]
    deep_ids = {r["id"] for r in deep}
    rest = sorted(
        (r for r in by_id.values() if r["id"] not in deep_ids),
        key=lambda r: (0 if "NSE_ALL" in r.get("index_ids", []) else 1, r.get("ticker") or ""),
    )
    ordered = deep + rest
    for row in ordered[:IN1000_CAP]:
        row["index_ids"].append("IN1000")
    for row in ordered:
        row["index_ids"] = [ix for ix in INDIA_INDEX_IDS if ix in row["index_ids"]]
    return tuple(ordered)


@lru_cache(maxsize=None)
def india_index_members(index_id: str) -> Tuple[StockRow, ...]:
    """Rows tagged with ``index_id`` — the same objects as the universe, not copies."""
    iid = (index_id or "").upper()
    return tuple(r for r in india_equity_universe() if iid in r["index_ids"])


@lru_cache(maxsize=1)
def _listings_by_id() -> Dict[str, StockRow]:
    return {row["id"]: row for row in india_equity_universe()}


def find_listing(company_id: str) -> Optional[StockRow]:
    row = _listings_by_id().get((company_id or "").strip())
    return dict(row) if row else None


@lru_cache(maxsize=1)
def _listings_by_ticker() -> Dict[str, StockRow]:
    out: Dict[str, StockRow] = {}
    for row in india_equity_universe():
        ticker = (row.get("ticker") or "").strip().upper()
        if ticker and ticker not in out:
            out[ticker] = row
    return out


def find_listing_by_ticker(ticker: str) -> Optional[StockRow]:
    """NSE/BSE listing lookup by exchange symbol (e.g. 20MICRONS)."""
    key = (ticker or "").strip().upper()
    if not key:
        return None
    row = _listings_by_ticker().get(key)
    return dict(row) if row else None


def listing_counts() -> Dict[str, Any]:
    rows = india_equity_universe()
    nse = sum(1 for r in rows if "NSE_ALL" in r.get("index_ids", []))
    bse = sum(1 for r in rows if "BSE_ALL" in r.get("index_ids", []))
    return {
        "merged": len(rows),
        "nse": nse,
        "bse": bse,
        "nse_source": nse_meta().get("source"),
        "bse_source": bse_meta().get("source"),
        "nse_file_count": nse_meta().get("count"),
        "bse_file_count": bse_meta().get("count"),
    }


def clear_listing_caches() -> None:
    india_equity_universe.cache_clear()
    india_index_members.cache_clear()
    _listings_by_id.cache_clear()
    nse_meta.cache_clear()
    nifty500_by_symbol.cache_clear()
    bse_meta.cache_clear()
    _sensex_by_ticker.cache_clear()
    _nifty_extra_by_ticker.cache_clear()
    _listings_by_ticker.cache_clear()
