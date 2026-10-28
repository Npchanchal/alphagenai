import { FormEvent, useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  OrgDeskKeyPanel,
  OrgInvitesPanel,
  OrgMembersPanel,
  OrgPartnersPanel,
} from "../components/OrgAdminPanel";
import Skeleton from "../components/Skeleton";
import { DestinationsPanel, HouseStylePanel, KeysPanel } from "./analyst/AnalystSettings";
import {
  fetchMyOrg,
  fetchOrgAudit,
  fetchOrgInvoices,
  fetchOrgPilotChecklist,
  fetchSsoStatus,
  patchOrgPilotChecklist,
  postSignOrgInvoice,
  putOrgOidc,
  type OrgAuditEvent,
  type OrgInvoice,
  type OrgPayload,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { useEntitlements } from "../lib/entitlements";

const ADMIN_SECTIONS = new Set([
  "overview",
  "members",
  "invites",
  "partners",
  "signin",
  "keys",
  "destinations",
  "style",
  "billing",
  "pilot",
  "audit",
]);

const SSO_LABELS: Record<string, string> = {
  SSO: "Identity-provider sign-in",
  OIDC_CLIENT_ID: "Client id on the service",
  OIDC_CLIENT_SECRET: "Client secret on the service",
  OIDC_ISSUER: "Issuer on the service",
  OIDC_REDIRECT_URI: "Redirect address",
  OIDC_REDIRECT_HTTPS: "Redirect uses HTTPS",
  FORCE_HTTPS: "Site requires HTTPS",
  OIDC_DEMO_ASSERT_OFF: "Demo sign-in is off",
};

function Denied({ children }: { children: ReactNode }) {
  return (
    <div className="panel" data-testid="org-section-denied">
      <h2 style={{ marginTop: 0 }}>This section is not open</h2>
      <p className="muted">{children}</p>
      <Link to="/org/settings?section=overview" className="btn">
        Back to summary
      </Link>
    </div>
  );
}

function SignInPanel({ org, onSaved }: { org: OrgPayload; onSaved: (next: OrgPayload) => void }) {
  const { token, user } = useAuth();
  const [issuer, setIssuer] = useState(String(org.oidc_issuer || ""));
  const [clientId, setClientId] = useState(String(org.oidc_client_id || ""));
  const [domain, setDomain] = useState(String(org.email_domain || ""));
  const [sso, setSso] = useState<Awaited<ReturnType<typeof fetchSsoStatus>> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchSsoStatus()
      .then(setSso)
      .catch(() => setSso(null));
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!token || !user?.org_id) return;
    setError(null);
    setMsg(null);
    try {
      const next = await putOrgOidc(user.org_id, token, {
        oidc_issuer: issuer.trim(),
        oidc_client_id: clientId.trim(),
        email_domain: domain.trim(),
      });
      onSaved(next);
      setMsg("Sign-in settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save sign-in");
    }
  }

  const blank = !issuer.trim() && !clientId.trim() && !domain.trim();

  return (
    <div data-testid="org-signin">
      <h2 style={{ marginTop: 0 }}>Sign-in</h2>
      <p className="muted">
        {blank
          ? "Blank fields mean people sign in with a password."
          : "These three fields record how this organisation signs in with its identity provider."}{" "}
        A client secret is not stored here.
      </p>
      <form className="auth-form" onSubmit={save} style={{ maxWidth: 480 }}>
        <label>
          Issuer
          <input value={issuer} onChange={(e) => setIssuer(e.target.value)} data-testid="org-oidc-issuer" />
        </label>
        <label>
          Client id
          <input value={clientId} onChange={(e) => setClientId(e.target.value)} data-testid="org-oidc-client" />
        </label>
        <label>
          Email domain
          <input value={domain} onChange={(e) => setDomain(e.target.value)} data-testid="org-oidc-domain" />
        </label>
        <button type="submit" className="btn-primary">
          Save sign-in
        </button>
      </form>
      {msg && <p className="muted">{msg}</p>}
      {error && <p className="error">{error}</p>}
      {sso && (
        <div data-testid="org-sso-readiness">
          <h3>Service readiness</h3>
          <p className="muted">
            Switched on: {sso.enabled ? "yes" : "no"} · Configured: {sso.configured ? "yes" : "no"} ·
            Production-ready: {sso.production_ready || sso.ready ? "yes" : "not yet"}
          </p>
          {sso.checklist && (
            <ul className="package-steps">
              {Object.entries(sso.checklist).map(([key, value]) =>
                SSO_LABELS[key] ? (
                  <li key={key}>
                    {SSO_LABELS[key]}: {value ? "ok" : "missing"}
                  </li>
                ) : null,
              )}
            </ul>
          )}
          <p className="muted">
            Register this redirect with your identity provider:{" "}
            <code>https://citealpha.com/api/auth/sso/callback</code>. See <Link to="/trust">Trust</Link>.
          </p>
        </div>
      )}
    </div>
  );
}

