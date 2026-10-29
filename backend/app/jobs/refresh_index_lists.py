"""Refresh index membership files used to order the filing walk.

    python -m app.jobs.refresh_index_lists            # Nifty 500 and S&P 500
    python -m app.jobs.refresh_index_lists --nifty500
    python -m app.jobs.refresh_index_lists --us
    python -m app.jobs.refresh_index_lists --world    # every market below
    python -m app.jobs.refresh_index_lists --world GB JP

Nifty 500: NSE's published constituent CSV. S&P 500: the public constituent
table (ticker, name, GICS sector, SEC CIK). Other markets: Nikkei's weight file,
B3's Ibovespa portfolio, and the public constituent tables for the rest.
Membership only — no prices, no scores.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

LISTINGS = Path(__file__).resolve().parents[1] / "data" / "listings"
NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NIKKEI225_URL = "https://indexes.nikkei.co.jp/en/nkave/archives/file/nikkei_stock_average_weight_en.csv"
B3_PORTFOLIO_URL = "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
WIKI = "https://en.wikipedia.org/wiki/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# index id -> (market, page, ticker column, name column, sector column, fewest rows accepted)
WIKI_TABLES: Dict[str, Tuple[str, str, str, str, Optional[str], int]] = {
    "FTSE100": ("GB", "FTSE_100_Index", "Ticker", "Company", "FTSE industry classification benchmark sector", 95),
    "HSI": ("HK", "Hang_Seng_Index", "Ticker", "Name", "Sub-index", 70),
    "CSI300": ("CN", "CSI_300_Index", "Ticker", "Company", "Segment", 290),
    "STOXX50": ("EU", "EURO_STOXX_50", "Ticker", "Name", "Sector", 48),
    "DAX": ("EU", "DAX", "Ticker", "Company", "Prime Standard Sector", 38),
    "CAC40": ("EU", "CAC_40", "Ticker", "Company", "Sector", 38),
    "STI": ("SG", "Straits_Times_Index", "Stock symbol", "Company", None, 28),
    "ASX200": ("AU", "S%26P/ASX_200", "Code", "Company", "Sector", 190),
    "KOSPI200": ("KR", "KOSPI_200", "Symbol", "Company", "GICS Sector", 190),
    "TSX60": ("CA", "S%26P/TSX_60", "Symbol", "Company", "Sector", 58),
}
WORLD_MARKETS = ("GB", "JP", "HK", "CN", "EU", "SG", "AU", "KR", "BR", "CA")
_HOME_EXCHANGE = {"GB": "LSE", "JP": "TSE", "HK": "HKEX", "SG": "SGX", "AU": "ASX", "KR": "KRX", "BR": "B3", "CA": "TSX"}
_EU_SUFFIX = {
    "DE": "XETRA",
    "PA": "EURONEXT PARIS",
    "AS": "EURONEXT AMSTERDAM",
    "BR": "EURONEXT BRUSSELS",
    "MI": "BORSA ITALIANA",
    "MC": "BME",
    "HE": "NASDAQ HELSINKI",
    "IR": "EURONEXT DUBLIN",
}


def _get(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=60) as resp:  # noqa: S310 — fixed URLs
        return resp.read()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_nifty500_csv(raw: str) -> List[Dict[str, str]]:
    rows = []
    for rec in csv.DictReader(io.StringIO(raw)):
        symbol = (rec.get("Symbol") or "").strip().upper()
        if not symbol:
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": (rec.get("Company Name") or "").strip(),
                "industry": (rec.get("Industry") or "").strip(),
                "isin": (rec.get("ISIN Code") or "").strip().upper(),
            }
        )
    return rows


def _cell_text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", html))).strip()


def parse_sp500_table(html: str) -> List[Dict[str, Any]]:
    m = re.search(r'<table[^>]*id="constituents"[^>]*>(.*?)</table>', html, re.S)
    if not m:
        return []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S)
    if not rows:
        return []
    header = [_cell_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S)]
    col = {name: i for i, name in enumerate(header)}
    need = ("Symbol", "Security", "GICS Sector", "CIK")
    if any(k not in col for k in need):
        return []
    out = []
    for row in rows[1:]:
        cells = [_cell_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
        if len(cells) < len(header):
            continue
        ticker = cells[col["Symbol"]].upper()
        cik = re.sub(r"\D", "", cells[col["CIK"]])
        if not ticker or not cik:
            continue
        out.append(
            {
                "ticker": ticker,
                "name": cells[col["Security"]],
                "sector": cells[col["GICS Sector"]],
                "cik": cik.zfill(10),
                "index_ids": ["SPX"],
            }
        )
    return out


def _header(text: str) -> str:
    return re.sub(r"\[\d+\]", "", text).strip()


def parse_wiki_constituents(
    html: str, ticker_col: str, name_col: str, sector_col: Optional[str] = None
) -> List[Dict[str, str]]:
    """Rows of the longest wikitable that has both the ticker and the name column."""
    best: List[Dict[str, str]] = []
    for table in re.findall(r"<table[^>]*wikitable[^>]*>(.*?)</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
        if not rows:
            continue
        header = [_header(_cell_text(c)) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S)]
        col = {name: i for i, name in enumerate(header)}
        if ticker_col not in col or name_col not in col:
            continue
        out = []
        for row in rows[1:]:
            cells = [_cell_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
            if len(cells) <= max(col[ticker_col], col[name_col]):
                continue
            ticker, name = cells[col[ticker_col]], cells[col[name_col]]
            if not ticker or not name:
                continue
            sector = cells[col[sector_col]] if sector_col in col and col[sector_col] < len(cells) else ""
            out.append({"ticker": ticker, "name": name, "sector": sector})
        if len(out) > len(best):
            best = out
    return best


def parse_nikkei225_csv(raw: str) -> List[Dict[str, str]]:
    out = []
    for rec in csv.DictReader(io.StringIO(raw)):
        code = (rec.get("Code") or "").strip().upper()
        if code:
            out.append(
                {
                    "ticker": code,
                    "name": (rec.get("Company Name") or "").strip(),
                    "sector": (rec.get("Nikkei Industrial Classification") or rec.get("Sector") or "").strip(),
                }
            )
    return out


def parse_b3_portfolio(raw: str) -> List[Dict[str, str]]:
    return [
        {"ticker": str(r.get("cod") or "").strip().upper(), "name": str(r.get("asset") or "").strip(), "sector": ""}
        for r in (json.loads(raw).get("results") or [])
        if r.get("cod")
    ]


def world_row(market_id: str, index_id: str, raw: Dict[str, str]) -> Dict[str, Any]:
    """One listing row: bare ticker, the exchange it trades on, and the index that named it."""
    prefix, sep, rest = raw["ticker"].partition(":")
    ticker = (rest if sep else prefix).strip().upper()
    venue = prefix.strip().upper() if sep else ""
    exchange = _HOME_EXCHANGE.get(market_id, market_id)
    suffix = ""
    if market_id == "CN":
        exchange = venue if venue in ("SSE", "SZSE") else ("SSE" if ticker.startswith("6") else "SZSE")
    elif market_id == "EU":
        ticker, _, suffix = ticker.partition(".")
        exchange = _EU_SUFFIX.get(suffix, suffix or "EU")
    elif market_id == "HK" and ticker.isdigit():
        ticker = ticker.zfill(4)
    return {
        "ticker": ticker,
        "name": re.sub(r"\s*\[[^\]]*\]", "", raw["name"]).strip() or ticker,
        "sector": raw.get("sector") or "Equity",
        "exchange": exchange,
        "index_ids": [index_id],
        "venue_suffix": suffix,
    }


def _disambiguate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same bare ticker on two venues (SAN in Madrid and Paris) keeps its venue suffix."""
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row["ticker"]] = counts.get(row["ticker"], 0) + 1
    out = []
    for row in rows:
        suffix = row.pop("venue_suffix", "")
        if counts[row["ticker"]] > 1 and suffix:
            row["ticker"] = f"{row['ticker']}.{suffix}"
        out.append(row)
    return out


