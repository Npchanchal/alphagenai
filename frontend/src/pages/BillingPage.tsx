import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";
import { useAuth } from "../lib/auth";
import { LEGAL_ENTITY } from "../lib/legal";
import { trackEvent } from "../lib/analytics";

type InvoiceRow = {
  id?: string;
  amount_inr?: number;
  status?: string;
  plan?: string;
  created_at?: string;
};

/** Quote / order-form billing. No PSP checkout (W8.8). */
export default function BillingPage() {
  const { t } = useI18n();
  const { user, token } = useAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);

  useEffect(() => {
    if (!token) return;
    void fetch("/api/billing/invoices", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((b) => setInvoices((b.invoices || []) as InvoiceRow[]))
      .catch(() => setInvoices([]));
  }, [token, msg]);

  async function issueMsa(e: FormEvent, fromPilot = false) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    const r = await fetch("/api/billing/msa", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        fromPilot
          ? { plan: "desk", seats: 5, from_pilot: true, conversion_path: "pilot_to_desk" }
          : { plan: "desk", seats: 5 },
      ),
    });
    const body = await r.json();
    if (!r.ok) {
      setError(body.detail || t("ui.BillingPage.msaIssueFailed"));
      return;
    }
    setMsg(
      fromPilot
        ? t("ui.BillingPage.msaIssuedPilot", { id: body.id })
        : t("ui.BillingPage.msaIssued", { id: body.id }),
    );
    if (body.next_steps) {
      setMsg((m) => `${m || ""}\n${(body.next_steps as string[]).join(" · ")}`);
    }
    const sign = await fetch(`/api/billing/msa/${body.id}/sign`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ signer_email: user?.email || "signer@example.com" }),
    });
    const signed = await sign.json();
    if (!sign.ok) {
      setError(signed.detail || t("ui.BillingPage.msaSignFailed"));
      return;
    }
    setMsg(t("ui.BillingPage.msaSigned", { id: signed.id }));
  }

  return (
    <section className="auth-page" data-testid="billing-page">
      <p className="page-kicker">{t("billing.kicker")}</p>
      <h1>{t("billing.title")}</h1>
      <p className="muted lede">{t("billing.lede", { entity: LEGAL_ENTITY })}</p>
      {!user || user.kind === "guest" ? (
        <div className="panel" data-testid="billing-guest">
          <h2 style={{ marginTop: 0 }}>{t("billing.guestTitle")}</h2>
          <p className="muted">{t("billing.guestLede")}</p>
          <p style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
            <Link to="/login" className="btn primary">
              {t("common.login")}
            </Link>
            <Link to="/products#plans" className="btn">
              {t("billing.viewPlans")}
            </Link>
          </p>
        </div>
      ) : (
        <div className="panel">
          {user.account_type === "retail" && (
            <>
              <h2 style={{ marginTop: 0 }}>{t("ui.BillingPage.retailTitle")}</h2>
              <p className="muted">{t("package.retailGate")}</p>
              <Link to="/pilot" className="btn primary">
                {t("package.quoteCta")}
              </Link>
            </>
          )}
          {(user.account_type === "b2b" || user.role === "admin" || user.role === "owner") && (
            <>
              <h2 style={{ marginTop: 0 }}>{t("ui.BillingPage.b2bTitle")}</h2>
              <p className="muted" style={{ fontSize: 13 }}>
                {t("ui.BillingPage.steps")}
              </p>
              <form onSubmit={(e) => void issueMsa(e, true)} style={{ marginBottom: 12 }}>
                <button
                  type="submit"
                  className="btn primary"
                  data-testid="billing-pilot-msa"
                  onClick={() => trackEvent("billing_cta", { source: "pilot_msa" })}
                >
                  {t("ui.BillingPage.issuePilot")}
                </button>
              </form>
              <form onSubmit={(e) => void issueMsa(e, false)}>
                <button type="submit" className="btn ghost">
                  {t("ui.BillingPage.issueDesk")}
                </button>
              </form>
            </>
          )}
          {msg && (
            <p className="muted" style={{ whiteSpace: "pre-wrap" }}>
              {msg}
            </p>
          )}
          {error && <p className="error">{error}</p>}
          <h3>{t("ui.BillingPage.invoices")}</h3>
          {invoices.length === 0 ? (
            <p className="muted">{t("ui.BillingPage.noInvoices")}</p>
          ) : (
            <div className="table-scroll">
              <table className="table" data-testid="billing-invoices">
                <thead>
                  <tr>
                    <th>{t("ui.BillingPage.colId")}</th>
                    <th>{t("ui.BillingPage.colPlan")}</th>
                    <th>{t("ui.BillingPage.colAmount")}</th>
                    <th>{t("ui.BillingPage.colStatus")}</th>
                    <th>{t("ui.BillingPage.colDate")}</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv, i) => (
                    <tr key={inv.id || i}>
                      <td>{inv.id || "—"}</td>
                      <td>{inv.plan || "—"}</td>
                      <td>{inv.amount_inr != null ? `₹${inv.amount_inr}` : "—"}</td>
                      <td>{inv.status || "—"}</td>
                      <td>{inv.created_at ? String(inv.created_at).slice(0, 10) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      <Disclaimer />
    </section>
  );
}
