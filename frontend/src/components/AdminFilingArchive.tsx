import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Skeleton from "./Skeleton";
import {
  fetchAdminFiling,
  fetchAdminFilingOriginal,
  fetchAdminFilings,
  postAdminFilingArchive,
  type AdminFilingDetail,
  type AdminFilingPage,
  type AdminFilingQuery,
  type ArchiveExchange,
} from "../lib/api";

const PAGE = 50;

const EXCHANGE_LABEL: Record<ArchiveExchange, string> = {
  nse: "NSE",
  bse: "BSE",
  intl: "Other markets",
};

const DOC_TYPE_LABEL: Record<string, string> = {
  concall: "Earnings call",
  transcript: "Call transcript",
  presentation: "Investor presentation",
  results: "Results",
  results_release: "Results release",
  press_release: "Press release",
  annual_report: "Annual report",
  agm: "AGM record",
  ir_guidance: "IR guidance",
  filing: "Exchange filing",
};

function docTypeLabel(kind: string): string {
  return DOC_TYPE_LABEL[kind] || kind.replace(/_/g, " ");
}

const EMPTY: AdminFilingQuery = {
  q: "",
  exchange: "",
  doc_type: "",
  company_id: "",
  date_from: "",
  date_to: "",
  in_s3: "",
};

