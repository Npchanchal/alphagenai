"""CiteAlpha Sights — India disclosure research OS (parallel SKU).

Composes research, GCI, citations, and Radar hooks. Does not redistribute
sell-side broker PDFs or operate an expert-call marketplace.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from app.services import repository
from app.services import research as research_svc
from app.services.feature_flags import (
    sights_deep_dive_enabled,
    sights_enabled,
    sights_grid_enabled,
    sights_web_assist_enabled,
)

# India IR business-language expansions (Business Lexicon).
_LEXICON: Dict[str, List[str]] = {
    "revenue": ["topline", "top line", "sales", "turnover", "net sales"],
    "topline": ["revenue", "sales", "turnover"],
    "ebitda": ["operating profit", "opbdita", "ebitda margin"],
    "margin": ["ebitda margin", "operating margin", "gross margin", "npm"],
    "capex": ["capital expenditure", "capital outlay", "gross block"],
    "guidance": ["outlook", "guided", "guide", "management expects"],
    "pat": ["net profit", "profit after tax", "bottom line"],
    "npa": ["asset quality", "slippages", "gnpa", "nnpa"],
    "aum": ["assets under management", "mf aum"],
}

_DISCLAIMER = (
    "Not investment advice. CiteAlpha Sights uses public IR, filings, concalls, "
    "and CiteAlpha-labeled outcomes — not sell-side note redistribution."
)


def _refuse_disabled(feature: str) -> Dict[str, Any]:
    return {
        "product": "CiteAlpha Sights",
        "enabled": False,
        "feature": feature,
        "message": f"{feature} is gated. Set the matching SIGHTS_* flag to enable.",
        "disclaimer": _DISCLAIMER,
    }


def expand_query_lexicon(query: str) -> str:
    """Expand query with India IR synonyms (Business Lexicon)."""
    q = (query or "").strip()
    if not q:
        return q
    lower = q.lower()
    extras: List[str] = []
    for key, syns in _LEXICON.items():
        if key in lower or any(s in lower for s in syns):
            extras.extend([key, *syns])
    if not extras:
        return q
    # Dedupe while preserving order
    seen = set()
    parts = [q]
    for t in extras:
        tl = t.lower()
        if tl not in seen and tl not in lower:
            seen.add(tl)
            parts.append(t)
    return " ".join(parts)


def sights_meta() -> Dict[str, Any]:
    return {
        "product": "CiteAlpha Sights",
        "sku_id": "sights",
        "enabled": sights_enabled(),
        "job": "Compare disclosures across Indian listed companies — themes, street context, field evidence, grids, deep dives",
        "vertical": "India Equity Desk",
        "ui": [
            "/sights",
            "/sights/themes",
            "/sights/street",
            "/sights/field",
            "/sights/grid",
            "/sights/deep-dive",
            "/sights/fundamentals",
            "/sights/settings",
        ],
        "flags": {
            "SIGHTS": sights_enabled(),
            "SIGHTS_DEEP_DIVE": sights_deep_dive_enabled(),
            "SIGHTS_GRID": sights_grid_enabled(),
            "SIGHTS_WEB_ASSIST": sights_web_assist_enabled(),
        },
        "brand_map": {
            "themes": "Delivery Themes",
            "deep_dive": "Deep Dive",
            "grid": "Compare Grid",
            "street": "Street Context",
            "field": "Field Evidence",
            "fundamentals": "Fundamentals Strip",
        },
        "moved": {
            "search": "/research?scope=all",
            "ask": "/research?tab=chat&scope=all",
            "boards": "/research?tab=watch",
            "agents": "/analyst",
            "export": "/analyst",
            "hooks": "/analyst",
        },
        "refuse": [
            "Unlicensed sell-side broker PDF corpus",
            "Expert-call marketplace / brokerage",
            "Competitor product trademarks in UI",
            "Buy/Hold/Sell recommendations",
            "Claims of hundreds of millions of documents",
        ],
        "variants": {
            "grid": "Compare Grid — prompt×company cite table (not competitor Generative Grid naming)",
            "street": "Street Context — public IR + licensed consensus (not broker PDF library)",
            "field": "Field Evidence — labeled outcomes + citations (not expert-call brokerage)",
            "themes": "Delivery Themes — met/miss/drop/pending (not sentiment OS)",
            "deep_dive": "Deep Dive — multi-step cite synthesis",
        },
        "content_model": (
            "Public IR + exchange filings + concalls + CiteAlpha labels + "
            "licensed consensus APIs we pay for. No Tegus-style expert network. "
            "No hosting or proxying sell-side research PDFs without redistribution rights."
        ),
        "related_skus": ["cite", "score", "radar", "ledger", "data"],
        "enterprise": {
            "trust": "/trust",
            "sso_docs": "docs/OIDC.md",
            "billing": "/billing",
            "package": "/products#plans",
            "desk_seats": "/desk",
        },
        "stretch": {
            "licensed_third_party": "Counsel-gated only; written redistribution rights required",
            "office_addins": "Deferred to S6 after pilot demand",
            "slack_teams": "Delivered by CiteAlpha Analyst destinations (webhook, Slack, Teams)",
        },
        "disclaimer": _DISCLAIMER,
        "docs": "docs/customer/skus/SIGHTS.md",
    }


def sights_search(
    query: str,
    *,
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    if not sights_enabled():
        return _refuse_disabled("Sights Search")
    expanded = expand_query_lexicon(query)
    result = research_svc.search_documents(
        expanded, company_id=company_id, doc_type=doc_type, limit=limit
    )
    result["product"] = "CiteAlpha Sights Search"
    result["superseded_by"] = "/api/research/search?expand=true"
    result["lexicon_expanded"] = expanded != (query or "").strip()
    result["original_query"] = query
    result["expanded_query"] = expanded
    result["disclaimer"] = _DISCLAIMER
    return result


def sights_ask(
    question: str,
    *,
    company_id: Optional[str] = None,
    web_assist: bool = False,
) -> Dict[str, Any]:
    if not sights_enabled():
        return _refuse_disabled("Sights Ask")
    expanded = expand_query_lexicon(question)
    result = research_svc.research_chat(expanded, company_id=company_id)
    result["product"] = "CiteAlpha Sights Ask"
    result["superseded_by"] = "/api/research/chat"
    result["lexicon_expanded"] = expanded != (question or "").strip()
    result["web_assist"] = {
        "requested": bool(web_assist),
        "enabled": sights_web_assist_enabled(),
        "used": False,
        "note": (
            "Web Assist is off by default. When enabled it will only attach "
            "cited open-web snippets — never invent actuals."
            if not sights_web_assist_enabled()
            else "Web Assist flag on; open-web fetch not wired in MVP (cite IR only)."
        ),
    }
    result["disclaimer"] = _DISCLAIMER
    return result


def delivery_themes(
    *,
    company_id: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 40,
) -> Dict[str, Any]:
    """Aggregate met/miss/drop/pending labels — not retail sentiment."""
    if not sights_enabled():
        return _refuse_disabled("Delivery Themes")
    limit = max(1, min(int(limit), 200))
    by_label: Counter[str] = Counter()
    by_metric: Dict[str, Counter[str]] = defaultdict(Counter)
    rows_out: List[Dict[str, Any]] = []

    from app.data.seed import list_companies

    companies = list_companies()
    for c in companies:
        if company_id and c["id"] != company_id:
            continue
        if sector and (c.get("sector") or "").lower() != sector.lower():
            continue
        try:
            detail = repository.get_company_gci(c["id"])
        except Exception:
            continue
        dq = getattr(detail, "data_quality", None) or c.get("data_quality") or "demo_structured"
        for o in detail.outcomes or []:
            label = (o.label or "unmapped").lower()
            metric = o.metric or "unknown"
            by_label[label] += 1
            by_metric[metric][label] += 1
            if len(rows_out) < limit:
                rows_out.append(
                    {
                        "company_id": c["id"],
                        "ticker": c.get("ticker") or detail.ticker,
                        "metric": metric,
                        "period": o.period,
                        "label": label,
                        "data_quality": dq,
                    }
                )

    themes = [
        {
            "theme": label,
            "count": count,
            "kind": "delivery_label",
            "note": "Guidance delivery label — not news sentiment",
        }
        for label, count in by_label.most_common()
    ]
    metric_themes = [
        {
            "metric": metric,
            "labels": dict(counts),
            "dominant": counts.most_common(1)[0][0] if counts else None,
        }
        for metric, counts in sorted(by_metric.items(), key=lambda x: -sum(x[1].values()))[:20]
    ]
    return {
        "product": "CiteAlpha Delivery Themes",
        "company_id": company_id,
        "sector": sector,
        "themes": themes,
        "metric_themes": metric_themes,
        "sample_rows": rows_out,
        "disclaimer": _DISCLAIMER,
    }


def street_context(company_id: str) -> Dict[str, Any]:
    """Street vs management guidance from public/licensed APIs — not broker notes."""
    if not sights_enabled():
        return _refuse_disabled("Street Context")
    estimates = research_svc.consensus_estimates(company_id)
    search = research_svc.search_documents(
        "guidance outlook", company_id=company_id, limit=5
    )
    return {
        "product": "CiteAlpha Street Context",
        "company_id": company_id,
        "note": (
            "Public Street Context: management guidance vs street consensus from "
            "sources CiteAlpha is entitled to use. This is not sell-side research "
            "note redistribution."
        ),
        "estimates": estimates,
        "public_filing_snippets": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "date": r.get("date"),
                "snippet": r.get("snippet"),
                "url": r.get("url"),
                "doc_type": r.get("doc_type"),
            }
            for r in search.get("results") or []
        ],
        "disclaimer": _DISCLAIMER,
    }


def field_evidence(company_id: str) -> Dict[str, Any]:
    """Hand-labeled outcomes + citation trail as primary-research substitute."""
    if not sights_enabled():
        return _refuse_disabled("Field Evidence")
    from app.services.citations import list_company_citations

    detail = repository.get_company_gci(company_id)
    dq = getattr(detail, "data_quality", None) or "demo_structured"
    citations = list_company_citations(company_id, citeable_only=True)
    outcomes = []
    for o in detail.outcomes or []:
        outcomes.append(
            {
                "metric": o.metric,
                "period": o.period,
                "label": o.label,
                "guided_low": getattr(o, "guided_low", None),
                "guided_high": getattr(o, "guided_high", None),
                "guided_value": getattr(o, "guided_value", None),
                "actual": getattr(o, "actual_value", None),
                "source_url": getattr(o, "source_url", None),
                "source_ref": getattr(o, "source_ref", None),
                "quote_span": getattr(o, "quote_span", None),
            }
        )
    return {
        "product": "CiteAlpha Field Evidence",
        "company_id": company_id,
        "ticker": detail.ticker,
        "name": detail.name,
        "data_quality": dq,
        "gci_score": detail.gci_score,
        "outcomes": outcomes,
        "citations": citations,
        "empty_demo": dq == "demo_structured" and not any(
            (getattr(o, "source_url", None) or getattr(o, "quote_span", None))
            for o in (detail.outcomes or [])
        ),
        "note": (
            "Field Evidence is CiteAlpha-authored labeling and public IR citations — "
            "not an expert-interview marketplace."
        ),
        "disclaimer": _DISCLAIMER,
    }


def compare_grid(
    prompts: List[str],
    *,
    company_ids: Optional[List[str]] = None,
    limit_per_cell: int = 2,
) -> Dict[str, Any]:
    if not sights_enabled():
        return _refuse_disabled("Compare Grid")
    if not sights_grid_enabled():
        return _refuse_disabled("SIGHTS_GRID")
    prompts = [p.strip() for p in prompts if p and p.strip()][:8]
    if not prompts:
        return {
            "product": "CiteAlpha Compare Grid",
            "refused": True,
            "message": "Provide at least one prompt.",
            "rows": [],
            "disclaimer": _DISCLAIMER,
        }
    from app.data.seed import list_companies

    ids = company_ids or [c["id"] for c in list_companies()[:5]]
    ids = ids[:8]
    rows: List[Dict[str, Any]] = []
    for prompt in prompts:
        cells = []
        for cid in ids:
            ask = sights_ask(prompt, company_id=cid)
            cites = (ask.get("citations") or [])[:limit_per_cell]
            cells.append(
                {
                    "company_id": cid,
                    "answer": ask.get("answer"),
                    "refused": bool(ask.get("refused")),
                    "citations": cites,
                }
            )
        rows.append({"prompt": prompt, "cells": cells})
    return {
        "product": "CiteAlpha Compare Grid",
        "company_ids": ids,
        "rows": rows,
        "disclaimer": _DISCLAIMER,
    }


def deep_dive(topic: str, *, company_id: Optional[str] = None) -> Dict[str, Any]:
    if not sights_enabled():
        return _refuse_disabled("Deep Dive")
    if not sights_deep_dive_enabled():
        return _refuse_disabled("SIGHTS_DEEP_DIVE")
    topic = (topic or "").strip()
    if not topic:
        return {
            "product": "CiteAlpha Deep Dive",
            "refused": True,
            "message": "Provide a topic.",
            "steps": [],
            "disclaimer": _DISCLAIMER,
        }
    sub_queries = [
        topic,
        f"{topic} guidance outlook",
        f"{topic} margin capex delivery",
        f"{topic} missed exceeded",
    ]
    steps: List[Dict[str, Any]] = []
    all_cites: List[Dict[str, Any]] = []
    for i, sq in enumerate(sub_queries, start=1):
        ask = sights_ask(sq, company_id=company_id)
        steps.append(
            {
                "step": i,
                "query": sq,
                "refused": bool(ask.get("refused")),
                "answer": ask.get("answer"),
                "citations": ask.get("citations") or [],
            }
        )
        if not ask.get("refused"):
            all_cites.extend(ask.get("citations") or [])
    if not all_cites:
        return {
            "product": "CiteAlpha Deep Dive",
            "topic": topic,
            "company_id": company_id,
            "refused": True,
            "message": (
                "Deep Dive refused — no cited evidence in the India disclosure corpus "
                "for this topic."
            ),
            "steps": steps,
            "report": None,
            "disclaimer": _DISCLAIMER,
        }
    # Deduplicate citations by id
    seen = set()
    unique = []
    for c in all_cites:
        cid = c.get("id") or c.get("citation_id") or str(c.get("n"))
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(c)
    report_parts = [f"# Deep Dive: {topic}", "", _DISCLAIMER, ""]
    for s in steps:
        if s["refused"]:
            continue
        report_parts.append(f"## Step {s['step']}: {s['query']}")
        report_parts.append(s["answer"] or "")
        report_parts.append("")
    report_parts.append("## Sources")
    for i, c in enumerate(unique[:12], start=1):
        title = c.get("title") or c.get("bibliographic") or c.get("id") or "source"
        report_parts.append(f"{i}. {title}")
    return {
        "product": "CiteAlpha Deep Dive",
        "topic": topic,
        "company_id": company_id,
        "refused": False,
        "steps": steps,
        "citations": unique[:12],
        "report": "\n".join(report_parts),
        "disclaimer": _DISCLAIMER,
    }


def fundamentals_strip(company_id: str) -> Dict[str, Any]:
    if not sights_enabled():
        return _refuse_disabled("Fundamentals Strip")
    snap = research_svc.company_snapshot(company_id)
    return {
        "product": "CiteAlpha Fundamentals Strip",
        "company_id": company_id,
        "snapshot": snap,
        "note": "Reuses Desk/Research snapshot shapes (MoM/QoQ/YoY). Demo tape labeled as demo.",
        "disclaimer": _DISCLAIMER,
    }


def enterprise_links() -> Dict[str, Any]:
    from app.services.feature_flags import sso_enabled

    return {
        "product": "CiteAlpha Sights Enterprise",
        "links": {
            "trust_center": "/trust",
            "billing": "/billing",
            "package": "/products#plans",
            "desk": "/desk",
            "oidc_docs": "docs/OIDC.md",
        },
        "sso_configured_flag": sso_enabled(),
        "note": (
            "Private-cloud / VPC is an ops conversation after revenue justifies — "
            "not a marketed fake Enterprise Intelligence SKU."
        ),
        "disclaimer": _DISCLAIMER,
    }
