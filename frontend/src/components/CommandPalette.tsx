import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchCompanies } from "../lib/api";
import { readRecentCompanies, rememberCompany } from "../lib/recentCompanies";

const TOOLS = [
  { label: "GCI Screener", to: "/tracker" },
  { label: "Filing Search", to: "/research" },
  { label: "CiteAlpha Analyst", to: "/analyst" },
  { label: "Public Snapshot", to: "/rankings" },
  { label: "Analyst Workbench", to: "/desk" },
  { label: "Disclosure Explorer", to: "/sights" },
  { label: "Holdings", to: "/holdings" },
  { label: "Financial Ninja", to: "/ninja" },
];

type Hit = { id: string; name: string; ticker: string };

export default function CommandPalette({ enabled = true }: { enabled?: boolean }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!enabled) setOpen(false);
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if (meta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
        return;
      }
      if (e.key === "/" && !typing && !open) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    function onOpen() {
      setOpen(true);
    }
    document.addEventListener("citealpha:palette", onOpen);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("citealpha:palette", onOpen);
    };
  }, [open, enabled]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
    else setQ("");
  }, [open]);

  useEffect(() => {
    if (!open || q.trim().length < 1) {
      setHits([]);
      return;
    }
    const handle = window.setTimeout(() => {
      void searchCompanies(q.trim(), 8)
        .then((res) => setHits(res.results || []))
        .catch(() => setHits([]));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [q, open]);

  const tools = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return TOOLS;
    return TOOLS.filter((tool) => tool.label.toLowerCase().includes(needle));
  }, [q]);

  function go(to: string, companyId?: string) {
    if (companyId) rememberCompany(companyId);
    setOpen(false);
    navigate(to);
  }

  if (!open) return null;

  const recent = readRecentCompanies();

  return (
    <div className="palette-overlay" role="presentation" onClick={() => setOpen(false)}>
      <div
        className="palette"
        role="dialog"
        aria-label="Search"
        data-testid="command-palette"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            if (hits[0]) go(`/companies/${hits[0].id}`, hits[0].id);
            else if (tools[0]) go(tools[0].to);
          }}
          placeholder="Company or tool"
          aria-label="Company or tool"
          data-testid="command-palette-input"
        />
        {recent.length > 0 && !q.trim() && (
          <ul>
            {recent.map((id) => (
              <li key={id}>
                <button type="button" onClick={() => go(`/companies/${id}`, id)}>
                  {id.toUpperCase()}
                </button>
              </li>
            ))}
          </ul>
        )}
        {hits.length > 0 && (
          <ul>
            {hits.map((hit) => (
              <li key={hit.id}>
                <button
                  type="button"
                  data-testid={`palette-company-${hit.id}`}
                  onClick={() => go(`/companies/${hit.id}`, hit.id)}
                >
                  {hit.ticker} · {hit.name}
                </button>
              </li>
            ))}
          </ul>
        )}
        {tools.length > 0 && (
          <ul>
            {tools.map((tool) => (
              <li key={tool.to}>
                <button type="button" onClick={() => go(tool.to)}>
                  {tool.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}