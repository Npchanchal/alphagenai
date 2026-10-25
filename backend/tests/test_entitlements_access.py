"""Plan × role entitlements, guest lock, labeling two-person, partner feedback."""

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services.session_auth import reset_auth_store

client = TestClient(app)


def setup_function():
    reset_data()
    reset_auth_store()


def test_platform_super_opens_holdings_and_ninja():
    me = client.get("/api/entitlements/me", headers={"X-API-Key": "intellens-admin"})
    assert me.status_code == 200, me.text
    assert {"holdings", "ninja"} <= set(me.json()["features"])
    opened = client.get("/api/ninja/templates", headers={"X-API-Key": "intellens-admin"})
    assert opened.status_code == 200, opened.text
    latest = client.get("/api/holdings/latest", headers={"X-API-Key": "intellens-admin"})
    assert latest.status_code in (200, 404)
    viewer = client.get("/api/ninja/templates", headers={"X-API-Key": "intellens-viewer"})
    assert viewer.status_code == 403


def test_entitlements_me_guest_default():
    r = client.get("/api/entitlements/me")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "guest"
    assert body["features"] == ["tracker"]
    assert body["limits"]["chat"] == 0


def test_retail_extract_forbidden():
    r = client.post(
        "/api/extract",
        json={"company_id": "infy"},
        headers={"X-API-Key": "intellens-retail"},
    )
    assert r.status_code == 403


def test_guest_session_blocks_review_even_with_demo_key():
    guest = client.post("/api/auth/guest", json={"accept_terms": True})
    assert guest.status_code == 200
    token = guest.json()["token"]
    r = client.post(
        "/api/review",
        json={"company_id": "infy", "outcome_index": 0, "action": "accept"},
        headers={
            "X-API-Key": "intellens-demo",
            "Authorization": f"Bearer {token}",
        },
    )
    assert r.status_code == 403
    assert "read-only" in (r.json().get("detail") or "").lower() or "guest" in (
        r.json().get("detail") or ""
    ).lower()


