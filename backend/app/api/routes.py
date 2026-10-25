from __future__ import annotations

import json
import os
from datetime import date as _date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Cookie, Depends, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse

from app.data.seed import get_data, reset_data
from app.models.schemas import (
    AcceptInviteRequest,
    AlertItem,
    ActualsImportRequest,
    AuthEmailRequest,
    AuthGuestRequest,
    AuthLoginRequest,
    AuthMfaConfirmRequest,
    AuthPasswordResetConfirm,
    AuthRegisterRequest,
    AuthVerifyConfirm,
    CommitExtractRequest,
    CompanyGCIDetail,
    CompanySummary,
    ConsensusImportRequest,
    CrawlRequest,
    DocDateRequest,
    DocReviewRequest,
    ExtractRequest,
    FeedbackCreate,
    HealthResponse,
    ImportFactsRequest,
    IngestMediaRequest,
    IngestPasteRequest,
    IngestUrlRequest,
    LabelDraftRequest,
    SetAuditFlagRequest,
    LabelImportRequest,
    LabelRejectRequest,
    LegalAttestRequest,
    MatchRequest,
    MemberRoleRequest,
    MsaInvoiceRequest,
    MsaSignRequest,
    OrgInviteRequest,
    OrgOidcRequest,
    OrgRevokeRequest,
    PilotRequestCreate,
    PilotRequestReview,
    PitPoint,
    PlatformAdminRoleRequest,
    PreferencesUpdate,
    RefreshRequest,
    ResearchChatRequest,
    RetailCheckoutRequest,
    RetailPayConfirm,
    ReviewRequest,
    SightsAskRequest,
    SightsDeepDiveRequest,
    SightsGridRequest,
)
from app.services import repository
from app.services.auth import optional_api_key, resolve_api_key
from app.services import admin_portal as admin_portal_svc
from app.services.entitlements import (
    has_feature,
    require_any_feature,
    require_feature,
    require_session_or_key,
    resolve_actor,
)
from app.services.extraction import extract_auto
from app.services.matching import alphahunter_facts_to_actuals, match_actuals
from app.services import research as research_svc

from app.version import APP_VERSION

router = APIRouter()


def _moved(feature: str, moved_to: str) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={"detail": f"{feature} moved to CiteAlpha Analyst", "moved_to": moved_to},
    )


