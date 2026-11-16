import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import TierBadge from "../components/TierBadge";
import { useI18n } from "../i18n";
import {
  fetchCompanies,
  fetchScoreChangelog,
  fetchScoreLedger,
  type ChangelogEntry,
  type CompanySummary,
  type ScoreLedgerRow,
} from "../lib/api";
import { formatCompanyScore } from "../lib/score";

/**
 * Public score changelog + ledger (plan W1.7, rule index-integrity).
 * `?company=<id>` filters both lists to one company (linked from the dossier footer).
 */
export default function ChangelogPage() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const company = params.get("company") || "";
  const [entries, setEntries] = useState<ChangelogEntry[] | null>(null);
  const [ledger, setLedger] = useState<ScoreLedgerRow[] | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    Promise.all([
      fetchScoreChangelog(company || undefined),
      fetchScoreLedger(company || undefined, 500),
    ])
      .then(([cl, lg]) => {
        if (!alive) return;
        setEntries(cl.entries);
        setLedger([...lg.rows].reverse());
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [company]);

  useEffect(() => {
    fetchCompanies()
      .then((rows: CompanySummary[]) => {
        const m: Record<string, string> = {};
        rows.forEach((r) => {
          m[r.id] = r.name;
        });
        setNames(m);
      })
      .catch(() => undefined);
  }, []);

  const nameOf = useMemo(
    () => (id: string) => names[id] || "",
    [names],
  );

  return (
    <section className="page changelog-page" data-testid="changelog-page">
      <p className="page-kicker">{t("changelog.kicker")}</p>
      <h1>{t("changelog.title")}</h1>
      <p className="muted lede">{t("changelog.lede")}</p>

      {company ? (
        <p className="muted" data-testid="changelog-filter">
          {t("changelog.filter.company", { name: nameOf(company) })}{" "}
          <button
            type="button"
            className="linkish"
            onClick={() => {
              params.delete("company");
              setParams(params, { replace: true });
            }}
          >
            {t("changelog.filter.clear")}
          </button>
          {" · "}
          <Link to={`/companies/${company}`}>{nameOf(company)}</Link>
        </p>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <div className="panel" data-testid="changelog-entries">
        {entries === null ? (
          <p className="muted">…</p>
        ) : entries.length === 0 ? (
          <p className="muted">{t("changelog.empty")}</p>
        ) : (
          <ol className="changelog-list">
            {entries.map((e, i) => (
              <li key={`${e.date}-${e.reason}-${i}`} className="changelog-entry">
                <div className="changelog-entry-head">
                  <time dateTime={e.date}>{e.date}</time>
                  <span className={`pill reason-${e.reason}`}>
                    {t(`changelog.reason.${e.reason}`)}
                  </span>
                  {e.companies.length > 0 ? (
                    <span className="changelog-companies">
                      {e.companies.map((cid) =>
                        nameOf(cid) ? (
                          <Link
                            key={cid}
                            to={`/companies/${cid}`}
                            className="inline-link"
                          >
                            {nameOf(cid)}
                          </Link>
                        ) : null,
                      )}
                    </span>
                  ) : null}
                </div>
                <p>{e.change}</p>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="panel" data-testid="changelog-ledger">
        <h2 style={{ marginTop: 0 }}>{t("changelog.ledger.title")}</h2>
        <p className="muted">{t("changelog.ledger.lede")}</p>
        {ledger === null ? (
          <p className="muted">…</p>
        ) : ledger.length === 0 ? (
          <p className="muted">{t("changelog.ledger.empty")}</p>
        ) : (
          <div className="table-scroll">
            <table className="table ledger-table">
              <thead>
                <tr>
                  <th>{t("changelog.ledger.cols.date")}</th>
                  <th>{t("changelog.ledger.cols.company")}</th>
                  <th>{t("changelog.ledger.cols.from")}</th>
                  <th>{t("changelog.ledger.cols.to")}</th>
                  <th>{t("changelog.ledger.cols.tier")}</th>
                  <th>{t("changelog.ledger.cols.reason")}</th>
                  <th>{t("changelog.ledger.cols.by")}</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((r, i) => (
                  <tr key={`${r.company_id}-${r.as_of}-${r.dataset_version}-${i}`}>
                    <td>
                      <time dateTime={r.as_of}>{r.as_of}</time>
                      <div className="muted" style={{ fontSize: 11 }}>
                        {r.dataset_version}
                      </div>
                    </td>
                    <td>
                      {nameOf(r.company_id) ? (
                        <Link to={`/companies/${r.company_id}`}>{nameOf(r.company_id)}</Link>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{r.prior_gci == null ? "—" : formatCompanyScore(r.prior_gci)}</td>
                    <td>
                      <strong>{formatCompanyScore(r.gci)}</strong>
                    </td>
                    <td>
                      <TierBadge tier={r.confidence_tier} testId={undefined} />
                    </td>
                    <td title={r.note}>{t(`changelog.reason.${r.reason}`)}</td>
                    <td className="muted">{r.by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted" style={{ fontSize: 12 }}>
          {t("changelog.api")}
        </p>
      </div>

      <Disclaimer compact />
    </section>
  );
}
