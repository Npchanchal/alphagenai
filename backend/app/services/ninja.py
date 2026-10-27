"""Financial Ninja worksheets. None of this writes a published GCI.

Valuation figures are the arithmetic of numbers the desk types in.
Layer indices exist only after cited observations. Hypothesis tests count
the published delivery record. They do not forecast.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

LAYERS = ("accounting", "causality", "conduct", "execution")
# Specification v4.3.1 commitment weights. Delivery is measured. The other four
# stay blank until this desk has cited observations. They are not the published GCI.
LAYER_WEIGHTS = {
    "delivery": 0.35,
    "accounting": 0.20,
    "causality": 0.20,
    "conduct": 0.15,
    "execution": 0.10,
}
# (label, phrases that match the stored sector, scale floor in percentage points, decay)
_SECTOR_SCALES = (
    ("IT services", ("it service", "information technology"), 1.0, 1.5),
    ("Pharma and healthcare", ("pharma", "healthcare", "health care"), 2.0, 1.0),
    ("Banking and financials", ("bank", "financial", "nbfc", "insurance"), 0.25, 2.0),
    ("Real estate and infrastructure", ("real estate", "infra", "construction"), 5.0, 0.8),
    ("Consumer and FMCG", ("fmcg", "consumer", "staple"), 1.5, 1.2),
)
STANCES = frozenset({"supported", "contradicted"})
MIN_OBSERVATIONS = 3
RATING_QUESTIONS = 5
# Desk questions. They are not the published index. A missing rating stays blank.
QUESTIONS = {
    "accounting": (
        ("definition_held", "How stable is the definition of the guided metric against the prior year?"),
        ("bridge_shown", "How complete is the bridge from the guided metric to the reported figure?"),
        ("one_offs_named", "How clearly are one-off items inside the metric named?"),
        ("restatement_clear", "How clearly does the filing deal with any restatement of this metric?"),
        ("segment_match", "How closely does the reported segment match the segment in the guidance?"),
    ),
    "causality": (
        ("driver_named", "How clearly did management name the driver when it gave the guidance?"),
        ("volume_price_mix", "How clearly are volume, price, and mix stated?"),
        ("acquired_separated", "How clearly is acquired growth separated from the ongoing business?"),
        ("external_vs_own", "How clearly is an external factor distinguished from the company's own action?"),
        ("same_driver", "How clearly does the result discuss the same driver as the guidance?"),
    ),
    "conduct": (
        ("cut_disclosed", "How plainly is an in-year cut or withdrawal disclosed?"),
        ("words_match", "How closely do the words in the filing match the number?"),
        ("question_answered", "How directly is a question on the call answered with a figure or a date?"),
        ("prior_miss_named", "How plainly is a prior miss named?"),
        ("metric_change", "How plainly is a change of metric disclosed?"),
    ),
    "execution": (
        ("capacity_named", "How clearly is capacity, hiring, or capital expenditure named with the guidance?"),
        ("milestone_dated", "How clearly does a milestone carry a date?"),
        ("milestone_later", "How clearly is that milestone reported in a later filing?"),
        ("spend_tied", "How clearly is the spend tied to the guided metric?"),
        ("slippage_named", "How plainly is a slip against the stated date disclosed?"),
    ),
}
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


def _read_published_gci(company_id: str) -> Optional[float]:
    """Read the published number. This does not append the score ledger."""
    from app.data.seed import get_outcomes
    from app.services.guidance_flags import audited_company_gci

    try:
        value = audited_company_gci(get_outcomes(company_id), company_id=company_id)
    except Exception:
        return None
    if value is None:
        return None
    return round(float(value), 1)


def _rate_sensitivity(kind: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Same inputs with the rate one point either way. Desk arithmetic only."""
    field = None
    noun = ""
    if kind in ("dcf", "reverse_dcf"):
        field = "discount_rate_pct"
        noun = "Discount rate"
    elif kind == "residual_income":
        field = "cost_of_equity_pct"
        noun = "Cost of equity"
    if field is None:
        return []
    try:
        rate = float(body.get(field))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return []
    builders = {"dcf": _dcf, "reverse_dcf": _reverse, "residual_income": _residual}
    build = builders[kind]
    points = []
    for delta, side in ((-1.0, "one point lower"), (1.0, "one point higher")):
        trial = dict(body)
        trial[field] = rate + delta
        try:
            figure = build(trial)["figure"]
        except HTTPException:
            continue
        points.append({"label": f"{noun} {side}", "figure": figure})
    return points


