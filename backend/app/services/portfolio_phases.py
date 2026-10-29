"""Portfolio phases P2–P5 — Radar habit, Ledger depth, Cite/Data licensing, stretch lines.

Composes existing stores only; does not invent financial actuals.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.services import repository
from app.services.pdf_minimal import text_to_pdf
from app.services.research import promise_brief

# Credit-adjacent commitment metrics (capex, margin floors, leverage proxies)
CREDIT_ADJACENT_METRICS = frozenset(
    {
        "capex_guidance",
        "capex",
        "fcf_guidance",
        "fcf",
        "operating_margin_pct",
        "ebitda_margin_pct",
        "net_margin_pct",
        "wc_days",
        "loan_growth_pct",
        "nim_pct",
        "free_cash_flow",
        "capital_expenditure",
    }
)

CITE_TIERS: List[Dict[str, Any]] = [
    {
        "id": "desk",
        "name": "Desk interactive",
        "rpm": 120,
        "daily_citations": None,
        "note": "Included in Desk seats — soft RPM via middleware",
    },
    {
        "id": "cite_api",
        "name": "Cite API embed",
        "rpm": 600,
        "daily_citations": 5000,
        "note": "Higher limits for copilot / platform embed (P4)",
    },
    {
        "id": "enterprise",
        "name": "Enterprise redistribution",
        "rpm": 2000,
        "daily_citations": None,
        "note": "Contracted; MSA defines redistribution rights",
    },
]


def _mid(low: Optional[float], high: Optional[float], mid: Optional[float]) -> Optional[float]:
    if low is not None and high is not None:
        return (float(low) + float(high)) / 2.0
    if mid is not None:
        return float(mid)
    return None


# --- P2 Radar ---


def guidance_diff_brief(company_id: str) -> Dict[str, Any]:
    """QoQ guided band / text delta per metric thread."""
    detail = repository.get_company_gci(company_id)
    events = detail.revision_timeline or []
    diffs: List[Dict[str, Any]] = []

    by_thread: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        tid = ev.get("thread_id") or f"{ev.get('metric')}|{ev.get('period')}"
        by_thread.setdefault(str(tid), []).append(ev)

    for tid, rows in by_thread.items():
        ordered = sorted(rows, key=lambda r: (str(r.get("as_of") or ""), str(r.get("period") or "")))
        prev = None
        for cur in ordered:
            if prev is None:
                prev = cur
                continue
            prev_mid = _mid(prev.get("guided_low"), prev.get("guided_high"), prev.get("guided_value"))
            cur_mid = _mid(cur.get("guided_low"), cur.get("guided_high"), cur.get("guided_value"))
            band_delta = None
            if prev_mid is not None and cur_mid is not None:
                band_delta = round(cur_mid - prev_mid, 2)
            text_changed = (prev.get("detail") or "") != (cur.get("detail") or "")
            kind = cur.get("kind") or "changed"
            if kind in ("revised_up", "revised_down") or band_delta not in (None, 0) or text_changed:
                diffs.append(
                    {
                        "thread_id": tid if tid and "|" not in tid[:3] else None,
                        "metric": cur.get("metric"),
                        "prior_period": prev.get("period"),
                        "current_period": cur.get("period"),
                        "prior_band_mid": prev_mid,
                        "current_band_mid": cur_mid,
                        "band_delta": band_delta,
                        "kind": kind,
                        "detail": cur.get("detail"),
                        "source_url": cur.get("source_url"),
                        "severity": cur.get("severity") or "medium",
                    }
                )
            prev = cur

    diffs.sort(key=lambda d: str(d.get("current_period") or ""), reverse=True)
    return {
        "product": "CiteAlpha Radar",
        "feature": "guidance_diff_brief",
        "company_id": detail.id,
        "ticker": detail.ticker,
        "name": detail.name,
        "count": len(diffs),
        "diffs": diffs,
        "note": "Quarter-over-quarter guided band and language changes — factual, not a forecast.",
        "disclaimer": "Not investment advice.",
    }


def radar_calendar(limit: int = 30) -> Dict[str, Any]:
    """Upcoming result windows linked to open promises."""
    limit = max(1, min(int(limit), 100))
    windows: List[Dict[str, Any]] = []

    for c in repository.list_company_summaries()[: limit * 2]:
        try:
            brief = promise_brief(c.id)
        except Exception:
            continue
        open_n = int(brief.get("open_promise_count") or 0)
        if open_n <= 0:
            continue
        promises = brief.get("promises") or []
        periods = sorted({str(p.get("period") or "") for p in promises if p.get("period")})
        windows.append(
            {
                "company_id": c.id,
                "ticker": c.ticker,
                "name": c.name,
                "open_promise_count": open_n,
                "periods": periods,
                "ledger_url": f"/companies/{c.id}#evidence",
                "brief_url": f"/api/research/brief/{c.id}",
                "promises_preview": promises[:3],
            }
        )
        if len(windows) >= limit:
            break

    return {
        "product": "CiteAlpha Radar",
        "feature": "result_calendar",
        "count": len(windows),
        "windows": windows,
        "note": "Companies with open (pending) guidance — linked to Ledger / promise brief.",
        "disclaimer": "Not investment advice. Calendar windows are period labels, not exchange dates.",
    }


# --- P3 Ledger ---


def company_ledger_filtered(
    company_id: str,
    *,
    credit_only: bool = False,
    mirror: bool = False,
) -> Dict[str, Any]:
    """Ledger with optional credit filter and IR Mirror copy."""
    from app.services.portfolio import company_ledger

    base = company_ledger(company_id)
    if credit_only:
        base["closed_promises"] = [
            r
            for r in base.get("closed_promises", [])
            if str(r.get("metric") or "").lower() in CREDIT_ADJACENT_METRICS
            or any(
                tok in str(r.get("metric") or "").lower()
                for tok in ("capex", "margin", "fcf", "leverage", "debt", "loan")
            )
        ]
        base["open_promises"] = [
            r
            for r in base.get("open_promises", [])
            if str(r.get("metric") or "").lower() in CREDIT_ADJACENT_METRICS
            or any(
                tok in str(r.get("metric") or "").lower()
                for tok in ("capex", "margin", "fcf", "leverage", "debt", "loan")
            )
        ]
        base["filter"] = "credit_adjacent"
    if mirror:
        base["product"] = "CiteAlpha Ledger — IR Mirror"
        base["mode"] = "ir_mirror"
        base["mirror_note"] = (
            "Corporate IR view: how an external accountability ledger reads for your "
            "disclosure history. Factual delivery record — not a rating or recommendation."
        )
        base["peer_context"] = _ir_mirror_peer_context(company_id)
    return base


def _ir_mirror_peer_context(company_id: str) -> Dict[str, Any]:
    detail = repository.get_company_gci(company_id)
    sector_rows = [
        c
        for c in repository.list_company_summaries()
        if (c.sector or "").lower() == (detail.sector or "").lower()
    ]
    scores = [c.gci_score for c in sector_rows if c.gci_score is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else None
    rank = detail.peer_rank_in_sector
    return {
        "sector": detail.sector,
        "sector_avg_gci": avg,
        "peer_rank_in_sector": rank,
        "sector_peers_count": len(sector_rows),
    }


def ledger_pdf_bytes(company_id: str, *, credit_only: bool = False) -> bytes:
    """Board / IC pack PDF from promise ledger."""
    led = company_ledger_filtered(company_id, credit_only=credit_only)
    lines = [
        f"CiteAlpha Promise Ledger — {led.get('ticker')} ({led.get('name')})",
        f"Data quality: {led.get('data_quality')} · GCI context: {led.get('gci_score')}",
        led.get("note") or "",
        "",
        "=== Closed promises ===",
    ]
    for row in led.get("closed_promises", [])[:40]:
        lines.append(
            f"{row.get('period')} | {row.get('metric')} | {row.get('status')} | "
            f"guided {row.get('guided_low')}–{row.get('guided_high')} | actual {row.get('actual_value')} | "
            f"src {row.get('source_url') or row.get('source_ref') or '—'}"
        )
    lines.extend(["", "=== Open promises ==="])
    for row in led.get("open_promises", [])[:20]:
        lines.append(
            f"{row.get('period')} | {row.get('metric')} | pending | "
            f"guided {row.get('guided_value')} | {row.get('guided_text', '')[:80]}"
        )
    lines.extend(["", led.get("disclaimer") or "Not investment advice."])
    return text_to_pdf(lines, title=f"Promise Ledger · {led.get('ticker')}")


# --- P4 Cite / Data ---


_cite_usage: Dict[str, int] = {}


def record_cite_usage(api_key: str, *, n: int = 1) -> None:
    _cite_usage[api_key or "anonymous"] = _cite_usage.get(api_key or "anonymous", 0) + n


def cite_usage_snapshot(api_key: Optional[str] = None) -> Dict[str, Any]:
    key = api_key or "anonymous"
    used = _cite_usage.get(key, 0)
    tier = "desk"
    if used > 5000:
        tier = "enterprise"
    elif used > 500:
        tier = "cite_api"
    tier_def = next((t for t in CITE_TIERS if t["id"] == tier), CITE_TIERS[0])
    return {
        "product": "CiteAlpha Cite",
        "api_key_hint": key[:8] + "…" if len(key) > 8 else key,
        "tier": tier,
        "tier_detail": tier_def,
        "citations_served_session": used,
        "tiers": CITE_TIERS,
        "note": "In-process session metering stub — production uses contract + Redis.",
    }


def bulk_outcomes_export(
    *,
    format: str = "json",
    market: Optional[str] = None,
    limit: int = 500,
    in_scope: Optional[Callable[[str], bool]] = None,
) -> Any:
    """PIT outcomes bulk export — JSON or CSV. ``in_scope`` keeps the desk's markets only."""
    fmt = (format or "json").lower()
    limit = max(1, min(int(limit), 5000))
    rows: List[Dict[str, Any]] = []

    for c in repository.list_company_summaries():
        if in_scope is not None and not in_scope(c.id):
            continue
        try:
            detail = repository.get_company_gci(c.id)
        except Exception:
            continue
        for o in detail.outcomes:
            if o.label == "pending":
                continue
            rows.append(
                {
                    "company_id": c.id,
                    "ticker": c.ticker,
                    "sector": c.sector,
                    "data_quality": detail.data_quality,
                    "period": o.period,
                    "metric": o.metric,
                    "label": o.label,
                    "guided_low": o.guided_low,
                    "guided_high": o.guided_high,
                    "guided_value": o.guided_value,
                    "actual_value": o.actual_value,
                    "delta_pct": o.delta_pct,
                    "source_url": o.source_url,
                    "as_of": o.as_of,
                }
            )
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break

    meta = {
        "product": "CiteAlpha Data",
        "export": "outcomes_bulk",
        "format": fmt,
        "row_count": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Not investment advice. Quality flags are first-class.",
    }

    if fmt == "json":
        return {**meta, "rows": rows}

    if fmt == "csv":
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            buf.write("company_id,ticker\n")
        return {"meta": meta, "csv": buf.getvalue()}

    if fmt in ("parquet", "pq"):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            table = pa.Table.from_pylist(rows) if rows else pa.table({})
            out = io.BytesIO()
            pq.write_table(table, out)
            return {"meta": meta, "parquet_bytes": out.getvalue()}
        except ImportError:
            return {
                **meta,
                "format": "csv",
                "csv": bulk_outcomes_export(format="csv", limit=limit)["csv"],
                "parquet_fallback": "pyarrow not installed",
            }

    return {**meta, "error": "format must be json, csv, or parquet"}


