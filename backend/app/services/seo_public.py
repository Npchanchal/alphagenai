"""Public SEO payloads for hand-labeled GCI dossiers (plan W5.1–W5.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data.metric_catalog import display_name_for, get_metric
from app.data.seed import get_outcomes, list_companies
from app.services.gci_scoring import OutcomeLabel, classify_outcome
from app.services.guidance_flags import score_meta
from app.services.score_policy import is_pending_guidance_cite, is_scoreable, is_source_verify_fail

CLOSED = {OutcomeLabel.MET.value, OutcomeLabel.EXCEEDED.value, OutcomeLabel.MISSED.value}
TIER_LABEL = {"provisional": "Provisional", "established": "Established", "deep": "Deep"}


def format_as_of(iso: Optional[str]) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)[:10]
    return d.strftime("%d %b %Y").lstrip("0")


def _dual_cited(o) -> bool:
    return not is_pending_guidance_cite(o) and not is_source_verify_fail(o)


def record_sentence(outcomes, metrics=None) -> str:
    return _sentence(
        [(o, classify_outcome(o).value) for o in outcomes if o.actual_value is not None and _dual_cited(o)],
        metrics=metrics,
    )


def record_sentence_from_views(views, metrics=None) -> str:
    """Same sentence from dossier ``OutcomeView`` rows, whose ``label`` already excludes uncited rows."""
    return _sentence([(o, o.label) for o in views if o.actual_value is not None], metrics=metrics)


def _sentence(labelled, metrics=None) -> str:
    closed_rows = [(o, lab) for o, lab in labelled if lab in CLOSED]
    wanted = {m for m in (metrics or []) if m}
    scored = [r for r in closed_rows if r[0].metric in wanted] if wanted else []
    if scored:
        focus = scored
    elif wanted:
        focus = closed_rows
    else:
        revenue = [r for r in closed_rows if "revenue" in (r[0].metric or "")]
        focus = revenue or closed_rows
    if not focus:
        return "No closed, dual-cited results yet."
    missed = sorted({r[0].period for r in focus if r[1] == OutcomeLabel.MISSED.value})
    met_or_beat = sum(1 for r in focus if r[1] in (OutcomeLabel.MET.value, OutcomeLabel.EXCEEDED.value))
    metric_label = display_name_for(focus[0][0].metric)
    closed = len(focus)
    if met_or_beat == 0:
        if closed == 1:
            return f"Missed {metric_label} guidance in {missed[0]}, the only closed year."
        return f"Missed {metric_label} guidance in all {closed} closed years ({', '.join(missed)})."
    years = "closed year" if closed == 1 else "closed years"
    missed_clause = f"; missed {', '.join(missed)}" if missed else ""
    return f"Met or beat {metric_label} guidance in {met_or_beat} of {closed} {years}{missed_clause}."


def dossier_title(
    name: str, gci: Optional[float], as_of: Optional[str], tier: Optional[str] = None
) -> str:
    """The tier sits next to every published number, title included (rule index-integrity)."""
    as_of_s = format_as_of(as_of)
    bits = [f"{name} — Guidance Credibility Index (GCI)"]
    if gci is not None:
        bits[0] += f" {gci:.1f}".rstrip("0").rstrip(".")
        if TIER_LABEL.get(tier or ""):
            bits.append(TIER_LABEL[tier])
    if as_of_s:
        bits.append(f"Data as of {as_of_s}")
    return " · ".join(bits)


def _evidence_rows(outcomes) -> List[Dict[str, Any]]:
    """Closed, dual-cited rows — the same rows the score is built from — latest first."""
    rows: List[Dict[str, Any]] = []
    for o in outcomes:
        if o.actual_value is None or not _dual_cited(o):
            continue
        label = classify_outcome(o).value
        if label not in CLOSED or not o.source_url or not o.guidance_source_url:
            continue
        meta = get_metric(o.metric) or {}
        rows.append(
            {
                "period": o.period,
                "metric": display_name_for(o.metric),
                "unit": meta.get("unit") or "",
                "guided_low": o.guided_low,
                "guided_high": o.guided_high,
                "guided_value": o.guided_value,
                "actual_value": o.actual_value,
                "outcome": label,
                "guidance_quote": o.guidance_quote or "",
                "guidance_source_url": o.guidance_source_url,
                "guidance_as_of": o.guidance_as_of or "",
                "actual_quote": o.quote_span or "",
                "source_url": o.source_url,
                "as_of": o.as_of or "",
            }
        )
    rows.sort(key=lambda r: (r["as_of"], r["period"]), reverse=True)
    return rows


def dossier_description(sentence: str, as_of: Optional[str]) -> str:
    as_of_s = format_as_of(as_of)
    bits = [sentence]
    if as_of_s:
        bits.append(f"Data as of {as_of_s}.")
    bits.append("Not investment advice.")
    return " ".join(bits)


def list_indexable_dossiers() -> List[Dict[str, Any]]:
    """Hand-labeled companies with a published GCI — the indexable public dossiers.

    A hand-labeled company without a published level stays ``noindex``: its page has no
    number to cite, and dozens of such pages read as thin, near-duplicate content.
    """
    rows: List[Dict[str, Any]] = []
    for c in list_companies():
        quality = c.get("data_quality") or ""
        if quality != "hand_labeled":
            continue
        outcomes = get_outcomes(c["id"])
        meta = score_meta(outcomes, scoreable=is_scoreable(quality), company_id=c["id"])
        gci = meta.get("gci_score")
        if gci is None:
            continue
        sentence = record_sentence(outcomes, metrics=list(meta.get("by_metric") or {}))
        as_of = meta.get("as_of")
        tier = meta.get("confidence_tier")
        rows.append(
            {
                "id": c["id"],
                "name": c["name"],
                "ticker": c["ticker"],
                "gci_score": gci,
                "confidence_tier": tier,
                "as_of": as_of,
                "data_quality": quality,
                "record_sentence": sentence,
                "title": dossier_title(c["name"], gci, as_of, tier),
                "description": dossier_description(sentence, as_of),
                "path": f"/companies/{c['id']}",
                "evidence": _evidence_rows(outcomes),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return rows