def worksheet(template: str, body: Dict[str, Any]) -> Dict[str, Any]:
    kind = (template or "").strip().lower()
    if kind == "dcf":
        pack = _dcf(body)
    elif kind == "relative":
        pack = _relative(body)
    elif kind == "residual_income":
        pack = _residual(body)
    elif kind == "reverse_dcf":
        pack = _reverse(body)
    elif kind == "asset_value":
        pack = _asset(body)
    else:
        raise HTTPException(status_code=400, detail="Unknown worksheet")
    company_id = str(body.get("company_id") or "").strip()
    pack["saved"] = False
    pack["sensitivity"] = _rate_sensitivity(kind, body) if company_id else []
    if company_id:
        pack["company_id"] = company_id
        pack["published_gci"] = _read_published_gci(company_id)
    return pack


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


def save_worksheet(org_id: str, template: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the desk's inputs when a company is named. No ledger write."""
    pack = worksheet(template, body)
    company_id = str(pack.get("company_id") or "").strip()
    if not company_id:
        return pack
    row = {
        "id": hashlib.sha256(
            f"{company_id}|{pack['template']}|{_now()}|{pack['figure']}".encode("utf-8")
        ).hexdigest()[:16],
        "company_id": company_id,
        "template": pack["template"],
        "figure": pack["figure"],
        "unit": pack["unit"],
        "inputs": pack["inputs"],
        "statement": pack["statement"],
        "published_gci": pack.get("published_gci"),
        "sensitivity": pack.get("sensitivity") or [],
        "saved_at": _now(),
    }
    with _LOCK:
        data = _load(org_id)
        rows = list(data.get("worksheets") or [])
        rows.append(row)
        data["worksheets"] = rows[-200:]
        _save(org_id, data)
    pack["saved"] = True
    pack["saved_at"] = row["saved_at"]
    pack["id"] = row["id"]
    return pack


def worksheet_record(org_id: str, company_id: str, template: Optional[str] = None) -> Dict[str, Any]:
    rows = [
        row
        for row in _load(org_id).get("worksheets") or []
        if row.get("company_id") == company_id
    ]
    history = list(reversed(rows))[:12]
    latest = None
    if template:
        latest = next((row for row in history if row.get("template") == template), None)
        if latest is None:
            older = [row for row in reversed(rows) if row.get("template") == template]
            latest = older[0] if older else None
    elif history:
        latest = history[0]
    return {
        "company_id": company_id,
        "template": template,
        "latest": latest,
        "history": history,
        "statement": WORKSHEET_LINE,
    }


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
        row["id"] = hashlib.sha256(
            f"{company_id}|{layer}|{quote}|{row['saved_at']}|{len(observations)}".encode("utf-8")
        ).hexdigest()[:16]
        observations.append(row)
        data["observations"] = observations[-400:]
        _save(org_id, data)
    return row


def delete_observation(org_id: str, obs_id: str) -> Dict[str, Any]:
    needle = (obs_id or "").strip()
    if not needle:
        raise HTTPException(status_code=404, detail="Observation not found")
    with _LOCK:
        data = _load(org_id)
        rows = list(data.get("observations") or [])
        kept = [row for row in rows if row.get("id") != needle]
        if len(kept) == len(rows):
            raise HTTPException(status_code=404, detail="Observation not found")
        data["observations"] = kept
        _save(org_id, data)
    return {"deleted": needle}


def _period(value: object) -> str:
    text = str(value or "").strip()
    if len(text) < 2 or len(text) > 16 or not text.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Period must be a short label such as FY26")
    return text


def _rating_score(value: object) -> int:
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail="Rating must be a whole number from 0 to 4")
    try:
        score = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Rating must be a whole number from 0 to 4")
    if score < 0 or score > 4:
        raise HTTPException(status_code=400, detail="Rating must be a whole number from 0 to 4")
    return score


