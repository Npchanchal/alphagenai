"""Daily guidance-quote and later-filing review.

Rotates one market per calendar day. Copies a citation only when the guided or
reported number is already in an accepted filing excerpt. Does not invent
quotes, actuals, or scores, and does not wait for an analyst.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.data.markets import MARKETS, list_stocks
from app.data.metric_catalog import CORE_METRICS, get_metric, list_metrics, normalize_metric
from app.data.seed import get_data, get_outcomes, list_companies, save_data
from app.services.score_policy import is_pending_guidance_cite, is_source_verify_fail
from app.services.source_verify import KNOWN_UNVERIFIED, quote_in_text

# 02:30 Asia/Kolkata, which is 21:00 UTC the same calendar evening.
RUN_HOUR_UTC = 21
RUN_MINUTE_UTC = 0

KIND = "guidance_review"
REVIEWER = "job:guidance_review"


def seconds_until_next_run(now: Optional[datetime] = None) -> int:
    """Seconds until the next 02:30 IST run. At least one second."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    nxt = current.replace(hour=RUN_HOUR_UTC, minute=RUN_MINUTE_UTC, second=0, microsecond=0)
    if nxt <= current:
        nxt += timedelta(days=1)
    return max(1, int((nxt - current).total_seconds()))


def market_ids() -> List[str]:
    return [str(m["id"]) for m in MARKETS]


def market_for_day(day: date) -> str:
    ids = market_ids()
    return ids[day.toordinal() % len(ids)]


def _getter(outcome: object):
    if isinstance(outcome, dict):
        return lambda key, default=None: outcome.get(key, default)
    return lambda key, default=None: getattr(outcome, key, default)


def row_gaps(outcome: object) -> List[str]:
    """What an analyst still has to attach before the row can be scored."""
    gaps: List[str] = []
    if is_pending_guidance_cite(outcome):
        gaps.append("missing_guidance_cite")
    g = _getter(outcome)
    has_promise = all(
        str(g(key) or "").strip()
        for key in ("guidance_source_url", "guidance_quote", "guidance_as_of")
    )
    has_filing = all(str(g(key) or "").strip() for key in ("source_url", "quote_span", "as_of"))
    if has_promise and g("actual_value") is None:
        gaps.append("awaiting_later_filing")
    elif not has_filing and (g("guided_value") is not None or g("guided_low") is not None):
        gaps.append("missing_later_filing")
    if is_source_verify_fail(outcome):
        gaps.append("source_unverified")
    return gaps


_GENERIC_TOKENS = frozenset(
    {"growth", "margin", "percent", "guidance", "pct", "spend", "value", "rate", "and", "the", "of",
     "usd", "gaap", "non"}
)
_SHORT_TOKENS = frozenset({"cc", "nim", "ape", "vnb", "arpu", "fcf", "pat", "sss", "eps"})
_UNIT_CUES = {
    "inr_cr": ("crore", " cr", "₹", " rs", "inr"),
    "days": ("day",),
    "mmt": ("mmt", "million tonne", " mt"),
    "units": ("unit", "vehicle"),
    "usd_mn": ("$", "usd", "dollar"),
    "usd": ("$", "usd", "per share", "eps"),
}
#: A US$-million figure may be written in billions in the filing.
_SCALED_UNITS = {"usd_mn": ((1.0, ("million", "mn", "$")), (0.001, ("billion", "bn")))}


def metric_rule(metric_id: Any) -> Optional[Dict[str, Any]]:
    """Catalog row for this stock's metric, including aliases such as volume_growth_pct."""
    nid = normalize_metric(None if metric_id is None else str(metric_id))
    return get_metric(nid) if nid else None


