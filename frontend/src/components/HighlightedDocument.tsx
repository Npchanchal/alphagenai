import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import { findQuoteRange, splitHighlighted } from "../lib/sourceHighlight";

type Props = {
  text: string;
  quote?: string | null;
  spanStart?: number | null;
  spanEnd?: number | null;
  excerptOnly?: boolean;
  indexedExcerpt?: boolean;
};

/** Filing/transcript body with the cited span marked and scrolled into view. */
export default function HighlightedDocument({
  text,
  quote,
  spanStart,
  spanEnd,
  excerptOnly = false,
  indexedExcerpt = false,
}: Props) {
  const { t } = useI18n();
  const markRef = useRef<HTMLElement | null>(null);
  const range = findQuoteRange(text, quote, spanStart, spanEnd);
  const parts = splitHighlighted(text, range);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [text, quote, spanStart, spanEnd]);

  if (!text) {
    return <p className="muted">{t("ui.HighlightedDocument.empty")}</p>;
  }

  return (
    <div className="source-doc" data-testid="highlighted-document">
      {(excerptOnly || indexedExcerpt) && (
        <p className="muted source-excerpt-note">
          {indexedExcerpt
            ? t("ui.HighlightedDocument.indexedExcerpt")
            : t("ui.HighlightedDocument.excerptOnly")}
        </p>
      )}
      {quote && !parts && (
        <blockquote className="quote-span">
          “<mark className="source-highlight" data-testid="source-highlight">{quote}</mark>”
        </blockquote>
      )}
      <pre className="source-doc-body">
        {parts ? (
          <>
            {parts.before}
            <mark ref={markRef} className="source-highlight" data-testid="source-highlight">
              {parts.match}
            </mark>
            {parts.after}
          </>
        ) : (
          text
        )}
      </pre>
    </div>
  );
}
