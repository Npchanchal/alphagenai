"""Public pilot request intake + admin review."""

import os
import re

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app

client = TestClient(app)
ADMIN = {"X-API-Key": "intellens-admin"}


def setup_function() -> None:
    reset_data()


def _challenge_answer(ch: dict) -> str:
    m = re.search(r"What is (\d+) \+ (\d+)\?", ch["prompt"])
    assert m
    return str(int(m.group(1)) + int(m.group(2)))


def _submit_pilot_request(**overrides):
    ch = client.get("/api/auth/abuse-challenge").json()
    payload = {
        "name": "Analyst One",
        "email": "analyst@desk.test",
        "firm": "Example Capital",
        "role": "Head of Research",
        "team_size": "6–15",
        "message": "Sensex coverage pilot",
        "challenge_id": ch["challenge_id"],
        "challenge_answer": _challenge_answer(ch),
        **overrides,
    }
    return client.post("/api/pilot-request", json=payload)


def test_pilot_request_notifies_both_inboxes(monkeypatch):
    sent = []

    def _capture(**kwargs):
        sent.append(kwargs)
        return {"status": "sent", "to": kwargs["to"]}

    monkeypatch.setattr("app.services.mailer.send_mail", _capture)
    monkeypatch.delenv("PILOT_REQUEST_TO", raising=False)
    res = _submit_pilot_request()
    assert res.status_code == 200, res.text
    assert [row["to"] for row in sent] == [
        "sales@citealpha.com",
        "contact@ocotilloinnovation.com",
    ]
    assert sent[0]["reply_to"] == "analyst@desk.test"
    assert "Example Capital" in sent[0]["body"]
    assert "analyst@desk.test" in sent[0]["body"]
    assert "Sensex coverage pilot" in sent[0]["body"]


def test_pilot_request_notify_list_is_configurable(monkeypatch):
    sent = []
    monkeypatch.setenv("PILOT_REQUEST_TO", "only@citealpha.com")
    monkeypatch.setattr(
        "app.services.mailer.send_mail",
        lambda **kwargs: sent.append(kwargs) or {"status": "sent", "to": kwargs["to"]},
    )
    res = _submit_pilot_request()
    assert res.status_code == 200, res.text
    assert [row["to"] for row in sent] == ["only@citealpha.com"]


def test_pilot_request_kept_when_notify_raises(monkeypatch):
    def _boom(**_kwargs):
        raise RuntimeError("ses down")

    monkeypatch.setattr("app.services.mailer.send_mail", _boom)
    res = _submit_pilot_request()
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "pending"
    listed = client.get("/api/admin/portal/pilot-requests", headers=ADMIN)
    row = next(i for i in listed.json()["items"] if i["id"] == res.json()["request_id"])
    assert row["status"] == "pending"
    assert row["notify"][0]["status"] == "error"


def test_pilot_request_stored_as_pending():
    res = _submit_pilot_request()
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "pending"
    assert body["request_id"].startswith("pr_")