def vernacular_digest(company_id: str, lang: str = "hi") -> Dict[str, Any]:
    """Factual earnings digest with source links — hi + en."""
    detail = repository.get_company_gci(company_id)
    led = company_ledger_filtered(company_id)
    open_n = len(led.get("open_promises") or [])
    closed = led.get("closed_promises") or []
    missed = sum(1 for r in closed if r.get("status") == "missed")
    met = sum(1 for r in closed if r.get("status") in ("met", "exceeded"))

    en = (
        f"{detail.name} ({detail.ticker}): GCI {detail.gci_score}. "
        f"Closed guidance rows: {len(closed)} ({met} met/exceeded, {missed} missed). "
        f"Open promises: {open_n}. Based on primary disclosure — not a forecast."
    )
    hi = (
        f"{detail.name} ({detail.ticker}): GCI {detail.gci_score}. "
        f"बंद मार्गदर्शन: {len(closed)} ({met} पूरे, {missed} चूके). "
        f"खुले वादे: {open_n}. प्राथमिक स्रोत पर आधारित — पूर्वानुमान नहीं।"
    )
    text = hi if lang == "hi" else en
    sources = [
        {"period": r.get("period"), "metric": r.get("metric"), "url": r.get("source_url")}
        for r in closed[:5]
        if r.get("source_url")
    ]
    return {
        "product": "CiteAlpha Cite",
        "feature": "vernacular_digest",
        "company_id": company_id,
        "lang": lang,
        "text": text,
        "text_en": en,
        "text_hi": hi,
        "sources": sources,
        "status": "factual_template",
        "disclaimer": "Not investment advice.",
    }


