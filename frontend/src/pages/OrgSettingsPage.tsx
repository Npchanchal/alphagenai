import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import OrgAdminPanel from "../components/OrgAdminPanel";
import Skeleton from "../components/Skeleton";
import { fetchMyOrg, fetchSsoStatus, type OrgPayload } from "../lib/api";
import { useAuth } from "../lib/auth";
import { LEGAL_ENTITY } from "../lib/legal";

/** B2B tenant admin — seats, API keys, SSO readiness. */
export default function OrgSettingsPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [org, setOrg] = useState<OrgPayload | null>(null);
  const [sso, setSso] = useState<Awaited<ReturnType<typeof fetchSsoStatus>> | null>(null);
  const [loading, setLoading] = useState(true);

  const orgId = user?.org_id;
  const canAdmin = user?.role === "owner" || user?.role === "admin";

  useEffect(() => {
    if (authLoading) return;
    if (!orgId || !token) {
      setOrg(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      fetchMyOrg(token).catch(() => null),
      fetchSsoStatus().catch(() => null),
    ])
      .then(([o, s]) => {
        setOrg(o);
        setSso(s);
      })
      .finally(() => setLoading(false));
  }, [authLoading, orgId, token]);

  if (authLoading || loading) {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <Skeleton rows={4} />
      </section>
    );
  }

  if (!user || user.kind === "guest") {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <p className="page-kicker">Organization</p>
        <h1>Org settings</h1>
        <div className="panel settings-panel">
          <p className="muted">
            Register a B2B desk account to manage seats and API keys for your tenant.
          </p>
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

  if (!orgId) {
    return (
      <section className="settings-page" data-testid="org-settings-page">
        <p className="page-kicker">Organization</p>
        <h1>Org settings</h1>
        <div className="panel settings-panel">
          <p className="muted">
            Retail accounts use a personal micro-tenant without shared seat administration. Upgrade
            to a B2B desk on register or contact sales for a pilot org.
          </p>
          <Link to="/account" className="btn">
            Account preferences →
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="settings-page" data-testid="org-settings-page">
      <p className="page-kicker">Organization</p>
      <h1>Org settings</h1>
      <p className="muted lede">
        Seat administration and API keys for <strong>{LEGAL_ENTITY}</strong> desk tenants. CSM
        metrics stay on{" "}
        <Link to="/desk?tab=csm">Desk → CSM</Link>.
      </p>

      <div className="settings-grid">
        <div className="panel settings-panel">
          <h2 style={{ marginTop: 0 }}>Tenant summary</h2>
          <div className="metrics">
            <div className="metric">
              <div className="label">Org</div>
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
          </div>
          <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
            Org id <code>{orgId}</code>
            {!canAdmin && " · read-only — ask an owner or admin to change seats"}
          </p>
          <div className="row gap" style={{ marginTop: 12 }}>
            <Link to="/billing" className="btn">
              Billing
            </Link>
            <Link to="/desk?tab=csm" className="btn-ghost">
              CSM dashboard
            </Link>
          </div>
        </div>

        {sso && (
          <div className="panel settings-panel" data-testid="org-sso-readiness">
            <h2 style={{ marginTop: 0 }}>Enterprise SSO</h2>
            <p className="muted" style={{ fontSize: 13 }}>
              Enabled: {sso.enabled ? "yes" : "no"} · Configured: {sso.configured ? "yes" : "no"}{" "}
              · Production-ready: {sso.production_ready || sso.ready ? "yes" : "not yet"}
            </p>
            {sso.note && <p className="muted">{sso.note}</p>}
            {sso.checklist && (
              <ul className="package-steps">
                {Object.entries(sso.checklist).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v ? "ok" : "missing"}
                  </li>
                ))}
              </ul>
            )}
            <p className="muted" style={{ fontSize: 12 }}>
              IdP redirect: <code>https://citealpha.com/api/auth/sso/callback</code> · See{" "}
              <Link to="/trust">Trust Center</Link>
            </p>
          </div>
        )}

        <div className="panel settings-panel settings-panel-wide">
          <OrgAdminPanel />
        </div>
      </div>

      {!token && (
        <p className="error" style={{ marginTop: 16 }}>
          Session expired — <Link to="/login">log in</Link> to manage seats.
        </p>
      )}
    </section>
  );
}
