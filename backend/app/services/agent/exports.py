"""Exports of saved CiteAlpha Analyst runs: Excel, PowerPoint, PDF memo, Markdown.

Every sourced cell, bullet and memo line carries its citation numbers; every file
ends with the run's Evidence Receipt, copied unchanged from the saved run. Quotes
are the stored spans only (never whole documents) while IR / transcript
redistribution rights are unreviewed (R3-35).
"""

from __future__ import annotations

import io
import re
import textwrap
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

MAX_QUOTE = 400
# Bump on any change to fixed export copy or layout; docs/compliance/ANALYST_SKILLS_SIGNOFF.md must be re-signed.
LAYOUT_VERSION = "1.1"

FORMATS: Dict[str, Tuple[str, str]] = {
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
    "pdf": ("application/pdf", "pdf"),
    "md": ("text/markdown; charset=utf-8", "md"),
}

_REF = re.compile(r"\[(\d+)\]")
_SLUG = re.compile(r"[^a-z0-9]+")
_SHEET_BAD = re.compile(r"[\[\]:*?/\\]")


def filename(run: Dict[str, Any], fmt: str) -> str:
    parts = ["citealpha", run["skill"]["id"], run.get("company_id") or "", run.get("as_of") or ""]
    slug = "-".join(p for p in (_SLUG.sub("-", str(x).lower()).strip("-") for x in parts) if p)
    return f"{slug}.{FORMATS[fmt][1]}"


def link_for(cite: Dict[str, Any], base_url: str) -> Optional[str]:
    """CiteAlpha citation page if there is one, else the public source; uploads have none."""
    if cite.get("permalink"):
        return base_url.rstrip("/") + cite["permalink"]
    url = str(cite.get("source_url") or "")
    if url.startswith("/") and not url.startswith("//"):
        return base_url.rstrip("/") + url
    return url if url.startswith(("http://", "https://")) else None


def _quote(cite: Dict[str, Any]) -> str:
    q = " ".join(str(cite.get("quote") or "").split())
    return q if len(q) <= MAX_QUOTE else q[: MAX_QUOTE - 1] + "…"


def _refs(cites: Iterable[int]) -> str:
    return "".join(f"[{n}]" for n in cites)


def _headline(run: Dict[str, Any]) -> Tuple[str, List[int]]:
    h = run.get("headline") or ""
    return _REF.sub("", h).strip(), [int(n) for n in _REF.findall(h)]


def _note(cites: Iterable[int], by_n: Dict[int, Dict[str, Any]], base_url: str) -> str:
    parts = []
    for n in cites:
        c = by_n.get(n)
        if not c:
            continue
        where = link_for(c, base_url) or ("your upload (no public link)" if c.get("kind") == "upload" else "no link")
        parts.append(f"[{n}] {c.get('title') or 'Source'}, {c.get('date') or 'undated'}\n“{_quote(c)}”\n{where}")
    return "\n\n".join(parts)[:4000]


def _header_lines(run: Dict[str, Any]) -> List[str]:
    lines = [
        f"Data as of {run.get('as_of')}. {run.get('disclaimer') or ''}".strip(),
        f"Run {run['run_id']} · {run['skill']['id']} v{run['skill'].get('version')} · generated {run.get('generated_at')}",
    ]
    if run.get("project"):
        lines.append(f"Project: {run['project']['name']}")
    if run.get("trigger"):
        t = run["trigger"]
        lines.append(f"Triggered by: {t.get('title') or 'new filing'} ({t.get('date') or 'undated'})")
    if run.get("includes_unreviewed"):
        lines.append("Includes unreviewed commitments.")
    return lines


def _receipt_fields(run: Dict[str, Any]) -> List[Tuple[str, Any]]:
    r = run.get("evidence_receipt") or {}
    return [
        ("Run", r.get("run_id")),
        ("Skill", f"{r.get('skill_id')} v{r.get('skill_version')}"),
        ("Engine", r.get("engine")),
        ("Model", r.get("model") or "none (no model-written text)"),
        ("Generated", r.get("generated_at")),
        ("Project", r.get("project_id") or "—"),
        ("Trigger document", r.get("trigger_doc_id") or "—"),
        ("Sources", len(r.get("sources") or [])),
        ("Tool calls", len(r.get("tool_calls") or [])),
        ("Statements removed by the verifier", (run.get("verifier") or {}).get("removed", 0)),
    ]