def _world_sources() -> Dict[str, Tuple[str, str, Callable[[str], List[Dict[str, str]]], int]]:
    """index id -> (market, url, parser, fewest rows accepted)."""
    out: Dict[str, Tuple[str, str, Callable[[str], List[Dict[str, str]]], int]] = {}
    for ix, (mid, page, tcol, ncol, scol, least) in WIKI_TABLES.items():
        out[ix] = (mid, WIKI + page, lambda html, t=tcol, n=ncol, s=scol: parse_wiki_constituents(html, t, n, s), least)
    out["N225"] = ("JP", NIKKEI225_URL, parse_nikkei225_csv, 220)
    query = base64.b64encode(
        json.dumps({"language": "en-us", "pageNumber": 1, "pageSize": 200, "index": "IBOV", "segment": "1"}).encode()
    ).decode()
    out["IBOV"] = ("BR", B3_PORTFOLIO_URL + query, parse_b3_portfolio, 60)
    return out


def refresh_world(
    markets: Optional[List[str]] = None, fetch: Callable[[str], str] = lambda u: _get(u).decode("utf-8", "ignore")
) -> Dict[str, Any]:
    """Write ``{market}_equity.json`` for each market whose every index list came back whole.

    A market whose source is short or down keeps its previous file, so a bad fetch
    never shrinks a published list.
    """
    wanted = [m.upper() for m in (markets or WORLD_MARKETS)]
    report: Dict[str, Any] = {}
    by_market: Dict[str, Dict[str, Any]] = {}
    failed: set = set()
    for ix, (mid, url, parse, least) in _world_sources().items():
        if mid not in wanted or mid in failed:
            continue
        try:
            rows = parse(fetch(url))
        except Exception as exc:  # noqa: BLE001 — reported, file left alone
            rows, report[ix] = [], f"error: {exc}"
        if len(rows) < least:
            report.setdefault(ix, f"short ({len(rows)} rows); {mid} not written")
            failed.add(mid)
            continue
        bucket = by_market.setdefault(mid, {"rows": {}, "sources": {}})
        bucket["sources"][ix] = url
        for raw in rows:
            row = world_row(mid, ix, raw)
            key = (row["ticker"], row["exchange"])
            held = bucket["rows"].get(key)
            if held is None:
                bucket["rows"][key] = row
            elif ix not in held["index_ids"]:
                held["index_ids"].append(ix)
        report[ix] = len(rows)
    for mid, bucket in by_market.items():
        if mid in failed:
            continue
        rows = sorted(_disambiguate(list(bucket["rows"].values())), key=lambda r: r["name"].lower())
        write_json(
            f"{mid.lower()}_equity.json",
            {
                "market_id": mid,
                "source": bucket["sources"],
                "as_of": _today(),
                "count": len(rows),
                "indexes": list(bucket["sources"]),
                "rows": rows,
            },
        )
        report[mid] = len(rows)
    return report


