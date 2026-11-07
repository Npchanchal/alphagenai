"""Public SEO payloads for hand-labeled GCI dossiers (plan W5.1–W5.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data.metric_catalog import display_name_for
from app.data.seed import get_outcomes, list_companies
from app.services.gci_scoring import OutcomeLabel, classify_outcome
from app.services.guidance_flags import score_meta
from app.services.score_policy import is_scoreable

CLOSED = {OutcomeLabel.MET.value, OutcomeLabel.EXCEEDED.value, OutcomeLabel.MISSED.value}


def format_as_of(iso: Optional[str]) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)[:10]
    return d.strftime("%d %b %Y").lstrip("0")


def record_sentence(outcomes) -> str:
    return _sentence([(o, classify_outcome(o).value) for o in outcomes if o.actual_value is not None])


def record_sentence_from_views(views) -> str:
    """Same sentence from dossier ``OutcomeView`` rows, whose ``label`` already excludes uncited rows."""
    return _sentence([(o, o.label) for o in views if o.actual_value is not None])


def _sentence(labelled) -> str:
    closed_rows = [(o, lab) for o, lab in labelled if lab in CLOSED]
    revenue = [r for r in closed_rows if "revenue" in (r[0].metric or "")]
    focus = revenue or closed_rows
    if not focus:
        return "No closed, dual-cited results yet."
    missed = sorted({r[0].period for r in focus if r[1] == OutcomeLabel.MISSED.value})
    met_or_beat = sum(1 for r in focus if r[1] in (OutcomeLabel.MET.value, OutcomeLabel.EXCEEDED.value))
    metric_label = display_name_for(focus[0][0].metric)
    missed_clause = f"; missed {', '.join(missed)}" if missed else ""
    return (
        f"Met or beat {metric_label} guidance in {met_or_beat} of {len(focus)} "
        f"closed years{missed_clause}."
    )


def dossier_title(name: str, gci: Optional[float], as_of: Optional[str]) -> str:
    as_of_s = format_as_of(as_of)
    if gci is None:
        base = f"{name} — Guidance Credibility Index (GCI)"
        return f"{base} · Data as of {as_of_s}" if as_of_s else base
    shown = f"{gci:.1f}".rstrip("0").rstrip(".")
    base = f"{name} — Guidance Credibility Index (GCI) {shown}"
    return f"{base} · Data as of {as_of_s}" if as_of_s else base


def dossier_description(sentence: str, as_of: Optional[str]) -> str:
    as_of_s = format_as_of(as_of)
    bits = [sentence]
    if as_of_s:
        bits.append(f"Data as of {as_of_s}.")
    bits.append("Not investment advice.")
    return " ".join(bits)


def list_indexable_dossiers() -> List[Dict[str, Any]]:
    """Hand-labeled companies only — these are the indexable public dossiers."""
    rows: List[Dict[str, Any]] = []
    for c in list_companies():
        quality = c.get("data_quality") or ""
        if quality != "hand_labeled":
            continue
        outcomes = get_outcomes(c["id"])
        meta = score_meta(outcomes, scoreable=is_scoreable(quality), company_id=c["id"])
        sentence = record_sentence(outcomes)
        as_of = meta.get("as_of")
        gci = meta.get("gci_score")
        rows.append(
            {
                "id": c["id"],
                "name": c["name"],
                "ticker": c["ticker"],
                "gci_score": gci,
                "confidence_tier": meta.get("confidence_tier"),
                "as_of": as_of,
                "data_quality": quality,
                "record_sentence": sentence,
                "title": dossier_title(c["name"], gci, as_of),
                "description": dossier_description(sentence, as_of),
                "path": f"/companies/{c['id']}",
            }
        )
    rows.sort(key=lambda r: r["id"])
    return rows
