"""CiteAlpha connectors (A6): public API v1, MCP server, org API keys, webhook / Slack / Teams destinations."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.models.schemas import (
    AnalystDestinationRequest,
    AnalystHouseStyleRequest,
    AnalystHouseTemplateRequest,
    AnalystOrgKeyRequest,
    PublicRunRequest,
)
from app.services.agent import public_api
from app.services.entitlements import require_feature

router = APIRouter()

ADMIN_ROLES = ("admin", "owner")


def api_actor(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Public API callers authenticate with an API key, as ``X-API-Key`` or ``Authorization: Bearer``."""
    from app.services.auth import lookup_api_key
    from app.services.entitlements import resolve_from_key

    key = (x_api_key or "").strip()
    if not key and (authorization or "").lower().startswith("bearer "):
        key = authorization.split(" ", 1)[1].strip()
    if not key:
        raise HTTPException(status_code=401, detail="API key required (X-API-Key or Authorization: Bearer)")
    row = lookup_api_key(key)
    if not row:
        raise HTTPException(status_code=403, detail="Invalid API key")
    ent = resolve_from_key(row)
    ent["key_id"] = row.get("key_id")
    return ent


def require_org_admin(ent: Dict[str, Any] = Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    if str(ent.get("role") or "").lower() not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only an organisation admin or owner can manage connectors")
    return ent


def _org(ent: Dict[str, Any]) -> str:
    return str(ent.get("org_id") or ent.get("org") or "demo")


def _who(ent: Dict[str, Any]) -> str:
    return str(ent.get("user_id") or ent.get("key") or "unknown")[:16]


# ── Public API v1 (keyed; the keyless GCI index reads stay in routes.py) ────────────────────────────────────────────────────────────────


@router.get("/api/v1/analyst/skills")
def v1_skills(_ent=Depends(api_actor)) -> Dict[str, Any]:
    return public_api.list_skills()


@router.get("/api/v1/analyst/companies/{company_id}/commitments")
def v1_commitments(company_id: str, _ent=Depends(api_actor)) -> Dict[str, Any]:
    return public_api.company_commitments(company_id)


@router.get("/api/v1/analyst/companies/{company_id}/search")
def v1_search(company_id: str, q: str, limit: int = 5, _ent=Depends(api_actor)) -> Dict[str, Any]:
    return public_api.search_filings(company_id, q, limit)


@router.post("/api/v1/analyst/runs")
def v1_run(body: PublicRunRequest, ent=Depends(api_actor)) -> Dict[str, Any]:
    return public_api.run_skill(ent, body.skill_id, body.company_id, body.project_id)


@router.get("/api/v1/analyst/runs/{run_id}")
def v1_run_get(run_id: str, ent=Depends(api_actor)) -> Dict[str, Any]:
    return public_api.get_run(ent, run_id)


@router.get("/api/v1/analyst/runs/{run_id}/export")
def v1_run_export(run_id: str, format: str = "xlsx", ent=Depends(api_actor)) -> Response:
    from app.services import mailer
    from app.services.agent import exports

    run = public_api.get_run(ent, run_id)["data"]
    fmt = format.lower()
    if fmt not in exports.FORMATS:
        raise HTTPException(status_code=422, detail=f"format must be one of {', '.join(exports.FORMATS)}")
    return Response(content=exports.render(run, fmt, mailer.public_base_url(), style=_style(ent)),
                    media_type=exports.FORMATS[fmt][0],
                    headers={"Content-Disposition": f'attachment; filename="{exports.filename(run, fmt)}"'})


def _style(ent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from app.services.agent import house_style

    return house_style.get_style(_org(ent))


# ── MCP server (streamable HTTP, JSON responses) ─────────────────────────────

MCP_PROTOCOL = "2025-06-18"
MCP_TOOLS = [
    {"name": "list_skills", "description": "List CiteAlpha Analyst Skills (cited research workflows) available to run.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_gci", "description": "Published Guidance Credibility Index for an Indian listed company, with confidence tier and the guidance and result citations behind every scored period. Unpublished companies return no number.",
     "inputSchema": {"type": "object", "properties": {"company_id": {"type": "string", "description": "CiteAlpha company id, e.g. infy"}},
                     "required": ["company_id"], "additionalProperties": False}},
    {"name": "get_commitments", "description": "Reviewed management commitments (capacity, capex, launches, deleveraging...) for a company, each with its source quote and state.",
     "inputSchema": {"type": "object", "properties": {"company_id": {"type": "string"}}, "required": ["company_id"], "additionalProperties": False}},
    {"name": "search_filings", "description": "Search a company's exchange filings and return quoted passages with source links and dates.",
     "inputSchema": {"type": "object", "properties": {"company_id": {"type": "string"}, "query": {"type": "string"},
                                                      "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
                     "required": ["company_id", "query"], "additionalProperties": False}},
    {"name": "run_skill", "description": "Run a CiteAlpha Analyst Skill for a company. Every sentence in the output is cited; unsupported sentences are removed.",
     "inputSchema": {"type": "object", "properties": {"skill_id": {"type": "string"}, "company_id": {"type": "string"},
                                                      "project_id": {"type": "string"}},
                     "required": ["skill_id", "company_id"], "additionalProperties": False}},
    {"name": "get_run", "description": "Fetch a saved Skill run of your organisation by run_id.",
     "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"], "additionalProperties": False}},
]


def _call_tool(ent: Dict[str, Any], name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "list_skills":
        return public_api.list_skills()
    if name == "get_gci":
        return public_api.company_gci(str(args.get("company_id") or ""))
    if name == "get_commitments":
        return public_api.company_commitments(str(args.get("company_id") or ""))
    if name == "search_filings":
        return public_api.search_filings(str(args.get("company_id") or ""), str(args.get("query") or ""),
                                         int(args.get("limit") or 5))
    if name == "run_skill":
        return public_api.run_skill(ent, str(args.get("skill_id") or ""), str(args.get("company_id") or ""),
                                    args.get("project_id") or None)
    if name == "get_run":
        return public_api.get_run(ent, str(args.get("run_id") or ""))
    raise KeyError(name)


def _rpc_error(rid: Any, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}, status_code=status)


@router.get("/api/mcp")
def mcp_get() -> Response:
    return Response(status_code=405, headers={"Allow": "POST"})


@router.post("/api/mcp")
async def mcp(request: Request, ent=Depends(api_actor)) -> Response:
    try:
        msg = json.loads(await request.body() or b"null")
    except ValueError:
        return _rpc_error(None, -32700, "Parse error", 400)
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return _rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid request", 400)
    rid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg:  # notification
        return Response(status_code=202)
    if method == "initialize":
        result: Dict[str, Any] = {
            "protocolVersion": MCP_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "citealpha", "title": "CiteAlpha", "version": public_api.API_VERSION},
            "instructions": "Cited facts on Indian listed companies: GCI, commitments, filings and Analyst Skills. Not investment advice.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": MCP_TOOLS}
    elif method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        try:
            data = _call_tool(ent, str(name), args if isinstance(args, dict) else {})
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                      "structuredContent": data, "isError": False}
        except KeyError:
            return _rpc_error(rid, -32602, f"Unknown tool: {name}")
        except HTTPException as exc:
            result = {"content": [{"type": "text", "text": str(exc.detail)}], "isError": True}
    else:
        return _rpc_error(rid, -32601, f"Method not found: {method}")
    return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": result},
                        headers={"MCP-Protocol-Version": MCP_PROTOCOL})


