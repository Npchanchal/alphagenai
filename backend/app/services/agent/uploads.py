"""Org-scoped user uploads for CiteAlpha Analyst Projects.

Files (PDF, DOCX, XLSX, TXT, CSV, Markdown) are parsed into passages, each with
a location a reader can find again (``p.3``, ``para 12``, ``Model!B14``). Passages
are stored per organisation and Project and are only ever read back with the same
``org_id`` + ``project_id``; nothing from an upload enters the shared document
store, the GCI or another organisation's runs.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

MAX_BYTES = 10 * 1024 * 1024
MAX_UPLOADS_PER_PROJECT = 20
MAX_PASSAGES = 5000
MAX_ZIP_MEMBER = 50 * 1024 * 1024
KINDS = {"pdf", "docx", "xlsx", "txt", "csv", "md"}

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_uploads"
_LOCK = threading.Lock()
_SENT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(r"[a-z0-9]{3,}")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class UploadError(ValueError):
    pass


def _root() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_uploads" if env else _PACKAGED


def _org_dir(org_id: str) -> Path:
    return _root() / hashlib.sha256(org_id.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Parsing ──────────────────────────────────────────────────────────────────


def kind_for(filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in KINDS:
        raise UploadError(f"Unsupported file type .{ext or '?'} — use PDF, DOCX, XLSX, TXT, CSV or MD")
    return ext


def _xml(zf: zipfile.ZipFile, name: str) -> Optional[ET.Element]:
    try:
        info = zf.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_ZIP_MEMBER:
        raise UploadError("File is too large once unpacked")
    raw = zf.read(name)
    if b"<!DOCTYPE" in raw[:2048] or b"<!ENTITY" in raw[:4096]:
        raise UploadError("File contains XML entity declarations and was rejected")
    return ET.fromstring(raw)


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENT.split(" ".join(text.split())) if len(s.strip()) >= 3]


def _parse_pdf(data: bytes) -> List[Tuple[str, str]]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        out = []
        for i, page in enumerate(reader.pages, start=1):
            for s in _sentences(page.extract_text() or ""):
                out.append((f"p.{i}", s))
        return out
    except Exception as exc:
        raise UploadError(f"Could not read PDF ({type(exc).__name__})")


def _parse_docx(data: bytes) -> List[Tuple[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        doc = _xml(zf, "word/document.xml")
    if doc is None:
        raise UploadError("Not a Word document (word/document.xml missing)")
    out = []
    for n, p in enumerate(doc.iter(f"{_W}p"), start=1):
        text = "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()
        if text:
            out.append((f"para {n}", text))
    return out


def _col_letters(ref: str) -> str:
    return re.match(r"[A-Z]+", ref).group(0) if re.match(r"[A-Z]+", ref) else ""


def _parse_xlsx(data: bytes) -> List[Tuple[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        wb = _xml(zf, "xl/workbook.xml")
        if wb is None:
            raise UploadError("Not an Excel workbook (xl/workbook.xml missing)")
        rels = _xml(zf, "xl/_rels/workbook.xml.rels")
        target = {r.get("Id"): r.get("Target") for r in (rels.iter(f"{_PR}Relationship") if rels is not None else [])}
        shared: List[str] = []
        ss = _xml(zf, "xl/sharedStrings.xml")
        if ss is not None:
            for si in ss.iter(f"{_S}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_S}t")))
        out: List[Tuple[str, str]] = []
        for sheet in wb.iter(f"{_S}sheet"):
            name = sheet.get("name") or "Sheet"
            tgt = target.get(sheet.get(f"{_R}id") or "", "")
            path = "xl/" + tgt.lstrip("/").removeprefix("xl/") if tgt else ""
            ws = _xml(zf, path) if path else None
            if ws is None:
                continue
            for row in ws.iter(f"{_S}row"):
                cells = []
                first_ref = None
                for c in row.iter(f"{_S}c"):
                    ref = c.get("r") or ""
                    t = c.get("t")
                    if t == "s":
                        v = c.find(f"{_S}v")
                        val = shared[int(v.text)] if v is not None and v.text and v.text.isdigit() and int(v.text) < len(shared) else ""
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(f"{_S}t"))
                    else:
                        v = c.find(f"{_S}v")
                        val = v.text if v is not None and v.text else ""
                    val = str(val).strip()
                    if val:
                        first_ref = first_ref or ref
                        cells.append(val)
                if cells and first_ref:
                    out.append((f"{name}!{first_ref}", " | ".join(cells)))
        return out


def _parse_text(data: bytes, kind: str) -> List[Tuple[str, str]]:
    text = data.decode("utf-8", errors="replace")
    out = []
    if kind == "csv":
        for n, line in enumerate(text.splitlines(), start=1):
            if line.strip():
                out.append((f"line {n}", " | ".join(x.strip() for x in line.split(",") if x.strip())))
        return out
    for n, block in enumerate(re.split(r"\n\s*\n", text), start=1):
        for s in _sentences(block):
            out.append((f"para {n}", s))
    return out


def parse(filename: str, data: bytes) -> List[Dict[str, str]]:
    kind = kind_for(filename)
    if len(data) > MAX_BYTES:
        raise UploadError(f"File is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        if kind == "pdf":
            rows = _parse_pdf(data)
        elif kind == "docx":
            rows = _parse_docx(data)
        elif kind == "xlsx":
            rows = _parse_xlsx(data)
        else:
            rows = _parse_text(data, kind)
    except zipfile.BadZipFile:
        raise UploadError(f"Not a valid .{kind} file")
    passages = [{"loc": loc, "text": text[:600]} for loc, text in rows if text.strip()][:MAX_PASSAGES]
    if not passages:
        raise UploadError("No readable text found in the file")
    return passages


# ── Store ────────────────────────────────────────────────────────────────────


def _index_path() -> Path:
    return _root() / "index.json"


def _load_index() -> Dict[str, Any]:
    p = _index_path()
    if not p.exists():
        return {"uploads": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_json(p: Path, data: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _public(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: row[k] for k in ("upload_id", "project_id", "filename", "kind", "bytes", "sha256",
                                "passages", "uploaded_by", "uploaded_at") if k in row}


def list_uploads(org_id: str, project_id: str) -> List[Dict[str, Any]]:
    return [_public(u) for u in _load_index()["uploads"]
            if u["org_id"] == org_id and u["project_id"] == project_id]


def add_upload(*, org_id: str, project_id: str, filename: str, data: bytes, uploaded_by: str) -> Dict[str, Any]:
    name = os.path.basename(filename or "").strip()[:200] or "upload"
    passages = parse(name, data)
    sha = hashlib.sha256(data).hexdigest()
    with _LOCK:
        idx = _load_index()
        mine = [u for u in idx["uploads"] if u["org_id"] == org_id and u["project_id"] == project_id]
        for u in mine:
            if u["sha256"] == sha:
                return _public(u)
        if len(mine) >= MAX_UPLOADS_PER_PROJECT:
            raise UploadError(f"Upload limit reached ({MAX_UPLOADS_PER_PROJECT} files per Project)")
        uid = "upl_" + uuid.uuid4().hex[:12]
        row = {"upload_id": uid, "org_id": org_id, "project_id": project_id, "filename": name,
               "kind": kind_for(name), "bytes": len(data), "sha256": sha, "passages": len(passages),
               "uploaded_by": uploaded_by, "uploaded_at": _now()}
        _save_json(_org_dir(org_id) / f"{uid}.json", {"upload_id": uid, "org_id": org_id, "passages": passages})
        idx["uploads"].append(row)
        _save_json(_index_path(), idx)
        return _public(row)


def delete_upload(org_id: str, project_id: str, upload_id: str) -> bool:
    with _LOCK:
        idx = _load_index()
        keep = [u for u in idx["uploads"]
                if not (u["org_id"] == org_id and u["project_id"] == project_id and u["upload_id"] == upload_id)]
        if len(keep) == len(idx["uploads"]):
            return False
        idx["uploads"] = keep
        _save_json(_index_path(), idx)
        (_org_dir(org_id) / f"{upload_id}.json").unlink(missing_ok=True)
        return True


def delete_project_uploads(org_id: str, project_id: str) -> int:
    ids = [u["upload_id"] for u in list_uploads(org_id, project_id)]
    for uid in ids:
        delete_upload(org_id, project_id, uid)
    return len(ids)


def passages(org_id: str, project_id: str) -> List[Dict[str, Any]]:
    """Every passage of the Project's uploads, each with its upload's metadata."""
    out = []
    for u in _load_index()["uploads"]:
        if u["org_id"] != org_id or u["project_id"] != project_id:
            continue
        p = _org_dir(org_id) / f"{u['upload_id']}.json"
        if not p.exists():
            continue
        body = json.loads(p.read_text(encoding="utf-8"))
        if body.get("org_id") != org_id:
            continue
        for row in body["passages"]:
            out.append({**row, "upload_id": u["upload_id"], "filename": u["filename"],
                        "kind": u["kind"], "uploaded_at": u["uploaded_at"]})
    return out


def search(org_id: str, project_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    q = set(_TOKEN.findall(query.lower()))
    scored = []
    for p in passages(org_id, project_id):
        s = len(q & set(_TOKEN.findall(p["text"].lower())))
        if s:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]
