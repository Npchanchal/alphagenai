"""MSA billing (B2B) + retail paywall (B2C)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.data.seed import get_data, save_data

# Illustrative INR list prices — commercial pack is source of truth for contracts
RETAIL_PRICE_INR = float(os.environ.get("RETAIL_PRICE_INR", "4999"))
DESK_SEAT_INR = float(os.environ.get("DESK_SEAT_INR", "45000"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store() -> Dict[str, Any]:
    data = get_data()
    return data.setdefault("billing", {"invoices": [], "subscriptions": {}})


def retail_marketing_allowed() -> bool:
    from app.services.legal_attest import sebi_retail_status

    return sebi_retail_status() == "counsel_approved"


def create_msa_invoice(
    *,
    org_id: str,
    plan: str,
    seats: int,
    amount_inr: Optional[float] = None,
    po_number: Optional[str] = None,
) -> Dict[str, Any]:
    plan_n = (plan or "desk").lower()
    seats_n = max(1, int(seats))
    if amount_inr is None:
        amount_inr = DESK_SEAT_INR * seats_n if plan_n in ("desk", "pilot") else DESK_SEAT_INR * seats_n
    inv = {
        "id": f"msa-{uuid.uuid4().hex[:10]}",
        "org_id": org_id,
        "kind": "msa",
        "plan": plan_n,
        "seats": seats_n,
        "amount_inr": float(amount_inr),
        "currency": "INR",
        "status": "issued",
        "po_number": po_number,
        "esign_status": "pending",
        "created_at": _now(),
        "pay_url": f"/billing/pay?invoice=msa-{uuid.uuid4().hex[:8]}",
    }
    store = _store()
    store["invoices"].append(inv)
    save_data()
    try:
        from app.db.auth_db import insert_billing, use_db_auth

        if use_db_auth():
            insert_billing(
                {
                    "id": inv["id"],
                    "org_id": org_id,
                    "kind": "msa",
                    "status": "issued",
                    "amount_inr": inv["amount_inr"],
                    "payload": inv,
                    "created_at": inv["created_at"],
                }
            )
    except Exception:
        pass
    return inv


def sign_msa(invoice_id: str, *, signer_email: str, org_id: str) -> Dict[str, Any]:
    store = _store()
    for inv in store["invoices"]:
        if (
            inv["id"] == invoice_id
            and inv.get("kind") == "msa"
            and str(inv.get("org_id") or "") == org_id
        ):
            inv["esign_status"] = "signed"
            inv["signed_by"] = signer_email
            inv["signed_at"] = _now()
            inv["status"] = "active"
            store["subscriptions"][inv["org_id"]] = {
                "plan": inv["plan"],
                "seats": inv["seats"],
                "invoice_id": inv["id"],
                "status": "active",
            }
            save_data()
            return inv
    raise HTTPException(status_code=404, detail="MSA invoice not found")


def create_retail_checkout(*, org_id: str, user_email: str) -> Dict[str, Any]:
    """Quote-only (W8.8). No PSP, including after a future retail attest."""
    del org_id, user_email
    raise HTTPException(
        status_code=403,
        detail="Paid plans are quote and order form only. There is no in-app checkout.",
    )


def confirm_retail_payment(order_id: str, *, payment_ref: str = "") -> Dict[str, Any]:
    """Refused until a payment provider is wired (W8.8). Arguments kept for the route."""
    del order_id, payment_ref
    raise HTTPException(
        status_code=403,
        detail="Paid plans are quote and order form only. There is no in-app checkout.",
    )


def create_msa_from_pilot(
    *,
    org_id: str,
    seats: int = 5,
    signer_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Pilot → paid path: issue Desk MSA after pilot checklist is ready."""
    inv = create_msa_invoice(org_id=org_id, plan="desk", seats=seats)
    inv["conversion_path"] = "pilot_to_desk"
    inv["signer_hint"] = signer_hint
    inv["next_steps"] = [
        "Complete the pilot checklist in the Analyst Workbench",
        "Sign the order form (e-sign or wet-ink via counsel)",
        "Provision Desk seats",
        "Invoicing is by quote. There is no in-app payment.",
    ]
    save_data()
    return inv


def list_invoices(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = list(_store().get("invoices") or [])
    if org_id:
        rows = [r for r in rows if r.get("org_id") == org_id]
    return rows


def subscription_for(org_id: str) -> Optional[Dict[str, Any]]:
    return (_store().get("subscriptions") or {}).get(org_id)
