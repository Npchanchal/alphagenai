"""W5: indexable dossiers, sitemap payload, OG cards."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_seo_dossiers_are_hand_labeled_and_include_infy():
    r = client.get("/api/public/seo-dossiers")
    assert r.status_code == 200
    body = r.json()
    rows = body["dossiers"]
    assert body["count"] == len(rows)
    assert rows
    assert all(d["data_quality"] == "hand_labeled" for d in rows)
    assert all(d["gci_score"] is not None for d in rows)
    infy = next(d for d in rows if d["id"] == "infy")
    assert infy["gci_score"] == 76.5
    assert "Guidance Credibility Index (GCI) 76.5" in infy["title"]
    assert infy["title"].startswith("Infosys")
    assert "Data as of" in infy["title"]
    assert "Not investment advice" in infy["description"]
    assert infy["record_sentence"].startswith("Met or beat")


def test_og_png_and_svg_for_infy():
    png = client.get("/api/og/infy.png")
    assert png.status_code == 200
    assert png.headers["content-type"].startswith("image/png")
    assert png.content[:8] == b"\x89PNG\r\n\x1a\n"
    svg = client.get("/api/og/infy.svg")
    assert svg.status_code == 200
    assert "image/svg+xml" in svg.headers["content-type"]
    text = svg.text
    assert "Infosys" in text
    assert "Not investment advice" in text
    score = client.get("/api/companies/infy/gci").json()["gci_score"]
    assert score is not None
    assert f"{score:.1f}".rstrip("0").rstrip(".") in text


def test_og_unknown_company_404():
    r = client.get("/api/og/not-a-real-company.png")
    assert r.status_code == 404
