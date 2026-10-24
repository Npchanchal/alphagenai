"""CiteAlpha Analyst Projects, memory and uploads: parsing, Skills, tenant isolation (US-A06, A3 gate)."""

import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.agent import projects, runtime, tools, uploads

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
OTHER = {"X-API-Key": "intellens-onestop"}

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    reset_data()


def make_docx(paras):
    body = "".join(f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>' for p in paras)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


def make_xlsx(rows, sheet="Model"):
    shared, xml_rows = [], []
    for i, row in enumerate(rows, start=1):
        cells = []
        for j, val in enumerate(row):
            ref = f"{chr(65 + j)}{i}"
            if isinstance(val, str):
                shared.append(val)
                cells.append(f'<c r="{ref}" t="s"><v>{len(shared) - 1}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
        xml_rows.append(f'<row r="{i}">{"".join(cells)}</row>')
    sst = "".join(f"<si><t>{s}</t></si>" for s in shared)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets><sheet name="{sheet}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   f'<Relationships xmlns="{PR}"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{S}">{sst}</sst>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{S}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
    return buf.getvalue()


MODEL = make_xlsx([["Driver", "FY26E", "FY27E"], ["Revenue growth cc %", 3, 6],
                   ["Operating margin %", 21, 21.5], ["Notes", "stub"]])
MEMO = make_docx([
    "Stub information memorandum prepared for testing.",
    "The company expects revenue growth of 9% in constant currency next year.",
    "A debt schedule with term loan repayment dates is attached as Annexure 4.",
])


def _upload(pid, name, data, headers=DEMO):
    return client.post(f"/api/analyst/projects/{pid}/uploads",
                       json={"filename": name, "content_base64": base64.b64encode(data).decode()}, headers=headers)


def _project(headers=DEMO, companies=("infy",)):
    r = client.post("/api/analyst/projects", json={"name": "Stub IT coverage", "company_ids": list(companies)}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


# ── Parsing ──────────────────────────────────────────────────────────────────


def test_parse_xlsx_keeps_sheet_and_cell():
    rows = uploads.parse("model.xlsx", MODEL)
    assert {"loc": "Model!A2", "text": "Revenue growth cc % | 3 | 6"} in rows


def test_parse_docx_csv_txt():
    assert uploads.parse("memo.docx", MEMO)[1]["loc"] == "para 2"
    assert uploads.parse("m.csv", b"Revenue,10,12\n\nEBITDA,3,4\n")[1] == {"loc": "line 3", "text": "EBITDA | 3 | 4"}
    assert uploads.parse("n.txt", b"First point here. Second point here.\n\nThird.")[0]["loc"] == "para 1"


@pytest.mark.parametrize("name,data,msg", [
    ("x.exe", b"MZ", "Unsupported"),
    ("x.docx", b"not a zip", "Not a valid"),
    ("x.txt", b"   ", "No readable"),
    ("x.txt", b"a" * (uploads.MAX_BYTES + 1), "larger than"),
])
def test_parse_rejects(name, data, msg):
    with pytest.raises(uploads.UploadError, match=msg):
        uploads.parse(name, data)


def test_parse_rejects_xml_entities():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", '<!DOCTYPE x [<!ENTITY a "aaaa">]><w:document xmlns:w="%s"/>' % W)
    with pytest.raises(uploads.UploadError, match="entity"):
        uploads.parse("x.docx", buf.getvalue())


# ── Skills inside a Project ──────────────────────────────────────────────────


def test_weekly_driver_review_cites_model_cells():
    pid = _project()
    assert _upload(pid, "model.xlsx", MODEL).status_code == 200
    r = client.post("/api/analyst/run", json={"skill_id": "weekly_driver_review", "company_id": "infy", "project_id": pid}, headers=DEMO)
    assert r.status_code == 200, r.text
    out = r.json()
    drivers = next(s for s in out["sections"] if s["id"] == "drivers")
    texts = [c["text"] for c in drivers["claims"]]
    assert "Model driver: Revenue growth cc % (model.xlsx (Model!A2))." in texts
    assert not any("Notes" in t for t in texts)
    up = [c for c in out["citations"] if c["kind"] == "upload"]
    assert up and all(c["source_url"].startswith("upload://") for c in up)
    assert out["project"]["project_id"] == pid


def test_diligence_room_checks_claims_and_lists_gaps():
    pid = _project()
    _upload(pid, "memo.docx", MEMO)
    out = client.post("/api/analyst/run", json={"skill_id": "diligence_room", "company_id": "infy", "project_id": pid}, headers=DEMO).json()
    claims = next(s for s in out["sections"] if s["id"] == "claims")["claims"]
    assert any("revenue growth of 9%" in c["text"] for c in claims)
    coverage = next(s for s in out["sections"] if s["id"] == "coverage")["claims"]
    assert any(c["text"].startswith("Debt schedule: covered in memo.docx") for c in coverage)
    assert any("Related-party transactions: not found in the uploaded files" in n for n in out["not_found"])


def test_project_skill_needs_project_and_cannot_be_monitored():
    r = client.post("/api/analyst/run", json={"skill_id": "diligence_room", "company_id": "infy"}, headers=DEMO)
    assert r.status_code == 422
    r = client.post("/api/analyst/monitors", json={"skill_id": "diligence_room", "company_id": "infy"}, headers=DEMO)
    assert r.status_code == 422


def test_company_must_be_in_project():
    pid = _project(companies=("infy",))
    r = client.post("/api/analyst/run", json={"skill_id": "board_scorecard", "company_id": "tcs", "project_id": pid}, headers=DEMO)
    assert r.status_code == 422


def test_memory_is_editable_and_never_cited():
    pid = _project()
    m = client.post(f"/api/analyst/projects/{pid}/memory", json={"text": "Focus on Mysuru campus utilisation"}, headers=DEMO).json()
    assert client.get(f"/api/analyst/projects/{pid}", headers=DEMO).json()["memory"][0]["id"] == m["id"]
    out = client.post("/api/analyst/run", json={"skill_id": "board_scorecard", "company_id": "infy", "project_id": pid}, headers=DEMO).json()
    assert out["project"]["memory_items"] == 1
    assert not any("Mysuru" in (c.get("quote") or "") for c in out["citations"])
    assert client.delete(f"/api/analyst/projects/{pid}/memory/{m['id']}", headers=DEMO).status_code == 200
    assert client.get(f"/api/analyst/projects/{pid}", headers=DEMO).json()["memory"] == []


def test_upload_dedupe_limit_and_bad_base64(monkeypatch):
    pid = _project()
    a = _upload(pid, "model.xlsx", MODEL).json()
    assert _upload(pid, "copy.xlsx", MODEL).json()["upload_id"] == a["upload_id"]
    monkeypatch.setattr(uploads, "MAX_UPLOADS_PER_PROJECT", 1)
    assert _upload(pid, "memo.docx", MEMO).status_code == 422
    bad = client.post(f"/api/analyst/projects/{pid}/uploads", json={"filename": "a.txt", "content_base64": "%%%"}, headers=DEMO)
    assert bad.status_code == 422


# ── Tenant isolation (A3 exit gate) ──────────────────────────────────────────


def test_other_org_cannot_see_use_or_change_project():
    pid = _project()
    uid = _upload(pid, "memo.docx", MEMO).json()["upload_id"]
    assert client.get(f"/api/analyst/projects/{pid}", headers=OTHER).status_code == 404
    assert client.get("/api/analyst/projects", headers=OTHER).json()["projects"] == []
    assert _upload(pid, "x.txt", b"Stub text here for org B.", headers=OTHER).status_code == 404
    assert client.delete(f"/api/analyst/projects/{pid}/uploads/{uid}", headers=OTHER).status_code == 404
    assert client.post(f"/api/analyst/projects/{pid}/memory", json={"text": "x"}, headers=OTHER).status_code == 404
    r = client.post("/api/analyst/run", json={"skill_id": "diligence_room", "company_id": "infy", "project_id": pid}, headers=OTHER)
    assert r.status_code == 404
    assert client.delete(f"/api/analyst/projects/{pid}", headers=OTHER).status_code == 404


def test_other_org_runs_never_retrieve_uploads():
    pid_a = _project()
    _upload(pid_a, "memo.docx", MEMO)
    pid_b = _project(headers=OTHER)
    out = client.post("/api/analyst/run", json={"skill_id": "diligence_room", "company_id": "infy", "project_id": pid_b}, headers=OTHER).json()
    assert not any(c["kind"] == "upload" for c in out["citations"])
    assert "Stub information memorandum" not in out["markdown"]
    for skill in ("results_prep", "company_ramp", "coverage_monitor"):
        o = client.post("/api/analyst/run", json={"skill_id": skill, "company_id": "infy"}, headers=OTHER).json()
        assert "revenue growth of 9%" not in o["markdown"]
    assert tools.project_uploads("infy", org_id="someone-else", project_id=pid_a)["evidence"] == []


def test_deleting_upload_and_project_removes_content():
    pid = _project()
    uid = _upload(pid, "memo.docx", MEMO).json()["upload_id"]
    assert client.delete(f"/api/analyst/projects/{pid}/uploads/{uid}", headers=DEMO).status_code == 200
    out = client.post("/api/analyst/run", json={"skill_id": "diligence_room", "company_id": "infy", "project_id": pid}, headers=DEMO).json()
    assert not any(c["kind"] == "upload" for c in out["citations"])
    _upload(pid, "memo.docx", MEMO)
    files = list((uploads._root()).rglob("upl_*.json"))
    assert len(files) == 1
    assert client.delete(f"/api/analyst/projects/{pid}", headers=DEMO).status_code == 200
    assert list(uploads._root().rglob("upl_*.json")) == []


def test_runtime_without_org_ignores_project_uploads():
    proj = projects.create_project(org_id="o1", created_by="u", name="p", company_ids=["infy"])
    uploads.add_upload(org_id="o1", project_id=proj["project_id"], filename="memo.docx", data=MEMO, uploaded_by="u")
    out = runtime.run_skill("diligence_room", "infy", use_llm=False, org_id=None, project=proj)
    assert not any(c["kind"] == "upload" for c in out["citations"])
