"""What a crawler or answer engine receives: nginx routing, 404s, machine-readable files, HEAD."""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
SERVED_CONFS = ["nginx.conf", "nginx.fargate.conf", "nginx.aws.conf"]
PROXY_CONFS = ["nginx.conf", "nginx.fargate.conf"]

client = TestClient(app)


def _app_route_segments() -> set:
    text = (FRONTEND / "src" / "App.tsx").read_text()
    return {
        p.split("/")[1]
        for p in re.findall(r'path="(/[^"]*)"', text)
        if p != "/" and p.split("/")[1]
    }


def _mapped_segments() -> set:
    text = (FRONTEND / "nginx.spa-routes.conf").read_text()
    alternation = re.search(r"~\^/\(([^)]*)\)", text).group(1)
    return set(alternation.split("|"))


def test_spa_route_map_matches_app_routes():
    assert _mapped_segments() == _app_route_segments()


@pytest.mark.parametrize("conf", SERVED_CONFS)
def test_unknown_paths_404_instead_of_app_shell(conf):
    text = (FRONTEND / conf).read_text()
    assert "include /etc/nginx/snippets/spa-routes.conf;" in text
    assert "try_files $uri $uri/index.html /app-shell.html" not in text
    spa = text.split("location @spa {", 1)[1].split("\n  }", 1)[0]
    assert "if ($spa_route = 0)" in spa and "return 404;" in spa
    assert "location ^~ /.well-known/ {" in text


@pytest.mark.parametrize("dockerfile", ["Dockerfile", "Dockerfile.aws"])
def test_images_ship_the_route_map(dockerfile):
    text = (FRONTEND / dockerfile).read_text()
    assert "COPY nginx.spa-routes.conf /etc/nginx/snippets/spa-routes.conf" in text
    assert "error_page 404 /404.html;" in (FRONTEND / "nginx.static.conf").read_text()


@pytest.mark.parametrize("conf", PROXY_CONFS)
def test_api_prefix_beats_static_regexes(conf):
    text = (FRONTEND / conf).read_text()
    assert "location ^~ /api/ {" in text
    assert re.search(r"^\s*location /api/ \{", text, re.M) is None


def test_ai_catalog_lists_public_data_entries():
    catalog = json.loads((FRONTEND / "public" / ".well-known" / "ai-catalog.json").read_text())
    urls = {e["url"] for e in catalog["entries"]}
    for url in (
        "https://citealpha.com/llms.txt",
        "https://citealpha.com/llms-full.txt",
        "https://citealpha.com/openapi.json",
        "https://citealpha.com/api/v1/rankings",
        "https://citealpha.com/api/v1/index/changelog.rss",
        "https://citealpha.com/sitemap.xml",
    ):
        assert url in urls
    assert all(u.startswith("https://citealpha.com/") for u in urls)


def test_organisation_entity_data_is_external_and_verifiable():
    org = json.loads((FRONTEND / "src" / "lib" / "seo-structured-data.json").read_text())["org"]
    assert re.fullmatch(r"[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}", org["identifier"]["value"])
    assert org["parentOrganization"]["url"].startswith("https://")
    profiles = org.get("socialProfiles") or []
    assert len(profiles) == len(set(profiles))
    for url in profiles + [u for f in org.get("founders") or [] for u in f.get("sameAs") or []]:
        assert url.startswith("https://") and "citealpha.com" not in url, url
        assert not re.search(r"/(sharing|intent|share)\b", url), f"{url} is a share link, not a profile"
        assert not re.search(r"/(admin|dashboard|edit)\b", url), f"{url} is an admin view, not the public profile"
    for founder in org.get("founders") or []:
        assert founder.get("name"), founder


def test_llms_txt_advertises_changelog_feed_and_honest_coverage():
    text = (FRONTEND / "public" / "llms.txt").read_text()
    assert "https://citealpha.com/api/v1/index/changelog.rss" in text
    assert "Sensex companies scored on" not in text


def test_sitemap_lastmod_is_never_the_build_day():
    script = (FRONTEND / "scripts" / "prerender-seo.mjs").read_text()
    assert "BUILD_DAY" not in script
    assert "new Date().toISOString().slice(0, 10)" not in script


def test_head_answers_public_reads():
    for path in ("/api/meta", "/health", "/api/v1/rankings"):
        res = client.head(path)
        assert res.status_code == 200, path
        assert res.content == b""


def test_head_is_not_served_outside_public_reads():
    assert client.head("/api/entitlements/me").status_code == 405