def test_pilot_analyst_extract_ok():
    r = client.post(
        "/api/extract",
        json={"company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200


def test_pilot_cannot_em_csv():
    r = client.get(
        "/api/export/em-factor/infy?format=csv",
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 403


def test_onestop_em_csv_ok():
    r = client.get(
        "/api/export/em-factor/infy?format=csv",
        headers={"X-API-Key": "intellens-onestop"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


def test_research_chat_requires_feature():
    denied = client.post("/api/research/chat", json={"question": "margin guidance"})
    assert denied.status_code in (401, 403)
    ok = client.post(
        "/api/research/chat",
        json={"question": "margin guidance", "company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert ok.status_code == 200


def test_sights_ask_requires_key():
    denied = client.post(
        "/api/sights/ask",
        json={"question": "What guidance was given on margins?", "company_id": "infy"},
    )
    assert denied.status_code in (401, 403)
    ok = client.post(
        "/api/sights/ask",
        json={"question": "What guidance was given on margins?", "company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert ok.status_code == 200


def test_label_workbench_two_person_and_cite_required(tmp_path, monkeypatch):
    from app.data import audit_log

    monkeypatch.setattr(audit_log, "_PATH", tmp_path / "audit.json")
    monkeypatch.setattr(audit_log, "_LOG", [])
    headers_l = {"X-API-Key": "intellens-onestop-labeler"}
    headers_a = {"X-API-Key": "intellens-onestop"}
    created = client.post(
        "/api/labeling/drafts",
        json={
            "company_id": "infy",
            "period": "FY25",
            "metric": "revenue_growth_pct",
            "guided_low": 8,
            "guided_high": 12,
            "guided_text": "High-single digit growth",
        },
        headers=headers_l,
    )
    assert created.status_code == 200
    draft_id = created.json()["draft"]["id"]
    missing = client.post(f"/api/labeling/drafts/{draft_id}/submit", headers=headers_l)
    assert missing.status_code == 400
    # save citeable fields by creating a complete draft
    created2 = client.post(
        "/api/labeling/drafts",
        json={
            "company_id": "infy",
            "period": "FY25",
            "metric": "revenue_growth_pct",
            "guided_low": 8,
            "guided_high": 12,
            "guided_value": 10,
            "actual_value": 9.5,
            "guided_text": "High-single digit growth",
            "quote_span": "we expect high single-digit revenue growth",
            "source_url": "https://www.infosys.com/investors/reports-filings/example.html",
            "source_ref": "INFY-FY25-PR",
        },
        headers=headers_l,
    )
    assert created2.status_code == 200
    did = created2.json()["draft"]["id"]
    sub = client.post(f"/api/labeling/drafts/{did}/submit", headers=headers_l)
    assert sub.status_code == 200
    same = client.post(f"/api/labeling/drafts/{did}/accept", headers=headers_l)
    assert same.status_code == 403
    acc = client.post(f"/api/labeling/drafts/{did}/accept", headers=headers_a)
    assert acc.status_code == 200
    assert acc.json()["draft"]["status"] == "accepted"


def test_pilot_labeling_forbidden_without_grant():
    r = client.post(
        "/api/labeling/drafts",
        json={"company_id": "infy", "metric": "revenue_growth_pct"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 403


def test_feedback_does_not_require_labeling():
    before = client.get("/api/companies/infy/gci").json()["gci_score"]
    r = client.post(
        "/api/feedback",
        json={
            "company_id": "infy",
            "period": "FY25",
            "metric": "revenue_growth_pct",
            "kind": "wrong_band",
            "comment": "Band looks off vs IR table",
        },
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    item = r.json()["item"]
    assert item["kind"] == "wrong_band"
    assert item.get("queue_item_id")
    listed = client.get("/api/feedback", headers={"X-API-Key": "intellens-demo"})
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1
    queue = client.get("/api/labeling/queue", headers={"X-API-Key": "intellens-demo"})
    assert queue.status_code == 200
    assert queue.json()["count"] >= 1
    after = client.get("/api/companies/infy/gci").json()["gci_score"]
    assert after == before


def test_nps_feedback_does_not_enqueue_queue():
    r = client.post(
        "/api/feedback",
        json={"company_id": "infy", "kind": "nps", "nps": 8},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 200
    assert not r.json()["item"].get("queue_item_id")


def test_guest_cannot_submit_feedback():
    guest = client.post("/api/auth/guest", json={"accept_terms": True})
    token = guest.json()["token"]
    r = client.post(
        "/api/feedback",
        json={"company_id": "infy", "kind": "nps", "nps": 8},
        headers={"Authorization": f"Bearer {token}", "X-API-Key": "intellens-demo"},
    )
    assert r.status_code == 403


def test_guest_sixteenth_dossier_is_cap():
    guest = client.post("/api/auth/guest", json={"accept_terms": True})
    assert guest.status_code == 200
    token = guest.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(15):
        r = client.get("/api/companies/infy/gci", headers=headers)
        assert r.status_code == 200, f"open {i + 1} should succeed"
    capped = client.get("/api/companies/infy/gci", headers=headers)
    assert capped.status_code == 403
    detail = capped.json().get("detail") or {}
    assert detail.get("code") == "guest_dossier_cap"
    assert "register" in (detail.get("message") or "").lower()
    assert "retail_marketing_allowed" in detail


def test_indexing_crawler_passes_the_guest_dossier_cap():
    guest = client.post("/api/auth/guest", json={"accept_terms": True})
    assert guest.status_code == 200
    token = guest.json()["token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    }
    for i in range(16):
        r = client.get("/api/companies/infy/gci", headers=headers)
        assert r.status_code == 200, f"indexer open {i + 1} should succeed"
    human_headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
    for i in range(15):
        r = client.get("/api/companies/infy/gci", headers=human_headers)
        assert r.status_code == 200, f"visitor open {i + 1} should succeed"
    capped = client.get("/api/companies/infy/gci", headers=human_headers)
    assert capped.status_code == 403
    assert (capped.json().get("detail") or {}).get("code") == "guest_dossier_cap"


def test_cite_copy_increments_pilot_checklist():
    ping = client.post(
        "/api/activity/cite-copy",
        json={"company_id": "infy"},
        headers={"X-API-Key": "intellens-demo"},
    )
    assert ping.status_code == 200
    assert ping.json().get("citations_copied", 0) >= 1
    chk = client.get("/api/orgs/demo/pilot-checklist", headers={"X-API-Key": "intellens-demo"})
    assert chk.status_code == 200
    body = chk.json()
    assert body["activity"]["citations_copied"] >= 1
    assert any(i["id"] == "habit_cite" and i["done"] for i in body["items"])


def test_trust_labeling_governance_and_csp():
    r = client.get("/api/trust")
    assert r.status_code == 200
    body = r.json()
    gov = body.get("labeling_governance") or {}
    assert gov.get("two_person_review") is False
    assert "csp" in (body.get("security") or {})
    assert "googletagmanager" in (body["security"].get("csp") or "")
    csp = r.headers.get("content-security-policy") or ""
    assert "googletagmanager.com" in csp
    assert "plausible.io" in csp


def test_vernacular_and_notes_follow_the_seat():
    admin = {"X-API-Key": "intellens-admin"}
    viewer = {"X-API-Key": "intellens-viewer"}
    analyst = {"X-API-Key": "intellens-demo"}
    labeler = {"X-API-Key": "intellens-onestop-labeler"}

    opened = client.get("/api/vernacular/infy?lang=en", headers=admin)
    assert opened.status_code == 200, opened.text
    assert opened.json()["lang"] == "en"

    closed = client.get("/api/vernacular/infy?lang=en", headers=viewer)
    assert closed.status_code == 403

    guest = client.get("/api/vernacular/infy?lang=en")
    assert guest.status_code == 401

    saved = client.post(
        "/api/notes",
        headers=analyst,
        json={"company_id": "infy", "title": "Focus", "body": "Watch the FY26 band."},
    )
    assert saved.status_code == 200, saved.text

    refused = client.post(
        "/api/notes",
        headers=labeler,
        json={"company_id": "infy", "title": "Focus", "body": "Should not save."},
    )
    assert refused.status_code == 403

    viewer_note = client.post(
        "/api/notes",
        headers=viewer,
        json={"company_id": "infy", "title": "Focus", "body": "Should not save."},
    )
    assert viewer_note.status_code == 403


def test_csm_labeling_audit_shape():
    r = client.get("/api/csm/demo", headers={"X-API-Key": "intellens-demo"})
    assert r.status_code == 200
    body = r.json()
    assert "labeling_audit" in body
    assert isinstance(body["labeling_audit"], list)
