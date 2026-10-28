import { Fragment, useMemo, useState } from "react";
import ChangeChip from "./ChangeChip";
import InfoTip from "./InfoTip";
import { useI18n } from "../i18n";
import type { OutcomeView } from "../lib/api";
import { recordCiteCopy } from "../lib/api";
import { formatOutcomeLabel, tipForLabel } from "../lib/glossary";
import { useSourceViewer } from "../lib/SourceViewerContext";
import { withTextHighlight } from "../lib/sourceHighlight";
import { trackEvent } from "../lib/analytics";
import {
  formatActual,
  formatCharLocator,
  formatDossierDate,
  formatGuideGap,
  formatGuidedBand,
  metricDisplayName,
  DEFAULT_EVIDENCE_SORT,
  evidenceTrack,
  evidenceYearColumns,
  listEvidenceRows,
  periodRank,
  type EvidenceSort,
} from "../lib/score";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

type Props = {
  outcomes: OutcomeView[];
  companyId?: string;
  /** When set, shows Accept/Reject review actions. */
  onReview?: (outcomeIndex: number, action: "accept" | "reject") => void;
  /** When set, shows an Edit action with an inline band/actual editor. */
  onEdit?: (outcomeIndex: number, edits: Record<string, unknown>) => void;
  /** Design-partner flag — does not mutate GCI. */
  onFlag?: (outcome: OutcomeView) => void;
  maxRows?: number;
  showDeltaActual?: boolean;
  testId?: string;
};

function sourceHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

type EditDraft = {
  period: string;
  guided_low: string;
  guided_high: string;
  actual_value: string;
  source_url: string;
  source_ref: string;
  quote_span: string;
};

function promiseAfterResult(o: OutcomeView): boolean {
  if (!o.guidance_as_of || !o.as_of) return false;
  const promise = Date.parse(o.guidance_as_of);
  const result = Date.parse(o.as_of);
  return Number.isFinite(promise) && Number.isFinite(result) && promise > result;
}

