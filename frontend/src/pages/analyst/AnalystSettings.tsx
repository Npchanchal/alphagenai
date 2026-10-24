import { useEffect, useState } from "react";
import {
  clearAnalystHouseAsset,
  deleteAnalystDestination,
  deleteAnalystKey,
  downloadHouseStylePreview,
  fetchAnalystDestinations,
  fetchAnalystDigest,
  fetchAnalystHouseStyle,
  fetchAnalystKeys,
  postAnalystDestination,
  postAnalystHouseTemplate,
  postAnalystKey,
  putAnalystDigest,
  putAnalystHouseStyle,
  resetAnalystHouseStyle,
  testAnalystDestination,
  type AnalystDeliveryLogRow,
  type AnalystDestination,
  type AnalystDestinationKind,
  type AnalystDigestSettings,
  type AnalystHouseStyle,
  type AnalystOrgKey,
} from "../../lib/api";
import { useI18n } from "../../i18n";

export function errorText(e: unknown, fallback: string): string {
  return e instanceof Error && e.message ? e.message : fallback;
}

export function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

const MAX_LOGO_BYTES = 500 * 1024;
const MAX_TEMPLATE_BYTES = 5 * 1024 * 1024;

function useAction(fallback: string) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function act<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(errorText(e, fallback));
      return undefined;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, act };
}