@router.get("/api/status")
def public_status() -> Dict[str, Any]:
    """W8.6 — live health plus latest frozen index file."""
    from app.jobs import publish_index_files as pub

    files = pub.list_files()
    latest = files[-1] if files else None
    return {
        "ok": True,
        "api": APP_VERSION,
        "index_file": latest,
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        from app.services.csm_sla import record_health

        record_health(True)
    except Exception:
        pass
    return HealthResponse(status="ok", version=APP_VERSION)


@router.get("/api/v1/companies", response_model=List[CompanySummary])
@router.get("/api/companies", response_model=List[CompanySummary])
def companies(
    market: Optional[str] = None,
    index: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    scored: bool = False,
) -> List[CompanySummary]:
    if scored:
        return repository.list_published_companies()
    return repository.list_company_summaries(
        market=market, index=index, limit=limit, offset=offset
    )


@router.get("/api/companies/count")
def companies_count(
    market: Optional[str] = None, index: Optional[str] = None
) -> Dict[str, Any]:
    n = repository.count_companies(market=market, index=index)
    return {"count": n, "market": market, "index": index}


@router.get("/api/companies/search")
def companies_search(
    q: str = "",
    limit: int = 25,
    exchange: Optional[str] = None,
    sector: Optional[str] = None,
    data_quality: Optional[str] = None,
    corpus_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Typeahead over covered India exchange listings + GCI when scored."""
    hits = repository.search_entities(
        q,
        limit=max(1, min(limit, 50)),
        exchange=exchange,
        sector=sector,
        data_quality=data_quality,
        corpus_status=corpus_status,
    )
    return {
        "q": q,
        "count": len(hits),
        "results": hits,
        "facets": {
            "exchange": exchange,
            "sector": sector,
            "data_quality": data_quality,
            "corpus_status": corpus_status,
        },
    }


@router.get("/api/sectors/leaderboard")
def sectors_leaderboard(
    market: Optional[str] = "IN",
    index: Optional[str] = None,
    limit: int = 40,
) -> Dict[str, Any]:
    rows = repository.sector_leaderboard(market=market, index=index, limit=limit)
    return {"market": market, "index": index, "count": len(rows), "sectors": rows}


@router.post("/api/gci/score-universe")
def score_universe(
    limit: Optional[int] = None,
    auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    """Rebuild NSE+BSE GCI cache with gci_scoring v2 (seed + listing_provisional)."""
    from app.data import audit_log
    from app.data.gci_score_cache import build_india_gci_cache, clear_memory_cache

    clear_memory_cache()
    report = build_india_gci_cache(limit=limit)
    audit_log.record(
        "gci_score_universe",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"count": report.get("count"), "scored_count": report.get("scored_count")},
    )
    return {
        "ok": True,
        "algorithm": report.get("algorithm"),
        "count": report.get("count"),
        "scored_count": report.get("scored_count"),
        "as_of": report.get("as_of"),
        "note": report.get("note"),
    }


@router.get("/api/v1/companies/{company_id}/gci", response_model=CompanyGCIDetail)
@router.get("/api/companies/{company_id}/gci", response_model=CompanyGCIDetail)
def company_gci(
    company_id: str,
    authorization: Optional[str] = Header(default=None),
    user_agent: Optional[str] = Header(default=None),
) -> CompanyGCIDetail:
    from app.services import session_auth
    from app.services.indexing_crawler import is_indexing_crawler

    # An indexer is here to record the public dossier. The 15-open guest cap
    # would stop that crawl. A visitor without an indexer user agent still hits it.
    if not is_indexing_crawler(user_agent):
        try:
            session_auth.bump_guest_dossier(session_auth.extract_bearer(authorization))
        except HTTPException:
            raise
        except Exception:
            pass
    return repository.get_company_gci(company_id)


@router.post("/api/companies/{company_id}/audit-flags")
def company_set_audit_flag(
    company_id: str,
    body: SetAuditFlagRequest,
    auth=Depends(require_feature("labeling")),
) -> Dict[str, Any]:
    from app.services.guidance_flags import set_audit_flag

    rec = set_audit_flag(
        company_id,
        body.flag,
        set_by=str(auth.get("user_id") or auth.get("key") or ""),
        source_url=body.source_url or "",
        note=body.note or "",
    )
    return {"ok": True, "flag": rec}


@router.delete("/api/companies/{company_id}/audit-flags/{flag}")
def company_clear_audit_flag(
    company_id: str,
    flag: str,
    _auth=Depends(require_feature("labeling")),
) -> Dict[str, Any]:
    from app.services.guidance_flags import clear_audit_flag

    clear_audit_flag(company_id, flag)
    return {"ok": True}


@router.get("/api/v1/companies/{company_id}/gci/history", response_model=List[PitPoint])
@router.get("/api/companies/{company_id}/gci/history", response_model=List[PitPoint])
def company_gci_history(company_id: str) -> List[PitPoint]:
    return repository.pit_history(company_id)


@router.get("/api/alerts", response_model=List[AlertItem])
def alerts() -> List[AlertItem]:
    return repository.list_alerts()


@router.get("/api/products")
def products_catalog() -> Dict[str, Any]:
    """Parallel SKU catalog (Score / Cite / Radar / Ledger / Data)."""
    from app.services import portfolio as portfolio_svc

    return portfolio_svc.list_products()


def _require_holdings(ent: Dict[str, Any] = Depends(resolve_actor)) -> Dict[str, Any]:
    if ent.get("kind") == "guest" or ent.get("source") == "guest":
        if ent.get("user_id"):
            raise HTTPException(status_code=403, detail="Sign in with a desk seat to open Holdings")
        raise HTTPException(status_code=401, detail="Authentication required")
    if not has_feature(ent, "holdings"):
        from app.services.pilot_checklist import pilot_evaluation_ended

        if ent.get("plan") == "pilot" and pilot_evaluation_ended(str(ent.get("org_id") or "")):
            raise HTTPException(
                status_code=403,
                detail="This evaluation has ended. Holdings stays on a paid desk.",
            )
        if ent.get("plan") == "pilot":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Holdings look-through is open during an admin-approved evaluation "
                    "of 30, 45, or 60 days, and on a paid desk after that."
                ),
            )
        raise HTTPException(
            status_code=403,
            detail=f"Plan {ent.get('plan')} / role {ent.get('role')} lacks holdings",
        )
    if not ent.get("org_id"):
        raise HTTPException(status_code=403, detail="Holdings is saved on a desk, not a personal guest session")
    return ent


@router.post("/api/holdings/lookthrough")
def holdings_lookthrough(
    body: Dict[str, Any],
    ent: Dict[str, Any] = Depends(_require_holdings),
) -> Dict[str, Any]:
    from app.services.holdings import submit_lookthrough

    return submit_lookthrough(str(ent["org_id"]), body)


@router.get("/api/holdings/latest")
def holdings_latest(ent: Dict[str, Any] = Depends(_require_holdings)) -> Dict[str, Any]:
    from app.services.holdings import latest_lookthrough

    return latest_lookthrough(str(ent["org_id"]))


@router.get("/api/radar/feed")
def radar_feed(
    company_id: Optional[str] = None,
    limit: int = 50,
    include_revisions: bool = True,
) -> Dict[str, Any]:
    """CiteAlpha Radar — guidance change / miss / drop / withdrawal feed."""
    from app.services import portfolio as portfolio_svc

    return portfolio_svc.radar_feed(
        company_id=company_id,
        limit=limit,
        include_revisions=include_revisions,
    )


@router.get("/api/ledger/{company_id}")
def company_ledger(
    company_id: str,
    credit_only: bool = False,
    mirror: bool = False,
    auth=Depends(optional_api_key),
) -> Dict[str, Any]:
    """CiteAlpha Ledger — promise accountability dossier."""
    from app.services import portfolio_phases as phases
    from app.services.feature_flags import ir_mirror_enabled

    if mirror and not ir_mirror_enabled():
        raise HTTPException(
            status_code=403,
            detail="IR Mirror requires IR_MIRROR=1 or enterprise MSA",
        )
    if mirror or credit_only:
        return phases.company_ledger_filtered(
            company_id, credit_only=credit_only, mirror=mirror
        )
    from app.services import portfolio as portfolio_svc

    return portfolio_svc.company_ledger(company_id)


@router.get("/api/ledger/{company_id}/pdf")
def company_ledger_pdf(
    company_id: str,
    credit_only: bool = False,
    auth=Depends(require_feature("ic_export")),
) -> Any:
    """CiteAlpha Ledger PDF — board / IC pack."""
    from fastapi.responses import Response

    from app.services import portfolio_phases as phases

    pdf = phases.ledger_pdf_bytes(company_id, credit_only=credit_only)
    detail = repository.get_company_gci(company_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ledger-{detail.ticker}.pdf"'
        },
    )


@router.get("/api/ledger/mirror/{company_id}")
def company_ledger_mirror(company_id: str, auth=Depends(optional_api_key)) -> Dict[str, Any]:
    """IR Mirror — corporate accountability view."""
    from app.services import portfolio_phases as phases
    from app.services.feature_flags import ir_mirror_enabled

    if not ir_mirror_enabled():
        raise HTTPException(status_code=403, detail="Set IR_MIRROR=1 for IR Mirror mode")
    return phases.company_ledger_filtered(company_id, mirror=True)


@router.get("/api/data/catalog")
def data_catalog() -> Dict[str, Any]:
    """CiteAlpha Data — discoverable PIT / factor export contracts."""
    from app.services import portfolio as portfolio_svc

    return portfolio_svc.data_catalog()


# --- Portfolio P2 Radar ---


@router.get("/api/radar/diff/{company_id}")
def radar_diff_brief(company_id: str) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    return phases.guidance_diff_brief(company_id)


@router.get("/api/radar/calendar")
def radar_calendar(limit: int = 30) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    return phases.radar_calendar(limit=limit)


@router.get("/api/radar/digest/preview")
def radar_digest_preview() -> JSONResponse:
    return _moved("Radar digest", "/api/analyst/digest")


@router.post("/api/radar/digest/send")
def radar_digest_send() -> JSONResponse:
    return _moved("Radar digest", "/api/analyst/digest")


@router.post("/api/radar/webhooks")
def radar_webhook_register() -> JSONResponse:
    return _moved("Radar webhooks", "/api/analyst/destinations")


# --- Portfolio P4 Cite / Data ---


@router.get("/api/cite/tiers")
def cite_tiers() -> Dict[str, Any]:
    from app.services.portfolio_phases import CITE_TIERS

    return {"product": "CiteAlpha Cite", "tiers": CITE_TIERS}


@router.get("/api/cite/usage")
def cite_usage(auth=Depends(optional_api_key)) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    key = (auth or {}).get("key") if auth else None
    return phases.cite_usage_snapshot(key)


@router.get("/api/data/export/outcomes")
def data_export_outcomes(
    format: str = "json",
    limit: int = 500,
    auth=Depends(resolve_actor),
) -> Any:
    from fastapi.responses import Response, StreamingResponse

    from app.services import portfolio_phases as phases

    fmt = (format or "json").lower()
    if fmt != "json":
        if auth.get("source") == "guest":
            raise HTTPException(status_code=401, detail="X-API-Key required for CSV/Parquet export")
        if not has_feature(auth, "em_export"):
            raise HTTPException(status_code=403, detail="EM / Data export requires Enterprise")
    result = phases.bulk_outcomes_export(format=fmt, limit=limit)
    if fmt == "json":
        return result
    if fmt == "csv":
        return Response(
            content=result.get("csv") or "",
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="outcomes_bulk.csv"'},
        )
    if fmt in ("parquet", "pq"):
        raw = result.get("parquet_bytes")
        if raw is None:
            return result
        return Response(
            content=raw,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="outcomes_bulk.parquet"'},
        )
    return result


@router.get("/api/digest/vernacular/{company_id}")
def digest_vernacular(company_id: str, lang: str = "hi") -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    return phases.vernacular_digest(company_id, lang=lang)


@router.get("/api/data/kpi-dictionary")
def data_kpi_dictionary(sector: Optional[str] = None) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    return phases.kpi_dictionary(sector)


# --- Portfolio P5 Stretch ---


@router.get("/api/score/narrative-consistency/{company_id}")
def score_narrative_consistency(company_id: str) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases
    from app.services.feature_flags import portfolio_stretch_enabled

    if not portfolio_stretch_enabled():
        raise HTTPException(status_code=404, detail="Stretch endpoints disabled")
    return phases.narrative_consistency_index(company_id)


@router.get("/api/workbench/extraction")
def workbench_extraction(auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases
    from app.services.feature_flags import portfolio_stretch_enabled

    if not portfolio_stretch_enabled():
        raise HTTPException(status_code=404, detail="Stretch endpoints disabled")
    return phases.extraction_workbench_status()


@router.get("/api/channel/trust-badge/{ticker}")
def channel_trust_badge(ticker: str) -> Dict[str, Any]:
    from app.services import portfolio_phases as phases

    result = phases.trust_badge_channel(ticker)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Ticker not found")
    return result


@router.get("/api/peers/{sector}")
def peers(sector: str) -> Dict[str, Any]:
    rows = [c for c in repository.list_company_summaries() if c.sector.lower() == sector.lower()]
    return {"sector": sector, "companies": rows}


@router.post("/api/extract")
def extract(body: ExtractRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.data import audit_log
    from app.services.extraction import extract_auto
    from app.services.feature_flags import llm_extract_enabled
    from app.services.llm_client import llm_configured

    text = body.text
    sample = not text
    if not text:
        text = get_data().get("sample_transcripts", {}).get(body.company_id)
    if not text:
        return {"statements": [], "error": "No transcript text provided or seeded"}
    statements = extract_auto(
        text,
        company_id=body.company_id,
        period=body.period,
        source_ref=body.source_ref,
    )
    batch = repository.save_pending_extract(body.company_id, statements, sample=sample)
    engines = sorted({str(s.get("extract_engine") or "") for s in statements})
    audit_log.record(
        "extract",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"extract_id": batch["id"], "count": len(statements), "engines": engines},
    )
    return {
        "statements": statements,
        "count": len(statements),
        "extract_id": batch["id"],
        "needs_review": True,
        "extract_engines": engines,
        "llm_extract_enabled": llm_extract_enabled(),
        "llm_configured": llm_configured(),
        "note": "Statements are pending — POST /api/extract/commit to enter GCI",
    }


@router.post("/api/match")
def match(body: MatchRequest, _auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    matched = match_actuals(body.statements, body.actuals)
    return {"matched": matched, "count": len(matched)}


@router.post("/api/import/alphahunter")
def import_alphahunter(body: ImportFactsRequest, _auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    return _import_facts(body)


@router.post("/api/import/facts")
def import_facts(body: ImportFactsRequest, _auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    """P1.4 — Facts JSON import (AlphaHunter-compatible alias)."""
    return _import_facts(body)


@router.get("/api/import/alphahunter/status")
def alphahunter_status() -> Dict[str, Any]:
    from app.services.alphahunter_live import connector_status

    return connector_status()


@router.post("/api/import/alphahunter/live")
def alphahunter_live_pull(
    company_id: Optional[str] = None,
    merge: bool = True,
    _auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    """Pull facts from ALPHAHUNTER_API_URL and optionally merge into a company."""
    from app.services.alphahunter_live import pull_facts

    try:
        pulled = pull_facts(company_id=company_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if not merge or not company_id:
        return pulled
    body = ImportFactsRequest(
        facts=pulled["facts"],
        merge_into_company=company_id,
        allow_custom=False,
    )
    merged = _import_facts(body)
    return {**pulled, **merged}


def _import_facts(body: ImportFactsRequest) -> Dict[str, Any]:
    from app.data.metric_catalog import normalize_metric, require_metric

    # Normalize metrics on facts before matching
    facts: List[Dict[str, Any]] = []
    for f in body.facts:
        row = dict(f)
        if row.get("metric") is not None or row.get("guided_value") is not None:
            try:
                row["metric"] = require_metric(
                    row.get("metric") or "revenue_growth_pct",
                    allow_custom=body.allow_custom,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
        facts.append(row)

    actuals = alphahunter_facts_to_actuals(facts)
    for a in actuals:
        nid = normalize_metric(a.get("metric"))
        if nid:
            a["metric"] = nid
        elif not body.allow_custom:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown metric in actuals: {a.get('metric')}",
            )

    if body.merge_into_company:
        statements = []
        for f in facts:
            if f.get("guidance_change") or f.get("guided_value") is not None:
                try:
                    metric = require_metric(
                        f.get("metric", "revenue_growth_pct"),
                        allow_custom=body.allow_custom,
                    )
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e)) from e
                statements.append(
                    {
                        "company_id": body.merge_into_company,
                        "period": f.get("period") or f.get("fiscal_period") or "FY25",
                        "metric": metric,
                        "guided_value": float(f.get("guided_value") or f.get("yoy_revenue_pct") or 0),
                        "guided_low": f.get("guided_low"),
                        "guided_high": f.get("guided_high"),
                        "actual_value": f.get("actual_value"),
                        "guided_text": str(f.get("guidance_change") or f.get("guidance_summary") or "imported"),
                        "confidence": float(f.get("confidence_flag") or 0.75),
                        "speaker": "CFO",
                        "thread_id": f"{body.merge_into_company}-import",
                        "dropped": False,
                        "source_url": f.get("source_ref"),
                        "source_ref": f.get("source_ref") or "facts_json",
                        "quote_span": None,
                        "as_of": f.get("as_of"),
                    }
                )
        matched = match_actuals(statements, actuals) if statements else []
        n = repository.merge_matched(body.merge_into_company, matched) if matched else 0
        return {"actuals": actuals, "merged": n, "import_kind": "facts_json"}
    return {"actuals": actuals, "import_kind": "facts_json"}


@router.post("/api/review")
def review(body: ReviewRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    return repository.apply_review(
        body.company_id,
        body.outcome_index,
        body.action,
        body.comment,
        body.edits,
        reviewer=auth.get("org", "unknown"),
        org_id=auth.get("org"),
    )


@router.get("/api/reviews")
def reviews(_auth=Depends(require_feature("desk"))) -> Dict[str, Any]:
    rows = list(get_data().get("reviews", []))
    if str(_auth.get("platform_admin_role") or "") != "super":
        org = _auth.get("org") or _auth.get("org_id")
        rows = [r for r in rows if r.get("org_id") == org]
    return {"reviews": rows}


@router.post("/api/admin/reset-demo")
def reset_demo(_auth=Depends(admin_portal_svc.require_platform_perm("system.ops"))) -> Dict[str, Any]:
    data = reset_data()
    return {"ok": True, "companies": len(data["companies"])}


@router.get("/api/companies/{company_id}/wordmap")
def wordmap(company_id: str, auth=Depends(require_feature("wordmap"))) -> Dict[str, Any]:
    """G13 / P1.1 — entity vs industry themes from corpus (seed fallback). Seat-only."""
    from app.services.wordmap import build_wordmap

    return build_wordmap(company_id)


@router.get("/api/orgs/me")
def org_me(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Session user's tenant snapshot (B2B or retail micro-tenant)."""
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    oid = user.get("org_id")
    if not oid:
        raise HTTPException(status_code=404, detail="No org on this session (guest)")
    return org_svc.org_snapshot(str(oid))


@router.get("/api/entitlements/me")
def entitlements_me(ent=Depends(resolve_actor)) -> Dict[str, Any]:
    """Effective plan × role access (intersection, never union)."""
    return ent


@router.get("/api/orgs/{org_id}")
def org(org_id: str, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    """G16 / P2.1 — org seats + plan entitlements."""
    from app.services import orgs as org_svc

    org_svc.assert_org_access(auth, org_id)
    return org_svc.org_snapshot(org_id)


@router.get("/api/vernacular/{company_id}")
def vernacular(
    company_id: str,
    lang: str = "hi",
    _auth=Depends(require_feature("vernacular")),
) -> Dict[str, Any]:
    """G19 / G23 — localized GCI blurb templates."""
    detail = repository.get_company_gci(company_id)
    score = detail.gci_score
    templates = {
        "hi": f"{detail.name} का GCI स्कोर {score} है। यह प्रबंधन मार्गदर्शन बनाम वास्तविक परिणाम पर आधारित है।",
        "en": f"{detail.name} GCI score is {score}, based on guidance vs actuals.",
        "ta": f"{detail.name} GCI மதிப்பெண் {score}. இது வழிகாட்டுதல் vs உண்மையான முடிவுகள் அடிப்படையில்.",
        "te": f"{detail.name} GCI స్కోర్ {score}. మార్గదర్శకత్వం vs వాస్తవాలు.",
        "kn": f"{detail.name} GCI ಸ್ಕೋರ್ {score}. ಮಾರ್ಗದರ್ಶನ vs ವಾಸ್ತವ.",
        "ml": f"{detail.name} GCI സ്കോർ {score}. മാർഗനിർദ്ദേശം vs യഥാർത്ഥം.",
        "gu": f"{detail.name} નો GCI સ્કોર {score} છે.",
        "mr": f"{detail.name} चा GCI स्कोअर {score} आहे.",
        "bn": f"{detail.name}-এর GCI স্কোর {score}।",
        "pa": f"{detail.name} ਦਾ GCI ਸਕੋਰ {score} ਹੈ।",
        "ja": f"{detail.name} の GCI スコアは {score} です（ガイダンス対実績）。",
        "zh": f"{detail.name} 的 GCI 评分为 {score}（指引对比实际）。",
        "ar": f"درجة GCI لـ {detail.name} هي {score} (التوجيه مقابل النتائج).",
        "es": f"La puntuación GCI de {detail.name} es {score} (orientación vs resultados).",
        "fr": f"Le score GCI de {detail.name} est {score} (guidance vs résultats).",
        "de": f"Der GCI-Score von {detail.name} beträgt {score} (Guidance vs. Ist).",
        "pt": f"A pontuação GCI de {detail.name} é {score} (orientação vs resultados).",
    }
    fallback = lang not in templates
    return {
        "company_id": company_id,
        "lang": "en" if fallback else lang,
        "text": templates.get(lang, templates["en"]),
        "supported_langs": list(templates.keys()),
        "status": "template",
        "fallback": fallback,
    }


@router.get("/api/badge/{ticker}")
def gci_badge(ticker: str) -> Dict[str, Any]:
    """Broker-embeddable Guidance Credibility Index badge."""
    from app.services import badge as badge_svc

    return badge_svc.payload(ticker)


@router.get("/api/badge/{ticker}/svg")
def gci_badge_svg(ticker: str):
    """SVG badge for broker embed (ticker, GCI, tier, as-of)."""
    from app.services import badge as badge_svc

    return badge_svc.svg_response(ticker)


@router.get("/api/public/seo-dossiers")
def public_seo_dossiers() -> Dict[str, Any]:
    """Hand-labeled dossiers for prerender + sitemap (W5.2)."""
    from app.services.seo_public import list_indexable_dossiers

    rows = list_indexable_dossiers()
    return {"dossiers": rows, "count": len(rows)}


@router.get("/api/og/{company_id}.png")
def og_png(company_id: str):
    """1200×630 PNG share card for a company dossier."""
    from app.services import og_card

    return og_card.png_response(company_id)


@router.get("/api/og/{company_id}.svg")
def og_svg(company_id: str):
    """SVG share card (same content as PNG)."""
    from app.services import og_card

    return og_card.svg_response(company_id)


@router.get("/api/meta")
def meta() -> Dict[str, Any]:
    from app.data import doc_store
    from app.data import markets as markets_data
    from app.data.market_history import history_meta
    from app.data.metric_catalog import METRICS
    from app.data.source_policy import POLICY_SUMMARY, policy_payload
    from app.services.feature_flags import flags_dict
    from app.services.legal import copyright_meta
    from app.services.pending_depth import pending_depth_report
    from app.services.refresh import refresh_interval_hours
    from app.db.postgres import postgres_status

    data = get_data()
    labeled = sum(1 for c in data["companies"] if c.get("data_quality") == "hand_labeled")
    demo = sum(1 for c in data["companies"] if c.get("data_quality") == "demo_structured")
    mmeta = markets_data.markets_meta()
    hmeta = history_meta()
    from app.services.gci_scoring import algorithm_id, compute_company_gci
    from app.data.seed import get_outcomes

    from app.data.india_listings import india_equity_universe
    from app.services.coverage import universe_coverage_counts
    from app.services.score_policy import is_scoreable

    scored = sum(
        1
        for c in data["companies"]
        if is_scoreable(c.get("data_quality"))
        and compute_company_gci(get_outcomes(c["id"])) is not None
    )
    from app.data.gci_score_cache import load_cache

    gci_cache = load_cache()
    listing_scored = int(gci_cache.get("scored_count") or 0)
    depth = pending_depth_report(bootstrap=False)
    return {
        "version": APP_VERSION,
        "company_count": len(data["companies"]),
        "hand_labeled_count": labeled,
        "demo_structured_count": demo,
        "gci_scored_count": scored,
        "sensex_scored_count": sum(
            1
            for r in markets_data.list_constituents("SENSEX")
            if is_scoreable(r.get("data_quality"))
            and compute_company_gci(get_outcomes(r["id"])) is not None
        ),
        "sensex_count": len(markets_data.list_constituents("SENSEX")),
        "gci_listing_scored_count": listing_scored,
        "gci_listing_unscored_count": max(
            0, len(gci_cache.get("scores") or {}) - listing_scored
        ),
        "gci_coverage": universe_coverage_counts(
            [c["id"] for c in data["companies"]],
            [r["id"] for r in india_equity_universe()],
        ),
        "gci_algorithm": algorithm_id(),
        "gci_cache_algorithm": gci_cache.get("algorithm") or "gci_scoring_v2",
        "gci_listing_as_of": gci_cache.get("as_of"),
        "markets_count": mmeta["markets_count"],
        "indexes_count": mmeta["indexes_count"],
        "gci_deep_markets": mmeta["gci_deep_markets"],
        "markets_note": mmeta["scaffold_note"],
        "market_universe_size": mmeta["market_universe_size"],
        "india_listings": mmeta.get("india_listings"),
        "history_years": hmeta["history_years"],
        "history_kind": hmeta["history_kind"],
        "history_note": hmeta["history_note"],
        "fmp_configured": hmeta.get("fmp_configured", False),
        "refresh": {
            "interval_hours": refresh_interval_hours(),
            "endpoint": "POST /api/ingest/refresh",
            "scheduler": "docker compose scheduler | scripts/gci-refresh-loop.sh",
            "note": "Live IR crawl every 6 hours. New documents stay in the review queue until an analyst accepts them.",
        },
        "filing_to_score": _filing_to_score_payload(),
        "document_count": len(doc_store.list_documents(include_rejected=True)),
        "gci_metric_count": len(METRICS),
        "gci_source_policy": POLICY_SUMMARY,
        "source_policy": policy_payload(),
        "implementation_phases": ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
        "feature_flags": flags_dict(),
        "gaps_closed": [
            "G01-hand-labeled-cohort",
            "G02-extract",
            "G03-match",
            "G04-sensex30",
            "G05-sources",
            "G06-asymmetric",
            "G07-ranges",
            "G08-labels",
            "G09-threads",
            "G10-trend",
            "G11-peers",
            "G12-dropped",
            "G13-wordmap",
            "G14-review",
            "G15-alphahunter-import",
            "G16-api-key-auth",
            "G17-pit-history",
            "G18-alerts",
            "G19-vernacular",
            "G20-badge",
            "G21-sebi-note",
            "G22-em-api-shape",
            "G23-japan",
            "G24-metric-catalog",
            "G25-source-policy",
        ],
        "open_gaps": [],
        "pending_depth": depth,
        "data_quality_note": (
            f"{labeled}/{len(data['companies'])} Sensex companies are hand_labeled "
            f"({demo} demo_structured). Prefer hand_labeled for external citations. "
            + POLICY_SUMMARY
        ),
        "pitch": "Keep your market terminal for prices; use CiteAlpha for guidance delivery.",
        "legal": copyright_meta(),
        "infra": {
            "postgres": postgres_status(),
            "https_required_note": "Terminate TLS at ALB/CloudFront; set HSTS in production.",
            "secrets_note": "Use AWS Secrets Manager/SSM; rotate intellens-demo out of production.",
        },
        "research_terminal": {
            "search": "/api/research/search",
            "chat": "/api/research/chat",
            "snapshot": "/api/research/snapshot/{id}",
            "estimates": "/api/research/estimates/{id}",
            "news": "/api/research/news",
            "watchlist": "/api/research/watchlist",
            "transcripts": "/api/research/transcripts",
            "citations": "/api/citations/{id}",
            "note": "CiteAlpha Filing Search; cite-only chat with numbered sources. Period changes are context — not GCI.",
        },
    }


@router.get("/api/compliance/sebi-note")
def sebi_note() -> Dict[str, Any]:
    """G21 — packaging guidance for SEBI RA scope."""
    from app.services.legal import COPYRIGHT_LINE, LEGAL_ENTITY, PRODUCT_NAME

    return {
        "lead_with": "factual GCI / evidence trail",
        "avoid_without_ra": ["buy", "hold", "sell", "retail recommendations"],
        "status": "counsel-required-before-retail",
        "product": PRODUCT_NAME,
        "legal_entity": LEGAL_ENTITY,
        "copyright": COPYRIGHT_LINE,
        "note": (
            f"{PRODUCT_NAME} is a product of {LEGAL_ENTITY}. "
            "Retail (B2C) access is research tooling only — not SEBI RA advice."
        ),
    }


@router.get("/api/legal/meta")
def legal_meta() -> Dict[str, Any]:
    from app.services.legal import copyright_meta

    return copyright_meta()


@router.get("/api/legal/terms")
def legal_terms() -> Dict[str, Any]:
    from app.services.legal import terms_document

    return terms_document()


@router.get("/api/legal/privacy")
def legal_privacy() -> Dict[str, Any]:
    from app.services.legal import privacy_document

    return privacy_document()


def _filing_to_score_payload() -> Dict[str, Any]:
    from app.services.score_sla import sla_summary

    return sla_summary()


def _source_verification_payload() -> Dict[str, Any]:
    from app.services.source_verify import load_report

    r = load_report()
    return {
        "as_of": r.get("as_of"),
        "checked": int(r.get("checked") or 0),
        "verified": int(r.get("verified") or 0),
        "failed": int(r.get("failed") or 0),
        "fetch_failed": int(r.get("fetch_failed") or 0),
        "note": r.get("note") or "",
    }


@router.get("/api/trust")
def trust_center() -> Dict[str, Any]:
    """Public Trust Center payload — procurement hygiene, not marketing fluff."""
    from app.services.feature_flags import flags_dict
    from app.services.legal import (
        CONTACT_EMAIL,
        LEGAL_ENTITY,
        PRODUCT_NAME,
        PUBLIC_DOMAIN,
        copyright_meta,
        privacy_document,
        terms_document,
    )
    from app.services import labeling as lbl
    from app.services.rbac import sso_status
    from app.services.security_headers import csp_policy, force_https, hsts_enabled

    st = sso_status()
    terms = terms_document()
    privacy = privacy_document()
    meta = copyright_meta()
    llm_on = bool(flags_dict().get("LLM_CONFIGURED") or flags_dict().get("INTELLENS_LLM_EXTRACT"))
    public_copyright = {
        "legal_entity": meta.get("legal_entity"),
        "product": meta.get("product"),
        "year": meta.get("year"),
        "line": meta.get("line"),
        "terms_version": meta.get("terms_version"),
        "privacy_version": meta.get("privacy_version"),
        "contact_email": meta.get("contact_email"),
        "domain": meta.get("domain"),
    }
    return {
        "product": PRODUCT_NAME,
        "legal_entity": LEGAL_ENTITY,
        "domain": PUBLIC_DOMAIN,
        "copyright": public_copyright,
        "security": {
            "force_https": force_https(),
            "hsts": hsts_enabled(),
            "headers": [
                "X-Content-Type-Options: nosniff",
                "X-Frame-Options: DENY",
                "Referrer-Policy: no-referrer",
                "Content-Security-Policy (GA/Plausible hosts allowed; scripts load after consent)",
                "Strict-Transport-Security (when HSTS enabled)",
            ],
            "auth_modes": ["register", "login", "guest", "api_key", "sso"],
            "csp": csp_policy(),
        },
        "sso": {
            "enabled": st.get("enabled"),
            "configured": st.get("configured"),
            "note": "SSO is available for desk tenants on request.",
        },
        "citations": {
            "model": "cite_* ids with quote, locator, bibliographic / markdown / IC footnote",
            "endpoints": ["/api/citations", "/api/citations/{id}", "/c/{citationId}"],
            "research_chat": "cite-only; refuses when evidence is missing",
        },
        "compliance": {
            "posture": "Factual research product — not investment advice; no Buy/Hold/Sell",
            "sebi": "Not a SEBI-registered Research Analyst product unless separately disclosed",
            "terms_version": terms.get("version"),
            "privacy_version": privacy.get("version"),
            "contact_email": CONTACT_EMAIL,
            "privacy_email": "privacy@citealpha.com",
            "link_out_policy": (
                "Filings and transcripts stay on the issuer or exchange site. "
                "CiteAlpha stores a dated quote and a link; we do not redistribute original PDFs."
            ),
            "prices_on_public": False,
            "links": {
                "terms": "/terms",
                "privacy": "/privacy",
                "package": "/products#plans",
                "help": "/help",
                "about": "/about",
            },
        },
        "data": {
            "beachhead": "India equity (Sensex → Nifty)",
            "gci": "Guidance Credibility Index — management promises vs delivery",
            "invent_actuals": False,
            "quality_badges": "hand_labeled (citeable) vs sample data vs listing-only",
        },
        "residency": {
            "region": "ap-south-1",
            "provider": "AWS",
            "note": (
                "Production compute and load balancing in AWS Mumbai (ap-south-1). "
                "Auth durability depends on configured Postgres or a durable volume."
            ),
        },
        "tenancy": {
            "model": "org_id isolation for reviews, seats, API keys, and labeling queue",
            "auth": "session, API key, optional OIDC SSO",
        },
        "subprocessors": [
            {
                "name": "Amazon Web Services",
                "role": "Hosting (ap-south-1)",
                "optional": False,
            },
            {
                "name": "Amazon SES",
                "role": "Account email: verification, password reset, invites, and pilot requests",
                "optional": True,
            },
            {
                "name": "OIDC identity provider",
                "role": "Enterprise SSO when configured",
                "optional": True,
            },
            {
                "name": "OpenAI or Anthropic",
                "role": "Optional guidance extract when a model is keyed — not used to invent actuals",
                "optional": True,
            },
            {
                "name": "Google Analytics / Tag Manager",
                "role": "Optional funnel analytics after DPDP consent",
                "optional": True,
            },
            {
                "name": "Plausible",
                "role": "Privacy-friendly analytics when enabled for the site",
                "optional": True,
            },
        ],
        "incident": {
            "contact": CONTACT_EMAIL,
            "privacy_email": "privacy@citealpha.com",
            "note": (
                "Security questionnaires and DPA requests via sales@citealpha.com. "
                "Privacy requests via privacy@citealpha.com."
            ),
        },
        "labeling_governance": lbl.audit_summary(),
        "source_verification": _source_verification_payload(),
        "filing_to_score": _filing_to_score_payload(),
        "llm": {
            "configured": llm_on,
            "note": (
                "Optional extract model (OpenAI or Anthropic when keyed) with heuristic fallback. "
                "Submitted extract text may be sent to that processor. Not used to invent actuals."
            ),
        },
        "feature_flags_public": {
            k: flags_dict().get(k)
            for k in ("SSO", "RESEARCH_LLM", "LLM_CONFIGURED")
            if k in flags_dict()
        },
    }


@router.get("/api/export/em-factor/{company_id}")
def em_factor(
    company_id: str,
    format: str = "json",
    auth=Depends(resolve_actor),
) -> Any:
    """G22 / P1.3 — EM factor feed (JSON default; CSV / Parquet download)."""
    fmt = (format or "json").lower()
    if fmt != "json":
        if auth.get("source") == "guest":
            raise HTTPException(status_code=401, detail="X-API-Key required for file export")
        if not has_feature(auth, "em_export"):
            raise HTTPException(status_code=403, detail="EM / Data export requires Enterprise")
    from app.services.pit_contract import series_meta_for

    hist = repository.pit_history(company_id)
    detail = repository.get_company_gci(company_id)
    meta = series_meta_for(company_id)
    payload = {
        "factor": "india_gci",
        "contract_version": meta["contract_version"],
        "company_id": company_id,
        "ticker": detail.ticker,
        "point_in_time": hist,
        "asof_gci": detail.gci_score,
        "status": "ok",
        "series_kind": meta["series_kind"],
        "citeable": meta["citeable"],
        "citeable_outcomes": meta["citeable_outcomes"],
        "pit_points": meta["pit_points"],
        "note": meta["note"],
    }
    if fmt == "json":
        return payload

    import csv
    import io

    from fastapi.responses import Response, StreamingResponse

    rows = []
    for p in hist:
        rows.append(
            {
                "factor": "india_gci",
                "contract_version": meta["contract_version"],
                "company_id": company_id,
                "ticker": detail.ticker,
                "as_of": p.as_of,
                "gci_score": p.gci_score,
                "prior_gci": p.prior_gci,
                "change_pct": p.change_pct,
                "change_horizon": p.change_horizon,
                "series_kind": meta["series_kind"],
                "citeable": meta["citeable"],
            }
        )
    if not rows:
        rows.append(
            {
                "factor": "india_gci",
                "contract_version": meta["contract_version"],
                "company_id": company_id,
                "ticker": detail.ticker,
                "as_of": "",
                "gci_score": detail.gci_score,
                "prior_gci": "",
                "change_pct": "",
                "change_horizon": "",
                "series_kind": meta["series_kind"],
                "citeable": meta["citeable"],
            }
        )

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="em_factor_{detail.ticker}.csv"'
            },
        )

    if fmt in ("parquet", "pq"):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            table = pa.Table.from_pylist(rows)
            sink = io.BytesIO()
            pq.write_table(table, sink)
            return Response(
                content=sink.getvalue(),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="em_factor_{detail.ticker}.parquet"'
                },
            )
        except ImportError:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            return StreamingResponse(
                iter([buf.getvalue()]),
                media_type="text/tab-separated-values",
                headers={
                    "Content-Disposition": f'attachment; filename="em_factor_{detail.ticker}.tsv"',
                    "X-Parquet-Fallback": "tsv",
                },
            )

    raise HTTPException(status_code=400, detail="format must be json, csv, or parquet")