def _question_prompt(layer: str, question: str) -> str:
    for qid, prompt in QUESTIONS.get(layer, ()):
        if qid == question:
            return prompt
    raise HTTPException(status_code=400, detail="Unknown question for this layer")


def upsert_rating(org_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    layer = str(body.get("layer") or "").strip().lower()
    if layer not in LAYERS:
        raise HTTPException(status_code=400, detail="Layer must be accounting, causality, conduct, or execution")
    question = str(body.get("question") or "").strip()
    prompt = _question_prompt(layer, question)
    quote = " ".join(str(body.get("quote") or "").split())
    if len(quote) < 12:
        raise HTTPException(status_code=400, detail="Quote the filing in at least a short sentence")
    source = str(body.get("source_url") or "").strip()
    if not source.startswith("http"):
        raise HTTPException(status_code=400, detail="A source link is required")
    company_id = str(body.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    period = _period(body.get("period"))
    row = {
        "company_id": company_id,
        "layer": layer,
        "question": question,
        "prompt": prompt,
        "period": period,
        "score": _rating_score(body.get("score")),
        "quote": quote[:500],
        "source_url": source[:500],
        "as_of": _date(body.get("as_of"), "as_of"),
        "saved_at": _now(),
    }
    with _LOCK:
        data = _load(org_id)
        ratings = [
            item
            for item in list(data.get("ratings") or [])
            if not (
                item.get("company_id") == company_id
                and item.get("layer") == layer
                and item.get("question") == question
                and item.get("period") == period
            )
        ]
        row["id"] = hashlib.sha256(
            f"{company_id}|{layer}|{question}|{period}|{row['saved_at']}|{len(ratings)}".encode("utf-8")
        ).hexdigest()[:16]
        ratings.append(row)
        data["ratings"] = ratings[-800:]
        _save(org_id, data)
    return row


def _desk_blend(company_id: str, period: str, layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    blank = {
        "period": period or None,
        "available": False,
        "level": None,
        "delivery": None,
        "statement": (
            "Desk blend appears when all four layers for that year have five cited ratings, "
            "and a delivery score for that year is on the published record. "
            "It is not the Guidance Credibility Index."
        ),
    }
    if not period or any(not layer.get("complete") for layer in layers):
        return blank
    rows = [row for row in _scored_delivery_rows(company_id) if row.get("period") == period]
    if not rows:
        blank["statement"] = (
            f"Delivery for {period} is not on the published record, so the desk blend stays blank. "
            "It is not the Guidance Credibility Index."
        )
        return blank
    delivery = sum(float(row["delivery"]) for row in rows) / len(rows)
    by_layer = {str(layer["layer"]): float(layer["level"]) for layer in layers}
    blend = (
        LAYER_WEIGHTS["delivery"] * delivery
        + LAYER_WEIGHTS["accounting"] * by_layer["accounting"]
        + LAYER_WEIGHTS["causality"] * by_layer["causality"]
        + LAYER_WEIGHTS["conduct"] * by_layer["conduct"]
        + LAYER_WEIGHTS["execution"] * by_layer["execution"]
    )
    level = round(blend, 1)
    return {
        "period": period,
        "available": True,
        "level": level,
        "delivery": round(delivery, 1),
        "statement": (
            f"Desk blend for {period} is {level}. Delivery in the blend is the average delivery score "
            f"of the closed cited rows for that year ({round(delivery, 1)}). "
            "This figure is yours. It is not the Guidance Credibility Index and it is not a recommendation."
        ),
    }


def _sheet(org_id: str, company_id: str, period: Optional[str] = None) -> Dict[str, Any]:
    ratings = [
        row
        for row in _load(org_id).get("ratings") or []
        if row.get("company_id") == company_id
    ]
    periods = sorted({str(row.get("period") or "") for row in ratings if row.get("period")})
    chosen = _period(period) if period else (periods[-1] if periods else "")
    layers = []
    for layer in LAYERS:
        questions = []
        cited = 0
        scores: List[int] = []
        for qid, prompt in QUESTIONS[layer]:
            match = [
                row
                for row in ratings
                if row.get("layer") == layer and row.get("question") == qid and (not chosen or row.get("period") == chosen)
            ]
            saved = match[-1] if match else None
            if saved is not None:
                cited += 1
                scores.append(int(saved["score"]))
            questions.append(
                {
                    "id": qid,
                    "prompt": prompt,
                    "score": None if saved is None else saved.get("score"),
                    "quote": "" if saved is None else saved.get("quote") or "",
                    "source_url": "" if saved is None else saved.get("source_url") or "",
                    "as_of": "" if saved is None else saved.get("as_of") or "",
                    "period": chosen,
                }
            )
        complete = cited == RATING_QUESTIONS
        layers.append(
            {
                "layer": layer,
                "cited": cited,
                "needed": RATING_QUESTIONS,
                "complete": complete,
                "level": round(sum(score / 4.0 for score in scores) / RATING_QUESTIONS * 100.0, 1) if complete else None,
                "questions": questions,
            }
        )
    return {
        "period": chosen,
        "periods": periods,
        "scale": "0 is absent from the filing. 4 is fully shown.",
        "layers": layers,
        "desk_blend": _desk_blend(company_id, chosen, layers),
        "statement": (
            "A layer level appears when all five questions for that year have a source. "
            "The desk blend is yours. It is not the Guidance Credibility Index and it is not a recommendation."
        ),
    }


def layer_index(org_id: str, company_id: str, period: Optional[str] = None) -> Dict[str, Any]:
    """A note-share only after three cited observations. The rating sheet stays separate."""
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
                "count": count,
                "needed": MIN_OBSERVATIONS,
                "level": round(100.0 * supported / count, 1) if published else None,
                "published": published,
            }
        )
    return {
        "company_id": company_id,
        "min_observations": MIN_OBSERVATIONS,
        "layers": layers,
        "observations": list(reversed(rows)),
        "sheet": _sheet(org_id, company_id, period),
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
    for row in _load(org_id).get("ratings") or []:
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
                "stance": "cited",
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
    from app.data.metric_catalog import display_name_for
    from app.data.seed import list_companies, outcome_from_dict
    from app.services.gci_scoring import OutcomeLabel, classify_outcome
    from app.services.score_policy import excluded_from_score

    names = {str(company.get("id")): company for company in list_companies()}
    labels = {
        OutcomeLabel.MET: "met",
        OutcomeLabel.EXCEEDED: "exceeded",
        OutcomeLabel.MISSED: "missed",
    }
    rows = []
    for company_id, raw_rows in HAND_LABELED.items():
        company = names.get(company_id) or {}
        for raw in raw_rows:
            outcome = outcome_from_dict(raw)
            if excluded_from_score(outcome):
                continue
            label = classify_outcome(outcome)
            if label not in labels:
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
                    "ticker": company.get("ticker") or company_id,
                    "name": company.get("name") or company_id,
                    "sector": company.get("sector") or "",
                    "period": outcome.period,
                    "metric": outcome.metric,
                    "metric_name": display_name_for(outcome.metric),
                    "outcome": labels[label],
                    "missed": label == OutcomeLabel.MISSED,
                    "downward": downward,
                }
            )
    return rows