# --- P5 Stretch ---


def narrative_consistency_index(company_id: str) -> Dict[str, Any]:
    """Cross-doc consistency flags — on-wedge stub using audit flags."""
    detail = repository.get_company_gci(company_id)
    flags = list(detail.audit_flags or [])
    conflicts: List[Dict[str, Any]] = []
    for ev in detail.revision_timeline or []:
        if ev.get("kind") in ("restatement", "definition_shift", "withdrawn"):
            conflicts.append(
                {
                    "kind": ev.get("kind"),
                    "period": ev.get("period"),
                    "metric": ev.get("metric"),
                    "detail": ev.get("detail"),
                    "source_url": ev.get("source_url"),
                }
            )
    score = 100
    score -= 15 * sum(1 for f in flags if f == "guidance_withdrawal")
    score -= 15 * sum(1 for f in flags if f == "restatement")
    score -= 10 * sum(1 for f in flags if f == "definition_shift")
    score = max(0, min(100, score))
    return {
        "product": "CiteAlpha Score",
        "feature": "narrative_consistency_index",
        "company_id": company_id,
        "ticker": detail.ticker,
        "nci_score": score,
        "audit_flags": flags,
        "conflicts": conflicts[:20],
        "status": "beta",
        "gate": "Requires hand_labeled cross-doc store for production claims",
        "disclaimer": "Not investment advice. Not a forensic accounting score.",
    }