def test_approve_emails_recorded_owner_who_joins_as_admin(monkeypatch):
    from app.services import session_auth

    session_auth.reset_auth_store()
    sent = []

    def _capture(**kwargs):
        sent.append(kwargs)
        return {"status": "sent", "to": kwargs["to"]}

    created = _submit_pilot_request(email="rajeev@desk.test", firm="LTM", name="Rajeev Jha").json()
    monkeypatch.setattr("app.services.mailer.send_mail", _capture)
    approved = client.patch(
        f"/api/admin/portal/pilot-requests/{created['request_id']}",
        headers=ADMIN,
        json={"action": "approve", "term_days": 45},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    org_id = body["request"]["org_id"]
    assert body["owner_invite"]["mail_status"] == "sent"
    assert body["owner_invite"]["role"] == "admin"
    assert body["owner_invite"]["email"] == "rajeev@desk.test"
    assert "dev_token" not in (body["request"].get("owner_invite") or {})
    owner_mails = [row for row in sent if row["to"] == "rajeev@desk.test"]
    assert len(owner_mails) == 1
    assert "accept-invite?token=" in owner_mails[0]["body"]
    assert "desk admin" in owner_mails[0]["body"]
    assert "LTM" in owner_mails[0]["subject"]

    joined = client.post(
        "/api/auth/accept-invite",
        json={
            "token": body["owner_invite"]["dev_token"],
            "password": "secret99pass!",
            "name": "Rajeev Jha",
            "accept_terms": True,
        },
    )
    assert joined.status_code == 200, joined.text
    user = joined.json()["user"]
    assert user["org_id"] == org_id
    assert user["role"] == "admin"
    assert user["email"] == "rajeev@desk.test"

    colleague = client.post(
        f"/api/orgs/{org_id}/invites",
        headers={"Authorization": f"Bearer {joined.json()['token']}"},
        json={"email": "analyst@ltm.test", "role": "analyst"},
    )
    assert colleague.status_code == 200, colleague.text

    again = client.post(f"/api/admin/portal/orgs/{org_id}/owner-invite", headers=ADMIN)
    assert again.status_code == 409


def test_approve_keeps_desk_when_invite_mail_raises(monkeypatch):
    created = _submit_pilot_request(email="mailfail@desk.test", firm="Mailfail Desk").json()

    def _boom(**_kwargs):
        raise RuntimeError("ses down")

    monkeypatch.setattr("app.services.mailer.send_mail", _boom)
    approved = client.patch(
        f"/api/admin/portal/pilot-requests/{created['request_id']}",
        headers=ADMIN,
        json={"action": "approve", "term_days": 45},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["request"]["status"] == "approved"
    assert body["request"]["org_id"]
    assert body["owner_invite"]["mail_status"] == "error"
    listed = client.get("/api/admin/portal/orgs", headers=ADMIN)
    assert any(org["id"] == body["request"]["org_id"] for org in listed.json()["orgs"])


def test_owner_invite_resend_and_refuses_other_desk():
    from app.services import session_auth

    session_auth.reset_auth_store()
    bare = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "No Owner Desk", "term_days": 45},
    )
    assert bare.status_code == 200, bare.text
    missing = client.post(
        f"/api/admin/portal/orgs/{bare.json()['org']['id']}/owner-invite",
        headers=ADMIN,
    )
    assert missing.status_code == 400

    opened = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "LTM", "owner_email": "rajeev_jha@hotmail.com", "term_days": 45},
    )
    assert opened.status_code == 200, opened.text
    org_id = opened.json()["org"]["id"]
    first = client.post(f"/api/admin/portal/orgs/{org_id}/owner-invite", headers=ADMIN)
    assert first.status_code == 200, first.text
    assert first.json()["email"] == "rajeev_jha@hotmail.com"
    assert first.json()["role"] == "admin"
    assert first.json()["dev_token"]
    second = client.post(f"/api/admin/portal/orgs/{org_id}/owner-invite", headers=ADMIN)
    assert second.status_code == 200, second.text
    assert second.json()["dev_token"] != first.json()["dev_token"]

    other = client.post(
        "/api/auth/register",
        json={
            "email": "taken@desk.test",
            "password": "secret99pass!",
            "name": "Taken",
            "accept_terms": True,
            "account_type": "b2b",
            "org_name": "Other Desk",
        },
    )
    assert other.status_code == 200, other.text
    clash = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "Clash Desk", "owner_email": "taken@desk.test", "term_days": 45},
    )
    refused = client.post(
        f"/api/admin/portal/orgs/{clash.json()['org']['id']}/owner-invite",
        headers=ADMIN,
    )
    assert refused.status_code == 409


def test_admin_lists_and_approves_pilot_request():
    created = _submit_pilot_request().json()
    request_id = created["request_id"]

    listed = client.get("/api/admin/portal/pilot-requests", headers=ADMIN)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(i["id"] == request_id and i["status"] == "pending" for i in items)

    approved = client.patch(
        f"/api/admin/portal/pilot-requests/{request_id}",
        headers=ADMIN,
        json={"action": "approve", "term_days": 45},
    )
    assert approved.status_code == 200, approved.text
    row = approved.json()["request"]
    assert row["status"] == "approved"
    assert row["org_id"]
    assert approved.json()["provisioned"]["org"]["id"] == row["org_id"]


def test_admin_rejects_pilot_request():
    created = _submit_pilot_request(email="reject@desk.test").json()
    request_id = created["request_id"]

    rejected = client.patch(
        f"/api/admin/portal/pilot-requests/{request_id}",
        headers=ADMIN,
        json={"action": "reject", "note": "Out of scope"},
    )
    assert rejected.status_code == 200
    row = rejected.json()["request"]
    assert row["status"] == "rejected"
    assert row["admin_note"] == "Out of scope"
    assert not row.get("org_id")


def test_pilot_request_requires_abuse_challenge_when_on():
    os.environ["INTELLENS_ABUSE_OFF"] = "0"
    try:
        bad = client.post(
            "/api/pilot-request",
            json={
                "name": "A",
                "email": "a@b.com",
                "firm": "Firm",
            },
        )
        assert bad.status_code == 400
    finally:
        os.environ["INTELLENS_ABUSE_OFF"] = "1"