def write_json(name: str, payload: Dict[str, Any]) -> Path:
    LISTINGS.mkdir(parents=True, exist_ok=True)
    path = LISTINGS / name
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def refresh_nifty500(raw: Optional[str] = None) -> Dict[str, Any]:
    text = raw if raw is not None else _get(NIFTY500_URL).decode("utf-8", errors="ignore")
    rows = parse_nifty500_csv(text)
    if len(rows) < 400:
        raise RuntimeError(f"Nifty 500 list looks short ({len(rows)} rows); not written")
    write_json("nifty500.json", {"source": NIFTY500_URL, "as_of": _today(), "count": len(rows), "rows": rows})
    return {"nifty500": len(rows)}


def refresh_us(html: Optional[str] = None) -> Dict[str, Any]:
    body = html if html is not None else _get(SP500_URL).decode("utf-8", errors="ignore")
    rows = parse_sp500_table(body)
    if len(rows) < 450:
        raise RuntimeError(f"S&P 500 list looks short ({len(rows)} rows); not written")
    write_json("us_equity.json", {"source": SP500_URL, "as_of": _today(), "count": len(rows), "rows": rows})
    return {"sp500": len(rows)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nifty500", action="store_true")
    ap.add_argument("--us", action="store_true")
    ap.add_argument("--world", nargs="*", metavar="MARKET", help="GB JP HK CN EU SG AU KR BR CA; none = all")
    args = ap.parse_args(argv)
    both = not (args.nifty500 or args.us or args.world is not None)
    report: Dict[str, Any] = {}
    if both or args.nifty500:
        report.update(refresh_nifty500())
    if both or args.us:
        report.update(refresh_us())
    if args.world is not None:
        report.update(refresh_world(args.world or None))
    print(json.dumps({"ok": True, **report}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
