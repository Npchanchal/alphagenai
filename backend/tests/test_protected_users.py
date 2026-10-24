"""Protected team accounts: created on start, repaired after tampering, not revocable by org admins."""

from fastapi.testclient import TestClient

from app.data.seed import get_data, reset_data
from app.main import app
from app.services import session_auth
from app.services.entitlements import resolve_from_user
from app.services.protected_users import ensure_protected_users, load_manifest
from app.services.session_auth import reset_auth_store

client = TestClient(app)
PASSWORD = "Magicpot@189"
ORG = "citealpha-team"


def setup_function() -> None:
    reset_auth_store()
    reset_data()


def _login(email: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _email(role: str) -> str:
    return next(u["email"] for u in load_manifest()["users"] if u["role"] == role)


def test_creates_every_role_and_password_works():
    res = ensure_protected_users()
    assert len(res["created"]) == len(load_manifest()["users"]) == 6
    for spec in load_manifest()["users"]:
        r = _login(spec["email"])
        assert r.status_code == 200, spec["email"]
        assert r.json()["user"]["role"] == spec["role"]
        assert r.json()["user"]["org_id"] == ORG
    org = get_data()["orgs"][ORG]
    assert org["seats_used"] == 6 and org["plan"] == "desk"


def test_roles_get_the_features_this_work_needs():
    ensure_protected_users()
    users = {u["role"]: u for u in session_auth._load_users()["users"] if u.get("org_id") == ORG}
    feats = {r: set(resolve_from_user(u)["features"]) for r, u in users.items()}
    assert "analyst_agent" in feats["analyst"] and "labeling" not in feats["analyst"]
    assert {"analyst_agent", "labeling"} <= feats["reviewer"]
    assert "labeling" in feats["labeler"] and "analyst_agent" not in feats["labeler"]
    assert {"analyst_agent", "labeling"} <= feats["admin"] and {"analyst_agent", "labeling"} <= feats["owner"]
    assert "analyst_agent" not in feats["viewer"]


def test_team_admin_keeps_platform_super():
    ensure_protected_users()
    user = session_auth._find_by_email(_email("admin"))
    assert user["platform_admin_role"] == "super"
    user.pop("platform_admin_role")
    session_auth._save_users()
    assert _email("admin") in ensure_protected_users()["repaired"]
    assert session_auth._find_by_email(_email("admin"))["platform_admin_role"] == "super"


def test_idempotent():
    ensure_protected_users()
    again = ensure_protected_users()
    assert again["created"] == [] and again["repaired"] == []
    assert sum(1 for u in session_auth._load_users()["users"] if u.get("org_id") == ORG) == 6


def test_repairs_deactivated_or_changed_account_but_keeps_changed_password():
    ensure_protected_users()
    user = session_auth._find_by_email(_email("analyst"))
    user["active"] = False
    user["role"] = "viewer"
    hashed = session_auth._hash_password("a-new-password-1")
    user["password_salt"], user["password_hash"] = hashed["salt"], hashed["hash"]
    session_auth._save_users()

    res = ensure_protected_users()
    assert res["repaired"] == [_email("analyst")]
    assert _login(_email("analyst"), "a-new-password-1").json()["user"]["role"] == "analyst"
    assert _login(_email("analyst")).status_code == 401


def test_team_accounts_open_on_india_once_then_keep_user_choice():
    ensure_protected_users()
    user = session_auth._find_by_email(_email("admin"))
    assert user["preferences"]["default_market"] == "IN"
    user["preferences"].update(default_market="US", default_index="DJI")
    user.pop("protected_universe_version")
    session_auth._save_users()

    assert _email("admin") in ensure_protected_users()["repaired"]
    user = session_auth._find_by_email(_email("admin"))
    assert (user["preferences"]["default_market"], user["preferences"]["default_index"]) == ("IN", "SENSEX")

    user["preferences"]["default_market"] = "US"
    session_auth._save_users()
    assert ensure_protected_users()["repaired"] == []
    assert session_auth._find_by_email(_email("admin"))["preferences"]["default_market"] == "US"


def test_recreated_after_auth_store_wipe():
    ensure_protected_users()
    reset_auth_store()
    ensure_protected_users()
    assert _login(_email("reviewer")).status_code == 200


def test_org_admin_cannot_revoke_or_change_role():
    ensure_protected_users()
    token = _login(_email("owner")).json()["token"]
    target = session_auth._find_by_email(_email("viewer"))["id"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/api/orgs/{ORG}/revoke", headers=h, json={"user_id": target}).status_code == 400
    assert _login(_email("viewer")).status_code == 200


def test_does_not_hijack_email_registered_elsewhere():
    reg = client.post("/api/auth/register", json={
        "email": _email("labeler"), "password": "someone-elses-pw", "name": "X",
        "accept_terms": True, "account_type": "b2b", "org_name": "Other Desk",
    })
    assert reg.status_code == 200
    res = ensure_protected_users()
    assert res["skipped"] == [_email("labeler")]
    assert _login(_email("labeler"), "someone-elses-pw").json()["user"]["org_id"] != ORG
