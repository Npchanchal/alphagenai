import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import LanguageSelect from "../components/LanguageSelect";
import {
  fetchCompanies,
  fetchMarkets,
  fetchMarketIndexes,
  postMfaConfirm,
  postMfaDisable,
  postMfaEnroll,
  type CompanySummary,
  type Market,
  type MarketIndex,
} from "../lib/api";
import { analyticsConfigured, writeAnalyticsConsent, initAnalytics } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { useI18n } from "../i18n";
import type { LangCode } from "../i18n/languages";

/** Unified account + preferences — syncs via `/api/auth/preferences`. */
export default function AccountSettingsPage() {
  const { t } = useI18n();
  const { user, preferences, updatePreferences, loading } = useAuth();
  const [markets, setMarkets] = useState<Market[]>([]);
  const [indexes, setIndexes] = useState<MarketIndex[]>([]);
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [addId, setAddId] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  const market = preferences?.default_market ?? "IN";
  const index = preferences?.default_index ?? "SENSEX";
  const watchlist = preferences?.watchlist ?? [];
  const density = preferences?.density ?? "compact";
  const showDemoTape = preferences?.show_demo_tape ?? true;
  const analyticsConsent = preferences?.analytics_consent;

  useEffect(() => {
    fetchMarkets()
      .then((r) => setMarkets(r.markets))
      .catch(() => setMarkets([]));
  }, []);

  useEffect(() => {
    fetchMarketIndexes(market)
      .then((r) => setIndexes(r.indexes))
      .catch(() => setIndexes([]));
  }, [market]);

  useEffect(() => {
    fetchCompanies({ market, index, limit: 500 })
      .then(setCompanies)
      .catch(() => setCompanies([]));
  }, [market, index]);

  const companyById = useMemo(() => {
    const map = new Map<string, CompanySummary>();
    for (const c of companies) map.set(c.id, c);
    return map;
  }, [companies]);

  const addCandidates = companies.filter((c) => !watchlist.includes(c.id));

  async function patch(p: Parameters<typeof updatePreferences>[0]) {
    setMsg(null);
    try {
      await updatePreferences(p);
      setMsg(t("ui.AccountSettingsPage.saved"));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : t("ui.AccountSettingsPage.saveFailed"));
    }
  }

  async function setAnalytics(granted: boolean) {
    writeAnalyticsConsent(granted);
    if (granted && analyticsConfigured()) initAnalytics();
    await patch({ analytics_consent: granted });
  }

  if (loading) {
    return (
      <section className="settings-page" data-testid="account-settings-page">
        <p className="muted">{t("common.loading")}</p>
      </section>
    );
  }

  return (
    <section className="settings-page" data-testid="account-settings-page">
      <p className="page-kicker">{t("common.account")}</p>
      <h1>{t("prefs.title")}</h1>
      <p className="muted lede">
        {t("ui.AccountSettingsPage.lede")}
      </p>

      <div className="settings-grid">
        <div className="panel settings-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.profile")}</h2>
          {!user ? (
            <p className="muted">
              <Link to="/login" state={{ from: "/account" }}>
                {t("common.login")}
              </Link>{" "}
              {t("ui.AccountSettingsPage.or")}{" "}
              <Link to="/register">{t("ui.AccountSettingsPage.registerLink")}</Link> {t("ui.AccountSettingsPage.syncHint")}
            </p>
          ) : (
            <dl className="settings-dl">
              <div>
                <dt>{t("ui.AccountSettingsPage.name")}</dt>
                <dd>{user.name || "—"}</dd>
              </div>
              <div>
                <dt>{t("auth.email")}</dt>
                <dd>{user.email || "—"}</dd>
              </div>
              <div>
                <dt>{t("common.account")}</dt>
                <dd>
                  {user.kind === "guest" ? t("ui.AccountSettingsPage.guest") : user.account_type ?? t("ui.AccountSettingsPage.registered")} · {t("ui.AccountSettingsPage.role")}{" "}
                  <code>{user.role ?? "—"}</code>
                </dd>
              </div>
              {user.org_id && (
                <div>
                  <dt>{t("ui.AccountSettingsPage.organization")}</dt>
                  <dd>
                    <code>{user.org_id}</code>{" "}
                    {(user.role === "owner" || user.role === "admin") && (
                      <Link to="/org/settings">{t("ui.AccountSettingsPage.orgSettings")}</Link>
                    )}
                  </dd>
                </div>
              )}
            </dl>
          )}
          {user && user.kind !== "guest" && (
            <p style={{ marginTop: 12 }}>
              <Link to="/billing" className="btn">
                {t("footer.billing")}
              </Link>
            </p>
          )}
        </div>

        {(user?.role === "owner" || user?.role === "admin") && (
          <div className="panel settings-panel" data-testid="account-mfa">
            <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.mfa")}</h2>
            <p className="muted" style={{ fontSize: 13 }}>
              {t("ui.AccountSettingsPage.mfaHint")}
            </p>
            <p>
              {user.mfa_enabled
                ? t("ui.AccountSettingsPage.mfaOn")
                : t("ui.AccountSettingsPage.mfaOff")}
            </p>
            {mfaSecret && (
              <p className="muted" style={{ fontSize: 13 }}>
                {t("ui.AccountSettingsPage.mfaSecret")}: <code>{mfaSecret}</code>
              </p>
            )}
            <div className="auth-form settings-form">
              <label>
                {t("auth.totp")}
                <input
                  type="text"
                  inputMode="numeric"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  data-testid="account-mfa-code"
                />
              </label>
            </div>
            <div className="row gap">
              <button
                type="button"
                className="btn-ghost"
                data-testid="account-mfa-enroll"
                onClick={() => {
                  void postMfaEnroll()
                    .then((r) => {
                      setMfaSecret(r.secret);
                      setMsg(t("ui.AccountSettingsPage.mfaSecret"));
                    })
                    .catch((e) =>
                      setMsg(e instanceof Error ? e.message : t("ui.AccountSettingsPage.saveFailed")),
                    );
                }}
              >
                {t("ui.AccountSettingsPage.mfaEnroll")}
              </button>
              <button
                type="button"
                className="btn-primary"
                data-testid="account-mfa-confirm"
                onClick={() => {
                  void postMfaConfirm(mfaCode)
                    .then(() => {
                      setMfaSecret(null);
                      setMfaCode("");
                      setMsg(t("ui.AccountSettingsPage.saved"));
                    })
                    .catch((e) =>
                      setMsg(e instanceof Error ? e.message : t("ui.AccountSettingsPage.saveFailed")),
                    );
                }}
              >
                {t("ui.AccountSettingsPage.mfaVerify")}
              </button>
              {user.mfa_enabled && (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    void postMfaDisable(mfaCode)
                      .then(() => {
                        setMfaCode("");
                        setMsg(t("ui.AccountSettingsPage.saved"));
                      })
                      .catch((e) =>
                        setMsg(e instanceof Error ? e.message : t("ui.AccountSettingsPage.saveFailed")),
                      );
                  }}
                >
                  {t("ui.AccountSettingsPage.mfaDisable")}
                </button>
              )}
            </div>
          </div>
        )}

        <div className="panel settings-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.locale")}</h2>
          <div className="auth-form settings-form">
            <label>
              {t("common.language")}
              <LanguageSelect
                onChange={(code: LangCode) => {
                  void patch({ language: code });
                }}
              />
            </label>
            <label>
              {t("common.market")}
              <select
                value={market}
                onChange={(e) => {
                  const m = e.target.value;
                  void fetchMarketIndexes(m).then((r) => {
                    setIndexes(r.indexes);
                    const nextIx = r.indexes[0]?.id;
                    void patch({
                      default_market: m,
                      ...(nextIx ? { default_index: nextIx } : {}),
                    });
                  });
                }}
                data-testid="account-pref-market"
              >
                {markets.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("common.index")}
              <select
                value={index}
                onChange={(e) => void patch({ default_index: e.target.value })}
                data-testid="account-pref-index"
              >
                {indexes.map((ix) => (
                  <option key={ix.id} value={ix.id}>
                    {ix.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="panel settings-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.display")}</h2>
          <div className="auth-form settings-form">
            <label>
              {t("prefs.density")}
              <select
                value={density}
                onChange={(e) =>
                  void patch({ density: e.target.value as "comfortable" | "compact" })
                }
                data-testid="account-pref-density"
              >
                <option value="comfortable">{t("ui.AccountSettingsPage.comfortable")}</option>
                <option value="compact">{t("ui.AccountSettingsPage.compact")}</option>
              </select>
            </label>
            <label className="settings-check">
              <input
                type="checkbox"
                checked={showDemoTape}
                onChange={(e) => void patch({ show_demo_tape: e.target.checked })}
                data-testid="account-pref-demo-tape"
              />
              {t("prefs.demoTape")}
            </label>
          </div>
        </div>

        <div className="panel settings-panel">
          <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.watchlist")}</h2>
          <p className="muted" style={{ fontSize: 13 }}>
            {t("ui.AccountSettingsPage.watchlistHint")}
          </p>
          {watchlist.length === 0 ? (
            <p className="muted">{t("ui.AccountSettingsPage.watchlistEmpty")}</p>
          ) : (
            <ul className="settings-watchlist" data-testid="account-watchlist">
              {watchlist.map((id) => {
                const c = companyById.get(id);
                return (
                  <li key={id}>
                    <span>
                      {c ? `${c.ticker} — ${c.name}` : id}
                    </span>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() =>
                        void patch({ watchlist: watchlist.filter((x) => x !== id) })
                      }
                    >
                      {t("ui.AccountSettingsPage.remove")}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {addCandidates.length > 0 && (
            <div className="settings-add-row">
              <select
                value={addId || addCandidates[0]?.id || ""}
                onChange={(e) => setAddId(e.target.value)}
                aria-label={t("ui.AccountSettingsPage.addAria")}
              >
                {addCandidates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.ticker} — {c.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn"
                data-testid="account-watchlist-add"
                onClick={() => {
                  const id = addId || addCandidates[0]?.id;
                  if (!id || watchlist.includes(id)) return;
                  void patch({ watchlist: [...watchlist, id] });
                  setAddId("");
                }}
              >
                {t("ui.AccountSettingsPage.add")}
              </button>
            </div>
          )}
          {watchlist.length > 0 && (
            <button
              type="button"
              className="btn-ghost"
              style={{ marginTop: 8 }}
              onClick={() => void patch({ watchlist: [] })}
            >
              {t("ui.AccountSettingsPage.clear")}
            </button>
          )}
        </div>

        {analyticsConfigured() && (
          <div className="panel settings-panel">
            <h2 style={{ marginTop: 0 }}>{t("ui.AccountSettingsPage.analytics")}</h2>
            <p className="muted" style={{ fontSize: 13 }}>
              {t("ui.AccountSettingsPage.analyticsHint")}
            </p>
            <p>
              {t("ui.AccountSettingsPage.current")}{" "}
              <strong>
                {analyticsConsent === true
                  ? t("ui.AccountSettingsPage.accepted")
                  : analyticsConsent === false
                    ? t("ui.AccountSettingsPage.declined")
                    : t("ui.AccountSettingsPage.notSet")}
              </strong>
            </p>
            <div className="row gap">
              <button type="button" className="btn-primary" onClick={() => void setAnalytics(true)}>
                {t("ui.ConsentBanner.accept")}
              </button>
              <button type="button" className="btn-ghost" onClick={() => void setAnalytics(false)}>
                {t("ui.ConsentBanner.decline")}
              </button>
            </div>
          </div>
        )}
      </div>

      {msg && (
        <p className="muted" style={{ marginTop: 16 }} data-testid="account-settings-msg">
          {msg}
        </p>
      )}
    </section>
  );
}
