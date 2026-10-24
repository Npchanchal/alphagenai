"""Major markets → flagship indexes → top-1000 constituent scaffolding.

India: one merged NSE + BSE equity master (`india_listings`). Every India index
(SENSEX, NIFTY50, NIFTYBANK, NIFTY500, NSE_ALL, BSE_ALL, IN1000) filters that
single row set by membership tag. US: the S&P 500 master (`us_listings`) when the
file is present. Other markets stay market_scaffold pads.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.data.india_listings import IN1000_CAP, INDIA_INDEX_IDS

StockRow = Dict[str, Any]

MARKET_TOP_N = 1000
GCI_DEEP_MARKETS = ["IN"]

MARKETS: List[Dict[str, str]] = [
    {"id": "IN", "name": "India", "currency": "INR", "timezone": "Asia/Kolkata"},
    {"id": "US", "name": "United States", "currency": "USD", "timezone": "America/New_York"},
    {"id": "GB", "name": "United Kingdom", "currency": "GBP", "timezone": "Europe/London"},
    {"id": "JP", "name": "Japan", "currency": "JPY", "timezone": "Asia/Tokyo"},
    {"id": "HK", "name": "Hong Kong", "currency": "HKD", "timezone": "Asia/Hong_Kong"},
    {"id": "CN", "name": "China", "currency": "CNY", "timezone": "Asia/Shanghai"},
    {"id": "EU", "name": "Eurozone", "currency": "EUR", "timezone": "Europe/Berlin"},
    {"id": "SG", "name": "Singapore", "currency": "SGD", "timezone": "Asia/Singapore"},
    {"id": "AU", "name": "Australia", "currency": "AUD", "timezone": "Australia/Sydney"},
    {"id": "KR", "name": "South Korea", "currency": "KRW", "timezone": "Asia/Seoul"},
    {"id": "BR", "name": "Brazil", "currency": "BRL", "timezone": "America/Sao_Paulo"},
    {"id": "CA", "name": "Canada", "currency": "CAD", "timezone": "America/Toronto"},
]

INDEXES: List[Dict[str, Any]] = [
    {"id": "SENSEX", "market_id": "IN", "name": "BSE Sensex", "ticker": "SENSEX"},
    {"id": "NIFTY50", "market_id": "IN", "name": "Nifty 50", "ticker": "NIFTY"},
    {"id": "NIFTYBANK", "market_id": "IN", "name": "Nifty Bank", "ticker": "BANKNIFTY"},
    {"id": "NIFTY500", "market_id": "IN", "name": "Nifty 500", "ticker": "NIFTY500"},
    {"id": "NSE_ALL", "market_id": "IN", "name": "NSE Equities (all)", "ticker": "NSE"},
    {"id": "BSE_ALL", "market_id": "IN", "name": "BSE Equities (all)", "ticker": "BSE"},
    {"id": "IN1000", "market_id": "IN", "name": "India Top 1000", "ticker": "IN1000"},
    {"id": "SPX", "market_id": "US", "name": "S&P 500", "ticker": "SPX"},
    {"id": "DJI", "market_id": "US", "name": "Dow Jones Industrial Average", "ticker": "DJI"},
    {"id": "NDX", "market_id": "US", "name": "Nasdaq-100", "ticker": "NDX"},
    {"id": "FTSE100", "market_id": "GB", "name": "FTSE / UK Top 1000", "ticker": "UKX"},
    {"id": "N225", "market_id": "JP", "name": "Nikkei 225 / JP Top 1000", "ticker": "N225"},
    {"id": "TOPIX", "market_id": "JP", "name": "TOPIX", "ticker": "TPX"},
    {"id": "HSI", "market_id": "HK", "name": "Hang Seng / HK Top 1000", "ticker": "HSI"},
    {"id": "CSI300", "market_id": "CN", "name": "CSI / China Top 1000", "ticker": "CSI300"},
    {"id": "SSEC", "market_id": "CN", "name": "Shanghai Composite", "ticker": "SSEC"},
    {"id": "STOXX50", "market_id": "EU", "name": "Euro Stoxx / EU Top 1000", "ticker": "SX5E"},
    {"id": "DAX", "market_id": "EU", "name": "DAX", "ticker": "DAX"},
    {"id": "CAC40", "market_id": "EU", "name": "CAC 40", "ticker": "CAC"},
    {"id": "STI", "market_id": "SG", "name": "STI / Singapore Top 1000", "ticker": "STI"},
    {"id": "ASX200", "market_id": "AU", "name": "ASX / Australia Top 1000", "ticker": "AS51"},
    {"id": "KOSPI200", "market_id": "KR", "name": "KOSPI / Korea Top 1000", "ticker": "KOSPI2"},
    {"id": "IBOV", "market_id": "BR", "name": "Bovespa / Brazil Top 1000", "ticker": "IBOV"},
    {"id": "TSX60", "market_id": "CA", "name": "TSX / Canada Top 1000", "ticker": "TX60"},
]

# Primary index per market carries the full top-1000 scaffold universe.
_PRIMARY_INDEX: Dict[str, str] = {
    "IN": "IN1000",
    "US": "SPX",
    "GB": "FTSE100",
    "JP": "N225",
    "HK": "HSI",
    "CN": "CSI300",
    "EU": "STOXX50",
    "SG": "STI",
    "AU": "ASX200",
    "KR": "KOSPI200",
    "BR": "IBOV",
    "CA": "TSX60",
}

_SECONDARY_CAP: Dict[str, int] = {
    "DJI": 30,
    "NDX": 100,
    "TOPIX": 400,
    "SSEC": 500,
    "DAX": 40,
    "CAC40": 40,
}

_SECTORS = [
    "Technology",
    "Banks",
    "Financials",
    "Healthcare",
    "Pharma",
    "Consumer",
    "FMCG",
    "Energy",
    "Industrials",
    "Metals",
    "Telecom",
    "Auto",
    "Materials",
    "Real Estate",
    "Insurance",
    "Utilities",
]

# Named anchors kept at the front of each market universe.
_ANCHORS: List[StockRow] = [
    {"id": "us_aapl", "market_id": "US", "index_ids": ["SPX", "NDX", "DJI"], "name": "Apple Inc.", "ticker": "AAPL", "sector": "Technology"},
    {"id": "us_msft", "market_id": "US", "index_ids": ["SPX", "NDX", "DJI"], "name": "Microsoft Corp.", "ticker": "MSFT", "sector": "Technology"},
    {"id": "us_amzn", "market_id": "US", "index_ids": ["SPX", "NDX"], "name": "Amazon.com Inc.", "ticker": "AMZN", "sector": "Consumer"},
    {"id": "us_nvda", "market_id": "US", "index_ids": ["SPX", "NDX"], "name": "NVIDIA Corp.", "ticker": "NVDA", "sector": "Technology"},
    {"id": "us_googl", "market_id": "US", "index_ids": ["SPX", "NDX"], "name": "Alphabet Inc.", "ticker": "GOOGL", "sector": "Technology"},
    {"id": "us_meta", "market_id": "US", "index_ids": ["SPX", "NDX"], "name": "Meta Platforms Inc.", "ticker": "META", "sector": "Technology"},
    {"id": "us_tsla", "market_id": "US", "index_ids": ["SPX", "NDX"], "name": "Tesla Inc.", "ticker": "TSLA", "sector": "Auto"},
    {"id": "us_jpm", "market_id": "US", "index_ids": ["SPX", "DJI"], "name": "JPMorgan Chase & Co.", "ticker": "JPM", "sector": "Banks"},
    {"id": "us_v", "market_id": "US", "index_ids": ["SPX", "DJI"], "name": "Visa Inc.", "ticker": "V", "sector": "Financials"},
    {"id": "us_unh", "market_id": "US", "index_ids": ["SPX", "DJI"], "name": "UnitedHealth Group", "ticker": "UNH", "sector": "Healthcare"},
    {"id": "us_hd", "market_id": "US", "index_ids": ["SPX", "DJI"], "name": "Home Depot Inc.", "ticker": "HD", "sector": "Consumer"},
    {"id": "us_pg", "market_id": "US", "index_ids": ["SPX", "DJI"], "name": "Procter & Gamble", "ticker": "PG", "sector": "FMCG"},
    {"id": "gb_azn", "market_id": "GB", "index_ids": ["FTSE100"], "name": "AstraZeneca PLC", "ticker": "AZN", "sector": "Pharma"},
    {"id": "gb_shel", "market_id": "GB", "index_ids": ["FTSE100"], "name": "Shell PLC", "ticker": "SHEL", "sector": "Energy"},
    {"id": "gb_hsba", "market_id": "GB", "index_ids": ["FTSE100"], "name": "HSBC Holdings", "ticker": "HSBA", "sector": "Banks"},
    {"id": "gb_ulvr", "market_id": "GB", "index_ids": ["FTSE100"], "name": "Unilever PLC", "ticker": "ULVR", "sector": "FMCG"},
    {"id": "gb_bp", "market_id": "GB", "index_ids": ["FTSE100"], "name": "BP PLC", "ticker": "BP", "sector": "Energy"},
    {"id": "gb_gsk", "market_id": "GB", "index_ids": ["FTSE100"], "name": "GSK PLC", "ticker": "GSK", "sector": "Pharma"},
    {"id": "gb_rio", "market_id": "GB", "index_ids": ["FTSE100"], "name": "Rio Tinto PLC", "ticker": "RIO", "sector": "Metals"},
    {"id": "gb_dge", "market_id": "GB", "index_ids": ["FTSE100"], "name": "Diageo PLC", "ticker": "DGE", "sector": "Consumer"},
    {"id": "jp_7203", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Toyota Motor", "ticker": "7203", "sector": "Auto"},
    {"id": "jp_6758", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Sony Group", "ticker": "6758", "sector": "Technology"},
    {"id": "jp_9984", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "SoftBank Group", "ticker": "9984", "sector": "Telecom"},
    {"id": "jp_6861", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Keyence", "ticker": "6861", "sector": "Technology"},
    {"id": "jp_8306", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Mitsubishi UFJ", "ticker": "8306", "sector": "Banks"},
    {"id": "jp_4063", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Shin-Etsu Chemical", "ticker": "4063", "sector": "Materials"},
    {"id": "jp_6501", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Hitachi", "ticker": "6501", "sector": "Industrials"},
    {"id": "jp_8035", "market_id": "JP", "index_ids": ["N225", "TOPIX"], "name": "Tokyo Electron", "ticker": "8035", "sector": "Technology"},
    {"id": "hk_0700", "market_id": "HK", "index_ids": ["HSI"], "name": "Tencent Holdings", "ticker": "0700", "sector": "Technology"},
    {"id": "hk_9988", "market_id": "HK", "index_ids": ["HSI"], "name": "Alibaba Group", "ticker": "9988", "sector": "Consumer"},
    {"id": "hk_0005", "market_id": "HK", "index_ids": ["HSI"], "name": "HSBC Holdings", "ticker": "0005", "sector": "Banks"},
    {"id": "hk_1299", "market_id": "HK", "index_ids": ["HSI"], "name": "AIA Group", "ticker": "1299", "sector": "Insurance"},
    {"id": "hk_2318", "market_id": "HK", "index_ids": ["HSI"], "name": "Ping An Insurance", "ticker": "2318", "sector": "Insurance"},
    {"id": "hk_0941", "market_id": "HK", "index_ids": ["HSI"], "name": "China Mobile", "ticker": "0941", "sector": "Telecom"},
    {"id": "cn_600519", "market_id": "CN", "index_ids": ["CSI300", "SSEC"], "name": "Kweichow Moutai", "ticker": "600519", "sector": "Consumer"},
    {"id": "cn_601318", "market_id": "CN", "index_ids": ["CSI300", "SSEC"], "name": "Ping An Insurance", "ticker": "601318", "sector": "Insurance"},
    {"id": "cn_600036", "market_id": "CN", "index_ids": ["CSI300", "SSEC"], "name": "China Merchants Bank", "ticker": "600036", "sector": "Banks"},
    {"id": "cn_000858", "market_id": "CN", "index_ids": ["CSI300"], "name": "Wuliangye Yibin", "ticker": "000858", "sector": "Consumer"},
    {"id": "cn_601012", "market_id": "CN", "index_ids": ["CSI300"], "name": "LONGi Green Energy", "ticker": "601012", "sector": "Energy"},
    {"id": "cn_300750", "market_id": "CN", "index_ids": ["CSI300"], "name": "CATL", "ticker": "300750", "sector": "Industrials"},
    {"id": "eu_asml", "market_id": "EU", "index_ids": ["STOXX50"], "name": "ASML Holding", "ticker": "ASML", "sector": "Technology"},
    {"id": "eu_sap", "market_id": "EU", "index_ids": ["STOXX50", "DAX"], "name": "SAP SE", "ticker": "SAP", "sector": "Technology"},
    {"id": "eu_sie", "market_id": "EU", "index_ids": ["STOXX50", "DAX"], "name": "Siemens AG", "ticker": "SIE", "sector": "Industrials"},
    {"id": "eu_mc", "market_id": "EU", "index_ids": ["STOXX50", "CAC40"], "name": "LVMH", "ticker": "MC", "sector": "Consumer"},
    {"id": "eu_or", "market_id": "EU", "index_ids": ["STOXX50", "CAC40"], "name": "L'Oréal", "ticker": "OR", "sector": "FMCG"},
    {"id": "eu_air", "market_id": "EU", "index_ids": ["STOXX50", "CAC40"], "name": "Airbus SE", "ticker": "AIR", "sector": "Industrials"},
    {"id": "eu_alv", "market_id": "EU", "index_ids": ["STOXX50", "DAX"], "name": "Allianz SE", "ticker": "ALV", "sector": "Insurance"},
    {"id": "eu_nesn", "market_id": "EU", "index_ids": ["STOXX50"], "name": "Nestlé SA", "ticker": "NESN", "sector": "FMCG"},
    {"id": "sg_dbs", "market_id": "SG", "index_ids": ["STI"], "name": "DBS Group", "ticker": "D05", "sector": "Banks"},
    {"id": "sg_ocbc", "market_id": "SG", "index_ids": ["STI"], "name": "OCBC Bank", "ticker": "O39", "sector": "Banks"},
    {"id": "sg_uob", "market_id": "SG", "index_ids": ["STI"], "name": "UOB", "ticker": "U11", "sector": "Banks"},
    {"id": "sg_st", "market_id": "SG", "index_ids": ["STI"], "name": "Singapore Telecom", "ticker": "Z74", "sector": "Telecom"},
    {"id": "sg_capl", "market_id": "SG", "index_ids": ["STI"], "name": "CapitaLand", "ticker": "C38U", "sector": "Real Estate"},
    {"id": "au_bhp", "market_id": "AU", "index_ids": ["ASX200"], "name": "BHP Group", "ticker": "BHP", "sector": "Metals"},
    {"id": "au_cba", "market_id": "AU", "index_ids": ["ASX200"], "name": "Commonwealth Bank", "ticker": "CBA", "sector": "Banks"},
    {"id": "au_csl", "market_id": "AU", "index_ids": ["ASX200"], "name": "CSL Ltd.", "ticker": "CSL", "sector": "Pharma"},
    {"id": "au_wbc", "market_id": "AU", "index_ids": ["ASX200"], "name": "Westpac Banking", "ticker": "WBC", "sector": "Banks"},
    {"id": "au_ncm", "market_id": "AU", "index_ids": ["ASX200"], "name": "Newcrest Mining", "ticker": "NCM", "sector": "Metals"},
    {"id": "kr_005930", "market_id": "KR", "index_ids": ["KOSPI200"], "name": "Samsung Electronics", "ticker": "005930", "sector": "Technology"},
    {"id": "kr_000660", "market_id": "KR", "index_ids": ["KOSPI200"], "name": "SK Hynix", "ticker": "000660", "sector": "Technology"},
    {"id": "kr_035420", "market_id": "KR", "index_ids": ["KOSPI200"], "name": "NAVER", "ticker": "035420", "sector": "Technology"},
    {"id": "kr_005380", "market_id": "KR", "index_ids": ["KOSPI200"], "name": "Hyundai Motor", "ticker": "005380", "sector": "Auto"},
    {"id": "kr_051910", "market_id": "KR", "index_ids": ["KOSPI200"], "name": "LG Chem", "ticker": "051910", "sector": "Materials"},
    {"id": "br_vale", "market_id": "BR", "index_ids": ["IBOV"], "name": "Vale S.A.", "ticker": "VALE3", "sector": "Metals"},
    {"id": "br_petr", "market_id": "BR", "index_ids": ["IBOV"], "name": "Petrobras", "ticker": "PETR4", "sector": "Energy"},
    {"id": "br_itub", "market_id": "BR", "index_ids": ["IBOV"], "name": "Itaú Unibanco", "ticker": "ITUB4", "sector": "Banks"},
    {"id": "br_bbdc", "market_id": "BR", "index_ids": ["IBOV"], "name": "Bradesco", "ticker": "BBDC4", "sector": "Banks"},
    {"id": "br_abev", "market_id": "BR", "index_ids": ["IBOV"], "name": "Ambev", "ticker": "ABEV3", "sector": "Consumer"},
    {"id": "ca_ry", "market_id": "CA", "index_ids": ["TSX60"], "name": "Royal Bank of Canada", "ticker": "RY", "sector": "Banks"},
    {"id": "ca_td", "market_id": "CA", "index_ids": ["TSX60"], "name": "Toronto-Dominion Bank", "ticker": "TD", "sector": "Banks"},
    {"id": "ca_shop", "market_id": "CA", "index_ids": ["TSX60"], "name": "Shopify Inc.", "ticker": "SHOP", "sector": "Technology"},
    {"id": "ca_enbin", "market_id": "CA", "index_ids": ["TSX60"], "name": "Enbridge Inc.", "ticker": "ENB", "sector": "Energy"},
    {"id": "ca_cnr", "market_id": "CA", "index_ids": ["TSX60"], "name": "Canadian National Railway", "ticker": "CNR", "sector": "Industrials"},
]

def _with_quality(row: StockRow, quality: str = "market_scaffold") -> StockRow:
    out = dict(row)
    out.setdefault("data_quality", quality)
    return out


def _ticker_for(market_id: str, n: int) -> str:
    mid = market_id.upper()
    if mid == "JP":
        return f"{1000 + n:04d}"
    if mid == "HK":
        return f"{n:04d}"
    if mid == "CN":
        return f"{600000 + n}"
    if mid == "KR":
        return f"{n:06d}"
    if mid == "BR":
        return f"B{n:04d}"
    if mid in {"GB", "EU", "AU", "CA", "SG"}:
        return f"{mid[0]}{n:04d}"
    return f"{mid}{n:04d}"


def _index_ids_for(market_id: str, rank: int, sector: str) -> List[str]:
    """Assign primary + optional secondary membership by rank/sector."""
    mid = market_id.upper()
    primary = _PRIMARY_INDEX[mid]
    ids = [primary]
    if mid == "US":
        if rank < _SECONDARY_CAP["DJI"]:
            ids.append("DJI")
        if sector == "Technology" and rank < _SECONDARY_CAP["NDX"]:
            ids.append("NDX")
        elif rank < _SECONDARY_CAP["NDX"] and rank % 3 == 0:
            ids.append("NDX")
    elif mid == "JP" and rank < _SECONDARY_CAP["TOPIX"]:
        ids.append("TOPIX")
    elif mid == "CN" and rank < _SECONDARY_CAP["SSEC"]:
        ids.append("SSEC")
    elif mid == "EU":
        if rank < _SECONDARY_CAP["DAX"] and rank % 2 == 0:
            ids.append("DAX")
        if rank < _SECONDARY_CAP["CAC40"] and rank % 2 == 1:
            ids.append("CAC40")
    return ids


def _with_anchor_tags(listed: Tuple[StockRow, ...]) -> Tuple[StockRow, ...]:
    """Real listing rows; secondary index tags come only from the named anchors."""
    tags = {a["id"]: a.get("index_ids") or [] for a in _ANCHORS}
    out = []
    for row in listed:
        ids = list(row.get("index_ids") or [])
        for ix in tags.get(row["id"], []):
            if ix not in ids:
                ids.append(ix)
        out.append({**row, "index_ids": ids})
    return tuple(out)


@lru_cache(maxsize=16)
def _market_universe(market_id: str) -> Tuple[Dict[str, Any], ...]:
    mid = market_id.upper()
    if not any(x["id"] == mid for x in MARKETS):
        return tuple()

    # India uses exchange equity masters (NSE + BSE), not synthetic Constituent pads
    if mid == "IN":
        from app.data.india_listings import india_equity_universe

        return india_equity_universe()

    if mid == "US":
        from app.data.us_listings import us_equity_universe

        listed = us_equity_universe()
        if listed:
            return _with_anchor_tags(listed)

    rows: List[StockRow] = []
    seen: set = set()

    for a in _ANCHORS:
        if a["market_id"] != mid:
            continue
        if a["id"] in seen:
            continue
        row = _with_quality(dict(a))
        # ensure primary index membership
        primary = _PRIMARY_INDEX[mid]
        ids = list(row.get("index_ids") or [])
        if primary not in ids:
            ids.insert(0, primary)
        row["index_ids"] = ids
        rows.append(row)
        seen.add(row["id"])

    n = 1
    while len(rows) < MARKET_TOP_N:
        sid = f"{mid.lower()}_{n:04d}"
        if sid in seen:
            n += 1
            continue
        sector = _SECTORS[(n - 1) % len(_SECTORS)]
        rank = len(rows)
        rows.append(
            _with_quality(
                {
                    "id": sid,
                    "market_id": mid,
                    "index_ids": _index_ids_for(mid, rank, sector),
                    "name": f"{mid} Constituent {n:04d}",
                    "ticker": _ticker_for(mid, n),
                    "sector": sector,
                }
            )
        )
        seen.add(sid)
        n += 1

    return tuple(rows)


def _universe_size(market_id: str) -> int:
    if market_id == "IN":
        from app.data.india_listings import listing_counts

        return listing_counts()["merged"]
    return len(_market_universe(market_id)) or MARKET_TOP_N


def list_markets() -> List[Dict[str, Any]]:
    out = []
    for m in MARKETS:
        out.append(
            {
                **m,
                "universe_size": _universe_size(m["id"]),
                "primary_index": _PRIMARY_INDEX[m["id"]],
            }
        )
    return out


def get_market(market_id: str) -> Optional[Dict[str, Any]]:
    mid = market_id.upper()
    m = next((dict(x) for x in MARKETS if x["id"] == mid), None)
    if m is None:
        return None
    m["universe_size"] = _universe_size(mid)
    m["primary_index"] = _PRIMARY_INDEX[mid]
    return m


def get_index_raw(index_id: str) -> Optional[Dict[str, Any]]:
    iid = index_id.upper()
    return next((dict(i) for i in INDEXES if i["id"] == iid), None)


def list_indexes(market_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = INDEXES
    if market_id:
        mid = market_id.upper()
        rows = [i for i in INDEXES if i["market_id"] == mid]
    out = []
    for ix in rows:
        out.append({**ix, "constituent_count": constituent_count(ix["id"])})
    return out


def get_index(index_id: str) -> Optional[Dict[str, Any]]:
    ix = get_index_raw(index_id)
    if ix is None:
        return None
    return {**ix, "constituent_count": constituent_count(ix["id"])}


def constituent_count(index_id: str) -> int:
    return len(_constituents_cached(index_id.upper()))


@lru_cache(maxsize=32)
def _constituents_cached(index_id: str) -> Tuple[StockRow, ...]:
    iid = index_id.upper()
    ix = get_index_raw(iid)
    if ix is None:
        return tuple()
    mid = ix["market_id"]

    if iid in INDIA_INDEX_IDS:
        from app.data.india_listings import india_index_members

        return india_index_members(iid)

    if iid == _PRIMARY_INDEX.get(mid):
        return _market_universe(mid)

    cap = _SECONDARY_CAP.get(iid)
    rows = tuple(r for r in _market_universe(mid) if iid in r.get("index_ids", []))
    if cap is not None:
        rows = rows[:cap]
    return rows


def list_constituents(index_id: str) -> List[StockRow]:
    # Shallow copy so callers can mutate safely without poisoning the cache
    return [dict(r) for r in _constituents_cached(index_id.upper())]


def constituents_readonly(index_id: str) -> Tuple[StockRow, ...]:
    """Cached membership rows — do not mutate."""
    return _constituents_cached(index_id.upper())


def list_stocks(
    market_id: Optional[str] = None, index_id: Optional[str] = None
) -> List[StockRow]:
    """Market/index filtered stocks. Default (no filter) remains Sensex deep GCI."""
    if index_id:
        return list_constituents(index_id)
    if market_id:
        return [dict(r) for r in _market_universe(market_id.upper())]
    return list_constituents("SENSEX")


@lru_cache(maxsize=1)
def _stock_index() -> Dict[str, StockRow]:
    out: Dict[str, StockRow] = {}
    for m in MARKETS:
        for r in _market_universe(m["id"]):
            out[r["id"]] = dict(r)
    return out


def get_stock(stock_id: str) -> Optional[StockRow]:
    return _stock_index().get(stock_id)


def markets_meta() -> Dict[str, Any]:
    from app.data.india_listings import listing_counts

    counts = listing_counts()
    return {
        "markets_count": len(MARKETS),
        "indexes_count": len(INDEXES),
        "gci_deep_markets": list(GCI_DEEP_MARKETS),
        "market_universe_size": MARKET_TOP_N,
        "india_listings": counts,
        "scaffold_note": (
            f"Coverage is India-first. Other markets are constituent lists for navigation, "
            f"not scored delivery records. India listings: NSE {counts['nse']}, "
            f"BSE {counts['bse']} (merged {counts['merged']}). "
            "A published GCI requires both quotes on the cited filings. "
            "Cite only companies that have passed that check."
        ),
    }
