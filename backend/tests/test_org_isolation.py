"""Desk admins stay inside their organisation and cannot appoint another admin."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ONESTOP = {"X-API-Key": "intellens-onestop"}
DEMO = {"X-API-Key": "intellens-demo"}
PLATFORM = {"X-API-Key": "intellens-admin"}


def _register(org_name: str) -> dict:
    email = f"owner-{uuid.uuid4().hex[:8]}@isolation.test"
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "secret99pass!",
            "name": "Owner",
            "accept_terms": True,
            "account_type": "b2b",
            "org_name": org_name,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _accept(token: str, email: str) -> dict:
    res = client.post(
        "/api/auth/accept-invite",
        json={
            "token": token,
            "password": "secret99pass!",
            "name": email.split("@")[0],
            "accept_terms": True,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _invite(org_id: str, token: str, email: str, role: str = "viewer"):
    return client.post(
        f"/api/orgs/{org_id}/invites",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": email, "role": role},
    )


def test_admin_cannot_appoint_or_remove_an_admin():
    owner = _register("Hierarchy Desk")
    token = owner["token"]
    org_id = owner["user"]["org_id"]

    invited = _invite(org_id, token, f"seat-{uuid.uuid4().hex[:8]}@isolation.test", "analyst")
    assert invited.status_code == 200, invited.text
    admin = _accept(invited.json()["dev_token"], "admin")
    promoted = client.post(
        f"/api/orgs/{org_id}/members/{admin['user']['id']}/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )
    assert promoted.status_code == 200, promoted.text

    peer = _invite(org_id, token, f"peer-{uuid.uuid4().hex[:8]}@isolation.test", "viewer")
    assert peer.status_code == 200, peer.text
    member = _accept(peer.json()["dev_token"], "peer")

    admin_headers = {"Authorization": f"Bearer {admin['token']}"}
    blocked_invite = _invite(
        org_id, admin["token"], f"nope-{uuid.uuid4().hex[:8]}@isolation.test", "admin"
    )
    assert blocked_invite.status_code == 403
    assert "owner" in blocked_invite.json()["detail"].lower()

    blocked_role = client.post(
        f"/api/orgs/{org_id}/members/{member['user']['id']}/role",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert blocked_role.status_code == 403

    working = client.post(
        f"/api/orgs/{org_id}/members/{member['user']['id']}/role",
        headers=admin_headers,
        json={"role": "analyst"},
    )
    assert working.status_code == 200, working.text
    assert working.json()["user"]["role"] == "analyst"

    blocked_revoke = client.post(
        f"/api/orgs/{org_id}/revoke",
        headers=admin_headers,
        json={"user_id": admin["user"]["id"]},
    )
    assert blocked_revoke.status_code in (400, 403)

    other_admin_invite = _invite(
        org_id, token, f"second-{uuid.uuid4().hex[:8]}@isolation.test", "admin"
    )
    assert other_admin_invite.status_code == 200, other_admin_invite.text
    second = _accept(other_admin_invite.json()["dev_token"], "second")
    assert second["user"]["role"] == "admin"
    removed = client.post(
        f"/api/orgs/{org_id}/revoke",
        headers=admin_headers,
        json={"user_id": second["user"]["id"]},
    )
    assert removed.status_code == 403


def test_session_cannot_read_another_org():
    left = _register("Left Desk")
    right = _register("Right Desk")
    foreign = client.get(
        f"/api/orgs/{right['user']['org_id']}/members",
        headers={"Authorization": f"Bearer {left['token']}"},
    )
    assert foreign.status_code == 403
    own = client.get(
        f"/api/orgs/{left['user']['org_id']}/members",
        headers={"Authorization": f"Bearer {left['token']}"},
    )
    assert own.status_code == 200


def test_desk_key_cannot_cross_orgs_platform_key_can():
    assert client.get("/api/orgs/demo", headers=ONESTOP).status_code == 403
    assert client.get("/api/csm/demo", headers=ONESTOP).status_code == 403
    assert client.get("/api/sla/demo", headers=ONESTOP).status_code == 403
    ticket = client.post(
        "/api/csm/demo/tickets",
        headers=ONESTOP,
        json={"subject": "cross", "severity": "3", "body": "no"},
    )
    assert ticket.status_code == 403
    assert client.get("/api/orgs/demo/pilot-checklist", headers=ONESTOP).status_code == 403
    assert client.get("/api/orgs/onestop-demo", headers=ONESTOP).status_code == 200
    assert client.get("/api/orgs/demo/pilot-checklist", headers=DEMO).status_code == 200
    assert client.get("/api/audit", headers=DEMO, params={"org": "onestop-demo"}).status_code == 403
    assert client.get("/api/orgs/onestop-demo", headers=PLATFORM).status_code == 200
    assert client.get("/api/analytics/events", headers=ONESTOP).status_code == 403
    assert client.get("/api/analytics/events", headers=PLATFORM).status_code == 200
    opened = client.post(
        "/api/orgs/pilot",
        headers=ONESTOP,
        json={"name": "Should Fail", "seats": 2},
    )
    assert opened.status_code == 403
    attest = client.post(
        "/api/legal/attest",
        headers=ONESTOP,
        json={"kind": "terms_privacy", "attested_by": "counsel@isolation.test"},
    )
    assert attest.status_code == 403
    assert client.post("/api/infra/db/migrate", headers=ONESTOP).status_code == 403


def test_msa_sign_stays_on_the_signing_org():
    left = _register("Bill Left")
    right = _register("Bill Right")
    inv = client.post(
        "/api/billing/msa",
        headers={"Authorization": f"Bearer {left['token']}"},
        json={"plan": "desk", "seats": 3},
    )
    assert inv.status_code == 200, inv.text
    stolen = client.post(
        f"/api/billing/msa/{inv.json()['id']}/sign",
        headers={"Authorization": f"Bearer {right['token']}"},
        json={"signer_email": right["user"]["email"]},
    )
    assert stolen.status_code == 404
    signed = client.post(
        f"/api/billing/msa/{inv.json()['id']}/sign",
        headers={"Authorization": f"Bearer {left['token']}"},
        json={"signer_email": left["user"]["email"]},
    )
    assert signed.status_code == 200, signed.text
