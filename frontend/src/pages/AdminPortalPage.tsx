import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CoverageEditor from "../components/CoverageEditor";
import Skeleton from "../components/Skeleton";
import { PLATFORM_SUPER_EMAILS } from "../lib/platformRole";
import {
  fetchAdminPortalAudit,
  fetchAdminPortalBilling,
  fetchAdminPortalBoard,
  fetchAdminPortalCommitments,
  fetchAdminPortalFeedback,
  fetchAdminPortalLabeling,
  fetchAdminPortalLegal,
  fetchAdminPortalMe,
  fetchAdminPortalOrgs,
  fetchMarkets,
  putAdminPortalOrgCoverage,
  type CoverageUnit,
  fetchAdminPortalPilotRequests,
  fetchAdminPortalReport,
  fetchAdminPortalReportCatalog,
  fetchAdminPortalSystem,
  deleteAdminPortalOrg,
  deleteAdminPortalPilotRequest,
  deleteAdminPortalUser,
  fetchAdminPortalUsers,
  patchAdminPortalFeedback,
  patchAdminPortalPilotRequest,
  patchAdminPortalUserRole,
  postAdminPortalCleanup,
  postAdminPortalInvoice,
  postAdminPortalLegalAttest,
  postAdminPortalOwnerInvite,
  postAdminPortalPilot,
  type AdminBoardRow,
  type AdminCommitmentItem,
  type AdminLabelingView,
  type AdminPortalMe,
  type AdminPortalUser,
  type AdminReportMeta,
  type AdminSystemStatus,
  type FeedbackItem,
  type OrgPayload,
  type OrgSeat,
  type PilotRequestItem,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { LEGAL_ENTITY } from "../lib/legal";

const PLATFORM_ROLES = ["super", "ops", "compliance", "billing", "support"] as const;

/** Grant lists sent with a pilot approval; comma-joined so a select can hold them. */
const PILOT_COVERAGE = [
  { id: "IN", label: "India" },
  { id: "IN:NSE", label: "India · NSE only" },
  { id: "IN:BSE", label: "India · BSE only" },
  { id: "US", label: "United States" },
  { id: "IN,US", label: "India and United States" },
  { id: "*", label: "All markets" },
];

function approvePilotMessage(result: {
  request: PilotRequestItem;
  owner_invite?: PilotRequestItem["owner_invite"];
}): string {
  const orgId = result.request.org_id;
  if (!orgId) return "Pilot request approved";
  const mail = result.owner_invite?.mail_status;
  const email = result.owner_invite?.email || result.request.email;
  if (mail === "sent") return `Approved ${orgId}. Invite sent to ${email}.`;
  if (mail === "stubbed") {
    return `Approved ${orgId}. Mail is not configured, so ${email} did not receive the link.`;
  }
  const detail = result.owner_invite?.detail;
  if (detail) return `Approved ${orgId}. Invite was not sent: ${detail}`;
  return `Approved ${orgId}. Invite mail status: ${mail || "unknown"}.`;
}

function SeatRow({
  member,
  orgName,
  canRemove,
  onRemove,
}: {
  member: OrgSeat;
  orgName: string;
  canRemove: boolean;
  onRemove: () => void;
}) {
  const who = member.email || member.name || member.id;
  return (
    <li>
      <span>{who}</span>
      <span className="muted">{member.role || "member"}</span>
      {member.active === false ? <span className="muted">inactive</span> : null}
      {member.platform_admin_role ? <span className="muted">{member.platform_admin_role}</span> : null}
      {member.protected ? <span className="muted">Standing account</span> : null}
      {canRemove ? (
        <button
          type="button"
          className="admin-delete"
          data-testid={`admin-remove-seat-${member.id}`}
          aria-label={`Remove ${who} from ${orgName}`}
          onClick={onRemove}
        >
          Remove seat
        </button>
      ) : null}
    </li>
  );
}

function AdminGate({
  title,
  children,
  testId,
}: {
  title: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <section className="admin-portal-page admin-portal-gate" data-testid={testId}>
      <p className="page-kicker">Operations</p>
      <h1>{title}</h1>
      <div className="panel desk-panel admin-portal-gate-panel">{children}</div>
    </section>
  );
}

export default function AdminPortalPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [portal, setPortal] = useState<AdminPortalMe | null>(null);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgs, setOrgs] = useState<OrgPayload[]>([]);
  const [users, setUsers] = useState<AdminPortalUser[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [legal, setLegal] = useState<Record<string, unknown> | null>(null);
  const [billing, setBilling] = useState<Record<string, unknown>[]>([]);
  const [audit, setAudit] = useState<Record<string, number> | null>(null);
  const [pilotRequests, setPilotRequests] = useState<PilotRequestItem[]>([]);
  const [board, setBoard] = useState<AdminBoardRow[]>([]);
  const [labeling, setLabeling] = useState<AdminLabelingView | null>(null);
  const [commitments, setCommitments] = useState<AdminCommitmentItem[]>([]);
  const [commitmentNote, setCommitmentNote] = useState("");
  const [reports, setReports] = useState<AdminReportMeta[]>([]);
  const [reportId, setReportId] = useState("");
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [reportDenied, setReportDenied] = useState(false);
  const [system, setSystem] = useState<AdminSystemStatus | null>(null);
  const [cleanupPreview, setCleanupPreview] = useState<{ users_removed: string[]; orgs_removed: string[] } | null>(null);
  const [standingOnly, setStandingOnly] = useState(false);
  const [invoiceOrg, setInvoiceOrg] = useState("demo");
  const [invoicePlan, setInvoicePlan] = useState("desk");
  const [invoiceSeats, setInvoiceSeats] = useState(5);
  const [invoiceSigner, setInvoiceSigner] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pilotName, setPilotName] = useState("New Pilot Desk");
  const [pilotTerm, setPilotTerm] = useState<30 | 45 | 60>(45);
  const [pilotCoverage, setPilotCoverage] = useState(PILOT_COVERAGE[0].id);
  const [coverageUnits, setCoverageUnits] = useState<CoverageUnit[]>([]);
  const [attestBy, setAttestBy] = useState("counsel@firm.com");
  const [attestKind, setAttestKind] = useState("terms_privacy");

  const section = searchParams.get("section") || "overview";
  const reportParam = searchParams.get("report") || "";
  const can = useCallback(
    (perm: string) => (portal?.permissions || []).includes(perm),
    [portal?.permissions],
  );

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      setLoading(false);
      setPortal(null);
      setAccessError(null);
      return;
    }
    setLoading(true);
    void fetchAdminPortalMe(token)
      .then((row) => {
        setPortal(row);
        setAccessError(null);
      })
      .catch((e) => {
        setPortal(null);
        setAccessError((e as Error).message || "Platform admin access required");
      })
      .finally(() => setLoading(false));
  }, [token, authLoading]);

  const loadSection = useCallback(async () => {
    if (!token || !portal) return;
    const allowed = new Set((portal.sections || []).map((s) => s.id));
    if (!allowed.has(section)) return;
    setErr(null);
    try {
      if (section === "orgs" && can("orgs.read")) {
        const res = await fetchAdminPortalOrgs(token);
        setOrgs(res.orgs || []);
        if (can("billing.write")) {
          fetchMarkets()
            .then((m) => setCoverageUnits(m.coverage_units || []))
            .catch(() => undefined);
        }
      }
      if (section === "users" && can("users.read")) {
        const res = await fetchAdminPortalUsers(token);
        setUsers(res.users || []);
      }
      if (section === "feedback" && can("feedback.read")) {
        const res = await fetchAdminPortalFeedback(token);
        setFeedback(res.items || []);
      }
      if (section === "legal" && can("legal.read")) {
        setLegal(await fetchAdminPortalLegal(token));
      }
      if (section === "billing" && can("billing.read")) {
        const res = await fetchAdminPortalBilling(token);
        setBilling(res.invoices || []);
      }
      if (section === "audit" && can("audit.read")) {
        setAudit(await fetchAdminPortalAudit(token));
      }
      if (section === "pilot-requests" && can("pilot.manage")) {
        const res = await fetchAdminPortalPilotRequests(undefined, token);
        setPilotRequests(res.items || []);
      }
      if (section === "overview") {
        const res = await fetchAdminPortalBoard(token);
        setBoard(res.rows || []);
      }
      if (section === "labeling" && can("audit.read")) {
        setLabeling(await fetchAdminPortalLabeling(token));
      }
      if (section === "commitments" && can("audit.read")) {
        const res = await fetchAdminPortalCommitments(token);
        setCommitments(res.items || []);
        setCommitmentNote(res.note || "");
      }
      if (section === "reports" && (can("audit.read") || can("billing.read") || can("legal.read"))) {
        const res = await fetchAdminPortalReportCatalog(token);
        setReports(res.reports || []);
      }
      if (section === "billing" && can("orgs.read") && orgs.length === 0) {
        const res = await fetchAdminPortalOrgs(token);
        setOrgs(res.orgs || []);
      }
      if (section === "system" && can("system.ops")) {
        setSystem(await fetchAdminPortalSystem(token));
      }
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [token, portal, section, can]);

  useEffect(() => {
    void loadSection();
  }, [loadSection]);

  useEffect(() => {
    if (!token || section !== "reports") return;
    if (!reportParam) {
      setReportDenied(false);
      return;
    }
    if (reports.length === 0) return;
    if (!reports.some((item) => item.id === reportParam)) {
      setReport(null);
      setReportId("");
      setReportDenied(true);
      return;
    }
    setReportDenied(false);
    setReportId(reportParam);
    void fetchAdminPortalReport(reportParam, token)
      .then((body) => setReport(body))
      .catch((ex) => setErr((ex as Error).message));
  }, [token, section, reportParam, reports]);

  const sections = useMemo(() => portal?.sections || [], [portal?.sections]);

  if (authLoading || (token && loading)) {
    return (
      <section className="admin-portal-page" data-testid="admin-portal-loading">
        <p className="page-kicker">Operations</p>
        <h1>Platform admin portal</h1>
        <div className="panel desk-panel">
          <Skeleton rows={4} />
        </div>
      </section>
    );
  }

  if (!token) {
    return (
      <AdminGate title="Platform admin portal" testId="admin-portal-signin">
        <p className="muted lede">
          Cross-tenant operations for {LEGAL_ENTITY}: organisations, users, legal attestations,
          billing, and partner feedback. Organisation administration does not unlock this portal.
        </p>
        <div className="admin-portal-cta row gap">
          <Link to="/login" state={{ from: "/admin" }} className="btn-primary">
            Sign in
          </Link>
          <Link to="/register" className="btn">
            Register
          </Link>
          <Link to="/desk" className="btn-ghost">
            Back to Desk
          </Link>
        </div>
        <p className="muted" style={{ fontSize: 13, marginTop: "1rem" }}>
          Need access? Ask a <code>super</code> admin to assign a platform role after you
          register.
        </p>
      </AdminGate>
    );
  }

  if (accessError || !portal) {
    return (
      <AdminGate title="Access denied" testId="admin-access-denied">
        <p className="error">{accessError || "Platform admin access required"}</p>
        <p className="muted">
          Signed in as <strong>{user?.email || user?.name}</strong> (organisation role{" "}
          <code>{user?.role || "—"}</code>). An organisation admin does not unlock this portal.
        </p>
        <ul className="admin-steps muted">
          <li>
            Request a platform role: <code>super</code>, <code>ops</code>,{" "}
            <code>compliance</code>, <code>billing</code>, or <code>support</code>.
          </li>
          <li>
            A <code>super</code> admin assigns it via Users → Platform admin, or{" "}
            <code>PATCH /api/admin/portal/users/&#123;id&#125;/platform-role</code>.
          </li>
          <li>Demo bootstrap: <code>X-API-Key: intellens-admin</code> (local only).</li>
        </ul>
        <div className="admin-portal-cta row gap">
          <Link to="/desk" className="btn-primary">
            Open Desk
          </Link>
          <Link to="/help" className="btn-ghost">
            Help
          </Link>
        </div>
      </AdminGate>
    );
  }

  return (
    <section className="admin-portal-page" data-testid="admin-portal">
      <header className="admin-portal-head">
        <div>
          <p className="page-kicker">Operations</p>
          <h1>Platform admin portal</h1>
          <p className="muted lede">
            Role <strong>{portal.platform_admin_role}</strong>
            {portal.email ? ` · ${portal.email}` : ""}
            {" · "}
            {LEGAL_ENTITY}
          </p>
        </div>
        <Link to="/desk" className="btn-ghost">
          Desk
        </Link>
      </header>

      <div className="admin-portal-layout">
        <div className="admin-portal-main panel desk-panel">
          {msg && <p className="muted admin-flash">{msg}</p>}
          {err && <p className="error">{err}</p>}

          {!sections.some((s) => s.id === section) && (
            <div data-testid="admin-section-denied">
              <h2 style={{ marginTop: 0 }}>This section is not open for your role</h2>
              <p className="muted">The platform menu lists the sections this role can open.</p>
              <button
                type="button"
                className="btn"
                onClick={() => setSearchParams({ section: sections[0]?.id || "overview" })}
              >
                Back to {sections[0]?.label || "Board"}
              </button>
            </div>
          )}

          {sections.some((s) => s.id === section) && section === "overview" && (
            <div data-testid="admin-section-overview">
              <h2 style={{ marginTop: 0 }}>Work board</h2>
              <p className="muted">Queues waiting on an operator. A row appears only when this role can open it.</p>
              {board.length === 0 ? (
                <p className="muted">No queues for this role.</p>
              ) : (
                <table className="admin-table" data-testid="admin-board">
                  <thead>
                    <tr>
                      <th>Queue</th>
                      <th>Count</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {board.map((row) => (
                      <tr key={row.id}>
                        <td>{row.label}</td>
                        <td>
                          {row.count}
                          {row.running ? " · in progress" : ""}
                        </td>
                        <td>
                          <button type="button" className="btn-ghost" onClick={() => setSearchParams({ section: row.section })}>
                            Open
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <h3>Permissions</h3>
              <ul className="admin-perm-list">
                {(portal.permissions || []).map((p) => (
                  <li key={p}>
                    <code>{p}</code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {section === "orgs" && can("orgs.read") && (
            <div data-testid="admin-section-orgs">
              <h2 style={{ marginTop: 0 }}>Organizations</h2>
              <p className="muted">
                Seat holders are the logins on that desk. A recorded owner with no login has not taken a seat yet.
                Delete an organisation only after its seats are empty. Standing CiteAlpha desks stay.
              </p>
              {can("pilot.manage") && (
                <form
                  className="admin-inline-form"
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    if (!token) return;
                    void postAdminPortalPilot(pilotName, pilotTerm, token)
                      .then((r) => {
                        setMsg(`Pilot provisioned: ${String(r.org_id || r.id || "ok")}`);
                        return fetchAdminPortalOrgs(token);
                      })
                      .then((res) => setOrgs(res.orgs || []))
                      .catch((ex) => setErr((ex as Error).message));
                  }}
                >
                  <input
                    value={pilotName}
                    onChange={(e) => setPilotName(e.target.value)}
                    placeholder="Pilot org name"
                    aria-label="Pilot org name"
                  />
                  <select
                    aria-label="Evaluation length"
                    value={pilotTerm}
                    onChange={(e) => setPilotTerm(Number(e.target.value) as 30 | 45 | 60)}
                  >
                    <option value={30}>30 days</option>
                    <option value={45}>45 days</option>
                    <option value={60}>60 days</option>
                  </select>
                  <button type="submit" className="btn-primary">
                    Provision pilot
                  </button>
                </form>
              )}
              {orgs.length === 0 ? (
                <p className="muted">No organizations found.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Organisation</th>
                      <th>Plan</th>
                      <th>Markets</th>
                      <th>Seats</th>
                      <th>Seat holders</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orgs.map((o) => {
                      const members = o.members || [];
                      const ownerEmail = String(o.owner_email || "").trim();
                      const ownerSeated = members.some(
                        (m) => (m.email || "").toLowerCase() === ownerEmail.toLowerCase(),
                      );
                      return (
                        <tr key={String(o.id)} data-testid={`admin-org-${o.id}`}>
                          <td>
                            <div>{o.name}</div>
                            <code>{String(o.id)}</code>
                          </td>
                          <td>{o.plan}</td>
                          <td data-testid={`admin-org-coverage-${o.id}`}>
                            <div>{o.coverage?.label ?? "—"}</div>
                            {can("billing.write") && token && coverageUnits.length > 0 ? (
                              <CoverageEditor
                                units={coverageUnits}
                                grants={o.coverage?.grants ?? []}
                                testId={`admin-org-coverage-edit-${o.id}`}
                                onSave={(grants) =>
                                  putAdminPortalOrgCoverage(String(o.id), grants, token)
                                    .then((updated) => {
                                      setOrgs((prev) => prev.map((x) => (x.id === o.id ? { ...x, ...updated } : x)));
                                      setMsg(`Markets for ${o.name || o.id}: ${updated.coverage?.label ?? "saved"}`);
                                    })
                                    .catch((ex) => setErr((ex as Error).message))
                                }
                              />
                            ) : null}
                          </td>
                          <td>
                            {o.seats_used ?? 0}/{o.seats ?? "—"}
                          </td>
                          <td data-testid={`admin-org-seats-${o.id}`}>
                            {members.length === 0 ? (
                              <span className="muted">
                                {ownerEmail
                                  ? `No login yet. Recorded owner ${ownerEmail}.`
                                  : "No seat allocated."}
                                {o.owner_invite?.mail_status
                                  ? ` Last invite ${o.owner_invite.mail_status}${
                                      o.owner_invite.sent_at
                                        ? ` on ${o.owner_invite.sent_at.slice(0, 10)}`
                                        : ""
                                    }.`
                                  : ""}
                              </span>
                            ) : (
                              <ul className="admin-seat-list">
                                {members.map((member) => (
                                  <SeatRow
                                    key={member.id}
                                    member={member}
                                    orgName={String(o.name || o.id)}
                                    canRemove={can("users.write") && !member.protected}
                                    onRemove={() => {
                                      if (!token) return;
                                      const who = member.email || member.name || member.id;
                                      if (
                                        !window.confirm(
                                          `Remove ${who} from ${o.name || o.id}? This frees the seat and signs them out.`,
                                        )
                                      ) {
                                        return;
                                      }
                                      void deleteAdminPortalUser(member.id, token)
                                        .then(() => {
                                          setMsg(`Removed ${who}`);
                                          return loadSection();
                                        })
                                        .catch((ex) => setErr((ex as Error).message));
                                    }}
                                  />
                                ))}
                                {ownerEmail && !ownerSeated ? (
                                  <li className="muted">Recorded owner {ownerEmail} has no login.</li>
                                ) : null}
                              </ul>
                            )}
                          </td>
                          <td>
                            <div className="row gap">
                            {can("pilot.manage") && ownerEmail && !ownerSeated && token ? (
                              <button
                                type="button"
                                className="btn-primary"
                                data-testid={`admin-invite-owner-${o.id}`}
                                onClick={() => {
                                  if (
                                    !window.confirm(
                                      `Email ${ownerEmail} a link to join ${o.name || o.id} as desk admin?`,
                                    )
                                  ) {
                                    return;
                                  }
                                  void postAdminPortalOwnerInvite(String(o.id), token)
                                    .then((r) => {
                                      const mail = r.mail_status || "sent";
                                      setMsg(
                                        mail === "sent"
                                          ? `Invite sent to ${r.email || ownerEmail}`
                                          : mail === "stubbed"
                                            ? `Invite created for ${r.email || ownerEmail}, but mail is not configured`
                                            : `Invite for ${r.email || ownerEmail} was not delivered (${mail})`,
                                      );
                                      return loadSection();
                                    })
                                    .catch((ex) => setErr((ex as Error).message));
                                }}
                              >
                                {o.owner_invite ? "Send invite again" : "Invite recorded owner"}
                              </button>
                            ) : null}
                            {can("orgs.write") && o.deletable && token ? (
                              <button
                                type="button"
                                className="admin-delete"
                                data-testid={`admin-delete-org-${o.id}`}
                                onClick={() => {
                                  if (
                                    !window.confirm(
                                      `Delete ${o.name || o.id}? The desk goes. A pilot request that named it stays until you delete that request.`,
                                    )
                                  ) {
                                    return;
                                  }
                                  void deleteAdminPortalOrg(String(o.id), token)
                                    .then(() => {
                                      setMsg(`Deleted ${o.name || o.id}`);
                                      return loadSection();
                                    })
                                    .catch((ex) => setErr((ex as Error).message));
                                }}
                              >
                                Delete organisation
                              </button>
                            ) : (
                              <span className="muted">{o.delete_block || "—"}</span>
                            )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {section === "users" && can("users.read") && (
            <div data-testid="admin-section-users">
              <h2 style={{ marginTop: 0 }}>Users</h2>
              <label className="muted">
                <input
                  type="checkbox"
                  checked={standingOnly}
                  onChange={(e) => setStandingOnly(e.target.checked)}
                />{" "}
                Standing accounts
              </label>
              {users.filter((u) => !standingOnly || u.protected).length === 0 ? (
                <p className="muted">No registered users yet.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Org</th>
                      <th>Org role</th>
                      <th>Platform admin</th>
                      {can("users.write") ? <th>Actions</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {users
                      .filter((u) => !standingOnly || u.protected)
                      .map((u) => (
                      <tr key={u.id}>
                        <td>{u.email || u.name || u.id}</td>
                        <td>
                          <code>{u.org_id || "—"}</code>
                        </td>
                        <td>{u.role || "—"}</td>
                        <td>
                          {can("users.write") ? (
                            <select
                              value={u.platform_admin_role || ""}
                              aria-label={`Platform role for ${u.email || u.id}`}
                              onChange={(e) => {
                                if (!token) return;
                                const select = e.target;
                                const prev = u.platform_admin_role || "";
                                const val = select.value || null;
                                const who = u.email || u.name || u.id;
                                const next = val || "no platform role";
                                if (
                                  !window.confirm(
                                    `Platform roles are for Ocotillo operators. Assign ${next} to ${who}? Do not grant these to a customer login.`,
                                  )
                                ) {
                                  select.value = prev;
                                  return;
                                }
                                void patchAdminPortalUserRole(u.id, val, token)
                                  .then(() => loadSection())
                                  .catch((ex) => setErr((ex as Error).message));
                              }}
                            >
                              <option value="">—</option>
                              {(PLATFORM_SUPER_EMAILS.has((u.email || "").trim().toLowerCase())
                                ? PLATFORM_ROLES
                                : PLATFORM_ROLES.filter((r) => r !== "super")
                              ).map((r) => (
                                <option key={r} value={r}>
                                  {r}
                                </option>
                              ))}
                            </select>
                          ) : (
                            u.platform_admin_role || "—"
                          )}
                        </td>
                        {can("users.write") ? (
                          <td>
                            {u.protected ? (
                              <span className="muted">Standing account</span>
                            ) : portal.email &&
                              (u.email || "").toLowerCase() === portal.email.toLowerCase() ? (
                              <span className="muted">Signed-in account</span>
                            ) : token ? (
                              <button
                                type="button"
                                className="admin-delete"
                                data-testid={`admin-delete-user-${u.id}`}
                                onClick={() => {
                                  const who = u.email || u.name || u.id;
                                  if (
                                    !window.confirm(
                                      `Delete ${who}? This frees their seat and signs them out.`,
                                    )
                                  ) {
                                    return;
                                  }
                                  void deleteAdminPortalUser(u.id, token)
                                    .then(() => {
                                      setMsg(`Deleted ${who}`);
                                      return loadSection();
                                    })
                                    .catch((ex) => setErr((ex as Error).message));
                                }}
                              >
                                Delete user
                              </button>
                            ) : (
                              "—"
                            )}
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {section === "feedback" && can("feedback.read") && (
            <div data-testid="admin-section-feedback">
              <h2 style={{ marginTop: 0 }}>Partner feedback</h2>
              {feedback.length === 0 ? (
                <p className="muted">No feedback items.</p>
              ) : (
                <ul className="org-member-list">
                  {feedback.map((it) => (
                    <li key={it.id}>
                      <span>
                        {it.kind} · org {it.org_id || "—"} · {it.company_id || "—"} · {it.status}
                        {it.comment ? ` — ${it.comment.slice(0, 100)}` : ""}
                      </span>
                      {can("feedback.write") && it.status === "open" && token && (
                        <button
                          type="button"
                          className="btn-ghost"
                          onClick={() => {
                            void patchAdminPortalFeedback(it.id, "ack", token)
                              .then(() => loadSection())
                              .catch((ex) => setErr((ex as Error).message));
                          }}
                        >
                          Ack
                        </button>
                      )}
                      {can("feedback.write") && it.status !== "closed" && token && (
                        <button
                          type="button"
                          className="btn-ghost"
                          onClick={() => {
                            void patchAdminPortalFeedback(it.id, "closed", token)
                              .then(() => loadSection())
                              .catch((ex) => setErr((ex as Error).message));
                          }}
                        >
                          Close
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {section === "pilot-requests" && can("pilot.manage") && (
            <div data-testid="admin-section-pilot-requests">
              <h2 style={{ marginTop: 0 }}>Pilot requests</h2>
              <p className="muted">
                Inbound evaluation requests from the public form. Approve opens a pilot desk and emails the requester a link to set a password as desk admin. The seat stays until you delete the user. Reject closes the request. Delete removes the request. The organisation stays until you delete it under Organizations.
              </p>
              <label className="muted" style={{ fontSize: 13 }}>
                Markets for the next approval{" "}
                <select
                  value={pilotCoverage}
                  onChange={(e) => setPilotCoverage(e.target.value)}
                  aria-label="Markets for approved pilot"
                  data-testid="pilot-coverage"
                >
                  {PILOT_COVERAGE.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              {pilotRequests.length === 0 ? (
                <p className="muted">No pilot requests yet.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Submitted</th>
                      <th>Contact</th>
                      <th>Firm</th>
                      <th>Details</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pilotRequests.map((req) => (
                      <tr key={req.id}>
                        <td>{req.created_at ? req.created_at.slice(0, 10) : "—"}</td>
                        <td>
                          <div>{req.name}</div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {req.email}
                          </div>
                        </td>
                        <td>{req.firm}</td>
                        <td>
                          {[req.role, req.team_size].filter(Boolean).join(" · ") || "—"}
                          {req.message ? (
                            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                              {req.message.slice(0, 120)}
                              {req.message.length > 120 ? "…" : ""}
                            </div>
                          ) : null}
                        </td>
                        <td>
                          <code>{req.status}</code>
                          {req.org_id ? (
                            <div className="muted" style={{ fontSize: 12 }}>
                              org {req.org_id}
                            </div>
                          ) : null}
                          {req.reviewed_by ? (
                            <div className="muted" style={{ fontSize: 12 }}>
                              by {req.reviewed_by}
                            </div>
                          ) : null}
                          {req.owner_invite?.mail_status ? (
                            <div className="muted" style={{ fontSize: 12 }}>
                              invite {req.owner_invite.mail_status}
                            </div>
                          ) : null}
                        </td>
                        <td>
                          <div className="row gap">
                            {req.status === "pending" && token ? (
                              <>
                                <button
                                  type="button"
                                  className="btn-primary"
                                  data-testid={`pilot-approve-${req.id}`}
                                  onClick={() => {
                                    void patchAdminPortalPilotRequest(
                                      req.id,
                                      {
                                        action: "approve",
                                        term_days: pilotTerm,
                                        coverage: pilotCoverage.split(","),
                                      },
                                      token,
                                    )
                                      .then((r) => {
                                        setMsg(approvePilotMessage(r));
                                        return loadSection();
                                      })
                                      .catch((ex) => setErr((ex as Error).message));
                                  }}
                                >
                                  Approve
                                </button>
                                <button
                                  type="button"
                                  className="btn-ghost"
                                  data-testid={`pilot-reject-${req.id}`}
                                  onClick={() => {
                                    void patchAdminPortalPilotRequest(req.id, { action: "reject" }, token)
                                      .then(() => {
                                        setMsg("Pilot request rejected");
                                        return loadSection();
                                      })
                                      .catch((ex) => setErr((ex as Error).message));
                                  }}
                                >
                                  Reject
                                </button>
                              </>
                            ) : null}
                            {token ? (
                              <button
                                type="button"
                                className="admin-delete"
                                data-testid={`admin-delete-pilot-${req.id}`}
                                onClick={() => {
                                  if (
                                    !window.confirm(
                                      `Delete the pilot request from ${req.email} (${req.firm})? The organisation, if one was created, stays until you delete it under Organizations.`,
                                    )
                                  ) {
                                    return;
                                  }
                                  void deleteAdminPortalPilotRequest(req.id, token)
                                    .then(() => {
                                      setMsg(`Deleted pilot request from ${req.email}`);
                                      return loadSection();
                                    })
                                    .catch((ex) => setErr((ex as Error).message));
                                }}
                              >
                                Delete request
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {section === "legal" && can("legal.read") && legal && (
            <div data-testid="admin-section-legal">
              <h2 style={{ marginTop: 0 }}>Legal attestations</h2>
              <p className="muted">
                Counsel: <code>{String(legal.counsel_status)}</code> · SEBI retail:{" "}
                <code>{String(legal.sebi_retail_status)}</code>
              </p>
              {can("legal.write") && token && (
                <form
                  className="admin-inline-form"
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    void postAdminPortalLegalAttest(
                      { kind: attestKind, attested_by: attestBy },
                      token,
                    )
                      .then(() => fetchAdminPortalLegal(token))
                      .then(setLegal)
                      .then(() => setMsg("Attestation recorded"))
                      .catch((ex) => setErr((ex as Error).message));
                  }}
                >
                  <select
                    value={attestKind}
                    onChange={(e) => setAttestKind(e.target.value)}
                    aria-label="Attestation kind"
                  >
                    <option value="terms_privacy">terms_privacy</option>
                    <option value="sebi_retail">sebi_retail</option>
                  </select>
                  <input
                    value={attestBy}
                    onChange={(e) => setAttestBy(e.target.value)}
                    placeholder="Attested by"
                    aria-label="Attested by"
                  />
                  <button type="submit" className="btn-primary">
                    Record attestation
                  </button>
                </form>
              )}
            </div>
          )}

          {section === "billing" && can("billing.read") && (
            <div data-testid="admin-section-billing">
              <h2 style={{ marginTop: 0 }}>Billing</h2>
              {can("billing.write") && token && (
                <form
                  className="admin-inline-form"
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    void postAdminPortalInvoice(
                      {
                        org_id: invoiceOrg,
                        plan: invoicePlan,
                        seats: invoiceSeats,
                        signer_email: invoiceSigner.trim() || undefined,
                      },
                      token,
                    )
                      .then(() => {
                        setMsg(invoiceSigner.trim() ? "Invoice signed." : "Invoice issued.");
                        setInvoiceSigner("");
                        return fetchAdminPortalBilling(token);
                      })
                      .then((res) => setBilling(res.invoices || []))
                      .catch((ex) => setErr((ex as Error).message));
                  }}
                >
                  <label>
                    Organisation
                    <select value={invoiceOrg} onChange={(e) => setInvoiceOrg(e.target.value)} aria-label="Invoice organisation">
                      {orgs.map((o) => (
                        <option key={String(o.id)} value={String(o.id)}>
                          {String(o.name || o.id)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Plan
                    <select value={invoicePlan} onChange={(e) => setInvoicePlan(e.target.value)} aria-label="Invoice plan">
                      <option value="pilot">pilot</option>
                      <option value="desk">desk</option>
                      <option value="enterprise">enterprise</option>
                    </select>
                  </label>
                  <label>
                    Seats
                    <input
                      type="number"
                      min={1}
                      value={invoiceSeats}
                      aria-label="Invoice seats"
                      onChange={(e) => setInvoiceSeats(Number(e.target.value) || 1)}
                    />
                  </label>
                  <label>
                    Signer email
                    <input
                      value={invoiceSigner}
                      aria-label="Signer email"
                      placeholder="Optional. Records the signature."
                      onChange={(e) => setInvoiceSigner(e.target.value)}
                    />
                  </label>
                  <button type="submit" className="btn-primary">
                    Issue MSA invoice
                  </button>
                </form>
              )}
              {billing.length === 0 ? (
                <p className="muted">No invoices yet.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Org</th>
                      <th>Kind</th>
                      <th>Status</th>
                      <th>INR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {billing.map((inv) => (
                      <tr key={String(inv.id)}>
                        <td>
                          <code>{String(inv.id)}</code>
                        </td>
                        <td>{String(inv.org_id || "—")}</td>
                        <td>{String(inv.kind || "—")}</td>
                        <td>{String(inv.status || "—")}</td>
                        <td>{String(inv.amount_inr ?? "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {section === "audit" && can("audit.read") && audit && (
            <div data-testid="admin-section-audit">
              <h2 style={{ marginTop: 0 }}>Audit summary</h2>
              <dl className="admin-dl">
                {Object.entries(audit).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k.replace(/_/g, " ")}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {section === "labeling" && can("audit.read") && labeling && (
            <div data-testid="admin-section-labeling">
              <h2 style={{ marginTop: 0 }}>Labeling</h2>
              <p className="muted">{labeling.note}</p>
              <h3>Queue</h3>
              {labeling.items.length === 0 ? (
                <p className="muted">No open labeling items.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Org</th>
                      <th>Kind</th>
                      <th>Status</th>
                      <th>Age (days)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labeling.items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.company_name || item.company_id}</td>
                        <td><code>{item.org_id || "—"}</code></td>
                        <td>{item.kind || "—"}</td>
                        <td>{item.status}</td>
                        <td>{item.age_days ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <h3>Extracts waiting</h3>
              {labeling.extracts.length === 0 ? (
                <p className="muted">No extracts waiting.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Statements</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labeling.extracts.map((batch) => (
                      <tr key={batch.id}>
                        <td><code>{batch.company_id}</code></td>
                        <td>{batch.statements}</td>
                        <td>{batch.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <h3>Source checks</h3>
              <p className="muted">
                Checked {labeling.source_checks.checked}, verified {labeling.source_checks.verified}, failed{" "}
                {labeling.source_checks.failed}, fetch failed {labeling.source_checks.fetch_failed}.
                {labeling.source_checks.as_of ? ` As of ${labeling.source_checks.as_of}.` : ""}
              </p>
              {labeling.source_checks.note ? <p className="muted">{labeling.source_checks.note}</p> : null}
              {labeling.source_checks.failures.length > 0 && (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Period</th>
                      <th>Metric</th>
                      <th>Side</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labeling.source_checks.failures.map((row, i) => (
                      <tr key={`${row.company_id}-${row.period}-${row.metric}-${i}`}>
                        <td><code>{row.company_id}</code></td>
                        <td>{row.period}</td>
                        <td>{row.metric}</td>
                        <td>{row.kind}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {section === "commitments" && can("audit.read") && (
            <div data-testid="admin-section-commitments">
              <h2 style={{ marginTop: 0 }}>Unreviewed commitments</h2>
              <p className="muted">{commitmentNote}</p>
              {commitments.length === 0 ? (
                <p className="muted">No unreviewed commitments.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Type</th>
                      <th>Subject</th>
                      <th>Due</th>
                      <th>Quote</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commitments.map((row) => (
                      <tr key={row.id}>
                        <td><code>{row.company_id}</code></td>
                        <td>{row.type}</td>
                        <td>{row.subject}</td>
                        <td>{row.due_period}</td>
                        <td>{row.quote}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {sections.some((s) => s.id === section) && section === "reports" && (
            <div data-testid="admin-section-reports">
              <h2 style={{ marginTop: 0 }}>
                {reportParam
                  ? reports.find((item) => item.id === reportParam)?.label || "Report"
                  : "Reports"}
              </h2>
              <p className="muted">Read from the files already on disk. As-of is the time of that file.</p>
              {reportDenied ? (
                <div data-testid="admin-section-denied">
                  <p>This report is not open for your role.</p>
                  <button type="button" className="btn" onClick={() => setSearchParams({ section: "overview" })}>
                    Back to Board
                  </button>
                </div>
              ) : (
              <div className="row gap">
                {(reportParam ? reports.filter((item) => item.id === reportParam) : reports).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={reportId === item.id ? "btn-primary" : "btn-ghost"}
                    onClick={() => setSearchParams({ section: "reports", report: item.id })}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              )}
              {!reportDenied && report && (
                <div data-testid="admin-report-body">
                  <p className="muted">As of {String(report.as_of || "—")}</p>
                  {report.empty_note ? <p>{String(report.empty_note)}</p> : null}
                  {report.note ? <p className="muted">{String(report.note)}</p> : null}
                  {reportId === "usage" && Array.isArray(report.orgs) && (
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Org</th>
                          <th>Plan</th>
                          <th>Seats used</th>
                          <th>Monitors</th>
                          <th>Skill runs, 7 days</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(report.orgs as Record<string, unknown>[]).map((org) => (
                          <tr key={String(org.org_id)}>
                            <td>{String(org.name || org.org_id)}</td>
                            <td>{String(org.plan || "—")}</td>
                            <td>
                              {String(org.seats_used ?? "—")} / {String(org.seats ?? "—")}
                            </td>
                            <td>{String(org.monitors ?? 0)}</td>
                            <td>{String(org.skill_runs_7d ?? 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {reportId === "audit-events" && Array.isArray(report.events) && (
                    <>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => {
                          const rows = report.events as Record<string, unknown>[];
                          const header = ["ts", "action", "org", "actor", "role", "detail"];
                          const lines = [
                            header.join(","),
                            ...rows.map((row) =>
                              header
                                .map((key) => `"${String(row[key] ?? "").replace(/"/g, '""')}"`)
                                .join(","),
                            ),
                          ];
                          const blob = new Blob([lines.join("\n")], { type: "text/csv" });
                          const url = URL.createObjectURL(blob);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = "audit-events.csv";
                          link.click();
                          URL.revokeObjectURL(url);
                        }}
                      >
                        Download this page
                      </button>
                      <table className="admin-table">
                        <thead>
                          <tr>
                            <th>When</th>
                            <th>Action</th>
                            <th>Org</th>
                            <th>Actor</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(report.events as Record<string, unknown>[]).map((row, i) => (
                            <tr key={`${row.ts}-${i}`}>
                              <td>{String(row.ts || "—")}</td>
                              <td>{String(row.action || "—")}</td>
                              <td>{String(row.org || "—")}</td>
                              <td>{String(row.actor || "—")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}
                  {reportId !== "usage" && reportId !== "audit-events" && (
                    <dl className="admin-dl">
                      {Object.entries(report)
                        .filter(([key]) => !["id", "as_of", "note", "empty_note", "snapshot"].includes(key))
                        .map(([key, value]) => (
                          <div key={key}>
                            <dt>{key.replace(/_/g, " ")}</dt>
                            <dd>
                              {value !== null && typeof value === "object"
                                ? JSON.stringify(value)
                                : String(value ?? "—")}
                            </dd>
                          </div>
                        ))}
                    </dl>
                  )}
                </div>
              )}
            </div>
          )}

          {section === "system" && can("system.ops") && (
            <div data-testid="admin-section-system">
              <h2 style={{ marginTop: 0 }}>System</h2>
              <p className="muted">Demo reset is not available on this page.</p>
              {system && (
                <>
                  <p className="muted">{system.note}</p>
                  <h3>Guidance review</h3>
                  <p>
                    {system.guidance_review.ran
                      ? `Last ran ${system.guidance_review.date} for ${system.guidance_review.market_id}. Bound ${system.guidance_review.bound_rows ?? 0} rows.`
                      : "Guidance review has not recorded a run."}
                  </p>
                  <h3>Analyst monitors</h3>
                  <p>
                    {system.monitors.monitors} monitors across {system.monitors.orgs} desks.
                    {system.monitors.last_triggered_at
                      ? ` Last trigger ${system.monitors.last_triggered_at}.`
                      : " No trigger recorded."}
                  </p>
                  <h3>Coverage roll</h3>
                  <p className="muted">
                    India searched today {String(system.india_coverage.searched_today ?? "—")} of{" "}
                    {String(system.india_coverage.cohort_size ?? "—")}.
                    {system.india_coverage.running ? " In progress." : ""}
                  </p>
                  <p className="muted">
                    US cohort {String(system.us_coverage.cohort_size ?? "—")}.
                    {system.us_coverage.running ? " In progress." : ""}
                  </p>
                  <h3>Source verification</h3>
                  <p className="muted">
                    Checked {system.source_verification.checked}, failed {system.source_verification.failed}.
                    {system.source_verification.as_of ? ` As of ${system.source_verification.as_of}.` : ""}
                  </p>
                  <h3>Flags</h3>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Job</th>
                        <th>On</th>
                      </tr>
                    </thead>
                    <tbody>
                      {system.flags.map((flag) => (
                        <tr key={flag.id}>
                          <td>{flag.label}</td>
                          <td>{flag.on ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
              <h3>Test tenants</h3>
              <p className="muted">
                Preview lists synthetic test desks and guest sessions. Approved pilots and CiteAlpha accounts stay.
              </p>
              {token && (
                <div className="row gap">
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => {
                      void postAdminPortalCleanup(true, token)
                        .then((res) => {
                          setCleanupPreview({ users_removed: res.users_removed, orgs_removed: res.orgs_removed });
                          setMsg("Preview only. Nothing was removed.");
                        })
                        .catch((ex) => setErr((ex as Error).message));
                    }}
                  >
                    Preview cleanup
                  </button>
                  {cleanupPreview && (
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => {
                        if (!window.confirm("Remove the listed test tenants?")) return;
                        void postAdminPortalCleanup(false, token)
                          .then((res) => {
                            setCleanupPreview({ users_removed: res.users_removed, orgs_removed: res.orgs_removed });
                            setMsg("Test tenants removed.");
                          })
                          .catch((ex) => setErr((ex as Error).message));
                      }}
                    >
                      Remove the listed test tenants
                    </button>
                  )}
                </div>
              )}
              {cleanupPreview && (
                <div data-testid="admin-cleanup-preview">
                  <p>Users: {cleanupPreview.users_removed.join(", ") || "none"}</p>
                  <p>Organisations: {cleanupPreview.orgs_removed.join(", ") || "none"}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
