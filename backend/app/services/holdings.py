"""Holdings look-through. Reads published scores. Does not recompute or write a GCI.

A line with no published score stays out of the weighted figure and is named in
the gap list. Cash, debt, indirect holdings, and unknown ISINs stay out too.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

RESIDUAL_KINDS = frozenset({"cash", "debt", "indirect", "other"})
MAX_LINES = 500
_LOCK = threading.Lock()
_PACKAGED = Path(__file__).resolve().parents[1] / "data" / "holdings"


def _root() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "holdings" if env else _PACKAGED


def _org_path(org_id: str) -> Path:
    digest = hashlib.sha256(org_id.encode("utf-8")).hexdigest()[:16]
    return _root() / f"{digest}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_of(value: object) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="as_of must be YYYY-MM-DD")
    return text


def _weight(value: object) -> float:
    try:
        weight = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Each line needs a numeric weight")
    if weight < 0 or weight != weight or weight in (float("inf"), float("-inf")):
        raise HTTPException(status_code=400, detail="Weights must be zero or positive")
    return weight


def build_lookthrough(
    lines: List[Dict[str, Any]],
    *,
    as_of: str,
    resolve_isin: Callable[[str], Optional[Dict[str, Any]]],
    published_score: Callable[[str], Optional[Dict[str, Any]]],
    commitment_counts: Optional[Callable[[str], int]] = None,
    universe_gci: Optional[float] = None,
    scheme: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Pure given the two readers. Missing scores are omitted from the weighted figure."""
    if not lines:
        raise HTTPException(status_code=400, detail="Add at least one holdings line")
    if len(lines) > MAX_LINES:
        raise HTTPException(status_code=400, detail=f"At most {MAX_LINES} lines")

    scored: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    residual: List[Dict[str, Any]] = []
    weight_sum = 0.0
    covered_weight = 0.0
    weighted = 0.0

    for raw in lines:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail="Each line must be an object")
        weight = _weight(raw.get("weight"))
        weight_sum += weight
        kind = str(raw.get("residual") or "").strip().lower()
        isin = str(raw.get("isin") or "").strip().upper().replace(" ", "")
        name = str(raw.get("name") or "").strip()
        if kind:
            if kind not in RESIDUAL_KINDS:
                raise HTTPException(
                    status_code=400,
                    detail="residual must be cash, debt, indirect, or other",
                )
            residual.append({"kind": kind, "name": name or kind, "weight": weight})
            continue
        if not isin:
            raise HTTPException(
                status_code=400,
                detail="Each company line needs an ISIN, or a residual kind",
            )
        company = resolve_isin(isin)
        if not company:
            gaps.append(
                {
                    "isin": isin,
                    "name": name or isin,
                    "weight": weight,
                    "reason": "unresolved",
                }
            )
            continue
        cid = str(company.get("id") or "")
        published = published_score(cid) or {}
        gci = published.get("gci_score")
        row = {
            "isin": isin,
            "company_id": cid,
            "name": name or company.get("name") or cid,
            "ticker": company.get("ticker"),
            "weight": weight,
            "gci_score": gci,
            "confidence_tier": published.get("confidence_tier"),
            "score_as_of": published.get("as_of"),
            "open_commitments": commitment_counts(cid) if commitment_counts else None,
        }
        if gci is None:
            row["reason"] = "unscored"
            gaps.append(row)
            continue
        scored.append(row)
        covered_weight += weight
        weighted += weight * float(gci)

    if weight_sum <= 0:
        raise HTTPException(status_code=400, detail="Weights must sum to more than zero")

    covered_gci = round(weighted / covered_weight, 1) if covered_weight else None
    gap_weight = sum(float(g["weight"]) for g in gaps)
    residual_weight = sum(float(r["weight"]) for r in residual)

    def _pct(part: float) -> float:
        return round(100.0 * part / weight_sum, 1)

    return {
        "product": "CiteAlpha Holdings",
        "as_of": as_of,
        "weight_sum": round(weight_sum, 4),
        "covered_weight": round(covered_weight, 4),
        "covered_weight_pct": _pct(covered_weight),
        "unscored_weight_pct": _pct(gap_weight),
        "residual_weight_pct": _pct(residual_weight),
        "covered_gci": covered_gci,
        "scored": scored,
        "gaps": gaps,
        "residual": residual,
        "manager": _manager(covered_gci, scored, universe_gci),
        "scheme": _scheme(scheme or []),
        "statement": _statement(covered_gci, _pct(covered_weight), _pct(gap_weight), _pct(residual_weight)),
        "note": (
            "Weighted published GCI of the holdings that have a score. "
            "Names without a score are listed and left out of the figure. "
            "Delivery tilt compares that weighted figure with the equal-weight figure of the same names. "
            "Scheme change uses only the scheme values in this file."
        ),
    }


