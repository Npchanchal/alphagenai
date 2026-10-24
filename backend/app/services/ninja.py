"""Financial Ninja worksheets. None of this writes a published GCI.

Valuation figures are the arithmetic of numbers the desk types in.
Layer indices exist only after cited observations. Hypothesis tests count
the published delivery record. They do not forecast.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

LAYERS = ("accounting", "causality", "conduct", "execution")
STANCES = frozenset({"supported", "contradicted"})
MIN_OBSERVATIONS = 3
TEMPLATES = ("dcf", "relative", "residual_income", "reverse_dcf", "asset_value")
WORKSHEET_LINE = (
    "This worksheet figure is yours. It is not the Guidance Credibility Index and it is not a recommendation."
)
_LOCK = threading.Lock()
_PACKAGED = Path(__file__).resolve().parents[1] / "data" / "ninja"


def _root() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "ninja" if env else _PACKAGED


def _org_path(org_id: str) -> Path:
    digest = hashlib.sha256(org_id.encode("utf-8")).hexdigest()[:16]
    return _root() / f"{digest}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date(value: object, field: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM-DD")
    return text


def _number(value: object, field: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field} must be a number")
    if number != number or number in (float("inf"), float("-inf")):
        raise HTTPException(status_code=400, detail=f"{field} must be a finite number")
    return number


def _pack(template: str, figure: float, unit: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "template": template,
        "figure": round(figure, 4),
        "unit": unit,
        "inputs": inputs,
        "statement": WORKSHEET_LINE,
    }


def worksheet(template: str, body: Dict[str, Any]) -> Dict[str, Any]:
    kind = (template or "").strip().lower()
    if kind == "dcf":
        return _dcf(body)
    if kind == "relative":
        return _relative(body)
    if kind == "residual_income":
        return _residual(body)
    if kind == "reverse_dcf":
        return _reverse(body)
    if kind == "asset_value":
        return _asset(body)
    raise HTTPException(status_code=400, detail="Unknown worksheet")


def _dcf(body: Dict[str, Any]) -> Dict[str, Any]:
    flows = body.get("cash_flows")
    if not isinstance(flows, list) or not flows or len(flows) > 30:
        raise HTTPException(status_code=400, detail="Enter between 1 and 30 cash flows")
    cash_flows = [_number(item, "cash flow") for item in flows]
    rate = _number(body.get("discount_rate_pct"), "discount rate") / 100.0
    if rate <= -1:
        raise HTTPException(status_code=400, detail="Discount rate must be above -100")
    terminal = _number(body.get("terminal_value"), "terminal value")
    if terminal < 0:
        raise HTTPException(status_code=400, detail="Terminal value cannot be negative")
    present = 0.0
    for year, cash in enumerate(cash_flows, start=1):
        present += cash / (1.0 + rate) ** year
    present += terminal / (1.0 + rate) ** len(cash_flows)
    return _pack(
        "dcf",
        present,
        "currency",
        {"cash_flows": cash_flows, "discount_rate_pct": body.get("discount_rate_pct"), "terminal_value": terminal},
    )


def _relative(body: Dict[str, Any]) -> Dict[str, Any]:
    metric = _number(body.get("metric"), "metric")
    multiple = _number(body.get("multiple"), "multiple")
    return _pack("relative", metric * multiple, "currency", {"metric": metric, "multiple": multiple})


def _residual(body: Dict[str, Any]) -> Dict[str, Any]:
    book = _number(body.get("book_value"), "book value")
    if book <= 0:
        raise HTTPException(status_code=400, detail="Book value must be positive")
    roe = _number(body.get("roe_pct"), "return on equity") / 100.0
    cost = _number(body.get("cost_of_equity_pct"), "cost of equity") / 100.0
    if cost <= -1:
        raise HTTPException(status_code=400, detail="Cost of equity must be above -100")
    payout = _number(body.get("payout_pct"), "payout") / 100.0
    if payout < 0 or payout > 1:
        raise HTTPException(status_code=400, detail="Payout must be between 0 and 100")
    try:
        years = int(body.get("years"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Years must be a whole number")
    if years < 1 or years > 15:
        raise HTTPException(status_code=400, detail="Years must be from 1 to 15")
    value = book
    running = book
    for year in range(1, years + 1):
        residual = (roe - cost) * running
        value += residual / (1.0 + cost) ** year
        running = running * (1.0 + roe * (1.0 - payout))
    return _pack(
        "residual_income",
        value,
        "currency",
        {
            "book_value": book,
            "roe_pct": body.get("roe_pct"),
            "cost_of_equity_pct": body.get("cost_of_equity_pct"),
            "payout_pct": body.get("payout_pct"),
            "years": years,
        },
    )


def _reverse(body: Dict[str, Any]) -> Dict[str, Any]:
    price = _number(body.get("price"), "price")
    cash = _number(body.get("cash_flow"), "cash flow")
    rate = _number(body.get("discount_rate_pct"), "discount rate") / 100.0
    if price <= 0 or cash <= 0 or rate <= 0:
        raise HTTPException(status_code=400, detail="Price, cash flow, and discount rate must be positive")
    growth = (rate * price - cash) / (price + cash)
    if growth >= rate:
        raise HTTPException(
            status_code=400,
            detail="These inputs do not produce a growth rate below the discount rate",
        )
    return _pack(
        "reverse_dcf",
        growth * 100.0,
        "percent",
        {"price": price, "cash_flow": cash, "discount_rate_pct": body.get("discount_rate_pct")},
    )


def _asset(body: Dict[str, Any]) -> Dict[str, Any]:
    items = body.get("items")
    if not isinstance(items, list) or not items or len(items) > 40:
        raise HTTPException(status_code=400, detail="Enter between 1 and 40 asset and liability lines")
    cleaned = []
    total = 0.0
    for raw in items:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail="Each line needs a name and an amount")
        name = str(raw.get("name") or "").strip()[:80]
        if not name:
            raise HTTPException(status_code=400, detail="Each line needs a name")
        amount = _number(raw.get("amount"), name)
        cleaned.append({"name": name, "amount": amount})
        total += amount
    return _pack("asset_value", total, "currency", {"items": cleaned})


def _load(org_id: str) -> Dict[str, Any]:
    path = _org_path(org_id)
    if not path.exists():
        return {"observations": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(org_id: str, data: Dict[str, Any]) -> None:
    path = _org_path(org_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def add_observation(org_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    layer = str(body.get("layer") or "").strip().lower()
    if layer not in LAYERS:
        raise HTTPException(status_code=400, detail="Layer must be accounting, causality, conduct, or execution")
    stance = str(body.get("stance") or "").strip().lower()
    if stance not in STANCES:
        raise HTTPException(status_code=400, detail="Stance must be supported or contradicted")
    quote = " ".join(str(body.get("quote") or "").split())
    if len(quote) < 12:
        raise HTTPException(status_code=400, detail="Quote the filing in at least a short sentence")
    source = str(body.get("source_url") or "").strip()
    if not source.startswith("http"):
        raise HTTPException(status_code=400, detail="A source link is required")
    company_id = str(body.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    row = {
        "company_id": company_id,
        "layer": layer,
        "stance": stance,
        "quote": quote[:500],
        "source_url": source[:500],
        "as_of": _date(body.get("as_of"), "as_of"),
        "saved_at": _now(),
    }
    with _LOCK:
        data = _load(org_id)
        observations = list(data.get("observations") or [])
        observations.append(row)
        data["observations"] = observations[-400:]
        _save(org_id, data)
    return row


def layer_index(org_id: str, company_id: str) -> Dict[str, Any]:
    """A level only after three cited observations. Otherwise the layer is unpublished."""
    rows = [
        row
        for row in _load(org_id).get("observations") or []
        if row.get("company_id") == company_id
    ]
    layers = []
    for layer in LAYERS:
        own = [row for row in rows if row.get("layer") == layer]
        supported = sum(1 for row in own if row.get("stance") == "supported")
        contradicted = sum(1 for row in own if row.get("stance") == "contradicted")
        count = supported + contradicted
        published = count >= MIN_OBSERVATIONS
        layers.append(
            {
                "layer": layer,
                "supported": supported,
                "contradicted": contradicted,
                "level": round(100.0 * supported / count, 1) if published else None,
                "published": published,
            }
        )
    return {
        "company_id": company_id,
        "min_observations": MIN_OBSERVATIONS,
        "layers": layers,
        "statement": (
            "A layer index is the share of this desk's cited observations marked supported. "
            "It is unpublished until three observations are on file. It is not the Guidance Credibility Index."
        ),
    }


NOTE_SKILLS = ("company_note", "thematic_note", "sector_note")


def profile_quotes(org_id: str, company_id: str) -> Dict[str, Any]:
    """Cited text for the dossier. The index level stays off this payload."""
    from app.services.agent.run_store import latest_skill_notes

    grouped = {layer: [] for layer in LAYERS}
    for row in _load(org_id).get("observations") or []:
        if row.get("company_id") != company_id:
            continue
        layer = row.get("layer")
        if layer not in grouped:
            continue
        grouped[layer].append(
            {
                "quote": row.get("quote"),
                "source_url": row.get("source_url"),
                "as_of": row.get("as_of"),
                "stance": row.get("stance"),
            }
        )
    from app.data.gci_score_cache import get_listing_score

    sector = str((get_listing_score(company_id) or {}).get("sector") or "")
    return {
        "company_id": company_id,
        "layers": grouped,
        "notes": latest_skill_notes(org_id, company_id, NOTE_SKILLS),
        "sector": sector or None,
        "note": "Cited notes on this desk. These sentences are not a score.",
    }


def sector_taxonomy() -> Dict[str, Any]:
    """The sector already stored on each listing. Not a second map."""
    from app.data.gci_score_cache import load_cache

    counts: Dict[str, int] = {}
    for row in (load_cache().get("scores") or {}).values():
        if not isinstance(row, dict):
            continue
        name = str(row.get("sector") or "Equity")
        counts[name] = counts.get(name, 0) + 1
    return {
        "note": (
            "Company, thematic, and sector notes use the sector already stored on the company. "
            "This list does not assign a second sector."
        ),
        "sectors": [{"sector": name, "companies": count} for name, count in sorted(counts.items())],
    }


def _delivery_rows() -> List[Dict[str, Any]]:
    from app.data.hand_labeled import HAND_LABELED
    from app.data.seed import outcome_from_dict
    from app.services.gci_scoring import OutcomeLabel, classify_outcome
    from app.services.score_policy import excluded_from_score

    rows = []
    for company_id, raw_rows in HAND_LABELED.items():
        for raw in raw_rows:
            outcome = outcome_from_dict(raw)
            if excluded_from_score(outcome):
                continue
            label = classify_outcome(outcome)
            if label not in (OutcomeLabel.MET, OutcomeLabel.EXCEEDED, OutcomeLabel.MISSED):
                continue
            opening = outcome.guided_high
            downward = False
            for revision in outcome.revisions or ():
                revised = revision.get("guided_high") if isinstance(revision, dict) else None
                if opening is not None and revised is not None and float(revised) < float(opening):
                    downward = True
            rows.append(
                {
                    "company_id": company_id,
                    "period": outcome.period,
                    "missed": label == OutcomeLabel.MISSED,
                    "downward": downward,
                }
            )
    return rows


def _share(flags: List[bool]) -> Optional[float]:
    if not flags:
        return None
    return round(100.0 * sum(1 for flag in flags if flag) / len(flags), 1)


def hypothesis_tests() -> Dict[str, Any]:
    """Counts on the published delivery record. No prices and no forecast."""
    rows = _delivery_rows()
    with_revision = [row["missed"] for row in rows if row["downward"]]
    without_revision = [row["missed"] for row in rows if not row["downward"]]
    revision_ready = len(with_revision) >= 5 and len(without_revision) >= 5
    by_company: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_company.setdefault(row["company_id"], []).append(row)
    pairs = []
    for group in by_company.values():
        ordered = sorted(group, key=lambda row: str(row["period"]))
        if len(ordered) >= 2:
            pairs.append((ordered[-2]["missed"], ordered[-1]["missed"]))
    both_missed = [prior and latest for prior, latest in pairs]
    persistence_ready = len(both_missed) >= 5
    return {
        "statement": (
            "These are counts of closed, cited guidance rows already on the published record. "
            "They are not a forecast and they do not use prices."
        ),
        "downward_revision": {
            "sufficient": revision_ready,
            "with_revision": {"n": len(with_revision), "miss_share_pct": _share(with_revision)},
            "without_revision": {"n": len(without_revision), "miss_share_pct": _share(without_revision)},
            "statement": (
                "Miss share among rows whose in-year band was cut, beside rows that were not."
                if revision_ready
                else "The published record does not yet have five rows on each side of this comparison."
            ),
        },
        "persistence": {
            "sufficient": persistence_ready,
            "companies": len(both_missed),
            "both_missed_share_pct": _share(both_missed) if persistence_ready else None,
            "statement": (
                "Share of companies whose last two closed rows were both misses."
                if persistence_ready
                else "Fewer than five companies have two closed rows on the published record."
            ),
        },
    }