def _count_bucket() -> Dict[str, int]:
    return {"met": 0, "exceeded": 0, "missed": 0}


def _stored_flag_rows() -> Dict[str, List[Dict[str, Any]]]:
    """Analyst-set flags only. Heuristic suggestions stay off this count."""
    from app.data.seed import list_companies
    from app.services.guidance_flags import list_audit_flag_records

    grouped: Dict[str, List[Dict[str, Any]]] = {"guidance_withdrawal": [], "definition_shift": []}
    for company in list_companies():
        company_id = str(company.get("id") or "")
        for rec in list_audit_flag_records(company_id):
            flag = str(rec.get("flag") or "")
            if flag not in grouped:
                continue
            grouped[flag].append(
                {
                    "company_id": company_id,
                    "ticker": company.get("ticker") or company_id,
                    "name": company.get("name") or company_id,
                    "flag": flag,
                    "source_url": rec.get("source_url"),
                    "set_at": rec.get("set_at"),
                }
            )
    return grouped


def _share(flags: List[bool]) -> Optional[float]:
    if not flags:
        return None
    return round(100.0 * sum(1 for flag in flags if flag) / len(flags), 1)


def _sector_scale(sector: str) -> Optional[Dict[str, Any]]:
    text = (sector or "").lower()
    for label, phrases, floor, decay in _SECTOR_SCALES:
        if any(phrase in text for phrase in phrases):
            return {"sector_rule": label, "scale_floor": floor, "decay": decay}
    return None


