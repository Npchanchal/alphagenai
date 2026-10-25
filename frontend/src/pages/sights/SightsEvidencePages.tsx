import { useEffect, useState } from "react";
import QualityBadge from "../../components/QualityBadge";
import CompanyPicker from "../../components/CompanyPicker";
import CitationCard from "../../components/CitationCard";
import {
  fetchCompanies,
  fetchSightsField,
  fetchSightsStreet,
  fetchSightsThemes,
  type CompanySummary,
  type CitationRecord,
} from "../../lib/api";
import { useSourceViewer } from "../../lib/SourceViewerContext";
import { withTextHighlight } from "../../lib/sourceHighlight";
import { useI18n } from "../../i18n";
import { compareEvidenceLatestFirst, metricDisplayName } from "../../lib/score";

export function SightsThemesPage() {
  const { t } = useI18n();
  const [themes, setThemes] = useState<{ theme: string; count: number; note: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSightsThemes({ limit: 30 })
      .then((r) => {
        if (!cancelled) setThemes(r.themes || []);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : t("ui.SightsEvidencePages.failed"));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="sights-panel" data-testid="sights-themes">
      <h2>{t("ui.SightsEvidencePages.themes.title")}</h2>
      <p className="muted">{t("ui.SightsEvidencePages.themes.subtitle")}</p>
      {error && <p className="error">{error}</p>}
      <table className="table">
        <thead>
          <tr>
            <th>{t("ui.SightsEvidencePages.themes.th.theme")}</th>
            <th>{t("ui.SightsEvidencePages.themes.th.count")}</th>
          </tr>
        </thead>
        <tbody>
          {themes.map((row) => (
            <tr key={row.theme}>
              <td>{row.theme}</td>
              <td>{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
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
        if (!cancelled) setFocusError(e instanceof Error ? e.message : t("ui.SightsEvidencePages.loadCompaniesFailed"));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { companies, companyId, setCompanyId, focusError };
}

export function SightsStreetPage() {
  const { t } = useI18n();
  const { companies, companyId, setCompanyId, focusError } = useCompanyFocus();
  const { openSource } = useSourceViewer();
  const [note, setNote] = useState("");
  const [snippets, setSnippets] = useState<
    { id?: string; title?: string; snippet?: string; date?: string; url?: string }[]
  >([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;
    fetchSightsStreet(companyId)
      .then((r) => {
        if (cancelled) return;
        setNote(r.note);
        setSnippets(r.public_filing_snippets || []);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : t("ui.SightsEvidencePages.failed"));
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return (
    <section className="sights-panel" data-testid="sights-street">
      <h2>{t("ui.SightsEvidencePages.street.title")}</h2>
      <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
      <p className="muted">{note}</p>
      {(error || focusError) && <p className="error">{error || focusError}</p>}
      <ul className="doc-list">
        {[...snippets]
          .sort((a, b) => (b.date || "").localeCompare(a.date || ""))
          .map((s, i) => (
          <li key={i}>
            <strong>{s.title}</strong> <span className="muted">{s.date}</span>
            <p>{s.snippet}</p>
            {(s.url || s.snippet) && (
              <button
                type="button"
                className="linkish"
                onClick={() =>
                  openSource({
                    doc_id: s.id,
                    title: s.title,
                    source_url: s.url,
                    highlight_url: withTextHighlight(s.url, s.snippet),
                    quote: s.snippet,
                    document_text: s.snippet,
                    company_id: companyId,
                  })
                }
              >
                {t("ui.SightsEvidencePages.openSource")}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SightsFieldPage() {
  const { t } = useI18n();
  const { companies, companyId, setCompanyId, focusError } = useCompanyFocus();
  const [ticker, setTicker] = useState("");
  const [dq, setDq] = useState("demo_structured");
  const [gci, setGci] = useState<number | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, unknown>[]>([]);
  const [cites, setCites] = useState<CitationRecord[]>([]);
  const [note, setNote] = useState("");
  const [emptyDemo, setEmptyDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;
    fetchSightsField(companyId)
      .then((r) => {
        if (cancelled) return;
        setTicker(r.ticker);
        setDq(r.data_quality);
        setGci(r.gci_score);
        setOutcomes(r.outcomes || []);
        setCites(r.citations || []);
        setNote(r.note);
        setEmptyDemo(!!r.empty_demo);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : t("ui.SightsEvidencePages.failed"));
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return (
    <section className="sights-panel" data-testid="sights-field">
      <h2>{t("ui.SightsEvidencePages.field.title")}</h2>
      <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
      <p className="muted">{note}</p>
      {(error || focusError) && <p className="error">{error || focusError}</p>}
      <p>
        {ticker} · GCI {gci ?? "n/a"} <QualityBadge quality={dq} />
      </p>
      {emptyDemo && (
        <p className="callout warn">{t("ui.SightsEvidencePages.field.thinEvidence")}</p>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>{t("ui.SightsEvidencePages.field.th.metric")}</th>
            <th>{t("ui.SightsEvidencePages.field.th.period")}</th>
            <th>{t("ui.SightsEvidencePages.field.th.label")}</th>
            <th>{t("ui.SightsEvidencePages.field.th.actual")}</th>
          </tr>
        </thead>
        <tbody>
          {[...outcomes].sort(compareEvidenceLatestFirst).map((o, i) => (
            <tr key={i}>
              <td>{metricDisplayName(String(o.metric ?? ""))}</td>
              <td>{String(o.period ?? "")}</td>
              <td>{String(o.label ?? "")}</td>
              <td>{String(o.actual ?? "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="cite-stack">
        {cites.map((c, i) => (
          <CitationCard key={c.citation_id || i} citation={c} />
        ))}
      </div>
    </section>
  );
}