# ── Excel ────────────────────────────────────────────────────────────────────


def _put(ws, row: int, col: int, value: Any):
    cell = ws.cell(row=row, column=col, value=value)
    if isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"  # never let an uploaded quote become a formula
    return cell


def _sheet_title(wb, title: str) -> str:
    base = _SHEET_BAD.sub(" ", title).strip()
    if len(base) > 28:
        base = base[:28].rsplit(" ", 1)[0]
    base = base or "Table"
    name, i = base, 2
    while name in wb.sheetnames:
        name = f"{base[:25]} {i}"
        i += 1
    return name


def _house_lines(style: Optional[Dict[str, Any]]) -> List[str]:
    st = style or {}
    return [x for x in (st.get("firm_name") and f"Prepared for {st['firm_name']}", st.get("classification"), st.get("footer")) if x]


def to_xlsx(run: Dict[str, Any], base_url: str, style: Optional[Dict[str, Any]] = None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill

    st = style or {}
    by_n = {c["n"]: c for c in run.get("citations") or []}
    fname = st.get("font") or "Calibri"
    wrap = Alignment(wrap_text=True, vertical="top")
    if st.get("primary_color"):
        bold = Font(bold=True, name=fname, color="FFFFFF")
        fill = PatternFill("solid", fgColor=st["primary_color"].lstrip("#").upper())
    else:
        bold, fill = Font(bold=True, name=fname), None

    def annotate(cell, cites: List[int]) -> None:
        if not cites:
            return
        note = Comment(_note(cites, by_n, base_url), "CiteAlpha")
        note.width, note.height = 420, 220
        cell.comment = note
        link = next((link_for(by_n[n], base_url) for n in cites if n in by_n and link_for(by_n[n], base_url)), None)
        if link:
            cell.hyperlink = link

    def header(ws, r: int, names: List[str]) -> None:
        for i, h in enumerate(names, start=1):
            cell = _put(ws, r, i, h)
            cell.font = bold
            if fill:
                cell.fill = fill

    wb = Workbook()
    ws = wb.active
    ws.title = "Brief"
    _put(ws, 1, 1, f"{run['skill']['title']}: {run['company_name']}").font = Font(bold=True, size=14, name=fname)
    r = 2
    for line in _house_lines(style) + _header_lines(run):
        _put(ws, r, 1, line)
        r += 1
    r += 1
    header(ws, r, ["Section", "Statement", "Sources"])
    text, cites = _headline(run)
    if text:
        r += 1
        _put(ws, r, 1, "Headline")
        annotate(_put(ws, r, 2, text), cites)
        _put(ws, r, 3, _refs(cites))
    for s in run.get("sections") or []:
        for c in s["claims"]:
            r += 1
            _put(ws, r, 1, s["title"])
            annotate(_put(ws, r, 2, c["text"]), c["cites"])
            _put(ws, r, 3, _refs(c["cites"]))
    for m in run.get("not_found") or []:
        r += 1
        _put(ws, r, 1, "What we could not find")
        _put(ws, r, 2, m)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 100
    ws.column_dimensions["C"].width = 14
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap

    for s in run.get("sections") or []:
        rows = [c for c in s["claims"] if c.get("row")]
        if not rows:
            continue
        cols: List[str] = []
        for c in rows:
            cols += [k for k in c["row"] if k not in cols]
        t = wb.create_sheet(_sheet_title(wb, s["title"]))
        header(t, 1, cols + ["Sources"])
        for i, c in enumerate(rows, start=2):
            for j, k in enumerate(cols, start=1):
                annotate(_put(t, i, j, c["row"].get(k, "")), c["cites"])
            _put(t, i, len(cols) + 1, _refs(c["cites"]))
        for j in range(1, len(cols) + 2):
            t.column_dimensions[t.cell(row=1, column=j).column_letter].width = 22

    src = wb.create_sheet("Sources")
    header(src, 1, ["#", "Kind", "Title", "Date", "Period", "Quote (span)", "Source", "CiteAlpha citation"])
    for i, c in enumerate(run.get("citations") or [], start=2):
        for j, v in enumerate([c["n"], c.get("kind"), c.get("title"), c.get("date"), c.get("period"), _quote(c)], start=1):
            _put(src, i, j, v)
        url = str(c.get("source_url") or "")
        if url.startswith("/") and not url.startswith("//"):
            url = base_url.rstrip("/") + url
        cell = _put(src, i, 7, url if url.startswith("http") else ("your upload" if c.get("kind") == "upload" else url))
        if url.startswith("http"):
            cell.hyperlink = url
        if c.get("permalink"):
            _put(src, i, 8, base_url.rstrip("/") + c["permalink"]).hyperlink = base_url.rstrip("/") + c["permalink"]
    for col, w in zip("ABCDEFGH", (5, 12, 50, 12, 12, 80, 50, 50)):
        src.column_dimensions[col].width = w

    rc = wb.create_sheet("Evidence receipt")
    r = 1
    for k, v in _receipt_fields(run):
        _put(rc, r, 1, k).font = bold
        _put(rc, r, 2, v)
        r += 1
    r += 1
    header(rc, r, ["#", "Kind", "Title", "Date", "Source", "Document id", "Quote SHA-256"])
    for s in (run.get("evidence_receipt") or {}).get("sources") or []:
        r += 1
        for j, v in enumerate([s.get("n"), s.get("kind"), s.get("title"), s.get("date"), s.get("source_url"),
                               s.get("doc_id"), s.get("quote_sha256")], start=1):
            _put(rc, r, j, v)
    r += 2
    header(rc, r, ["Tool", "Company", "Arguments", "Evidence items"])
    for call in (run.get("evidence_receipt") or {}).get("tool_calls") or []:
        r += 1
        args = ", ".join(f"{k}={v}" for k, v in sorted((call.get("args") or {}).items()) if k != "org_id")
        for j, v in enumerate([call.get("tool"), call.get("company_id"), args, call.get("evidence")], start=1):
            _put(rc, r, j, v)
    for col, w in zip("ABCDEFG", (34, 14, 50, 12, 50, 30, 66)):
        rc.column_dimensions[col].width = w

    house = " · ".join(_house_lines(style))
    if house:
        for sheet in wb.worksheets:
            sheet.oddFooter.center.text = house[:240]
            sheet.oddHeader.right.text = (st.get("classification") or "")[:120]

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── PowerPoint ───────────────────────────────────────────────────────────────

_PER_SLIDE = 6
_SOURCES_PER_SLIDE = 6


def _chunks(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def _rgb(hex_color: str):
    from pptx.dml.color import RGBColor

    return RGBColor.from_string(hex_color.lstrip("#").upper())


def _drop_slides(prs) -> None:
    ids = prs.slides._sldIdLst
    for sld in list(ids):
        prs.part.drop_rel(sld.rId)
        ids.remove(sld)


def _layout(prs):
    by_name = {l.name.lower(): l for l in prs.slide_layouts}
    for name in ("title only", "blank"):
        if name in by_name:
            return by_name[name]
    return prs.slide_layouts[len(prs.slide_layouts) - 1]


def to_pptx(run: Dict[str, Any], base_url: str, style: Optional[Dict[str, Any]] = None) -> bytes:
    from pptx import Presentation
    from pptx.util import Emu, Pt

    st = style or {}
    by_n = {c["n"]: c for c in run.get("citations") or []}
    font = st.get("font") or "Arial"
    primary = st.get("primary_color")
    accent = st.get("accent_color")
    if st.get("template"):
        prs = Presentation(io.BytesIO(st["template"]))
        _drop_slides(prs)
    else:
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    W, H = prs.slide_width, prs.slide_height
    layout = _layout(prs)
    left, width = int(W * 0.045), int(W * 0.91)

    def box(s, top: float, height: float):
        tf = s.shapes.add_textbox(left, int(H * top), width, int(H * height)).text_frame
        tf.word_wrap = True
        return tf

    def chrome(s) -> None:
        if accent and not st.get("template"):
            bar = s.shapes.add_shape(1, left, int(H * 0.155), int(W * 0.12), int(H * 0.008))
            bar.fill.solid()
            bar.fill.fore_color.rgb = _rgb(accent)
            bar.line.fill.background()
        if st.get("logo"):
            try:
                s.shapes.add_picture(io.BytesIO(st["logo"]), int(W * 0.85), int(H * 0.035), height=int(H * 0.08))
            except Exception:
                pass
        bits = [b for b in (st.get("firm_name"), st.get("footer"), st.get("classification")) if b]
        if bits:
            tf = box(s, 0.955, 0.04)
            tf.text = "  ·  ".join(bits)
            tf.paragraphs[0].runs[0].font.size = Pt(8)

    def new_slide(title: str):
        s = prs.slides.add_slide(layout)
        if s.shapes.title is not None:
            s.shapes.title.text = title
            tf = s.shapes.title.text_frame
        else:
            tf = box(s, 0.045, 0.11)
            tf.text = title
            tf.paragraphs[0].runs[0].font.size = Pt(26)
            tf.paragraphs[0].runs[0].font.bold = True
        for p in tf.paragraphs:
            for r_ in p.runs:
                if primary:
                    r_.font.color.rgb = _rgb(primary)
        title_id = s.shapes.title.shape_id if s.shapes.title is not None else None
        for ph in list(s.placeholders):
            if ph.shape_id != title_id:
                ph._element.getparent().remove(ph._element)
        chrome(s)
        return s

    def body(s, lines: List[Tuple[str, int]], size: int = 16):
        tf = box(s, 0.18, 0.68)
        for i, (text, pt) in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = text
            p.space_after = Pt(6)
            for run_ in p.runs:
                run_.font.size = Pt(pt or size)

    def footer(s, cites: List[int]):
        cites = [n for n in dict.fromkeys(cites) if n in by_n]
        if not cites:
            return
        tf = box(s, 0.87, 0.085)
        p = tf.paragraphs[0]
        lead = p.add_run()
        lead.text = "Sources: "
        lead.font.size = Pt(9)
        lead.font.bold = True
        for i, n in enumerate(cites[:8]):
            c = by_n[n]
            r_ = p.add_run()
            r_.text = f"{'' if i == 0 else ' · '}[{n}] {str(c.get('title') or 'Source')[:70]}, {c.get('date') or 'undated'}"
            r_.font.size = Pt(9)
            link = link_for(c, base_url)
            if link:
                r_.hyperlink.address = link
        if len(cites) > 8:
            more = p.add_run()
            more.text = f" · +{len(cites) - 8} more on the Sources slides"
            more.font.size = Pt(9)

    s = new_slide(f"{run['skill']['title']}: {run['company_name']}")
    text, cites = _headline(run)
    lines = [(f"{text} {_refs(cites)}", 20)] if text else []
    prepared = [(f"Prepared for {st['firm_name']}", 14)] if st.get("firm_name") else []
    body(s, lines + prepared + [(l, 14) for l in _header_lines(run)])
    footer(s, cites)

    for sec in run.get("sections") or []:
        if not sec["claims"]:
            continue
        for i, part in enumerate(_chunks(sec["claims"], _PER_SLIDE)):
            s = new_slide(sec["title"] + (" (continued)" if i else ""))
            body(s, [(f"• {c['text']} {_refs(c['cites'])}", 15) for c in part])
            footer(s, [n for c in part for n in c["cites"]])

    if run.get("not_found"):
        for i, part in enumerate(_chunks(run["not_found"], 10)):
            s = new_slide("What we could not find" + (" (continued)" if i else ""))
            body(s, [(f"• {m}", 14) for m in part])

    for i, part in enumerate(_chunks(run.get("citations") or [], _SOURCES_PER_SLIDE)):
        if not part:
            break
        s = new_slide("Sources" + (" (continued)" if i else ""))
        lines = []
        for c in part:
            lines.append((f"[{c['n']}] {c.get('title') or 'Source'} — {c.get('date') or 'undated'}", 12))
            q = _quote(c)
            lines.append((f"“{q[:220]}{'…' if len(q) > 220 else ''}”  {link_for(c, base_url) or 'your upload'}", 10))
        body(s, lines)

    receipt = (run.get("evidence_receipt") or {}).get("sources") or []
    s = new_slide("Evidence receipt")
    body(s, [(f"{k}: {v}", 14) for k, v in _receipt_fields(run)]
         + [("Each source's quote hash (SHA-256) is listed on the following slides and in the Excel export.", 12)])
    for i, part in enumerate(_chunks(receipt, 14)):
        if not part:
            break
        s = new_slide("Evidence receipt — quote hashes" + (" (continued)" if i else ""))
        body(s, [(f"[{x.get('n')}] {x.get('quote_sha256')}  {str(x.get('title') or '')[:60]}", 10) for x in part])

    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    for run_ in p.runs:
                        run_.font.name = font

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ── PDF memo and Markdown ────────────────────────────────────────────────────

_ASCII = {
    "“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "…": "...",
    "₹": "Rs ", "·": "-", "•": "-", "×": "x", "≥": ">=", "≤": "<=", "\u00a0": " ",
}


def _ascii(text: str) -> str:
    for k, v in _ASCII.items():
        text = text.replace(k, v)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def memo_lines(run: Dict[str, Any], base_url: str, style: Optional[Dict[str, Any]] = None) -> List[str]:
    house = _house_lines(style)
    lines = [f"{run['skill']['title']}: {run['company_name']}", ""] + house + _header_lines(run) + [""]
    text, cites = _headline(run)
    if text:
        lines += [f"{text} {_refs(cites)}", ""]
    for s in run.get("sections") or []:
        if not s["claims"]:
            continue
        lines += [s["title"].upper()] + [f"- {c['text']} {_refs(c['cites'])}" for c in s["claims"]] + [""]
    if run.get("not_found"):
        lines += ["WHAT WE COULD NOT FIND"] + [f"- {m}" for m in run["not_found"]] + [""]
    lines.append("SOURCES")
    for c in run.get("citations") or []:
        lines.append(f"[{c['n']}] {c.get('title') or 'Source'} - {c.get('date') or 'undated'}")
        lines.append(f'    "{_quote(c)}"')
        lines.append(f"    {link_for(c, base_url) or 'your upload'}")
    lines += ["", "EVIDENCE RECEIPT"] + [f"{k}: {v}" for k, v in _receipt_fields(run)]
    for x in (run.get("evidence_receipt") or {}).get("sources") or []:
        lines.append(f"[{x.get('n')}] sha256 {x.get('quote_sha256')}")
    if house:
        lines += [""] + house
    return lines


def to_pdf(run: Dict[str, Any], base_url: str, style: Optional[Dict[str, Any]] = None) -> bytes:
    from app.services.pdf_minimal import text_to_pdf

    wrapped: List[str] = []
    for line in memo_lines(run, base_url, style):
        line = _ascii(line)
        indent = " " * (len(line) - len(line.lstrip()))
        wrapped += textwrap.wrap(line, width=95, subsequent_indent=indent or "  ", break_long_words=True) or [""]
    firm = (style or {}).get("firm_name") or "CiteAlpha"
    return text_to_pdf(wrapped, title=_ascii(f"{firm} {run['skill']['title']}: {run['company_name']}"))


def to_markdown(run: Dict[str, Any], base_url: str, style: Optional[Dict[str, Any]] = None) -> bytes:
    house = _house_lines(style)
    md = ("> " + " · ".join(house) + "\n\n" if house else "") + (run.get("markdown") or "")
    md += "\n\n## Evidence receipt\n" + "\n".join(f"- {k}: {v}" for k, v in _receipt_fields(run))
    md += "\n" + "\n".join(
        f"- [{x.get('n')}] sha256 `{x.get('quote_sha256')}`"
        for x in (run.get("evidence_receipt") or {}).get("sources") or []
    )
    return md.encode("utf-8")


_RENDER = {"xlsx": to_xlsx, "pptx": to_pptx, "pdf": to_pdf, "md": to_markdown}


def render(run: Dict[str, Any], fmt: str, base_url: str, style: Optional[Dict[str, Any]] = None) -> bytes:
    return _RENDER[fmt](run, base_url, style)
