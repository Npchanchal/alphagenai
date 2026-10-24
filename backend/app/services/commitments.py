"""Commitment Record — pure rules (no I/O).

A commitment is a dated, checkable forward-looking statement by a company that is
*not* numeric guidance on a GCI metric: a plant commissioning date, a capex
programme, a deleveraging target, a launch count, a scheme closing date.

Commitments never feed the GCI (plan `docs/PLAN_CITEALPHA_ANALYST.md` D2). The
company-level summary is a plain count, never an index level.
"""

from __future__ import annotations

import copy
import re
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence

COMMITMENT_TYPES: tuple[str, ...] = (
    "capacity",
    "capex",
    "balance_sheet",
    "order_book",
    "launch",
    "corporate_action",
    "operational",
    "esg",
)

TYPE_LABELS: Dict[str, str] = {
    "capacity": "Capacity / commissioning",
    "capex": "Capital expenditure",
    "balance_sheet": "Balance sheet / leverage",
    "order_book": "Order book / execution",
    "launch": "Launches / expansion",
    "corporate_action": "Corporate action",
    "operational": "Operational target",
    "esg": "ESG target",
}

OPEN = "open"
STATES: tuple[str, ...] = (
    OPEN,
    "delivered",
    "delivered_late",
    "partially_delivered",
    "missed",
    "withdrawn_with_reason",
    "quietly_dropped",
    "superseded",
)
STATE_LABELS: Dict[str, str] = {
    OPEN: "Open",
    "delivered": "Delivered",
    "delivered_late": "Delivered late",
    "partially_delivered": "Partly delivered",
    "missed": "Missed",
    "withdrawn_with_reason": "Withdrawn (reason given)",
    "quietly_dropped": "Dropped without explanation",
    "superseded": "Replaced by a newer commitment",
}

REVIEW_STATUSES: tuple[str, ...] = ("unreviewed", "accepted", "rejected")

QUIET_DROP_CYCLES = 2

_REQUIRED = ("company_id", "type", "subject", "outcome", "due_period", "quote", "source_url", "as_of")
_PROOF_REQUIRED = ("quote", "source_url", "as_of")

# ── Indian fiscal periods ────────────────────────────────────────────────────

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FY = re.compile(r"^(?:(Q[1-4]|H[12])\s*)?FY\s*'?(\d{2}|\d{4})$", re.IGNORECASE)
_QUARTER_END = {"Q1": (0, 6, 30), "Q2": (0, 9, 30), "Q3": (0, 12, 31), "Q4": (1, 3, 31)}
_HALF_END = {"H1": (0, 9, 30), "H2": (1, 3, 31)}


def period_end(due_period: str) -> Optional[str]:
    """Last day of an Indian fiscal period, ISO. ``FY26`` → ``2026-03-31``.

    Accepts ``FY26``, ``FY2026``, ``Q3 FY26``, ``H1 FY27``, or an ISO date.
    Returns None when the period cannot be read — such a commitment is not checkable.
    """
    raw = (due_period or "").strip()
    if not raw:
        return None
    if _ISO_DATE.match(raw):
        try:
            date.fromisoformat(raw)
        except ValueError:
            return None
        return raw
    m = _FY.match(raw.replace("-", " "))
    if not m:
        return None
    part, yy = m.group(1), m.group(2)
    fy_end_year = int(yy) if len(yy) == 4 else 2000 + int(yy)
    start_year = fy_end_year - 1
    if not part:
        return f"{fy_end_year}-03-31"
    part = part.upper()
    table = _QUARTER_END if part.startswith("Q") else _HALF_END
    offset, month, day = table[part]
    return f"{start_year + offset:04d}-{month:02d}-{day:02d}"


# ── Validation ───────────────────────────────────────────────────────────────


def validate_commitment(row: Dict[str, Any]) -> List[str]:
    """Errors that keep a proposal out of the record. Empty list = valid."""
    errors = [f"missing_{k}" for k in _REQUIRED if not str(row.get(k) or "").strip()]
    t = row.get("type")
    if t and t not in COMMITMENT_TYPES:
        errors.append("unknown_type")
    if row.get("due_period") and period_end(str(row["due_period"])) is None:
        errors.append("unreadable_due_period")
    state = row.get("state", OPEN)
    if state not in STATES:
        errors.append("unknown_state")
    return errors


def quote_is_verbatim(quote: str, source_text: str) -> bool:
    """A commitment quote must appear word-for-word in its source (whitespace-normalised)."""
    q = " ".join((quote or "").split())
    t = " ".join((source_text or "").split())
    return bool(q) and q in t


def validate_transition(
    row: Dict[str, Any], new_state: str, proof: Optional[Dict[str, Any]]
) -> List[str]:
    """Errors for moving ``row`` to ``new_state``. Only accepted, open rows move."""
    errors: List[str] = []
    if row.get("review_status") != "accepted":
        errors.append("not_reviewed")
    if row.get("state", OPEN) != OPEN:
        errors.append("not_open")
    if new_state not in STATES or new_state == OPEN:
        errors.append("invalid_state")
        return errors
    proof = proof or {}
    if new_state == "quietly_dropped":
        if int(proof.get("cycles_checked") or 0) < QUIET_DROP_CYCLES:
            errors.append("needs_two_cycles")
        if not proof.get("last_mentioned_as_of"):
            errors.append("missing_last_mentioned_as_of")
        return errors
    errors.extend(f"proof_missing_{k}" for k in _PROOF_REQUIRED if not str(proof.get(k) or "").strip())
    return errors


