"""CiteAlpha Analyst A6: org API keys, public API v1, rate limits, MCP server, webhook / Slack / Teams delivery."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.agent import delivery, monitors, org_keys

client = TestClient(app)
ADMIN = {"X-API-Key": "intellens-admin"}
DEMO = {"X-API-Key": "intellens-demo"}
OTHER = {"X-API-Key": "intellens-onestop"}


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INTELLENS_PUBLIC_URL", "https://citealpha.example")
    monkeypatch.setattr(delivery, "_private_host", lambda host: host.endswith(".internal"))
    reset_data()


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def poster(url, body, headers):
        calls.append({"url": url, "body": body, "headers": headers})
        return 200

    monkeypatch.setattr(delivery, "_post", poster)
    return calls


def _key(headers=ADMIN, role="analyst"):
    r = client.post("/api/analyst/keys", json={"label": "Desk script", "role": role}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _bearer(plain):
    return {"Authorization": f"Bearer {plain}"}


# ── Org API keys ─────────────────────────────────────────────────────────────


def test_key_shown_once_hash_stored_and_listed_without_secret(tmp_path):
    out = _key()
    assert out["key"].startswith("ca_live_") and out["prefix"] == out["key"][:14]
    stored = (tmp_path / "analyst_org_keys.json").read_text()
    assert out["key"] not in stored
    assert hashlib.sha256(out["key"].encode()).hexdigest() in stored
    listed = client.get("/api/analyst/keys", headers=ADMIN).json()["keys"]
    assert [k["key_id"] for k in listed] == [out["key_id"]]
    assert "key" not in listed[0] and "sha256" not in listed[0]


def test_only_admins_manage_keys():
    assert client.post("/api/analyst/keys", json={"label": "x"}, headers=DEMO).status_code == 403
    assert client.get("/api/analyst/keys", headers=DEMO).status_code == 403


def test_revoked_key_stops_working():
    out = _key()
    assert client.get("/api/v1/analyst/skills", headers=_bearer(out["key"])).status_code == 200
    assert client.delete(f"/api/analyst/keys/{out['key_id']}", headers=ADMIN).status_code == 200
    assert client.get("/api/v1/analyst/skills", headers=_bearer(out["key"])).status_code == 403


def test_org_key_cannot_call_operator_routes():
    out = _key()
    r = client.post("/api/ops/analyst/digest/send", headers={"X-API-Key": out["key"]})
    assert r.status_code == 403


def test_key_limit_per_org():
    for _ in range(org_keys.MAX_KEYS_PER_ORG):
        _key()
    r = client.post("/api/analyst/keys", json={"label": "one too many"}, headers=ADMIN)
    assert r.status_code == 409


# ── Public API v1 ────────────────────────────────────────────────────────────


def test_public_api_requires_a_key():
    assert client.get("/api/v1/analyst/skills").status_code == 401
    assert client.get("/api/v1/analyst/skills", headers=_bearer("ca_live_nope")).status_code == 403


def test_public_api_envelope_and_run_isolation():
    mine = _key()
    skills = client.get("/api/v1/analyst/skills", headers=_bearer(mine["key"])).json()
    assert skills["data"] and {"api_version", "disclaimer"} <= set(skills)
    r = client.post("/api/v1/analyst/runs", json={"skill_id": "peer_delivery_grid", "company_id": "infy"},
                    headers=_bearer(mine["key"]))
    assert r.status_code == 200, r.text
    run_id = r.json()["data"]["run_id"]
    assert client.get(f"/api/v1/analyst/runs/{run_id}", headers=_bearer(mine["key"])).status_code == 200
    other = _key(OTHER)
    assert client.get(f"/api/v1/analyst/runs/{run_id}", headers=_bearer(other["key"])).status_code == 404
    exp = client.get(f"/api/v1/analyst/runs/{run_id}/export?format=md", headers=_bearer(mine["key"]))
    assert exp.status_code == 200 and b"Evidence receipt" in exp.content


def test_public_commitments_and_search_shapes():
    k = _bearer(_key()["key"])
    c = client.get("/api/v1/analyst/companies/infy/commitments", headers=k)
    assert c.status_code == 200
    body = c.json()
    cites = {x["n"] for x in body["citations"]}
    assert all(row["cite"] in cites for row in body["data"]["commitments"])
    assert all(row["state"] != "proposed" for row in body["data"]["commitments"])
    s = client.get("/api/v1/analyst/companies/infy/search?q=revenue", headers=k)
    assert s.status_code == 200 and s.json()["data"]["found"] == len(s.json()["citations"])
    assert client.get("/api/v1/analyst/companies/infy/search?q=", headers=k).status_code == 422
    assert client.get("/api/v1/analyst/companies/nope/commitments", headers=k).status_code == 404


def test_public_api_rate_limit(monkeypatch):
    monkeypatch.setenv("PUBLIC_API_RPM", "5")
    k = _bearer(_key()["key"])
    codes = [client.get("/api/v1/analyst/skills", headers=k).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


# ── MCP server ───────────────────────────────────────────────────────────────


def _rpc(method, params=None, rid=1, headers=None):
    body = {"jsonrpc": "2.0", "method": method, **({"id": rid} if rid is not None else {})}
    if params is not None:
        body["params"] = params
    return client.post("/api/mcp", json=body, headers=headers)


def test_mcp_needs_auth_and_get_is_405():
    assert _rpc("initialize").status_code == 401
    assert client.get("/api/mcp").status_code == 405


def test_mcp_initialize_list_and_call():
    k = _bearer(_key()["key"])
    init = _rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}}, headers=k)
    assert init.status_code == 200
    assert init.json()["result"]["protocolVersion"] == "2025-06-18"
    assert _rpc("notifications/initialized", rid=None, headers=k).status_code == 202
    tools = _rpc("tools/list", headers=k).json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"list_skills", "get_gci", "get_commitments", "search_filings", "run_skill", "get_run"} <= names
    assert all(t["inputSchema"]["type"] == "object" for t in tools)
    call = _rpc("tools/call", {"name": "run_skill", "arguments": {"skill_id": "peer_delivery_grid", "company_id": "infy"}},
                headers=k).json()["result"]
    assert call["isError"] is False
    assert json.loads(call["content"][0]["text"])["data"]["run_id"] == call["structuredContent"]["data"]["run_id"]


def test_mcp_errors():
    k = _bearer(_key()["key"])
    assert _rpc("tools/call", {"name": "nope", "arguments": {}}, headers=k).json()["error"]["code"] == -32602
    assert _rpc("bogus", headers=k).json()["error"]["code"] == -32601
    bad = _rpc("tools/call", {"name": "get_commitments", "arguments": {"company_id": "nope"}}, headers=k).json()
    assert bad["result"]["isError"] is True


def test_mcp_get_gci_hides_unpublished_scores():
    k = _bearer(_key()["key"])
    from app.services import repository

    unpublished = 0
    for c in repository.list_companies()[:40]:
        cid = c.get("id") or c.get("company_id")
        res = _rpc("tools/call", {"name": "get_gci", "arguments": {"company_id": cid}}, headers=k).json()["result"]
        if res["isError"]:
            continue
        data = res["structuredContent"]["data"]
        if data.get("published"):
            assert data["confidence_tier"] and res["structuredContent"]["citations"]
        else:
            unpublished += 1
            assert data.get("gci") is None and "record" not in data
    assert unpublished


# ── Delivery ─────────────────────────────────────────────────────────────────


def test_destination_url_rules():
    bad = [
        ("webhook", "http://example.com/hook"),
        ("webhook", "https://db.internal/hook"),
        ("slack", "https://evil.example/services/x"),
        ("teams", "https://example.com/webhook"),
    ]
    for kind, url in bad:
        r = client.post("/api/analyst/destinations", json={"kind": kind, "url": url}, headers=ADMIN)
        assert r.status_code == 422, (kind, url)
    ok = client.post("/api/analyst/destinations",
                     json={"kind": "teams", "url": "https://acme.webhook.office.com/webhookb2/abc"}, headers=ADMIN)
    assert ok.status_code == 200


def test_webhook_is_signed_and_secret_shown_once(sent):
    out = client.post("/api/analyst/destinations", json={"kind": "webhook", "url": "https://hooks.example.com/ca"},
                      headers=ADMIN).json()
    secret = out["secret"]
    assert secret.startswith("whsec_")
    assert "secret" not in client.get("/api/analyst/destinations", headers=ADMIN).json()["destinations"][0]
    res = client.post(f"/api/analyst/destinations/{out['destination_id']}/test", headers=ADMIN).json()["result"]
    assert res["ok"] is True
    h = sent[0]["headers"]
    expect = hmac.new(secret.encode(), f"{h['X-CiteAlpha-Timestamp']}.".encode() + sent[0]["body"], hashlib.sha256)
    assert h["X-CiteAlpha-Signature"] == "sha256=" + expect.hexdigest()
    assert h["X-CiteAlpha-Event"] == "monitor.run"


def test_slack_and_teams_payloads(sent):
    for kind, url in (("slack", "https://hooks.slack.com/services/T/B/x"),
                      ("teams", "https://acme.webhook.office.com/webhookb2/abc")):
        client.post("/api/analyst/destinations", json={"kind": kind, "url": url, "events": ["digest.weekly"]}, headers=ADMIN)
    delivery.deliver("demo", "digest.weekly", {"x": 1}, "Line one\nLine two")
    bodies = {c["url"]: json.loads(c["body"]) for c in sent}
    assert bodies["https://hooks.slack.com/services/T/B/x"] == {"text": "Line one\nLine two"}
    assert bodies["https://acme.webhook.office.com/webhookb2/abc"] == {"text": "Line one<br>Line two"}
    assert all("X-CiteAlpha-Signature" not in c["headers"] for c in sent)


def test_delivery_respects_events_and_org(sent):
    client.post("/api/analyst/destinations", json={"kind": "webhook", "url": "https://hooks.example.com/a",
                                                    "events": ["digest.weekly"]}, headers=ADMIN)
    assert delivery.deliver("demo", "monitor.run", {}, "x") == []
    assert delivery.deliver("onestop-demo", "digest.weekly", {}, "x") == []
    assert len(delivery.deliver("demo", "digest.weekly", {}, "x")) == 1


def test_failed_delivery_retries_once_and_is_logged(monkeypatch):
    calls = []

    def flaky(url, body, headers):
        calls.append(url)
        raise OSError("down")

    monkeypatch.setattr(delivery, "_post", flaky)
    client.post("/api/analyst/destinations", json={"kind": "webhook", "url": "https://hooks.example.com/a"}, headers=ADMIN)
    res = delivery.deliver("demo", "monitor.run", {}, "x")
    assert len(calls) == 2 and res[0]["ok"] is False and res[0]["error"] == "OSError"
    log = client.get("/api/analyst/destinations", headers=ADMIN).json()["log"]
    assert log and log[0]["ok"] is False


def test_monitor_run_pushes_cited_payload(sent):
    client.post("/api/analyst/destinations", json={"kind": "webhook", "url": "https://hooks.example.com/a"}, headers=ADMIN)
    run = client.post("/api/analyst/run", json={"skill_id": "peer_delivery_grid", "company_id": "infy"}, headers=DEMO).json()
    monitors._push({"org_id": "demo", "monitor_id": "mon_t"}, run)
    body = json.loads(sent[0]["body"])
    assert body["event"] == "monitor.run"
    data = body["data"]
    assert data["run_id"] == run["run_id"] and data["citations"] and data["disclaimer"]
    assert data["link"].startswith("https://citealpha.example/analyst?run=")
    assert all(c["kind"] != "upload" for c in data["citations"])
