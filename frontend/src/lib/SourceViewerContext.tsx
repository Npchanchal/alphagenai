import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import SourceViewer from "../components/SourceViewer";
import { withTextHighlight } from "./sourceHighlight";

export type SourceTarget = {
  citation_id?: string | null;
  doc_id?: string | null;
  title?: string | null;
  source_url?: string | null;
  highlight_url?: string | null;
  quote?: string | null;
  document_text?: string | null;
  span_start?: number | null;
  span_end?: number | null;
  company_id?: string | null;
  excerpt_only?: boolean;
  indexed_excerpt?: boolean;
  /** Open the original filing beside the extract. */
  preferSplit?: boolean;
};

type Ctx = {
  openSource: (target: SourceTarget) => void;
};

const SourceViewerContext = createContext<Ctx | null>(null);

function fallbackOpen(target: SourceTarget) {
  const url =
    target.highlight_url ||
    withTextHighlight(target.source_url, target.quote);
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

export function SourceViewerProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<SourceTarget | null>(null);
  const openSource = useCallback((next: SourceTarget) => {
    const hasHandle =
      Boolean(next.citation_id) ||
      Boolean(next.doc_id) ||
      Boolean(next.document_text) ||
      Boolean(next.source_url);
    if (!hasHandle) return;
    setTarget(next);
  }, []);
  const close = useCallback(() => setTarget(null), []);
  const value = useMemo(() => ({ openSource }), [openSource]);

  return (
    <SourceViewerContext.Provider value={value}>
      {children}
      {target && <SourceViewer target={target} onClose={close} />}
    </SourceViewerContext.Provider>
  );
}

export function useSourceViewer(): Ctx {
  const ctx = useContext(SourceViewerContext);
  if (!ctx) {
    return { openSource: fallbackOpen };
  }
  return ctx;
}