# --- Research Terminal (Intellens Search + Intellens Desk, demo) ---


def _reading_room_company(company_id: str) -> bool:
    """A published GCI. Hand-labeled names without a number stay outside the room."""
    from app.data.gci_score_cache import published_gci

    return published_gci(company_id) is not None


def _reading_cookie(response: JSONResponse, browser_id: Optional[str], request: Request) -> JSONResponse:
    if not browser_id:
        return response
    response.set_cookie(
        key="citealpha_reading",
        value=browser_id,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return response


@router.get("/api/research/reading-room")
def research_reading_room(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    citealpha_reading: Optional[str] = Cookie(default=None),
    ent: Dict[str, Any] = Depends(resolve_actor),
) -> Dict[str, Any]:
    """Searches left in this browser. Does not count a search."""
    from app.services.session_auth import READING_ROOM_CAP, extract_bearer, reading_room_status

    if has_feature(ent, "research"):
        return {"limited": False, "blocked": False, "cap": READING_ROOM_CAP, "used": 0, "remaining": None}
    _ = request
    return reading_room_status(extract_bearer(authorization), citealpha_reading)


@router.get("/api/research/search")
def research_search(
    request: Request,
    q: str = "",
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 25,
    expand: bool = False,
    reading_room: bool = False,
    authorization: Optional[str] = Header(default=None),
    citealpha_reading: Optional[str] = Cookie(default=None),
    ent: Dict[str, Any] = Depends(resolve_actor),
) -> Any:
    """Filing search for one company, or all covered companies when company_id is omitted.

    ``expand=true`` adds India IR synonyms (e.g. "EBITDA margin" also finds "operating margin").
    A caller without a research seat always searches one company with a published GCI,
    and this browser is counted toward 8. ``reading_room`` is accepted and not required.
    """
    from app.services.session_auth import consume_reading_search, extract_bearer
    from app.services.sights import expand_query_lexicon

    _ = reading_room
    browser_id = None
    allowance = None
    if not has_feature(ent, "research"):
        if not company_id or not _reading_room_company(company_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "reading_room_scope",
                    "message": "The reading room searches companies with a published GCI. Pick one from the list.",
                },
            )
        allowance, browser_id = consume_reading_search(extract_bearer(authorization), citealpha_reading)
        if allowance.get("blocked"):
            return _reading_cookie(
                JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "reading_room_cap",
                            "message": (
                                "This browser has used its 8 filing searches on companies with a published GCI. "
                                "Request an evaluation for the full Filing Search."
                            ),
                            "cap": allowance.get("cap"),
                            "used": allowance.get("used"),
                        }
                    },
                ),
                browser_id,
                request,
            )
    query = expand_query_lexicon(q) if expand else q
    out = research_svc.search_documents(query, company_id=company_id, doc_type=doc_type, limit=limit)
    if expand:
        out.update(original_query=q, expanded_query=query)
    if allowance is not None:
        out["reading_room"] = allowance
        return _reading_cookie(JSONResponse(content=jsonable_encoder(out)), browser_id, request)
    return out


