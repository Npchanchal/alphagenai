"""Refresh index membership files used to order the filing walk.

    python -m app.jobs.refresh_index_lists            # both
    python -m app.jobs.refresh_index_lists --nifty500
    python -m app.jobs.refresh_index_lists --us

Nifty 500: NSE's published constituent CSV. S&P 500: the public constituent
table (ticker, name, GICS sector, SEC CIK). Membership only — no prices, no scores.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

LISTINGS = Path(__file__).resolve().parents[1] / "data" / "listings"
NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"


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
    args = ap.parse_args(argv)
    both = not (args.nifty500 or args.us)
    report: Dict[str, Any] = {}
    if both or args.nifty500:
        report.update(refresh_nifty500())
    if both or args.us:
        report.update(refresh_us())
    print(json.dumps({"ok": True, **report}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