def _delivery_score(low: float, high: float, actual: float, scale: float, decay: float) -> float:
    """Specification Layer 2. Inside the band is 100. Either side decays."""
    half = (high - low) / 2.0
    width = max(half, scale)
    outside = max(low - actual, 0.0, actual - high)
    if outside <= 0:
        return 100.0
    if width <= 0:
        return 0.0
    return 100.0 * math.exp(-decay * outside / width)


def _blend(delivery: float) -> Dict[str, float]:
    """Flat rubrics. A constant rubric shifts the level and does not change the path shape."""
    floor = LAYER_WEIGHTS["delivery"] * delivery
    return {"floor": floor, "ceiling": floor + (1.0 - LAYER_WEIGHTS["delivery"]) * 100.0}


def _metric_mean(rows: List[Dict[str, Any]], period_rank: Dict[str, int]) -> Optional[float]:
    from app.services.gci_scoring import _recency_weight

    by_period: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_period.setdefault(row["period"], []).append(row)
    num = 0.0
    den = 0.0
    for period, group in by_period.items():
        rank = period_rank.get(period)
        if rank is None:
            continue
        score = sum(item["delivery"] for item in group) / len(group)
        confidence = sum(item["confidence"] for item in group) / len(group)
        weight = _recency_weight(rank) * confidence
        num += weight * score
        den += weight
    if den <= 0:
        return None
    return num / den


def _company_delivery(rows: List[Dict[str, Any]], outcomes: List[Any]) -> Optional[float]:
    """Recency and evidence weights, the same rules as the published composite, on delivery scores."""
    from app.services.gci_scoring import _periods_newest_first

    if not rows:
        return None
    periods = _periods_newest_first(outcomes)
    period_rank = {period: index + 1 for index, period in enumerate(periods)}
    by_metric: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_metric.setdefault(row["metric"], []).append(row)
    means: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for metric, group in by_metric.items():
        mean = _metric_mean(group, period_rank)
        if mean is None:
            continue
        means[metric] = mean
        counts[metric] = len({item["period"] for item in group if item["period"] in period_rank})
    if not means:
        return None
    deep = {metric for metric, count in counts.items() if count >= 2}
    composite = {metric: value for metric, value in means.items() if metric in deep} if deep else means
    num = 0.0
    den = 0.0
    for metric, value in composite.items():
        weight = float(min(counts.get(metric, 1), 5))
        num += weight * value
        den += weight
    if den <= 0:
        return None
    return num / den


def _scored_delivery_rows(company_id: str) -> List[Dict[str, Any]]:
    from app.data.metric_catalog import display_name_for, metric_is_rate
    from app.data.seed import get_outcomes
    from app.services.gci_scoring import outcome_score_v4

    sector = ""
    from app.data.seed import list_companies

    for company in list_companies():
        if company.get("id") == company_id:
            sector = str(company.get("sector") or "")
            break
    scale = _sector_scale(sector)
    rows = []
    for outcome in get_outcomes(company_id):
        published = outcome_score_v4(outcome)
        if published is None or outcome.guided_low is None or outcome.guided_high is None:
            continue
        if outcome.actual_value is None:
            continue
        rate = metric_is_rate(outcome.metric)
        floor = float(scale["scale_floor"]) if scale and rate else 0.0
        decay = float(scale["decay"]) if scale else 1.0
        delivery = _delivery_score(
            float(outcome.guided_low),
            float(outcome.guided_high),
            float(outcome.actual_value),
            floor,
            decay,
        )
        band = _blend(delivery)
        rubric = (published - band["floor"]) / (1.0 - LAYER_WEIGHTS["delivery"])
        rows.append(
            {
                "period": outcome.period,
                "metric": outcome.metric,
                "metric_name": display_name_for(outcome.metric),
                "as_of": outcome.as_of,
                "band_low": float(outcome.guided_low),
                "band_high": float(outcome.guided_high),
                "actual": float(outcome.actual_value),
                "confidence": min(max(float(outcome.confidence), 0.5), 1.0),
                "delivery": delivery,
                "published_year": published,
                "floor": band["floor"],
                "ceiling": band["ceiling"],
                "rubric_needed": rubric,
                "reachable": 0.0 <= rubric <= 100.0,
                "scale_applied": bool(scale and rate),
                "_outcome": outcome,
            }
        )
    return rows