export function DigestPanel() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<AnalystDigestSettings | null>(null);
  const [preview, setPreview] = useState("");
  const [emails, setEmails] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [saved, setSaved] = useState(false);
  const { busy, error, setError, act } = useAction(t("analyst.digest.err"));

  useEffect(() => {
    fetchAnalystDigest()
      .then((d) => {
        setSettings(d.settings);
        setEnabled(d.settings.enabled);
        setEmails(d.settings.emails.join(", "));
        setPreview(d.text);
      })
      .catch((e) => setError(errorText(e, t("analyst.digest.err"))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setSaved(false);
    const list = emails
      .split(/[,\s]+/)
      .map((x) => x.trim())
      .filter(Boolean);
    const out = await act(() => putAnalystDigest({ enabled, emails: list }));
    if (out) {
      setSettings(out);
      setEmails(out.emails.join(", "));
      setSaved(true);
    }
  }

  return (
    <section className="panel" data-testid="analyst-digest">
      <div className="panel-head">
        <h2>{t("analyst.digest.title")}</h2>
      </div>
      <p className="muted analyst-small">{t("analyst.digest.lede")}</p>
      <div className="analyst-monitor-form">
        <label className="analyst-check">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            data-testid="analyst-digest-enabled"
          />
          {t("analyst.digest.enabled")}
        </label>
        <label>
          {t("analyst.digest.emails")}
          <input
            value={emails}
            onChange={(e) => setEmails(e.target.value)}
            placeholder={t("analyst.digest.emailsPlaceholder")}
            data-testid="analyst-digest-emails"
          />
        </label>
        <button type="button" className="btn-primary" disabled={busy} onClick={() => void save()} data-testid="analyst-digest-save">
          {t("analyst.digest.save")}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {saved && <p className="muted analyst-small">{t("analyst.digest.saved")}</p>}
      {settings?.last_sent_at && (
        <p className="muted analyst-small">{t("analyst.digest.lastSent", { date: settings.last_sent_at })}</p>
      )}
      {preview && (
        <details>
          <summary>{t("analyst.digest.preview")}</summary>
          <pre className="code-block" data-testid="analyst-digest-preview">{preview}</pre>
        </details>
      )}
    </section>
  );
}

export function HouseStylePanel({ canEdit }: { canEdit: boolean }) {
  const { t } = useI18n();
  const [style, setStyle] = useState<AnalystHouseStyle | null>(null);
  const [logo, setLogo] = useState<string | undefined>(undefined);
  const [saved, setSaved] = useState(false);
  const { busy, error, setError, act } = useAction(t("analyst.style.err"));

  useEffect(() => {
    fetchAnalystHouseStyle()
      .then(setStyle)
      .catch((e) => setError(errorText(e, t("analyst.style.err"))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!style) {
    return error ? (
      <section className="panel" data-testid="analyst-house-style">
        <p className="error">{error}</p>
      </section>
    ) : null;
  }

  const set = (k: keyof AnalystHouseStyle, v: string) => {
    setSaved(false);
    setStyle({ ...style, [k]: v });
  };

  async function save() {
    if (!style) return;
    const { firm_name, primary_color, accent_color, font, footer, classification, fonts } = style;
    const out = await act(() =>
      putAnalystHouseStyle({ firm_name, primary_color, accent_color, font, footer, classification, logo_base64: logo })
    );
    if (out) {
      setStyle({ ...out, fonts });
      setLogo(undefined);
      setSaved(true);
    }
  }

  async function pickLogo(file: File) {
    if (file.size > MAX_LOGO_BYTES) {
      setError(t("analyst.style.logoTooLarge"));
      return;
    }
    setLogo(await toBase64(file));
  }

  async function uploadTemplate(file: File) {
    if (file.size > MAX_TEMPLATE_BYTES) {
      setError(t("analyst.style.templateTooLarge"));
      return;
    }
    const out = await act(async () =>
      postAnalystHouseTemplate({ filename: file.name, content_base64: await toBase64(file) })
    );
    if (out && style) setStyle({ ...out, fonts: style.fonts });
  }

  async function clear(asset: "template" | "logo") {
    const out = await act(() => clearAnalystHouseAsset(asset));
    if (out && style) setStyle({ ...out, fonts: style.fonts });
  }

  async function reset() {
    if (!window.confirm(t("analyst.style.confirmReset"))) return;
    const out = await act(() => resetAnalystHouseStyle());
    if (out && style) setStyle({ ...out, fonts: style.fonts });
  }

  return (
    <section className="panel" data-testid="analyst-house-style">
      <div className="panel-head">
        <h2>{t("analyst.style.title")}</h2>
      </div>
      <p className="muted analyst-small">
        {style.configured ? t("analyst.style.ledeOn") : t("analyst.style.ledeOff")}
      </p>
      <div className="analyst-monitor-form">
        <label>
          {t("analyst.style.firm")}
          <input value={style.firm_name} disabled={!canEdit} maxLength={80} onChange={(e) => set("firm_name", e.target.value)} data-testid="analyst-style-firm" />
        </label>
        <label>
          {t("analyst.style.primary")}
          <input type="color" value={style.primary_color} disabled={!canEdit} onChange={(e) => set("primary_color", e.target.value.toUpperCase())} />
        </label>
        <label>
          {t("analyst.style.accent")}
          <input type="color" value={style.accent_color} disabled={!canEdit} onChange={(e) => set("accent_color", e.target.value.toUpperCase())} />
        </label>
        <label>
          {t("analyst.style.font")}
          <select value={style.font} disabled={!canEdit} onChange={(e) => set("font", e.target.value)}>
            {style.fonts.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("analyst.style.footer")}
          <input value={style.footer} disabled={!canEdit} maxLength={160} onChange={(e) => set("footer", e.target.value)} />
        </label>
        <label>
          {t("analyst.style.classification")}
          <input
            value={style.classification}
            disabled={!canEdit}
            maxLength={60}
            placeholder={t("analyst.style.classificationPlaceholder")}
            onChange={(e) => set("classification", e.target.value)}
          />
        </label>
        {canEdit && (
          <label>
            {t("analyst.style.logo")}
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void pickLogo(f);
              }}
            />
          </label>
        )}
      </div>
      <p className="muted analyst-small">
        {style.has_logo ? t("analyst.style.hasLogo") : t("analyst.style.noLogo")} ·{" "}
        {style.has_template ? t("analyst.style.hasTemplate") : t("analyst.style.noTemplate")}
      </p>
      {canEdit && (
        <div className="analyst-actions">
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void save()} data-testid="analyst-style-save">
            {t("analyst.style.save")}
          </button>
          <label className="btn ghost small">
            {t("analyst.style.uploadTemplate")}
            <input
              type="file"
              hidden
              accept=".pptx,.potx"
              data-testid="analyst-style-template"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void uploadTemplate(f);
                e.target.value = "";
              }}
            />
          </label>
          {style.has_template && (
            <button type="button" className="btn ghost small" disabled={busy} onClick={() => void clear("template")}>
              {t("analyst.style.removeTemplate")}
            </button>
          )}
          {style.has_logo && (
            <button type="button" className="btn ghost small" disabled={busy} onClick={() => void clear("logo")}>
              {t("analyst.style.removeLogo")}
            </button>
          )}
          {style.configured && (
            <button type="button" className="btn ghost small" disabled={busy} onClick={() => void reset()}>
              {t("analyst.style.reset")}
            </button>
          )}
        </div>
      )}
      <p>
        <button
          type="button"
          className="btn ghost small"
          disabled={busy}
          onClick={() => void act(() => downloadHouseStylePreview())}
          data-testid="analyst-style-preview"
        >
          {t("analyst.style.preview")}
        </button>
      </p>
      {!canEdit && <p className="muted analyst-small">{t("analyst.adminOnly")}</p>}
      {error && <p className="error">{error}</p>}
      {saved && <p className="muted analyst-small">{t("analyst.style.saved")}</p>}
    </section>
  );
}

