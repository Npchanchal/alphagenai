"""Incremental change helpers (MoM / QoQ / YoY / PoP) for investment metrics.

Absolute levels are kept; change vs prior comparable period is first-class.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

_FY = re.compile(r"^FY\s*(\d{2}|\d{4})$", re.I)
_QFY = re.compile(r"^Q([1-4])\s*FY\s*(\d{2}|\d{4})$", re.I)
_FYQ = re.compile(r"^FY\s*(\d{2}|\d{4})\s*Q([1-4])$", re.I)
_YQ = re.compile(r"^(\d{4})-Q([1-4])$", re.I)
_YM = re.compile(r"^(\d{4})-(\d{2})$")
_ASOF = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def pct_change(current: Optional[float], prior: Optional[float]) -> Optional[float]:
    if current is None or prior is None:
        return None
    if prior == 0:
        return 0.0 if current == 0 else None
    return round(100.0 * (current - prior) / abs(prior), 2)


def _norm_year(y: str) -> int:
    n = int(y)
    if n < 100:
        return 2000 + n
    return n


def parse_period(period: str) -> Tuple[int, str]:
    """Return (sort_key_months, frequency) for ordering and horizon inference.

    frequency: annual | quarterly | monthly | daily | unknown
    sort_key approximates months since year 0 for coarse ordering.
    """
    p = (period or "").strip()
    m = _FY.match(p)
    if m:
        y = _norm_year(m.group(1))
        return y * 12 + 3, "annual"  # fiscal year-end approx Mar
    m = _QFY.match(p)
    if m:
        q, y = int(m.group(1)), _norm_year(m.group(2))
        return y * 12 + (q - 1) * 3, "quarterly"
    m = _FYQ.match(p)
    if m:
        y, q = _norm_year(m.group(1)), int(m.group(2))
        return y * 12 + (q - 1) * 3, "quarterly"
    m = _YQ.match(p)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        return y * 12 + (q - 1) * 3, "quarterly"
    m = _YM.match(p)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return y * 12 + (mo - 1), "monthly"
    m = _ASOF.match(p)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return y * 12 + (mo - 1), "daily"
    # fallback: lexical hash for stable unknown order
    return abs(hash(p)) % 10_000, "unknown"


def infer_horizon(prior_period: str, current_period: str) -> str:
    """Label the change window: YoY, QoQ, MoM, or PoP (generic prior)."""
    _, f_cur = parse_period(current_period)
    k0, f0 = parse_period(prior_period)
    k1, f1 = parse_period(current_period)
    if f0 == "unknown" or f1 == "unknown" or f0 != f1:
        # FY22→FY23 still YoY even if freq parse matches annual
        if _FY.match(prior_period) and _FY.match(current_period):
            return "YoY"
        return "PoP"
    delta = k1 - k0
    if f_cur == "annual" and 10 <= delta <= 14:
        return "YoY"
    if f_cur == "quarterly":
        if 2 <= delta <= 4:
            return "QoQ"
        if 10 <= delta <= 14:
            return "YoY"
    if f_cur == "monthly":
        if delta == 1:
            return "MoM"
        if 11 <= delta <= 13:
            return "YoY"
    if f_cur == "daily":
        if delta == 0:
            # same month bucket — treat as WoW when as-of day gap ~7 handled in change_bundle
            return "MoM"
        if delta == 1:
            return "MoM"
        if 2 <= delta <= 4:
            return "QoQ"
        if 11 <= delta <= 13:
            return "YoY"
    if f_cur == "annual":
        return "YoY"
    return "PoP"


def sort_periods(periods: Sequence[str]) -> List[str]:
    return sorted(periods, key=lambda p: parse_period(p)[0])


def period_rank(period: str) -> Optional[int]:
    """Months-since-year-0 rank from ``parse_period``, or None if the label is unknown."""
    key, freq = parse_period(period)
    if freq == "unknown":
        return None
    return key


def _row_field(row: Any, name: str) -> str:
    if isinstance(row, dict):
        return str(row.get(name) or "")
    return str(getattr(row, name, None) or "")


def sort_evidence_listing(rows: Sequence[Any]) -> List[Any]:
    """Latest period first, then latest ``as_of``, then metric name.

    A label that is not a fiscal period or a date sorts last. Revision trails
    that read opening → final should keep ``sort_periods`` (oldest first).
    """
    items = list(rows)
    items.sort(key=lambda row: _row_field(row, "metric"))
    items.sort(key=_evidence_chrono_key, reverse=True)
    return items


def _evidence_chrono_key(row: Any) -> Tuple[bool, int, str]:
    rank = period_rank(_row_field(row, "period"))
    as_of = _row_field(row, "as_of") or _row_field(row, "date") or _row_field(row, "ingested_at")
    return (rank is not None, rank or 0, as_of)


def sort_document_listing(docs: Sequence[Any]) -> List[Any]:
    """Newest filing date first. Undated rows fall back to period, latest first."""
    items = list(docs)

    def key(row: Any) -> Tuple[str, bool, int]:
        date = _row_field(row, "date") or _row_field(row, "ingested_at")
        rank = period_rank(_row_field(row, "period"))
        return (date, rank is not None, rank or 0)

    items.sort(key=key, reverse=True)
    return items


def enrich_value_series(
    points: Sequence[Dict[str, Any]],
    *,
    period_key: str = "period",
    value_key: str = "value",
) -> List[Dict[str, Any]]:
    """Attach prior_value, change_pct, change_horizon to each point (ordered)."""
    ordered = sorted(points, key=lambda r: parse_period(str(r.get(period_key, "")))[0])
    out: List[Dict[str, Any]] = []
    prev_period: Optional[str] = None
    prev_val: Optional[float] = None
    for row in ordered:
        cur = dict(row)
        period = str(cur.get(period_key, ""))
        raw = cur.get(value_key)
        val = None if raw is None else float(raw)
        cur["prior_value"] = prev_val
        cur["change_pct"] = pct_change(val, prev_val)
        cur["change_horizon"] = (
            None if prev_period is None else infer_horizon(prev_period, period)
        )
        out.append(cur)
        if val is not None:
            prev_val = val
            prev_period = period
    return out


def enrich_metric_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    value_keys: Sequence[str] = ("actual", "management_guidance", "street_consensus"),
) -> List[Dict[str, Any]]:
    """For estimate-like rows, add *_change_pct / *_change_horizon per metric series."""
    by_metric: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_metric.setdefault(str(r.get("metric", "")), []).append(dict(r))

    enriched: List[Dict[str, Any]] = []
    for metric, group in by_metric.items():
        ordered = sorted(group, key=lambda r: parse_period(str(r.get("period", "")))[0])
        priors: Dict[str, Tuple[Optional[str], Optional[float]]] = {
            k: (None, None) for k in value_keys
        }
        for row in ordered:
            period = str(row.get("period", ""))
            for vk in value_keys:
                prev_p, prev_v = priors[vk]
                cur = row.get(vk)
                cur_f = None if cur is None else float(cur)
                row[f"{vk}_prior"] = prev_v
                row[f"{vk}_change_pct"] = pct_change(cur_f, prev_v)
                row[f"{vk}_change_horizon"] = (
                    None if prev_p is None else infer_horizon(prev_p, period)
                )
                if cur_f is not None:
                    priors[vk] = (period, cur_f)
            enriched.append(row)

    # restore original relative order within metric groups by period sort overall
    return sorted(
        enriched,
        key=lambda r: (str(r.get("metric", "")), parse_period(str(r.get("period", "")))[0]),
    )


def change_bundle(
    current: Optional[float],
    series: Sequence[Tuple[str, Optional[float]]],
) -> Dict[str, Any]:
    """Build WoW/MoM/QoQ/YoY bundle from a dated series ending at current.

    series: oldest→newest (period, value). Missing horizons stay null — never fake 0.

    Calendar-aligned resolution (preferred when periods parse):
      WoW ≈ 5–9 days · MoM ≈ 25–40 days · QoQ ≈ 80–110 days · YoY ≈ 350–380 days
    Also matches FY / quarter / month labels via ``infer_horizon`` and same-period prior year.
    """
    ordered = list(series)
    if not ordered and current is not None:
        return {
            "value": current,
            "wow_pct": None,
            "mom_pct": None,
            "qoq_pct": None,
            "yoy_pct": None,
            "pop_pct": None,
            "pop_horizon": None,
            "history": [],
        }
    hist = enrich_value_series(
        [{"period": p, "value": v} for p, v in ordered],
        period_key="period",
        value_key="value",
    )
    latest = hist[-1] if hist else {"value": current, "change_pct": None, "change_horizon": None}
    mom = qoq = yoy = wow = None

    from datetime import date

    def _as_date(p: str) -> Optional[date]:
        m = _ASOF.match(p)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = _YM.match(p)
        if m:
            return date(int(m.group(1)), int(m.group(2)), 1)
        m = _YQ.match(p)
        if m:
            y, q = int(m.group(1)), int(m.group(2))
            return date(y, (q - 1) * 3 + 1, 1)
        m = _QFY.match(p)
        if m:
            q, y = int(m.group(1)), _norm_year(m.group(2))
            return date(y, (q - 1) * 3 + 1, 1)
        m = _FYQ.match(p)
        if m:
            y, q = _norm_year(m.group(1)), int(m.group(2))
            return date(y, (q - 1) * 3 + 1, 1)
        m = _FY.match(p)
        if m:
            return date(_norm_year(m.group(1)), 3, 31)
        return None

    dated: List[Tuple[date, str, float]] = []
    for row in hist:
        p = str(row.get("period") or "")
        if row.get("value") is None:
            continue
        d = _as_date(p)
        if d is not None:
            dated.append((d, p, float(row["value"])))

    if len(dated) >= 2:
        cur_d, _cur_p, cur_v = dated[-1]

        def _pick(lo: int, hi: int) -> Optional[float]:
            best = None
            best_dist = None
            target = (lo + hi) // 2
            for d, _p, v in reversed(dated[:-1]):
                days = (cur_d - d).days
                if lo <= days <= hi:
                    dist = abs(days - target)
                    if best_dist is None or dist < best_dist:
                        best = pct_change(cur_v, v)
                        best_dist = dist
            return best

        wow = _pick(5, 9)
        mom = _pick(25, 40)
        qoq = _pick(80, 110)
        yoy = _pick(350, 380)

    # Label-based fill when calendar windows miss (FY / QoQ chains)
    for row in reversed(hist):
        h = row.get("change_horizon")
        ch = row.get("change_pct")
        if h == "MoM" and mom is None:
            mom = ch
        elif h == "QoQ" and qoq is None:
            qoq = ch
        elif h == "YoY" and yoy is None:
            yoy = ch

    if yoy is None and hist:
        last_p = str(hist[-1].get("period", ""))
        last_v = hist[-1].get("value")
        last_k, freq = parse_period(last_p)
        for row in hist[:-1]:
            pk = str(row.get("period", ""))
            k, f = parse_period(pk)
            if f == freq and abs((last_k - k) - 12) <= 1:
                yoy = pct_change(
                    None if last_v is None else float(last_v),
                    None if row.get("value") is None else float(row["value"]),
                )
                break
    if yoy is None and hist and hist[-1].get("change_horizon") in ("YoY", "PoP"):
        # Only accept PoP as YoY for annual series
        last_p = str(hist[-1].get("period", ""))
        if _FY.match(last_p) or hist[-1].get("change_horizon") == "YoY":
            yoy = hist[-1].get("change_pct")
    if qoq is None and hist and hist[-1].get("change_horizon") == "QoQ":
        qoq = hist[-1].get("change_pct")
    if mom is None and hist and hist[-1].get("change_horizon") == "MoM":
        mom = hist[-1].get("change_pct")

    return {
        "value": latest.get("value", current),
        "wow_pct": wow,
        "mom_pct": mom,
        "qoq_pct": qoq,
        "yoy_pct": yoy,
        "pop_pct": latest.get("change_pct"),
        "pop_horizon": latest.get("change_horizon"),
        "history": hist,
    }


def multi_horizon_gci_series(
    company_id: str,
    anchor: float,
    *,
    weeks: int = 56,
) -> List[Tuple[str, float]]:
    """Deterministic weekly GCI path so WoW/MoM/QoQ/YoY all resolve.

    Newest point = ``anchor``. Demo / provisional analytics only — not citeable IR.
    """
    import hashlib
    from datetime import date, timedelta

    digest = hashlib.sha256(f"{company_id}|mh|{anchor}".encode("utf-8")).hexdigest()
    end = date(2025, 8, 15)
    points: List[Tuple[str, float]] = []
    # Build oldest→newest; walk backward from anchor
    trail = [float(anchor)]
    for i in range(1, weeks):
        u = (int(digest[(i * 2) % 60 : (i * 2) % 60 + 4], 16) % 10000) / 10000.0
        delta = (u - 0.5) * 5.0
        prev = max(35.0, min(98.0, trail[-1] - delta * 0.4))
        trail.append(prev)
    trail.reverse()
    trail[-1] = float(anchor)
    for i, score in enumerate(trail):
        d = end - timedelta(weeks=(weeks - 1 - i))
        # Snap to Friday-ish labels for stable WoW gaps of 7 days
        points.append((d.isoformat(), round(score, 1)))
    return points



def demo_fundamental_series(
    base: float, ticker: str, *, kind: str = "quarterly"
) -> List[Tuple[str, float]]:
    """Deterministic demo history so UI always has MoM/QoQ/YoY context."""
    seed = sum(ord(c) for c in ticker) % 17
    if kind == "annual":
        periods = [f"FY{y}" for y in (22, 23, 24, 25)]
        vals = [round(base - 3 + i * 0.8 + (seed % 5) * 0.1, 2) for i in range(4)]
        vals[-1] = base
        return list(zip(periods, vals))
    # quarterly: include YoY anchor (same quarter prior year)
    periods = ["Q4FY24", "Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25"]
    vals = [round(base - 2.0 + i * 0.45 + ((seed + i) % 3) * 0.12, 2) for i in range(5)]
    vals[-1] = base
    return list(zip(periods, vals))
