from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.services.guidance_flags import audited_company_gci, score_meta
from app.data.seed import get_data, get_outcomes, list_companies, outcome_from_dict, save_data
from app.models.schemas import (
    AlertItem,
    CompanyGCIDetail,
    CompanySummary,
    GuidanceRevision,
    OutcomeView,
    PitPoint,
)
from app.services.changes import (
    change_bundle,
    enrich_metric_rows,
    enrich_value_series,
    sort_document_listing,
    sort_evidence_listing,
)
from app.services.citations import enrich_outcome_citation
from app.services.coverage import coverage_reason, coverage_status_for
from app.services.score_policy import NOT_SCORED_STATUS, is_scoreable, publishable_score
from app.services.gci_scoring import (
    classify_outcome,
    compute_company_gci,
    delta_pct,
    final_band,
    final_band_label,
    revision_direction,
    gci_trend_series,
    label_counts,
    metric_breakdown,
    outcome_score,
)


def _to_view(
    o,
    *,
    company_id: str = "",
    data_quality: str = "demo_structured",
    outcome_index: Optional[int] = None,
    actual_change_pct=None,
    actual_change_horizon=None,
    guided_change_pct=None,
    guided_change_horizon=None,
) -> OutcomeView:
    from app.data import doc_store

    score = outcome_score(o) if is_scoreable(data_quality) else None
    cite = enrich_outcome_citation(o, company_id=company_id, data_quality=data_quality)
    doc = doc_store.document_meta(cite["doc_id"]) or {}
    final = final_band(o)
    final_lbl = final_band_label(o) if o.actual_value is not None else None
    return OutcomeView(
        period=o.period,
        metric=o.metric,
        outcome_index=outcome_index,
        guided_value=o.guided_value,
        guided_low=o.guided_low,
        guided_high=o.guided_high,
        actual_value=o.actual_value,
        delta_pct=delta_pct(o.guided_value, o.actual_value),
        guided_text=o.guided_text,
        confidence=o.confidence,
        speaker=o.speaker,
        contribution_score=None if score is None else round(score, 1),
        label=classify_outcome(o).value,
        thread_id=o.thread_id,
        source_url=o.source_url,
        source_ref=o.source_ref,
        quote_span=cite["quote_span"],
        as_of=o.as_of,
        guidance_source_url=o.guidance_source_url,
        guidance_source_ref=o.guidance_source_ref,
        guidance_quote=o.guidance_quote,
        guidance_as_of=o.guidance_as_of,
        revisions=[GuidanceRevision(**r) for r in o.revisions],
        revision_direction=revision_direction(o),
        final_guided_low=final[0] if final else None,
        final_guided_high=final[1] if final else None,
        final_label=final_lbl.value if final_lbl else None,
        dropped=o.dropped,
        actual_change_pct=actual_change_pct,
        actual_change_horizon=actual_change_horizon,
        guided_change_pct=guided_change_pct,
        guided_change_horizon=guided_change_horizon,
        citation_id=cite["citation_id"],
        doc_id=cite["doc_id"],
        citeable=cite["citeable"],
        cite_reason=cite["cite_reason"],
        span_start=cite.get("span_start"),
        span_end=cite.get("span_end"),
        reviewed_by=o.reviewed_by,
        reviewed_at=o.reviewed_at,
        reporting_basis=o.reporting_basis,
        actual_reporting_basis=o.actual_reporting_basis,
        unit=o.unit,
        actual_unit=o.actual_unit,
        scope=o.scope,
        actual_scope=o.actual_scope,
        evidence_hashes={
            "guidance_quote_sha256": _sha256(o.guidance_quote),
            "quote_sha256": _sha256(cite["quote_span"]),
            "doc_sha256": doc.get("content_hash"),
            "doc_ingested_at": doc.get("ingested_at"),
        },
    )


def _sha256(text: Optional[str]) -> Optional[str]:
    """Same convention as Analyst citations: SHA-256 of the exact quote, UTF-8."""
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _outcome_change_map(outcomes) -> Dict[Tuple[str, str], Dict[str, Any]]:
    rows = [
        {
            "period": o.period,
            "metric": o.metric,
            "actual": o.actual_value,
            "management_guidance": o.guided_value,
        }
        for o in outcomes
    ]
    enriched = enrich_metric_rows(
        rows, value_keys=("actual", "management_guidance")
    )
    return {
        (r["period"], r["metric"]): r
        for r in enriched
    }


def _latest_trend_change(trend: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str]]:
    if not trend:
        return None, None
    last = trend[-1]
    return last.get("change_pct"), last.get("change_horizon")


def _by_metric_changes(outcomes) -> Dict[str, Dict[str, Any]]:
    by_m: Dict[str, List] = {}
    for o in outcomes:
        by_m.setdefault(o.metric, []).append(o)
    out: Dict[str, Dict[str, Any]] = {}
    for metric, rows in by_m.items():
        series = [(o.period, o.actual_value) for o in rows if o.actual_value is not None]
        # unique by period keep last
        seen = {}
        for p, v in series:
            seen[p] = v
        hist = list(seen.items())
        if not hist:
            continue
        out[metric] = change_bundle(hist[-1][1], hist)
    return out


def _detail_status(score: Optional[float], data_quality: Optional[str]) -> str:
    if not is_scoreable(data_quality):
        return NOT_SCORED_STATUS
    return "ok" if score is not None else "insufficient_data"


def _sector_stats() -> Dict[str, Tuple[Optional[float], Dict[str, Optional[float]]]]:
    """sector -> (avg, {company_id: score}) for seed companies only."""
    by_sector: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for c in list_companies():
        score = publishable_score(
            audited_company_gci(get_outcomes(c["id"]), company_id=c["id"]),
            c.get("data_quality"),
        )
        by_sector[c["sector"]][c["id"]] = score
    out: Dict[str, Tuple[Optional[float], Dict[str, Optional[float]]]] = {}
    for sector, mapping in by_sector.items():
        vals = [v for v in mapping.values() if v is not None]
        avg = round(sum(vals) / len(vals), 1) if vals else None
        out[sector] = (avg, mapping)
    return out


def _listing_sector_maps(
    scores: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Optional[float]], Dict[str, int], Dict[str, int]]:
    """Precompute sector avg + rank + count once (O(n log n)), not per row."""
    by_sector: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for sid, srow in scores.items():
        sc = srow.get("gci_score")
        if sc is None:
            continue
        by_sector[srow.get("sector") or "Equity"].append((sid, float(sc)))
    avg_map: Dict[str, Optional[float]] = {}
    rank_map: Dict[str, int] = {}
    count_map: Dict[str, int] = {}
    for sector, peers in by_sector.items():
        peers.sort(key=lambda x: -x[1])
        vals = [v for _, v in peers]
        avg_map[sector] = round(sum(vals) / len(vals), 1) if vals else None
        count_map[sector] = len(peers)
        for i, (cid, _) in enumerate(peers):
            rank_map[cid] = i + 1
    return avg_map, rank_map, count_map