def parameters_for_company(
    company: Optional[Dict[str, Any]],
    outcomes: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Metrics a reviewer would open for this stock: its sector catalog, plus metrics it already files."""
    sector = str((company or {}).get("sector") or "")
    chosen = list(list_metrics(sector) if sector else CORE_METRICS)
    seen = {str(row["id"]) for row in chosen}
    for outcome in outcomes or []:
        rule = metric_rule(outcome.get("metric") if isinstance(outcome, dict) else None)
        if rule is None or rule["id"] in seen:
            continue
        chosen.append(rule)
        seen.add(rule["id"])
    return chosen


def _metric_tokens(rule: Dict[str, Any]) -> List[str]:
    parts: List[str] = []
    parts.extend(re.split(r"[^a-z0-9]+", str(rule.get("id") or "").lower()))
    parts.extend(re.findall(r"[a-z0-9]{4,}", str(rule.get("display_name") or "").lower()))
    for alias in rule.get("aliases") or []:
        parts.extend(re.split(r"[^a-z0-9]+", str(alias).lower()))
    out: List[str] = []
    for part in parts:
        if not part or part in _GENERIC_TOKENS:
            continue
        if len(part) < 4 and part not in _SHORT_TOKENS:
            continue
        if part not in out:
            out.append(part)
    return out


def _mentions_metric(rule: Dict[str, Any], text: str) -> bool:
    body = (text or "").lower()
    return any(token in body for token in _metric_tokens(rule))


def _number_in_text(value: float, text: str) -> bool:
    body = (text or "").replace(",", "")
    tokens = {format(value, "g"), f"{value:.1f}", f"{value:.2f}"}
    for token in tokens:
        if token and re.search(rf"(?<![\d.]){re.escape(token)}(?!\d)", body):
            return True
    return False


def _number_with_unit(value: float, text: str, unit: str) -> bool:
    """A percent metric must sit next to % or 'percent'. A crore metric must say crore, Rs, or INR.

    A US$-million metric matches the figure in millions or in billions with the scale word.
    """
    if unit in _SCALED_UNITS:
        lowered = (text or "").lower()
        return any(
            _number_in_text(round(value * factor, 6), text) and any(w in lowered for w in words)
            for factor, words in _SCALED_UNITS[unit]
        )
    if not _number_in_text(value, text):
        return False
    body = (text or "").replace(",", "")
    tokens = {format(value, "g"), f"{value:.1f}", f"{value:.2f}"}
    if unit == "pct":
        return any(
            token
            and re.search(
                rf"(?<![\d.]){re.escape(token)}(?!\d)\s*(%|percent|per cent)",
                body,
                flags=re.IGNORECASE,
            )
            for token in tokens
        )
    cues = _UNIT_CUES.get(unit)
    if not cues:
        return True
    lowered = body.lower()
    return any(cue in lowered or cue in body for cue in cues)


def _guided_numbers(outcome: Dict[str, Any], rule: Dict[str, Any]) -> List[float]:
    low = _targets(outcome, ("guided_low",))
    high = _targets(outcome, ("guided_high",))
    if rule.get("bands_preferred") and low and high:
        return low + high
    band = low + high
    if len(band) >= 2:
        return band
    return _targets(outcome, ("guided_value",)) or band


def _targets(outcome: Dict[str, Any], keys: tuple) -> List[float]:
    found: List[float] = []
    for key in keys:
        raw = outcome.get(key)
        if raw is None or raw == "":
            continue
        try:
            found.append(float(raw))
        except (TypeError, ValueError):
            continue
    return found


def _accepted_docs(company_id: str) -> List[Dict[str, Any]]:
    from app.data.doc_store import list_documents

    rows = []
    for doc in list_documents(company_id=company_id):
        if doc.get("review_status") not in (None, "accepted"):
            continue
        text = str(doc.get("text") or "")
        if not text.strip() or not str(doc.get("url") or "").strip():
            continue
        # Generated completeness packs repeat a quote under a guidance label.
        # They are not the filing a reviewer would cite.
        if doc.get("source") == "hand_labeled_period_pack" or "auto corpus pack" in text.lower():
            continue
        if "this quote is not on the page" in text.lower():
            continue
        rows.append(doc)
    return rows


def _matching_doc(
    docs: List[Dict[str, Any]],
    *,
    period: str,
    numbers: List[float],
    rule: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not numbers or not rule:
        return None
    unit = str(rule.get("unit") or "")
    for doc in docs:
        doc_period = str(doc.get("period") or "")
        if doc_period and period and doc_period != period:
            continue
        text = str(doc.get("text") or "")
        if not _mentions_metric(rule, text):
            continue
        if all(_number_with_unit(n, text, unit) for n in numbers):
            return doc
    return None


def _quote_from_doc(doc: Dict[str, Any]) -> str:
    text = str(doc.get("text") or "").strip()[:500]
    if not quote_in_text(text, str(doc.get("text") or "")):
        return ""
    return text


def _doc_for_quote(docs: List[Dict[str, Any]], quote: Any) -> Optional[Dict[str, Any]]:
    q = str(quote or "").strip()
    if len(q) < 12:
        return None
    for doc in docs:
        if quote_in_text(q, str(doc.get("text") or "")):
            return doc
    return None


def _metric_allowed(
    company: Optional[Dict[str, Any]],
    rule: Dict[str, Any],
    outcomes: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """File a metric when it is in this stock's parameter set."""
    if company is None:
        return True
    if not str(company.get("sector") or "") and not outcomes:
        return True
    allowed = {row["id"] for row in parameters_for_company(company, outcomes or [])}
    return rule["id"] in allowed


def _as_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _promise_distinct(outcome: Dict[str, Any]) -> bool:
    """A result number copied into the guidance fields is not a promise.

    A band with two different ends, or a guided number different from the actual, can be filed.
    """
    actual = _as_float(outcome.get("actual_value"))
    if actual is None:
        return True
    low = _as_float(outcome.get("guided_low"))
    high = _as_float(outcome.get("guided_high"))
    guided = _as_float(outcome.get("guided_value"))
    if low is not None and high is not None and abs(low - high) >= 0.05:
        return True
    for value in (guided, low, high):
        if value is not None and abs(value - actual) >= 0.05:
            return True
    return False


def _known_unverified(company: Optional[Dict[str, Any]], outcome: Dict[str, Any]) -> bool:
    if not company:
        return False
    metric = str(outcome.get("metric") or "")
    rule = metric_rule(metric)
    metric_ids = {metric}
    if rule is not None:
        metric_ids.add(str(rule["id"]))
    period = str(outcome.get("period") or "")
    company_id = str(company.get("id") or "")
    return any((company_id, period, mid) in KNOWN_UNVERIFIED for mid in metric_ids)


def _quote_fits(rule: Dict[str, Any], quote: Any, numbers: List[float]) -> bool:
    text = str(quote or "")
    if not numbers or not _mentions_metric(rule, text):
        return False
    unit = str(rule.get("unit") or "")
    return all(_number_with_unit(n, text, unit) for n in numbers)


def bind_from_documents(
    outcome: Dict[str, Any],
    docs: List[Dict[str, Any]],
    company: Optional[Dict[str, Any]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """File a citation when this stock's metric rules match an accepted filing.

    The quote is the filing text already stored. The metric name and unit have to be in
    that text. A band-preferred metric files only when both ends of the recorded band are
    in the text. A number that is not in that text is left blank.
    """
    if not isinstance(outcome, dict):
        return False
    rule = metric_rule(outcome.get("metric"))
    if rule is None or not _metric_allowed(company, rule, outcomes):
        return False
    changed = False
    period = str(outcome.get("period") or "")
    guidance_missing = not all(
        str(outcome.get(key) or "").strip()
        for key in ("guidance_source_url", "guidance_quote", "guidance_as_of")
    )
    if guidance_missing and _promise_distinct(outcome) and not _known_unverified(company, outcome):
        numbers = _guided_numbers(outcome, rule)
        doc = _matching_doc(docs, period=period, numbers=numbers, rule=rule)
        quote = _quote_from_doc(doc) if doc is not None else ""
        if doc is not None and quote:
            outcome["guidance_quote"] = quote
            outcome["guidance_source_url"] = str(doc.get("url") or "").strip()
            outcome["guidance_source_ref"] = str(doc.get("source") or doc.get("doc_id") or "")
            outcome["guidance_as_of"] = str(doc.get("date") or "")[:10]
            changed = True
    filing_missing = not all(
        str(outcome.get(key) or "").strip() for key in ("source_url", "quote_span", "as_of")
    )
    if filing_missing and outcome.get("actual_value") is not None:
        doc = _matching_doc(
            docs,
            period=period,
            numbers=_targets(outcome, ("actual_value",)),
            rule=rule,
        )
        quote = _quote_from_doc(doc) if doc is not None else ""
        if doc is not None and quote:
            outcome["quote_span"] = quote
            outcome["source_url"] = str(doc.get("url") or "").strip()
            outcome["source_ref"] = str(doc.get("source") or doc.get("doc_id") or "")
            outcome["as_of"] = str(doc.get("date") or "")[:10]
            changed = True
    present = [
        q
        for q in (outcome.get("guidance_quote"), outcome.get("quote_span"))
        if str(q or "").strip()
    ]
    quotes_checked = bool(present) and all(_doc_for_quote(docs, q) for q in present)
    guided_ok = _quote_fits(rule, outcome.get("guidance_quote"), _guided_numbers(outcome, rule))
    actual_numbers = _targets(outcome, ("actual_value",))
    actual_ok = outcome.get("actual_value") is None or _quote_fits(
        rule, outcome.get("quote_span"), actual_numbers
    )
    if (
        quotes_checked
        and guided_ok
        and actual_ok
        and _promise_distinct(outcome)
        and not _known_unverified(company, outcome)
        and outcome.get("source_verified") is False
    ):
        filing = _doc_for_quote(docs, outcome.get("quote_span"))
        if filing is not None and str(filing.get("url") or "") != outcome.get("source_url"):
            outcome["source_url"] = str(filing.get("url") or "").strip()
            outcome["source_ref"] = str(filing.get("source") or filing.get("doc_id") or "")
        outcome["source_verified"] = True
        outcome["citeable"] = True
        changed = True
    dual = all(
        str(outcome.get(key) or "").strip()
        for key in (
            "guidance_source_url",
            "guidance_quote",
            "guidance_as_of",
            "source_url",
            "quote_span",
            "as_of",
        )
    )
    if (
        dual
        and quotes_checked
        and guided_ok
        and actual_ok
        and _promise_distinct(outcome)
        and not _known_unverified(company, outcome)
        and outcome.get("source_verified") is not False
        and not str(outcome.get("reviewed_by") or "").strip()
    ):
        outcome["reviewed_by"] = REVIEWER
        outcome["reviewed_at"] = datetime.now(timezone.utc).date().isoformat()
        changed = True
    return changed


def companies_for_market(market_id: str) -> List[Dict[str, Any]]:
    """Hand-labeled dossiers in this market. Other listings are left unscored."""
    wanted = {str(row["id"]) for row in list_stocks(market_id)}
    out: List[Dict[str, Any]] = []
    for company in list_companies():
        if company["id"] not in wanted:
            continue
        from app.services.score_policy import is_scoreable

        if not is_scoreable(company.get("data_quality")):
            continue
        out.append(company)
    return out


def citation_gaps(company: Dict[str, Any]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for outcome in get_outcomes(company["id"]):
        gaps = row_gaps(outcome)
        if not gaps:
            continue
        g = _getter(outcome)
        found.append(
            {
                "period": g("period") or "",
                "metric": g("metric") or "",
                "gaps": gaps,
            }
        )
    return found


def _binds_path() -> Optional[Path]:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    if not override:
        return None
    base = Path(override)
    base.mkdir(parents=True, exist_ok=True)
    return base / "guidance_review_outcomes.json"


def apply_stored_binds(data: Dict[str, Any]) -> None:
    """Re-apply citations saved on the data volume after a new image rebuilds store.json."""
    path = _binds_path()
    if path is None or not path.exists() or not isinstance(data, dict):
        return
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    outcomes = data.setdefault("outcomes", {})
    for company_id, rows in (blob.get("outcomes") or {}).items():
        if isinstance(rows, list):
            outcomes[company_id] = rows


def _save_binds(company_ids: List[str]) -> None:
    path = _binds_path()
    if path is None or not company_ids:
        return
    blob: Dict[str, Any] = {"outcomes": {}}
    if path.exists():
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blob = {"outcomes": {}}
    outcomes = blob.setdefault("outcomes", {})
    stored = (get_data().get("outcomes") or {})
    for company_id in company_ids:
        outcomes[company_id] = stored.get(company_id) or []
    path.write_text(json.dumps(blob) + "\n", encoding="utf-8")


def _stamp_path() -> Path:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    base = Path(override) if override else Path(__file__).resolve().parents[1] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "guidance_review_stamp.json"


def _read_stamp() -> Dict[str, Any]:
    path = _stamp_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def last_stamp() -> Dict[str, Any]:
    """Last completed daily review. Read from the stamp file. Does not run the job."""
    stamp = _read_stamp()
    if not stamp:
        return {"ran": False, "market_id": None, "date": None, "at": None, "bound_rows": None}
    return {
        "ran": True,
        "market_id": stamp.get("market_id"),
        "date": stamp.get("date"),
        "at": stamp.get("at"),
        "bound_rows": stamp.get("bound_rows"),
    }


def _write_stamp(day: date, market_id: str, queued: int) -> None:
    _stamp_path().write_text(
        json.dumps(
            {
                "date": day.isoformat(),
                "market_id": market_id,
                "job": KIND,
                "bound_rows": queued,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def run_daily(
    *,
    day: Optional[date] = None,
    market_id: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Bind today's market from accepted filings. One run per calendar day unless forced."""
    today = day or datetime.now(timezone.utc).date()
    market = (market_id or market_for_day(today)).upper()
    known = set(market_ids())
    if market not in known:
        return {"ok": False, "error": "unknown_market", "market_id": market}

    if not force and not dry_run:
        stamp = _read_stamp()
        if stamp.get("date") == today.isoformat():
            return {
                "ok": True,
                "skipped": True,
                "market_id": stamp.get("market_id") or market,
                "date": today.isoformat(),
                "reason": "already_ran",
            }

    bound_rows = 0
    still_open = 0
    companies_touched: List[str] = []
    parameters: Dict[str, List[str]] = {}
    data = get_data()
    for company in companies_for_market(market):
        cid = company["id"]
        docs = _accepted_docs(cid)
        rows = list((data.get("outcomes") or {}).get(cid) or [])
        parameters[str(company.get("ticker") or cid)] = [
            row["id"] for row in parameters_for_company(company, rows)
        ]
        company_changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            before = dict(row)
            changed = bind_from_documents(row, docs, company=company, outcomes=rows)
            if row_gaps(row):
                still_open += 1
            if changed:
                bound_rows += 1
                company_changed = True
            if dry_run:
                row.clear()
                row.update(before)
        if company_changed and not dry_run:
            companies_touched.append(cid)

    ledger_n = 0
    if not dry_run:
        if companies_touched:
            save_data()
            _save_binds(companies_touched)
            from app.services.score_ledger import append_many, snapshot_rows

            moves = snapshot_rows(
                reason="new_filing",
                note="Guidance review bound quotes found in accepted filings.",
                by=REVIEWER,
                as_of=today.isoformat(),
            )
            moves = [row for row in moves if row.company_id in set(companies_touched)]
            ledger_n = append_many(moves)
            if moves:
                _append_changelog(today, moves)
        _write_stamp(today, market, bound_rows)

    return {
        "ok": True,
        "skipped": False,
        "date": today.isoformat(),
        "market_id": market,
        "hand_labeled": len(companies_for_market(market)),
        "bound_rows": bound_rows,
        "still_open": still_open,
        "companies": companies_touched,
        "parameters": parameters,
        "ledger_rows": ledger_n,
        "dry_run": dry_run,
        "note": (
            "Each stock is filed on its own metrics. A quote is copied only when the filing "
            "names that metric, uses its unit, and contains the recorded band. "
            "Rows that do not match stay unscored."
        ),
    }


def _packaged_changelog() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "score_changelog.json"


def changelog_write_path() -> Path:
    """Job entries go to the data dir when set, so a test run cannot edit the packaged file."""
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    if override:
        base = Path(override)
        base.mkdir(parents=True, exist_ok=True)
        return base / "score_changelog.json"
    return _packaged_changelog()


def changelog_entries() -> List[Dict[str, Any]]:
    """Packaged changelog plus any entries the daily job appended on the data volume."""
    entries: List[Dict[str, Any]] = []
    packaged = _packaged_changelog()
    if packaged.exists():
        try:
            entries = list(json.loads(packaged.read_text(encoding="utf-8")).get("entries") or [])
        except json.JSONDecodeError:
            entries = []
    extra_path = changelog_write_path()
    if extra_path.resolve() == packaged.resolve() or not extra_path.exists():
        return entries
    try:
        extra = list(json.loads(extra_path.read_text(encoding="utf-8")).get("entries") or [])
    except json.JSONDecodeError:
        return entries
    seen = {(row.get("date"), row.get("change")) for row in entries}
    for row in reversed(extra):
        key = (row.get("date"), row.get("change"))
        if key in seen:
            continue
        entries.insert(0, row)
        seen.add(key)
    return entries


def _append_changelog(
    day: date,
    moves: List[Any],
    *,
    lead: str = "Daily guidance review copied quotes from accepted filings.",
) -> None:
    path = changelog_write_path()
    payload: Dict[str, Any] = {"entries": []}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"entries": []}
    bits = [f"{row.company_id} {row.prior_gci} → {row.gci}" for row in moves]
    payload.setdefault("entries", []).insert(
        0,
        {
            "date": day.isoformat(),
            "reason": "new_filing",
            "companies": [row.company_id for row in moves],
            "change": f"{lead} " + "; ".join(bits) + ".",
        },
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