export function KeysPanel() {
  const { t } = useI18n();
  const [keys, setKeys] = useState<AnalystOrgKey[]>([]);
  const [limit, setLimit] = useState(0);
  const [label, setLabel] = useState("");
  const [role, setRole] = useState<"analyst" | "viewer">("analyst");
  const [fresh, setFresh] = useState<string | null>(null);
  const { busy, error, act } = useAction(t("analyst.keys.err"));

  const load = () =>
    void act(async () => {
      const r = await fetchAnalystKeys();
      setKeys(r.keys);
      setLimit(r.limit);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  async function create() {
    const out = await act(() => postAnalystKey({ label: label.trim() || "API key", role }));
    if (out) {
      setFresh(out.key);
      setLabel("");
      load();
    }
  }

  async function revoke(k: AnalystOrgKey) {
    if (!window.confirm(t("analyst.keys.confirmRevoke", { label: k.label }))) return;
    if (await act(() => deleteAnalystKey(k.key_id))) load();
  }

  return (
    <section className="panel" data-testid="analyst-keys">
      <div className="panel-head">
        <h2>{t("analyst.keys.title")}</h2>
      </div>
      <p className="muted analyst-small">{t("analyst.keys.lede", { limit })}</p>
      <div className="analyst-monitor-form">
        <label>
          {t("analyst.keys.label")}
          <input value={label} maxLength={80} onChange={(e) => setLabel(e.target.value)} placeholder={t("analyst.keys.labelPlaceholder")} />
        </label>
        <label>
          {t("analyst.keys.role")}
          <select value={role} onChange={(e) => setRole(e.target.value as "analyst" | "viewer")}>
            <option value="analyst">{t("analyst.keys.roleAnalyst")}</option>
            <option value="viewer">{t("analyst.keys.roleViewer")}</option>
          </select>
        </label>
        <button type="button" className="btn-primary" disabled={busy} onClick={() => void create()} data-testid="analyst-key-create">
          {t("analyst.keys.create")}
        </button>
      </div>
      {fresh && (
        <div className="callout" data-testid="analyst-key-fresh">
          <p>{t("analyst.keys.copyNow")}</p>
          <code>{fresh}</code>{" "}
          <button type="button" className="btn ghost small" onClick={() => void navigator.clipboard?.writeText(fresh)}>
            {t("analyst.keys.copy")}
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      {keys.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>{t("analyst.keys.label")}</th>
              <th>{t("analyst.keys.role")}</th>
              <th>{t("analyst.keys.prefix")}</th>
              <th>{t("analyst.keys.lastUsed")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.key_id}>
                <td>{k.label}</td>
                <td>{k.role === "viewer" ? t("analyst.keys.roleViewer") : t("analyst.keys.roleAnalyst")}</td>
                <td>
                  <code>{k.prefix}…</code>
                </td>
                <td>{k.last_used_at || t("analyst.monitors.never")}</td>
                <td>
                  <button type="button" className="btn ghost small" disabled={busy} onClick={() => void revoke(k)}>
                    {t("analyst.keys.revoke")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted analyst-small">
        {t("analyst.keys.docs")} <a href="/developers">{t("products.openDevelopers")}</a>
      </p>
    </section>
  );
}

const EVENT_KEYS: Record<string, string> = {
  "monitor.run": "analyst.dest.eventMonitor",
  "digest.weekly": "analyst.dest.eventDigest",
};

export function DestinationsPanel() {
  const { t } = useI18n();
  const [dests, setDests] = useState<AnalystDestination[]>([]);
  const [log, setLog] = useState<AnalystDeliveryLogRow[]>([]);
  const [events, setEvents] = useState<string[]>(["monitor.run", "digest.weekly"]);
  const [kind, setKind] = useState<AnalystDestinationKind>("slack");
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [chosen, setChosen] = useState<string[]>(["monitor.run", "digest.weekly"]);
  const [secret, setSecret] = useState<string | null>(null);
  const [tested, setTested] = useState<Record<string, AnalystDeliveryLogRow | null>>({});
  const { busy, error, act } = useAction(t("analyst.dest.err"));

  const load = () =>
    void act(async () => {
      const r = await fetchAnalystDestinations();
      setDests(r.destinations);
      setLog(r.log);
      setEvents(r.events);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  async function add() {
    const out = await act(() =>
      postAnalystDestination({ kind, url: url.trim(), events: chosen, label: label.trim() || undefined })
    );
    if (out) {
      setSecret(out.secret || null);
      setUrl("");
      setLabel("");
      load();
    }
  }

  async function test(id: string) {
    const out = await act(() => testAnalystDestination(id));
    if (out) {
      setTested((prev) => ({ ...prev, [id]: out.result }));
      load();
    }
  }

  async function remove(d: AnalystDestination) {
    if (!window.confirm(t("analyst.dest.confirmRemove", { label: d.label }))) return;
    if (await act(() => deleteAnalystDestination(d.destination_id))) load();
  }

  const kindLabel = (k: string) => t(`analyst.dest.kind.${k}`);

  return (
    <section className="panel" data-testid="analyst-destinations">
      <div className="panel-head">
        <h2>{t("analyst.dest.title")}</h2>
      </div>
      <p className="muted analyst-small">{t("analyst.dest.lede")}</p>
      <div className="analyst-monitor-form">
        <label>
          {t("analyst.dest.kindLabel")}
          <select value={kind} onChange={(e) => setKind(e.target.value as AnalystDestinationKind)} data-testid="analyst-dest-kind">
            {(["slack", "teams", "webhook"] as const).map((k) => (
              <option key={k} value={k}>
                {kindLabel(k)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("analyst.dest.url")}
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t(`analyst.dest.urlPlaceholder.${kind}`)}
            data-testid="analyst-dest-url"
          />
        </label>
        <label>
          {t("analyst.dest.label")}
          <input value={label} maxLength={80} onChange={(e) => setLabel(e.target.value)} />
        </label>
        <fieldset className="analyst-events">
          {events.map((ev) => (
            <label key={ev} className="analyst-check">
              <input
                type="checkbox"
                checked={chosen.includes(ev)}
                onChange={(e) =>
                  setChosen((prev) => (e.target.checked ? [...prev, ev] : prev.filter((x) => x !== ev)))
                }
              />
              {t(EVENT_KEYS[ev] || ev)}
            </label>
          ))}
        </fieldset>
        <button
          type="button"
          className="btn-primary"
          disabled={busy || !url.trim() || chosen.length === 0}
          onClick={() => void add()}
          data-testid="analyst-dest-add"
        >
          {t("analyst.dest.add")}
        </button>
      </div>
      {secret && (
        <div className="callout" data-testid="analyst-dest-secret">
          <p>{t("analyst.dest.secretNow")}</p>
          <code>{secret}</code>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      {dests.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>{t("analyst.dest.label")}</th>
              <th>{t("analyst.dest.kindLabel")}</th>
              <th>{t("analyst.dest.url")}</th>
              <th>{t("analyst.dest.events")}</th>
              <th>{t("analyst.dest.lastStatus")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {dests.map((d) => {
              const r = tested[d.destination_id];
              return (
                <tr key={d.destination_id}>
                  <td>{d.label}</td>
                  <td>{kindLabel(d.kind)}</td>
                  <td>
                    <code>{d.url}</code>
                  </td>
                  <td>{d.events.map((ev) => t(EVENT_KEYS[ev] || ev)).join(", ")}</td>
                  <td>
                    {r
                      ? r.ok
                        ? t("analyst.dest.testOk", { status: r.status })
                        : t("analyst.dest.testFailed", { status: r.status || r.error || "—" })
                      : d.last_status ?? "—"}
                  </td>
                  <td className="row gap">
                    <button type="button" className="btn ghost small" disabled={busy} onClick={() => void test(d.destination_id)} data-testid="analyst-dest-test">
                      {t("analyst.dest.test")}
                    </button>
                    <button type="button" className="btn ghost small" disabled={busy} onClick={() => void remove(d)}>
                      {t("analyst.dest.remove")}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {log.length > 0 && (
        <details>
          <summary>{t("analyst.dest.log")}</summary>
          <ul className="doc-list">
            {log.slice(0, 20).map((row, i) => (
              <li key={`${row.at}-${i}`} className="analyst-small">
                {row.at} · {kindLabel(row.kind)} · {t(EVENT_KEYS[row.event] || row.event)} ·{" "}
                {row.ok ? t("analyst.dest.testOk", { status: row.status }) : t("analyst.dest.testFailed", { status: row.status || row.error || "—" })}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
