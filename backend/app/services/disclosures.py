"""Promises and results read from filings since 2022, reconciled into GCI rows.

Each filing chunk is read once by the model, which returns two lists: guidance
(metric, period, range, the sentence) and reported results (metric, period,
value, the sentence). Nothing is kept unless the sentence is word-for-word in
the stored filing and carries the number with its unit.

Reconciliation is pure (:func:`reconcile`): the earliest promise made before a
period closed is the opening band, later different bands are in-year revisions,
and the first result filed after the period closed is the actual. A promise with
no matching result stays open. No number is ever filled in.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from app.data.metric_catalog import get_metric, metrics_for_market, normalize_metric
from app.data.store_lock import locked
from app.services.source_verify import normalize_text

ENGINE = "disclosures_v1"
REVIEWER = "job:disclosure_reconcile"
#: Engines whose rows this module owns and may replace on a re-run.
OWNED_ENGINES = frozenset({ENGINE, "llm_v1", "llm_fallback_heuristic", "heuristic", "auto"})
MIN_QUOTE_CHARS = 20
MAX_QUOTE_CHARS = 400
#: A result filed more than this long after the period closed is a restatement, not the actual.
RESULT_WINDOW_DAYS = 550
#: Promises further out than this are long-range ambitions, not period guidance.
GUIDANCE_HORIZON_DAYS = 5 * 366
#: Consecutive model failures (quota, outage) after which a company's read stops for today.
MAX_FAILURE_STREAK = 3

Extractor = Callable[..., Dict[str, List[Dict[str, Any]]]]


# ── Fiscal periods ───────────────────────────────────────────────────────────

_FY_SPAN = re.compile(r"^FY\s*'?(\d{4})\s*[-/]\s*(\d{2,4})$")
_Q = re.compile(r"^(?:Q([1-4])|([1-4])Q)\s*(?:FY|F|FISCAL)?\s*'?(\d{2}|\d{4})$")
_FY = re.compile(r"^(?:FY|F|FISCAL(?:\s+YEAR)?)\s*'?(\d{2}|\d{4})$")
_YEAR = re.compile(r"^(?:CY\s*)?(\d{4})$")


def _year4(raw: str) -> int:
    return int(raw) if len(raw) == 4 else 2000 + int(raw)


def canonical_period(raw: Any, market_id: str) -> Optional[str]:
    """``FY25`` / ``Q3 FY25`` for India, ``FY2025`` / ``Q3 FY2025`` for the US; None if unreadable."""
    text = re.sub(r"\s+", " ", str(raw or "").strip().upper())
    if not text:
        return None
    quarter: Optional[int] = None
    year: Optional[int] = None
    m = _FY_SPAN.match(text)
    if m:
        year = _year4(m.group(2)[-2:]) if len(m.group(2)) == 2 else int(m.group(2))
    else:
        flat = text.replace("-", " ").replace("’", "'")
        flat = re.sub(r"\s+", " ", flat)
        m = _Q.match(flat) or _Q.match(flat.replace(" ", ""))
        if m:
            quarter = int(m.group(1) or m.group(2))
            year = _year4(m.group(3))
        else:
            m = _FY.match(flat) or _FY.match(flat.replace(" ", "")) or _YEAR.match(flat)
            if m:
                year = _year4(m.group(1))
    if year is None or not 2000 <= year <= 2100:
        return None
    label = f"FY{year % 100:02d}" if market_id == "IN" else f"FY{year}"
    return f"Q{quarter} {label}" if quarter else label


def _last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def period_bounds(period: str, market_id: str, fy_end_mmdd: Optional[str] = None) -> Optional[Tuple[date, date]]:
    """(start, end) of a canonical period. India: April–March. US: the company's fiscal year end."""
    m = re.match(r"^(?:Q([1-4]) )?FY(\d{2}|\d{4})$", period or "")
    if not m:
        return None
    quarter = int(m.group(1)) if m.group(1) else None
    year = _year4(m.group(2))
    end_month = 3
    if market_id != "IN":
        mmdd = (fy_end_mmdd or "1231").strip()
        end_month = int(mmdd[:2]) if mmdd[:2].isdigit() and 1 <= int(mmdd[:2]) <= 12 else 12
    fy_end = _last_day(year, end_month)
    if quarter is None:
        start = date(year, 1, 1) if end_month == 12 else date(year - 1, end_month + 1, 1)
        return start, fy_end
    months_back = (4 - quarter) * 3
    q_month = end_month - months_back
    q_year = year
    while q_month <= 0:
        q_month += 12
        q_year -= 1
    q_end = _last_day(q_year, q_month)
    s_month, s_year = q_month - 2, q_year
    if s_month <= 0:
        s_month += 12
        s_year -= 1
    return date(s_year, s_month, 1), q_end


