"""CiteAlpha Analyst + Commitment Record routes (plan `docs/PLAN_CITEALPHA_ANALYST.md`)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.models.schemas import (
    AnalystDigestRequest,
    AnalystMemoryRequest,
    AnalystMonitorRequest,
    AnalystProjectPatch,
    AnalystProjectRequest,
    AnalystRunRequest,
    AnalystUploadRequest,
    CommitmentExtractRequest,
    CommitmentProposeRequest,
    CommitmentReviewRequest,
    CommitmentTransitionRequest,
)
from app.services import commitment_store
from app.services import commitments as commitment_rules
from app.services.auth import resolve_api_key
from app.services.entitlements import has_feature, require_feature, resolve_actor

router = APIRouter()

REVIEWER_ROLES = ("reviewer", "admin", "owner")


def _actor_id(ent: Dict[str, Any]) -> str:
    return str(ent.get("user_id") or ent.get("key") or ent.get("org_id") or "unknown")


def _org_id(ent: Dict[str, Any]) -> str:
    return str(ent.get("org_id") or ent.get("org") or "demo")


def _known_company(company_id: str) -> None:
    from app.services import repository

    try:
        repository.get_company_gci(company_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Unknown company")


def require_reviewer(ent: Dict[str, Any] = Depends(require_feature("labeling"))) -> Dict[str, Any]:
    if str(ent.get("role") or "").lower() not in REVIEWER_ROLES:
        raise HTTPException(status_code=403, detail="Only a reviewer can accept or close a commitment")
    return ent


# ── CiteAlpha Analyst ────────────────────────────────────────────────────────


@router.get("/api/analyst/skills")
def analyst_skills(_ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import skills, tools

    return {"product": "CiteAlpha Analyst", "skills": skills.list_skills(), "tools": tools.describe()}


@router.post("/api/analyst/run")
def analyst_run(body: AnalystRunRequest, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import run_store, runtime, skills

    try:
        spec = skills.get_skill(body.skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown skill")
    _known_company(body.company_id)
    project = None
    if body.project_id:
        project = _project_or_404(ent, body.project_id)
        if project["company_ids"] and body.company_id not in project["company_ids"]:
            raise HTTPException(status_code=422, detail="Company is not in this Project")
    elif spec.get("requires_project"):
        raise HTTPException(status_code=422, detail="This Skill runs inside a Project — choose or create one")
    out = runtime.run_skill(
        body.skill_id,
        body.company_id,
        include_unreviewed=body.include_unreviewed and has_feature(ent, "labeling"),
        org_id=_org_id(ent),
        project=project,
    )
    run_store.save_run(_org_id(ent), _actor_id(ent), out)
    return out


@router.get("/api/analyst/runs")
def analyst_runs(
    company_id: Optional[str] = None,
    limit: int = 50,
    ent=Depends(require_feature("analyst_agent")),
) -> Dict[str, Any]:
    from app.services.agent import run_store

    return {"runs": run_store.list_runs(_org_id(ent), company_id=company_id, limit=min(limit, 200))}


@router.get("/api/analyst/runs/{run_id}")
def analyst_run_detail(run_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import run_store

    out = run_store.get_run(_org_id(ent), run_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return out


@router.get("/api/analyst/runs/{run_id}/export")
def analyst_run_export(run_id: str, format: str = "xlsx", ent=Depends(require_feature("analyst_agent"))) -> Response:
    from app.services import mailer
    from app.services.agent import exports, house_style, run_store

    fmt = format.lower()
    if fmt not in exports.FORMATS:
        raise HTTPException(status_code=422, detail=f"format must be one of {', '.join(exports.FORMATS)}")
    out = run_store.get_run(_org_id(ent), run_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return Response(
        content=exports.render(out, fmt, mailer.public_base_url(), style=house_style.get_style(_org_id(ent))),
        media_type=exports.FORMATS[fmt][0],
        headers={"Content-Disposition": f'attachment; filename="{exports.filename(out, fmt)}"'},
    )


def _project_or_404(ent: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    from app.services.agent import projects

    proj = projects.get_project(_org_id(ent), project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


def _project_view(proj: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.agent import uploads

    return {**{k: v for k, v in proj.items() if k != "org_id"},
            "uploads": uploads.list_uploads(proj["org_id"], proj["project_id"])}


@router.get("/api/analyst/projects")
def analyst_projects(ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import projects

    return {"projects": [_project_view(p) for p in projects.list_projects(_org_id(ent))]}


@router.post("/api/analyst/projects")
def analyst_project_create(body: AnalystProjectRequest, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import projects

    for cid in body.company_ids:
        _known_company(cid)
    try:
        proj = projects.create_project(org_id=_org_id(ent), created_by=_actor_id(ent),
                                       name=body.name, company_ids=body.company_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _project_view(proj)


@router.get("/api/analyst/projects/{project_id}")
def analyst_project(project_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    return _project_view(_project_or_404(ent, project_id))


@router.patch("/api/analyst/projects/{project_id}")
def analyst_project_update(
    project_id: str, body: AnalystProjectPatch, ent=Depends(require_feature("analyst_agent"))
) -> Dict[str, Any]:
    from app.services.agent import projects

    _project_or_404(ent, project_id)
    for cid in body.company_ids or []:
        _known_company(cid)
    try:
        proj = projects.update_project(_org_id(ent), project_id, name=body.name, company_ids=body.company_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _project_view(proj)


@router.delete("/api/analyst/projects/{project_id}")
def analyst_project_delete(project_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import monitors, projects

    if not projects.delete_project(_org_id(ent), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    monitors.delete_project_monitors(_org_id(ent), project_id)
    return {"deleted": project_id}


@router.post("/api/analyst/projects/{project_id}/memory")
def analyst_memory_add(
    project_id: str, body: AnalystMemoryRequest, ent=Depends(require_feature("analyst_agent"))
) -> Dict[str, Any]:
    from app.services.agent import projects

    _project_or_404(ent, project_id)
    try:
        return projects.add_memory(_org_id(ent), project_id, text=body.text, created_by=_actor_id(ent))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/projects/{project_id}/memory/{memory_id}")
def analyst_memory_delete(project_id: str, memory_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import projects

    _project_or_404(ent, project_id)
    if not projects.delete_memory(_org_id(ent), project_id, memory_id):
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"deleted": memory_id}


@router.post("/api/analyst/projects/{project_id}/models")
def analyst_model_add(
    project_id: str, body: Dict[str, Any], ent=Depends(require_feature("analyst_agent"))
) -> Dict[str, Any]:
    from app.services.agent import projects

    _project_or_404(ent, project_id)
    company_id = str(body.get("company_id") or "")
    _known_company(company_id)
    try:
        return projects.add_model(
            _org_id(ent),
            project_id,
            name=str(body.get("name") or ""),
            figure=body.get("figure"),
            unit=str(body.get("unit") or ""),
            as_of=str(body.get("as_of") or ""),
            assumptions=str(body.get("assumptions") or ""),
            sources=str(body.get("sources") or ""),
            not_found=str(body.get("not_found") or ""),
            company_id=company_id,
            created_by=_actor_id(ent),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/api/analyst/projects/{project_id}/uploads")
def analyst_upload(
    project_id: str, body: AnalystUploadRequest, ent=Depends(require_feature("analyst_agent"))
) -> Dict[str, Any]:
    import base64
    import binascii

    from app.services.agent import uploads

    _project_or_404(ent, project_id)
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="content_base64 is not valid base64")
    try:
        return uploads.add_upload(org_id=_org_id(ent), project_id=project_id, filename=body.filename,
                                  data=data, uploaded_by=_actor_id(ent))
    except uploads.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/projects/{project_id}/uploads/{upload_id}")
def analyst_upload_delete(project_id: str, upload_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import uploads

    _project_or_404(ent, project_id)
    if not uploads.delete_upload(_org_id(ent), project_id, upload_id):
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"deleted": upload_id}


@router.get("/api/analyst/feed")
def analyst_feed(limit: int = 50, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import run_store

    return {"runs": run_store.list_runs(_org_id(ent), limit=min(limit, 200), triggered_only=True)}


@router.get("/api/analyst/monitors")
def analyst_monitors(ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import monitors

    return {"monitors": monitors.list_monitors(_org_id(ent)), "limit": monitors.MAX_MONITORS_PER_ORG}


@router.post("/api/analyst/monitors")
def analyst_monitor_create(
    body: AnalystMonitorRequest, ent=Depends(require_feature("analyst_agent"))
) -> Dict[str, Any]:
    from app.services.agent import monitors, skills

    try:
        spec = skills.get_skill(body.skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown skill")
    if spec.get("requires_project") and body.scope != "project":
        raise HTTPException(status_code=422, detail="This Skill runs inside a Project — monitor the Project instead")
    if body.scope == "company":
        if not body.company_id:
            raise HTTPException(status_code=422, detail="company_id is required")
        _known_company(body.company_id)
    elif body.scope == "project":
        _project_or_404(ent, body.project_id or "")
    elif not ent.get("user_id"):
        raise HTTPException(status_code=422, detail="Sign in to monitor your watchlist")
    email = (body.email or "").strip() or None
    if email and ("@" not in email or " " in email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    try:
        return monitors.create_monitor(
            org_id=_org_id(ent), created_by=_actor_id(ent), skill_id=body.skill_id, email=email,
            scope=body.scope, company_id=body.company_id, project_id=body.project_id,
            user_id=ent.get("user_id"),
        )
    except monitors.LimitError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/monitors/{monitor_id}")
def analyst_monitor_delete(monitor_id: str, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import monitors

    if not monitors.delete_monitor(_org_id(ent), monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")
    return {"deleted": monitor_id}


@router.get("/api/analyst/digest")
def analyst_digest(ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import digest

    d = digest.build_digest(_org_id(ent))
    return {"settings": digest.get_settings(_org_id(ent)), "preview": d, "text": digest.render_text(d)}


@router.put("/api/analyst/digest")
def analyst_digest_settings(body: AnalystDigestRequest, ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import digest

    try:
        return digest.set_settings(_org_id(ent), enabled=body.enabled, emails=body.emails)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/api/ops/analyst/digest/send")
def analyst_digest_send(force: bool = False, _auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.agent import digest

    return digest.send_due_digests(force=force)


@router.post("/api/ops/analyst/events/ingest")
def analyst_events_ingest(company_id: str, _auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    """Discover and ingest rating, USFDA, scheme/open-offer and offer-document filings from NSE for one company."""
    from app.services import event_filings

    _known_company(company_id)
    try:
        return event_filings.ingest_events(company_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Exchange fetch failed: {type(exc).__name__}")


@router.get("/api/ops/analyst/monitors/status")
def analyst_monitors_status(_auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.agent import monitors

    return monitors.status()


@router.post("/api/ops/analyst/monitors/process")
def analyst_monitors_process(limit: int = 50, _auth=Depends(resolve_api_key)) -> Dict[str, Any]:
    from app.services.agent import monitors

    return monitors.process_new_documents(limit=min(max(limit, 1), 200))


# ── Commitment Record ────────────────────────────────────────────────────────


@router.get("/api/commitments/meta")
def commitments_meta() -> Dict[str, Any]:
    return {
        "types": [{"id": t, "label": commitment_rules.TYPE_LABELS[t]} for t in commitment_rules.COMMITMENT_TYPES],
        "states": [{"id": s, "label": commitment_rules.STATE_LABELS[s]} for s in commitment_rules.STATES],
        "quiet_drop_cycles": commitment_rules.QUIET_DROP_CYCLES,
        "note": "Commitments are tracked separately from the GCI and do not change it.",
    }


@router.get("/api/companies/{company_id}/commitments")
def company_commitments(
    company_id: str,
    include_unreviewed: bool = False,
    ent=Depends(resolve_actor),
) -> Dict[str, Any]:
    _known_company(company_id)
    seat = ent.get("kind") != "guest" and has_feature(ent, "desk")
    return commitment_store.company_view(company_id, include_unreviewed=include_unreviewed and seat)


@router.post("/api/commitments/propose")
def commitments_propose(
    body: CommitmentProposeRequest, ent=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    return commitment_store.propose(
        [c.model_dump() | {"extractor": "manual"} for c in body.commitments],
        proposed_by=_actor_id(ent),
    )


@router.post("/api/commitments/extract")
def commitments_extract(
    body: CommitmentExtractRequest, ent=Depends(require_feature("labeling"))
) -> Dict[str, Any]:
    from app.data import doc_store
    from app.services import commitment_extract

    if body.doc_id:
        doc = doc_store.get_document(body.doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
    else:
        if not (body.company_id and body.text and body.source_url and body.as_of):
            raise HTTPException(status_code=422, detail="doc_id, or company_id + text + source_url + as_of")
        _known_company(body.company_id)
        doc = {"company_id": body.company_id, "text": body.text, "url": body.source_url, "date": body.as_of}
    res = commitment_extract.extract_from_document(doc, use_llm=body.use_llm)
    stored = commitment_store.propose(res["proposals"], proposed_by=_actor_id(ent))
    return {**res, **stored}


@router.post("/api/commitments/{commitment_id}/review")
def commitments_review(
    commitment_id: str, body: CommitmentReviewRequest, ent=Depends(require_reviewer)
) -> Dict[str, Any]:
    try:
        return commitment_store.review(
            commitment_id, decision=body.decision, reviewer=_actor_id(ent), edits=body.edits, note=body.note
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Commitment not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/api/commitments/{commitment_id}/transition")
def commitments_transition(
    commitment_id: str, body: CommitmentTransitionRequest, ent=Depends(require_reviewer)
) -> Dict[str, Any]:
    try:
        return commitment_store.transition(
            commitment_id, new_state=body.new_state, proof=body.proof, reviewer=_actor_id(ent)
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Commitment not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/api/companies/{company_id}/commitments/quiet-drop-scan")
def commitments_quiet_drop_scan(company_id: str, _ent=Depends(require_feature("labeling"))) -> Dict[str, Any]:
    from app.services import commitment_monitor

    _known_company(company_id)
    return commitment_monitor.scan_company(company_id)