def apply_transition(
    row: Dict[str, Any],
    new_state: str,
    proof: Dict[str, Any],
    *,
    reviewer: str,
    reviewed_at: str,
) -> Dict[str, Any]:
    """Return a copy of ``row`` in ``new_state``; history is appended, never rewritten."""
    errors = validate_transition(row, new_state, proof)
    if not reviewer:
        errors.append("missing_reviewer")
    if errors:
        raise ValueError(",".join(errors))
    out = copy.deepcopy(row)
    out.setdefault("history", []).append(
        {
            "from": row.get("state", OPEN),
            "to": new_state,
            "proof": dict(proof),
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
        }
    )
    out["state"] = new_state
    out["proof"] = dict(proof)
    out["closed_by"] = reviewer
    out["closed_at"] = reviewed_at
    return out


# ── Quiet-drop detection ─────────────────────────────────────────────────────


def detect_quiet_drops(
    commitments: Iterable[Dict[str, Any]],
    cycles: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Propose ``quietly_dropped`` for open, accepted commitments.

    ``cycles``: disclosure cycles for one company, each
    ``{"as_of": ISO date, "mentions": set of commitment ids}``. A commitment is
    proposed when the most recent ``QUIET_DROP_CYCLES`` cycles after its last
    mention all omit it and its due date has not yet been reached or has passed
    without a proof filing. Proposals go to review; nothing is closed here.
    """
    ordered = sorted(cycles, key=lambda c: str(c.get("as_of") or ""))
    proposals: List[Dict[str, Any]] = []
    for c in commitments:
        if c.get("review_status") != "accepted" or c.get("state", OPEN) != OPEN:
            continue
        cid = c.get("id")
        last = str(c.get("last_mentioned_as_of") or c.get("as_of") or "")
        for cy in ordered:
            if cid in (cy.get("mentions") or set()):
                last = max(last, str(cy.get("as_of") or ""))
        after = [cy for cy in ordered if str(cy.get("as_of") or "") > last]
        if len(after) < QUIET_DROP_CYCLES:
            continue
        window = after[-QUIET_DROP_CYCLES:]
        if any(cid in (cy.get("mentions") or set()) for cy in window):
            continue
        proposals.append(
            {
                "commitment_id": cid,
                "company_id": c.get("company_id"),
                "proposed_state": "quietly_dropped",
                "last_mentioned_as_of": last,
                "cycles_checked": len(after),
                "cycle_dates": [cy.get("as_of") for cy in after],
            }
        )
    return proposals


# ── Summary (plain counts, never an index level) ─────────────────────────────

_DELIVERED = ("delivered", "delivered_late")


def delivery_summary(commitments: Iterable[Dict[str, Any]], *, as_of: str) -> Dict[str, Any]:
    """Counts over accepted commitments due on or before ``as_of``."""
    due: List[Dict[str, Any]] = []
    open_future = 0
    for c in commitments:
        if c.get("review_status") != "accepted":
            continue
        end = period_end(str(c.get("due_period") or ""))
        if end is None:
            continue
        if end <= as_of:
            due.append(c)
        elif c.get("state", OPEN) == OPEN:
            open_future += 1
    counts = {s: 0 for s in STATES}
    for c in due:
        counts[c.get("state", OPEN)] += 1
    delivered = sum(counts[s] for s in _DELIVERED)
    closed = len(due) - counts[OPEN]
    return {
        "as_of": as_of,
        "due": len(due),
        "closed": closed,
        "delivered": delivered,
        "counts": counts,
        "awaiting_proof": counts[OPEN],
        "open_not_yet_due": open_future,
        "sentence": summary_sentence(len(due), delivered, counts),
    }


def summary_sentence(due: int, delivered: int, counts: Dict[str, int]) -> str:
    if due == 0:
        return "No reviewed commitments have fallen due yet."
    parts = [f"Delivered {delivered} of {due} dated commitments that have fallen due"]
    extras = []
    if counts.get("delivered_late"):
        extras.append(f"{counts['delivered_late']} late")
    if counts.get("partially_delivered"):
        extras.append(f"{counts['partially_delivered']} partly delivered")
    if counts.get("missed"):
        extras.append(f"{counts['missed']} missed")
    if counts.get("quietly_dropped"):
        extras.append(f"{counts['quietly_dropped']} dropped without explanation")
    if counts.get("withdrawn_with_reason"):
        extras.append(f"{counts['withdrawn_with_reason']} withdrawn with a reason")
    if counts.get(OPEN):
        extras.append(f"{counts[OPEN]} awaiting a result filing")
    sentence = parts[0]
    if extras:
        sentence += "; " + ", ".join(extras)
    return sentence + "."
