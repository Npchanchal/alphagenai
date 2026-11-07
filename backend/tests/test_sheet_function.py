"""Excel add-in (=CITEALPHA.GCI): GET /api/v1/sheet and the static add-in files under frontend/public/office."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.connector_routes import api_actor
from app.main import app

client = TestClient(app)
DEMO = {"X-API-Key": "intellens-demo"}
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
OFFICE = FRONTEND / "public" / "office"


def _rows(params, headers=DEMO):
    r = client.get("/api/v1/sheet", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return {row["query"]: row for row in r.json()["data"]["rows"]}


def test_requires_api_key():
    assert client.get("/api/v1/sheet", params={"tickers": "INFY"}).status_code == 401


def test_key_without_read_api_is_refused():
    app.dependency_overrides[api_actor] = lambda: {"features": ["tracker"], "org_id": "demo"}
    try:
        r = client.get("/api/v1/sheet", params={"tickers": "INFY"})
    finally:
        app.dependency_overrides.pop(api_actor, None)
    assert r.status_code == 403


def test_published_level_matches_dossier():
    dossier = client.get("/api/companies/infy/gci").json()
    row = _rows({"tickers": "INFY"})["INFY"]
    assert row["found"] is True
    assert row["company_id"] == "infy"
    assert row["gci"] == dossier["gci_score"]
    assert row["confidence_tier"] == dossier["confidence_tier"]
    assert row["as_of"] == dossier["as_of"]
    assert row["record"].startswith("Met or beat")
    assert row["coverage_reason"] is None
    assert row["dossier_url"].endswith("/companies/infy")


def test_unscored_name_has_reason_and_no_number():
    row = _rows({"tickers": "TCS"})["TCS"]
    assert row["found"] is True
    assert row["gci"] is None and row["confidence_tier"] is None and row["record"] is None
    assert row["coverage_reason"]


def test_unknown_ticker_is_not_found_and_does_not_fail_the_batch():
    rows = _rows({"tickers": "INFY, NOPE_NOT_LISTED"})
    assert rows["INFY"]["found"] is True
    assert rows["NOPE_NOT_LISTED"]["found"] is False


def test_lowercase_id_and_ticker_resolve_to_same_company():
    rows = _rows({"tickers": "infy,INFY"})
    assert rows["infy"]["company_id"] == rows["INFY"]["company_id"] == "infy"


def test_as_of_reads_the_ledger():
    levels = client.get("/api/v1/index/levels").json()["levels"]
    published = {r["company_id"]: r for r in levels}
    assert "infy" in published
    today = client.get("/api/v1/index/levels").json()["as_of"]
    row = _rows({"tickers": "INFY", "as_of": today})["INFY"]
    assert row["gci"] == published["infy"]["gci"]
    assert row["confidence_tier"] == published["infy"]["confidence_tier"]
    assert row["as_of"] == published["infy"]["as_of"]


def test_as_of_before_first_publication_has_no_number():
    row = _rows({"tickers": "INFY", "as_of": "2020-01-01"})["INFY"]
    assert row["gci"] is None
    assert "2020-01-01" in row["coverage_reason"]


@pytest.mark.parametrize("params", [{"tickers": ",".join(f"T{i}" for i in range(51))},
                                    {"tickers": " , "},
                                    {"tickers": "INFY", "as_of": "01/10/2026"}])
def test_bad_arguments_are_422(params):
    assert client.get("/api/v1/sheet", params=params, headers=DEMO).status_code == 422


def test_sheet_shares_the_public_api_rate_bucket():
    r = client.get("/api/v1/sheet", params={"tickers": "INFY"}, headers=DEMO)
    assert r.headers.get("x-ratelimit-bucket") == "public_api"


# ── Add-in files ─────────────────────────────────────────────────────────────


def test_manifest_points_at_files_that_exist():
    root = ET.parse(OFFICE / "manifest.xml").getroot()
    urls = {el.get("DefaultValue") for el in root.iter() if (el.get("DefaultValue") or "").startswith("https://")}
    office_files = {u.split("/office/", 1)[1] for u in urls if "/office/" in u}
    assert {"functions.js", "functions.json", "taskpane.html"} <= office_files
    for name in office_files:
        assert (OFFICE / name).is_file(), name
    for u in urls:
        if "/office/" not in u and u.endswith(".png"):
            assert (FRONTEND / "public" / u.rsplit("/", 1)[1]).is_file(), u
    ns = {"bt": "http://schemas.microsoft.com/office/officeappbasictypes/1.0"}
    names = {s.get("id"): s.get("DefaultValue") for s in root.iterfind(".//bt:String", ns)}
    assert names["Functions.Namespace"] == "CITEALPHA"


def test_function_metadata_matches_associations():
    meta = json.loads((OFFICE / "functions.json").read_text())
    ids = {f["id"] for f in meta["functions"]}
    associated = set(re.findall(r'CustomFunctions\.associate\("([A-Z]+)"', (OFFICE / "functions.js").read_text()))
    assert ids == associated == {"GCI", "TIER", "ASOF", "RECORD", "LINK"}


def test_taskpane_loads_only_allowed_scripts():
    html = (OFFICE / "taskpane.html").read_text()
    scripts = re.findall(r'<script src="([^"]+)"', html)
    assert scripts == ["https://appsforoffice.microsoft.com/lib/1/hosted/office.js", "functions.js", "taskpane.js"]
    assert "<script>" not in html
    assert "Not investment advice" in html


@pytest.mark.parametrize("conf", ["nginx.conf", "nginx.fargate.conf"])
def test_nginx_lets_office_frame_the_add_in(conf):
    text = (FRONTEND / conf).read_text()
    block = text.split("location ^~ /office/ {", 1)[1].split("}", 1)[0]
    assert "frame-ancestors 'self' https://*.officeapps.live.com" in block
    assert "https://appsforoffice.microsoft.com" in block
    assert "X-Frame-Options" not in block
    assert "Strict-Transport-Security" in block and "nosniff" in block
