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
import { SEAT_COPY } from "../lib/seatLanding";

const WORKING_ROLES = ["viewer", "pm", "data", "ir", "oversight", "analyst", "labeler", "reviewer"] as const;

function seatLabel(id: string): string {
  return SEAT_COPY[id]?.label || id;
}

function friendly(err: unknown, fallback: string): string {
  const msg = err instanceof Error ? err.message : fallback;
  if (/protected team|kept for the citealpha team/i.test(msg)) {
    return "This account is kept for the CiteAlpha team.";
  }
  return msg || fallback;
}

function useDeskAdmin() {
  const { user, token } = useAuth();
  const [members, setMembers] = useState<AuthUser[]>([]);
  const [desk, setDesk] = useState<OrgPayload | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const orgId = user?.org_id;
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
    void reload().catch((err) => setError(friendly(err, "Could not load seats")));
  }, [reload]);

  return {
    user,
    token,
    orgId,
    isOwner,
    assignable,
    members,
    desk,
    msg,
    setMsg,
    error,
    setError,
    reload,
  };
}

function Notices({ msg, error }: { msg: string | null; error: string | null }) {
  return (
    <>
      {msg && <p className="muted">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </>
  );
}

export function OrgMembersPanel() {
  const { token, orgId, isOwner, assignable, members, desk, msg, setMsg, error, setError, reload } =
    useDeskAdmin();

  return (
    <div data-testid="org-members">
      <h2 style={{ marginTop: 0 }}>Members</h2>
      <p className="muted">
        {desk?.seats != null
          ? `${desk.seats_used ?? 0} of ${desk.seats} seats in use. `
          : ""}
        Revoke frees a seat.
        {isOwner
          ? " You can appoint an admin."
          : " Only the organisation owner can appoint or remove an admin."}
      </p>
      <Notices msg={msg} error={error} />
      <ul className="org-member-list">
        {members.map((m) => {
          const canEdit =
            !m.protected &&
            m.role !== "owner" &&
            m.active !== false &&
            (isOwner || m.role !== "admin");
          return (
            <li key={m.id}>
              <span>
                {m.email || m.name} · {seatLabel(m.role || "viewer")}
                {m.active === false ? " · revoked" : ""}
                {m.email_verified ? " · verified" : " · unverified"}
              </span>
              {canEdit && (
                <select
                  value={m.role || "viewer"}
                  aria-label={`Role for ${m.email || m.name}`}
                  onChange={(e) => {
                    if (!token || !orgId) return;
                    setError(null);
                    void postMemberRole(orgId, token, m.id, e.target.value)
                      .then(() => reload())
                      .catch((err) => setError(friendly(err, "Role update failed")));
                  }}
                >
                  {assignable.map((seat) => (
                    <option key={seat} value={seat}>
                      {seatLabel(seat)}
                    </option>
                  ))}
                </select>
              )}
              {canEdit && m.role === "ir" && (
                <label>
                  Companies this seat may pack
                  <input
                    aria-label={`Companies for ${m.email || m.name}`}
                    defaultValue={(m.company_scope || []).join(", ")}
                    placeholder="infy"
                    onBlur={(e) => {
                      if (!token || !orgId) return;
                      const scope = e.target.value
                        .split(/[,\s]+/)
                        .map((id) => id.trim().toLowerCase())
                        .filter(Boolean);
                      setError(null);
                      void postMemberRole(orgId, token, m.id, "ir", scope)
                        .then(() => reload())
                        .catch((err) => setError(friendly(err, "Company list failed")));
                    }}
                  />
                  {(m.company_scope || []).length === 0 ? (
                    <span className="muted"> No company named yet</span>
                  ) : null}
                </label>
              )}
              {canEdit && (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    if (!token || !orgId) return;
                    setError(null);
                    void postOrgRevoke(orgId, token, m.id)
                      .then(() => {
                        setMsg("Seat freed.");
                        return reload();
                      })
                      .catch((err) => setError(friendly(err, "Revoke failed")));
                  }}
                >
                  Revoke
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function OrgInvitesPanel() {
  const { token, orgId, isOwner, assignable, desk, msg, setMsg, error, setError } = useDeskAdmin();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("analyst");

  useEffect(() => {
    if (!isOwner && role === "admin") setRole("analyst");
  }, [isOwner, role]);

  async function onInvite(e: FormEvent) {
    e.preventDefault();
    if (!token || !orgId) return;
    setError(null);
    setMsg(null);
    try {
      const res = await postOrgInvite(orgId, token, email, role);
      setMsg(
        res.dev_token
          ? `Invite sent. Dev link token: ${res.dev_token}`
          : res.mail_status && res.mail_status !== "ok" && res.mail_status !== "sent"
            ? `Mail status: ${res.mail_status}`
            : "Invite queued. A seat is taken when they accept.",
      );
      setEmail("");
    } catch (err) {
      setError(friendly(err, "Invite failed"));
    }
  }

  const available = desk?.seats_available;
  return (
    <div data-testid="org-invites">
      <h2 style={{ marginTop: 0 }}>Invites</h2>
      <p className="muted">
        {available != null ? `${available} seat${available === 1 ? "" : "s"} available. ` : ""}
        A seat is taken when the invite is accepted, not when it is sent. Send again to the same
        address if the message did not arrive.
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
                {seatLabel(seat)}
              </option>
            ))}
          </select>
          {SEAT_COPY[role]?.sentence ? <p className="muted">{SEAT_COPY[role].sentence}</p> : null}
        </label>
        <button type="submit" className="btn-primary" data-testid="org-invite-submit">
          Send invite
        </button>
      </form>
      <Notices msg={msg} error={error} />
    </div>
  );
}

export function OrgPartnersPanel() {
  const { token, orgId, msg, setMsg, error, setError } = useDeskAdmin();
  const [email, setEmail] = useState("");

  return (
    <div data-testid="org-partners">
      <h2 style={{ marginTop: 0 }}>Design partners</h2>
      <p className="muted">
        A design partner joins as a viewer with feedback, for 60 days. This is not a working seat
        role.
      </p>
      <form
        className="auth-form"
        style={{ maxWidth: 420 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!token || !orgId) return;
          setError(null);
          void postPartnerInvite(orgId, token, email)
            .then((res) => {
              setMsg(
                res.dev_token
                  ? `Design partner invite sent. Dev link token: ${res.dev_token}`
                  : "Design partner invite queued.",
              );
              setEmail("");
            })
            .catch((err) => setError(friendly(err, "Invite failed")));
        }}
      >
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            data-testid="org-partner-email"
          />
        </label>
        <button type="submit" className="btn-primary">
          Invite design partner
        </button>
      </form>
      <Notices msg={msg} error={error} />
    </div>
  );
}

export function OrgDeskKeyPanel() {
  const { token, orgId, error, setError } = useDeskAdmin();
  const [apiKey, setApiKey] = useState<string | null>(null);

  return (
    <div data-testid="org-desk-key">
      <h3>Desk key</h3>
      <p className="muted">
        This key is for Workbench write paths on this organisation. It is not an Analyst key. Copy
        it now; it is shown once.
      </p>
      <button
        type="button"
        className="btn"
        onClick={() => {
          if (!token || !orgId) return;
          setError(null);
          void postOrgApiKey(orgId, token)
            .then((r) => setApiKey(r.api_key))
            .catch((err) => setError(friendly(err, "Key mint failed")));
        }}
      >
        Mint desk key
      </button>
      {apiKey && (
        <p className="muted">
          New key (copy now): <code data-testid="org-api-key">{apiKey}</code>
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
