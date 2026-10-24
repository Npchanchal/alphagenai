import { useEffect, useState } from "react";
import CompanyPicker from "../../components/CompanyPicker";
import {
  fetchCompanies,
  fetchSightsEnterprise,
  fetchSightsFundamentals,
  postSightsDeepDive,
  postSightsGrid,
  type CompanySummary,
} from "../../lib/api";
import { Link } from "react-router-dom";
import { formatScore } from "../../lib/score";
import { useI18n } from "../../i18n";

function errorText(e: unknown, fallback: string): string {
  return e instanceof Error ? e.message : fallback;
}

function useCompanyFocus() {
  const { t } = useI18n();
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [focusError, setFocusError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchCompanies({ limit: 20 })
      .then((rows) => {
        if (cancelled) return;
        setCompanies(rows);
        if (rows[0]) setCompanyId(rows[0].id);
      })
      .catch((e) => {
        if (!cancelled) setFocusError(errorText(e, t("ui.SightsAdvancedPages.err.companies")));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { companies, companyId, setCompanyId, focusError };
}

export function SightsGridPage() {
  const { t } = useI18n();
  const { companies, companyId, focusError } = useCompanyFocus();
  const [prompt, setPrompt] = useState("margin guidance");
  const [rows, setRows] = useState<
    { prompt: string; cells: { company_id: string; answer?: string; refused: boolean }[] }[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const ids = companies.slice(0, 3).map((c) => c.id);
      const res = await postSightsGrid({
        prompts: [prompt],
        company_ids: ids.length ? ids : companyId ? [companyId] : undefined,
      });
      setRows(res.rows || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("ui.SightsAdvancedPages.err.grid"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sights-panel" data-testid="sights-grid">
      <h2>{t("ui.SightsAdvancedPages.grid.title")}</h2>
      <p className="muted">{t("ui.SightsAdvancedPages.grid.subtitle")}</p>
      <div className="row gap">
        <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button type="button" className="btn" disabled={busy} onClick={() => void run()}>
          {busy ? t("ui.SightsAdvancedPages.grid.running") : t("ui.SightsAdvancedPages.grid.run")}
        </button>
      </div>
      {(error || focusError) && <p className="error">{error || focusError}</p>}
      {rows.map((r) => (
        <div key={r.prompt}>
          <h3>{r.prompt}</h3>
          <div className="sights-grid-row">
            {r.cells.map((c) => (
              <div key={c.company_id} className="sights-grid-cell">
                <strong>{c.company_id}</strong>
                <p className={c.refused ? "muted" : ""}>{c.answer}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

export function SightsDeepDivePage() {
  const { t } = useI18n();
  const { companies, companyId, setCompanyId, focusError } = useCompanyFocus();
  const [topic, setTopic] = useState("guidance delivery");
  const [report, setReport] = useState<string | null>(null);
  const [refused, setRefused] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await postSightsDeepDive({ topic, company_id: companyId || undefined });
      setRefused(!!res.refused);
      setMessage(res.message || "");
      setReport(res.report || null);
    } catch (e) {
      setError(errorText(e, t("ui.SightsAdvancedPages.err.deepDive")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sights-panel" data-testid="sights-deep-dive">
      <h2>{t("ui.SightsAdvancedPages.deepDive.title")}</h2>
      <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
      <div className="row gap">
        <input className="input" value={topic} onChange={(e) => setTopic(e.target.value)} />
        <button type="button" className="btn" disabled={busy} onClick={() => void run()}>
          {busy ? t("ui.SightsAdvancedPages.deepDive.running") : t("ui.SightsAdvancedPages.deepDive.run")}
        </button>
      </div>
      {(error || focusError) && <p className="error">{error || focusError}</p>}
      {refused && <p className="callout warn">{message}</p>}
      {report && <pre className="code-block">{report}</pre>}
    </section>
  );
}

export function SightsFundamentalsPage() {
  const { t } = useI18n();
  const { companies, companyId, setCompanyId, focusError } = useCompanyFocus();
  const [gci, setGci] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;
    setError(null);
    fetchSightsFundamentals(companyId)
      .then((r) => {
        if (cancelled) return;
        setNote(r.note);
        const score = r.snapshot?.gci?.score;
        setGci(typeof score === "number" ? score : null);
      })
      .catch((e) => {
        if (!cancelled) setError(errorText(e, t("ui.SightsAdvancedPages.err.fundamentals")));
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return (
    <section className="sights-panel" data-testid="sights-fundamentals">
      <h2>{t("ui.SightsAdvancedPages.fundamentals.title")}</h2>
      <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
      {(error || focusError) && <p className="error">{error || focusError}</p>}
      <p className="muted">{note}</p>
      <p>
        GCI {formatScore(gci)} ·{" "}
        <Link to={`/companies/${companyId}`}>{t("ui.SightsAdvancedPages.fundamentals.openDossier")}</Link>
      </p>
    </section>
  );
}

export function SightsSettingsPage() {
  const { t } = useI18n();
  const [links, setLinks] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [sso, setSso] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSightsEnterprise()
      .then((r) => {
        if (cancelled) return;
        setLinks(r.links || {});
        setNote(r.note);
        setSso(!!r.sso_configured_flag);
      })
      .catch((e) => {
        if (!cancelled) setError(errorText(e, t("ui.SightsAdvancedPages.err.enterprise")));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="sights-panel" data-testid="sights-settings">
      <h2>{t("ui.SightsAdvancedPages.settings.title")}</h2>
      {error && <p className="error">{error}</p>}
      <p className="muted">{note}</p>
      <p>
        {t("ui.SightsAdvancedPages.settings.sso", {
          state: sso ? t("ui.SightsAdvancedPages.settings.on") : t("ui.SightsAdvancedPages.settings.off"),
        })}
      </p>
      <ul>
        {Object.entries(links).map(([k, v]) => (
          <li key={k}>
            {k}:{" "}
            {v.startsWith("/") ? (
              <Link to={v}>{v}</Link>
            ) : (
              <code>{v}</code>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