export default function AdminFilingArchive({ token, canRun }: { token: string; canRun: boolean }) {
  const [draft, setDraft] = useState<AdminFilingQuery>(EMPTY);
  const [query, setQuery] = useState<AdminFilingQuery>(EMPTY);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<AdminFilingPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<AdminFilingDetail | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const readerRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setErr(null);
    return fetchAdminFilings({ ...query, limit: PAGE, offset }, token)
      .then(setPage)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoading(false));
  }, [query, offset, token]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (open) readerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [open]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setQuery({ ...draft });
  };

  const readDoc = (docId: string) => {
    setOpening(docId);
    setErr(null);
    void fetchAdminFiling(docId, token)
      .then(setOpen)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setOpening(null));
  };

  const openOriginal = (docId: string) => {
    const tab = window.open("", "_blank");
    void fetchAdminFilingOriginal(docId, token)
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        if (tab) tab.location.href = url;
        else window.location.href = url;
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      })
      .catch((e) => {
        tab?.close();
        setErr((e as Error).message);
      });
  };

  const archive = page?.archive;
  const facets = page?.facets;
  const total = page?.total ?? 0;
  const inS3 = facets ? facets.in_s3.yes : 0;
  const stored = facets ? facets.in_s3.yes + facets.in_s3.no : 0;

  return (
    <div data-testid="admin-section-filings">
      <h2 style={{ marginTop: 0 }}>Filing archive</h2>
      <p className="muted">
        Transcripts, results, presentations and annual reports already read from NSE, BSE, EDGAR and issuer
        sites. Each one is kept in S3 as extracted text and, where it was kept, the file as served. Opening a
        document here does not fetch the source again.
      </p>

      {archive && (
        <div className="filing-archive-status" data-testid="filing-archive-status">
          {archive.configured ? (
            <p>
              {inS3.toLocaleString()} of {stored.toLocaleString()} matching filings are in S3.
              {archive.running && archive.progress
                ? ` Upload in progress: ${archive.progress.uploaded ?? 0} copied since ${String(archive.progress.started_at || "").slice(0, 16).replace("T", " ")} UTC.`
                : archive.last_run
                  ? ` Last upload finished ${archive.last_run.finished_at.slice(0, 16).replace("T", " ")} UTC: ${archive.last_run.uploaded} copied, ${archive.last_run.failed} failed.`
                  : " No upload has run yet."}
            </p>
          ) : (
            <p className="muted">S3 buckets are not configured on this server. Filings below are on the data volume only.</p>
          )}
          {archive.configured && (
            <ul className="filing-archive-buckets muted">
              {archive.buckets.map((b) => (
                <li key={b.exchange}>
                  {b.label}: <code>{b.bucket || "not set"}</code>
                </li>
              ))}
            </ul>
          )}
          {canRun && archive.configured && (
            <button
              type="button"
              className="btn"
              disabled={archive.running}
              data-testid="filing-archive-run"
              onClick={() => {
                void postAdminFilingArchive(token)
                  .then((r) => {
                    setMsg(
                      r.status === "started"
                        ? "Upload started. Filings not yet in S3 are copied in the background."
                        : r.status === "already_running"
                          ? "An upload is already running."
                          : "S3 buckets are not configured.",
                    );
                    return load();
                  })
                  .catch((e) => setErr((e as Error).message));
              }}
            >
              {archive.running ? "Upload running" : "Copy new filings to S3"}
            </button>
          )}
        </div>
      )}

      {msg && <p className="muted admin-flash">{msg}</p>}
      {err && <p className="error">{err}</p>}

      <form className="admin-inline-form filing-archive-filters" onSubmit={submit}>
        <input
          type="search"
          value={draft.q}
          onChange={(e) => setDraft({ ...draft, q: e.target.value })}
          placeholder="Company, ticker, title or words in the opening pages"
          aria-label="Search filings"
          style={{ minWidth: "18rem", flex: "1 1 18rem" }}
        />
        <select
          value={draft.exchange}
          onChange={(e) => setDraft({ ...draft, exchange: e.target.value as ArchiveExchange | "" })}
          aria-label="Exchange"
        >
          <option value="">All exchanges</option>
          {(Object.keys(EXCHANGE_LABEL) as ArchiveExchange[]).map((ex) => (
            <option key={ex} value={ex}>
              {EXCHANGE_LABEL[ex]}
              {facets ? ` (${(facets.exchange[ex] || 0).toLocaleString()})` : ""}
            </option>
          ))}
        </select>
        <select
          value={draft.doc_type}
          onChange={(e) => setDraft({ ...draft, doc_type: e.target.value })}
          aria-label="Document type"
        >
          <option value="">All document types</option>
          {Object.entries(facets?.doc_type || {})
            .sort((a, b) => b[1] - a[1])
            .map(([kind, n]) => (
              <option key={kind} value={kind}>
                {docTypeLabel(kind)} ({n.toLocaleString()})
              </option>
            ))}
        </select>
        <select
          value={draft.in_s3}
          onChange={(e) => setDraft({ ...draft, in_s3: e.target.value as "" | "true" | "false" })}
          aria-label="In S3"
        >
          <option value="">In S3 or not</option>
          <option value="true">In S3</option>
          <option value="false">Not yet in S3</option>
        </select>
        <input
          value={draft.company_id}
          onChange={(e) => setDraft({ ...draft, company_id: e.target.value.trim() })}
          placeholder="Company id"
          aria-label="Company id"
          style={{ width: "9rem" }}
        />
        <label className="muted">
          From{" "}
          <input
            type="date"
            value={draft.date_from}
            onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
            aria-label="Filed on or after"
          />
        </label>
        <label className="muted">
          To{" "}
          <input
            type="date"
            value={draft.date_to}
            onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
            aria-label="Filed on or before"
          />
        </label>
        <button type="submit" className="btn-primary">
          Search
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setDraft(EMPTY);
            setOffset(0);
            setQuery(EMPTY);
          }}
        >
          Clear
        </button>
      </form>
      <p className="muted" style={{ fontSize: 13 }}>
        For a phrase anywhere in the full text, use <Link to="/research">Filing Search</Link>.
      </p>

      {open && (
        <div className="panel filing-reader" data-testid="filing-reader" ref={readerRef}>
          <div className="row gap" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <div>
              <h3 style={{ margin: 0 }}>{open.title}</h3>
              <p className="muted" style={{ margin: "0.25rem 0 0" }}>
                {open.name} ({open.ticker}) · {docTypeLabel(open.doc_type)} · filed {open.date || "undated"}
                {open.period ? ` · ${open.period}` : ""} · {EXCHANGE_LABEL[open.exchange]} ·{" "}
                {open.chars.toLocaleString()} characters
              </p>
            </div>
            <div className="row gap">
              {open.has_original && (
                <button type="button" className="btn-primary" onClick={() => openOriginal(open.doc_id)}>
                  Open original file
                </button>
              )}
              {open.url && (
                <a href={open.url} target="_blank" rel="noopener noreferrer" className="btn-ghost">
                  Source page
                </a>
              )}
              <button type="button" className="btn-ghost" onClick={() => setOpen(null)}>
                Close
              </button>
            </div>
          </div>
          <dl className="filing-reader-meta muted">
            <div>
              <dt>Public from</dt>
              <dd>{open.public_available_at || "—"}</dd>
            </div>
            <div>
              <dt>Stored</dt>
              <dd>{open.ingested_at ? open.ingested_at.slice(0, 10) : "—"}</dd>
            </div>
            <div>
              <dt>S3 text</dt>
              <dd>{open.s3_text ? <code>{open.s3_text}</code> : "Not yet in S3"}</dd>
            </div>
            {open.s3_original && (
              <div>
                <dt>S3 original</dt>
                <dd>
                  <code>{open.s3_original}</code>
                </dd>
              </div>
            )}
          </dl>
          <pre className="filing-reader-text">{open.text}</pre>
        </div>
      )}

      {loading && !page ? (
        <Skeleton rows={6} />
      ) : !page || page.documents.length === 0 ? (
        <p className="muted">No stored filings match.</p>
      ) : (
        <>
          <p className="muted" style={{ fontSize: 13 }}>
            {(offset + 1).toLocaleString()}–{Math.min(offset + PAGE, total).toLocaleString()} of{" "}
            {total.toLocaleString()}, latest filing first.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="admin-table" data-testid="filing-archive-table">
              <thead>
                <tr>
                  <th>Filed</th>
                  <th>Company</th>
                  <th>Type</th>
                  <th>Title</th>
                  <th>Exchange</th>
                  <th>In S3</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {page.documents.map((d) => (
                  <tr key={d.doc_id}>
                    <td>{d.date || "—"}</td>
                    <td>
                      <div>{d.name}</div>
                      <code>{d.ticker}</code>
                    </td>
                    <td>{docTypeLabel(d.doc_type)}</td>
                    <td>
                      {d.title}
                      {d.period ? <span className="muted"> · {d.period}</span> : null}
                    </td>
                    <td>{EXCHANGE_LABEL[d.exchange]}</td>
                    <td>{d.archived ? (d.s3_original ? "Text and original" : "Text") : "Not yet"}</td>
                    <td>
                      <div className="row gap">
                        <button
                          type="button"
                          className="btn-ghost"
                          disabled={opening === d.doc_id}
                          onClick={() => readDoc(d.doc_id)}
                        >
                          Read
                        </button>
                        {d.has_original && (
                          <button type="button" className="btn-ghost" onClick={() => openOriginal(d.doc_id)}>
                            Original
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row gap" style={{ marginTop: "0.75rem" }}>
            <button
              type="button"
              className="btn-ghost"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE))}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={offset + PAGE >= total}
              onClick={() => setOffset(offset + PAGE)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
