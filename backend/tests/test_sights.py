"""CiteAlpha Sights SKU — meta, search, ask, themes, grid, agents, export."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_function():
    from app.data.seed import reset_data

    reset_data()


def _sample_company_id() -> str:
    companies = client.get("/api/companies").json()
    assert companies
    return companies[0]["id"]


def test_sights_in_products_catalog():
    r = client.get("/api/products")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["products"]}
    assert "sights" in ids
    sights = next(p for p in r.json()["products"] if p["id"] == "sights")
    assert sights["ui"][0] == "/sights"
    assert "/api/sights/meta" in sights["endpoints"]


def test_sights_meta():
    r = client.get("/api/sights/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Sights"
    assert body["enabled"] is True
    assert "Compare Grid" in body["brand_map"].values()
    assert body["moved"]["search"] == "/research?scope=all"
    assert "/sights/agents" not in body["ui"]
    assert any("broker" in x.lower() for x in body["refuse"])
    assert "Not investment advice" in body["disclaimer"]


def test_sights_search_lexicon():
    r = client.get("/api/sights/search", params={"q": "revenue guidance", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Sights Search"
    assert "results" in body
    assert body.get("expanded_query")


def test_sights_ask_cite_only():
    cid = _sample_company_id()
    r = client.post(
        "/api/sights/ask",
        json={"question": "What guidance was given on margins?", "company_id": cid},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Sights Ask"
    assert "refused" in body
    assert "citations" in body
    assert body["web_assist"]["enabled"] is False


def test_sights_ask_empty_refuses_or_prompts():
    r = client.post("/api/sights/ask", json={"question": ""}, headers={"X-API-Key": "intellens-demo"})
    assert r.status_code == 200
    assert r.json().get("refused") is False or "Ask" in r.json().get("answer", "")


def test_sights_themes():
    r = client.get("/api/sights/themes", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Delivery Themes"
    assert "themes" in body


def test_sights_street_and_field():
    cid = _sample_company_id()
    street = client.get(f"/api/sights/street/{cid}")
    assert street.status_code == 200
    assert "sell-side" in street.json()["note"].lower()
    field = client.get(f"/api/sights/field/{cid}")
    assert field.status_code == 200
    assert field.json()["product"] == "CiteAlpha Field Evidence"
    assert "outcomes" in field.json()


def test_sights_grid():
    cid = _sample_company_id()
    r = client.post(
        "/api/sights/grid",
        json={"prompts": ["margin guidance"], "company_ids": [cid]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Compare Grid"
    assert body["rows"]
    assert body["rows"][0]["cells"]


def test_sights_deep_dive():
    cid = _sample_company_id()
    r = client.post(
        "/api/sights/deep-dive",
        json={"topic": "guidance delivery", "company_id": cid},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "CiteAlpha Deep Dive"
    assert "steps" in body
    assert "refused" in body


def test_sights_deep_dive_empty_topic():
    r = client.post("/api/sights/deep-dive", json={"topic": "  "})
    assert r.status_code == 200
    assert r.json()["refused"] is True


def test_sights_fundamentals_and_enterprise():
    cid = _sample_company_id()
    fund = client.get(f"/api/sights/fundamentals/{cid}")
    assert fund.status_code == 200
    ent = client.get("/api/sights/enterprise")
    assert ent.status_code == 200
    assert ent.json()["links"]["trust_center"] == "/trust"


def test_retired_sights_tools_point_to_analyst():
    cid = _sample_company_id()
    for method, path, moved in (
        ("get", "/api/sights/agents", "/api/analyst/skills"),
        ("post", "/api/sights/agents/run", "/api/analyst/run"),
        ("get", "/api/sights/hooks", "/api/analyst/destinations"),
        ("get", f"/api/sights/export/{cid}", "/api/analyst/runs/{run_id}/export"),
    ):
        r = getattr(client, method)(path)
        assert r.status_code == 410, path
        assert r.json()["moved_to"] == moved


def test_filing_search_expands_and_spans_all_companies():
    r = client.get("/api/research/search", params={"q": "revenue guidance", "expand": "true", "limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["expanded_query"] != body["original_query"]
    assert len({d["company_id"] for d in body["results"]}) > 1
    plain = client.get("/api/research/search", params={"q": "revenue guidance"}).json()
    assert "expanded_query" not in plain


def test_sights_lexicon_expand_unit():
    from app.services.sights import expand_query_lexicon

    expanded = expand_query_lexicon("revenue outlook")
    assert "topline" in expanded.lower() or "sales" in expanded.lower()