def _round_year(row: Dict[str, Any], in_composite: bool) -> Dict[str, Any]:
    return {
        "period": row["period"],
        "metric": row["metric"],
        "metric_name": row["metric_name"],
        "as_of": row["as_of"],
        "band_low": row["band_low"],
        "band_high": row["band_high"],
        "actual": row["actual"],
        "delivery": round(row["delivery"], 1),
        "published_year": round(row["published_year"], 1),
        "floor": round(row["floor"], 1),
        "ceiling": round(row["ceiling"], 1),
        "rubric_needed": round(row["rubric_needed"], 1),
        "reachable": row["reachable"],
        "in_composite": in_composite,
        "scale_applied": row["scale_applied"],
    }


def _num(value: float) -> str:
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def _company_meta(company_id: str) -> Dict[str, Any]:
    from app.data.seed import list_companies

    for company in list_companies():
        if company.get("id") == company_id:
            return company
    return {}


def _heatmap(years: List[Dict[str, Any]]) -> Dict[str, Any]:
    columns = [
        {
            "key": f"{row['period']}|{row['metric']}",
            "period": row["period"],
            "metric_name": row["metric_name"],
            "in_composite": row["in_composite"],
        }
        for row in years
    ]
    fields = (
        ("delivery", "Delivery"),
        ("published_year", "Published year"),
        ("floor", "Four layers at 0"),
        ("ceiling", "Four layers at 100"),
    )
    return {
        "columns": columns,
        "rows": [{"id": key, "label": label, "values": [row[key] for row in years]} for key, label in fields],
    }


def chronology_for(company_id: str) -> Dict[str, Any]:
    """Opening guidance, each in-year revision, and the reported actual, in date order."""
    from app.data.metric_catalog import display_name_for
    from app.data.seed import get_outcomes

    company = _company_meta(company_id)
    if str(company.get("data_quality") or "") != "hand_labeled":
        return {
            "events": [],
            "statement": "This name is on the demo seed. A filing chronology starts from a hand-labeled row.",
        }
    scored = {(row["period"], row["metric"]): row for row in _scored_delivery_rows(company_id)}
    events: List[Dict[str, Any]] = []
    kind_order = {"guidance": 0, "revision": 1, "actual": 2}
    for outcome in get_outcomes(company_id):
        metric_name = display_name_for(outcome.metric)
        scored_row = scored.get((outcome.period, outcome.metric))
        if outcome.guidance_as_of or outcome.guidance_quote:
            band = ""
            if outcome.guided_low is not None and outcome.guided_high is not None:
                band = f"Opening band {_num(outcome.guided_low)}–{_num(outcome.guided_high)}."
            events.append(
                {
                    "date": outcome.guidance_as_of or "",
                    "kind": "guidance",
                    "period": outcome.period,
                    "metric": outcome.metric,
                    "metric_name": metric_name,
                    "text": band,
                    "quote": outcome.guidance_quote or None,
                    "source_url": outcome.guidance_source_url or None,
                }
            )
        for revision in outcome.revisions or ():
            low = revision.get("guided_low")
            high = revision.get("guided_high")
            text = ""
            if low is not None and high is not None:
                text = f"Band revised to {_num(float(low))}–{_num(float(high))}."
            events.append(
                {
                    "date": str(revision.get("as_of") or ""),
                    "kind": "revision",
                    "period": outcome.period,
                    "metric": outcome.metric,
                    "metric_name": metric_name,
                    "text": text,
                    "quote": revision.get("quote") or None,
                    "source_url": revision.get("source_url") or None,
                }
            )
        if outcome.as_of and outcome.actual_value is not None:
            if scored_row is None:
                text = (
                    f"Actual {_num(float(outcome.actual_value))}. "
                    "The row has no cited opening band, so it stays out of the delivery worksheet."
                )
            else:
                text = (
                    f"Actual {_num(float(outcome.actual_value))}. "
                    f"Delivery {round(scored_row['delivery'], 1)}. "
                    f"Published year-score {round(scored_row['published_year'], 1)}."
                )
            events.append(
                {
                    "date": outcome.as_of,
                    "kind": "actual",
                    "period": outcome.period,
                    "metric": outcome.metric,
                    "metric_name": metric_name,
                    "text": text,
                    "quote": outcome.quote_span or None,
                    "source_url": outcome.source_url or None,
                }
            )
    events.sort(key=lambda row: (row["date"] or "9999", row["period"], kind_order.get(row["kind"], 9), row["metric"]))
    if events:
        statement = "Opening guidance, each in-year revision, and the reported actual, in date order."
    else:
        statement = "No hand-labeled guidance date or actual is on file for this company."
    return {"statement": statement, "events": events}