def count_companies(
    market: Optional[str] = None, index: Optional[str] = None
) -> int:
    """Fast count — membership only, no GCI scoring."""
    from app.data import markets as markets_data

    mid = market.upper() if market else None
    iid = index.upper() if index else None
    if not mid and not iid:
        return len(list_companies())
    if iid:
        return markets_data.constituent_count(iid)
    return len(markets_data.list_stocks(market_id=mid, index_id=None))


def list_published_companies() -> List[CompanySummary]:
    """Companies that carry a published GCI. The reading room searches this list."""
    from app.data.gci_score_cache import load_cache
    from app.data.india_listings import find_listing
    from app.data.us_listings import find_world_listing

    seed = {c["id"]: c for c in list_companies()}
    rows: List[CompanySummary] = []
    for cid, cached in (load_cache().get("scores") or {}).items():
        if not isinstance(cached, dict) or cached.get("gci_score") is None:
            continue
        seeded = seed.get(cid) or {}
        listing = find_listing(cid) or find_world_listing(cid) or {}
        ticker = seeded.get("ticker") or listing.get("ticker") or cached.get("ticker") or cid
        rows.append(
            CompanySummary(
                id=cid,
                name=seeded.get("name") or listing.get("name") or str(ticker),
                ticker=str(ticker),
                sector=seeded.get("sector") or listing.get("sector") or cached.get("sector") or "Equity",
                gci_score=cached.get("gci_score"),
                data_quality=cached.get("data_quality") or seeded.get("data_quality") or "hand_labeled",
                confidence_tier=cached.get("confidence_tier"),
                closed_periods=int(cached.get("closed_periods") or 0),
                metrics_scored=int(cached.get("metrics_scored") or 0),
                as_of=cached.get("as_of"),
                algorithm_id=cached.get("algorithm_id"),
                coverage_status=cached.get("coverage_status"),
                market_id=(listing.get("market_id") or seeded.get("market_id") or "IN"),
                index_ids=listing.get("index_ids"),
                exchange=listing.get("exchange"),
            )
        )
    rows.sort(key=lambda row: (-(row.gci_score or 0), row.ticker))
    return rows


