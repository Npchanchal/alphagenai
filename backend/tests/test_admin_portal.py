"""Platform admin portal — role-based access."""

from fastapi.testclient import TestClient

from app.data.seed import reset_data
from app.main import app
from app.services import session_auth

client = TestClient(app)
ADMIN = {"X-API-Key": "intellens-admin"}


def setup_function() -> None:
    reset_data()
    session_auth.reset_auth_store()


def _register(email: str, *, org_name: str = "Ops Desk") -> dict:
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "secret99pass!",
            "name": "Admin User",
            "accept_terms": True,
            "account_type": "b2b",
            "org_name": org_name,
        },
    ).json()


def _grant_platform_role(actor_headers: dict, user_id: str, role: str) -> None:
    r = client.patch(
        f"/api/admin/portal/users/{user_id}/platform-role",
        headers=actor_headers,
        json={"platform_admin_role": role},
    )
    assert r.status_code == 200, r.text


def test_cleanup_drops_e2e_tenants_and_keeps_approved_desks():
    from app.data.seed import get_data, save_data

    real = _register("sunil@gmail.com", org_name="Sunil")
    data = get_data()
    data["orgs"]["rbi-approved"] = {
        "name": "RBI",
        "plan": "pilot",
        "account_type": "b2b",
        "seats": 5,
        "seats_used": 0,
    }
    data["pilot_requests"] = [
        {
            "id": "pr_rbi",
            "status": "approved",
            "email": "syshende@gmail.com",
            "firm": "RBI",
            "org_id": "rbi-approved",
        }
    ]
    data["orgs"]["e2e-desk-abc"] = {
        "name": "E2E Desk",
        "plan": "pilot",
        "account_type": "b2b",
        "seats": 5,
        "seats_used": 1,
    }
    data["pilot_checklists"] = {"e2e-desk-abc": {"org_id": "e2e-desk-abc"}}
    save_data()
    store = session_auth._load_users()
    store["users"].extend(
        [
            {
                "id": "e2e-user",
                "email": "e2e-pilot@ocotillo.test",
                "name": "E2E",
                "kind": "registered",
                "org_id": "e2e-desk-abc",
                "role": "owner",
                "active": True,
            },
            {
                "id": "guest-1",
                "email": None,
                "kind": "guest",
                "role": "guest",
                "active": True,
            },
        ]
    )
    session_auth._save_users()

    dry = client.post(
        "/api/admin/portal/cleanup-test-tenants",
        headers=ADMIN,
        json={"dry_run": True},
    )
    assert dry.status_code == 200, dry.text
    assert "e2e-pilot@ocotillo.test" in dry.json()["users_removed"]
    assert "e2e-desk-abc" in dry.json()["orgs_removed"]
    assert "rbi-approved" not in dry.json()["orgs_removed"]
    assert any(u.get("email") == "e2e-pilot@ocotillo.test" for u in session_auth._load_users()["users"])

    live = client.post(
        "/api/admin/portal/cleanup-test-tenants",
        headers=ADMIN,
        json={"dry_run": False},
    )
    assert live.status_code == 200, live.text
    emails = {u.get("email") for u in session_auth._load_users()["users"]}
    assert "sunil@gmail.com" in emails
    assert "e2e-pilot@ocotillo.test" not in emails
    assert real["user"]["id"] in {u.get("id") for u in session_auth._load_users()["users"]}
    org_ids = set(get_data()["orgs"])
    assert "e2e-desk-abc" not in org_ids
    assert "rbi-approved" in org_ids
    assert "e2e-desk-abc" not in (get_data().get("pilot_checklists") or {})


