import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import InfoTip from "./InfoTip";
import TierBadge from "./TierBadge";
import { useI18n } from "../i18n";
import {
  fetchSectorBenchmark,
  fetchSectorLeaderboard,
  type CompanySummary,
  type ConfidenceTier,
} from "../lib/api";
import { formatScore, scoreClass, formatCompanyScore, NOT_SCORED_LABEL } from "../lib/score";

type SectorRow = {
  sector: string;
  avg: number | null;
  count: number;
  best: {
    id: string;
    ticker: string;
    name: string;
    gci_score: number | null;
  } | null;
  names?: { id: string; ticker: string; name: string; confidence_tier?: string | null }[];
};

type Props = {
  market?: string;
  index?: string;
  limit?: number;
  compact?: boolean;
};

/** Sector credibility leaderboard — shared across Tracker / Desk / Research. */
export default function SectorLeaderboard({
  market = "IN",
  index = "SENSEX",
  limit = 40,
  compact = false,
}: Props) {
  const { t } = useI18n();
  const [rows, setRows] = useState<SectorRow[] | null>(null);
  const [minNames, setMinNames] = useState(3);
  const [openSector, setOpenSector] = useState<string | null>(null);
  const [peers, setPeers] = useState<CompanySummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSectorLeaderboard({ market, index, limit })
      .then((r) => {
        if (!cancelled) {
          setRows((r.sectors || []) as SectorRow[]);
          if (r.min_names) setMinNames(r.min_names);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [market, index, limit]);

  function toggleSector(sector: string) {
    if (openSector === sector) {
      setOpenSector(null);
      setPeers([]);
      return;
    }
    setOpenSector(sector);
    setPeers([]);
    fetchSectorBenchmark(sector)
      .then((b) => setPeers(b.companies || []))
      .catch(() => setPeers([]));
  }

  if (error) {
    return (
      <div className="panel" data-testid="sector-leaderboard">
        <p className="muted">{t("ui.SectorLeaderboard.unavailable", { error })}</p>
      </div>
    );
  }
  if (rows === null) return null;
  const averaged = rows.filter((s) => s.avg != null);
  const building = rows.filter((s) => s.avg == null);
  const published = rows.reduce((n, s) => n + (s.count || 0), 0);

  return (
    <div className="panel" data-testid="sector-leaderboard">
      <div className="panel-head">
        <h2>
          {t("ui.SectorLeaderboard.title")} <InfoTip termId="sector_avg" />
        </h2>
        {!compact && (
          <span className="muted" style={{ fontSize: 13 }}>
            {t("ui.SectorLeaderboard.subtitle")}
          </span>
        )}
      </div>
      {!compact && (
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          {t("ui.SectorLeaderboard.lede")}
        </p>
      )}
      <p data-testid="sector-coverage">
        {published === 0
          ? t("ui.SectorLeaderboard.nonePublished")
          : averaged.length === 0
            ? t("ui.SectorLeaderboard.noneAveraged", { n: published, sectors: rows.length, min: minNames })
            : t("ui.SectorLeaderboard.coverage", { n: published, sectors: rows.length, averaged: averaged.length, min: minNames })}{" "}
        {published === 0 ? <Link to="/tracker">{t("ui.SectorLeaderboard.openScreener")}</Link> : null}
      </p>
      {averaged.length > 0 && (
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>{t("ui.SectorLeaderboard.th.sector")}</th>
              <th>{t("ui.SectorLeaderboard.th.avg")}</th>
              <th>{t("ui.SectorLeaderboard.th.names")}</th>
              <th>{t("ui.SectorLeaderboard.th.best")}</th>
            </tr>
          </thead>
          <tbody>
            {averaged.map((s, i) => (
              <tr
                key={s.sector}
                className="row-link"
                onClick={() => toggleSector(s.sector)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSector(s.sector);
                  }
                }}
                tabIndex={0}
                style={{ cursor: "pointer" }}
                data-testid={`sector-row-${s.sector}`}
              >
                <td>{i + 1}</td>
                <td>
                  <strong>{s.sector}</strong>{" "}
                  <span className="muted" style={{ fontSize: 12 }}>
                    {openSector === s.sector ? "▾" : "▸"}
                  </span>
                </td>
                <td className={`score ${scoreClass(s.avg)}`}>{formatScore(s.avg)}</td>
                <td>{s.count}</td>
                <td>
                  {s.best ? (
                    <>
                      <Link to={`/companies/${s.best.id}`} onClick={(e) => e.stopPropagation()}>
                        {s.best.ticker}
                      </Link>{" "}
                      <span className={`score ${scoreClass(s.best.gci_score)}`}>
                        {formatScore(s.best.gci_score)}
                      </span>
                    </>
                  ) : (
                    <span className="muted" title={t("ui.SectorLeaderboard.bestNone")}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
      {building.length > 0 && (
        <div className="table-scroll" data-testid="sector-building">
          <h3 style={{ fontSize: 14 }}>{t("ui.SectorLeaderboard.buildingTitle", { min: minNames })}</h3>
          <table className="table">
            <thead>
              <tr>
                <th>{t("ui.SectorLeaderboard.th.sector")}</th>
                <th className="num">{t("ui.SectorLeaderboard.th.published")}</th>
                <th>{t("ui.SectorLeaderboard.th.companies")}</th>
              </tr>
            </thead>
            <tbody>
              {building.map((s) => (
                <tr key={s.sector} data-testid={`sector-building-${s.sector}`}>
                  <td>
                    <strong>{s.sector}</strong>
                  </td>
                  <td className="num">
                    {s.count} / {minNames}
                  </td>
                  <td>
                    {(s.names || []).map((n, i) => (
                      <span key={n.id}>
                        {i > 0 ? " · " : ""}
                        <Link to={`/companies/${n.id}`}>{n.name}</Link>{" "}
                        <TierBadge tier={(n.confidence_tier || null) as ConfidenceTier | null} />
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {openSector && (
        <div className="sector-peers" data-testid="sector-peers">
          <h3 style={{ fontSize: 14 }}>{t("ui.SectorLeaderboard.peerRanking", { sector: openSector })}</h3>
          <ul className="peer-list">
            {peers.slice(0, compact ? 8 : 15).map((c) => (
              <li key={c.id}>
                <Link to={`/companies/${c.id}`}>
                  {c.ticker} · {c.name}
                </Link>{" "}
                <span className={`score ${scoreClass(c.gci_score)}`}>
                  {formatCompanyScore(c.gci_score) === NOT_SCORED_LABEL
                    ? t("ui.ScoreReveal.notScored")
                    : formatCompanyScore(c.gci_score)}
                </span>
              </li>
            ))}
            {peers.length === 0 && <li className="muted">{t("ui.SectorLeaderboard.loadingPeers")}</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
