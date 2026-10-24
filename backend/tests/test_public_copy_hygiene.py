"""Public copy must stay factual (no recommendation phrasing) and match shipped data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

PUBLIC_COPY_FILES = [
    FRONTEND / "src/i18n/locales/en.json",
    FRONTEND / "src/lib/seoRoutes.json",
    FRONTEND / "src/lib/glossary.ts",
    FRONTEND / "src/lib/tours.ts",
    FRONTEND / "src/lib/blogPosts.ts",
    FRONTEND / "scripts/seo-shared.mjs",
    FRONTEND / "public/llms.txt",
    FRONTEND / "public/llms-full.txt",
    FRONTEND / "public/ai.txt",
    FRONTEND / "public/.well-known/ai-catalog.json",
]

BANNED_VOICE = [
    r"AlphaHunter",
    r"intellens",
    r"Trust Score",
    r"Promoter",
    r"\bOne-Stop\b",
    r"corpus hits",
    r"hybrid_pit",
    r"pit\.v1",
    r"Tier-1 gate",
    r"INTELLENS_",
    r"docs/",
    r"Current access:",
    r"\{o\.",
    r"\bCSM\b",
    r"\bsignal\b",
]

RECOMMENDATION_PATTERNS = [
    r"\b(buy|sell|accumulate|avoid|reduce|add)\s+(this|the|these)\s+(stock|stocks|share|shares|name|names)\b",
    r"\btop\s+picks?\b",
    r"\b(strong\s+)?(buy|sell|hold)\s+(rating|signal|call|recommendation)s?\b",
    r"\b(over|under)weight\b",
    r"\btarget\s+price\b",
    r"\bmulti-?bagger\b",
    r"\boutperform(s|ing)?\s+the\s+(market|index|sensex|nifty)\b",
]

NEGATION = re.compile(r"\b(not|no|never|without|nor)\b[^.]{0,30}$", re.IGNORECASE)

RETIRED_CLAIMS = [
    r"Sensex\s*(→|and|&amp;|&|/)\s*Nifty\s+(names|by)",
    r"research OS\b",
    r'href="\$\{SITE\}/api/meta"',
    r"provisional scores?\b",
    r"Versioned, unit-tested scorer",
    r"pit\.v1",
]


def _copy_text(path: Path) -> str:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return "\n".join(str(v) for v in data.values())
        return json.dumps(data, ensure_ascii=False)
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", PUBLIC_COPY_FILES, ids=lambda p: p.name)
def test_public_copy_has_no_recommendation_phrasing(path: Path):
    text = _copy_text(path)
    hits = [
        m.group(0)
        for pat in RECOMMENDATION_PATTERNS
        for m in re.finditer(pat, text, flags=re.IGNORECASE)
        if not NEGATION.search(text[max(0, m.start() - 40) : m.start()])
    ]
    assert not hits, f"{path.name}: recommendation-style phrasing {hits}"


def test_negation_guard_still_catches_recommendations():
    text = "Analysts should buy this stock. Not a Buy, Hold, or Sell recommendation."
    hits = [
        m.group(0)
        for pat in RECOMMENDATION_PATTERNS
        for m in re.finditer(pat, text, flags=re.IGNORECASE)
        if not NEGATION.search(text[max(0, m.start() - 40) : m.start()])
    ]
    assert hits == ["buy this stock"]


@pytest.mark.parametrize("path", PUBLIC_COPY_FILES, ids=lambda p: p.name)
def test_public_copy_has_no_retired_claims(path: Path):
    text = _copy_text(path)
    hits = [m.group(0) for pat in RETIRED_CLAIMS for m in re.finditer(pat, text)]
    assert not hits, f"{path.name}: retired claim {hits}"


def test_static_worked_example_matches_live_infosys_data():
    gci = client.get("/api/companies/infy/gci").json()
    rows = {
        o["period"]: o
        for o in gci["outcomes"]
        if o.get("thread_id") == "infy-rev-cc" and o.get("actual_value") is not None
    }
    static_html = (FRONTEND / "scripts/seo-shared.mjs").read_text(encoding="utf-8")
    for period in ("FY22", "FY23", "FY24"):
        o = rows[period]
        assert o["citeable"] is True
        assert o["source_url"] in static_html
        assert o["guidance_source_url"] in static_html
        assert f"“{o['guidance_quote']}”" in static_html
        assert f"“{o['quote_span']}”" in static_html
        line = (
            f"{period} — guided {o['guided_low']:g}–{o['guided_high']:g}%, "
            f"actual {o['actual_value']:g}% — <strong>{o['label']}</strong> "
            f"(reported {o['as_of']})"
        )
        assert line in static_html or line.replace("4–7%", "4.0–7.0%") in static_html, line


@pytest.mark.parametrize("path", PUBLIC_COPY_FILES, ids=lambda p: p.name)
def test_public_copy_bans_legacy_voice(path: Path):
    text = _copy_text(path)
    hits = [m.group(0) for pat in BANNED_VOICE for m in re.finditer(pat, text)]
    assert not hits, f"{path.name}: banned voice {hits}"


def test_ai_catalog_manifest_shape():
    """Lighthouse fetches /.well-known/ai-catalog.json and rejects HTML or a bad schema."""
    data = json.loads((FRONTEND / "public/.well-known/ai-catalog.json").read_text(encoding="utf-8"))
    assert data["specVersion"] == "1.0"
    assert data["host"]["displayName"] == "CiteAlpha"
    ident = re.compile(r"^urn:air:[a-zA-Z0-9.-]+(:[a-zA-Z0-9._-]+)+$")
    seen: set[str] = set()
    assert data["entries"]
    for entry in data["entries"]:
        assert ident.match(entry["identifier"]), entry["identifier"]
        assert entry["identifier"] not in seen
        seen.add(entry["identifier"])
        assert entry["displayName"]
        assert entry["type"]
        assert entry.get("url", "").startswith("https://citealpha.com/")
        assert "data" not in entry


def test_ai_search_crawlers_may_index_and_quote():
    """Answer engines opt in only when their own crawler token is allowed."""
    robots = (FRONTEND / "public/robots.txt").read_text(encoding="utf-8")
    for bot in (
        "OAI-SearchBot",
        "ChatGPT-User",
        "Claude-SearchBot",
        "PerplexityBot",
        "Google-Extended",
        "Google-InspectionTool",
        "Bingbot",
    ):
        assert f"User-agent: {bot}" in robots
    assert "Disallow:" not in robots
    assert "search=yes" in robots
    assert "ai-input=yes" in robots
    llms = (FRONTEND / "public/llms.txt").read_text(encoding="utf-8")
    assert "https://citealpha.com/llms-full.txt" in llms
    assert "/sights/ask" not in llms
    full = (FRONTEND / "public/llms-full.txt").read_text(encoding="utf-8")
    assert "Guidance Credibility Index (GCI)" in full
    assert "Not a Buy, Hold, or Sell recommendation." in full


def test_badge_and_trust_api_strings_ban_legacy_voice():
    badge = client.get("/api/badge/INFY").json()
    svg = client.get("/api/badge/INFY/svg").text
    trust = client.get("/api/trust").json()
    blob = json.dumps(badge) + "\n" + svg + "\n" + json.dumps(trust)
    for pat in (r"Trust Score", r"intellens", r"Promoter", r"One-Stop", r"AlphaHunter"):
        assert not re.search(pat, blob), pat
    assert trust["compliance"].get("prices_on_public") is False
    assert trust["compliance"].get("link_out_policy")


def test_methodology_names_promise_keeping_and_constants():
    """Public methodology states the floor philosophy, δ=1 points, and the filing check."""
    data = json.loads((FRONTEND / "src/i18n/locales/en.json").read_text(encoding="utf-8"))
    philosophy = data["method.page.formula.philosophy"]
    assert "promise-keeping discipline, not forecast accuracy" in philosophy
    constants = data["method.page.formula.constants.text"]
    assert "about 59" in constants
    assert "about 88" in constants
    assert "15 points" in constants
    review = data["method.page.review.i4"]
    assert "both contain the recorded quotes" in review
    assert "analyst" not in review.lower()
    limits = data["method.page.limitations.i3"]
    assert "±2%" in limits
    assert "0.1 percentage point" in limits
    comparable = data["method.page.company.comparable.text"]
    assert "half-width" in comparable
    assert "not adjusted by sector" in comparable
    trust_note = client.get("/api/trust").json()["labeling_governance"]["note"]
    assert trust_note == review
    static_html = (FRONTEND / "scripts/seo-shared.mjs").read_text(encoding="utf-8")
    assert "was well off" not in static_html
    assert "promise-keeping discipline, not forecast accuracy" in static_html


def test_badge_api_strings_ban_trust_score_and_intellens():
    """W5.4: broker badge is GCI, not a Trust Score / intellens embed."""
    badge = client.get("/api/badge/INFY").json()
    svg = client.get("/api/badge/INFY/svg").text
    blob = json.dumps(badge) + "\n" + svg
    assert "Trust Score" not in blob
    assert "intellens" not in blob.lower()
    assert "Promoter" not in blob
    assert badge["label"] == "Guidance Credibility Index (GCI)"
