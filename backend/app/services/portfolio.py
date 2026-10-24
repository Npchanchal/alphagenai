"""Parallel product catalog + Radar / Ledger / Data compositions.

Composes existing repository outcomes, alerts, and promise briefs.
Does not invent financial actuals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services import repository
from app.services.research import promise_brief

PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "score",
        "name": "CiteAlpha Score",
        "job": "GCI 0–100 + peer delivery benchmarks",
        "status": "live",
        "buyer": "Buy-side / sell-side analysts",
        "endpoints": [
            "/api/companies",
            "/api/companies/{id}/gci",
            "/api/public/gci-rankings",
            "/api/peers/{sector}",
        ],
        "ui": ["/", "/tracker", "/companies/:id", "/rankings"],
        "docs": "docs/customer/skus/SCORE.md",
    },
    {
        "id": "cite",
        "name": "CiteAlpha Cite",
        "job": "Mandatory primary citations + Research Terminal",
        "status": "live",
        "buyer": "Research ops / AI copilots",
        "endpoints": [
            "/api/citations",
            "/api/citations/{id}",
            "/api/research/chat",
            "/api/research/search",
        ],
        "ui": ["/research", "/c/:citationId", "/trust"],
        "docs": "docs/customer/skus/CITE.md",
    },
    {
        "id": "radar",
        "name": "CiteAlpha Radar",
        "job": "Guidance change / miss / drop / withdrawal feed",
        "status": "live",
        "buyer": "PMs, risk, IR-watch desks",
        "endpoints": ["/api/radar/feed", "/api/alerts"],
        "ui": ["/products", "/desk"],
        "delivery": "Weekly digest and webhook/Slack/Teams delivery through CiteAlpha Analyst (/api/analyst/digest, /api/analyst/destinations)",
        "docs": "docs/customer/skus/RADAR.md",
        "phase": "P2",
        "endpoints_extended": [
            "/api/radar/diff/{company_id}",
            "/api/radar/calendar",
        ],
    },
    {
        "id": "ledger",
        "name": "CiteAlpha Ledger",
        "job": "Promise ledger / accountability dossier",
        "status": "live",
        "buyer": "Compliance, credit, IR, board packs",
        "endpoints": [
            "/api/ledger/{company_id}",
            "/api/research/brief/{company_id}",
        ],
        "ui": ["/products", "/companies/:id"],
        "docs": "docs/customer/skus/LEDGER.md",
        "phase": "P3",
        "endpoints_extended": [
            "/api/ledger/{company_id}/pdf",
            "/api/ledger/mirror/{company_id}",
            "?credit_only=true",
        ],
    },
    {
        "id": "data",
        "name": "CiteAlpha Data",
        "job": "PIT guidance-outcome dataset + factor export",
        "status": "live",
        "buyer": "Quant / alt-data / platforms",
        "endpoints": [
            "/api/data/catalog",
            "/api/v1/pit/companies/{company_id}/history",
            "/api/companies/{id}/gci/history",
            "/api/export/em-factor/{company_id}",
        ],
        "ui": ["/products"],
        "docs": "docs/customer/skus/DATA.md",
        "phase": "P4",
        "endpoints_extended": [
            "/api/data/export/outcomes",
            "/api/cite/usage",
            "/api/cite/tiers",
            "/api/digest/vernacular/{company_id}",
            "/api/data/kpi-dictionary",
        ],
    },
    {
        "id": "sights",
        "name": "CiteAlpha Sights",
        "job": "India disclosure research OS — search, cite GenAI, grids, agents",
        "status": "live",
        "buyer": "India equity research desks (alongside Score/Cite)",
        "endpoints": [
            "/api/sights/meta",
            "/api/sights/search",
            "/api/sights/ask",
            "/api/sights/themes",
            "/api/sights/street/{company_id}",
            "/api/sights/field/{company_id}",
        ],
        "ui": ["/sights", "/sights/search", "/sights/ask", "/sights/boards"],
        "docs": "docs/customer/skus/SIGHTS.md",
        "phase": "S0–S6",
        "endpoints_extended": [
            "/api/sights/grid",
            "/api/sights/deep-dive",
            "/api/sights/fundamentals/{company_id}",
            "/api/sights/agents",
            "/api/sights/agents/run",
            "/api/sights/hooks",
            "/api/sights/export/{company_id}",
            "/api/sights/enterprise",
        ],
    },
    {
        "id": "holdings",
        "name": "CiteAlpha Holdings",
        "job": "Holdings-weighted published GCI, coverage, and residual assets",
        "status": "live",
        "buyer": "MF, PMS, AIF, and pension desks",
        "endpoints": ["/api/holdings/lookthrough", "/api/holdings/latest"],
        "ui": ["/holdings"],
        "docs": "docs/customer/skus/HOLDINGS.md",
        "note": (
            "Reads published company scores. A missing score stays out of the weighted figure. "
            "Open during an admin-approved 30, 45, or 60 day pilot, and on a paid desk after that."
        ),
    },
]

_SEV_RANK = {"high": 0, "medium": 1, "low": 2}

_REVISION_KINDS = frozenset(
    {
        "revised_up",
        "revised_down",
        "withdrawn",
        "restatement",
        "resolved_missed",
    }
)


def list_products() -> Dict[str, Any]:
    return {
        "product": "CiteAlpha Portfolio",
        "entity": "Ocotillo Innovation Private Limited",
        "note": (
            "Parallel SKUs on one India disclosure spine. "
            "Factual research tooling — not investment advice."
        ),
        "disclaimer": "Not investment advice. No Buy/Hold/Sell recommendations.",
        "catalog_doc": "docs/PRODUCT_PORTFOLIO.md",
        "roadmap_doc": "docs/PORTFOLIO_ROADMAP.md",
        "products": PRODUCTS,
    }


def radar_feed(
    *,
    company_id: Optional[str] = None,
    limit: int = 50,
    include_revisions: bool = True,
) -> Dict[str, Any]:
    """Unified near-term change feed for CiteAlpha Radar."""
    limit = max(1, min(int(limit), 200))
    items: List[Dict[str, Any]] = []

    for a in repository.list_alerts():
        if company_id and a.company_id != company_id:
            continue
        items.append(
            {
                "source": "alert",
                "company_id": a.company_id,
                "ticker": a.ticker,
                "kind": a.kind,
                "message": a.message,
                "severity": a.severity,
                "period": a.period,
                "metric": a.metric,
                "source_url": a.source_url,
                "audit_flag": a.audit_flag,
                "deduction_pts": a.deduction_pts,
                "as_of": a.period,
            }
        )

    if include_revisions:
        # Prefer companies already on the alert rail; otherwise a bounded universe scan.
        alert_ids = {a.company_id for a in repository.list_alerts()}
        if company_id:
            targets = [c for c in repository.list_company_summaries() if c.id == company_id]
        else:
            summaries = repository.list_company_summaries()
            by_id = {c.id: c for c in summaries}
            targets = [by_id[i] for i in alert_ids if i in by_id]
            if len(targets) < 15:
                for c in summaries:
                    if c.id in alert_ids:
                        continue
                    targets.append(c)
                    if len(targets) >= 15:
                        break

        for c in targets:
            try:
                detail = repository.get_company_gci(c.id)
            except Exception:
                continue
            for ev in detail.revision_timeline or []:
                if ev.get("kind") not in _REVISION_KINDS:
                    continue
                items.append(
                    {
                        "source": "revision",
                        "company_id": c.id,
                        "ticker": c.ticker,
                        "kind": ev["kind"],
                        "message": ev.get("detail") or ev["kind"],
                        "severity": ev.get("severity") or "medium",
                        "period": ev.get("period"),
                        "metric": ev.get("metric"),
                        "source_url": ev.get("source_url"),
                        "audit_flag": None,
                        "deduction_pts": None,
                        "as_of": ev.get("as_of"),
                    }
                )
            for ra in detail.red_alerts or []:
                items.append(
                    {
                        "source": "audit",
                        "company_id": ra.get("company_id") or c.id,
                        "ticker": ra.get("ticker") or c.ticker,
                        "kind": ra.get("kind"),
                        "message": ra.get("message"),
                        "severity": ra.get("severity") or "high",
                        "period": ra.get("period"),
                        "metric": ra.get("metric"),
                        "source_url": ra.get("source_url"),
                        "audit_flag": ra.get("kind"),
                        "deduction_pts": ra.get("deduction_pts"),
                        "as_of": ra.get("period"),
                    }
                )

    # Deduplicate by company + kind + period + metric + message
    seen: set[tuple] = set()
    unique: List[Dict[str, Any]] = []
    for row in items:
        key = (
            row.get("company_id"),
            row.get("kind"),
            row.get("period"),
            row.get("metric"),
            row.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    # High severity first; within severity, newest as_of first
    buckets: Dict[int, List[Dict[str, Any]]] = {}
    for r in unique:
        rank = _SEV_RANK.get(str(r.get("severity") or "low"), 9)
        buckets.setdefault(rank, []).append(r)
    ordered: List[Dict[str, Any]] = []
    for rank in sorted(buckets.keys()):
        bucket = buckets[rank]
        bucket.sort(key=lambda r: str(r.get("as_of") or ""), reverse=True)
        ordered.extend(bucket)

    trimmed = ordered[:limit]
    return {
        "product": "CiteAlpha Radar",
        "company_id": company_id,
        "count": len(trimmed),
        "items": trimmed,
        "note": (
            "Composed from alerts, revision events, and audit flags. "
            "Factual change feed — not a trading signal."
        ),
        "disclaimer": "Not investment advice.",
    }


def company_ledger(company_id: str) -> Dict[str, Any]:
    """Accountability dossier: closed outcomes + open promises + sources."""
    detail = repository.get_company_gci(company_id)
    brief = promise_brief(company_id)

    closed: List[Dict[str, Any]] = []
    for o in detail.outcomes:
        if o.label == "pending":
            continue
        closed.append(
            {
                "period": o.period,
                "metric": o.metric,
                "status": o.label,
                "guided_value": o.guided_value,
                "guided_low": o.guided_low,
                "guided_high": o.guided_high,
                "actual_value": o.actual_value,
                "delta_pct": o.delta_pct,
                "guided_text": o.guided_text,
                "speaker": o.speaker,
                "source_url": o.source_url,
                "source_ref": o.source_ref,
                "quote_span": o.quote_span,
                "citation_id": getattr(o, "citation_id", None),
                "as_of": o.as_of,
                "thread_id": o.thread_id,
                "dropped": o.dropped,
            }
        )

    by_status: Dict[str, int] = {}
    for row in closed:
        st = str(row["status"] or "unknown")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "product": "CiteAlpha Ledger",
        "company_id": detail.id,
        "name": detail.name,
        "ticker": detail.ticker,
        "sector": detail.sector,
        "data_quality": detail.data_quality,
        "gci_score": detail.gci_score,
        "summary": {
            "closed_count": len(closed),
            "open_promise_count": brief.get("open_promise_count", 0),
            "by_status": by_status,
        },
        "closed_promises": closed,
        "open_promises": brief.get("promises", []),
        "note": (
            "Audit-oriented promise ledger. GCI score is optional context — "
            "every row links to guidance and subsequent actual when closed."
        ),
        "disclaimer": "Not investment advice. Not a credit rating.",
    }


def data_catalog() -> Dict[str, Any]:
    return {
        "product": "CiteAlpha Data",
        "note": (
            "Point-in-time guidance outcomes and factor export shapes. "
            "Does not invent actuals; quality flags are first-class."
        ),
        "disclaimer": "Not investment advice.",
        "exports": [
            {
                "id": "pit_history",
                "path": "/api/companies/{id}/gci/history",
                "format": "json",
                "description": "Point-in-time GCI series per company",
            },
            {
                "id": "pit_v1",
                "path": "/api/v1/pit/companies/{company_id}/history",
                "format": "json",
                "description": "Versioned PIT history for embed clients",
            },
            {
                "id": "pit_contract",
                "path": "/api/v1/pit/contract",
                "format": "json",
                "description": "Schema / contract description for PIT payloads",
            },
            {
                "id": "em_factor",
                "path": "/api/export/em-factor/{company_id}",
                "format": "json",
                "description": "EM factor export shape for quant research",
            },
            {
                "id": "company_gci",
                "path": "/api/companies/{id}/gci",
                "format": "json",
                "description": "Full dossier including outcomes (guided band, actual, label)",
            },
            {
                "id": "ledger",
                "path": "/api/ledger/{company_id}",
                "format": "json",
                "description": "Promise ledger composition for accountability packs",
            },
            {
                "id": "ledger_pdf",
                "path": "/api/ledger/{company_id}/pdf",
                "format": "pdf",
                "description": "Board / IC promise ledger PDF (API key)",
            },
            {
                "id": "outcomes_bulk",
                "path": "/api/data/export/outcomes",
                "format": "json|csv|parquet",
                "description": "Bulk guidance outcomes export",
            },
            {
                "id": "kpi_dictionary",
                "path": "/api/data/kpi-dictionary",
                "format": "json",
                "description": "India metric ontology (P5 infrastructure)",
            },
        ],
        "roadmap": [
            "Redistribution rights tiers in MSA",
        ],
        "docs": "docs/customer/skus/DATA.md",
    }
