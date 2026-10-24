import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchMyOrg,
  fetchOrgMembers,
  postMemberRole,
  postOrgApiKey,
  postOrgInvite,
  postOrgRevoke,
  postPartnerInvite,
  type AuthUser,
  type OrgPayload,
} from "../lib/api";
import { useAuth } from "../lib/auth";

const WORKING_ROLES = ["viewer", "analyst", "labeler", "reviewer"] as const;

/** B2B seat admin — invite / revoke / mint API key. */
export default function OrgAdminPanel() {
  const { user, token } = useAuth();
  const [members, setMembers] = useState<AuthUser[]>([]);
  const [desk, setDesk] = useState<OrgPayload | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("analyst");
  const [partnerEmail, setPartnerEmail] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);

  const orgId = user?.org_id;
  const canAdmin = user?.role === "owner" || user?.role === "admin";
  const isOwner = user?.role === "owner";
  const assignable = isOwner ? [...WORKING_ROLES, "admin"] : [...WORKING_ROLES];

  const reload = useCallback(async () => {
    if (!orgId || !token) return;
    const [res, snap] = await Promise.all([
      fetchOrgMembers(orgId, token),
      fetchMyOrg(token).catch(() => null),
    ]);
    setMembers(res.members);
    setDesk(snap);
  }, [orgId, token]);

  useEffect(() => {
    void reload().catch(() => setMembers([]));
  }, [reload]);

  useEffect(() => {
    if (!isOwner && role === "admin") setRole("analyst");
  }, [isOwner, role]);

  if (!user || user.kind === "guest" || !orgId) {
    return (
      <p className="muted">
        Register a B2B desk account to manage seats. Guests and retail users have personal
        tenants without shared invites.
      </p>
    );
  }

  if (!canAdmin) {
    return (
      <p className="muted">
        Signed in as {user.email} ({user.role}) on org <code>{orgId}</code>. Ask an owner or
        admin to invite or revoke seats. Only the organisation owner can appoint an admin.
      </p>
    );
  }

  async function onInvite(e: FormEvent) {
    e.preventDefault();
    if (!token || !orgId) return;
    setError(null);
    setMsg(null);
    try {
      const res = await postOrgInvite(orgId, token, email, role);
      setMsg(
        res.dev_token
          ? `Invite sent (dev token: ${res.dev_token})`
          : `Invite queued (${res.mail_status || "ok"})`,
      );
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    }
  }

  return (
    <div className="org-admin" data-testid="org-admin-panel">
      <h3 style={{ marginTop: 0 }}>Seat administration</h3>
      <p className="muted">
        Org <code>{orgId}</code>
        {desk?.plan ? ` · ${desk.plan}` : ""}
        {desk?.seats != null
          ? ` · ${desk.seats_used ?? 0} of ${desk.seats} seats in use`
          : ""}
        . Invite consumes a seat on accept. Revoke frees a seat.
        {isOwner
          ? " You can appoint an admin."
          : " Only the organisation owner can appoint or remove an admin."}
      </p>
      <form className="auth-form" onSubmit={onInvite} style={{ maxWidth: 420 }}>
        <label>
          Invite email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            data-testid="org-invite-email"
          />
        </label>
        <label>
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            data-testid="org-invite-role"
          >
            {assignable.map((seat) => (
              <option key={seat} value={seat}>
                {seat}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn-primary" data-testid="org-invite-submit">
          Send invite
        </button>
      </form>
      <form
        className="auth-form"
        style={{ maxWidth: 420 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!token || !orgId) return;
          void postPartnerInvite(orgId, token, partnerEmail)
            .then((res) => {
              setMsg(
                res.dev_token
                  ? `Partner invite (dev token: ${res.dev_token})`
                  : "Partner invite queued",
              );
              setPartnerEmail("");
            })
            .catch((err) => setError(err instanceof Error ? err.message : "Invite failed"));
        }}
      >
        <label>
          Design-partner email (viewer + feedback, 60-day)
          <input
            type="email"
            required
            value={partnerEmail}
            onChange={(e) => setPartnerEmail(e.target.value)}
          />
        </label>
        <button type="submit" className="btn">
          Invite design partner
        </button>
      </form>
      {msg && <p className="muted">{msg}</p>}
      {error && <p className="error">{error}</p>}
      <ul className="org-member-list">
        {members.map((m) => (
          <li key={m.id}>
            <span>
              {m.email || m.name} · {m.role}
              {m.active === false ? " · revoked" : ""}
              {m.email_verified ? " · verified" : " · unverified"}
            </span>
            {m.role !== "owner" && m.active !== false && (isOwner || m.role !== "admin") && (
              <select
                value={m.role || "viewer"}
                onChange={(e) => {
                  if (!token) return;
                  void postMemberRole(orgId, token, m.id, e.target.value)
                    .then(() => reload())
                    .catch((err) =>
                      setError(err instanceof Error ? err.message : "Role update failed"),
                    );
                }}
                aria-label={`Role for ${m.email || m.name}`}
              >
                {assignable.map((seat) => (
                  <option key={seat} value={seat}>
                    {seat}
                  </option>
                ))}
              </select>
            )}
            {m.role !== "owner" && m.active !== false && (isOwner || m.role !== "admin") && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  if (!token) return;
                  void postOrgRevoke(orgId, token, m.id)
                    .then(() => reload())
                    .catch((err) =>
                      setError(err instanceof Error ? err.message : "Revoke failed"),
                    );
                }}
              >
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="btn"
        onClick={() => {
          if (!token) return;
          void postOrgApiKey(orgId, token)
            .then((r) => setApiKey(r.api_key))
            .catch((err) => setError(err instanceof Error ? err.message : "Key mint failed"));
        }}
      >
        Mint org API key
      </button>
      {apiKey && (
        <p className="muted">
          New key (copy now): <code data-testid="org-api-key">{apiKey}</code>
        </p>
      )}
    </div>
  );
}