function BillingPanel() {
  const { token, user } = useAuth();
  const [invoices, setInvoices] = useState<OrgInvoice[]>([]);
  const [signer, setSigner] = useState(user?.email || "");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void fetchOrgInvoices(token)
      .then((row) => setInvoices(row.invoices || []))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load invoices"));
  }, [token, msg]);

  return (
    <div data-testid="org-billing">
      <h2 style={{ marginTop: 0 }}>Billing</h2>
      <p className="muted">
        Invoices for this organisation. A new agreement is issued by CiteAlpha.{" "}
        <Link to="/billing">Open the billing page</Link>.
      </p>
      {invoices.length === 0 ? (
        <p className="muted">No invoices yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="table" data-testid="org-invoices">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Plan</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv, i) => (
                <tr key={inv.id || i}>
                  <td>{inv.id || "—"}</td>
                  <td>{inv.plan || "—"}</td>
                  <td>{inv.amount_inr != null ? `₹${inv.amount_inr}` : "—"}</td>
                  <td>{inv.esign_status || inv.status || "—"}</td>
                  <td>{inv.created_at ? String(inv.created_at).slice(0, 10) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {invoices.some((inv) => inv.esign_status === "pending" || inv.status === "issued") && (
        <form
          className="auth-form"
          style={{ maxWidth: 420, marginTop: 16 }}
          onSubmit={(e) => {
            e.preventDefault();
            if (!token) return;
            const waiting = invoices.find((inv) => inv.id && (inv.esign_status === "pending" || inv.status === "issued"));
            if (!waiting?.id) return;
            setError(null);
            void postSignOrgInvoice(waiting.id, token, signer)
              .then(() => {
                setMsg("Signature recorded.");
              })
              .catch((err) => setError(err instanceof Error ? err.message : "Could not record the signature"));
          }}
        >
          <label>
            Signer email
            <input type="email" required value={signer} onChange={(e) => setSigner(e.target.value)} />
          </label>
          <button type="submit" className="btn-primary">
            Record signature
          </button>
        </form>
      )}
      {msg && <p className="muted">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function PilotPanel({ orgId }: { orgId: string }) {
  const { token } = useAuth();
  const [items, setItems] = useState<Array<{ id: string; label: string; done: boolean }>>([]);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void fetchOrgPilotChecklist(orgId, token)
      .then((row) => {
        setItems(row.items || []);
        setProgress(row.progress);
        setNotes(row.notes || "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load the checklist"));
  }, [orgId, token]);

  return (
    <div data-testid="org-pilot">
      <h2 style={{ marginTop: 0 }}>Pilot checklist</h2>
      {progress && (
        <p className="muted">
          {progress.done} of {progress.total} steps marked.
        </p>
      )}
      <ul className="package-steps">
        {items.map((item) => (
          <li key={item.id}>
            <label>
              <input
                type="checkbox"
                checked={item.done}
                onChange={(e) => {
                  if (!token) return;
                  const done = e.target.checked;
                  void patchOrgPilotChecklist(orgId, token, { item_id: item.id, done })
                    .then((row) => {
                      setItems(row.items || []);
                      setProgress(row.progress);
                    })
                    .catch((err) => setError(err instanceof Error ? err.message : "Could not update the step"));
                }}
              />{" "}
              {item.label}
            </label>
          </li>
        ))}
      </ul>
      <form
        className="auth-form"
        style={{ maxWidth: 480 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!token) return;
          void patchOrgPilotChecklist(orgId, token, { notes })
            .then((row) => setNotes(row.notes || ""))
            .catch((err) => setError(err instanceof Error ? err.message : "Could not save notes"));
        }}
      >
        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>
        <button type="submit" className="btn">
          Save notes
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

const AUDIT_ACTIONS: Record<string, string> = {
  review_accept: "Accepted a row",
  review_edit: "Edited a row",
  review_reject: "Rejected a row",
  pack_export: "Exported a board pack",
  seat_change: "Changed a seat",
};

function auditActionLabel(action?: string | null): string {
  if (!action) return "—";
  return AUDIT_ACTIONS[action] || action.replace(/_/g, " ");
}

function auditDetail(detail?: Record<string, unknown> | null): string {
  if (!detail) return "—";
  const parts: string[] = [];
  if (detail.company_id) parts.push(String(detail.company_id).toUpperCase());
  if (detail.member) parts.push(String(detail.member));
  if (detail.from || detail.to) parts.push(`${String(detail.from || "—")} → ${String(detail.to || "—")}`);
  return parts.length ? parts.join(" · ") : "—";
}

function AuditPanel() {
  const { token } = useAuth();
  const [events, setEvents] = useState<OrgAuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void fetchOrgAudit(token)
      .then((row) => setEvents(row.events || []))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load audit events"));
  }, [token]);

  return (
    <div data-testid="org-audit">
      <h2 style={{ marginTop: 0 }}>Audit</h2>
      <p className="muted">
        Newest first: who accepted or rejected a row, who exported a pack, who changed a seat, and
        sign-in events for this organisation.
      </p>
      {events.length === 0 ? (
        <p className="muted">No events yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Person</th>
                <th>Action</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event, i) => (
                <tr key={`${event.ts || ""}-${i}`}>
                  <td>{event.ts ? String(event.ts).slice(0, 19).replace("T", " ") : "—"}</td>
                  <td>{event.actor || "—"}</td>
                  <td>{auditActionLabel(event.action)}</td>
                  <td>{auditDetail(event.detail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

/** Organisation administration. One section per query. */
export default function OrgSettingsPage() {
  const { user, token, loading: authLoading } = useAuth();
  const { has, entitlements, loading: entitlementsLoading } = useEntitlements();
  const [searchParams] = useSearchParams();
  const [org, setOrg] = useState<OrgPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const section = searchParams.get("section") || "overview";
  const orgId = user?.org_id;
  const canAdmin = user?.role === "owner" || user?.role === "admin";
  const analyst = has("analyst_agent");
  const pilot = (org?.plan || entitlements.plan) === "pilot";

  useEffect(() => {
    if (authLoading) return;
    if (!orgId || !token) {
      setOrg(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    void fetchMyOrg(token)
      .then(setOrg)
      .catch(() => setOrg(null))
      .finally(() => setLoading(false));
  }, [authLoading, orgId, token]);

  if (authLoading || loading || entitlementsLoading) {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <Skeleton rows={4} />
      </section>
    );
  }

  if (!user || user.kind === "guest") {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <p className="page-kicker">Organisation</p>
        <h1>Organisation settings</h1>
        <div className="panel settings-panel">
          <p className="muted">Register a research desk to manage seats and API keys.</p>
          <div className="row gap" style={{ marginTop: 12 }}>
            <Link to="/register" className="btn-primary">
              Register desk
            </Link>
            <Link to="/login" state={{ from: "/org/settings" }} className="btn">
              Log in
            </Link>
          </div>
        </div>
      </section>
    );
  }

  if (!orgId || user.account_type === "retail") {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <p className="page-kicker">Organisation</p>
        <h1>Organisation settings</h1>
        <div className="panel settings-panel">
          <p className="muted">
            Retail accounts use a personal account without shared seats. Register a research desk
            or contact sales for a pilot.
          </p>
          <Link to="/account" className="btn">
            Account preferences →
          </Link>
        </div>
      </section>
    );
  }

  const canAudit = has("org_audit");
  let body = null;
  if (section === "audit" && canAudit) {
    body = <AuditPanel />;
  } else if (!canAdmin && section !== "overview") {
    body = canAudit ? (
      <Denied>This seat reads the audit trail. It does not invite seats or open billing.</Denied>
    ) : (
      <Denied>
        Signed in as {user.email} ({user.role}). Ask an owner or admin to change seats, keys, or
        sign-in.
      </Denied>
    );
  } else if (!ADMIN_SECTIONS.has(section)) {
    body = <Denied>That section is not part of organisation settings.</Denied>;
  } else if ((section === "destinations" || section === "style") && !analyst) {
    body = (
      <Denied>
        Destinations and export style are part of CiteAlpha Analyst. This plan does not include it.
      </Denied>
    );
  } else if (section === "pilot" && !pilot) {
    body = <Denied>The pilot checklist is for evaluation desks.</Denied>;
  } else if (section === "overview") {
    body = (
      <div data-testid="org-overview">
        <h2 style={{ marginTop: 0 }}>Summary</h2>
        <div className="metrics">
          <div className="metric">
            <div className="label">Organisation</div>
            <div className="value" style={{ fontSize: 20 }}>
              {org?.name ?? orgId}
            </div>
          </div>
          <div className="metric">
            <div className="label">Plan</div>
            <div className="value" style={{ fontSize: 20 }}>
              {String(org?.plan ?? "—")}
            </div>
          </div>
          <div className="metric">
            <div className="label">Seats</div>
            <div className="value" style={{ fontSize: 20 }}>
              {String(org?.seats_used ?? "—")} / {String(org?.seats ?? "—")}
            </div>
          </div>
          <div className="metric">
            <div className="label">Your role</div>
            <div className="value" style={{ fontSize: 20 }}>
              {user.role ?? "—"}
            </div>
          </div>
          <div className="metric">
            <div className="label">Account</div>
            <div className="value" style={{ fontSize: 20 }}>
              {String(org?.account_type ?? user.account_type ?? "—")}
            </div>
          </div>
        </div>
        <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
          Org id <code>{orgId}</code>
          {!canAdmin && " · read-only — ask an owner or admin to change seats"}
        </p>
        {!canAdmin && canAudit && (
          <div className="row gap" style={{ marginTop: 12 }}>
            <Link to="/org/settings?section=audit" className="btn" data-testid="org-audit-link">
              Audit trail
            </Link>
          </div>
        )}
        {canAdmin && (
          <div className="row gap" style={{ marginTop: 12 }}>
            <Link to="/org/settings?section=members" className="btn">
              Members
            </Link>
            <Link to="/org/settings?section=keys" className="btn">
              API keys
            </Link>
            <Link to="/org/settings?section=billing" className="btn-ghost">
              Billing
            </Link>
          </div>
        )}
      </div>
    );
  } else if (section === "members") body = <OrgMembersPanel />;
  else if (section === "invites") body = <OrgInvitesPanel />;
  else if (section === "partners") body = <OrgPartnersPanel />;
  else if (section === "signin" && org) body = <SignInPanel org={org} onSaved={setOrg} />;
  else if (section === "keys") {
    body = (
      <div data-testid="org-keys">
        <h2 style={{ marginTop: 0 }}>API keys</h2>
        {analyst ? (
          <>
            <p className="muted">
              Analyst keys call the public API and the MCP server. The desk key is separate and is
              not an Analyst key.
            </p>
            <KeysPanel />
          </>
        ) : (
          <p className="muted">This plan does not include Analyst keys. The desk key is below.</p>
        )}
        <OrgDeskKeyPanel />
      </div>
    );
  } else if (section === "destinations") body = <DestinationsPanel />;
  else if (section === "style") {
    body = (
      <div data-testid="org-style">
        <HouseStylePanel canEdit />
      </div>
    );
  } else if (section === "billing") body = <BillingPanel />;
  else if (section === "pilot") body = <PilotPanel orgId={orgId} />;
  else if (section === "audit") body = <AuditPanel />;

  return (
    <section className="settings-page" data-testid="org-settings-page">
      <p className="page-kicker">Organisation</p>
      <h1>Organisation settings</h1>
      <p className="muted lede">
        {canAdmin
          ? `Seats, sign-in, keys, and billing for ${(org?.name || "this organisation").trim()}.`
          : canAudit
            ? `The audit trail for ${(org?.name || "this organisation").trim()}: review decisions, pack exports, and seat changes.`
            : `Your seat on ${(org?.name || "this organisation").trim()}.`}
      </p>
      <div className="panel settings-panel">{body}</div>
      {!token && (
        <p className="error" style={{ marginTop: 16 }}>
          Session expired — <Link to="/login">log in</Link> to manage seats.
        </p>
      )}
    </section>
  );
}