def period_end(period: str, market_id: str, fy_end_mmdd: Optional[str] = None) -> Optional[str]:
    bounds = period_bounds(period, market_id, fy_end_mmdd)
    return bounds[1].isoformat() if bounds else None


# ── Quote checks ─────────────────────────────────────────────────────────────


def quote_verbatim(quote: Any, text: str) -> bool:
    """The whole sentence is in the filing (case and spacing aside). No prefix match."""
    q = normalize_text(str(quote or ""))
    body = normalize_text(text or "")
    if len(q) < MIN_QUOTE_CHARS or not body:
        return False
    if q in body:
        return True
    squash = lambda s: re.sub(r"[^a-z0-9%.,$-]+", "", s)  # noqa: E731
    return squash(q) in squash(body)


def _numbers_fit(metric_id: str, quote: str, numbers: List[float]) -> bool:
    from app.services.guidance_review import _quote_fits

    rule = get_metric(metric_id)
    return bool(rule) and _quote_fits(rule, quote, numbers)


def _as_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _iso(raw: Any) -> Optional[str]:
    try:
        return datetime.strptime(str(raw or "")[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


# ── Model call ───────────────────────────────────────────────────────────────

_PROMPT = """You read one excerpt of a company filing and list numbers management stated.
Return ONLY a JSON object: {{"guidance": [...], "results": [...]}}. No markdown.

guidance = a target management gives for a period that has not ended yet.
  keys: metric, period, low, high, quote
results = a figure the company reports for a period that has ended.
  keys: metric, period, value, quote

metric: one of {metrics}. Skip anything that fits none, segment-only figures, and other companies.
period: {period_rule}
Resolve "this year", "next quarter", "full year" to an explicit period from the filing date.
low/high: the guided range; repeat the number for a point target.
For "X, plus or minus Y%" give low = high = X and add "pm_pct": Y.
Units: pct = percent (12.5); inr_cr = INR crore; usd_mn = US$ millions ($1.2 billion = 1200);
usd = US$ per share; days; mmt = million tonnes; units = vehicles.
quote: copy the sentence exactly as written, 20-300 characters, containing the number.
If there is nothing, return {{"guidance": [], "results": []}}."""

_PERIOD_RULES = {
    "IN": 'Indian fiscal year ends 31 March. Write "FY25" (April 2024 to March 2025) or "Q3 FY25".',
    "US": (
        'Use the company\'s own fiscal labels: "FY2025" or "Q3 FY2025". The fiscal year ends in {fy_month}; '
        "name it by the calendar year in which it ends."
    ),
}


def _metric_list(market_id: str) -> str:
    return ", ".join(f"{m['id']} [{m.get('unit')}]" for m in metrics_for_market(market_id))


def build_prompt(market_id: str, fy_end_mmdd: Optional[str] = None) -> str:
    rule = _PERIOD_RULES.get(market_id, _PERIOD_RULES["US"])
    if "{fy_month}" in rule:
        month = int((fy_end_mmdd or "1231")[:2] or 12)
        rule = rule.replace("{fy_month}", calendar.month_name[month if 1 <= month <= 12 else 12])
    return _PROMPT.format(metrics=_metric_list(market_id), period_rule=rule)


def _parse_json_object(raw: str) -> Dict[str, Any]:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = json.loads(cleaned)
    if isinstance(parsed, list):
        return {"guidance": parsed, "results": []}
    if not isinstance(parsed, dict):
        raise RuntimeError("model did not return a JSON object")
    return parsed


def llm_extract(
    chunk: str,
    *,
    company_name: str,
    market_id: str,
    doc_date: str,
    fy_end_mmdd: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    from app.services import llm_client

    messages = [
        {"role": "system", "content": build_prompt(market_id, fy_end_mmdd)},
        {"role": "user", "content": f"Company: {company_name}\nFiling date: {doc_date}\n\n{chunk}"},
    ]
    tier = service_tier()
    ask = dict(max_tokens=8192, reasoning="low", timeout=FLEX_TIMEOUT_S if tier == "flex" else 180.0)
    for wait in RETRY_WAITS:
        try:
            raw = llm_client.chat_completion(messages, service_tier=tier, **ask)
            break
        except RuntimeError as exc:
            if not _transient(exc):
                raise
            _sleep(wait)
    else:
        # Flex capacity is shed under load; the last try goes to the standard tier.
        raw = llm_client.chat_completion(messages, service_tier=None, **ask)
    parsed = _parse_json_object(raw)
    return {
        "guidance": [g for g in parsed.get("guidance") or [] if isinstance(g, dict)],
        "results": [r for r in parsed.get("results") or [] if isinstance(r, dict)],
    }


# A per-minute 429 or a 503 clears in seconds; a daily-quota 429 still fails after the last try.
RETRY_WAITS = (5.0, 20.0)
_sleep = time.sleep


def _transient(exc: Exception) -> bool:
    text = str(exc)
    return "LLM HTTP 429" in text or "LLM HTTP 503" in text


# Flex requests may queue for minutes before they are served.
FLEX_TIMEOUT_S = 600.0


def service_tier() -> Optional[str]:
    """``flex`` reads filings at half price with slower, best-effort service; unset means standard."""
    tier = os.environ.get("INTELLENS_DISCLOSURE_SERVICE_TIER", "").strip().lower()
    return tier or None


def read_workers() -> int:
    """Chunks one walk sends to the model at once; the process-wide rate limit still applies."""
    try:
        return max(1, int(os.environ.get("INTELLENS_DISCLOSURE_READ_WORKERS", "1")))
    except ValueError:
        return 1


_PAUSED_DAY = ""


def configured() -> bool:
    from app.services import llm_client
    from app.services.feature_flags import llm_extract_enabled

    if os.environ.get("INTELLENS_DISCLOSURE_RECONCILE", "1").strip().lower() in ("0", "false", "no"):
        return False
    return llm_extract_enabled() and llm_client.llm_configured()


def paused() -> bool:
    return _PAUSED_DAY == datetime.now(timezone.utc).date().isoformat()


def pause_for_today() -> None:
    """The model hit its quota or daily cap: walks continue without it until tomorrow."""
    global _PAUSED_DAY
    _PAUSED_DAY = datetime.now(timezone.utc).date().isoformat()


def enabled() -> bool:
    return configured() and not paused()


# ── Extraction cache (one file per company) ─────────────────────────────────


def _cache_dir() -> Path:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    base = Path(override) if override else Path(__file__).resolve().parents[1] / "data"
    return base / "disclosures"


def _cache_path(company_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9_]+", "_", company_id.lower())
    return _cache_dir() / f"{safe}.json"


def load_extracts(company_id: str) -> Dict[str, Any]:
    path = _cache_path(company_id)
    if not path.exists():
        return {"docs": {}}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"docs": {}}
    blob.setdefault("docs", {})
    return blob


def save_extracts(company_id: str, blob: Dict[str, Any]) -> None:
    path = _cache_path(company_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(blob, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


# One call reads up to 48k characters: the prompt and per-call overhead are paid once per piece.
READ_CHUNK_CHARS = 48000
READ_CHUNK_OVERLAP = 1000
# Earlier reads cut 12k pieces; a filing fully read at that size is not read again.
LEGACY_CHUNK_CHARS = 12000


def read_chunks(text: str) -> List[str]:
    from app.services.extract_pipeline import text_chunks

    return text_chunks(text, size=READ_CHUNK_CHARS, overlap=READ_CHUNK_OVERLAP)


def _read_at_legacy_size(text: str, chunks: Dict[str, Any]) -> int:
    """Pieces of ``text`` already read at the old size; 0 unless every one of them was read."""
    from app.services.extract_pipeline import text_chunks

    keys = [_chunk_key(c) for c in text_chunks(text, size=LEGACY_CHUNK_CHARS)]
    return len(keys) if keys and all(k in chunks for k in keys) else 0


def _chunk_key(chunk: str) -> str:
    return hashlib.sha1(f"{ENGINE}|{chunk}".encode("utf-8")).hexdigest()[:20]


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _worth_reading(chunk: str) -> bool:
    """Skip boilerplate: a chunk with almost no figures cannot hold a promise or a result."""
    return len(_NUMBER.findall(chunk)) >= 3


def read_documents(
    company_id: str,
    docs: Iterable[Dict[str, Any]],
    *,
    company_name: str,
    market_id: str,
    fy_end_mmdd: Optional[str] = None,
    extractor: Optional[Extractor] = None,
) -> Dict[str, Any]:
    """Send unread chunks to the model under the shared daily budget. Returns call counts."""
    from app.services.extract_pipeline import _llm_budget_ok, note_llm_use

    blob = load_extracts(company_id)
    calls = skipped = failed = streak = 0
    budget_out = model_down = False
    use_model = extractor is not None or enabled()
    run = extractor or llm_extract
    pending: List[Tuple[Dict[str, Any], str, str, str]] = []
    for doc in docs if use_model else []:
        doc_id = str(doc.get("doc_id") or doc.get("url") or "")
        doc_date = _iso(doc.get("date"))
        if not doc_id or not doc_date:
            continue
        entry = blob["docs"].setdefault(
            doc_id,
            {"url": doc.get("url"), "date": doc_date, "title": doc.get("title"), "chunks": {}},
        )
        entry.update(url=doc.get("url"), date=doc_date, title=doc.get("title"))
        text = str(doc.get("text") or "")
        legacy = _read_at_legacy_size(text, entry["chunks"]) if entry["chunks"] else 0
        if legacy:
            skipped += legacy
            continue
        for chunk in read_chunks(text):
            key = _chunk_key(chunk)
            if key in entry["chunks"]:
                skipped += 1
            elif not _worth_reading(chunk):
                entry["chunks"][key] = {"guidance": [], "results": []}
            else:
                pending.append((entry, key, chunk, doc_date))

    def read_one(item: Tuple[Dict[str, Any], str, str, str]) -> Any:
        _, _, chunk, doc_date = item
        try:
            return run(
                chunk,
                company_name=company_name,
                market_id=market_id,
                doc_date=doc_date,
                fy_end_mmdd=fy_end_mmdd,
            )
        except Exception as exc:  # noqa: BLE001 — retried on a later run
            return exc

    workers = read_workers()
    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        for start in range(0, len(pending), workers):
            batch = []
            for item in pending[start : start + workers]:
                if extractor is None and not _llm_budget_ok():
                    budget_out = True
                    break
                if extractor is None:
                    note_llm_use()
                batch.append(item)
            calls += len(batch)
            outcomes = list(pool.map(read_one, batch)) if pool else [read_one(i) for i in batch]
            for (entry, key, _, _), found in zip(batch, outcomes):
                if isinstance(found, Exception):
                    failed += 1
                    streak += 1
                    model_down = model_down or streak >= MAX_FAILURE_STREAK
                else:
                    entry["chunks"][key] = found
                    streak = 0
            if budget_out or model_down:
                break
    finally:
        if pool:
            pool.shutdown(wait=True)
    save_extracts(company_id, blob)
    if extractor is None and (budget_out or model_down):
        pause_for_today()
    return {
        "model_used": use_model,
        "llm_calls": calls,
        "chunks_already_read": skipped,
        "failed": failed,
        "budget_out": budget_out or model_down,
        "model_unavailable": model_down,
    }


# ── Reconciliation (pure) ───────────────────────────────────────────────────


def _plus_minus_band(low: float, high: float, pm_raw: Any, quote: str) -> Optional[Tuple[float, float]]:
    """``$32.5 billion, plus or minus 2%`` → (31.85, 33.15) bn, only when the quote says so."""
    pm = _as_float(pm_raw)
    if pm is None or low != high or not 0 < pm <= 20:
        return None
    lowered = quote.lower()
    if not re.search(rf"(?<![\d.]){re.escape(format(pm, 'g'))}\s*(%|percent)", lowered):
        return None
    if not re.search(r"plus or minus|\+/-|±", lowered):
        return None
    return round(low * (1 - pm / 100), 6), round(low * (1 + pm / 100), 6)


def _found_items(
    docs_by_id: Dict[str, Dict[str, Any]],
    blob: Dict[str, Any],
    market_id: str,
    fy_end_mmdd: Optional[str],
) -> Iterable[Tuple[str, Dict[str, Any], str, Dict[str, Any]]]:
    """(doc_id, doc, filing date, {guidance, results}) from the model's reads and, for US
    releases, the rule reader."""
    for doc_id, entry in (blob.get("docs") or {}).items():
        doc = docs_by_id.get(doc_id)
        doc_date = _iso((entry or {}).get("date") or (doc or {}).get("date"))
        if doc is None or not doc_date:
            continue
        for found in ((entry or {}).get("chunks") or {}).values():
            yield doc_id, doc, doc_date, found
    if market_id != "US":
        return
    from app.services import us_release_rules

    for doc_id, doc in docs_by_id.items():
        doc_date = _iso(doc.get("date"))
        if doc.get("source") != "sec_filing" or not doc_date:
            continue
        yield doc_id, doc, doc_date, us_release_rules.extract(
            str(doc.get("text") or ""), doc_date=doc_date, fy_end_mmdd=fy_end_mmdd
        )


def _check_item(
    kind: str, item: Dict[str, Any], text: str, market_id: str, fy_end_mmdd: Optional[str], allowed: set
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """One statement → (checked fields, None) or (None, reason it was dropped)."""
    metric = normalize_metric(item.get("metric"))
    if not metric or metric not in allowed:
        return None, "unknown_metric"
    period = canonical_period(item.get("period"), market_id)
    if not period or not period_bounds(period, market_id, fy_end_mmdd):
        return None, "bad_period"
    quote = re.sub(r"\s+", " ", str(item.get("quote") or "")).strip()[:MAX_QUOTE_CHARS]
    if not quote_verbatim(quote, text):
        return None, "not_verbatim"
    band: Optional[Tuple[float, float]] = None
    if kind == "guidance":
        low, high = _as_float(item.get("low")), _as_float(item.get("high"))
        if low is None and high is None:
            low = high = _as_float(item.get("value"))
        low = low if low is not None else high
        high = high if high is not None else low
        if low is None or high is None:
            return None, "number_not_in_quote"
        low, high = min(low, high), max(low, high)
        numbers = [low] if low == high else [low, high]
        band = _plus_minus_band(low, high, item.get("pm_pct"), quote)
    else:
        value = _as_float(item.get("value"))
        if value is None:
            return None, "number_not_in_quote"
        numbers = [value]
    if not _numbers_fit(metric, quote, numbers):
        return None, "number_not_in_quote"
    lo, hi = band or (numbers[0], numbers[-1])
    return {"metric": metric, "period": period, "quote": quote, "numbers": numbers, "low": lo, "high": hi}, None


def _statements(
    docs_by_id: Dict[str, Dict[str, Any]],
    blob: Dict[str, Any],
    market_id: str,
    fy_end_mmdd: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """Checked guidance and result statements across every read filing."""
    guidance: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    dropped = {"unknown_metric": 0, "bad_period": 0, "not_verbatim": 0, "number_not_in_quote": 0}
    seen = set()
    allowed = {m["id"] for m in metrics_for_market(market_id)}
    for doc_id, doc, doc_date, found in _found_items(docs_by_id, blob, market_id, fy_end_mmdd):
        text = str(doc.get("text") or "")
        entry = (blob.get("docs") or {}).get(doc_id) or {}
        for kind, items in (("guidance", found.get("guidance") or []), ("result", found.get("results") or [])):
            for item in items:
                checked, why = _check_item(kind, item, text, market_id, fy_end_mmdd, allowed)
                if checked is None:
                    dropped[str(why)] += 1
                    continue
                key = (kind, checked["metric"], checked["period"], tuple(checked["numbers"]), doc_id)
                if key in seen:
                    continue
                seen.add(key)
                row = {
                    "metric": checked["metric"],
                    "period": checked["period"],
                    "quote": checked["quote"],
                    "doc_id": doc_id,
                    "url": str(doc.get("url") or entry.get("url") or ""),
                    "title": str(doc.get("title") or entry.get("title") or ""),
                    "date": doc_date,
                }
                if kind == "guidance":
                    guidance.append({**row, "low": checked["low"], "high": checked["high"]})
                else:
                    results.append({**row, "value": checked["numbers"][0]})
    return guidance, results, dropped


def _stem(metric_id: str) -> str:
    stem = metric_id
    for suffix in ("_pct", "_cc"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def metrics_lookalike(left: str, right: str) -> bool:
    """Same family and unit, different id, shared stem (reported growth vs constant-currency)."""
    if not left or not right or left == right:
        return False
    a, b = get_metric(left), get_metric(right)
    if not a or not b:
        return False
    if a.get("family") != b.get("family") or a.get("unit") != b.get("unit"):
        return False
    return _stem(left) == _stem(right)


_BPS_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:basis\s+points|\bbps\b)", re.I)
_CRORE_RE = re.compile(r"\d+(?:\.\d+)?\s*crore", re.I)
_MILLION_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:million|\bmn\b)", re.I)


def unit_conflict(metric_id: str, guidance_quote: str, result_quote: str) -> bool:
    """The catalog unit and the scale words beside the numbers disagree.

    A percent metric quoted in basis points, or a crore metric quoted in millions,
    is not a match even when the bare digits sit in both sentences.
    """
    rule = get_metric(metric_id) or {}
    unit = str(rule.get("unit") or "")
    g, r = guidance_quote or "", result_quote or ""
    g_bps, r_bps = bool(_BPS_RE.search(g)), bool(_BPS_RE.search(r))
    if unit == "pct" and g_bps != r_bps:
        return True
    g_cr, r_cr = bool(_CRORE_RE.search(g)), bool(_CRORE_RE.search(r))
    g_mn, r_mn = bool(_MILLION_RE.search(g)), bool(_MILLION_RE.search(r))
    if unit in ("inr_cr", "usd_mn") and ((g_cr and r_mn) or (g_mn and r_cr)):
        return True
    return False


def quiet_drop_proposals(guidance_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A metric missing from the next two guidance filings is a proposal, not a miss.

    The cycle count matches ``commitments.QUIET_DROP_CYCLES``. A later mention clears it.
    """
    from app.services.commitments import QUIET_DROP_CYCLES

    filings: List[Dict[str, Any]] = []
    seen = set()
    by_doc: Dict[str, set] = {}
    for g in sorted(guidance_rows, key=lambda row: (row["date"], row["doc_id"])):
        by_doc.setdefault(g["doc_id"], set()).add(g["metric"])
        if g["doc_id"] in seen:
            continue
        seen.add(g["doc_id"])
        filings.append(g)
    last_idx: Dict[str, int] = {}
    for i, filing in enumerate(filings):
        for metric in by_doc[filing["doc_id"]]:
            last_idx[metric] = i
    proposals: List[Dict[str, Any]] = []
    for metric, idx in sorted(last_idx.items()):
        after = filings[idx + 1 : idx + 1 + QUIET_DROP_CYCLES]
        if len(after) < QUIET_DROP_CYCLES:
            continue
        period = next(
            g["period"]
            for g in guidance_rows
            if g["doc_id"] == filings[idx]["doc_id"] and g["metric"] == metric
        )
        proposals.append(
            {
                "metric": metric,
                "period": period,
                "doc_ids": [f["doc_id"] for f in after],
            }
        )
    return proposals


def reconcile(
    company_id: str,
    docs: Iterable[Dict[str, Any]],
    blob: Dict[str, Any],
    *,
    market_id: str,
    fy_end_mmdd: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, Any]:
    """Outcome rows from read filings. Pure: same inputs, same rows."""
    reviewed_on = today or datetime.now(timezone.utc).date().isoformat()
    docs_by_id = {str(d.get("doc_id") or d.get("url") or ""): d for d in docs}
    guidance, results, dropped = _statements(docs_by_id, blob, market_id, fy_end_mmdd)

    by_key: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for g in guidance:
        start, end = period_bounds(g["period"], market_id, fy_end_mmdd)  # type: ignore[misc]
        made = date.fromisoformat(g["date"])
        if made >= end or (end - made).days > GUIDANCE_HORIZON_DAYS:
            continue
        by_key.setdefault((g["period"], g["metric"]), []).append(g)
    actual_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in sorted(results, key=lambda x: (x["date"], x["doc_id"])):
        _, end = period_bounds(r["period"], market_id, fy_end_mmdd)  # type: ignore[misc]
        filed = date.fromisoformat(r["date"])
        if filed < end or (filed - end).days > RESULT_WINDOW_DAYS:
            continue
        actual_by_key.setdefault((r["period"], r["metric"]), r)

    conflicts: List[Dict[str, Any]] = []
    seen_conflict = set()

    def _add_conflict(item: Dict[str, Any]) -> None:
        key = (item["period"], item["promise_metric"], item["result_metric"], item["reason"])
        if key in seen_conflict:
            return
        seen_conflict.add(key)
        conflicts.append(item)

    rows: List[Dict[str, Any]] = []
    for (period, metric), stmts in sorted(by_key.items()):
        stmts.sort(key=lambda x: (x["date"], x["doc_id"], x["low"], x["high"]))
        opening = stmts[0]
        revisions: List[Dict[str, Any]] = []
        band = (opening["low"], opening["high"])
        for s in stmts[1:]:
            if s["date"] == opening["date"] or (s["low"], s["high"]) == band:
                continue
            band = (s["low"], s["high"])
            revisions.append(
                {
                    "as_of": s["date"],
                    "guided_low": s["low"],
                    "guided_high": s["high"],
                    "source_url": s["url"],
                    "source_ref": s["title"],
                    "quote": s["quote"],
                }
            )
        row: Dict[str, Any] = {
            "company_id": company_id,
            "period": period,
            "period_end": period_end(period, market_id, fy_end_mmdd),
            "metric": metric,
            "guided_low": opening["low"],
            "guided_high": opening["high"],
            "guided_value": (opening["low"] + opening["high"]) / 2.0,
            "guided_text": opening["quote"],
            "guidance_quote": opening["quote"],
            "guidance_source_url": opening["url"],
            "guidance_source_ref": opening["title"],
            "guidance_as_of": opening["date"],
            "guidance_doc_id": opening["doc_id"],
            "revisions": revisions,
            "actual_value": None,
            "confidence": 0.85,
            "speaker": "Management",
            "thread_id": f"{company_id}-{metric}",
            "dropped": False,
            "extract_engine": ENGINE,
            "review_status": "pending",
        }
        from app.data.metric_catalog import metric_basis

        basis = metric_basis(metric)
        if basis:
            row["reporting_basis"] = basis
        actual = actual_by_key.get((period, metric))
        if actual is not None and unit_conflict(metric, opening["quote"], actual["quote"]):
            _add_conflict(
                {
                    "period": period,
                    "promise_metric": metric,
                    "result_metric": metric,
                    "promise_doc_id": opening["doc_id"],
                    "result_doc_id": actual["doc_id"],
                    "promise_quote": opening["quote"],
                    "result_quote": actual["quote"],
                    "reason": "unit",
                }
            )
            actual = None
        for (other_period, other_metric), other in actual_by_key.items():
            if other_period != period or not metrics_lookalike(metric, other_metric):
                continue
            _add_conflict(
                {
                    "period": period,
                    "promise_metric": metric,
                    "result_metric": other_metric,
                    "promise_doc_id": opening["doc_id"],
                    "result_doc_id": other["doc_id"],
                    "promise_quote": opening["quote"],
                    "result_quote": other["quote"],
                    "reason": "metric",
                }
            )
        if actual is not None:
            row.update(
                actual_value=actual["value"],
                quote_span=actual["quote"],
                source_url=actual["url"],
                source_ref=actual["title"],
                as_of=actual["date"],
                doc_id=actual["doc_id"],
                review_status="accepted",
                reviewed_by=REVIEWER,
                reviewed_at=reviewed_on,
                source_verified=True,
                citeable=True,
            )
            if basis:
                row["actual_reporting_basis"] = basis
        rows.append(row)
    kept = [g for stmts in by_key.values() for g in stmts]
    return {
        "rows": rows,
        "guidance_found": len(guidance),
        "results_found": len(results),
        "closed": sum(1 for r in rows if r["actual_value"] is not None),
        "dropped": dropped,
        "conflicts": conflicts,
        "quiet_drops": quiet_drop_proposals(kept),
    }


# ── Apply to the dataset ────────────────────────────────────────────────────


def _owned(row: Dict[str, Any]) -> bool:
    return str(row.get("extract_engine") or "") in OWNED_ENGINES or not str(row.get("reviewed_by") or "").strip()


@locked
def apply_rows(company_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Replace this module's rows for one company. Hand-labeled dossiers are never touched."""
    from app.data.seed import get_data, save_data
    from app.services.extract_pipeline import _save_overlay, maybe_promote_extracted

    data = get_data()
    company = next((c for c in data.get("companies") or [] if c["id"] == company_id), None)
    if company is None:
        return {"applied": False, "reason": "no_company_record"}
    if company.get("data_quality") == "hand_labeled":
        return {"applied": False, "reason": "hand_labeled"}
    outcomes = data.setdefault("outcomes", {})
    kept = [r for r in outcomes.get(company_id) or [] if not _owned(r)]
    have = {(str(r.get("period")), str(r.get("metric"))) for r in kept}
    outcomes[company_id] = kept + [r for r in rows if (r["period"], r["metric"]) not in have]
    save_data()
    _save_overlay([company_id])
    quality = maybe_promote_extracted(company_id)
    return {"applied": True, "rows": len(outcomes[company_id]), "data_quality": quality}


@locked
def log_moves(company_ids: Iterable[str], *, lead: str) -> int:
    """Ledger row + public changelog line for every number these companies gained, moved or lost."""
    from app.services.guidance_review import _append_changelog
    from app.services.score_ledger import append_many, snapshot_rows

    wanted = set(company_ids)
    if not wanted:
        return 0
    moves = [m for m in snapshot_rows(reason="new_filing", note=lead, by=REVIEWER) if m.company_id in wanted]
    n = append_many(moves)
    if moves:
        _append_changelog(datetime.now(timezone.utc).date(), moves, lead=lead)
    return n


def process_company(
    company_id: str,
    *,
    market_id: str,
    company_name: str,
    fy_end_mmdd: Optional[str] = None,
    extractor: Optional[Extractor] = None,
) -> Dict[str, Any]:
    """Read unread filings, reconcile every read filing, and store the rows."""
    from app.services.exchange_filings import discovery_since
    from app.services.extract_pipeline import _accepted_docs

    docs = _accepted_docs(company_id)
    # Filings before the walk's start date are not sent to the model; earlier reads still reconcile.
    since = discovery_since()
    read = read_documents(
        company_id,
        [d for d in docs if (_iso(d.get("date")) or "") >= since],
        company_name=company_name,
        market_id=market_id,
        fy_end_mmdd=fy_end_mmdd,
        extractor=extractor,
    )
    out = reconcile(company_id, docs, load_extracts(company_id), market_id=market_id, fy_end_mmdd=fy_end_mmdd)
    applied = apply_rows(company_id, out["rows"])
    from app.services.labeling_queue import sync_reconcile_findings

    queued = sync_reconcile_findings(company_id, out)
    return {
        "company_id": company_id,
        "docs": len(docs),
        **read,
        **{k: v for k, v in out.items() if k != "rows"},
        "rows": len(out["rows"]),
        **applied,
        "queue": queued,
    }
