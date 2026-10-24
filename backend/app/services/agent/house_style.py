"""A desk's own house style for CiteAlpha Analyst exports.

Per organisation: firm name, primary and accent colours, font, footer line,
classification label (e.g. "Internal — not for distribution"), an optional logo
(PNG/JPEG, 500 KB) and an optional PowerPoint template (.pptx/.potx, 5 MB) whose
slide master and layouts the deck is built on. Citations, source footers and the
Evidence Receipt are always kept; a house style changes presentation only.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import threading
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

MAX_LOGO_BYTES = 500 * 1024
MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
MAX_UNZIPPED = 60 * 1024 * 1024
FONTS = ("Arial", "Calibri", "Georgia", "Helvetica", "Times New Roman", "Verdana")
DEFAULTS = {"firm_name": "", "primary_color": "#0B3D5C", "accent_color": "#C8102E", "font": "Arial",
            "footer": "", "classification": ""}
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PACKAGED = Path(__file__).resolve().parents[2] / "data"
_LOCK = threading.Lock()


class StyleError(ValueError):
    pass


def _root() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) if env else _PACKAGED


def _store() -> Path:
    return _root() / "analyst_house_style.json"


def _asset(org_id: str, ext: str) -> Path:
    return _root() / "analyst_house_style" / f"{hashlib.sha256(org_id.encode()).hexdigest()[:16]}.{ext}"


def _load() -> Dict[str, Any]:
    p = _store()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"orgs": {}}


def _save(data: Dict[str, Any]) -> None:
    p = _store()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def describe(org_id: str) -> Dict[str, Any]:
    s = {**DEFAULTS, **(_load()["orgs"].get(org_id) or {})}
    return {**{k: s.get(k) for k in DEFAULTS}, "has_logo": _asset(org_id, "img").exists(),
            "has_template": _asset(org_id, "pptx").exists(), "configured": org_id in _load()["orgs"]}


def get_style(org_id: str) -> Optional[Dict[str, Any]]:
    """Style for exports, or None when the org has not set one (CiteAlpha default layout)."""
    if org_id not in _load()["orgs"]:
        return None
    s = {**DEFAULTS, **_load()["orgs"][org_id]}
    logo, tpl = _asset(org_id, "img"), _asset(org_id, "pptx")
    s["logo"] = logo.read_bytes() if logo.exists() else None
    s["template"] = tpl.read_bytes() if tpl.exists() else None
    return s


def _check_logo(raw: bytes) -> None:
    if len(raw) > MAX_LOGO_BYTES:
        raise StyleError("Logo must be 500 KB or smaller")
    if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
        raise StyleError("Logo must be a PNG or JPEG image")


def set_style(org_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
    clean = {k: str(values.get(k) if values.get(k) is not None else DEFAULTS[k]).strip() for k in DEFAULTS}
    for k in ("primary_color", "accent_color"):
        if not _HEX.match(clean[k]):
            raise StyleError(f"{k} must be a #RRGGBB colour")
    if clean["font"] not in FONTS:
        raise StyleError(f"font must be one of {', '.join(FONTS)}")
    logo_b64 = values.get("logo_base64")
    logo = None
    if logo_b64:
        try:
            logo = base64.b64decode(logo_b64, validate=True)
        except Exception:
            raise StyleError("Logo is not valid base64")
        _check_logo(logo)
    with _LOCK:
        data = _load()
        data["orgs"][org_id] = clean
        _save(data)
        if logo:
            _write(_asset(org_id, "img"), logo)
    return describe(org_id)


def check_template(raw: bytes) -> None:
    if len(raw) > MAX_TEMPLATE_BYTES:
        raise StyleError("Template must be 5 MB or smaller")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
                raise StyleError("Template expands too large")
            for info in z.infolist():
                if info.filename.endswith((".xml", ".rels")):
                    head = z.read(info)[:4096].upper()
                    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
                        raise StyleError("Template contains a DOCTYPE declaration")
            if "ppt/presentation.xml" not in z.namelist():
                raise StyleError("Not a PowerPoint file (.pptx or .potx)")
    except zipfile.BadZipFile:
        raise StyleError("Not a PowerPoint file (.pptx or .potx)")
    from pptx import Presentation

    try:
        Presentation(io.BytesIO(_as_pptx(raw)))
    except Exception:
        raise StyleError("PowerPoint could not open this template")


def _as_pptx(raw: bytes) -> bytes:
    """A .potx differs from a .pptx only in its main content type; rewrite it so python-pptx opens it."""
    src = zipfile.ZipFile(io.BytesIO(raw))
    ct = src.read("[Content_Types].xml")
    if b"presentationml.template.main+xml" not in ct:
        return raw
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "[Content_Types].xml":
                data = data.replace(b"presentationml.template.main+xml", b"presentationml.presentation.main+xml")
            dst.writestr(info, data)
    return out.getvalue()


def set_template(org_id: str, raw: bytes) -> Dict[str, Any]:
    check_template(raw)
    with _LOCK:
        data = _load()
        data["orgs"].setdefault(org_id, dict(DEFAULTS))
        _save(data)
        _write(_asset(org_id, "pptx"), _as_pptx(raw))
    return describe(org_id)


def clear_asset(org_id: str, what: str) -> Dict[str, Any]:
    p = _asset(org_id, "pptx" if what == "template" else "img")
    if p.exists():
        p.unlink()
    return describe(org_id)


def reset(org_id: str) -> None:
    with _LOCK:
        data = _load()
        data["orgs"].pop(org_id, None)
        _save(data)
    for ext in ("img", "pptx"):
        p = _asset(org_id, ext)
        if p.exists():
            p.unlink()