def test_admin_portal_requires_platform_role():
    user = _register("noadmin@desk.test")
    token = user["token"]
    r = client.get("/api/admin/portal/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_super_admin_api_key_has_full_portal():
    r = client.get("/api/admin/portal/me", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["platform_admin_role"] == "super"
    assert "users.write" in body["permissions"]
    assert any(s["id"] == "system" for s in body["sections"])


def test_compliance_role_cannot_list_users():
    compliance = _register("compliance@ocotillo.test")
    _grant_platform_role(ADMIN, compliance["user"]["id"], "compliance")
    ctoken = compliance["token"]

    me = client.get("/api/admin/portal/me", headers={"Authorization": f"Bearer {ctoken}"})
    assert me.status_code == 200
    assert me.json()["platform_admin_role"] == "compliance"
    assert "legal.read" in me.json()["permissions"]
    assert "users.read" not in me.json()["permissions"]

    users = client.get("/api/admin/portal/users", headers={"Authorization": f"Bearer {ctoken}"})
    assert users.status_code == 403


def test_ops_role_can_list_orgs_not_legal_write():
    ops = _register("ops@ocotillo.test")
    _grant_platform_role(ADMIN, ops["user"]["id"], "ops")
    otoken = ops["token"]

    orgs = client.get("/api/admin/portal/orgs", headers={"Authorization": f"Bearer {otoken}"})
    assert orgs.status_code == 200
    assert len(orgs.json()["orgs"]) >= 1

    attest = client.post(
        "/api/admin/portal/legal/attest",
        headers={"Authorization": f"Bearer {otoken}"},
        json={"kind": "terms_privacy", "attested_by": "ops@ocotillo.test"},
    )
    assert attest.status_code == 403


def test_super_role_refused_for_every_other_email():
    other = _register("random.super@desk.test")
    denied = client.patch(
        f"/api/admin/portal/users/{other['user']['id']}/platform-role",
        headers=ADMIN,
        json={"platform_admin_role": "super"},
    )
    assert denied.status_code == 400
    store = session_auth._load_users()
    for user in store["users"]:
        if user.get("id") == other["user"]["id"]:
            user["platform_admin_role"] = "super"
    session_auth._save_users()
    me = client.get(
        "/api/admin/portal/me",
        headers={"Authorization": f"Bearer {other['token']}"},
    )
    assert me.status_code == 403

    dk = _register("dk@citealpha.com", org_name="Operator")
    granted = client.patch(
        f"/api/admin/portal/users/{dk['user']['id']}/platform-role",
        headers=ADMIN,
        json={"platform_admin_role": "super"},
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["platform_admin_role"] == "super"
    cleared = client.patch(
        f"/api/admin/portal/users/{dk['user']['id']}/platform-role",
        headers=ADMIN,
        json={"platform_admin_role": None},
    )
    assert cleared.status_code == 400


def test_super_assigns_support_role():
    super_user = _register("dk@citealpha.com", org_name="Operator")
    _grant_platform_role(ADMIN, super_user["user"]["id"], "super")
    super_token = super_user["token"]

    support = _register("support@ocotillo.test")
    assign = client.patch(
        f"/api/admin/portal/users/{support['user']['id']}/platform-role",
        headers={"Authorization": f"Bearer {super_token}"},
        json={"platform_admin_role": "support"},
    )
    assert assign.status_code == 200
    assert assign.json()["platform_admin_role"] == "support"

    stoken = support["token"]
    audit = client.get("/api/admin/portal/audit", headers={"Authorization": f"Bearer {stoken}"})
    assert audit.status_code == 200

    pilot = client.post(
        "/api/admin/portal/pilot",
        headers={"Authorization": f"Bearer {stoken}"},
        json={"name": "Should Fail"},
    )
    assert pilot.status_code == 403

    opened = client.post(
        "/api/orgs/pilot",
        headers=ADMIN,
        json={"name": "LTM", "owner_email": "owner@ltm.test", "term_days": 45},
    )
    assert opened.status_code == 200, opened.text
    invite = client.post(
        f"/api/admin/portal/orgs/{opened.json()['org']['id']}/owner-invite",
        headers={"Authorization": f"Bearer {stoken}"},
    )
    assert invite.status_code == 403


def test_super_sees_seats_and_deletes_user_org_and_pilot_request():
    from app.data.seed import get_data, save_data

    owner = _register("desk.owner@gmail.com", org_name="Desk Owner")
    org_id = owner["user"]["org_id"]
    user_id = owner["user"]["id"]

    listed = client.get("/api/admin/portal/orgs", headers=ADMIN)
    assert listed.status_code == 200
    row = next(o for o in listed.json()["orgs"] if o["id"] == org_id)
    assert row["members"][0]["email"] == "desk.owner@gmail.com"
    assert row["members"][0]["role"] == "owner"
    assert row["deletable"] is False

    occupied = client.delete(f"/api/admin/portal/orgs/{org_id}", headers=ADMIN)
    assert occupied.status_code == 409
    standing = client.delete("/api/admin/portal/orgs/demo", headers=ADMIN)
    assert standing.status_code == 400

    store = session_auth._load_users()
    for user in store["users"]:
        if user.get("id") == user_id:
            user["protected"] = True
    session_auth._save_users()
    refused = client.delete(f"/api/admin/portal/users/{user_id}", headers=ADMIN)
    assert refused.status_code == 400
    for user in session_auth._load_users()["users"]:
        if user.get("id") == user_id:
            user["protected"] = False
    session_auth._save_users()

    removed = client.delete(f"/api/admin/portal/users/{user_id}", headers=ADMIN)
    assert removed.status_code == 200, removed.text
    emails = {u.get("email") for u in session_auth._load_users()["users"]}
    assert "desk.owner@gmail.com" not in emails
    assert get_data()["orgs"][org_id]["seats_used"] == 0

    gone = client.delete(f"/api/admin/portal/orgs/{org_id}", headers=ADMIN)
    assert gone.status_code == 200, gone.text
    assert org_id not in get_data()["orgs"]
    assert "demo" in get_data()["orgs"]

    data = get_data()
    data["pilot_requests"] = [
        {
            "id": "pr_keeporg",
            "status": "approved",
            "email": "a@b.com",
            "firm": "Keep",
            "org_id": "demo",
        }
    ]
    save_data()
    deleted = client.delete("/api/admin/portal/pilot-requests/pr_keeporg", headers=ADMIN)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["org_id"] == "demo"
    assert "demo" in get_data()["orgs"]
    assert all(r.get("id") != "pr_keeporg" for r in get_data().get("pilot_requests") or [])
    missing = client.delete("/api/admin/portal/pilot-requests/pr_keeporg", headers=ADMIN)
    assert missing.status_code == 404


def test_ops_cannot_delete_users_and_super_cannot_delete_self():
    super_user = _register("admin.team@citealpha.com", org_name="Operator")
    _grant_platform_role(ADMIN, super_user["user"]["id"], "super")
    victim = _register("victim@gmail.com", org_name="Victim Desk")
    ops = _register("opsdel@ocotillo.test")
    _grant_platform_role(ADMIN, ops["user"]["id"], "ops")

    denied = client.delete(
        f"/api/admin/portal/users/{victim['user']['id']}",
        headers={"Authorization": f"Bearer {ops['token']}"},
    )
    assert denied.status_code == 403

    self_del = client.delete(
        f"/api/admin/portal/users/{super_user['user']['id']}",
        headers={"Authorization": f"Bearer {super_user['token']}"},
    )
    assert self_del.status_code == 400
    assert any(u.get("id") == super_user["user"]["id"] for u in session_auth._load_users()["users"])


def test_rotated_admin_key_disables_seeded_super_key(monkeypatch) -> None:
    monkeypatch.setenv("INTELLENS_API_KEY", "rotated-ops-key")
    rotated = {"X-API-Key": "rotated-ops-key"}

    assert client.get("/api/admin/portal/me", headers=ADMIN).status_code == 403
    assert client.get("/api/labeling/queue", headers=ADMIN).status_code == 403

    me = client.get("/api/admin/portal/me", headers=rotated)
    assert me.status_code == 200
    assert me.json()["platform_admin_role"] == "super"
    assert client.get("/api/labeling/queue", headers=rotated).status_code == 200
    assert client.get("/api/labeling/queue", headers={"X-API-Key": "intellens-demo"}).status_code == 200


def _role_token(email: str, role: str) -> str:
    user = _register(email)
    _grant_platform_role(ADMIN, user["user"]["id"], role)
    return user["token"]


def test_board_hides_coverage_from_support_and_counts_open_work(monkeypatch, tmp_path):
    from app.services import commitment_store, feedback, labeling_queue

    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    feedback.create(company_id="infy", kind="missing_source", comment="Quote missing", actor={"org_id": "demo"})
    labeling_queue.enqueue(company_id="infy", org_id="demo", note="manual")
    added = commitment_store.propose(
        [
            {
                "company_id": "infy",
                "type": "capacity",
                "subject": "Stub plant commissioning",
                "outcome": "Stub plant is commissioned",
                "due_period": "Q3 FY26",
                "quote": "We expect the stub plant to be commissioned in Q3 FY26.",
                "source_url": "https://example.invalid/stub-concall.pdf",
                "as_of": "2025-05-01",
            }
        ],
        proposed_by="labeler",
    )
    assert added["added"]

    support = _role_token("support.board@ocotillo.test", "support")
    board = client.get("/api/admin/portal/board", headers={"Authorization": f"Bearer {support}"})
    assert board.status_code == 200, board.text
    ids = {row["id"] for row in board.json()["rows"]}
    assert "coverage" not in ids
    assert "labeling" in ids
    labeling = next(row for row in board.json()["rows"] if row["id"] == "labeling")
    assert labeling["count"] >= 1
    commitments = next(row for row in board.json()["rows"] if row["id"] == "commitments")
    assert commitments["count"] == 1
    feedback_row = next(row for row in board.json()["rows"] if row["id"] == "feedback")
    assert feedback_row["count"] >= 1

    super_board = client.get("/api/admin/portal/board", headers=ADMIN)
    assert super_board.status_code == 200
    assert any(row["id"] == "coverage" for row in super_board.json()["rows"])
    me = client.get("/api/admin/portal/me", headers=ADMIN)
    section_ids = {row["id"] for row in me.json()["sections"]}
    assert {"labeling", "commitments", "reports", "system"} <= section_ids


def test_ops_cannot_clean_or_invoice_and_guest_cannot_read_board():
    ops = _role_token("ops.gap@ocotillo.test", "ops")
    headers = {"Authorization": f"Bearer {ops}"}
    assert client.post("/api/admin/portal/cleanup-test-tenants", headers=headers, json={"dry_run": True}).status_code == 403
    assert (
        client.post(
            "/api/admin/portal/billing/invoices",
            headers=headers,
            json={"org_id": "demo", "plan": "desk", "seats": 2},
        ).status_code
        == 403
    )
    plain = _register("plain.gap@ocotillo.test")
    denied = {"Authorization": f"Bearer {plain['token']}"}
    assert client.get("/api/admin/portal/board", headers=denied).status_code == 403
    assert client.get("/api/admin/portal/reports", headers=denied).status_code == 403
    assert client.get("/api/admin/portal/system", headers=denied).status_code == 403
    assert client.get("/api/admin/portal/labeling", headers=denied).status_code == 403


def test_super_invoice_reports_and_system_are_read_from_stores(monkeypatch, tmp_path):
    from app.services import gci_scoring
    from app.data import audit_log

    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    (tmp_path / "guidance_review_stamp.json").write_text(
        '{"date":"2026-10-24","market_id":"IN","bound_rows":3,"at":"2026-10-24T02:30:00+00:00"}',
        encoding="utf-8",
    )

    def _boom(*_args, **_kwargs):
        raise AssertionError("portal must not recompute a GCI")

    monkeypatch.setattr(gci_scoring, "compute_company_gci", _boom)

    created = client.post(
        "/api/admin/portal/billing/invoices",
        headers=ADMIN,
        json={"org_id": "demo", "plan": "desk", "seats": 3, "signer_email": "cfo@demo.test"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["esign_status"] == "signed"
    assert created.json()["org_id"] == "demo"
    missing = client.post(
        "/api/admin/portal/billing/invoices",
        headers=ADMIN,
        json={"org_id": "no-such-org", "seats": 1},
    )
    assert missing.status_code == 404

    catalog = client.get("/api/admin/portal/reports", headers=ADMIN)
    assert catalog.status_code == 200
    assert {row["id"] for row in catalog.json()["reports"]} == {
        "index",
        "coverage",
        "sla",
        "usage",
        "trust",
        "audit-events",
    }
    billing = _role_token("billing.gap@ocotillo.test", "billing")
    billing_headers = {"Authorization": f"Bearer {billing}"}
    assert client.get("/api/admin/portal/reports/usage", headers=billing_headers).status_code == 200
    assert client.get("/api/admin/portal/reports/index", headers=billing_headers).status_code == 200
    support = _role_token("support.usage@ocotillo.test", "support")
    assert (
        client.get("/api/admin/portal/reports/usage", headers={"Authorization": f"Bearer {support}"}).status_code
        == 403
    )

    index = client.get("/api/admin/portal/reports/index", headers=ADMIN)
    assert index.status_code == 200, index.text
    body = index.json()
    assert isinstance(body["published_companies"], int)
    assert isinstance(body["pending_guidance_cite"], int)
    assert "tiers" in body

    coverage = client.get("/api/admin/portal/reports/coverage", headers=ADMIN)
    assert coverage.status_code == 200
    assert "india" in coverage.json() and "us" in coverage.json()

    audit_path = tmp_path / "audit.json"
    audit_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(audit_log, "_PATH", audit_path)
    monkeypatch.setattr(audit_log, "_LOG", None)
    audit_log.record("login", org="demo", actor="tester", detail={"password": "secret-value", "method": "session"})
    events = client.get("/api/admin/portal/reports/audit-events", headers=ADMIN)
    assert events.status_code == 200
    dumped = events.text
    assert "secret-value" not in dumped
    assert "session" in dumped
    csv_body = client.get("/api/admin/portal/reports/audit-events?format=csv", headers=ADMIN)
    assert csv_body.status_code == 200
    assert "secret-value" not in csv_body.text
    assert csv_body.text.startswith("ts,action,org,actor,role,detail")

    system = client.get("/api/admin/portal/system", headers=ADMIN)
    assert system.status_code == 200, system.text
    status = system.json()
    assert status["guidance_review"]["market_id"] == "IN"
    assert status["guidance_review"]["date"] == "2026-10-24"
    assert "monitors" in status and "flags" in status
    assert all("INTELLENS" not in row["id"] and "INTELLENS" not in row["label"] for row in status["flags"])
    assert any(row["id"] == "guidance_review" for row in status["flags"])

    labeling = client.get("/api/admin/portal/labeling", headers=ADMIN)
    assert labeling.status_code == 200
    assert "note" in labeling.json()
    commitments = client.get("/api/admin/portal/commitments", headers=ADMIN)
    assert commitments.status_code == 200
    assert "items" in commitments.json()
