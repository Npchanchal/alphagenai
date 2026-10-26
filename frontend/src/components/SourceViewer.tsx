import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import HighlightedDocument from "./HighlightedDocument";
import { useI18n } from "../i18n";
import { fetchCitation, fetchDocument, fetchDocumentByUrl } from "../lib/api";
import { findQuoteRange, withTextHighlight } from "../lib/sourceHighlight";
import type { SourceTarget } from "../lib/SourceViewerContext";

type Props = {
  target: SourceTarget;
  onClose: () => void;
};

type Resolved = {
  title: string;
  text: string;
  quote: string;
  url: string;
  highlightUrl: string;
  spanStart: number | null;
  spanEnd: number | null;
  companyId: string | null;
  citationId: string | null;
  excerptOnly: boolean;
  indexedExcerpt: boolean;
  error: string | null;
};

function frameUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") return url;
  } catch {
    /* not a navigable filing URL */
  }
  return "";
}

export default function SourceViewer({ target, onClose }: Props) {
  const { t } = useI18n();
  const closeRef = useRef<HTMLButtonElement>(null);
  const [busy, setBusy] = useState(true);
  const [showOriginal, setShowOriginal] = useState(Boolean(target.preferSplit));
  const [resolved, setResolved] = useState<Resolved>(() => ({
    title: target.title || t("ui.SourceViewer.defaultTitle"),
    text: target.document_text || "",
    quote: target.quote || "",
    url: target.source_url || "",
    highlightUrl:
      target.highlight_url ||
      (target.indexed_excerpt
        ? ""
        : withTextHighlight(target.source_url, target.quote) || ""),
    spanStart: target.span_start ?? null,
    spanEnd: target.span_end ?? null,
    companyId: target.company_id || null,
    citationId: target.citation_id || null,
    excerptOnly: Boolean(target.excerpt_only),
    indexedExcerpt: Boolean(target.indexed_excerpt),
    error: null,
  }));

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  useEffect(() => {
    setShowOriginal(Boolean(target.preferSplit));
  }, [target]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const hasText = Boolean(target.document_text);
      if (hasText && (target.span_start != null || !target.citation_id)) {
        setBusy(false);
        return;
      }
      setBusy(true);
      try {
        if (target.citation_id) {
          const rec = await fetchCitation(target.citation_id);
          if (cancelled) return;
          const quote = rec.quote_span || rec.quote || rec.snippet || target.quote || "";
          const url = rec.source_url || rec.url || target.source_url || "";
          let text = rec.document_text || "";
          let excerptOnly = Boolean(rec.excerpt_only);
          const spanStart = rec.span_start ?? target.span_start ?? null;
          const spanEnd = rec.span_end ?? target.span_end ?? null;
          if (url && (!text || excerptOnly || !findQuoteRange(text, quote, spanStart, spanEnd))) {
            try {
              const listed = await fetchDocumentByUrl(url);
              const fuller = listed.documents?.[0]?.text || "";
              if (fuller.length > text.length && findQuoteRange(fuller, quote)) {
                text = fuller;
                excerptOnly = false;
              }
            } catch {
              /* the citation extract still stands */
            }
          }
          if (cancelled) return;
          setResolved({
            title: rec.title || rec.document_title || target.title || t("ui.SourceViewer.defaultTitle"),
            text: text || quote,
            quote,
            url,
            highlightUrl: rec.highlight_url || withTextHighlight(url, quote),
            spanStart: text && text !== (rec.document_text || "") ? null : spanStart,
            spanEnd: text && text !== (rec.document_text || "") ? null : spanEnd,
            companyId: rec.company_id || target.company_id || null,
            citationId: rec.citation_id || target.citation_id || null,
            excerptOnly: text ? excerptOnly : Boolean(quote),
            indexedExcerpt: Boolean(rec.indexed_excerpt),
            error: null,
          });
          return;
        } else if (target.doc_id) {
          const doc = await fetchDocument(target.doc_id);
          if (cancelled) return;
          const quote = target.quote || "";
          const url = doc.url || target.source_url || "";
          setResolved({
            title: doc.title || target.title || t("ui.SourceViewer.defaultTitle"),
            text: doc.text || quote,
            quote,
            url,
            highlightUrl: withTextHighlight(url, quote),
            spanStart: target.span_start ?? null,
            spanEnd: target.span_end ?? null,
            companyId: doc.company_id || target.company_id || null,
            citationId: target.citation_id || null,
            excerptOnly: false,
            indexedExcerpt: false,
            error: null,
          });
          return;
        } else if (target.source_url) {
          const listed = await fetchDocumentByUrl(target.source_url);
          if (cancelled) return;
          const doc = listed.documents?.[0];
          if (doc?.text) {
            const quote = target.quote || "";
            const url = doc.url || target.source_url || "";
            setResolved({
              title: doc.title || target.title || t("ui.SourceViewer.defaultTitle"),
              text: doc.text,
              quote,
              url,
              highlightUrl: withTextHighlight(url, quote),
              spanStart: target.span_start ?? null,
              spanEnd: target.span_end ?? null,
              companyId: doc.company_id || target.company_id || null,
              citationId: target.citation_id || null,
              excerptOnly: false,
              indexedExcerpt: Boolean(target.indexed_excerpt),
              error: null,
            });
            return;
          }
        }
        if (!cancelled) {
          setResolved((prev) => ({
            ...prev,
            text: prev.text || prev.quote,
            excerptOnly: prev.text ? prev.excerptOnly : Boolean(prev.quote),
          }));
        }
      } catch (e) {
        if (!cancelled) {
          setResolved((prev) => ({
            ...prev,
            error: e instanceof Error ? e.message : t("ui.SourceViewer.loadError"),
          }));
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [target]);

  const originalUrl = frameUrl(resolved.highlightUrl || resolved.url);
  const originalLabel = showOriginal
    ? t("ui.SourceViewer.hideOriginal")
    : resolved.highlightUrl
      ? t("ui.SourceViewer.openHighlight")
      : resolved.indexedExcerpt
        ? t("ui.SourceViewer.openIrPortal")
        : t("ui.SourceViewer.openOriginal");

  return (
    <div className="source-viewer-overlay" role="presentation" onClick={onClose}>
      <div
        className={`source-viewer${showOriginal ? " is-split" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-viewer-title"
        data-testid="source-viewer"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="source-viewer-head">
          <div>
            <p className="page-kicker">{t("ui.SourceViewer.kicker")}</p>
            <h2 id="source-viewer-title">{resolved.title}</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="btn ghost small"
            onClick={onClose}
            data-testid="source-viewer-close"
          >
            {t("ui.SourceViewer.close")}
          </button>
        </header>
        {busy && <p className="muted">{t("ui.SourceViewer.loading")}</p>}
        {resolved.error && <p className="error">{resolved.error}</p>}
        {!busy && (
          <div className={showOriginal ? "source-split" : undefined}>
            <HighlightedDocument
              text={resolved.text || resolved.quote}
              quote={resolved.quote}
              spanStart={resolved.spanStart}
              spanEnd={resolved.spanEnd}
              excerptOnly={resolved.excerptOnly || (!resolved.text && Boolean(resolved.quote))}
              indexedExcerpt={resolved.indexedExcerpt}
            />
            {showOriginal && originalUrl ? (
              <div className="source-split-original" data-testid="source-split">
                <p className="muted source-excerpt-note">{t("ui.SourceViewer.splitNote")}</p>
                <iframe
                  className="source-frame"
                  title={resolved.title}
                  src={originalUrl}
                  data-testid="source-frame"
                  referrerPolicy="no-referrer"
                />
                <p className="muted source-excerpt-note">
                  {t("ui.SourceViewer.embedBlocked")}{" "}
                  <a href={originalUrl} target="_blank" rel="noreferrer">
                    {t("ui.SourceViewer.openNewTab")}
                  </a>
                </p>
              </div>
            ) : null}
          </div>
        )}
        <footer className="source-viewer-foot">
          {originalUrl ? (
            <button
              type="button"
              className="linkish"
              data-testid={resolved.highlightUrl ? "open-original-source" : "open-related-portal"}
              aria-expanded={showOriginal}
              onClick={() => setShowOriginal((open) => !open)}
            >
              {originalLabel}
            </button>
          ) : null}
          {resolved.citationId && (
            <Link to={`/c/${encodeURIComponent(resolved.citationId)}`}>{t("ui.SourceViewer.permalink")}</Link>
          )}
          {resolved.companyId && (
            <Link to={`/companies/${resolved.companyId}`}>{t("ui.SourceViewer.openDossier")}</Link>
          )}
        </footer>
      </div>
    </div>
  );
}
