"""Core of the CiteAlpha public API (``/api/v1``) and MCP server (``/api/mcp``).

Both surfaces call these functions, so a customer's own agent gets exactly what the
REST client gets: published GCI levels only (with tier and both citations per
row), reviewed commitments only, cited filing passages, and org-scoped Skill runs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

API_VERSION = "1"


def _company(company_id: str) -> None:
    from app.services import repository

    try:
        repository.get_company_gci(company_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Unknown company")
    except Exception:
        raise HTTPException(status_code=404, detail="Unknown company")


def envelope(data: Any, citations: Optional[list] = None) -> Dict[str, Any]:
    return {"api_version": API_VERSION, "data": data, "citations": citations or [],
            "disclaimer": "Factual summary of company disclosures with sources. Not investment advice."}


def list_skills() -> Dict[str, Any]:
    from app.services.agent import skills

    return envelope(skills.list_skills())


def company_gci(company_id: str) -> Dict[str, Any]:
    from app.services.agent import tools

    _company(company_id)
    prof = tools.profile(company_id)["data"]
    data: Dict[str, Any] = {k: prof[k] for k in ("company_id", "name", "ticker", "sector", "published")}
    if not prof["published"]:
        data["note"] = "No published GCI for this company: it lacks a reviewed, dual-cited record."
        return envelope(data)
    rec = tools.guidance_record(company_id)
    ev = rec["evidence"]
    citations = [{**e, "n": i + 1} for i, e in enumerate(ev)]
    data.update(gci=prof["gci_score"], confidence_tier=prof["confidence_tier"], as_of=prof["as_of"],
                record=[{"period": r["period"], "metric": r["metric_name"], "guided": r["guided"],
                         "reported": r["actual"] if r["label"] != "dropped" else None, "result": r["label"],
                         "guidance_cite": r["guidance_ev"] + 1,
                         "actual_cite": None if r["actual_ev"] is None else r["actual_ev"] + 1}
                        for r in rec["data"]["rows"]])
    return envelope(data, citations)


def company_commitments(company_id: str) -> Dict[str, Any]:
    from app.services.agent import tools

    _company(company_id)
    res = tools.commitments(company_id, include_unreviewed=False)
    citations = [{**e, "n": i + 1} for i, e in enumerate(res["evidence"])]
    rows = [{"subject": r.get("subject"), "type": r.get("type"), "state": r.get("state"),
             "state_label": r.get("state_label"), "due_period": r.get("due_period"), "due_date": r.get("due_date"),
             "cite": r["ev"] + 1, "proof_cite": r["proof_ev"] + 1 if r.get("proof_ev") is not None else None}
            for r in res["data"]["rows"]]
    return envelope({"company_id": company_id, "summary": res["data"]["summary"], "commitments": rows}, citations)


def search_filings(company_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
    from app.services.agent import tools

    _company(company_id)
    if not (query or "").strip():
        raise HTTPException(status_code=422, detail="query is required")
    ev = tools.filing_search(company_id, query=query.strip()[:200], limit=max(1, min(int(limit or 5), 10)))["evidence"]
    return envelope({"company_id": company_id, "query": query, "found": len(ev)},
                    [{**e, "n": i + 1} for i, e in enumerate(ev)])


def run_skill(ent: Dict[str, Any], skill_id: str, company_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    from app.services.agent import projects, run_store, runtime, skills
    from app.services.entitlements import has_feature

    if not has_feature(ent, "analyst_agent"):
        raise HTTPException(status_code=403, detail="This key's plan or role lacks CiteAlpha Analyst")
    try:
        spec = skills.get_skill(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown skill")
    _company(company_id)
    org_id = str(ent.get("org_id") or "demo")
    project = None
    if project_id:
        project = projects.get_project(org_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["company_ids"] and company_id not in project["company_ids"]:
            raise HTTPException(status_code=422, detail="Company is not in this Project")
    elif spec.get("requires_project"):
        raise HTTPException(status_code=422, detail="This Skill runs inside a Project — pass project_id")
    out = runtime.run_skill(skill_id, company_id, org_id=org_id, project=project)
    run_store.save_run(org_id, f"api:{ent.get('key_id') or 'key'}", out)
    return envelope(out, out["citations"])


def get_run(ent: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    from app.services.agent import run_store
    from app.services.entitlements import has_feature

    if not has_feature(ent, "analyst_agent"):
        raise HTTPException(status_code=403, detail="This key's plan or role lacks CiteAlpha Analyst")
    out = run_store.get_run(str(ent.get("org_id") or "demo"), run_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return envelope(out, out["citations"])
