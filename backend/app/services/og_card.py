"""OG share cards for company dossiers (plan W5.3). SVG + PNG."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

from fastapi import HTTPException
from fastapi.responses import Response

from app.services import repository
from app.services.seo_public import dossier_title, format_as_of, record_sentence
from app.data.seed import get_outcomes
from app.services.guidance_flags import score_meta
from app.services.score_policy import is_scoreable

_TIER = {"provisional": "Provisional", "established": "Established", "deep": "Deep"}
_FONTS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
)


def _row(company_id: str):
    return repository.get_company_gci(company_id)


def _payload(company_id: str) -> dict:
    d = _row(company_id)
    outcomes = get_outcomes(d.id)
    meta = score_meta(outcomes, scoreable=is_scoreable(d.data_quality), company_id=d.id)
    gci = d.gci_score if d.gci_score is not None else meta.get("gci_score")
    as_of = d.as_of or meta.get("as_of")
    sentence = record_sentence(outcomes)
    score = "—" if gci is None else f"{gci:.1f}".rstrip("0").rstrip(".")
    return {
        "id": d.id,
        "name": d.name,
        "ticker": d.ticker,
        "gci": gci,
        "score": score,
        "tier": _TIER.get(d.confidence_tier or "", ""),
        "as_of": format_as_of(as_of),
        "sentence": sentence,
        "title": dossier_title(d.name, gci, as_of, d.confidence_tier),
        "data_quality": d.data_quality,
    }


def svg_bytes(company_id: str) -> bytes:
    p = _payload(company_id)
    name = xml_escape(p["name"])
    ticker = xml_escape(p["ticker"])
    score = xml_escape(p["score"])
    meta_bits = [b for b in (p["tier"], p["as_of"] and f"Data as of {p['as_of']}") if b]
    meta = xml_escape(" · ".join(meta_bits)) if meta_bits else "Hand-labeled evidence"
    sentence = xml_escape(p["sentence"][:180])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#0e1a16"/>
  <rect x="0" y="0" width="16" height="630" fill="#0b6b5f"/>
  <text x="64" y="88" fill="#9aa3ad" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="22">CiteAlpha · Guidance Credibility Index</text>
  <text x="64" y="170" fill="#f4f1ea" font-family="ui-serif, Georgia, serif" font-size="48" font-weight="600">{name}</text>
  <text x="64" y="230" fill="#c5cdc8" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="24">{ticker}</text>
  <text x="64" y="360" fill="#f4f1ea" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="96" font-weight="700">{score}</text>
  <text x="64" y="420" fill="#d4e8e4" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="22">{meta}</text>
  <text x="64" y="490" fill="#c5cdc8" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="22">{sentence}</text>
  <text x="64" y="580" fill="#9aa3ad" font-family="ui-sans-serif, Helvetica, Arial, sans-serif" font-size="18">Not investment advice. Factual guidance vs delivery.</text>
</svg>"""
    return svg.encode("utf-8")


def svg_response(company_id: str) -> Response:
    return Response(content=svg_bytes(company_id), media_type="image/svg+xml")


def _font(size: int, bold: bool = False):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    names = ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf") if bold else ("DejaVuSans.ttf",)
    for base in _FONTS:
        if base.exists():
            try:
                return ImageFont.truetype(str(base), size)
            except OSError:
                continue
        parent = base.parent
        for n in names:
            cand = parent / n
            if cand.exists():
                try:
                    return ImageFont.truetype(str(cand), size)
                except OSError:
                    continue
    try:
        from PIL import ImageFont

        return ImageFont.load_default()
    except Exception:
        return None


def png_bytes(company_id: str) -> bytes:
    p = _payload(company_id)
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="PNG renderer unavailable") from exc
    img = Image.new("RGB", (1200, 630), (14, 26, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 16, 630), fill=(11, 107, 95))
    title_f = _font(44, bold=True)
    score_f = _font(96, bold=True)
    body_f = _font(22)
    small_f = _font(18)
    draw.text((64, 56), "CiteAlpha · Guidance Credibility Index", fill=(154, 163, 173), font=small_f)
    draw.text((64, 120), p["name"][:42], fill=(244, 241, 234), font=title_f)
    draw.text((64, 190), p["ticker"], fill=(197, 205, 200), font=body_f)
    draw.text((64, 280), p["score"], fill=(244, 241, 234), font=score_f)
    meta_bits = [b for b in (p["tier"], p["as_of"] and f"Data as of {p['as_of']}") if b]
    draw.text((64, 400), " · ".join(meta_bits) or "Hand-labeled evidence", fill=(212, 232, 228), font=body_f)
    draw.text((64, 460), p["sentence"][:90], fill=(197, 205, 200), font=body_f)
    draw.text((64, 560), "Not investment advice. Factual guidance vs delivery.", fill=(154, 163, 173), font=small_f)
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def png_response(company_id: str) -> Response:
    return Response(content=png_bytes(company_id), media_type="image/png")
