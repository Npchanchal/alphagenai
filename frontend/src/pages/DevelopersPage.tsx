import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";
import { downloadOutcomesExport, fetchCompanyGci } from "../lib/api";
import { useEntitlements } from "../lib/entitlements";
import { metricDisplayName } from "../lib/score";

const READS = [
  { path: "/api/v1/companies", note: "Universe + scores" },
  { path: "/api/v1/companies/{id}/gci", note: "Dossier payload" },
  { path: "/api/v1/companies/{id}/gci/history", note: "Point-in-time path" },
  { path: "/api/v1/rankings", note: "Public Snapshot" },
  { path: "/api/v1/index/ledger", note: "Append-only score ledger" },
  { path: "/api/v1/index/changelog", note: "Methodology changelog" },
  { path: "/api/v1/index/changelog.rss", note: "Changelog RSS" },
  { path: "/api/v1/index/files", note: "Frozen daily levels" },
];

type Field = { field: string; meaning: string; value: string | number | null; whenNull: string };

const SAMPLE_COMPANY = "infy";

async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default function DevelopersPage() {
  const { t } = useI18n();
  const { has } = useEntitlements();
  const [fields, setFields] = useState<Field[] | null>(null);
  const [file, setFile] = useState<{ sha: string; bytes: number } | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const canFile = has("em_export");

  useEffect(() => {
    void fetchCompanyGci(SAMPLE_COMPANY)
      .then((detail) => {
        const row = detail.outcomes?.find((o) => o.guidance_as_of && o.as_of) ?? detail.outcomes?.[0];
        if (!row) return;
        setFields([
          { field: "company", meaning: "Ticker", value: detail.ticker || detail.id, whenNull: "Never null" },
          { field: "period", meaning: "Fiscal period of the promise", value: row.period, whenNull: "Never null" },
          { field: "metric", meaning: "Metric name", value: metricDisplayName(row.metric), whenNull: "Never null" },
          { field: "guided_low", meaning: "Low end of the guided band", value: row.guided_low ?? null, whenNull: "A point guide has no band" },
          { field: "guided_high", meaning: "High end of the guided band", value: row.guided_high ?? null, whenNull: "A point guide has no band" },
          { field: "actual_value", meaning: "Reported figure", value: row.actual_value ?? null, whenNull: "Result not yet filed" },
          { field: "label", meaning: "Outcome", value: row.label, whenNull: "Never null" },
          { field: "guidance_as_of", meaning: "Promise date", value: row.guidance_as_of ?? null, whenNull: "Promise quote not yet cited" },
          { field: "as_of", meaning: "Result date", value: row.as_of ?? null, whenNull: "Result not yet filed" },
          { field: "reviewed_at", meaning: "Available date: the day the row entered the index", value: row.reviewed_at ?? null, whenNull: "Not yet reviewed" },
          { field: "confidence_tier", meaning: "Tier of the company score", value: detail.confidence_tier ?? null, whenNull: "Company not scored" },
          { field: "algorithm_id", meaning: "Scorer version", value: detail.algorithm_id ?? null, whenNull: "Company not scored" },
        ]);
      })
      .catch(() => setFields(null));
  }, []);

  async function download() {
    setFileError(null);
    try {
      const blob = await downloadOutcomesExport("csv", 500);
      setFile({ sha: await sha256Hex(blob), bytes: blob.size });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "outcomes_bulk.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "Download failed");
    }
  }

  return (
    <section className="help-page" data-testid="developers-page">
      <p className="page-kicker">{t("developers.kicker")}</p>
      <h1>{t("developers.title")}</h1>
      <p className="muted lede">{t("developers.lede")}</p>
      <div className="panel" data-testid="developers-fields">
        <h2 style={{ marginTop: 0 }}>One published outcome</h2>
        <p className="muted">
          The sample is a published row on Infosys. A monitor and an upload do not write the index.
        </p>
        {fields ? (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Meaning</th>
                  <th>Sample</th>
                  <th>When null</th>
                </tr>
              </thead>
              <tbody>
                {fields.map((f) => (
                  <tr key={f.field}>
                    <td>
                      <code>{f.field}</code>
                    </td>
                    <td>{f.meaning}</td>
                    <td className="num">{f.value == null || f.value === "" ? "null" : String(f.value)}</td>
                    <td className="muted">{f.whenNull}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">The sample row loads from the published dossier payload.</p>
        )}
        {canFile ? (
          <div className="row gap" style={{ marginTop: 12 }}>
            <button type="button" className="btn-primary" data-testid="developers-download" onClick={() => void download()}>
              Download the published file (CSV)
            </button>
            {file ? (
              <span className="muted" data-testid="developers-sha">
                sha256 <code>{file.sha}</code> · {file.bytes.toLocaleString()} bytes
              </span>
            ) : null}
            {fileError ? <span className="error">{fileError}</span> : null}
          </div>
        ) : (
          <p data-testid="developers-enterprise">The file is on the Enterprise plan.</p>
        )}
      </div>
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Public reads</h2>
        <ul className="about-list">
          {READS.map((r) => (
            <li key={r.path}>
              <code>{r.path}</code> — {r.note}
            </li>
          ))}
        </ul>
        <p>
          <a href="/docs" rel="noreferrer">
            OpenAPI
          </a>
          {" · "}
          <Link to="/products#plans">Request a quote</Link>
          {" · "}
          <Link to="/changelog">Changelog</Link>
        </p>
      </div>
      <Disclaimer />
    </section>
  );
}