function YearGrid({
  rows,
}: {
  rows: { o: OutcomeView; period: string; metric: string }[];
}) {
  const periods = evidenceYearColumns(rows.map((row) => row.period));
  const metrics = [...new Set(rows.map((row) => row.metric).filter(Boolean))].sort((a, b) =>
    metricDisplayName(a).localeCompare(metricDisplayName(b)),
  );
  return (
    <div className="table-scroll">
      <table className="table" data-testid="evidence-year">
        <thead>
          <tr>
            <th>Metric</th>
            {periods.map((period) => (
              <th key={period} className="mono">
                {period}
              </th>
            ))}
            <th>Track</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => {
            const cells = periods.map(
              (period) => rows.find((row) => row.metric === metric && row.period === period)?.o,
            );
            return (
              <tr key={metric} data-testid={`evidence-year-row-${metric}`}>
                <td>{metricDisplayName(metric)}</td>
                {cells.map((o, index) => (
                  <td key={periods[index]} className="year-cell">
                    {o ? (
                      <>
                        <div className="num">{formatGuidedBand({ ...o, metric: o.metric })}</div>
                        <div className="num">{formatActual(o)}</div>
                        <span className={`pill ${o.label}`}>{formatOutcomeLabel(o.label)}</span>
                        {promiseAfterResult(o) ? (
                          <div className="muted" style={{ fontSize: 11 }}>
                            Promise date is after the result date
                          </div>
                        ) : null}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                ))}
                <td data-testid={`evidence-track-${metric}`}>
                  {evidenceTrack(cells.map((o) => o?.label)).map(formatOutcomeLabel).join(" · ") || "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function EvidenceTable({
  outcomes,
  companyId,
  onReview,
  onEdit,
  onFlag,
  maxRows,
  showDeltaActual = false,
  testId = "evidence-table",
}: Props) {
  const { t } = useI18n();
  const { openSource } = useSourceViewer();
  const [sort, setSort] = useState<EvidenceSort>(DEFAULT_EVIDENCE_SORT);
  const [layout, setLayout] = useState<"year" | "row">(onReview || onEdit ? "row" : "year");
  const [periodFilter, setPeriodFilter] = useState("");
  const [metricFilter, setMetricFilter] = useState("");
  const periods = useMemo(() => {
    const unique = [...new Set(outcomes.map((o) => o.period).filter(Boolean))];
    unique.sort((a, b) => {
      const ka = periodRank(a);
      const kb = periodRank(b);
      if (ka == null && kb == null) return b.localeCompare(a);
      if (ka == null) return 1;
      if (kb == null) return -1;
      return kb - ka;
    });
    return unique;
  }, [outcomes]);
  const metrics = useMemo(() => {
    const unique = [...new Set(outcomes.map((o) => o.metric).filter(Boolean))];
    unique.sort((a, b) => metricDisplayName(a).localeCompare(metricDisplayName(b)));
    return unique;
  }, [outcomes]);
  const rows = useMemo(() => {
    const indexed = outcomes.map((o, i) => ({
      o,
      sourceIndex: typeof o.outcome_index === "number" ? o.outcome_index : i,
      period: o.period,
      metric: o.metric,
      as_of: o.as_of,
    }));
    const listed = listEvidenceRows(indexed, {
      period: periodFilter,
      metric: metricFilter,
      sort,
    });
    return maxRows != null ? listed.slice(0, maxRows) : listed;
  }, [outcomes, maxRows, periodFilter, metricFilter, sort]);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<EditDraft>({
    period: "",
    guided_low: "",
    guided_high: "",
    actual_value: "",
    source_url: "",
    source_ref: "",
    quote_span: "",
  });

  const toggleSort = (key: EvidenceSort["key"]) => {
    setSort((current) => {
      if (current.key === key) {
        return { key, dir: current.dir === "asc" ? "desc" : "asc" };
      }
      return { key, dir: key === "period" ? "desc" : "asc" };
    });
  };

  const sortNote =
    sort.key === "metric"
      ? t(sort.dir === "asc" ? "ui.EvidenceTable.sort.metricThenPeriod" : "ui.EvidenceTable.sort.metricDesc")
      : t(sort.dir === "desc" ? "ui.EvidenceTable.sort.periodLatest" : "ui.EvidenceTable.sort.periodOldest");

  if (outcomes.length === 0) {
    return (
      <div className="empty" data-testid="empty-state">
        {t("ui.EvidenceTable.empty")}
      </div>
    );
  }

  const startEdit = (idx: number, o: OutcomeView) => {
    setEditingIdx(idx);
    setDraft({
      period: o.period,
      guided_low: o.guided_low != null ? String(o.guided_low) : "",
      guided_high: o.guided_high != null ? String(o.guided_high) : "",
      actual_value: o.actual_value != null ? String(o.actual_value) : "",
      source_url: o.source_url || "",
      source_ref: o.source_ref || "",
      quote_span: o.quote_span || "",
    });
  };

  const saveEdit = (sourceIndex: number) => {
    if (!onEdit) return;
    const edits: Record<string, unknown> = {};
    if (draft.period.trim()) edits.period = draft.period.trim();
    if (draft.guided_low.trim() !== "") edits.guided_low = Number(draft.guided_low);
    if (draft.guided_high.trim() !== "") edits.guided_high = Number(draft.guided_high);
    if (draft.guided_low.trim() !== "" && draft.guided_high.trim() !== "") {
      edits.guided_value = (Number(draft.guided_low) + Number(draft.guided_high)) / 2;
    }
    if (draft.actual_value.trim() !== "") edits.actual_value = Number(draft.actual_value);
    edits.source_url = draft.source_url.trim() || null;
    edits.source_ref = draft.source_ref.trim() || null;
    edits.quote_span = draft.quote_span.trim() || null;
    setEditingIdx(null);
    onEdit(sourceIndex, edits);
  };

  const showActions = Boolean(onReview || onEdit || onFlag);
  const colCount = 8 + (showDeltaActual ? 1 : 0) + (showActions ? 1 : 0);

  const copyCitation = (o: OutcomeView) => {
    const promise = o.guidance_source_url
      ? `Promise: ${o.guidance_as_of || ""} ${o.guidance_source_url}`
      : "";
    const actual = o.source_url ? `Actual: ${o.as_of || ""} ${o.source_url}` : "";
    const loc = formatCharLocator(o.span_start, o.span_end);
    const quote = o.quote_span ? ` Quote: “${o.quote_span}”` : "";
    const gq = o.guidance_quote ? ` Guidance: “${o.guidance_quote}”` : "";
    const line = `${o.period} ${metricDisplayName(o.metric)}. ${promise}. ${actual}${loc ? ` (${loc})` : ""}.${gq}${quote}`;
    void copyText(line.trim()).then((ok) => {
      if (ok) {
        setCopiedId(`${o.period}-${o.metric}`);
        recordCiteCopy(companyId);
        window.setTimeout(() => setCopiedId(null), 1600);
      }
    });
  };

  const sortMark = (key: EvidenceSort["key"]) =>
    sort.key === key ? (sort.dir === "asc" ? " ↑" : " ↓") : "";

  return (
    <div data-testid="evidence-listing">
      <div className="evidence-controls" data-testid="evidence-controls">
        <div className="index-chips" role="group" aria-label="Evidence layout">
          <button
            type="button"
            className={layout === "year" ? "chip active" : "chip"}
            aria-pressed={layout === "year"}
            data-testid="evidence-by-year"
            onClick={() => setLayout("year")}
          >
            By year
          </button>
          <button
            type="button"
            className={layout === "row" ? "chip active" : "chip"}
            aria-pressed={layout === "row"}
            data-testid="evidence-by-row"
            onClick={() => setLayout("row")}
          >
            By row
          </button>
        </div>
        <label>
          {t("ui.EvidenceTable.filter.period")}
          <select
            value={periods.includes(periodFilter) ? periodFilter : ""}
            onChange={(e) => setPeriodFilter(e.target.value)}
            data-testid="evidence-filter-period"
          >
            <option value="">{t("ui.EvidenceTable.filter.allPeriods")}</option>
            {periods.map((period) => (
              <option key={period} value={period}>
                {period}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("ui.EvidenceTable.filter.metric")}
          <select
            value={metrics.includes(metricFilter) ? metricFilter : ""}
            onChange={(e) => setMetricFilter(e.target.value)}
            data-testid="evidence-filter-metric"
          >
            <option value="">{t("ui.EvidenceTable.filter.allMetrics")}</option>
            {metrics.map((metric) => (
              <option key={metric} value={metric}>
                {metricDisplayName(metric)}
              </option>
            ))}
          </select>
        </label>
        {periodFilter || metricFilter ? (
          <button
            type="button"
            className="btn ghost small"
            data-testid="evidence-filter-clear"
            onClick={() => {
              setPeriodFilter("");
              setMetricFilter("");
            }}
          >
            {t("ui.EvidenceTable.filter.clear")}
          </button>
        ) : null}
        <p className="muted evidence-sort-note" data-testid="evidence-sort-note">
          {sortNote}
        </p>
      </div>
      {rows.length === 0 ? (
        <div className="empty" data-testid="evidence-filter-empty">
          {t("ui.EvidenceTable.filter.empty")}
        </div>
      ) : layout === "year" ? (
        <YearGrid rows={rows} />
      ) : (
    <div className="table-scroll">
      <table className="table" data-testid={testId}>
        <thead>
          <tr>
            <th aria-sort={sort.key === "period" ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
              <button
                type="button"
                className="th-sort"
                data-testid="evidence-sort-period"
                aria-label={t("ui.EvidenceTable.sort.byPeriod")}
                onClick={() => toggleSort("period")}
              >
                {t("ui.EvidenceTable.th.period")}
                {sortMark("period")}
              </button>{" "}
              <InfoTip termId="period" />
            </th>
            <th aria-sort={sort.key === "metric" ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
              <button
                type="button"
                className="th-sort"
                data-testid="evidence-sort-metric"
                aria-label={t("ui.EvidenceTable.sort.byMetric")}
                onClick={() => toggleSort("metric")}
              >
                {t("ui.EvidenceTable.th.metric")}
                {sortMark("metric")}
              </button>{" "}
              <InfoTip termId="metric" />
            </th>
            <th>
              {t("ui.EvidenceTable.th.band")} <InfoTip termId="band" />
            </th>
            <th>
              {t("ui.EvidenceTable.th.actual")} <InfoTip termId="actual" />
            </th>
            {showDeltaActual && (
              <th>
                {t("ui.EvidenceTable.th.deltaActual")} <InfoTip termId="change_trend" />
              </th>
            )}
            <th>
              {t("ui.EvidenceTable.th.label")} <InfoTip termId="label" />
            </th>
            <th>
              {t("ui.EvidenceTable.th.points")}{" "}
              <InfoTip termId="gci" text={t("ui.EvidenceTable.pointsTip")} />
            </th>
            <th>{t("ui.EvidenceTable.th.promise")}</th>
            <th>{t("ui.EvidenceTable.th.actualSource")}</th>
            <th>{t("ui.EvidenceTable.th.cite")}</th>
            {showActions && (
              <th>
                {t("ui.EvidenceTable.th.review")} <InfoTip termId="review" />
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ o, sourceIndex }, idx) => (
            <Fragment key={`${o.period}-${o.metric}-${sourceIndex}`}>
              <tr>
                <td>{o.period}</td>
                <td>
                  {metricDisplayName(o.metric)}
                  {o.reporting_basis && o.actual_reporting_basis ? (
                    <div className="muted" style={{ fontSize: 11 }}>
                      {o.label === "basis_mismatch"
                        ? t("dossier.basis.mismatch")
                        : t(`dossier.basis.${o.reporting_basis}`)}
                    </div>
                  ) : null}
                </td>
                <td>{formatGuidedBand({ ...o, metric: o.metric })}</td>
                <td>{formatActual(o)}</td>
                {showDeltaActual && (
                  <td>
                    <ChangeChip
                      value={o.actual_change_pct}
                      horizon={o.actual_change_horizon}
                    />
                  </td>
                )}
                <td>
                  <span className={`pill ${o.label}`}>{formatOutcomeLabel(o.label)}</span>{" "}
                  {promiseAfterResult(o) ? (
                    <span className="muted" data-testid={`promise-after-result-${sourceIndex}`}>
                      Promise date is after the result date
                    </span>
                  ) : null}
                  <InfoTip termId={o.label.toLowerCase()} text={tipForLabel(o.label)} />
                </td>
                <td className="num" title={t("ui.EvidenceTable.gapTitle", { gap: formatGuideGap(o) })}>
                  {o.contribution_score != null ? o.contribution_score.toFixed(1) : "—"}
                  <div className="muted" style={{ fontSize: 11 }}>
                    {formatGuideGap(o)}
                  </div>
                </td>
                <td className="evidence-source" data-testid={`promise-source-${idx}`}>
                  {o.guidance_source_url ? (
                    <details>
                      <summary>
                        <button
                          type="button"
                          className="linkish"
                          data-testid={`open-promise-${idx}`}
                          onClick={() =>
                            openSource({
                              title: `${o.period} ${metricDisplayName(o.metric)} · promise`,
                              source_url: o.guidance_source_url,
                              highlight_url: withTextHighlight(o.guidance_source_url, o.guidance_quote),
                              quote: o.guidance_quote,
                              company_id: companyId,
                            })
                          }
                        >
                          {o.guidance_as_of ? formatDossierDate(o.guidance_as_of) : sourceHost(o.guidance_source_url)}
                        </button>
                      </summary>
                      {o.guidance_quote ? <blockquote className="quote-span">“{o.guidance_quote}”</blockquote> : null}
                    </details>
                  ) : (
                    <span className="muted">{t("ui.EvidenceTable.pendingPromise")}</span>
                  )}
                </td>
                <td className="evidence-source" data-testid={`actual-source-${idx}`}>
                  {o.source_url ? (
                    <>
                      <button
                        type="button"
                        className="linkish"
                        data-testid={`open-source-${idx}`}
                        onClick={() =>
                          openSource({
                            citation_id: o.citation_id,
                            doc_id: o.doc_id,
                            title: `${o.period} ${metricDisplayName(o.metric)}`,
                            source_url: o.source_url,
                            highlight_url: withTextHighlight(o.source_url, o.quote_span),
                            quote: o.quote_span,
                            span_start: o.span_start,
                            span_end: o.span_end,
                          })
                        }
                      >
                        {o.as_of ? formatDossierDate(o.as_of) : sourceHost(o.source_url)}
                      </button>
                      {o.quote_span ? (
                        <details>
                          <summary>{t("ui.EvidenceTable.quote")}</summary>
                          <blockquote className="quote-span quote-span-click">
                            <button
                              type="button"
                              className="linkish quote-open"
                              onClick={() => {
                                trackEvent("open_citation");
                                openSource({
                                  citation_id: o.citation_id,
                                  doc_id: o.doc_id,
                                  title: `${o.period} ${metricDisplayName(o.metric)}`,
                                  source_url: o.source_url,
                                  highlight_url: withTextHighlight(o.source_url, o.quote_span),
                                  quote: o.quote_span,
                                  span_start: o.span_start,
                                  span_end: o.span_end,
                                });
                              }}
                            >
                              “{o.quote_span}”
                            </button>
                          </blockquote>
                        </details>
                      ) : null}
                    </>
                  ) : (
                    "—"
                  )}
                  {o.citeable === false ? (
                    <div className="muted" style={{ fontSize: 11 }}>
                      {t("ui.EvidenceTable.notCiteable")}
                    </div>
                  ) : null}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn ghost small"
                    data-testid={`copy-cite-${idx}`}
                    onClick={() => copyCitation(o)}
                  >
                    {copiedId === `${o.period}-${o.metric}`
                      ? t("ui.EvidenceTable.copied")
                      : t("ui.EvidenceTable.copyCite")}
                  </button>
                </td>
                {showActions && (
                  <td>
                    <div className="review-actions">
                      {onReview && (
                        <button
                          type="button"
                          className="btn ghost small"
                          onClick={() => onReview(sourceIndex, "accept")}
                        >
                          {t("ui.EvidenceTable.accept")}
                        </button>
                      )}
                      {onEdit && (
                        <button
                          type="button"
                          className="btn ghost small"
                          data-testid={`edit-outcome-${idx}`}
                          onClick={() =>
                            editingIdx === idx ? setEditingIdx(null) : startEdit(idx, o)
                          }
                        >
                          {editingIdx === idx ? t("ui.EvidenceTable.cancel") : t("ui.EvidenceTable.edit")}
                        </button>
                      )}
                      {onFlag && (
                        <button
                          type="button"
                          className="btn ghost small"
                          data-testid={`flag-outcome-${idx}`}
                          onClick={() => onFlag(o)}
                        >
                          {t("ui.EvidenceTable.flag")}
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
              {editingIdx === idx && onEdit && (
                <tr className="edit-row">
                  <td colSpan={colCount}>
                    <div className="edit-form" data-testid={`edit-form-${idx}`}>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.period")}</span>
                        <input
                          value={draft.period}
                          onChange={(e) => setDraft({ ...draft, period: e.target.value })}
                        />
                      </label>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.guidedLow")}</span>
                        <input
                          type="number"
                          value={draft.guided_low}
                          onChange={(e) =>
                            setDraft({ ...draft, guided_low: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.guidedHigh")}</span>
                        <input
                          type="number"
                          value={draft.guided_high}
                          onChange={(e) =>
                            setDraft({ ...draft, guided_high: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.actual")}</span>
                        <input
                          type="number"
                          value={draft.actual_value}
                          onChange={(e) =>
                            setDraft({ ...draft, actual_value: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.sourceUrl")}</span>
                        <input
                          value={draft.source_url}
                          onChange={(e) =>
                            setDraft({ ...draft, source_url: e.target.value })
                          }
                          placeholder="https://…"
                        />
                      </label>
                      <label>
                        <span className="field-label">{t("ui.EvidenceTable.field.sourceRef")}</span>
                        <input
                          value={draft.source_ref}
                          onChange={(e) =>
                            setDraft({ ...draft, source_ref: e.target.value })
                          }
                        />
                      </label>
                      <label className="edit-span-full">
                        <span className="field-label">{t("ui.EvidenceTable.field.quoteSpan")}</span>
                        <input
                          value={draft.quote_span}
                          onChange={(e) =>
                            setDraft({ ...draft, quote_span: e.target.value })
                          }
                          placeholder={t("ui.EvidenceTable.field.quoteSpanPlaceholder")}
                        />
                      </label>
                      <button
                        type="button"
                        className="btn small"
                        data-testid={`save-edit-${idx}`}
                        onClick={() => saveEdit(sourceIndex)}
                      >
                        {t("ui.EvidenceTable.saveEdit")}
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
      )}
    </div>
  );
}
