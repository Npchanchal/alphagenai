"""Market and exchange scope a desk has bought.

A plan says which tools a seat opens. The scope says on which listings. Published
GCI levels stay open on every market (Screener, dossier, Public Snapshot); the
scope gates the seat tools: Filing Search, chat, Workbench, Analyst, Holdings,
Ninja, and exports.

A grant is ``*`` (every market), a market id (``IN``, ``US``), or a
``market:exchange`` pair (``IN:NSE``, ``IN:BSE``). A company listed on NSE and
BSE is in scope under either exchange. The US is sold as one market until the
listing master carries NYSE / Nasdaq.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from fastapi import HTTPException, Request

from app.data import markets as markets_data

ALL = "*"

# Exchanges sold separately inside a market. A market missing here is sold whole.
EXCHANGES: Dict[str, Tuple[str, ...]] = {"IN": ("NSE", "BSE")}

# Paid desks signed before scope existed keep every market. Pilots evaluate India.
_ALL_MARKET_PLANS = frozenset({"desk", "enterprise", "onestop"})


def _market_ids() -> Set[str]:
    return {m["id"] for m in markets_data.MARKETS}


def _market_name(market_id: str) -> str:
    m = markets_data.get_market(market_id)
    return m["name"] if m else market_id


def normalize_grants(raw: Any) -> List[str]:
    """Validate and collapse grants. Unknown entries are dropped, not guessed."""
    if raw is None:
        return []
    items = raw.split(",") if isinstance(raw, str) else list(raw)
    known = _market_ids()
    out: Set[str] = set()
    for item in items:
        g = str(item or "").strip().upper()
        if not g:
            continue
        if g == ALL:
            return [ALL]
        if ":" in g:
            mid, ex = g.split(":", 1)
            if ex in EXCHANGES.get(mid, ()):
                out.add(f"{mid}:{ex}")
            continue
        if g in known:
            out.add(g)
    for mid, exchanges in EXCHANGES.items():
        if mid in out or all(f"{mid}:{ex}" in out for ex in exchanges):
            out.difference_update(f"{mid}:{ex}" for ex in exchanges)
            out.add(mid)
    return sorted(out)


def default_grants(plan: Optional[str]) -> List[str]:
    p = (plan or "").strip().lower()
    if p == "guest":
        return []
    return [ALL] if p in _ALL_MARKET_PLANS else ["IN"]


def org_grants(row: Dict[str, Any], plan: Optional[str]) -> List[str]:
    if isinstance(row.get("coverage"), (list, str)):
        return normalize_grants(row["coverage"])
    return default_grants(plan)


def _market_label(market_id: str, grants: Iterable[str]) -> Optional[str]:
    gs = set(grants)
    name = _market_name(market_id)
    if market_id in gs:
        exchanges = EXCHANGES.get(market_id)
        return f"{name} ({' and '.join(exchanges)})" if exchanges else name
    held = [ex for ex in EXCHANGES.get(market_id, ()) if f"{market_id}:{ex}" in gs]
    return f"{name} ({' and '.join(held)})" if held else None


def describe(grants: List[str]) -> Dict[str, Any]:
    """Entitlement payload: what the desk bought, in ids and in one plain line."""
    if ALL in grants:
        return {
            "grants": [ALL],
            "all": True,
            "markets": [m["id"] for m in markets_data.MARKETS],
            "exchanges": {},
            "label": "All markets and exchanges",
        }
    markets: List[str] = []
    exchanges: Dict[str, List[str]] = {}
    labels: List[str] = []
    for m in markets_data.MARKETS:
        mid = m["id"]
        label = _market_label(mid, grants)
        if not label:
            continue
        markets.append(mid)
        labels.append(label)
        if mid in EXCHANGES:
            exchanges[mid] = (
                list(EXCHANGES[mid])
                if mid in grants
                else [ex for ex in EXCHANGES[mid] if f"{mid}:{ex}" in grants]
            )
    return {
        "grants": list(grants),
        "all": False,
        "markets": markets,
        "exchanges": exchanges,
        "label": " · ".join(labels) if labels else "No markets",
    }


def catalog() -> List[Dict[str, Any]]:
    """Units a desk can buy: each listed market, and inside it each exchange sold apart."""
    out: List[Dict[str, Any]] = []
    for mid in markets_data.listed_market_ids():
        name = _market_name(mid)
        out.append(
            {
                "id": mid,
                "market_id": mid,
                "label": name,
                "exchanges": [
                    {"id": f"{mid}:{ex}", "exchange": ex, "label": f"{name} · {ex}"}
                    for ex in EXCHANGES.get(mid, ())
                ],
            }
        )
    return out


def listing_of(company_id: str) -> Optional[Tuple[str, Set[str]]]:
    """(market_id, exchanges) for a listed company; None when the id is not a listing."""
    row = markets_data.get_stock(str(company_id or "").strip())
    if row is None:
        return None
    exchanges = {x for x in str(row.get("exchange") or "").upper().split("+") if x}
    return str(row.get("market_id") or ""), exchanges


def listing_in_scope(grants: Iterable[str], market_id: Optional[str], exchanges: Iterable[str]) -> bool:
    gs = set(grants)
    if ALL in gs:
        return True
    if not market_id:
        return False
    if market_id in gs:
        return True
    return any(f"{market_id}:{ex}" in gs for ex in exchanges)


def company_in_scope(grants: Iterable[str], company_id: str) -> bool:
    listing = listing_of(company_id)
    if listing is None:
        # Not a listed company (an upload, a project, a typo): nothing to price; the route 404s on its own.
        return True
    return listing_in_scope(grants, listing[0], listing[1])


def grants_of(ent: Dict[str, Any]) -> List[str]:
    cov = ent.get("coverage") or {}
    return list(cov.get("grants") or [])


def require_in_scope(ent: Dict[str, Any], company_id: str) -> None:
    grants = grants_of(ent)
    if company_in_scope(grants, company_id):
        return
    market_id, exchanges = listing_of(company_id) or ("", set())
    where = _market_name(market_id)
    if market_id in EXCHANGES and exchanges:
        where = f"{where} ({' and '.join(sorted(exchanges))})"
    covered = describe(grants)["label"]
    raise HTTPException(
        status_code=403,
        detail={
            "code": "market_not_in_plan",
            "message": (
                f"This company lists in {where}. Your plan covers {covered}. "
                "Its published GCI stays open; this tool opens once the market is on your order form."
            ),
            "company_id": company_id,
            "market_id": market_id,
            "exchanges": sorted(exchanges),
            "coverage": covered,
        },
    )


def predicate(ent: Dict[str, Any]) -> Optional[Callable[[str], bool]]:
    """company_id -> in scope; None when the desk holds every market."""
    grants = grants_of(ent)
    if ALL in grants:
        return None
    return lambda cid: company_in_scope(grants, cid)


def filter_rows(ent: Dict[str, Any], rows: List[Dict[str, Any]], key: str = "company_id") -> List[Dict[str, Any]]:
    grants = grants_of(ent)
    if ALL in grants:
        return rows
    return [r for r in rows if not r.get(key) or company_in_scope(grants, str(r[key]))]


async def check_request(ent: Dict[str, Any], request: Request) -> None:
    """Scope-check every company a gated request names: path, query, or JSON body."""
    if ALL in grants_of(ent):
        return
    ids: List[str] = []
    for source in (request.path_params, request.query_params):
        cid = source.get("company_id")
        if cid:
            ids.append(str(cid))
    if request.method in ("POST", "PUT", "PATCH") and "json" in (request.headers.get("content-type") or ""):
        try:
            body = json.loads(await request.body() or b"null")
        except ValueError:
            body = None
        if isinstance(body, dict):
            if body.get("company_id"):
                ids.append(str(body["company_id"]))
            if isinstance(body.get("company_ids"), list):
                ids.extend(str(x) for x in body["company_ids"] if x)
    for cid in ids:
        require_in_scope(ent, cid)
