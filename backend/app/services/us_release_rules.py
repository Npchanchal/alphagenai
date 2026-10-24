"""Rule-based reading of US results releases: company-total revenue and EPS only.

Works without a model, so the US walk still produces checked rows when the
model is unavailable. Deliberately narrow: a sentence has to state company
revenue or EPS in one of the standard release forms, and the period has to be
stated in the sentence, in the outlook heading just above it, or follow from
the filing date (a release reports the quarter that ended just before it).
Segment lines ("Data Center revenue was …") are never read as company revenue.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

ENGINE = "us_release_rules_v1"
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
_ORD_RE = r"(first|second|third|fourth|1st|2nd|3rd|4th)"
_SCALE = {"billion": 1000.0, "bn": 1000.0, "million": 1.0, "mn": 1.0}
_MONEY = r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(billion|million|bn|mn)?"
_HEADING_Q = re.compile(
    rf"(?:outlook|guidance|expects?)[^.]{{0,60}}?{_ORD_RE}[ -]quarter (?:of )?(?:fiscal (?:year )?)?(\d{{4}})",
    re.I,
)
_HEADING_Q2 = re.compile(rf"{_ORD_RE}[ -]quarter (?:of )?(?:fiscal (?:year )?)?(\d{{4}}) (?:outlook|guidance)", re.I)
_HEADING_QN = re.compile(r"\bQ([1-4])\s*(?:FY|F)?\s?(\d{4}) (?:outlook|guidance)", re.I)
_FY_IN = re.compile(r"(?:full[- ]year|fiscal(?: year)?|for the year|calendar year)\s*'?(\d{4})", re.I)
_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-Z•])|\s*•\s*")

_COMPANY_REVENUE = re.compile(
    r"^(?:(?:total|consolidated|net|quarterly|record|company)\s+)?(?:revenues?|net sales|sales)\b", re.I
)
_FY_REVENUE = re.compile(
    r"^(?:for (?:the )?(?:full[- ]year|fiscal(?: year)?) ?(?:\d{4})?,?\s+)(?:total |net )?(?:revenues?|net sales|sales)\b"
    r"|^(?:fiscal|full)[- ]year (?:total |net )?(?:revenues?|net sales|sales)\b",
    re.I,
)
_REPORTED = re.compile(
    rf"reported (?:record )?(?:total |quarterly )?(?:revenues?|net sales|sales) for the {_ORD_RE}[ -]quarter"
    rf"[^$]{{0,80}}?(?:of|was|were|totaled)\s+(?:a record\s+)?{_MONEY}",
    re.I,
)
_REV_WAS = re.compile(rf"\b(?:was|were|of|totaled|reached)\s+(?:a record\s+)?(?:approximately\s+)?{_MONEY}", re.I)
_EXPECT = re.compile(r"\b(?:expected|expects|expect|anticipate[sd]?|guidance|outlook|forecast|projects?)\b", re.I)
_RANGE = re.compile(
    rf"{_MONEY}\s*(?:to|and|-|–)\s*{_MONEY}",
    re.I,
)
_PLUS_MINUS = re.compile(r"plus or minus (\d+(?:\.\d+)?)\s*(?:%|percent)", re.I)
_EPS_VALUE = re.compile(r"\$\s?(\d+\.\d{2})\b")
_EPS_MENTION = re.compile(r"\b(?:diluted eps|eps|earnings per (?:diluted )?share)\b", re.I)
_EPS_PAIR = r"\$\s?(\d+\.\d{2})\s*(?:to|-|–|and)\s*\$\s?(\d+\.\d{2})"
_COMPARISON = re.compile(r"\b(?:compared (?:to|with)|versus|vs\.|up from|down from)\b[^;]*", re.I)
#: Flattened tables read as one long "sentence" packed with figures; such runs are skipped.
MAX_FIGURES = 6
_BASELINE = re.compile(r"based on the following|figures:|prior[- ]year (?:figures|base)", re.I)


def _num(raw: str) -> float:
    return float(raw.replace(",", ""))


def _usd_mn(value: str, scale: Optional[str], default_scale: Optional[str] = None) -> Optional[float]:
    s = (scale or default_scale or "").lower()
    if s not in _SCALE:
        return None
    return round(_num(value) * _SCALE[s], 6)


def _sentences(text: str) -> List[Tuple[int, str]]:
    out = []
    pos = 0
    for part in _SPLIT.split(text or ""):
        part_s = part.strip()
        if part_s:
            out.append((text.find(part_s, pos), part_s))
            pos = max(pos, out[-1][0])
    return out


def _quarter_label(q: int, fy: int) -> str:
    return f"Q{q} FY{fy}"


def _latest_quarter(filed: date, fy_end_mmdd: Optional[str], ordinal: Optional[int] = None) -> Optional[str]:
    from app.services.disclosures import period_bounds

    best: Optional[Tuple[date, str]] = None
    for fy in range(filed.year - 1, filed.year + 2):
        for q in range(1, 5):
            label = _quarter_label(q, fy)
            bounds = period_bounds(label, "US", fy_end_mmdd)
            if not bounds or bounds[1] >= filed or (filed - bounds[1]).days > 120:
                continue
            if ordinal is not None and q != ordinal:
                continue
            if best is None or bounds[1] > best[0]:
                best = (bounds[1], label)
    return best[1] if best else None


def _latest_fy(filed: date, fy_end_mmdd: Optional[str]) -> Optional[str]:
    from app.services.disclosures import period_bounds

    for fy in (filed.year, filed.year - 1):
        bounds = period_bounds(f"FY{fy}", "US", fy_end_mmdd)
        if bounds and bounds[1] < filed and (filed - bounds[1]).days <= 120:
            return f"FY{fy}"
    return None


def _heading_period(text: str, before: int) -> Optional[str]:
    window = text[max(0, before - 700) : before]
    found: Optional[Tuple[int, str]] = None
    for rx in (_HEADING_Q, _HEADING_Q2):
        for m in rx.finditer(window):
            label = _quarter_label(_ORD[m.group(1).lower()], int(m.group(2)))
            if found is None or m.start() > found[0]:
                found = (m.start(), label)
    for m in _HEADING_QN.finditer(window):
        if found is None or m.start() > found[0]:
            found = (m.start(), _quarter_label(int(m.group(1)), int(m.group(2))))
    return found[1] if found else None


def _guidance_band(sentence: str) -> Optional[Tuple[float, float, str]]:
    """(low, high, unit) in US$ m for revenue; None if the sentence states no band or point."""
    m = _RANGE.search(sentence)
    if m:
        lo = _usd_mn(m.group(1), m.group(2), m.group(4))
        hi = _usd_mn(m.group(3), m.group(4))
        if lo is not None and hi is not None and lo <= hi:
            return lo, hi, "range"
    m = re.search(rf"(?:to be|of|at)\s+(?:approximately\s+|about\s+)?{_MONEY}", sentence, re.I)
    if m:
        mid = _usd_mn(m.group(1), m.group(2))
        if mid is None:
            return None
        return mid, mid, "plus_minus" if _PLUS_MINUS.search(sentence) else "point"
    return None


def _eps_items(sentence: str, forward: bool) -> List[Tuple[str, float, float, int]]:
    """Each EPS mention takes the figure right after it, up to the next mention, so
    "GAAP EPS of $3.72 and adjusted EPS of $5.15" gives two items, not one mislabelled."""
    mentions = list(_EPS_MENTION.finditer(sentence))
    out: List[Tuple[str, float, float, int]] = []
    for i, m in enumerate(mentions):
        prev_figure = max((d.end() for d in _EPS_VALUE.finditer(sentence, 0, m.start())), default=0)
        adjusted = bool(re.search(r"adjusted|non-gaap", sentence[prev_figure : m.end()], re.I))
        metric = "eps_adjusted_usd" if adjusted else "eps_diluted_usd"
        segment = sentence[m.end() : mentions[i + 1].start() if i + 1 < len(mentions) else len(sentence)]
        cut = _COMPARISON.search(segment)
        segment = segment[: cut.start()] if cut else segment
        if forward:
            pair = re.search(_EPS_PAIR, segment)
            if pair and pair.start() <= 80:
                lo, hi = float(pair.group(1)), float(pair.group(2))
                if lo <= hi:
                    out.append((metric, lo, hi, m.end() + pair.start()))
        else:
            value = _EPS_VALUE.search(segment)
            if value and value.start() <= 60:
                out.append((metric, float(value.group(1)), float(value.group(1)), m.end() + value.start()))
    return out


def _stated_period(sentence: str) -> Optional[str]:
    m = re.search(rf"{_ORD_RE}[ -]quarter (?:of )?(?:fiscal (?:year )?)?(\d{{4}})", sentence, re.I)
    if m:
        return _quarter_label(_ORD[m.group(1).lower()], int(m.group(2)))
    m = re.search(rf"fiscal (?:year )?(\d{{4}}) {_ORD_RE}[ -]quarter", sentence, re.I)
    if m:
        return _quarter_label(_ORD[m.group(2).lower()], int(m.group(1)))
    m = _FY_IN.search(sentence)
    return f"FY{m.group(1)}" if m else None


def extract(text: str, *, doc_date: str, fy_end_mmdd: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    """{guidance: [...], results: [...]} in the same shape the model returns."""
    try:
        filed = date.fromisoformat(doc_date[:10])
    except ValueError:
        return {"guidance": [], "results": []}
    guidance: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    for at, s in _sentences(text):
        if len(s) < 20 or len(s) > 400 or _BASELINE.search(s):
            continue
        lowered = s.lower()
        forward = bool(_EXPECT.search(s))
        # ── company revenue ──
        reported = _REPORTED.search(s)
        if reported:
            value = _usd_mn(reported.group(2), reported.group(3))
            period = _latest_quarter(filed, fy_end_mmdd, _ORD[reported.group(1).lower()])
            if value is not None and period:
                results.append({"metric": "revenue_usd_mn", "period": period, "value": value, "quote": s})
            continue
        if len(re.findall(r"\d[\d,]*(?:\.\d+)?", s)) > MAX_FIGURES:
            continue
        if _FY_REVENUE.search(s) and not forward:
            m = _REV_WAS.search(s)
            fy = _FY_IN.search(s)
            period = f"FY{fy.group(1)}" if fy else _latest_fy(filed, fy_end_mmdd)
            if m and period:
                value = _usd_mn(m.group(1), m.group(2))
                if value is not None:
                    results.append({"metric": "revenue_usd_mn", "period": period, "value": value, "quote": s})
            continue
        if _COMPANY_REVENUE.search(s):
            if forward:
                band = _guidance_band(s)
                period = _stated_period(s) or (_heading_period(text, at) if len(s) <= 200 else None)
                if band and period:
                    lo, hi, _kind = band
                    guidance.append(
                        {"metric": "revenue_usd_mn", "period": period, "low": lo, "high": hi, "quote": s,
                         **({"pm_pct": float(_PLUS_MINUS.search(s).group(1))} if _kind == "plus_minus" else {})}
                    )
                continue
            q = re.search(rf"for the {_ORD_RE}[ -]quarter", s, re.I)
            m = _REV_WAS.search(s)
            if q and m:
                value = _usd_mn(m.group(1), m.group(2))
                period = _latest_quarter(filed, fy_end_mmdd, _ORD[q.group(1).lower()])
                if value is not None and period:
                    results.append({"metric": "revenue_usd_mn", "period": period, "value": value, "quote": s})
            continue
        # ── EPS ──
        if "per share" in lowered or "eps" in lowered:
            if "gaap and non-gaap" in lowered or "respectively" in lowered:
                continue
            for metric, lo, hi, at_figure in _eps_items(s, forward):
                # The period must be stated before the figure; text after it is often the next heading.
                before = _COMPARISON.sub("", s[:at_figure])
                if forward:
                    period = _stated_period(before)
                elif "for the quarter" in before.lower():
                    period = _latest_quarter(filed, fy_end_mmdd)
                else:
                    fy = _FY_IN.search(before)
                    period = f"FY{fy.group(1)}" if fy else None
                if not period:
                    continue
                if forward:
                    guidance.append({"metric": metric, "period": period, "low": lo, "high": hi, "quote": s})
                else:
                    results.append({"metric": metric, "period": period, "value": lo, "quote": s})
    return {"guidance": guidance, "results": results}