def _manager(
    covered_gci: Optional[float],
    scored: List[Dict[str, Any]],
    universe_gci: Optional[float],
) -> Dict[str, Any]:
    """Weight versus equal weight on the same published scores. Not a return."""
    gcis = [float(row["gci_score"]) for row in scored if row.get("gci_score") is not None]
    equal = round(sum(gcis) / len(gcis), 1) if gcis else None
    tilt = None if covered_gci is None or equal is None else round(float(covered_gci) - equal, 1)
    versus_universe = (
        None
        if covered_gci is None or universe_gci is None
        else round(float(covered_gci) - float(universe_gci), 1)
    )
    if tilt is None:
        text = "Delivery tilt needs at least one holding with a published GCI."
    else:
        text = (
            f"Delivery tilt on this file is {tilt} points: the weighted published GCI "
            f"minus the equal-weight published GCI of the same scored names ({equal})."
        )
        if versus_universe is not None:
            text += (
                f" Against the equal-weight published GCI of the scored companies on the published list "
                f"({universe_gci}), the gap is {versus_universe} points."
            )
    return {
        "equal_weight_gci": equal,
        "delivery_tilt": tilt,
        "universe_gci": universe_gci,
        "versus_universe": versus_universe,
        "statement": text,
    }


def _scheme(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Change between scheme values the desk typed in. Not a CiteAlpha return."""
    cleaned: List[Dict[str, Any]] = []
    for raw in points:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail="Each scheme point needs a date and a value")
        as_of = _as_of(raw.get("as_of"))
        try:
            value = float(raw.get("value"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Each scheme point needs a numeric value")
        if value != value or value in (float("inf"), float("-inf")):
            raise HTTPException(status_code=400, detail="Scheme values must be finite")
        cleaned.append({"as_of": as_of, "value": value})
    if len(cleaned) < 2:
        return {
            "available": False,
            "points": cleaned,
            "change_pct": None,
            "statement": "Add two dated scheme values to see the change between them.",
        }
    ordered = sorted(cleaned, key=lambda row: row["as_of"])
    first, last = ordered[0], ordered[-1]
    if float(first["value"]) == 0:
        raise HTTPException(status_code=400, detail="The first scheme value cannot be zero")
    change = round(100.0 * (float(last["value"]) - float(first["value"])) / float(first["value"]), 1)
    return {
        "available": True,
        "points": ordered,
        "from_date": first["as_of"],
        "to_date": last["as_of"],
        "from_value": first["value"],
        "to_value": last["value"],
        "change_pct": change,
        "statement": (
            f"Scheme values in this file move from {first['value']} on {first['as_of']} "
            f"to {last['value']} on {last['as_of']}, a change of {change}%. "
            "This is the change in the values you entered."
        ),
    }


def _statement(
    covered_gci: Optional[float],
    covered_pct: float,
    gap_pct: float,
    residual_pct: float,
) -> str:
    if covered_gci is None:
        return (
            f"No holding in this file has a published GCI. "
            f"{gap_pct}% of the weight has no score. {residual_pct}% is cash, debt, indirect, or other."
        )
    return (
        f"Covered holdings are {covered_pct}% of the file by weight, "
        f"with a weighted published GCI of {covered_gci}. "
        f"{gap_pct}% of the weight has no score. "
        f"{residual_pct}% is cash, debt, indirect, or other."
    )


def _line_key(row: Dict[str, Any]) -> str:
    if row.get("isin"):
        return f"isin:{row['isin']}"
    return f"residual:{row.get('kind') or row.get('name')}"


def diff_snapshots(prior: Optional[Dict[str, Any]], current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prior:
        return None
    prior_rows = {
        _line_key(r): r
        for r in list(prior.get("scored") or [])
        + list(prior.get("gaps") or [])
        + list(prior.get("residual") or [])
    }
    current_rows = {
        _line_key(r): r
        for r in list(current.get("scored") or [])
        + list(current.get("gaps") or [])
        + list(current.get("residual") or [])
    }
    entered = [current_rows[k] for k in current_rows if k not in prior_rows]
    exited = [prior_rows[k] for k in prior_rows if k not in current_rows]
    changed = []
    for key, row in current_rows.items():
        old = prior_rows.get(key)
        if not old:
            continue
        if float(old.get("weight") or 0) != float(row.get("weight") or 0):
            changed.append(
                {
                    "key": key,
                    "name": row.get("name"),
                    "prior_weight": old.get("weight"),
                    "weight": row.get("weight"),
                    "prior_gci": old.get("gci_score"),
                    "gci_score": row.get("gci_score"),
                }
            )
    prior_gci = prior.get("covered_gci")
    current_gci = current.get("covered_gci")
    return {
        "prior_as_of": prior.get("as_of"),
        "prior_covered_gci": prior_gci,
        "covered_gci_change": (
            None
            if prior_gci is None or current_gci is None
            else round(float(current_gci) - float(prior_gci), 1)
        ),
        "entered": entered,
        "exited": exited,
        "weight_changes": changed,
    }


_SINCE_FILING_KINDS = frozenset({"results", "filing", "ir_guidance", "transcript"})
FILINGS_PER_NAME = 3


def since_last_open(
    company_rows: List[Dict[str, Any]],
    *,
    since: Optional[str],
    filings_for: Callable[[str], List[Dict[str, Any]]],
    missed_for: Callable[[str], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Stored records on held names since the last open. Pure given the two readers.

    A new filing and a missed row count only after ``since``. Open guidance is listed
    whenever the count is above zero. Nothing here writes a score.
    """
    cutoff = str(since or "")
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for row in company_rows:
        cid = str(row.get("company_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        name = row.get("name") or row.get("ticker") or cid
        docs = sorted(
            filings_for(cid),
            key=lambda d: str(d.get("ingested_at") or d.get("date") or ""),
            reverse=True,
        )
        for doc in docs[:FILINGS_PER_NAME]:
            stamp = str(doc.get("ingested_at") or doc.get("date") or "")
            if cutoff and stamp <= cutoff:
                continue
            out.append(
                {
                    "company_id": cid,
                    "name": name,
                    "kind": "filing",
                    "title": doc.get("title") or doc.get("doc_type"),
                    "at": stamp,
                    "doc_id": doc.get("doc_id"),
                }
            )
        if int(row.get("open_commitments") or 0) > 0:
            out.append(
                {
                    "company_id": cid,
                    "name": name,
                    "kind": "open_guidance",
                    "count": int(row.get("open_commitments") or 0),
                }
            )
        for miss in missed_for(cid):
            stamp = str(miss.get("as_of") or "")
            if cutoff and stamp and stamp <= cutoff[:10]:
                continue
            out.append(
                {
                    "company_id": cid,
                    "name": name,
                    "kind": "missed",
                    "period": miss.get("period"),
                    "metric": miss.get("metric"),
                    "at": stamp or None,
                }
            )
    return out


def _stored_filings(company_id: str) -> List[Dict[str, Any]]:
    from app.data import doc_store

    return [
        d
        for d in doc_store.list_documents(company_id=company_id, hydrate=False)
        if d.get("review_status") == "accepted" and str(d.get("doc_type") or "") in _SINCE_FILING_KINDS
    ]


def _published_misses(company_id: str) -> List[Dict[str, Any]]:
    from app.services.repository import get_company_gci

    try:
        detail = get_company_gci(company_id)
    except HTTPException:
        return []
    if detail.gci_score is None:
        return []
    return [
        {"period": o.period, "metric": o.metric, "as_of": o.as_of}
        for o in detail.outcomes
        if str(o.label or "").lower() == "missed"
    ]


def _load(org_id: str) -> Dict[str, Any]:
    path = _org_path(org_id)
    if not path.exists():
        return {"snapshots": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(org_id: str, data: Dict[str, Any]) -> None:
    path = _org_path(org_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _resolve_isin(isin: str) -> Optional[Dict[str, Any]]:
    from app.data.india_listings import india_equity_universe

    for row in india_equity_universe():
        if str(row.get("isin") or "").upper() == isin:
            return row
    return None


def _published(company_id: str) -> Optional[Dict[str, Any]]:
    from app.data.gci_score_cache import get_listing_score

    return get_listing_score(company_id)


def _universe_gci() -> Optional[float]:
    from app.data.gci_score_cache import load_cache

    scores = []
    for row in (load_cache().get("scores") or {}).values():
        if not isinstance(row, dict):
            continue
        value = row.get("gci_score")
        if isinstance(value, (int, float)) and value == value:
            scores.append(float(value))
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _open_commitments(company_id: str) -> int:
    from app.services.commitment_store import company_view

    summary = company_view(company_id, include_unreviewed=False).get("summary") or {}
    return int(summary.get("due") or 0) + int(summary.get("open_not_yet_due") or 0) + int(
        summary.get("awaiting_proof") or 0
    )


def submit_lookthrough(org_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    as_of = _as_of(body.get("as_of"))
    lines = body.get("lines")
    if not isinstance(lines, list):
        raise HTTPException(status_code=400, detail="lines must be a list")
    scheme = body.get("scheme") or []
    if not isinstance(scheme, list):
        raise HTTPException(status_code=400, detail="scheme must be a list")
    report = build_lookthrough(
        lines,
        as_of=as_of,
        resolve_isin=_resolve_isin,
        published_score=_published,
        commitment_counts=_open_commitments,
        universe_gci=_universe_gci(),
        scheme=scheme,
    )
    with _LOCK:
        stored = _load(org_id)
        snapshots = list(stored.get("snapshots") or [])
        prior = snapshots[-1] if snapshots else None
        report["diff"] = diff_snapshots(prior, report)
        report["org_id"] = org_id
        report["saved_at"] = _now()
        snapshots.append(
            {
                "as_of": report["as_of"],
                "saved_at": report["saved_at"],
                "covered_gci": report["covered_gci"],
                "covered_weight_pct": report["covered_weight_pct"],
                "unscored_weight_pct": report["unscored_weight_pct"],
                "residual_weight_pct": report["residual_weight_pct"],
                "statement": report["statement"],
                "note": report["note"],
                "scored": report["scored"],
                "gaps": report["gaps"],
                "residual": report["residual"],
                "manager": report["manager"],
                "scheme": report["scheme"],
                "lines": lines,
            }
        )
        stored["snapshots"] = snapshots[-24:]
        _save(org_id, stored)
    return report


def latest_lookthrough(org_id: str) -> Dict[str, Any]:
    with _LOCK:
        stored = _load(org_id)
        snapshots = list(stored.get("snapshots") or [])
        last_opened = stored.get("last_opened_at")
        if snapshots:
            stored["last_opened_at"] = _now()
            _save(org_id, stored)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No holdings file saved for this desk")
    stored_row = dict(snapshots[-1])
    prior = snapshots[-2] if len(snapshots) > 1 else None
    stored_lines = stored_row.get("lines")
    if isinstance(stored_lines, list) and stored_lines:
        report = build_lookthrough(
            stored_lines,
            as_of=str(stored_row.get("as_of") or ""),
            resolve_isin=_resolve_isin,
            published_score=_published,
            commitment_counts=_open_commitments,
            universe_gci=_universe_gci(),
            scheme=list((stored_row.get("scheme") or {}).get("points") or []),
        )
        report["lines"] = stored_lines
        report["saved_at"] = stored_row.get("saved_at")
    else:
        report = stored_row
        if "manager" not in report:
            report["manager"] = _manager(
                report.get("covered_gci"), list(report.get("scored") or []), _universe_gci()
            )
        report.setdefault("scheme", _scheme([]))
        report.setdefault("statement", "")
        report.setdefault("note", "")
        report.setdefault("scored", [])
        report.setdefault("gaps", [])
        report.setdefault("residual", [])
        report.setdefault("covered_weight_pct", 0)
        report.setdefault("unscored_weight_pct", 0)
        report.setdefault("residual_weight_pct", 0)
    report["product"] = "CiteAlpha Holdings"
    report["diff"] = diff_snapshots(prior, report)
    report["org_id"] = org_id
    report["last_opened_at"] = last_opened
    report["since_last_open"] = since_last_open(
        list(report.get("scored") or []) + list(report.get("gaps") or []),
        since=last_opened,
        filings_for=_stored_filings,
        missed_for=_published_misses,
    )
    return report