@router.post("/api/research/chat")
def research_chat(body: ResearchChatRequest, _auth=Depends(require_feature("research_chat"))) -> Dict[str, Any]:
    from app.services.sights import expand_query_lexicon

    question = expand_query_lexicon(body.question) if body.expand else body.question
    return research_svc.research_chat(question, company_id=body.company_id)


@router.get("/api/citations")
def list_citations(
    company_id: str,
    citeable_only: bool = True,
) -> Dict[str, Any]:
    from app.services.citations import list_company_citations

    rows = list_company_citations(company_id, citeable_only=citeable_only)
    return {"company_id": company_id, "count": len(rows), "citations": rows}


@router.get("/api/citations/{citation_id}")
def get_citation(citation_id: str) -> Dict[str, Any]:
    from app.services.citations import lookup_citation

    rec = lookup_citation(citation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Citation not found")
    return rec


@router.get("/api/research/snapshot/{company_id}")
def research_snapshot(company_id: str) -> Dict[str, Any]:
    return research_svc.company_snapshot(company_id)


@router.get("/api/research/estimates/{company_id}")
def research_estimates(company_id: str) -> Dict[str, Any]:
    return research_svc.consensus_estimates(company_id)


@router.get("/api/research/brief/{company_id}")
def research_brief(company_id: str) -> Dict[str, Any]:
    """Pre-earnings promise brief — open guidance + historical hit rate per metric."""
    return research_svc.promise_brief(company_id)


@router.get("/api/research/news")
def research_news(company_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    return research_svc.news_feed(company_id=company_id, limit=limit)


@router.get("/api/research/watchlist")
def research_watchlist(
    ids: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Watchlist tape. Prefer `ids=` query, else session preferences.watchlist, else default."""
    from app.services import session_auth

    company_ids: Optional[List[str]] = None
    if ids:
        company_ids = [x.strip() for x in ids.split(",") if x.strip()]
    else:
        user = session_auth.resolve_token(session_auth.extract_bearer(authorization))
        if user:
            wl = (user.get("preferences") or {}).get("watchlist") or []
            if isinstance(wl, list) and wl:
                company_ids = [str(x) for x in wl]
    return research_svc.watchlist(company_ids=company_ids)


@router.get("/api/research/transcripts")
def research_transcripts(company_id: Optional[str] = None) -> Dict[str, Any]:
    return research_svc.list_transcripts(company_id=company_id)


# --- CiteAlpha Sights (parallel SKU) ---


@router.get("/api/sights/meta")
def sights_meta() -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.sights_meta()


@router.get("/api/sights/search")
def sights_search(
    q: str = "",
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.sights_search(q, company_id=company_id, doc_type=doc_type, limit=limit)


@router.post("/api/sights/ask")
def sights_ask(body: SightsAskRequest, _auth=Depends(require_feature("sights_ask"))) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.sights_ask(
        body.question, company_id=body.company_id, web_assist=body.web_assist
    )


@router.get("/api/sights/themes")
def sights_themes(
    company_id: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 40,
) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.delivery_themes(company_id=company_id, sector=sector, limit=limit)


@router.get("/api/sights/street/{company_id}")
def sights_street(company_id: str) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    try:
        return sights_svc.street_context(company_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found") from None
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/sights/field/{company_id}")
def sights_field(company_id: str) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    try:
        return sights_svc.field_evidence(company_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/sights/grid")
def sights_grid(body: SightsGridRequest) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.compare_grid(body.prompts, company_ids=body.company_ids)


@router.post("/api/sights/deep-dive")
def sights_deep_dive(body: SightsDeepDiveRequest) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.deep_dive(body.topic, company_id=body.company_id)


@router.get("/api/sights/fundamentals/{company_id}")
def sights_fundamentals(company_id: str) -> Dict[str, Any]:
    from app.services import sights as sights_svc

    try:
        return sights_svc.fundamentals_strip(company_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/sights/agents")
def sights_agents() -> JSONResponse:
    return _moved("Desk Agents", "/api/analyst/skills")


@router.post("/api/sights/agents/run")
def sights_agents_run() -> JSONResponse:
    return _moved("Desk Agents", "/api/analyst/run")


@router.get("/api/sights/hooks")
def sights_hooks() -> JSONResponse:
    return _moved("Notify Hooks", "/api/analyst/destinations")


@router.get("/api/sights/export/{company_id}")
def sights_export(company_id: str) -> JSONResponse:
    return _moved("Cite Export", "/api/analyst/runs/{run_id}/export")


@router.get("/api/sights/enterprise")
def sights_enterprise() -> Dict[str, Any]:
    from app.services import sights as sights_svc

    return sights_svc.enterprise_links()


# --- Phase 2–8 APIs ---


@router.post("/api/extract/commit")
def extract_commit(body: CommitExtractRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.data import audit_log

    result = repository.commit_pending_extract(
        body.extract_id,
        body.accepted_indices,
        edits=body.edits,
        reviewer=auth.get("org", "queue"),
    )
    audit_log.record(
        "extract_commit",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail=result,
    )
    return result


@router.get("/api/extract/pending")
def extract_pending(company_id: Optional[str] = None, _auth=Depends(require_feature("desk"))) -> Dict[str, Any]:
    rows = repository.list_pending_extracts(company_id)
    return {"count": len(rows), "batches": rows}


@router.post("/api/ingest/paste")
def ingest_paste(body: IngestPasteRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.data import audit_log
    from app.services import ingest

    doc = ingest.ingest_paste(body.company_id, body.text, title=body.title, doc_type=body.doc_type)
    extract_batch = None
    if (body.text or "").strip():
        statements = extract_auto(body.text, company_id=body.company_id, period="FY26")
        if statements:
            extract_batch = repository.save_pending_extract(body.company_id, statements)
    audit_log.record(
        "ingest_paste",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"doc_id": doc["doc_id"], "extract_id": (extract_batch or {}).get("id")},
    )
    return {
        "ok": True,
        "document": doc,
        "extract": extract_batch,
        "note": "Document stored pending review; extract candidates queued when quantified guidance found.",
    }


@router.post("/api/ingest/text")
def ingest_text(body: IngestPasteRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.services import ingest

    doc = ingest.ingest_plain_text(body.company_id, body.text, title=body.title, doc_type=body.doc_type)
    extract_batch = None
    if (body.text or "").strip():
        statements = extract_auto(body.text, company_id=body.company_id, period="FY26")
        if statements:
            extract_batch = repository.save_pending_extract(body.company_id, statements)
    return {"ok": True, "document": doc, "extract": extract_batch}


@router.post("/api/ingest/url")
def ingest_url(body: IngestUrlRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.services import ingest

    try:
        doc = ingest.ingest_html_url(body.company_id, body.url, title=body.title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}") from e
    extract_batch = None
    text = (doc.get("text") or doc.get("content") or "").strip()
    if text:
        statements = extract_auto(text, company_id=body.company_id, period="FY26")
        if statements:
            extract_batch = repository.save_pending_extract(body.company_id, statements)
    return {"ok": True, "document": doc, "extract": extract_batch}


@router.post("/api/ingest/bootstrap")
def ingest_bootstrap(_auth=Depends(require_feature("desk_write")), limit: int = 10) -> Dict[str, Any]:
    from app.services import ingest

    n = ingest.bootstrap_top_companies(limit=limit)
    return {"ok": True, "companies_with_docs": n}


@router.post("/api/ingest/ensure-citations")
def ingest_ensure_citations(
    limit: Optional[int] = None,
    company_id: Optional[str] = None,
    auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    """Tier 1 gate helper: bind hand_labeled outcomes → accepted period docs + spans.

    Also builds the demo_pit_extension warehouse (≥12 quarters) for Tier 2/3 analytics.
    """
    from app.data import audit_log
    from app.services.citation_corpus import (
        ensure_company_citation_corpus,
        ensure_sensex_citation_corpus,
    )
    from app.services.pit_warehouse import ensure_pit_series, ensure_sensex_pit_warehouse

    if company_id:
        report = ensure_company_citation_corpus(company_id)
        pit = ensure_pit_series(company_id)
        report["pit"] = {"n": pit.get("n"), "series_kind": pit.get("series_kind")}
    else:
        report = ensure_sensex_citation_corpus(limit=limit)
        pit = ensure_sensex_pit_warehouse(limit=limit)
        report["pit"] = pit
    audit_log.record(
        "ensure_citations",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"company_id": company_id, "limit": limit, "linked": report.get("linked")},
    )
    return report


@router.post("/api/ingest/universe-gci-depth")
def ingest_universe_gci_depth(
    limit: Optional[int] = None,
    skip_cache: bool = False,
    skip_citations: bool = False,
    auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    """Rebuild Sensex citations + India listing GCI with WoW/MoM/QoQ/YoY horizons."""
    from app.data import audit_log
    from app.jobs.build_universe_gci_depth import main as depth_main
    import io
    from contextlib import redirect_stdout

    argv: List[str] = []
    if limit is not None:
        argv.extend(["--limit", str(limit)])
    if skip_cache:
        argv.append("--skip-cache")
    if skip_citations:
        argv.append("--skip-citations")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = depth_main(argv)
    raw = buf.getvalue()
    try:
        report = json.loads(raw) if raw.strip() else {"ok": code == 0}
    except json.JSONDecodeError:
        report = {"ok": code == 0, "raw": raw}
    audit_log.record(
        "universe_gci_depth",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"limit": limit, "ok": report.get("ok")},
    )
    return report


@router.post("/api/ingest/tier-foundation")
def ingest_tier_foundation(
    limit: Optional[int] = None,
    auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    """One-shot: Sensex citation corpus + PIT warehouse for Tier 1–3 demos."""
    from app.data import audit_log
    from app.services.citation_corpus import ensure_sensex_citation_corpus
    from app.services.pit_warehouse import ensure_sensex_pit_warehouse

    cites = ensure_sensex_citation_corpus(limit=limit)
    pit = ensure_sensex_pit_warehouse(limit=limit)
    audit_log.record(
        "tier_foundation",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"cites": cites.get("companies"), "pit": pit.get("companies")},
    )
    return {"ok": True, "citations": cites, "pit_warehouse": pit}


@router.post("/api/ingest/crawl")
def ingest_crawl(body: CrawlRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    """On-demand / scheduled Sensex IR crawl → pending docs for review."""
    from app.data import audit_log
    from app.services.crawl import run_sensex_ir_crawl

    report = run_sensex_ir_crawl(
        limit=body.limit,
        dry_run=body.dry_run,
        live=body.live,
        company_ids=body.company_ids,
    )
    if not body.dry_run:
        audit_log.record(
            "ingest_crawl",
            org=auth.get("org", "demo"),
            actor=auth.get("key", "unknown"),
            role=auth.get("role", "analyst"),
            detail={
                "live": body.live,
                "targets": report.get("targets"),
                "pending_new": report.get("pending_new"),
                "failed": report.get("failed"),
            },
        )
    return report


@router.get("/api/ingest/crawl/status")
def ingest_crawl_status(_auth=Depends(require_feature("desk"))) -> Dict[str, Any]:
    from app.services.crawl import load_state, pending_document_counts
    from app.services.refresh import refresh_interval_hours

    state = load_state()
    pending = pending_document_counts()
    return {
        "last": state.get("last"),
        "last_refresh": state.get("last_refresh"),
        "runs": state.get("runs", [])[-10:],
        "pending_total": sum(pending.values()),
        "pending_by_company": pending,
        "schedule": {
            "interval_hours": refresh_interval_hours(),
            "crawl_live_default": True,
            "note": "Compose service `scheduler` or cron every 6h; POST /api/ingest/refresh",
        },
    }


@router.post("/api/ingest/refresh")
def ingest_refresh(body: RefreshRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    """Scheduled/on-demand live refresh: IR crawl + extract queue (+ optional FMP warm)."""
    from app.data import audit_log
    from app.services.refresh import run_gci_refresh

    report = run_gci_refresh(
        limit=body.limit,
        live=body.live,
        auto_extract=body.auto_extract,
        warm_fmp=body.warm_fmp,
    )
    audit_log.record(
        "ingest_refresh",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={
            "live": report.get("live"),
            "pending_new": (report.get("crawl") or {}).get("pending_new"),
            "extract_batches": (report.get("extract") or {}).get("batches"),
        },
    )
    return report


@router.post("/api/ingest/media")
def ingest_media(body: IngestMediaRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    """Audio/video stub — GCI scores from ASR transcript text only, never raw AV."""
    from app.data import audit_log

    mt = (body.media_type or "").strip().lower()
    if mt not in ("audio", "video"):
        raise HTTPException(status_code=400, detail="media_type must be audio or video")
    audit_log.record(
        "ingest_media_stub",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"company_id": body.company_id, "media_type": mt},
    )
    return {
        "status": "accepted_stub",
        "company_id": body.company_id,
        "media_type": mt,
        "title": body.title,
        "note": body.note,
        "next": "provide ASR transcript via /api/ingest/text",
        "scored_from": "transcript_only",
        "disallowed": ["audio_raw", "video_raw", "tone_scoring"],
    }


@router.get("/api/metrics")
def metrics_list(sector: Optional[str] = None) -> Dict[str, Any]:
    from collections import Counter

    from app.data.metric_catalog import list_metrics
    from app.data.seed import get_outcomes, list_companies

    counts: Counter = Counter()
    for c in list_companies():
        for o in get_outcomes(c["id"]):
            counts[o.metric] += 1
    rows = []
    for m in list_metrics(sector=sector):
        rows.append({**m, "outcome_count": counts.get(m["id"], 0)})
    return {"count": len(rows), "metrics": rows}


@router.get("/api/metrics/{metric_id}")
def metrics_detail(metric_id: str) -> Dict[str, Any]:
    from app.data.metric_catalog import get_metric, normalize_metric
    from app.data.seed import get_outcomes, list_companies

    nid = normalize_metric(metric_id) or metric_id
    m = get_metric(nid)
    if m is None:
        raise HTTPException(status_code=404, detail="Metric not in catalog")
    n = 0
    companies = set()
    for c in list_companies():
        for o in get_outcomes(c["id"]):
            if o.metric == nid:
                n += 1
                companies.add(c["id"])
    return {**m, "outcome_count": n, "company_count": len(companies)}


@router.post("/api/actuals/import")
def actuals_import(body: ActualsImportRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    """Import reported actuals to match guidance — not a fundamentals score."""
    from app.data import audit_log
    from app.data.metric_catalog import require_metric
    from app.data.seed import get_data, save_data

    data = get_data()
    merged = 0
    errors = []
    for i, row in enumerate(body.rows):
        try:
            company_id = row["company_id"]
            period = row["period"]
            metric = require_metric(row.get("metric"), allow_custom=body.allow_custom)
            actual = float(row["actual_value"])
        except (KeyError, TypeError, ValueError) as e:
            errors.append({"index": i, "error": str(e)})
            continue
        outs = data.setdefault("outcomes", {}).setdefault(company_id, [])
        hit = False
        for o in outs:
            if o.get("period") == period and o.get("metric") == metric:
                o["actual_value"] = actual
                if row.get("source_ref"):
                    o["source_ref"] = row["source_ref"]
                hit = True
                merged += 1
                break
        if not hit:
            # store as pending-style actual-only row is skipped — actuals need a guidance row
            errors.append(
                {
                    "index": i,
                    "error": f"No guidance outcome for {company_id}/{period}/{metric} to attach actual",
                }
            )
    save_data(data)
    audit_log.record(
        "actuals_import",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"merged": merged, "errors": len(errors)},
    )
    return {
        "ok": True,
        "merged": merged,
        "errors": errors,
        "note": "Fundamentals/reported numbers fill actual_value only — not a parallel GCI",
    }


@router.post("/api/documents/review")
def documents_review(body: DocReviewRequest, auth=Depends(require_feature("desk_write"))) -> Dict[str, Any]:
    from app.data import audit_log, doc_store

    status = "accepted" if body.action == "accept" else "rejected"
    try:
        doc = doc_store.set_review_status(body.doc_id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    audit_log.record(
        "doc_review",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={"doc_id": body.doc_id, "status": status},
    )
    return {"ok": True, "document": doc}


@router.get("/api/documents/undated")
def documents_undated(company_id: Optional[str] = None) -> Dict[str, Any]:
    from app.services.document_dating import undated_documents

    rows = undated_documents(company_id)
    return {"count": len(rows), "documents": rows}


@router.post("/api/documents/{doc_id}/date")
def documents_date(
    doc_id: str, body: DocDateRequest, auth=Depends(require_feature("desk_write"))
) -> Dict[str, Any]:
    from app.data import audit_log
    from app.services.document_dating import date_document

    try:
        out = date_document(
            doc_id, as_of=body.as_of, evidence=body.evidence, basis=body.basis, reviewer=body.reviewer
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    audit_log.record(
        "doc_dated",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "analyst"),
        detail={**out, "basis": body.basis, "evidence": body.evidence[:300], "reviewer": body.reviewer},
    )
    return {"ok": True, **out}


@router.get("/api/filings/recent")
def filings_recent(limit: int = 8) -> Dict[str, Any]:
    """Newest stored filings for the public homepage. Metadata only — no filing text."""
    from app.data import doc_store
    from app.data.india_listings import find_listing
    from app.data.seed import list_companies
    from app.data.us_listings import find_us_listing

    names = {c["id"]: c for c in list_companies()}
    rows = []
    for doc in doc_store.recent_filings(limit):
        company_id = doc.get("company_id") or ""
        company = names.get(company_id) or find_listing(company_id) or find_us_listing(company_id) or {}
        rows.append(
            {
                "doc_id": doc.get("doc_id"),
                "company_id": company_id,
                "name": company.get("name"),
                "ticker": company.get("ticker"),
                "doc_type": doc.get("doc_type"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "date": doc.get("date"),
                "source_type": doc.get("source_type"),
            }
        )
    return {"count": len(rows), "filings": rows}


@router.get("/api/documents")
def documents_list(
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    review_status: Optional[str] = None,
) -> Dict[str, Any]:
    from app.data import doc_store

    rows = doc_store.list_documents(company_id=company_id, doc_type=doc_type)
    if review_status:
        rows = [d for d in rows if d.get("review_status") == review_status]
    return {"count": len(rows), "documents": rows}


@router.get("/api/documents/{doc_id}")
def document_get(doc_id: str) -> Dict[str, Any]:
    """Indexed filing/transcript text for in-app highlight."""
    from app.data import doc_store

    if not doc_store.list_documents():
        doc_store.seed_from_outcomes_and_transcripts()
    doc = doc_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    text = doc.get("text") or ""
    return {
        "doc_id": doc.get("doc_id"),
        "company_id": doc.get("company_id"),
        "doc_type": doc.get("doc_type"),
        "title": doc.get("title"),
        "text": text,
        "url": doc.get("url"),
        "date": doc.get("date"),
        "source": doc.get("source"),
        "period": doc.get("period"),
        "review_status": doc.get("review_status"),
    }


@router.post("/api/consensus/import")
def consensus_import(
    body: ConsensusImportRequest,
    demo: bool = False,
    auth=Depends(require_feature("desk_write")),
) -> Dict[str, Any]:
    from app.data import audit_log, consensus_store
    from app.services.feature_flags import allow_demo_street, consensus_import_enabled

    if not consensus_import_enabled():
        raise HTTPException(status_code=404, detail="CONSENSUS_IMPORT disabled")
    rows = list(body.rows or [])
    has_sample = any(
        str(r.get("source") or "").startswith("sample")
        or str(r.get("source") or "") == "sample_import"
        for r in rows
    )
    if has_sample and not (demo or allow_demo_street()):
        raise HTTPException(
            status_code=400,
            detail=(
                "sample_import rows require ?demo=true or ALLOW_DEMO_STREET=true "
                "(synthetic street — not licensed consensus)"
            ),
        )
    n = consensus_store.import_rows(rows)
    audit_log.record(
        "consensus_import",
        org=auth.get("org", "demo"),
        actor=auth.get("key", "unknown"),
        role=auth.get("role", "admin"),
        detail={"count": n, "demo": bool(demo or has_sample)},
    )
    return {"ok": True, "imported": n, "demo": bool(demo or has_sample)}


@router.get("/api/consensus/stats")
def consensus_stats(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.data import consensus_store

    return consensus_store.stats()


@router.get("/api/consensus/sample")
def consensus_sample(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    """Synthetic street fixture for pilot demos — not licensed consensus."""
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "data" / "consensus_import_sample.json"
    rows = json.loads(path.read_text()) if path.exists() else []
    return {
        "rows": rows,
        "note": "sample_import — require ?demo=true on POST /api/consensus/import",
    }


@router.get("/api/audit")
def audit_list(
    org: Optional[str] = None,
    limit: int = 100,
    auth=Depends(require_session_or_key),
) -> Dict[str, Any]:
    from app.data import audit_log

    if auth.get("role") not in ("owner", "admin", "reviewer", "analyst"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    caller = str(auth.get("org_id") or auth.get("org") or "")
    cross_org = str(auth.get("platform_admin_role") or "") == "super"
    if org and org != caller and not cross_org:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if not cross_org:
        org = caller
    rows = audit_log.public_events(org=org or caller, limit=min(max(limit, 1), 200))
    return {"count": len(rows), "events": rows}


@router.get("/api/analytics/events")
def analytics_events(limit: int = 50, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.analytics import recent_events

    if not auth.get("platform_admin_role"):
        raise HTTPException(status_code=403, detail="Platform operator required")
    return {"events": recent_events(limit)}


@router.get("/api/auth/sso/status")
def auth_sso_status() -> Dict[str, Any]:
    from app.services.rbac import sso_status

    st = sso_status()
    ready = bool(st.get("production_ready") or (st.get("enabled") and st.get("configured")))
    return {
        **st,
        "coming_soon": not st.get("enabled"),
        "ready": ready,
        "modes": ["register", "login", "guest", "api_key", "sso"],
    }


@router.get("/api/auth/sso/login")
def auth_sso_login(org_id: Optional[str] = None) -> Dict[str, Any]:
    from app.services.rbac import sso_login_stub

    return sso_login_stub(org_id=org_id)


@router.get("/api/auth/sso/callback")
def auth_sso_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    format: Optional[str] = None,
):
    """OIDC callback — JSON for API clients; HTML bridge for browser IdP redirects."""
    from fastapi.responses import HTMLResponse, JSONResponse

    from app.services import sso as sso_svc

    result = sso_svc.sso_callback(code=code, state=state, email=email, name=name)
    accept = (request.headers.get("accept") or "").lower()
    want_json = (format or "").lower() == "json" or (
        "application/json" in accept and "text/html" not in accept
    )
    if want_json:
        return JSONResponse(result)
    token = result.get("token") or ""
    front = (os.environ.get("OIDC_FRONTEND_REDIRECT") or "/").strip() or "/"
    # Escape for inline script
    safe_token = token.replace("\\", "\\\\").replace("'", "\\'")
    safe_front = front.replace("\\", "\\\\").replace("'", "\\'")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>SSO</title></head>
<body><p>Completing sign-in…</p>
<script>
try {{ localStorage.setItem('intellens.auth.token', '{safe_token}'); }} catch (e) {{}}
window.location.replace('{safe_front}');
</script></body></html>"""
    return HTMLResponse(html)


def _labeling_queue_scope(
    auth: Dict[str, Any],
    requested_org: Optional[str],
    authorization: Optional[str],
    x_api_key: Optional[str],
) -> Optional[str]:
    """Org the caller may act on; None means all orgs (platform admins only)."""
    from app.services import admin_portal

    if admin_portal.platform_actor_or_none(authorization, x_api_key):
        return requested_org or None
    own = str(auth.get("org_id") or auth.get("org") or "")
    if not own:
        raise HTTPException(status_code=403, detail="Organization required")
    if requested_org and requested_org != own:
        raise HTTPException(status_code=403, detail="Org mismatch")
    return own


@router.get("/api/labeling/queue")
def labeling_queue_list(
    org_id: Optional[str] = None,
    auth=Depends(require_feature("desk")),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import labeling_queue as lq

    scope = _labeling_queue_scope(auth, org_id, authorization, x_api_key)
    items = lq.list_queue(org_id=scope)
    return {"items": items, "count": len(items)}


@router.post("/api/labeling/queue")
def labeling_queue_enqueue(
    body: Dict[str, Any],
    auth=Depends(require_feature("desk")),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import labeling_queue as lq

    company_id = body.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    requested = str(body["org_id"]) if body.get("org_id") else None
    scope = _labeling_queue_scope(auth, requested, authorization, x_api_key)
    item = lq.enqueue(
        company_id=str(company_id),
        org_id=scope or str(auth.get("org_id") or auth.get("org") or "demo"),
        priority=str(body.get("priority") or "normal"),
        note=str(body.get("note") or ""),
        requested_by=str(auth.get("org") or "api"),
    )
    return {"ok": True, "item": item}


@router.patch("/api/labeling/queue/{item_id}")
def labeling_queue_patch(
    item_id: str,
    body: Dict[str, Any],
    auth=Depends(require_feature("desk")),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import labeling_queue as lq

    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status required")
    scope = _labeling_queue_scope(auth, None, authorization, x_api_key)
    return {"ok": True, "item": lq.update_status(item_id, str(status), org_id=scope)}


@router.get("/api/labeling/companies")
def labeling_queue_companies(
    limit: int = 40, _auth=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    rows = lbl.queue_companies(limit=limit)
    return {"count": len(rows), "companies": rows}


@router.get("/api/labeling/drafts")
def labeling_list_drafts(
    company_id: Optional[str] = None,
    status: Optional[str] = None,
    auth=Depends(require_feature("labeling")),
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    rows = lbl.list_drafts(
        org_id=auth.get("org_id") or auth.get("org"),
        company_id=company_id,
        status=status,
    )
    return {"count": len(rows), "drafts": rows}


@router.post("/api/labeling/drafts")
def labeling_create_draft(
    body: LabelDraftRequest, auth=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    row = lbl.create_draft(body=body.model_dump(), actor=auth)
    return {"ok": True, "draft": row}


@router.post("/api/labeling/drafts/{draft_id}/submit")
def labeling_submit_draft(
    draft_id: str, auth=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    return {"ok": True, "draft": lbl.submit_draft(draft_id, actor=auth)}


@router.post("/api/labeling/drafts/{draft_id}/accept")
def labeling_accept_draft(
    draft_id: str, auth=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    return {"ok": True, "draft": lbl.accept_draft(draft_id, actor=auth)}


@router.post("/api/labeling/drafts/{draft_id}/reject")
def labeling_reject_draft(
    draft_id: str,
    body: LabelRejectRequest,
    auth=Depends(require_feature("labeling")),
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    return {"ok": True, "draft": lbl.reject_draft(draft_id, actor=auth, comment=body.comment)}


@router.post("/api/labeling/import")
def labeling_import_csv(
    body: LabelImportRequest, auth=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.services import labeling as lbl

    return lbl.import_csv(body.csv, actor=auth)


@router.get("/api/feedback")
def feedback_list(
    status: Optional[str] = None, auth=Depends(require_feature("feedback"))
) -> Dict[str, Any]:
    from app.services import feedback as fb

    rows = fb.list_feedback(org_id=auth.get("org_id") or auth.get("org"), status=status)
    return {"count": len(rows), "items": rows}


@router.post("/api/feedback")
def feedback_create(
    body: FeedbackCreate, auth=Depends(require_feature("feedback"))
) -> Dict[str, Any]:
    from app.services import feedback as fb

    row = fb.create(
        company_id=body.company_id or "",
        kind=body.kind,
        comment=body.comment,
        period=body.period,
        metric=body.metric,
        nps=body.nps,
        actor=auth,
    )
    return {"ok": True, "item": row}


@router.patch("/api/feedback/{item_id}")
def feedback_patch(
    item_id: str, body: Dict[str, Any], _auth=Depends(require_feature("feedback"))
) -> Dict[str, Any]:
    from app.services import feedback as fb

    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status required")
    return {"ok": True, "item": fb.set_status(item_id, str(status))}


@router.post("/api/activity/cite-copy")
def activity_cite_copy(
    body: Dict[str, Any] = Body(default={}),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Dict[str, Any]:
    """Habit ping when an analyst copies a citation. Does not store quote text."""
    from app.services import activity as activity_svc
    from app.services import session_auth

    token = session_auth.extract_bearer(authorization)
    if token:
        return session_auth.record_cite_copy(token, company_id=(body or {}).get("company_id"))
    if x_api_key:
        from app.data.seed import get_data as _gd

        for row in _gd().get("api_keys") or []:
            if row.get("key") == x_api_key:
                counts = activity_svc.bump(str(row.get("org") or row.get("org_id") or ""), "cite_copies")
                return {"ok": True, "citations_copied": counts.get("cite_copies") or 0}
        raise HTTPException(status_code=403, detail="Invalid API key")
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("/api/auth/register")
def auth_register(body: AuthRegisterRequest) -> Dict[str, Any]:
    from app.services import abuse
    from app.services import session_auth

    if body.org_id:
        raise HTTPException(
            status_code=403,
            detail="Joining an existing organization requires an invite link",
        )
    abuse.verify_challenge(body.challenge_id or "", body.challenge_answer or "")
    return session_auth.register(
        body.email,
        body.password,
        body.name,
        merge_preferences=body.preferences,
        guest_token=body.guest_token,
        accept_terms=body.accept_terms,
        account_type=body.account_type,
        org_name=body.org_name,
    )


@router.post("/api/auth/login")
def auth_login(body: AuthLoginRequest) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.login(body.email, body.password, totp_code=body.totp_code)


@router.post("/api/auth/guest")
def auth_guest(body: AuthGuestRequest) -> Dict[str, Any]:
    from app.services import abuse
    from app.services import session_auth

    abuse.verify_challenge(body.challenge_id or "", body.challenge_answer or "")
    return session_auth.create_guest(accept_terms=body.accept_terms)


@router.get("/api/auth/abuse-challenge")
def auth_abuse_challenge() -> Dict[str, Any]:
    from app.services import abuse

    return abuse.issue_challenge()


@router.post("/api/pilot-request")
def pilot_request(body: PilotRequestCreate) -> Dict[str, Any]:
    from app.services import abuse
    from app.services import pilot_request as pilot_svc

    abuse.verify_challenge(body.challenge_id or "", body.challenge_answer or "")
    row = pilot_svc.create_request(
        name=body.name,
        email=body.email,
        firm=body.firm,
        role=body.role,
        team_size=body.team_size,
        message=body.message,
    )
    return {
        "ok": True,
        "request_id": row["id"],
        "status": row["status"],
        "submitted_at": row["created_at"],
    }


@router.post("/api/auth/verify-email/request")
def auth_verify_request(body: AuthEmailRequest) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.request_email_verification(body.email)


@router.post("/api/auth/verify-email/confirm")
def auth_verify_confirm(body: AuthVerifyConfirm) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.confirm_email_verification(body.token)


@router.post("/api/auth/password-reset/request")
def auth_reset_request(body: AuthEmailRequest) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.request_password_reset(body.email)


@router.post("/api/auth/password-reset/confirm")
def auth_reset_confirm(body: AuthPasswordResetConfirm) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.confirm_password_reset(body.token, body.password)


@router.post("/api/auth/accept-invite")
def auth_accept_invite(body: AcceptInviteRequest) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.accept_org_invite(
        invite_token=body.token,
        password=body.password,
        name=body.name,
        accept_terms=body.accept_terms,
    )


@router.get("/api/orgs/{org_id}/members")
def org_members(
    org_id: str, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    from app.services import session_auth

    from app.services.admin_portal import effective_platform_role

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    platform_role = effective_platform_role(user.get("email"), user.get("platform_admin_role"))
    if user.get("org_id") != org_id and platform_role != "super":
        raise HTTPException(status_code=403, detail="Org mismatch")
    return {"org_id": org_id, "members": session_auth.list_org_members(org_id)}


@router.post("/api/orgs/{org_id}/invites")
def org_invite(
    org_id: str,
    body: OrgInviteRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("org_id") != org_id or user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    return org_svc.create_invite(
        org_id=org_id,
        email=body.email,
        invited_by=user["id"],
        role=body.role,
        actor_role=str(user.get("role") or ""),
    )


@router.post("/api/orgs/{org_id}/partner-invite")
def org_partner_invite(
    org_id: str,
    body: OrgInviteRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("org_id") != org_id or user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    return org_svc.create_partner_invite(
        org_id=org_id, email=body.email, invited_by=user["id"]
    )


@router.post("/api/orgs/{org_id}/members/{user_id}/role")
def org_member_role(
    org_id: str,
    user_id: str,
    body: MemberRoleRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    return session_auth.set_member_role(
        org_id=org_id, user_id=user_id, role=body.role, actor=user
    )


@router.post("/api/orgs/{org_id}/revoke")
def org_revoke(
    org_id: str,
    body: OrgRevokeRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    return session_auth.revoke_org_member(
        org_id=org_id, user_id=body.user_id, actor=user
    )


@router.post("/api/orgs/{org_id}/api-keys")
def org_mint_key(
    org_id: str, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("org_id") != org_id or user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    return org_svc.mint_api_key(org_id=org_id)


@router.put("/api/orgs/{org_id}/oidc")
def org_oidc(
    org_id: str,
    body: OrgOidcRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("org_id") != org_id or user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    return org_svc.set_org_oidc(
        org_id,
        oidc_issuer=body.oidc_issuer,
        oidc_client_id=body.oidc_client_id,
        email_domain=body.email_domain,
    )


@router.get("/api/infra/postgres")
def infra_postgres() -> Dict[str, Any]:
    from app.db.auth_db import backend_name, use_db_auth
    from app.db.postgres import postgres_status

    st = postgres_status()
    st["db_auth"] = use_db_auth()
    st["auth_backend"] = backend_name()
    return st


@router.post("/api/infra/db/migrate")
def infra_db_migrate(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    """Apply SQL auth schema (SQLite or Postgres). Admin/demo key."""
    from app.db.auth_db import apply_schema, backend_name

    if not _auth.get("platform_admin_role"):
        raise HTTPException(status_code=403, detail="Platform operator required")
    return {**apply_schema(), "backend": backend_name()}


@router.post("/api/legal/attest")
def legal_attest(body: LegalAttestRequest, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services import legal_attest as la

    return la.attest(
        kind=body.kind,
        attested_by=body.attested_by,
        note=body.note,
        admin_key_ok=bool(auth.get("platform_admin_role")),
    )


@router.get("/api/legal/attestations")
def legal_attestations() -> Dict[str, Any]:
    from app.services import legal_attest as la

    return la.snapshot()


@router.post("/api/billing/msa")
def billing_msa(
    body: MsaInvoiceRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    from app.services import billing
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    oid = user.get("org_id")
    if not oid:
        raise HTTPException(status_code=400, detail="No org on session")
    if body.from_pilot or (body.conversion_path or "") == "pilot_to_desk":
        return billing.create_msa_from_pilot(
            org_id=str(oid),
            seats=body.seats,
            signer_hint=str(user.get("email") or ""),
        )
    return billing.create_msa_invoice(
        org_id=str(oid),
        plan=body.plan,
        seats=body.seats,
        amount_inr=body.amount_inr,
        po_number=body.po_number,
    )


@router.post("/api/billing/msa/{invoice_id}/sign")
def billing_msa_sign(
    invoice_id: str,
    body: MsaSignRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import billing
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")
    oid = user.get("org_id")
    if not oid:
        raise HTTPException(status_code=400, detail="No org on session")
    return billing.sign_msa(invoice_id, signer_email=body.signer_email, org_id=str(oid))


@router.post("/api/billing/retail/checkout")
def billing_retail_checkout(
    body: RetailCheckoutRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import billing
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    oid = user.get("org_id")
    if not oid:
        raise HTTPException(status_code=400, detail="Register a retail account first")
    return billing.create_retail_checkout(org_id=str(oid), user_email=str(user.get("email") or ""))


@router.post("/api/billing/retail/confirm")
def billing_retail_confirm(
    body: RetailPayConfirm, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    from app.services import billing
    from app.services import session_auth

    session_auth.require_session(session_auth.extract_bearer(authorization))
    return billing.confirm_retail_payment(body.order_id, payment_ref=body.payment_ref)


@router.get("/api/billing/invoices")
def billing_invoices(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    from app.services import billing
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    oid = user.get("org_id")
    if not oid:
        return {"invoices": [], "subscription": None}
    return {
        "invoices": billing.list_invoices(str(oid)),
        "subscription": billing.subscription_for(str(oid)),
    }


@router.post("/api/auth/mfa/enroll")
def auth_mfa_enroll(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.mfa_enroll_start(session_auth.extract_bearer(authorization))


@router.post("/api/auth/mfa/confirm")
def auth_mfa_confirm(
    body: AuthMfaConfirmRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.mfa_enroll_confirm(session_auth.extract_bearer(authorization), body.code)


@router.post("/api/auth/mfa/disable")
def auth_mfa_disable(
    body: AuthMfaConfirmRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    return session_auth.mfa_disable(session_auth.extract_bearer(authorization), body.code)


@router.post("/api/auth/logout")
def auth_logout(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    from app.services import session_auth

    token = session_auth.extract_bearer(authorization)
    return session_auth.logout(token)


@router.get("/api/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services import session_auth

    user = session_auth.require_session(session_auth.extract_bearer(authorization))
    payload: Dict[str, Any] = {"user": user}
    if user.get("org_id"):
        try:
            payload["org"] = org_svc.org_snapshot(str(user["org_id"]))
        except HTTPException:
            payload["org"] = None
    return payload


@router.get("/api/auth/preferences")
def auth_get_preferences(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    prefs = session_auth.get_preferences(session_auth.extract_bearer(authorization))
    return {"preferences": prefs}


@router.put("/api/auth/preferences")
def auth_put_preferences(
    body: PreferencesUpdate,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    from app.services import session_auth

    patch = body.model_dump(exclude_none=True)
    prefs = session_auth.update_preferences(
        session_auth.extract_bearer(authorization), patch
    )
    return {"preferences": prefs}


@router.get("/api/universe/nifty")
def universe_nifty() -> Dict[str, Any]:
    from app.data.universe import NIFTY_EXTRA, SENSEX_30
    from app.services.nifty_milestones import milestones_payload

    return {
        "sensex_count": len(SENSEX_30),
        "nifty_extra": [
            {"id": a, "name": b, "ticker": c, "sector": d} for a, b, c, d in NIFTY_EXTRA
        ],
        "milestones": milestones_payload(),
        "note": (
            "Nifty scaffolding only — deep hand_labeled GCI remains Sensex pilot. "
            "Do not treat Nifty rows as day-1 GCI depth."
        ),
    }


@router.get("/api/universe/nifty/milestones")
def nifty_milestones() -> Dict[str, Any]:
    from app.services.nifty_milestones import milestones_payload

    return milestones_payload()


@router.post("/api/universe/nifty/enqueue-labeling")
def nifty_enqueue_labeling(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.nifty_milestones import ensure_nifty_labeling_queue

    return ensure_nifty_labeling_queue(org_id=_auth.get("org") or "demo")


@router.get("/api/csm/{org_id}")
def csm_dashboard(org_id: str, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.csm_sla import csm_dashboard as dash

    from app.services import orgs as org_svc

    org_svc.assert_org_access(auth, org_id)
    return dash(org_id)


@router.get("/api/sla/{org_id}")
def sla_for_org(org_id: str, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.csm_sla import sla_status

    from app.services import orgs as org_svc

    org_svc.assert_org_access(auth, org_id)
    return sla_status(org_id)


@router.post("/api/csm/{org_id}/tickets")
def csm_ticket(org_id: str, body: Dict[str, Any], auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.csm_sla import create_ticket

    from app.services import orgs as org_svc

    org_svc.assert_org_access(auth, org_id)
    ticket = create_ticket(
        org_id=org_id,
        subject=str(body.get("subject") or ""),
        severity=str(body.get("severity") or "3"),
        body=str(body.get("body") or ""),
        requested_by=str(auth.get("org") or "api"),
    )
    return {"ok": True, "ticket": ticket}


@router.get("/api/vpc/posture")
def vpc_posture() -> Dict[str, Any]:
    from app.services.csm_sla import vpc_posture as posture

    return posture()


@router.get("/api/markets")
def markets_list() -> Dict[str, Any]:
    from app.data import markets as markets_data

    rows = markets_data.list_markets()
    return {
        "count": len(rows),
        "markets": rows,
        "gci_deep_markets": markets_data.GCI_DEEP_MARKETS,
        "note": markets_data.markets_meta()["scaffold_note"],
    }


@router.get("/api/markets/{market_id}/indexes")
def market_indexes(market_id: str) -> Dict[str, Any]:
    from app.data import markets as markets_data

    if markets_data.get_market(market_id) is None:
        raise HTTPException(status_code=404, detail="Market not found")
    rows = markets_data.list_indexes(market_id)
    return {
        "market_id": market_id.upper(),
        "count": len(rows),
        "indexes": rows,
        "gci_deep": market_id.upper() in markets_data.GCI_DEEP_MARKETS,
    }


@router.get("/api/indexes/{index_id}/constituents")
def index_constituents(
    index_id: str, limit: Optional[int] = None, offset: int = 0
) -> Dict[str, Any]:
    from app.data import markets as markets_data

    ix = markets_data.get_index(index_id)
    if ix is None:
        raise HTTPException(status_code=404, detail="Index not found")
    rows = markets_data.list_constituents(index_id)
    total = len(rows)
    if offset:
        rows = rows[offset:]
    if limit is not None and limit > 0:
        rows = rows[:limit]
    return {
        "index": ix,
        "count": total,
        "returned": len(rows),
        "offset": offset,
        "constituents": rows,
        "gci_deep": ix["market_id"] in markets_data.GCI_DEEP_MARKETS
        and index_id.upper() == "SENSEX",
    }


@router.get("/api/markets/{market_id}/history")
def market_history(
    market_id: str, index: Optional[str] = None, years: int = 5
) -> Dict[str, Any]:
    from app.data.market_history import get_market_history

    row = get_market_history(market_id, index_id=index, years=years)
    if row is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return row


@router.get("/api/indexes/{index_id}/history")
def index_history(index_id: str, years: int = 5) -> Dict[str, Any]:
    from app.data.market_history import get_index_history

    row = get_index_history(index_id, years=years)
    if row is None:
        raise HTTPException(status_code=404, detail="Index not found")
    return row


@router.get("/api/stocks/{stock_id}/history")
def stock_history(
    stock_id: str, years: int = 5, auth=Depends(require_feature("analytics_experimental"))
) -> Dict[str, Any]:
    """Price tape (demo unless a market-data key is configured). Workbench-only."""
    from app.data.market_history import get_stock_history

    row = get_stock_history(stock_id, years=years)
    if row is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return row


@router.get("/api/sectors/{sector}/benchmark")
def sector_benchmark(sector: str) -> Dict[str, Any]:
    rows = [c for c in repository.list_company_summaries() if c.sector.lower() == sector.lower()]
    scores = [c.gci_score for c in rows if c.gci_score is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "sector": sector,
        "company_count": len(rows),
        "avg_gci": avg,
        "companies": rows,
        "product": "Intellens Sector Benchmark",
    }


@router.get("/api/research/eval")
def research_eval(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    cases = [
        {"q": "Infosys margin guidance", "company_id": "infy", "expect_company_id": "infy"},
        {"q": "revenue growth guidance", "company_id": "tcs", "expect_company_id": "tcs"},
        {"q": "completely unrelated xyzzy999", "expect_refuse": True},
    ]
    # pad to 30 lightweight cases
    for cid in ["reliance", "wipro", "hcltech", "hdfcbank", "maruti"]:
        cases.append({"q": "guidance", "company_id": cid, "expect_company_id": cid})
    while len(cases) < 30:
        cases.append({"q": "guidance growth margin", "expect_company_id": "infy"})
    return research_svc.chat_eval_hit_rate(cases)


@router.get("/api/companies/{company_id}/docs")
def company_docs(company_id: str, period: Optional[str] = None) -> Dict[str, Any]:
    # Lazy Tier-1 corpus bind for hand_labeled dossiers
    try:
        detail = repository.get_company_gci(company_id)
        if detail.data_quality == "hand_labeled":
            from app.services.citation_corpus import ensure_company_citation_corpus

            ensure_company_citation_corpus(company_id)
    except Exception:
        pass
    docs = repository.company_period_docs(company_id, period=period)
    completeness = repository.period_completeness(company_id)
    return {
        "company_id": company_id,
        "period": period,
        "count": len(docs),
        "documents": docs,
        "completeness": completeness,
    }


@router.get("/api/companies/{company_id}/changes")
def company_changes(company_id: str) -> Dict[str, Any]:
    bundle = repository.gci_change_bundle_for(company_id)
    return {"company_id": company_id, **bundle}


@router.get("/api/companies/{company_id}/analytics")
def company_analytics(
    company_id: str, auth=Depends(require_feature("analytics_experimental"))
) -> Dict[str, Any]:
    """Workbench-only. Experimental — synthetic inputs (rule `index-integrity`)."""
    from app.data.market_history import get_stock_history
    from app.services.factor_analytics import build_company_analytics
    from app.services.feature_flags import (
        analytics_experimental_ui,
        analytics_granger_v1_enabled,
    )
    from app.services.granger_analytics import build_granger_bundle
    from app.services.pit_warehouse import (
        analytics_series_for,
        build_aligned_factor_series,
        ensure_pit_series,
    )

    detail = repository.get_company_gci(company_id)
    price = get_stock_history(company_id, years=5) or {}
    analytics = build_company_analytics(
        gci_trend=detail.trend or [],
        price_points=price.get("points") or [],
        by_metric=detail.by_metric or {},
        gci_score=detail.gci_score,
    )
    analytics["experimental"] = True
    analytics["synthetic_inputs"] = True
    analytics["banner"] = "Experimental — synthetic inputs. Not part of the published GCI."
    analytics["show_experimental_ui"] = analytics_experimental_ui()
    # Prefer PIT warehouse (≥12) for #7 alignment disclosure
    gci_vals, pit_points = analytics_series_for(company_id)
    closes = [
        float(p["close"])
        for p in (price.get("points") or [])
        if p.get("close") is not None
    ]
    if len(gci_vals) >= 3 and closes:
        from app.services.factor_analytics import _pearson, lead_lag

        n = min(len(gci_vals), len(closes))
        analytics["sample_n"] = n
        analytics["window_label"] = (
            f"last {n} PIT quarters "
            f"({(pit_points[-1] or {}).get('series_kind', 'demo_pit_extension')} + price tape)"
            if pit_points
            else f"last {n} PIT quarters (demo_pit_extension + price tape)"
        )
        analytics["gci_price_corr"] = _pearson(gci_vals[-n:], closes[-n:])
        analytics["lead_lag_gci_vs_price"] = lead_lag(
            gci_vals[-n:], closes[-n:], max_lag=3
        )
        analytics["pit_as_of"] = [p.get("as_of") for p in pit_points[-n:]]
        sk = (pit_points[-1] or {}).get("series_kind") if pit_points else "demo_pit_extension"
        analytics["series_kind"] = sk
        analytics["citeable"] = bool((pit_points[-1] or {}).get("citeable")) if pit_points else False
        analytics["methodology"] = (
            "Pearson / lag corr on PIT GCI + price tape. "
            "Descriptive pattern only — not causation, not a forecast. "
            + (
                "Series is citeable outcome as_of PIT."
                if analytics["citeable"]
                else "demo_pit_extension is non-citeable analytics scaffolding."
            )
        )
    if analytics_granger_v1_enabled():
        ensure_pit_series(company_id)
        factors = build_aligned_factor_series(
            company_id,
            gci_vals,
            by_metric=detail.by_metric or {},
            price_closes=closes,
        )
        analytics["granger"] = build_granger_bundle(
            gci_series=gci_vals,
            price_series=factors.get("price") or closes[-len(gci_vals) :],
            factor_series=factors,
        )
    else:
        analytics["granger"] = {
            "enabled": False,
            "flag": "ANALYTICS_GRANGER_V1",
            "note": "Enable env ANALYTICS_GRANGER_V1=1 after Tier 1 citation gate.",
        }
    return {"company_id": company_id, **analytics}


@router.get("/api/notes")
def notes_list(
    company_id: Optional[str] = None,
    auth=Depends(resolve_api_key),
) -> Dict[str, Any]:
    from app.services import analyst_notes

    actor = auth.get("key") or auth.get("email") or "anonymous"
    rows = analyst_notes.list_notes(actor=actor, company_id=company_id)
    return {"actor": actor, "count": len(rows), "notes": rows}


@router.post("/api/notes")
def notes_upsert(body: Dict[str, Any], auth=Depends(require_any_feature("analyst_agent", "ninja"))) -> Dict[str, Any]:
    from app.services import analyst_notes

    actor = auth.get("key") or auth.get("email") or "anonymous"
    company_id = (body.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    note = analyst_notes.upsert_note(
        actor=actor,
        company_id=company_id,
        body=str(body.get("body") or ""),
        note_id=body.get("id"),
        title=str(body.get("title") or ""),
    )
    return {"ok": True, "note": note}


@router.delete("/api/notes/{note_id}")
def notes_delete(note_id: str, auth=Depends(require_any_feature("analyst_agent", "ninja"))) -> Dict[str, Any]:
    from app.services import analyst_notes

    actor = auth.get("key") or auth.get("email") or "anonymous"
    ok = analyst_notes.delete_note(actor=actor, note_id=note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@router.get("/api/reports/templates")
def report_templates(role: Optional[str] = None, industry: Optional[str] = None) -> Dict[str, Any]:
    from app.services.reports import list_templates

    rows = list_templates(role=role, industry=industry)
    return {"count": len(rows), "templates": rows}


@router.post("/api/reports/generate")
def report_generate(body: Dict[str, Any], auth=Depends(require_feature("ic_export"))) -> Any:
    from app.services import analyst_notes
    from app.services.audit_dossier import render_ic_audit
    from app.services.reports import render_report
    from app.data.market_history import get_stock_history
    from app.services.factor_analytics import build_company_analytics
    from fastapi.responses import Response

    company_id = (body.get("company_id") or "").strip()
    template_id = (body.get("template_id") or "ra_delivery").strip()
    fmt = (body.get("format") or "markdown").strip().lower()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    detail = repository.get_company_gci(company_id)
    actor = auth.get("key") or auth.get("email") or "anonymous"
    notes = analyst_notes.list_notes(actor=actor, company_id=company_id)
    docs = repository.company_period_docs(company_id)
    price = get_stock_history(company_id, years=5) or {}
    analytics = build_company_analytics(
        gci_trend=detail.trend or [],
        price_points=price.get("points") or [],
        by_metric=detail.by_metric or {},
        gci_score=detail.gci_score,
    )
    gci_payload = detail.model_dump() if hasattr(detail, "model_dump") else detail.dict()
    gci_payload["change_bundle"] = repository.gci_change_bundle_for(company_id)
    company = {"id": detail.id, "name": detail.name, "ticker": detail.ticker}

    if template_id == "ic_audit" or fmt in ("json", "pdf"):
        # IC pack path — structured JSON / PDF / markdown
        pack = render_ic_audit(
            company=company,
            gci=gci_payload,
            notes=notes,
            docs=docs,
            analytics=analytics,
            fmt="pdf" if fmt == "pdf" else ("json" if fmt == "json" else "markdown"),
            generated_by=actor,
        )
        if fmt == "pdf":
            pdf_bytes = pack.pop("pdf_bytes", None)
            if pdf_bytes is None:
                raise HTTPException(status_code=500, detail="PDF generation failed")
            ticker = detail.ticker or company_id
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="ic-audit-{ticker}.pdf"'
                },
            )
        pack.pop("pdf_bytes", None)
        return pack

    report = render_report(
        template_id=template_id,
        company=company,
        gci=gci_payload,
        notes=notes,
        analytics=analytics,
        docs=docs,
    )
    return report


@router.get("/api/ops/pending-depth")
def ops_pending_depth(bootstrap: bool = False, auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    """Depth backlog status; ``bootstrap=true`` enqueues Nifty M2 + ensures PIT warehouse."""
    from app.services.pending_depth import pending_depth_report

    return pending_depth_report(bootstrap=bootstrap)


@router.post("/api/ops/pending-depth/bootstrap")
def ops_pending_depth_bootstrap(auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.pending_depth import ensure_bootstrap

    return ensure_bootstrap(org_id=auth.get("org") or "demo")


@router.get("/api/ops/corpus-coverage")
def ops_corpus_coverage(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.pending_depth import sensex_corpus_coverage

    return sensex_corpus_coverage()


@router.get("/api/ops/coverage-progress")
def ops_coverage_progress(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.india_coverage import coverage_progress
    from app.services.us_coverage import coverage_progress as us_progress

    return {**coverage_progress(), "us": us_progress()}


@router.get("/api/ops/throughput")
def ops_throughput(auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.throughput import desk_throughput

    return desk_throughput()


@router.post("/api/orgs/pilot")
def orgs_provision_pilot(body: Dict[str, Any], auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.pilot_checklist import provision_pilot_org

    if not auth.get("platform_admin_role") and auth.get("key") != "intellens-demo":
        raise HTTPException(status_code=403, detail="Platform operator required")
    name = (body.get("name") or "").strip() or "Pilot Desk"
    return provision_pilot_org(
        name=name,
        owner_email=body.get("owner_email"),
        seats=int(body.get("seats") or 5),
        term_days=body.get("term_days"),
    )


@router.get("/api/orgs/{org_id}/pilot-checklist")
def org_pilot_checklist(org_id: str, auth=Depends(require_session_or_key)) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services.pilot_checklist import get_pilot_checklist

    org_svc.assert_org_access(auth, org_id)
    return get_pilot_checklist(org_id)


@router.patch("/api/orgs/{org_id}/pilot-checklist")
def org_pilot_checklist_patch(
    org_id: str, body: Dict[str, Any], auth=Depends(require_session_or_key)
) -> Dict[str, Any]:
    from app.services import orgs as org_svc
    from app.services.pilot_checklist import patch_pilot_checklist

    org_svc.assert_org_access(auth, org_id)
    return patch_pilot_checklist(
        org_id,
        item_id=body.get("item_id"),
        done=body.get("done"),
        notes=body.get("notes"),
        convert_intent=body.get("convert_intent"),
        target_sku=body.get("target_sku"),
    )


@router.get("/api/v1/rankings")
@router.get("/api/public/gci-rankings")
def public_gci_rankings(
    market: str = "IN",
    index: str = "SENSEX",
    limit: int = 10,
    format: str = "json",
) -> Any:
    """Public citeable-only GCI rankings (Guidance Credibility Quarterly)."""
    from app.services.gci_rankings import gci_rankings, rankings_markdown

    payload = gci_rankings(market=market, index=index, limit=limit, citeable_only=True)
    if (format or "json").lower() in ("md", "markdown"):
        return {"format": "markdown", "markdown": rankings_markdown(payload), **payload}
    return payload


# --- Index integrity: score ledger + public changelog (W1.6 / W1.7) ---


def _as_of_param(as_of: Optional[str]) -> Optional[str]:
    if as_of is None:
        return None
    try:
        return _date.fromisoformat(as_of.strip()).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD") from None


@router.get("/api/v1/index/ledger")
def index_ledger(
    company_id: Optional[str] = None, limit: int = 200, as_of: Optional[str] = None
) -> Dict[str, Any]:
    """Append-only record of every published GCI level (newest last)."""
    from app.services import score_ledger

    cutoff = _as_of_param(as_of)
    rows = score_ledger.rows_for(company_id) if company_id else score_ledger.read_all()
    if cutoff:
        rows = [r for r in rows if str(r.get("as_of") or "") <= cutoff]
    lim = max(1, min(int(limit), 1000))
    rows = rows[-lim:]
    return {
        "company_id": company_id,
        "as_of": cutoff,
        "count": len(rows),
        "rows": rows,
        "note": (
            "One row per published level. A correction is a new row with a later as_of "
            "and a reason; earlier rows are never edited."
        ),
    }


@router.get("/api/v1/index/levels")
def index_levels(as_of: Optional[str] = None) -> Dict[str, Any]:
    """The level each company was published at on a given day, from the ledger alone."""
    from app.services import score_ledger

    cutoff = _as_of_param(as_of) or _date.today().isoformat()
    latest: Dict[str, Dict[str, Any]] = {}
    for row in score_ledger.read_all():
        if str(row.get("as_of") or "") <= cutoff:
            latest[str(row.get("company_id"))] = row
    levels = [
        {k: r.get(k) for k in ("company_id", "gci", "confidence_tier", "as_of", "algorithm_id", "dataset_version", "reason")}
        for r in latest.values()
        if r.get("gci") is not None
    ]
    levels.sort(key=lambda r: r["company_id"])
    return {
        "as_of": cutoff,
        "count": len(levels),
        "levels": levels,
        "note": "Rebuilt from the append-only ledger. Rows dated after as_of are ignored.",
    }


@router.get("/api/v1/index/evidence")
def index_evidence(checksum: str) -> Dict[str, Any]:
    """Stored filing for a SHA-256 content hash: URL, filing date, ingestion time."""
    from app.data import doc_store

    doc = doc_store.find_by_hash(checksum)
    if doc is None:
        raise HTTPException(status_code=404, detail="No stored filing with that SHA-256")
    return doc


@router.get("/api/v1/index/changelog")
def index_changelog(company_id: Optional[str] = None) -> Dict[str, Any]:
    """Public methodology / data changelog (mirrors docs/kb/03-scoring.md)."""
    from app.services.guidance_review import changelog_entries

    entries = changelog_entries()
    if company_id:
        entries = [e for e in entries if company_id in (e.get("companies") or [])]
    entries.sort(key=lambda e: e.get("date") or "", reverse=True)
    return {"company_id": company_id, "count": len(entries), "entries": entries}


@router.get("/api/v1/index/changelog.rss")
def index_changelog_rss():
    """W9.6 — RSS of the public changelog."""
    from fastapi.responses import PlainTextResponse

    data = index_changelog()
    items = []
    for e in data.get("entries") or []:
        date = e.get("date") or ""
        title = e.get("reason") or "update"
        body = (e.get("change") or "").replace("&", "&amp;").replace("<", "&lt;")
        items.append(
            f"<item><title>{title} {date}</title><description>{body}</description>"
            f"<pubDate>{date}</pubDate></item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>CiteAlpha GCI changelog</title>"
        "<link>https://citealpha.com/changelog</link>"
        "<description>Published GCI methodology and data corrections</description>"
        + "".join(items)
        + "</channel></rss>"
    )
    return PlainTextResponse(xml, media_type="application/rss+xml")


@router.get("/api/v1/index/files")
def index_files() -> Dict[str, Any]:
    """Frozen daily GCI level files (W9.2). Reproducible from the score ledger."""
    from app.jobs import publish_index_files as pub

    files = pub.list_files()
    if not files:
        pub.publish()
        files = pub.list_files()
    return {"files": files, "count": len(files)}


@router.get("/api/v1/index/files/{name}")
def index_file_download(name: str):
    """Download one frozen CSV, Parquet, or checksum file."""
    import re

    from fastapi.responses import FileResponse

    from app.jobs.publish_index_files import resolve_file

    if not re.fullmatch(r"gci_levels_\d{8}\.(csv|parquet|sha256|json)", name):
        raise HTTPException(status_code=404, detail="Unknown index file")
    try:
        path = resolve_file(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Index file not published") from None
    media = {
        ".csv": "text/csv",
        ".parquet": "application/vnd.apache.parquet",
        ".sha256": "text/plain",
        ".json": "application/json",
    }[path.suffix]
    return FileResponse(path, media_type=media, filename=path.name)


@router.get("/api/v1/index/digest")
def index_ledger_digest() -> Dict[str, Any]:
    """Preview of the weekly ledger-move email (W9.6). Does not send."""
    from app.services.ledger_digest import preview

    body = preview()
    body.pop("recipients", None)
    return body


@router.get("/api/v1/pit/contract")
def pit_contract() -> Dict[str, Any]:
    from app.services.pit_contract import contract_schema

    return contract_schema()


@router.get("/api/v1/pit/companies/{company_id}/history")
def pit_history_v1(company_id: str) -> Dict[str, Any]:
    from app.services.pit_contract import history_v1

    return history_v1(company_id)


@router.get("/api/v1/pit/bulk")
def pit_bulk(ids: str = "", auth=Depends(optional_api_key)) -> Dict[str, Any]:
    from app.services.pit_contract import bulk_history

    id_list = [x.strip() for x in (ids or "").split(",") if x.strip()]
    if len(id_list) > 10 and auth is None:
        raise HTTPException(status_code=401, detail="X-API-Key required for bulk >10")
    return bulk_history(id_list)


# --- Platform admin portal (role-based; separate from org admin) ---


@router.get("/api/admin/portal/me")
def admin_portal_me(actor=Depends(admin_portal_svc.resolve_platform_admin)) -> Dict[str, Any]:
    return admin_portal_svc.portal_me(actor)


@router.get("/api/admin/portal/orgs")
def admin_portal_orgs(actor=Depends(admin_portal_svc.require_platform_perm("orgs.read"))) -> Dict[str, Any]:
    return {"orgs": admin_portal_svc.list_orgs()}


@router.delete("/api/admin/portal/orgs/{org_id}")
def admin_portal_delete_org(
    org_id: str,
    actor=Depends(admin_portal_svc.require_platform_perm("orgs.write")),
) -> Dict[str, Any]:
    """Delete an empty organisation. Standing desks and occupied seats are refused."""
    return admin_portal_svc.delete_org(org_id)


@router.post("/api/admin/portal/orgs/{org_id}/owner-invite")
def admin_portal_owner_invite(
    org_id: str,
    actor=Depends(admin_portal_svc.require_platform_perm("pilot.manage")),
) -> Dict[str, Any]:
    """Email the recorded owner a link to join this desk as admin."""
    from app.services import orgs as org_svc

    invited_by = str(actor.get("email") or actor.get("user_id") or "platform")
    return org_svc.invite_recorded_owner(org_id=org_id, invited_by=invited_by)


@router.get("/api/admin/portal/users")
def admin_portal_users(actor=Depends(admin_portal_svc.require_platform_perm("users.read"))) -> Dict[str, Any]:
    return {"users": admin_portal_svc.list_users()}


@router.patch("/api/admin/portal/users/{user_id}/platform-role")
def admin_portal_user_platform_role(
    user_id: str,
    body: PlatformAdminRoleRequest,
    actor=Depends(admin_portal_svc.require_platform_perm("users.write")),
) -> Dict[str, Any]:
    return admin_portal_svc.assign_platform_admin_role(
        user_id, body.platform_admin_role, actor=actor
    )


@router.delete("/api/admin/portal/users/{user_id}")
def admin_portal_delete_user(
    user_id: str,
    actor=Depends(admin_portal_svc.require_platform_perm("users.write")),
) -> Dict[str, Any]:
    """Delete a login and free the seat. Standing team accounts are refused."""
    return admin_portal_svc.delete_user(user_id, actor=actor)


@router.post("/api/admin/portal/cleanup-test-tenants")
def admin_portal_cleanup_test_tenants(
    body: Dict[str, Any],
    actor=Depends(admin_portal_svc.require_platform_perm("system.ops")),
) -> Dict[str, Any]:
    """Remove e2e tenants and guests. dry_run defaults on. Approved desks are kept."""
    dry_run = body.get("dry_run", True)
    return admin_portal_svc.cleanup_test_tenants(dry_run=bool(dry_run))


@router.get("/api/admin/portal/feedback")
def admin_portal_feedback(
    status: Optional[str] = None,
    actor=Depends(admin_portal_svc.require_platform_perm("feedback.read")),
) -> Dict[str, Any]:
    from app.services import feedback as fb

    return {"items": fb.list_feedback(status=status)}


@router.patch("/api/admin/portal/feedback/{item_id}")
def admin_portal_feedback_patch(
    item_id: str,
    body: Dict[str, Any],
    actor=Depends(admin_portal_svc.require_platform_perm("feedback.write")),
) -> Dict[str, Any]:
    from app.services import feedback as fb

    status = str(body.get("status") or "ack")
    return fb.set_status(item_id, status)


@router.get("/api/admin/portal/legal")
def admin_portal_legal(
    actor=Depends(admin_portal_svc.require_platform_perm("legal.read")),
) -> Dict[str, Any]:
    from app.services import legal_attest

    return legal_attest.snapshot()


@router.get("/api/admin/portal/trust")
def admin_portal_trust(
    actor=Depends(admin_portal_svc.require_platform_perm("legal.read")),
) -> Dict[str, Any]:
    """Internal Trust fields that must not appear on public /api/trust (W8.2)."""
    from app.services import legal_attest
    from app.services.rbac import sso_status

    snap = legal_attest.snapshot()
    return {
        **snap,
        "sso": sso_status(),
        "counsel_status": snap.get("counsel_status"),
    }


@router.post("/api/admin/portal/legal/attest")
def admin_portal_legal_attest(
    body: LegalAttestRequest,
    actor=Depends(admin_portal_svc.require_platform_perm("legal.write")),
) -> Dict[str, Any]:
    from app.services import legal_attest

    return legal_attest.attest(
        kind=body.kind,
        attested_by=body.attested_by,
        note=body.note,
        admin_key_ok=True,
    )


@router.get("/api/admin/portal/billing")
def admin_portal_billing(
    actor=Depends(admin_portal_svc.require_platform_perm("billing.read")),
) -> Dict[str, Any]:
    from app.services import billing

    return {"invoices": billing.list_invoices(None)}


@router.get("/api/admin/portal/audit")
def admin_portal_audit(
    actor=Depends(admin_portal_svc.require_platform_perm("audit.read")),
) -> Dict[str, Any]:
    return admin_portal_svc.audit_summary()


@router.get("/api/admin/portal/board")
def admin_portal_board(actor=Depends(admin_portal_svc.resolve_platform_admin)) -> Dict[str, Any]:
    return admin_portal_svc.portal_board(actor)


@router.get("/api/admin/portal/labeling")
def admin_portal_labeling(
    actor=Depends(admin_portal_svc.require_platform_perm("audit.read")),
) -> Dict[str, Any]:
    return admin_portal_svc.labeling_queue_view()


@router.get("/api/admin/portal/commitments")
def admin_portal_commitments(
    actor=Depends(admin_portal_svc.require_platform_perm("audit.read")),
) -> Dict[str, Any]:
    return admin_portal_svc.unreviewed_commitments()


@router.get("/api/admin/portal/system")
def admin_portal_system(
    actor=Depends(admin_portal_svc.require_platform_perm("system.ops")),
) -> Dict[str, Any]:
    return admin_portal_svc.system_status()


@router.post("/api/admin/portal/billing/invoices")
def admin_portal_create_invoice(
    body: Dict[str, Any],
    actor=Depends(admin_portal_svc.require_platform_perm("billing.write")),
) -> Dict[str, Any]:
    return admin_portal_svc.create_msa(body)


@router.get("/api/admin/portal/reports")
def admin_portal_reports(actor=Depends(admin_portal_svc.resolve_platform_admin)) -> Dict[str, Any]:
    return admin_portal_svc.report_catalog(actor)


@router.get("/api/admin/portal/reports/{report_id}")
def admin_portal_report(
    report_id: str,
    format: Optional[str] = None,
    actor=Depends(admin_portal_svc.resolve_platform_admin),
):
    body = admin_portal_svc.portal_report(actor, report_id)
    if format == "csv" and report_id == "audit-events":
        return PlainTextResponse(admin_portal_svc.audit_events_csv(body), media_type="text/csv")
    return body


@router.post("/api/admin/portal/pilot")
def admin_portal_provision_pilot(
    body: Dict[str, Any],
    actor=Depends(admin_portal_svc.require_platform_perm("pilot.manage")),
) -> Dict[str, Any]:
    from app.services.pilot_checklist import provision_pilot_org

    name = str(body.get("name") or "New Pilot Desk")
    return provision_pilot_org(name=name, term_days=body.get("term_days"))


@router.get("/api/admin/portal/pilot-requests")
def admin_portal_pilot_requests(
    status: Optional[str] = None,
    actor=Depends(admin_portal_svc.require_platform_perm("pilot.manage")),
) -> Dict[str, Any]:
    from app.services import pilot_request as pr

    return {"items": pr.list_requests(status=status)}


@router.patch("/api/admin/portal/pilot-requests/{request_id}")
def admin_portal_pilot_request_review(
    request_id: str,
    body: PilotRequestReview,
    actor=Depends(admin_portal_svc.require_platform_perm("pilot.manage")),
) -> Dict[str, Any]:
    from app.services import pilot_request as pr

    return pr.review_request(
        request_id,
        action=body.action,
        actor=actor,
        note=body.note,
        term_days=body.term_days,
    )


@router.delete("/api/admin/portal/pilot-requests/{request_id}")
def admin_portal_delete_pilot_request(
    request_id: str,
    actor=Depends(admin_portal_svc.require_platform_perm("pilot.manage")),
) -> Dict[str, Any]:
    """Delete the intake row. A provisioned organisation is left in place."""
    from app.services import pilot_request as pr

    return pr.delete_request(request_id)