def kpi_dictionary(sector: Optional[str] = None) -> Dict[str, Any]:
    """India sector metric ontology from catalog."""
    from app.data.metric_catalog import list_metrics

    metrics = list_metrics(sector)
    families: Dict[str, List[str]] = {}
    for m in metrics:
        fam = m.get("family") or "other"
        families.setdefault(fam, []).append(m["id"])
    return {
        "product": "CiteAlpha Data",
        "feature": "kpi_dictionary",
        "sector_filter": sector,
        "metric_count": len(metrics),
        "families": families,
        "metrics": metrics,
        "note": "Normalization layer for India disclosure variants — infrastructure SKU.",
    }


def extraction_workbench_status() -> Dict[str, Any]:
    """Ops workbench stub — pending extract + review queue depth."""
    from app.services.throughput import desk_throughput

    tp = desk_throughput()
    backlog = tp.get("backlog") or {}
    pending = backlog.get("pending_extract_batches") or 0
    return {
        "product": "Extraction Workbench",
        "status": "internal_preview",
        "throughput": tp,
        "pending_extract_batches": pending,
        "gate": "Sell when labeling ops stable 90 days",
        "note": "SaaS packaging for captive research factories — not GA.",
    }


def trust_badge_channel(ticker: str) -> Dict[str, Any]:
    """Broker GCI badge channel metadata (wraps badge endpoint)."""
    row = repository.resolve_ticker_summary(ticker)
    if row is None:
        return {"status": "not_found", "ticker": ticker}
    return {
        "product": "GCI badge",
        "channel": "white_label",
        "ticker": row["ticker"],
        "company_id": row["id"],
        "gci_score": row["gci_score"],
        "embed_path": f"/api/badge/{row['ticker']}",
        "svg_path": f"/api/badge/{row['ticker']}/svg",
        "gate": "SEBI-reviewed badge copy + partner MSA before retail embed",
        "disclaimer": "Not investment advice. Factual guidance-delivery metric.",
    }