def calculation_for(company_id: str) -> Optional[Dict[str, Any]]:
    """Specification delivery and the legal range of the four rubric layers.

    Rubric ratings are not inferred. The published GCI is reported beside the
    worksheet and is not rewritten.
    """
    from app.data.seed import get_outcomes, list_companies
    from app.services.guidance_flags import audited_company_gci

    rows = _scored_delivery_rows(company_id)
    if not rows:
        return None
    outcomes = [row["_outcome"] for row in rows]
    delivery = _company_delivery(rows, outcomes)
    if delivery is None:
        return None
    band = _blend(delivery)
    published = audited_company_gci(get_outcomes(company_id), company_id=company_id)
    name = company_id
    sector = ""
    for company in list_companies():
        if company.get("id") == company_id:
            name = str(company.get("name") or company_id)
            sector = str(company.get("sector") or "")
            break
    scale = _sector_scale(sector)
    periods_by_metric: Dict[str, set] = {}
    for row in rows:
        periods_by_metric.setdefault(row["metric"], set()).add(row["period"])
    deep_metrics = {metric for metric, periods in periods_by_metric.items() if len(periods) >= 2}
    use_deep = bool(deep_metrics)
    years = [
        _round_year(row, (row["metric"] in deep_metrics) if use_deep else True)
        for row in sorted(rows, key=lambda item: (item["as_of"] or "", item["period"], item["metric"]))
    ]
    above = sum(1 for row in rows if row["published_year"] > row["ceiling"])
    dates = sorted({row["as_of"] for row in rows if row["as_of"]})
    path = []
    all_outcomes = get_outcomes(company_id)
    for date in dates:
        subset_outcomes = [item for item in all_outcomes if item.as_of and item.as_of <= date]
        subset_rows = [row for row in rows if row["as_of"] and row["as_of"] <= date]
        level = _company_delivery(subset_rows, [row["_outcome"] for row in subset_rows])
        if level is None:
            continue
        subset_band = _blend(level)
        published_then = audited_company_gci(subset_outcomes, company_id=company_id)
        path.append(
            {
                "as_of": date,
                "published": None if published_then is None else round(float(published_then), 1),
                "delivery": round(level, 1),
                "floor": round(subset_band["floor"], 1),
                "ceiling": round(subset_band["ceiling"], 1),
            }
        )
    published_text = "unpublished" if published is None else f"{published}"
    sentence = (
        f"Delivery on the opening band is {round(delivery, 1)}. "
        f"With the four layers at 0 the blend is {round(band['floor'], 1)}. "
        f"With them at 100 it is {round(band['ceiling'], 1)}. "
        f"The published Guidance Credibility Index is {published_text}. This page does not change it."
    )
    if above:
        sentence += (
            f" {above} published year-score{'s sit' if above != 1 else ' sits'} above the highest blend these weights can return."
        )
    sentence += " The four layers have no ratings on this file."
    return {
        "company_id": company_id,
        "name": name,
        "sector": sector or None,
        "sector_rule": None if scale is None else scale["sector_rule"],
        "scale_floor": None if scale is None else scale["scale_floor"],
        "decay": None if scale is None else scale["decay"],
        "weights": dict(LAYER_WEIGHTS),
        "published_gci": published,
        "delivery": round(delivery, 1),
        "floor": round(band["floor"], 1),
        "ceiling": round(band["ceiling"], 1),
        "years_above_ceiling": above,
        "rubrics_on_file": False,
        "years": years,
        "path": path,
        "heatmap": _heatmap(years),
        "chronology": chronology_for(company_id),
        "statement": sentence,
    }