# ── Org API keys and delivery destinations (admin / owner) ───────────────────


@router.get("/api/analyst/keys")
def keys_list(ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import org_keys

    return {"keys": org_keys.list_keys(_org(ent)), "limit": org_keys.MAX_KEYS_PER_ORG}


@router.post("/api/analyst/keys")
def keys_create(body: AnalystOrgKeyRequest, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import org_keys

    try:
        row, plain = org_keys.create_key(_org(ent), label=body.label, created_by=_who(ent), role=body.role)
    except OverflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {**row, "key": plain, "note": "Copy this key now. CiteAlpha stores only a hash and cannot show it again."}


@router.delete("/api/analyst/keys/{key_id}")
def keys_revoke(key_id: str, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import org_keys

    if not org_keys.revoke_key(_org(ent), key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"revoked": key_id}


@router.get("/api/analyst/destinations")
def destinations_list(ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import delivery

    return {"destinations": delivery.list_destinations(_org(ent)), "log": delivery.delivery_log(_org(ent)),
            "events": list(delivery.EVENTS), "kinds": list(delivery.KINDS)}


@router.post("/api/analyst/destinations")
def destinations_add(body: AnalystDestinationRequest, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import delivery

    try:
        return delivery.add_destination(_org(ent), kind=body.kind, url=body.url, events=body.events,
                                        label=body.label or body.kind, created_by=_who(ent))
    except OverflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/destinations/{destination_id}")
def destinations_delete(destination_id: str, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import delivery

    if not delivery.delete_destination(_org(ent), destination_id):
        raise HTTPException(status_code=404, detail="Destination not found")
    return {"deleted": destination_id}


@router.post("/api/analyst/destinations/{destination_id}/test")
def destinations_test(destination_id: str, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import delivery

    if not any(d["destination_id"] == destination_id for d in delivery.list_destinations(_org(ent))):
        raise HTTPException(status_code=404, detail="Destination not found")
    text = "CiteAlpha test message: this destination will receive Monitor runs and weekly digests you subscribed to."
    res = delivery.deliver(_org(ent), "monitor.run", {"test": True, "message": text}, text, only=destination_id)
    return {"result": res[0] if res else None}


# ── House style for exports (admin / owner edit; any analyst seat reads) ──────


@router.get("/api/analyst/house-style")
def house_style_get(ent=Depends(require_feature("analyst_agent"))) -> Dict[str, Any]:
    from app.services.agent import house_style

    return {**house_style.describe(_org(ent)), "fonts": list(house_style.FONTS)}


@router.put("/api/analyst/house-style")
def house_style_put(body: AnalystHouseStyleRequest, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import house_style

    try:
        return house_style.set_style(_org(ent), body.model_dump())
    except house_style.StyleError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/house-style")
def house_style_reset(ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import house_style

    house_style.reset(_org(ent))
    return house_style.describe(_org(ent))


@router.post("/api/analyst/house-style/template")
def house_style_template(body: AnalystHouseTemplateRequest, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    import base64
    import binascii

    from app.services.agent import house_style

    try:
        raw = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="Template is not valid base64")
    try:
        return house_style.set_template(_org(ent), raw)
    except house_style.StyleError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/analyst/house-style/{asset}")
def house_style_clear(asset: str, ent=Depends(require_org_admin)) -> Dict[str, Any]:
    from app.services.agent import house_style

    if asset not in ("template", "logo"):
        raise HTTPException(status_code=404, detail="Unknown asset")
    return house_style.clear_asset(_org(ent), asset)


@router.get("/api/analyst/house-style/preview")
def house_style_preview(ent=Depends(require_feature("analyst_agent"))) -> Response:
    """A sample deck in the org's style, built from a placeholder run with no company data."""
    from app.services import mailer
    from app.services.agent import exports

    sample = {
        "run_id": "preview", "skill": {"id": "house_style_preview", "title": "House style preview", "version": "1"},
        "company_id": "", "company_name": "Sample layout", "as_of": "", "generated_at": "",
        "disclaimer": "Layout preview only. No company data.",
        "headline": "Headlines, bullets and source footers will appear in this style.",
        "sections": [{"title": "Section title", "claims": [
            {"text": "Each statement carries its source numbers.", "cites": []},
            {"text": "Source footers and the Evidence Receipt are always included.", "cites": []}]}],
        "citations": [], "not_found": [], "evidence_receipt": {"sources": [], "tool_calls": []},
    }
    return Response(content=exports.to_pptx(sample, mailer.public_base_url(), _style(ent)),
                    media_type=exports.FORMATS["pptx"][0],
                    headers={"Content-Disposition": 'attachment; filename="citealpha-house-style-preview.pptx"'})
