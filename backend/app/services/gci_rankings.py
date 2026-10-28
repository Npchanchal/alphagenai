"""Public citeable-only GCI ranking report (content / GTM)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services import repository
from app.services.score_policy import RANKABLE_TIERS, is_rankable

RANKED_THRESHOLD = 20


def gci_rankings(
    *,
    market: str = "IN",
    index: str = "SENSEX",
    limit: int = 30,
    citeable_only: bool = True,
) -> Dict[str, Any]:
    """Rank companies by GCI — hand_labeled rows with an *established* or *deep*
    confidence tier only (W1.3). Provisional scores are published on the dossier
    but never ranked."""
    rows = repository.list_company_summaries(market=market, index=index)
    scored: List[Dict[str, Any]] = []
    for c in rows:
        quality = (c.data_quality or "").lower()
        if citeable_only and quality != "hand_labeled":
            continue
        score = c.gci_score
        if score is None:
            continue
        if not is_rankable(c.confidence_tier):
            continue
        # Prefer companies with at least one citeable outcome when available
        try:
            outs = repository.get_company_gci(c.id).outcomes
            cite_n = sum(1 for o in outs if o.citeable)
        except Exception:
            cite_n = 0
        if citeable_only and cite_n < 1 and quality != "hand_labeled":
            continue
        scored.append(
            {
                "rank": 0,
                "company_id": c.id,
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "gci_score": score,
                "delta": c.gci_change_pct,
                "wow_pct": getattr(c, "wow_pct", None),
                "mom_pct": getattr(c, "mom_pct", None),
                "qoq_pct": getattr(c, "qoq_pct", None),
                "yoy_pct": getattr(c, "yoy_pct", None),
                "data_quality": c.data_quality,
                "citeable_outcomes": cite_n,
                "confidence_tier": c.confidence_tier,
                "closed_periods": c.closed_periods,
                "metrics_scored": c.metrics_scored,
                "as_of": c.as_of,
                "algorithm_id": c.algorithm_id,
            }
        )

    scored.sort(key=lambda r: (-float(r["gci_score"]), r["ticker"]))
    lim = max(1, min(int(limit), 100))
    top = scored[:lim]
    bottom = list(reversed(scored[-lim:])) if len(scored) > lim else list(reversed(scored))
    for i, row in enumerate(top, start=1):
        row["rank"] = i
    for i, row in enumerate(bottom, start=1):
        row["rank"] = i

    as_of = datetime.now(timezone.utc).date().isoformat()
    records = _delivery_records(rows)
    ranked = len(scored) >= RANKED_THRESHOLD
    return {
        "title": (
            "Guidance Credibility Quarterly — ranked"
            if ranked
            else "Delivery record — published GCI, not a rank"
        ),
        "as_of": as_of,
        "market": market,
        "index": index,
        "citeable_only": citeable_only,
        "universe_n": len(scored),
        "mode": "ranked" if ranked else "record",
        "ranked_threshold": RANKED_THRESHOLD,
        "records": records,
        "top": top if ranked else [],
        "bottom": bottom if ranked else [],
        "tiers_ranked": sorted(RANKABLE_TIERS),
        "methodology": (
            "Ranks use analyst-reviewed GCI with an established or deep confidence tier "
            "(≥3 closed reporting periods across ≥2 metrics). Provisional scores and sample data "
            "are excluded. Not investment advice; no Buy/Hold/Sell."
        ),
        "legal": (
            "© Ocotillo Innovation Private Limited. Factual research tooling — "
            "not a SEBI-registered research analyst product."
        ),
    }


def _delivery_records(summaries: List[Any]) -> List[Dict[str, Any]]:
    """Scored hand-labeled names for the Snapshot record table (until ranked mode)."""
    out: List[Dict[str, Any]] = []
    for c in summaries:
        if (c.data_quality or "").lower() != "hand_labeled":
            continue
        if c.gci_score is None:
            continue
        try:
            detail = repository.get_company_gci(c.id)
        except Exception:
            continue
        counts = detail.label_counts or {}
        out.append(
            {
                "company_id": c.id,
                "ticker": c.ticker,
                "name": c.name,
                "confidence_tier": c.confidence_tier,
                "gci_score": c.gci_score,
                "met": int(counts.get("met") or 0),
                "exceeded": int(counts.get("exceeded") or 0),
                "missed": int(counts.get("missed") or 0),
                "as_of": c.as_of,
                "closed_periods": c.closed_periods,
            }
        )
    out.sort(key=lambda r: (-int(r.get("closed_periods") or 0), r["ticker"]))
    return out


def rankings_markdown(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    data = payload or gci_rankings(**kwargs)
    lines = [
        f"# {data['title']}",
        "",
        (
            f"**As of:** {data['as_of']} · **Universe:** {data['index']} ({data['market']}) · "
            f"{data['universe_n']} established or deep names ranked"
            if data.get("mode") == "ranked"
            else f"**As of:** {data['as_of']} · **Universe:** {data['index']} ({data['market']}) · "
            f"{len(data.get('records') or [])} published names, shown as a delivery record. "
            "A provisional row is not a rank."
        ),
        "",
        data["methodology"],
        "",
    ]
    if data.get("mode") == "ranked":
        lines += [
            "## Top management delivery (GCI)",
            "",
            "| Rank | Ticker | Name | Sector | GCI | Citeable rows |",
            "|---|---|---|---|---|---|",
        ]
        for r in data["top"]:
            lines.append(
                f"| {r['rank']} | {r['ticker']} | {r['name']} | {r['sector']} | "
                f"{r['gci_score']} | {r['citeable_outcomes']} |"
            )
        lines += [
            "",
            "## Lowest GCI (same citeable universe)",
            "",
            "| Rank | Ticker | Name | Sector | GCI | Citeable rows |",
            "|---|---|---|---|---|---|",
        ]
        for r in data["bottom"]:
            lines.append(
                f"| {r['rank']} | {r['ticker']} | {r['name']} | {r['sector']} | "
                f"{r['gci_score']} | {r['citeable_outcomes']} |"
            )
    else:
        lines += [
            "## Delivery record (ranked view opens at 20 Established names)",
            "",
            "| Company | Tier | Met | Exceeded | Missed | Last filing |",
            "|---|---|---|---|---|---|",
        ]
        for r in data.get("records") or []:
            lines.append(
                f"| {r['ticker']} {r['name']} | {(r.get('confidence_tier') or '').capitalize()} | "
                f"{r.get('met', 0)} | {r.get('exceeded', 0)} | {r.get('missed', 0)} | "
                f"{r.get('as_of') or ''} |"
            )
    lines += ["", "---", data["legal"], ""]
    return "\n".join(lines)
