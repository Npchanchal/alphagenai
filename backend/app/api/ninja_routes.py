"""Financial Ninja routes. Worksheets and layer notes. Not the public GCI spec."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services import market_scope
from app.services.entitlements import has_feature, resolve_actor
from app.services.pilot_checklist import pilot_evaluation_ended

router = APIRouter()


async def _require_ninja(request: Request, ent: Dict[str, Any] = Depends(resolve_actor)) -> Dict[str, Any]:
    if ent.get("kind") == "guest" or ent.get("source") == "guest":
        if ent.get("user_id"):
            raise HTTPException(status_code=403, detail="Sign in with a desk seat to open Financial Ninja")
        raise HTTPException(status_code=401, detail="Authentication required")
    if not has_feature(ent, "ninja"):
        if ent.get("plan") == "pilot" and pilot_evaluation_ended(str(ent.get("org_id") or "")):
            raise HTTPException(
                status_code=403,
                detail="This evaluation has ended. Financial Ninja stays on a paid desk.",
            )
        if ent.get("plan") == "pilot":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Financial Ninja is open during an admin-approved evaluation "
                    "of 30, 45, or 60 days, and on a paid desk after that."
                ),
            )
        raise HTTPException(
            status_code=403,
            detail=f"Plan {ent.get('plan')} / role {ent.get('role')} lacks ninja",
        )
    await market_scope.check_request(ent, request)
    return ent


def _known_company(company_id: str) -> None:
    from app.services import repository

    try:
        repository.get_company_gci(company_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Unknown company")


@router.get("/api/ninja/templates")
def ninja_templates(_ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import TEMPLATES, WORKSHEET_LINE

    return {"templates": list(TEMPLATES), "statement": WORKSHEET_LINE}


@router.post("/api/ninja/worksheets/{template}")
def ninja_worksheet(template: str, body: Dict[str, Any], ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import save_worksheet

    company_id = str(body.get("company_id") or "").strip()
    if company_id:
        _known_company(company_id)
    return save_worksheet(str(ent.get("org_id") or ""), template, body)


@router.get("/api/ninja/worksheets")
def ninja_worksheet_record(
    company_id: str,
    template: Optional[str] = None,
    ent=Depends(_require_ninja),
) -> Dict[str, Any]:
    from app.services.ninja import worksheet_record

    _known_company(company_id)
    return worksheet_record(str(ent.get("org_id") or ""), company_id, template or None)


@router.get("/api/ninja/taxonomy")
def ninja_taxonomy(_ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import sector_taxonomy

    return sector_taxonomy()


@router.post("/api/ninja/observations")
def ninja_observation(body: Dict[str, Any], ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import add_observation

    _known_company(str(body.get("company_id") or ""))
    return add_observation(str(ent.get("org_id") or ""), body)


@router.delete("/api/ninja/observations/{obs_id}")
def ninja_observation_delete(obs_id: str, ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import delete_observation

    return delete_observation(str(ent.get("org_id") or ""), obs_id)


@router.post("/api/ninja/ratings")
def ninja_rating(body: Dict[str, Any], ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import upsert_rating

    _known_company(str(body.get("company_id") or ""))
    return upsert_rating(str(ent.get("org_id") or ""), body)


@router.get("/api/ninja/indices")
def ninja_index_book(_ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import calculation_book

    return calculation_book()


@router.get("/api/ninja/indices/{company_id}")
def ninja_index(
    company_id: str,
    period: Optional[str] = None,
    ent=Depends(_require_ninja),
) -> Dict[str, Any]:
    from app.services.ninja import calculation_for, chronology_for, layer_index

    _known_company(company_id)
    payload = layer_index(str(ent.get("org_id") or ""), company_id, period or None)
    payload["calculation"] = calculation_for(company_id)
    payload["chronology"] = chronology_for(company_id)
    return payload


@router.get("/api/ninja/profile/{company_id}")
def ninja_profile(company_id: str, ent: Dict[str, Any] = Depends(resolve_actor)) -> Dict[str, Any]:
    """Cited layer text for the signed-in desk. Guests receive an empty record."""
    from app.services.ninja import profile_quotes

    if not ent.get("org_id") or not (has_feature(ent, "ninja") or has_feature(ent, "analyst_agent")):
        return {
            "company_id": company_id,
            "layers": {name: [] for name in ("accounting", "causality", "conduct", "execution")},
            "notes": [],
            "sector": None,
            "note": "Cited notes on this desk. These sentences are not a score.",
        }
    profile = profile_quotes(str(ent["org_id"]), company_id)
    if not has_feature(ent, "ninja"):
        profile["layers"] = {name: [] for name in ("accounting", "causality", "conduct", "execution")}
    return profile


@router.get("/api/ninja/tests")
def ninja_tests(_ent=Depends(_require_ninja)) -> Dict[str, Any]:
    from app.services.ninja import hypothesis_tests

    return hypothesis_tests()