def calculation_book() -> Dict[str, Any]:
    """Universe listing, plus one worksheet per company with a closed, cited guidance row."""
    from app.data.seed import get_data
    from app.services.repository import list_company_summaries

    companies = []
    for company_id in sorted(get_data().get("outcomes") or {}):
        report = calculation_for(company_id)
        if report is not None:
            companies.append(report)
    companies.sort(key=lambda row: row["name"].lower())
    by_id = {row["company_id"]: row for row in companies}
    listing = []
    for summary in list_company_summaries():
        report = by_id.get(summary.id)
        listing.append(
            {
                "company_id": summary.id,
                "ticker": summary.ticker,
                "name": summary.name,
                "sector": summary.sector,
                "data_quality": summary.data_quality,
                "has_worksheet": report is not None,
                "published_gci": None if report is None else report["published_gci"],
            }
        )
    listing.sort(key=lambda row: (not row["has_worksheet"], row["name"].lower()))
    return {
        "statement": (
            "The listing is every name on the Guidance Credibility Index universe. "
            "Open a name for the delivery worksheet, the score heatmap, and the filing chronology. "
            "Delivery follows the specification's outside-band formula. "
            "The four rubric layers have no ratings, so a worksheet shows the range they are allowed to add. "
            "None of this is the Guidance Credibility Index."
        ),
        "listing": listing,
        "companies": companies,
    }


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
    pair_rows = []
    for group in by_company.values():
        ordered = sorted(group, key=lambda row: str(row["period"]))
        if len(ordered) < 2:
            continue
        prior, latest = ordered[-2], ordered[-1]
        pair_rows.append(
            {
                "company_id": prior["company_id"],
                "ticker": prior["ticker"],
                "name": prior["name"],
                "prior_period": prior["period"],
                "latest_period": latest["period"],
                "prior_missed": prior["missed"],
                "latest_missed": latest["missed"],
                "both_missed": bool(prior["missed"] and latest["missed"]),
            }
        )
    by_name: Dict[str, Dict[str, Any]] = {}
    by_sector: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        company_bucket = by_name.setdefault(
            row["company_id"],
            {
                "company_id": row["company_id"],
                "ticker": row["ticker"],
                "name": row["name"],
                "sector": row["sector"],
                **_count_bucket(),
            },
        )
        company_bucket[row["outcome"]] += 1
        sector_bucket = by_sector.setdefault(
            row["sector"] or "Equity",
            {"sector": row["sector"] or "Equity", **_count_bucket()},
        )
        sector_bucket[row["outcome"]] += 1
    flags = _stored_flag_rows()
    public_rows = [
        {key: row[key] for key in ("company_id", "ticker", "name", "sector", "period", "metric_name", "outcome", "downward")}
        for row in rows
    ]
    return {
        "statement": (
            "These are counts of closed, cited guidance rows already on the published record. "
            "They are not a forecast and they do not use prices."
        ),
        "rows": public_rows,
        "by_company": sorted(by_name.values(), key=lambda item: str(item["name"]).lower()),
        "by_sector": sorted(by_sector.values(), key=lambda item: str(item["sector"]).lower()),
        "flags": {
            "guidance_withdrawal": {"n": len(flags["guidance_withdrawal"]), "rows": flags["guidance_withdrawal"]},
            "definition_shift": {"n": len(flags["definition_shift"]), "rows": flags["definition_shift"]},
        },
        "downward_revision": {
            "sufficient": revision_ready,
            "with_revision": {
                "n": len(with_revision),
                "miss_share_pct": _share(with_revision) if revision_ready else None,
            },
            "without_revision": {
                "n": len(without_revision),
                "miss_share_pct": _share(without_revision) if revision_ready else None,
            },
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
            "rows": pair_rows,
            "statement": (
                "Share of companies whose last two closed rows were both misses."
                if persistence_ready
                else "Fewer than five companies have two closed rows on the published record."
            ),
        },
    }