def list_company_summaries(
    market: Optional[str] = None,
    index: Optional[str] = None,
    *,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[CompanySummary]:
    """List GCI universe, optionally filtered to a market/index.

    Large indexes (NSE_ALL / BSE_ALL) use the score cache + O(1) peer maps.
    Never rebuild the full India cache on a request path.
    """
    from app.data import markets as markets_data
    from app.data.gci_score_cache import load_cache

    mid = market.upper() if market else None
    iid = index.upper() if index else None

    # Default product path — existing Sensex GCI seed
    if not mid and not iid:
        from app.data.gci_score_cache import load_cache
        from app.data.india_listings import find_listing
        from app.data.us_listings import find_world_listing

        cache_scores = load_cache().get("scores") or {}
        stats = _sector_stats()
        rows: List[CompanySummary] = []
        for c in list_companies():
            outcomes = get_outcomes(c["id"])
            scoreable = is_scoreable(c.get("data_quality"))
            meta = score_meta(
                outcomes,
                scoreable=scoreable,
                company_id=c["id"],
                data_quality=c.get("data_quality"),
            )
            score = meta["gci_score"]
            trend = gci_trend_series(outcomes) if scoreable else []
            ch_pct, ch_h = _latest_trend_change(trend)
            avg, mapping = stats[c["sector"]]
            ranked = sorted(
                [(cid, s) for cid, s in mapping.items() if s is not None],
                key=lambda x: x[1],
                reverse=True,
            )
            rank = next((i + 1 for i, (cid, _) in enumerate(ranked) if cid == c["id"]), None)
            cached = cache_scores.get(c["id"]) or {}
            hz = {
                "wow_pct": cached.get("wow_pct"),
                "mom_pct": cached.get("mom_pct"),
                "qoq_pct": cached.get("qoq_pct"),
                "yoy_pct": cached.get("yoy_pct"),
            }
            if all(v is None for v in hz.values()) and score is not None:
                try:
                    b = gci_change_bundle_for(c["id"])
                    hz = {
                        "wow_pct": b.get("wow_pct"),
                        "mom_pct": b.get("mom_pct"),
                        "qoq_pct": b.get("qoq_pct"),
                        "yoy_pct": b.get("yoy_pct"),
                    }
                except Exception:
                    pass
            rows.append(
                CompanySummary(
                    id=c["id"],
                    name=c["name"],
                    ticker=c["ticker"],
                    sector=c["sector"],
                    gci_score=score,
                    data_quality=c.get("data_quality", "demo_structured"),
                    peer_rank_in_sector=rank,
                    sector_avg_gci=avg,
                    gci_change_pct=ch_pct,
                    gci_change_horizon=ch_h,
                    market_id=c.get("market_id") or "IN",
                    index_ids=(find_listing(c["id"]) or find_world_listing(c["id"]) or {}).get("index_ids"),
                    exchange=(find_listing(c["id"]) or find_world_listing(c["id"]) or {}).get("exchange"),
                    confidence_tier=meta["confidence_tier"],
                    closed_periods=meta["closed_periods"],
                    metrics_scored=meta["metrics_scored"],
                    as_of=meta["as_of"],
                    algorithm_id=meta["algorithm_id"],
                    coverage_status=coverage_status_for(
                        c["id"], score=score, outcomes=outcomes, data_quality=c.get("data_quality")
                    ),
                    **hz,
                )
            )
        rows.sort(key=lambda r: (r.gci_score is None, -(r.gci_score or 0)))
        if offset:
            rows = rows[offset:]
        if limit is not None and limit > 0:
            rows = rows[:limit]
        return _with_reasons(rows)

    stock_rows = (
        markets_data.constituents_readonly(iid)
        if iid
        else markets_data.list_stocks(market_id=mid, index_id=None)
    )
    seed_by_id = {c["id"]: c for c in list_companies()}
    cache_scores = load_cache().get("scores") or {}
    avg_map, rank_map, _ = _listing_sector_maps(cache_scores)
    large = len(stock_rows) > 200
    seed_stats = None if large else _sector_stats()

    def _score_key(s: Dict[str, Any]) -> Tuple:
        cached = cache_scores.get(s["id"]) or {}
        sc = cached.get("gci_score")
        return (sc is None, -(sc or 0), s.get("ticker") or "")

    # Sort membership first, then materialize only the requested page for large indexes
    ordered = sorted(stock_rows, key=_score_key)
    if offset:
        ordered = ordered[offset:]
    page = ordered[:limit] if (limit is not None and limit > 0) else ordered

    rows = []
    for s in page:
        cid = s["id"]
        seeded = seed_by_id.get(cid)
        cached = cache_scores.get(cid)
        if seeded is not None and (
            not cached or seeded.get("data_quality") in ("hand_labeled", "demo_structured")
        ):
            # Prefer live seed outcomes for deep GCI names on small pages
            if seeded.get("data_quality") == "hand_labeled" or not large:
                outcomes = get_outcomes(seeded["id"])
                scoreable = is_scoreable(seeded.get("data_quality"))
                meta = score_meta(
                    outcomes,
                    scoreable=scoreable,
                    company_id=seeded["id"],
                    data_quality=seeded.get("data_quality"),
                )
                score = meta["gci_score"]
                trend = gci_trend_series(outcomes) if scoreable else []
                ch_pct, ch_h = _latest_trend_change(trend)
                sector = seeded["sector"]
                if seed_stats:
                    avg, mapping = seed_stats.get(sector, (None, {}))
                    ranked = sorted(
                        [(i, sc) for i, sc in mapping.items() if sc is not None],
                        key=lambda x: x[1],
                        reverse=True,
                    )
                    rank = next((i + 1 for i, (x, _) in enumerate(ranked) if x == cid), None)
                else:
                    avg = avg_map.get(sector)
                    rank = rank_map.get(cid)
                rows.append(
                    CompanySummary(
                        id=seeded["id"],
                        name=seeded["name"],
                        ticker=seeded["ticker"],
                        sector=sector,
                        gci_score=score,
                        data_quality=seeded.get("data_quality", "demo_structured"),
                        peer_rank_in_sector=rank,
                        sector_avg_gci=avg,
                        gci_change_pct=ch_pct,
                        gci_change_horizon=ch_h,
                        wow_pct=(cached or {}).get("wow_pct"),
                        mom_pct=(cached or {}).get("mom_pct"),
                        qoq_pct=(cached or {}).get("qoq_pct"),
                        yoy_pct=(cached or {}).get("yoy_pct"),
                        market_id=s.get("market_id", "IN"),
                        index_ids=s.get("index_ids"),
                        exchange=s.get("exchange"),
                        confidence_tier=meta["confidence_tier"],
                        closed_periods=meta["closed_periods"],
                        metrics_scored=meta["metrics_scored"],
                        as_of=meta["as_of"],
                        algorithm_id=meta["algorithm_id"],
                        coverage_status=coverage_status_for(
                            seeded["id"],
                            score=score,
                            outcomes=outcomes,
                            data_quality=seeded.get("data_quality"),
                        ),
                    )
                )
                continue
        score = cached.get("gci_score") if cached else None
        quality = (cached or {}).get("data_quality") or s.get("data_quality") or "listing_master"
        sector = s.get("sector") or (cached or {}).get("sector") or "Equity"
        if seeded and not cached:
            quality = seeded.get("data_quality", quality)
            sector = seeded.get("sector", sector)
        rows.append(
            CompanySummary(
                id=cid,
                name=s.get("name") or (seeded or {}).get("name") or cid,
                ticker=s.get("ticker") or (seeded or {}).get("ticker") or cid,
                sector=sector,
                gci_score=score,
                data_quality=quality,
                peer_rank_in_sector=rank_map.get(cid),
                sector_avg_gci=avg_map.get(sector),
                gci_change_pct=(cached or {}).get("gci_change_pct"),
                gci_change_horizon=(cached or {}).get("gci_change_horizon"),
                wow_pct=(cached or {}).get("wow_pct"),
                mom_pct=(cached or {}).get("mom_pct"),
                qoq_pct=(cached or {}).get("qoq_pct"),
                yoy_pct=(cached or {}).get("yoy_pct"),
                market_id=s.get("market_id"),
                index_ids=s.get("index_ids"),
                exchange=s.get("exchange"),
                confidence_tier=(cached or {}).get("confidence_tier"),
                closed_periods=int((cached or {}).get("closed_periods") or 0),
                metrics_scored=int((cached or {}).get("metrics_scored") or 0),
                as_of=(cached or {}).get("as_of"),
                algorithm_id=(cached or {}).get("algorithm_id"),
                coverage_status=(cached or {}).get("coverage_status")
                or coverage_status_for(cid, score=score, data_quality=quality),
            )
        )
    return _with_reasons(rows)


def _with_reasons(rows: List[CompanySummary]) -> List[CompanySummary]:
    for r in rows:
        if r.gci_score is None:
            r.coverage_reason = coverage_reason(r.id, r.coverage_status)
    return rows


def get_company_gci(company_id: str) -> CompanyGCIDetail:
    company = next((c for c in list_companies() if c["id"] == company_id), None)
    if company is None:
        from app.data.india_listings import find_listing
        from app.services.provisional_gci import QUALITY

        from app.data.us_listings import find_world_listing

        listing = find_listing(company_id) or find_world_listing(company_id)
        if listing is None:
            raise HTTPException(status_code=404, detail="Company not found")

        audit = _audit_payload([], company_id=listing["id"], ticker=listing["ticker"])
        status = coverage_status_for(listing["id"], score=None, data_quality=QUALITY)
        return CompanyGCIDetail(
            id=listing["id"],
            name=listing["name"],
            ticker=listing["ticker"],
            sector=listing.get("sector") or "Equity",
            gci_score=None,
            status=NOT_SCORED_STATUS,
            data_quality=QUALITY,
            by_metric={},
            label_counts={},
            outcomes=[],
            trend=[],
            peer_rank_in_sector=None,
            sector_avg_gci=None,
            threads={},
            gci_change_pct=None,
            gci_change_horizon=None,
            by_metric_changes={},
            algorithm_id=score_meta([], scoreable=False)["algorithm_id"],
            coverage_status=status,
            coverage_reason=coverage_reason(listing["id"], status),
            **audit,
        )

    quality = company.get("data_quality", "demo_structured")
    if quality == "hand_labeled":
        from app.data import doc_store
        from app.data.seed import get_data as _gd
        from app.services.citation_corpus import ensure_company_citation_corpus

        raw = (_gd().get("outcomes") or {}).get(company_id) or []
        missing_bind = any(
            (r.get("source_url") and r.get("quote_span") and not r.get("doc_id")) for r in raw
        )
        accepted = [
            d
            for d in doc_store.list_documents(company_id=company_id, include_rejected=True)
            if d.get("review_status") == "accepted"
        ]
        if missing_bind or not accepted:
            ensure_company_citation_corpus(company_id)
    outcomes = get_outcomes(company_id)
    scoreable = is_scoreable(quality)
    smeta = score_meta(
        outcomes, scoreable=scoreable, company_id=company_id, data_quality=quality
    )
    score = smeta["gci_score"]
    chmap = _outcome_change_map(outcomes)
    views = []
    for index, o in enumerate(outcomes):
        meta = chmap.get((o.period, o.metric), {})
        views.append(
            _to_view(
                o,
                company_id=company_id,
                data_quality=quality,
                outcome_index=index,
                actual_change_pct=meta.get("actual_change_pct"),
                actual_change_horizon=meta.get("actual_change_horizon"),
                guided_change_pct=meta.get("management_guidance_change_pct"),
                guided_change_horizon=meta.get("management_guidance_change_horizon"),
            )
        )
    views = sort_evidence_listing(views)
    threads: Dict[str, List[OutcomeView]] = defaultdict(list)
    for v in views:
        if v.thread_id:
            threads[v.thread_id].append(v)

    stats = _sector_stats()
    avg, mapping = stats.get(company["sector"], (None, {}))
    ranked = sorted(
        [(cid, s) for cid, s in mapping.items() if s is not None],
        key=lambda x: x[1],
        reverse=True,
    )
    rank = next((i + 1 for i, (cid, _) in enumerate(ranked) if cid == company_id), None)
    trend = gci_trend_series(outcomes) if scoreable else []
    ch_pct, ch_h = _latest_trend_change(trend)
    audit = _audit_payload(outcomes, company_id=company_id, ticker=company["ticker"])
    status = coverage_status_for(company_id, score=score, outcomes=outcomes, data_quality=quality)

    return CompanyGCIDetail(
        id=company["id"],
        name=company["name"],
        ticker=company["ticker"],
        sector=company["sector"],
        gci_score=score,
        status=_detail_status(score, quality),
        data_quality=company.get("data_quality", "demo_structured"),
        by_metric=smeta["by_metric"],
        context_metrics=smeta["context_metrics"],
        periods_by_metric=smeta["periods_by_metric"],
        composite_weights=smeta["composite_weights"],
        label_counts=label_counts(outcomes),
        outcomes=views,
        trend=trend,
        peer_rank_in_sector=rank,
        sector_avg_gci=avg,
        threads=dict(threads),
        gci_change_pct=ch_pct,
        gci_change_horizon=ch_h,
        by_metric_changes=_by_metric_changes(outcomes),
        confidence_tier=smeta["confidence_tier"],
        closed_periods=smeta["closed_periods"],
        metrics_scored=smeta["metrics_scored"],
        as_of=smeta["as_of"],
        reviewed_at=smeta.get("reviewed_at"),
        algorithm_id=smeta["algorithm_id"],
        coverage_status=status,
        coverage_reason=coverage_reason(company_id, status, outcomes=outcomes),
        **audit,
    )


def pit_history(company_id: str) -> List[PitPoint]:
    company = next((c for c in list_companies() if c["id"] == company_id), None)
    if company is None:
        from app.data.india_listings import find_listing

        if find_listing(company_id) is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return []
    if not is_scoreable(company.get("data_quality")):
        return []
    outcomes = get_outcomes(company_id)
    if not outcomes:
        return []
    # Prefer explicit as_of; else use period labels as chronological proxy (still citeable outcomes).
    dates = sorted({o.as_of for o in outcomes if o.as_of})
    if len(dates) < 2:
        periods = sorted({o.period for o in outcomes if o.period})
        raw = []
        for i, period in enumerate(periods):
            subset = [o for o in outcomes if o.period in periods[: i + 1]]
            score = audited_company_gci(subset, company_id=company_id)
            if score is None:
                continue
            raw.append({"as_of": period, "gci_score": score})
    else:
        raw = []
        for d in dates:
            subset = [o for o in outcomes if o.as_of and o.as_of <= d]
            raw.append(
                {
                    "as_of": d,
                    "gci_score": audited_company_gci(subset, company_id=company_id),
                }
            )
    enriched = enrich_value_series(raw, period_key="as_of", value_key="gci_score")
    return [
        PitPoint(
            as_of=r["as_of"],
            gci_score=r.get("gci_score"),
            prior_gci=r.get("prior_value"),
            change_pct=r.get("change_pct"),
            change_horizon=r.get("change_horizon"),
        )
        for r in enriched
    ]


def _audit_payload(
    outcomes: List[Any],
    *,
    company_id: str,
    ticker: str,
) -> Dict[str, Any]:
    from app.services.guidance_flags import (
        audit_summary,
        company_red_alerts,
        revision_summaries,
        revision_timeline,
    )
    from app.services.guidance_profile import guidance_profile

    summary = audit_summary(outcomes, company_id=company_id)
    return {
        "audit_flags": summary["flags"],
        "audit_deduction": summary["deduction"],
        "audit_badges": summary["badges"],
        "audit_note": summary["note"],
        "red_alerts": company_red_alerts(outcomes, company_id=company_id, ticker=ticker),
        "revision_timeline": revision_timeline(
            outcomes, company_id=company_id, ticker=ticker
        ),
        "revision_summaries": revision_summaries(outcomes),
        "guidance_profile": guidance_profile(outcomes),
    }


def _short_name(company: Dict[str, Any]) -> str:
    name = str(company.get("name") or company.get("ticker") or "")
    for suffix in (" Ltd.", " Ltd", " Limited"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def list_alerts() -> List[AlertItem]:
    from app.services.guidance_profile import guided_text, human_date, metric_phrase, value_text
    from app.services.guidance_flags import collect_audit_flags, AUDIT_LABELS, AUDIT_SEVERITY
    from app.services.gci_scoring import AUDIT_PENALTY_PTS

    alerts: List[AlertItem] = []

    # Pending IR / transcript docs awaiting analyst review (crawl + ingest)
    try:
        from app.data import doc_store

        pending_by: Dict[str, int] = {}
        for d in doc_store.list_documents(include_rejected=False):
            if d.get("review_status") == "pending":
                pending_by[d["company_id"]] = pending_by.get(d["company_id"], 0) + 1
        cos = {c["id"]: c for c in list_companies()}
        for cid, n in sorted(pending_by.items(), key=lambda x: -x[1]):
            c = cos.get(cid)
            if not c:
                continue
            alerts.append(
                AlertItem(
                    company_id=cid,
                    ticker=c["ticker"],
                    kind="docs_pending_review",
                    message=(
                        f"{_short_name(c)}: {n} {'filing' if n == 1 else 'filings'} "
                        f"awaiting review in the Analyst Workbench."
                    ),
                    severity="medium",
                )
            )
    except Exception:
        pass

    for c in list_companies():
        outs = get_outcomes(c["id"])

        # Audit flags → red rail (withdrawal / restatement / definition shift)
        for flag in collect_audit_flags(outs, company_id=c["id"]):
            pts = AUDIT_PENALTY_PTS.get(flag, 0.0)
            alerts.append(
                AlertItem(
                    company_id=c["id"],
                    ticker=c["ticker"],
                    kind=flag,
                    message=(
                        f"{_short_name(c)}: {AUDIT_LABELS.get(flag, flag)}, "
                        f"{pts:.0f} points deducted from the GCI."
                    ),
                    severity=AUDIT_SEVERITY.get(flag, "medium"),
                    audit_flag=flag,
                    deduction_pts=pts,
                )
            )

        # Credibility drift — ≥2 down moves in the trailing trend window
        trend = gci_trend_series(outs)
        recent_ch = [
            float(p["change_pct"])
            for p in trend[-5:]
            if p.get("change_pct") is not None
        ]
        down_moves = sum(1 for ch in recent_ch if ch < -0.5)
        # Also count consecutive negatives from the end (zeros don't break the streak)
        drops = 0
        for ch in reversed(recent_ch):
            if ch < -0.5:
                drops += 1
            elif abs(ch) < 0.05:
                continue
            else:
                break
        if down_moves >= 2 or drops >= 2:
            n = max(down_moves, drops)
            alerts.append(
                AlertItem(
                    company_id=c["id"],
                    ticker=c["ticker"],
                    kind="credibility_drift",
                    message=(
                        f"{_short_name(c)}: GCI fell in {n} of the last {len(recent_ch)} reporting periods."
                    ),
                    severity="high" if n >= 3 else "medium",
                )
            )

        # Quietly shelved promise — a pending thread with no restatement since
        # the company's most recent disclosure date (distinct from dropped label)
        dated = [o for o in outs if o.as_of]
        if dated:
            latest_as_of = max(o.as_of for o in dated)
            by_thread: Dict[str, List[Any]] = {}
            for o in dated:
                if o.thread_id:
                    by_thread.setdefault(o.thread_id, []).append(o)
            for rows in by_thread.values():
                last = max(rows, key=lambda r: r.as_of)
                if last.as_of < latest_as_of and classify_outcome(last).value == "pending":
                    alerts.append(
                        AlertItem(
                            company_id=c["id"],
                            ticker=c["ticker"],
                            kind="thread_stale",
                            message=(
                                f"{_short_name(c)} has not reiterated its {last.period} "
                                f"{metric_phrase(last.metric)} guidance since {human_date(last.as_of)}."
                            ),
                            severity="medium",
                            period=last.period,
                            metric=last.metric,
                            source_url=last.source_url,
                        )
                    )

        for o in outs:
            label = classify_outcome(o).value
            if label == "missed":
                alerts.append(
                    AlertItem(
                        company_id=c["id"],
                        ticker=c["ticker"],
                        kind="large_miss",
                        message=(
                            f"{_short_name(c)} missed its {o.period} {metric_phrase(o.metric)} guidance "
                            f"(guided {guided_text(o)}, reported {value_text(o.metric, o.actual_value)})."
                        ),
                        severity="high",
                        period=o.period,
                        metric=o.metric,
                        source_url=o.source_url,
                    )
                )
            if label == "dropped":
                alerts.append(
                    AlertItem(
                        company_id=c["id"],
                        ticker=c["ticker"],
                        kind="guidance_dropped",
                        message=(
                            f"{_short_name(c)} stopped reiterating its {o.period} "
                            f"{metric_phrase(o.metric)} guidance."
                        ),
                        severity="high",
                        period=o.period,
                        metric=o.metric,
                        source_url=o.source_url,
                    )
                )
            if o.thread_id:
                thread = [x for x in outs if x.thread_id == o.thread_id]
                if len(thread) >= 2:
                    ordered = sorted(thread, key=lambda x: (x.as_of or "", x.period))
                    vals = []
                    for x in ordered:
                        if x.guided_low is not None and x.guided_high is not None:
                            vals.append((x.guided_low + x.guided_high) / 2.0)
                        else:
                            vals.append(float(x.guided_value))
                    prev_m, cur_m = vals[0], vals[-1]
                    if abs(cur_m - prev_m) >= 2:
                        direction = "raised" if cur_m > prev_m else "lowered"
                        alerts.append(
                            AlertItem(
                                company_id=c["id"],
                                ticker=c["ticker"],
                                kind="guidance_revised",
                                message=(
                                    f"{_short_name(c)} {direction} its {metric_phrase(o.metric)} guidance "
                                    f"from {value_text(o.metric, prev_m)} to {value_text(o.metric, cur_m)}."
                                ),
                                severity="medium",
                                period=o.period,
                                metric=o.metric,
                                source_url=o.source_url,
                            )
                        )
                        break
    # de-dupe messages; prefer high severity first
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_rank.get(a.severity, 9), a.ticker, a.kind))
    seen = set()
    unique: List[AlertItem] = []
    for a in alerts:
        key = (a.company_id, a.kind, a.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
    return unique[:120]


def apply_review(
    company_id: str,
    outcome_index: int,
    action: str,
    comment: Optional[str],
    edits: Optional[Dict[str, Any]],
    reviewer: str,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    data = get_data()
    rows = data["outcomes"].get(company_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if outcome_index < 0 or outcome_index >= len(rows):
        raise HTTPException(status_code=400, detail="Invalid outcome_index")

    action = action.lower().strip()
    if action not in {"accept", "edit", "reject"}:
        raise HTTPException(status_code=400, detail="action must be accept|edit|reject")

    if action == "edit" and edits:
        allowed = set(rows[outcome_index].keys()) | {
            "source_url",
            "source_ref",
            "quote_span",
            "doc_id",
            "span_start",
            "span_end",
            "guided_text",
            "period",
            "metric",
            "guided_low",
            "guided_high",
            "guided_value",
            "actual_value",
            "confidence",
        }
        for k, v in edits.items():
            if k in allowed:
                rows[outcome_index][k] = v
    if action == "reject":
        rows[outcome_index]["dropped"] = True
        rows[outcome_index]["actual_value"] = None

    review = {
        "company_id": company_id,
        "outcome_index": outcome_index,
        "action": action,
        "comment": comment,
        "edits": edits or {},
        "reviewer": reviewer,
        "org_id": org_id or reviewer,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    data.setdefault("reviews", []).append(review)
    rows[outcome_index]["review_status"] = action
    save_data()
    return {"ok": True, "review": review, "outcome": rows[outcome_index]}


def append_outcomes(company_id: str, statements: List[Dict[str, Any]]) -> int:
    data = get_data()
    if company_id not in {c["id"] for c in data["companies"]}:
        raise HTTPException(status_code=404, detail="Company not found")
    data["outcomes"].setdefault(company_id, []).extend(statements)
    save_data()
    return len(statements)


def merge_matched(company_id: str, matched: List[Dict[str, Any]]) -> int:
    """Replace/append matched rows for company."""
    data = get_data()
    if company_id not in {c["id"] for c in data["companies"]}:
        raise HTTPException(status_code=404, detail="Company not found")
    cleaned = []
    for m in matched:
        row = dict(m)
        row.pop("company_id", None)
        row.pop("match_status", None)
        row.pop("review_status", None)
        cleaned.append(row)
    data["outcomes"][company_id] = data["outcomes"].get(company_id, []) + cleaned
    save_data()
    try:
        from app.services.labeling_queue import enqueue_flag_suggestions

        enqueue_flag_suggestions(company_id)
    except Exception:
        pass
    return len(cleaned)


def save_pending_extract(
    company_id: str, statements: List[Dict[str, Any]], *, sample: bool = False
) -> Dict[str, Any]:
    from uuid import uuid4

    data = get_data()
    batch = {
        "id": str(uuid4()),
        "company_id": company_id,
        "statements": statements,
        "status": "pending",
        "sample": sample,
    }
    data.setdefault("pending_extracts", []).append(batch)
    save_data()
    return batch


def list_pending_extracts(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = get_data().get("pending_extracts", [])
    if company_id:
        rows = [r for r in rows if r["company_id"] == company_id]
    return rows


def commit_pending_extract(
    extract_id: str,
    accepted_indices: List[int],
    edits: Optional[Dict[int, Dict[str, Any]]] = None,
    reviewer: str = "queue",
) -> Dict[str, Any]:
    """Phase 3.4 — only accepted statements enter GCI outcomes.

    ``edits`` carries per-statement analyst corrections (band, period, metric…)
    applied before commit; each accepted statement is recorded in the reviews
    corpus so the correction history compounds.
    """
    data = get_data()
    batches = data.setdefault("pending_extracts", [])
    batch = next((b for b in batches if b["id"] == extract_id), None)
    if batch is None:
        raise HTTPException(status_code=404, detail="Extract batch not found")
    edits = edits or {}
    accepted = []
    reviews = data.setdefault("reviews", [])
    company_id = batch["company_id"]
    now = datetime.now(timezone.utc).isoformat()
    edited_count = 0
    for i in accepted_indices:
        if 0 <= i < len(batch["statements"]):
            row = dict(batch["statements"][i])
            row_edits = edits.get(i) or {}
            for k, v in row_edits.items():
                if k in row:
                    row[k] = v
            action = "edit" if row_edits else "accept"
            if row_edits:
                edited_count += 1
            row["needs_review"] = False
            row["review_status"] = "accepted" if action == "accept" else "edited"
            # strip flags that aren't part of scoring outcome
            row.pop("extract_engine", None)
            accepted.append(row)
            reviews.append(
                {
                    "company_id": company_id,
                    "extract_id": extract_id,
                    "statement_index": i,
                    "action": action,
                    "edits": row_edits,
                    "reviewer": reviewer,
                    "source": "extract_queue",
                    "at": now,
                }
            )
    data["outcomes"].setdefault(company_id, []).extend(accepted)
    batch["status"] = "committed"
    batch["accepted_count"] = len(accepted)
    save_data()
    return {
        "ok": True,
        "committed": len(accepted),
        "edited": edited_count,
        "company_id": company_id,
    }


def search_entities(
    q: str,
    *,
    limit: int = 25,
    exchange: Optional[str] = None,
    sector: Optional[str] = None,
    data_quality: Optional[str] = None,
    corpus_status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Typeahead over Sensex seed + full NSE/BSE listing masters.

    Ranks hand_labeled / deep coverage above provisional shells. Adds
    doc_count, citeable_outcomes, and corpus_status honesty fields.
    Optional facet filters: exchange, sector, data_quality, corpus_status.
    """
    from app.data import doc_store
    from app.data.india_listings import india_equity_universe
    from app.data.gci_score_cache import get_listing_score
    from app.services.citations import CITEABLE_QUALITIES

    query = (q or "").strip().lower()
    if len(query) < 1:
        return []
    ex_f = (exchange or "").strip().upper() or None
    sec_f = (sector or "").strip().lower() or None
    dq_f = (data_quality or "").strip().lower() or None
    cs_f = (corpus_status or "").strip().lower() or None
    seed_by_id = {c["id"]: c for c in list_companies()}
    hits: List[Dict[str, Any]] = []
    for row in india_equity_universe():
        blob = f"{row.get('ticker','')} {row.get('name','')} {row.get('id','')}".lower()
        if query not in blob:
            continue
        if ex_f and (row.get("exchange") or "").upper() != ex_f:
            continue
        if sec_f and sec_f not in (row.get("sector") or "").lower():
            continue
        seeded = seed_by_id.get(row["id"])
        cached = get_listing_score(row["id"])
        score = None
        quality = row.get("data_quality") or "listing_provisional"
        citeable_n = 0
        if seeded:
            outs = get_outcomes(seeded["id"])
            quality = seeded.get("data_quality", quality)
            score = publishable_score(
                audited_company_gci(outs, company_id=seeded["id"]), quality
            )
            if quality in CITEABLE_QUALITIES:
                citeable_n = sum(
                    1
                    for o in outs
                    if (o.source_url or "").strip() and (o.quote_span or "").strip()
                )
        elif cached:
            score = cached.get("gci_score")
            quality = cached.get("data_quality", quality)
        if dq_f and (quality or "").lower() != dq_f:
            continue
        docs = doc_store.list_documents(company_id=row["id"], include_rejected=False)
        doc_count = len(docs)
        if quality in CITEABLE_QUALITIES and citeable_n > 0:
            status = "gci_citeable"
        elif seeded or doc_count > 0:
            status = "gci_available"
        else:
            status = "listed_not_in_corpus"
        if cs_f and status != cs_f:
            continue
        hits.append(
            {
                "id": row["id"],
                "name": row["name"],
                "ticker": row["ticker"],
                "sector": row.get("sector") or "Equity",
                "gci_score": score,
                "data_quality": quality,
                "market_id": "IN",
                "index_ids": row.get("index_ids"),
                "exchange": row.get("exchange"),
                "doc_count": doc_count,
                "citeable_outcomes": citeable_n,
                "corpus_status": status,
                "coverage_status": coverage_status_for(
                    row["id"], score=score, data_quality=quality
                ),
            }
        )
        if len(hits) >= max(limit * 4, 40):
            break

    def _rank(r: Dict[str, Any]) -> Tuple:
        q = r.get("data_quality") or ""
        q_rank = 0 if q == "hand_labeled" else (1 if q == "demo_structured" else 2)
        status_rank = {
            "gci_citeable": 0,
            "gci_available": 1,
            "listed_not_in_corpus": 2,
        }.get(str(r.get("corpus_status")), 3)
        return (
            status_rank,
            q_rank,
            -(r.get("citeable_outcomes") or 0),
            -(r.get("doc_count") or 0),
            r["gci_score"] is None,
            -(r["gci_score"] or 0),
            r["ticker"],
        )

    hits.sort(key=_rank)
    return hits[:limit]


def sector_leaderboard(
    market: Optional[str] = None, index: Optional[str] = None, *, limit: int = 40
) -> List[Dict[str, Any]]:
    """Sector average of published GCI — the same scorer call as the screener rows.

    A sector carries an average only at ``SECTOR_AVG_MIN_NAMES`` published names;
    ``best`` names a company only when its confidence tier may be ranked.
    """
    from app.data import markets as markets_data
    from app.services.score_policy import SECTOR_AVG_MIN_NAMES, is_rankable

    mid = market.upper() if market else None
    iid = index.upper() if index else None
    members = {s["id"] for s in markets_data.constituents_readonly(iid)} if iid else None

    by: Dict[str, Dict[str, Any]] = {}
    for c in list_companies():
        if mid and (c.get("market_id") or "IN").upper() != mid:
            continue
        if members is not None and c["id"] not in members:
            continue
        if not is_scoreable(c.get("data_quality")):
            continue
        meta = score_meta(get_outcomes(c["id"]), company_id=c["id"], data_quality=c.get("data_quality"))
        if meta["gci_score"] is None:
            continue
        sector = c.get("sector") or "Equity"
        cur = by.setdefault(sector, {"sector": sector, "scores": [], "names": [], "best": None})
        sc = float(meta["gci_score"])
        tier = meta["confidence_tier"]
        cur["scores"].append(sc)
        cur["names"].append(
            {"id": c["id"], "ticker": c.get("ticker") or c["id"], "name": c.get("name") or c["id"], "confidence_tier": tier}
        )
        if is_rankable(tier) and (cur["best"] is None or sc > cur["best"]["gci_score"]):
            cur["best"] = {"id": c["id"], "ticker": c.get("ticker") or c["id"], "name": c.get("name") or c["id"], "gci_score": sc}

    out = []
    for sector, v in by.items():
        count = len(v["scores"])
        enough = count >= SECTOR_AVG_MIN_NAMES
        out.append(
            {
                "sector": sector,
                "avg": round(sum(v["scores"]) / count, 1) if enough else None,
                "count": count,
                "min_names": SECTOR_AVG_MIN_NAMES,
                "best": v["best"] if enough else None,
                "names": sorted(v["names"], key=lambda n: n["name"]),
            }
        )
    out.sort(key=lambda r: (r["avg"] is None, -(r["avg"] or 0), -r["count"], r["sector"]))
    return out[:limit]


def company_period_docs(company_id: str, period: Optional[str] = None) -> List[Dict[str, Any]]:
    """Docs already ingested for a company (optional period filter on title/text meta)."""
    from app.data import doc_store

    docs = doc_store.list_documents(company_id=company_id, include_rejected=True)
    if period:
        p = period.lower()
        docs = [
            d
            for d in docs
            if p in (d.get("title") or "").lower()
            or p in (d.get("period") or "").lower()
            or p in (d.get("source_ref") or "").lower()
        ]
    return sort_document_listing(docs)


EXPECTED_DOC_TYPES = ("transcript", "results", "ir_guidance")


def period_completeness(company_id: str, periods: Optional[List[str]] = None) -> Dict[str, Any]:
    """Sensex-style period matrix: missing / pending / accepted + expected doc types."""
    from app.data import doc_store
    from app.services.citations import assess_citeability

    # Prefer periods that actually appear on outcomes for this company
    if periods is None:
        try:
            raw = (get_data().get("outcomes") or {}).get(company_id) or []
            derived = sorted({str(o.get("period")) for o in raw if o.get("period")})
            fy = [p for p in derived if p.upper().startswith("FY")]
            periods = fy[-3:] if len(fy) >= 3 else (fy or ["FY24", "FY25", "FY26"])
        except Exception:
            periods = ["FY24", "FY25", "FY26"]

    company = next((c for c in list_companies() if c["id"] == company_id), None)
    quality = (company or {}).get("data_quality") or "demo_structured"

    docs = doc_store.list_documents(company_id=company_id, include_rejected=True)
    rows = []
    for period in periods:
        pl = period.lower()
        period_docs = [
            d
            for d in docs
            if pl == (d.get("period") or "").lower()
            or pl in (d.get("title") or "").lower()
            or pl in (d.get("text") or "")[:240].lower()
        ]
        by_status = {"accepted": 0, "pending": 0, "rejected": 0, "other": 0}
        for d in period_docs:
            st = (d.get("review_status") or "pending").lower()
            if st in by_status:
                by_status[st] += 1
            else:
                by_status["other"] += 1
        have_types = {
            (d.get("doc_type") or "").lower()
            for d in period_docs
            if d.get("review_status") == "accepted"
        }
        type_coverage = {
            t: (t in have_types or (t == "ir_guidance" and "guidance" in have_types))
            for t in EXPECTED_DOC_TYPES
        }
        types_ok = all(type_coverage.values())
        if by_status["accepted"] > 0 and types_ok:
            status = "accepted"
        elif by_status["accepted"] > 0:
            status = "partial"
        elif by_status["pending"] > 0 or period_docs:
            status = "pending"
        else:
            status = "missing"
        rows.append(
            {
                "period": period,
                "status": status,
                "doc_count": len(period_docs),
                "by_status": by_status,
                "expected_types": list(EXPECTED_DOC_TYPES),
                "type_coverage": type_coverage,
                "types_complete": types_ok,
                "documents": [
                    {
                        "doc_id": d.get("doc_id"),
                        "title": d.get("title"),
                        "doc_type": d.get("doc_type"),
                        "review_status": d.get("review_status"),
                        "url": d.get("url"),
                        "source_type": d.get("source_type"),
                        "period": d.get("period"),
                    }
                    for d in sort_document_listing(period_docs)[:8]
                ],
            }
        )
    rows = sort_evidence_listing(rows)
    accepted = sum(1 for r in rows if r["status"] in ("accepted", "partial"))
    types_complete_n = sum(1 for r in rows if r.get("types_complete"))
    citeable_bound = 0
    citeable_ok = 0
    outcome_n = 0
    try:
        raw = (get_data().get("outcomes") or {}).get(company_id) or []
        outcome_n = len(raw)
        for o in raw:
            ok, _ = assess_citeability(
                data_quality=quality,
                source_url=o.get("source_url"),
                quote_span=o.get("quote_span"),
                doc_id=o.get("doc_id"),
            )
            if ok:
                citeable_ok += 1
            if o.get("doc_id") and o.get("quote_span") and o.get("source_url"):
                citeable_bound += 1
    except Exception:
        pass
    citeable_pct = round(100.0 * citeable_ok / outcome_n, 1) if outcome_n else 0.0
    tier1_gate = (
        len(rows) > 0
        and types_complete_n == len(rows)
        and citeable_pct >= 95.0
        and citeable_bound > 0
    )
    return {
        "company_id": company_id,
        "periods": rows,
        "expected_doc_types": list(EXPECTED_DOC_TYPES),
        "summary": {
            "accepted_periods": accepted,
            "types_complete_periods": types_complete_n,
            "total_periods": len(rows),
            "complete": accepted == len(rows) and len(rows) > 0,
            "citeable_bound_outcomes": citeable_bound,
            "citeable_outcomes": citeable_ok,
            "outcome_count": outcome_n,
            "citeable_pct": citeable_pct,
            "tier1_gate": tier1_gate,
            "missing_periods": [
                r["period"] for r in rows if r.get("status") in ("missing", "partial")
            ],
            "sla": {
                "target_citeable_pct": 95.0,
                "target_types_complete": True,
                "refresh_hours": float(os.environ.get("INTELLENS_REFRESH_HOURS", "6")),
            },
        },
        "note": (
            "Automatic corpus preferred — paste ingest is exception path. "
            "Tier-1 gate: expected doc types accepted per period + ≥95% citeable outcomes."
        ),
    }


def resolve_ticker_summary(ticker: str) -> Optional[Dict[str, Any]]:
    """Resolve one name by exchange ticker across seed + India listings.

    Default ``list_company_summaries()`` is Sensex seed only, so NSE_ALL
    names (20MICRONS, 360ONE, …) 404'd on ``/api/badge/{ticker}``.
    """
    clean = (ticker or "").replace(".svg", "").strip()
    if not clean:
        return None
    key = clean.upper()

    for c in list_companies():
        if (c.get("ticker") or "").upper() == key:
            outcomes = get_outcomes(c["id"])
            quality = c.get("data_quality", "demo_structured")
            from app.services.guidance_flags import score_meta
            from app.services.score_policy import is_scoreable

            meta = score_meta(
                outcomes,
                scoreable=is_scoreable(quality),
                company_id=c["id"],
                data_quality=quality,
            )
            return {
                "id": c["id"],
                "name": c.get("name"),
                "ticker": c["ticker"],
                "gci_score": meta["gci_score"],
                "data_quality": quality,
                "confidence_tier": meta.get("confidence_tier"),
                "as_of": meta.get("as_of"),
                "algorithm_id": meta.get("algorithm_id"),
                "coverage_status": coverage_status_for(
                    c["id"], score=meta["gci_score"], outcomes=outcomes, data_quality=quality
                ),
            }

    from app.data.gci_score_cache import get_listing_score
    from app.data.india_listings import find_listing_by_ticker
    from app.services.provisional_gci import QUALITY, score_provisional

    listing = find_listing_by_ticker(clean)
    if listing is None:
        return None
    cached = get_listing_score(listing["id"])
    if cached and cached.get("gci_score") is not None:
        score = cached.get("gci_score")
        quality = cached.get("data_quality") or listing.get("data_quality") or QUALITY
    else:
        scored = score_provisional(
            listing["id"], listing["ticker"], listing.get("sector") or "Equity"
        )
        score = scored.get("gci_score")
        quality = scored.get("data_quality") or QUALITY
    return {
        "id": listing["id"],
        "name": listing.get("name"),
        "ticker": listing["ticker"],
        "gci_score": publishable_score(score, quality),
        "data_quality": quality,
        "confidence_tier": (cached or {}).get("confidence_tier"),
        "as_of": (cached or {}).get("as_of"),
        "coverage_status": (cached or {}).get("coverage_status")
        or coverage_status_for(
            listing["id"], score=publishable_score(score, quality), data_quality=quality
        ),
        "algorithm_id": (cached or {}).get("algorithm_id"),
    }


MIN_CITEABLE_PIT_FOR_DELTAS = 4


def gci_change_bundle_for(company_id: str) -> Dict[str, Any]:
    """Score changes over time — only from the citeable outcome-as-of PIT series.

    Rule `index-integrity`: a Δ is published only when ``series_kind == "citeable_pit"``
    (≥4 analyst-reviewed as-of points). Otherwise every horizon is ``None`` and the
    bundle says why. No synthetic (`demo_*` / `hybrid_*`) path is ever blended in.
    """
    from app.services.changes import change_bundle

    detail = get_company_gci(company_id)
    anchor = detail.gci_score
    if anchor is None:
        bundle = change_bundle(None, [])
        bundle["series_kind"] = NOT_SCORED_STATUS
        bundle["series_n"] = 0
        bundle["citeable"] = False
        return bundle

    pit = pit_history(company_id)
    if len(pit) >= MIN_CITEABLE_PIT_FOR_DELTAS:
        series = [(p.as_of, p.gci_score) for p in pit]
        bundle = change_bundle(anchor, series)
        bundle["series_kind"] = "citeable_pit"
        bundle["series_n"] = len(series)
        bundle["citeable"] = True
        return bundle

    # Too few reviewed as-of points for a defensible delta — publish nothing.
    bundle = change_bundle(None, [])
    bundle["value"] = anchor
    bundle["series_kind"] = "citeable_pit_short" if len(pit) >= 2 else "insufficient_history"
    bundle["series_n"] = len(pit)
    bundle["citeable"] = len(pit) >= 2
    bundle["history"] = [
        {"period": p.as_of, "value": p.gci_score, "change_pct": None, "change_horizon": None}
        for p in pit
    ]
    bundle["note"] = (
        f"Score changes appear after {MIN_CITEABLE_PIT_FOR_DELTAS} reviewed reporting dates "
        f"({len(pit)} so far)."
    )
    return bundle
