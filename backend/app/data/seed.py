"""Build Sensex-30 style seed with statements, actuals, threads, sources, PIT history."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.data.store_lock import STORE_LOCK, locked
from app.data.universe import SENSEX_30
from app.services.gci_scoring import GuidanceOutcome


def _ir(company_id: str, ticker: str) -> str:
    from app.data.ir_sources import target_for

    ir = target_for(company_id)
    if ir and (ir.get("url") or "").strip():
        return str(ir["url"]).strip()
    return f"https://www.bseindia.com/stock-share-price/{ticker.lower()}/"


def _make_outcomes(company_id: str, ticker: str, sector: str) -> List[Dict[str, Any]]:
    """Generate ≥8 structured outcomes with ranges, threads, sources (demo-grade)."""
    # Deterministic variation from ticker hash
    h = sum(ord(c) for c in ticker) % 7
    base_rev = 8 + h
    rows: List[Dict[str, Any]] = []

    # Thread: revenue guidance restated across periods
    thread = f"{company_id}-rev-growth"
    rows.append(
        {
            "period": "FY23",
            "metric": "revenue_growth_pct",
            "guided_value": float(base_rev),
            "guided_low": float(base_rev - 1),
            "guided_high": float(base_rev + 1),
            "actual_value": float(base_rev + 0.5),
            "guided_text": f"We guide FY23 revenue growth around {base_rev - 1}–{base_rev + 1}%.",
            "confidence": 0.9,
            "speaker": "CFO",
            "thread_id": thread,
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q4FY22-concall",
            "quote_span": f"revenue growth around {base_rev - 1}–{base_rev + 1}%",
            "as_of": "2023-05-15",
        }
    )
    rows.append(
        {
            "period": "FY24",
            "metric": "revenue_growth_pct",
            "guided_value": float(base_rev - 1),
            "guided_low": float(base_rev - 2),
            "guided_high": float(base_rev),
            "actual_value": float(base_rev - 1.2),
            "guided_text": f"Updating FY24 growth guidance to {base_rev - 2}–{base_rev}%.",
            "confidence": 0.92,
            "speaker": "CFO",
            "thread_id": thread,
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q4FY23-concall",
            "quote_span": f"{base_rev - 2}–{base_rev}%",
            "as_of": "2024-05-12",
        }
    )
    # Miss case
    rows.append(
        {
            "period": "FY25",
            "metric": "revenue_growth_pct",
            "guided_value": float(base_rev + 2),
            "guided_low": float(base_rev + 1),
            "guided_high": float(base_rev + 3),
            "actual_value": float(max(base_rev - 3, 1)),
            "guided_text": f"FY25 revenue growth guided {base_rev + 1}–{base_rev + 3}%.",
            "confidence": 0.88,
            "speaker": "CEO",
            "thread_id": thread,
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q4FY24-concall",
            "quote_span": f"{base_rev + 1}–{base_rev + 3}%",
            "as_of": "2025-05-10",
        }
    )
    # Margin met
    rows.append(
        {
            "period": "FY24",
            "metric": "ebitda_margin_pct",
            "guided_value": 18.0 + (h % 3),
            "guided_low": 17.5 + (h % 3),
            "guided_high": 18.5 + (h % 3),
            "actual_value": 18.2 + (h % 3),
            "guided_text": "EBITDA margin expected in the guided band.",
            "confidence": 0.85,
            "speaker": "CFO",
            "thread_id": f"{company_id}-margin",
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q2FY24-concall",
            "quote_span": "EBITDA margin",
            "as_of": "2023-11-01",
        }
    )
    rows.append(
        {
            "period": "FY25",
            "metric": "ebitda_margin_pct",
            "guided_value": 19.0 + (h % 3),
            "guided_low": 18.5 + (h % 3),
            "guided_high": 19.5 + (h % 3),
            "actual_value": 20.5 + (h % 3),
            "guided_text": "We expect further margin expansion next year.",
            "confidence": 0.8,
            "speaker": "CFO",
            "thread_id": f"{company_id}-margin",
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q4FY24-concall",
            "quote_span": "margin expansion",
            "as_of": "2025-05-10",
        }
    )
    # Capex — one dropped
    rows.append(
        {
            "period": "FY24",
            "metric": "capex_inr_cr",
            "guided_value": 2000.0 + h * 100,
            "guided_low": 1800.0 + h * 100,
            "guided_high": 2200.0 + h * 100,
            "actual_value": 2100.0 + h * 100,
            "guided_text": "Capex planned within the stated band for FY24.",
            "confidence": 0.75,
            "speaker": "CFO",
            "thread_id": f"{company_id}-capex",
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-AR-FY23",
            "quote_span": "Capex planned",
            "as_of": "2023-07-01",
        }
    )
    rows.append(
        {
            "period": "FY25",
            "metric": "capex_inr_cr",
            "guided_value": 2500.0 + h * 100,
            "guided_low": 2300.0 + h * 100,
            "guided_high": 2700.0 + h * 100,
            "actual_value": None,
            "guided_text": "Earlier FY25 capex guidance — management stopped reiterating.",
            "confidence": 0.7,
            "speaker": "CFO",
            "thread_id": f"{company_id}-capex",
            "dropped": True,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q1FY25-concall",
            "quote_span": "capex guidance",
            "as_of": "2024-08-01",
        }
    )
    # Sector-specific
    if sector == "Banks":
        rows.append(
            {
                "period": "FY25",
                "metric": "nim_pct",
                "guided_value": 3.5,
                "guided_low": 3.4,
                "guided_high": 3.6,
                "actual_value": 3.55,
                "guided_text": "NIM expected to stabilize near 3.4–3.6%.",
                "confidence": 0.82,
                "speaker": "CFO",
                "thread_id": f"{company_id}-nim",
                "dropped": False,
                "source_url": _ir(company_id, ticker),
                "source_ref": f"{ticker}-Q3FY25-concall",
                "quote_span": "3.4–3.6%",
                "as_of": "2025-01-20",
            }
        )
    else:
        rows.append(
            {
                "period": "FY25",
                "metric": "utilization_pct",
                "guided_value": 80.0 + h,
                "guided_low": 78.0 + h,
                "guided_high": 82.0 + h,
                "actual_value": 81.0 + h,
                "guided_text": "Utilization guided in the high-70s to low-80s.",
                "confidence": 0.78,
                "speaker": "CEO",
                "thread_id": f"{company_id}-util",
                "dropped": False,
                "source_url": _ir(company_id, ticker),
                "source_ref": f"{ticker}-Q3FY25-concall",
                "quote_span": "Utilization",
                "as_of": "2025-01-20",
            }
        )

    # Pending open guidance (no actual yet)
    rows.append(
        {
            "period": "FY26",
            "metric": "revenue_growth_pct",
            "guided_value": float(base_rev),
            "guided_low": float(base_rev - 1),
            "guided_high": float(base_rev + 1),
            "actual_value": None,
            "guided_text": f"FY26 growth guided {base_rev - 1}–{base_rev + 1}% — period not closed.",
            "confidence": 0.85,
            "speaker": "CFO",
            "thread_id": thread,
            "dropped": False,
            "source_url": _ir(company_id, ticker),
            "source_ref": f"{ticker}-Q4FY25-concall",
            "quote_span": f"{base_rev - 1}–{base_rev + 1}%",
            "as_of": "2026-05-01",
        }
    )
    return rows


def build_dataset() -> Dict[str, Any]:
    from app.data.hand_labeled import HAND_LABELED, HAND_LABELED_COMPANY_IDS
    from app.services.feature_flags import freeze_demo_pad

    companies = []
    outcomes: Dict[str, List[Dict[str, Any]]] = {}
    for cid, name, ticker, sector in SENSEX_30:
        quality = "hand_labeled" if cid in HAND_LABELED_COMPANY_IDS else "demo_structured"
        companies.append(
            {
                "id": cid,
                "name": name,
                "ticker": ticker,
                "sector": sector,
                "data_quality": quality,
            }
        )
        if cid in HAND_LABELED:
            labeled = copy.deepcopy(HAND_LABELED[cid])
            # Phase 1.6 — freeze demo pad when FREEZE_DEMO_PAD (default True)
            if not freeze_demo_pad() and len(labeled) < 8:
                filler = _make_outcomes(cid, ticker, sector)
                keys = {(r["period"], r["metric"], r.get("dropped")) for r in labeled}
                for row in filler:
                    key = (row["period"], row["metric"], row.get("dropped"))
                    if key in keys:
                        continue
                    row = dict(row)
                    row["guided_text"] = "[supplemental demo row] " + row["guided_text"]
                    row["confidence"] = min(float(row.get("confidence", 0.7)), 0.55)
                    labeled.append(row)
                    keys.add(key)
                    if len(labeled) >= 8:
                        break
            outcomes[cid] = labeled
        else:
            outcomes[cid] = _make_outcomes(cid, ticker, sector)

    # Nifty-50 extras beyond Sensex — demo until promoted into HAND_LABELED
    # (see docs/LABELING_RUNBOOK.md wave P0 / milestone M2→M3).
    from app.data.universe import NIFTY50_BEYOND_SENSEX

    sensex_ids = {c["id"] for c in companies}
    for cid, name, ticker, sector in NIFTY50_BEYOND_SENSEX:
        if cid in sensex_ids:
            continue
        quality = "hand_labeled" if cid in HAND_LABELED_COMPANY_IDS else "demo_structured"
        companies.append(
            {
                "id": cid,
                "name": name,
                "ticker": ticker,
                "sector": sector,
                "data_quality": quality,
            }
        )
        if cid in HAND_LABELED:
            outcomes[cid] = copy.deepcopy(HAND_LABELED[cid])
        else:
            outcomes[cid] = _make_outcomes(cid, ticker, sector)

    # Sentiment stubs for Wordmap integration (G13)
    sentiment = {
        cid: {
            "margin_expansion": 60 + (i % 30),
            "pricing_power": 55 + (i % 35),
            "demand_recovery": 50 + (i % 40),
            "working_capital": 40 + (i % 25),
        }
        for i, (cid, *_rest) in enumerate(SENSEX_30)
    }

    sample_transcripts = {
        "infy": (
            "CFO: Our guidance for growth for financial year '26 is 0% to 3% in constant currency terms. "
            "Our margin guidance for financial year 2026 is 20% to 22%. "
            "CEO: We had an excellent financial year 2025. Our revenues grew at 4.2% in constant currency terms."
        ),
        "reliance": (
            "CFO: Consolidated revenue expected to grow 10–12% YoY. "
            "EBITDA margin guided at about 15–16% for the year. "
            "Capex will stay within 1.2–1.4 lakh crore."
        ),
        "tcs": (
            "CEO: Financial year 2025 revenue grew by 4.2% in constant currency. "
            "Operating margin for the year came in at 24.3%. "
            "We expect FY26 to be better than FY25 based on the order book."
        ),
    }

    return {
        "companies": companies,
        "outcomes": outcomes,
        "sentiment": sentiment,
        "sample_transcripts": sample_transcripts,
        "reviews": [],
        "pending_extracts": [],
        "company_audit_flags": {},
        "api_keys": [
            {"key": "intellens-demo", "org": "demo", "role": "reviewer"},
            {"key": "intellens-admin", "org": "demo", "role": "admin", "platform_admin_role": "super"},
            {"key": "intellens-viewer", "org": "demo", "role": "viewer"},
            {"key": "intellens-retail", "org": "retail", "role": "viewer"},
            {"key": "intellens-onestop", "org": "onestop-demo", "role": "admin"},
            {"key": "intellens-onestop-labeler", "org": "onestop-demo", "role": "labeler"},
        ],
        "orgs": {
            "demo": {
                "name": "CiteAlpha Pilot Desk",
                "plan": "pilot",
                "account_type": "b2b",
                "seats": 5,
                "seats_used": 0,
                "csm": "Assigned at convert",
                "legal_entity": "Ocotillo Innovation Private Limited",
                "api_key_hint": "intellens-demo",
            },
            "onestop-demo": {
                "name": "CiteAlpha One-Stop Demo",
                "plan": "onestop",
                "account_type": "b2b",
                "seats": 40,
                "seats_used": 0,
                "csm": "Named CSM on convert",
                "legal_entity": "Ocotillo Innovation Private Limited",
                "api_key_hint": "intellens-onestop",
                "labeling_granted": True,
            },
            "retail": {
                "name": "CiteAlpha Retail (B2C)",
                "plan": "retail",
                "account_type": "retail",
                "seats": 10000,
                "seats_used": 0,
                "csm": "Self-serve retail",
                "legal_entity": "Ocotillo Innovation Private Limited",
                "api_key_hint": None,
            },
        },
        "labeling_queue": [],
    }


def outcome_from_dict(d: Dict[str, Any]) -> GuidanceOutcome:
    from app.data.metric_catalog import normalize_metric

    metric = normalize_metric(d.get("metric")) or d["metric"]
    return GuidanceOutcome(
        period=d["period"],
        metric=metric,
        guided_value=float(d["guided_value"]),
        actual_value=None if d.get("actual_value") is None else float(d["actual_value"]),
        guided_text=d.get("guided_text") or d.get("guidance_quote") or d.get("quote_span") or "",
        confidence=float(d.get("confidence", 1.0)),
        speaker=d.get("speaker", "CFO"),
        guided_low=None if d.get("guided_low") is None else float(d["guided_low"]),
        guided_high=None if d.get("guided_high") is None else float(d["guided_high"]),
        dropped=bool(d.get("dropped", False)),
        thread_id=d.get("thread_id"),
        source_url=d.get("source_url"),
        source_ref=d.get("source_ref"),
        quote_span=d.get("quote_span"),
        as_of=d.get("as_of"),
        doc_id=d.get("doc_id"),
        span_start=None if d.get("span_start") is None else int(d["span_start"]),
        span_end=None if d.get("span_end") is None else int(d["span_end"]),
        unmapped=bool(d.get("unmapped", False)),
        guidance_source_url=d.get("guidance_source_url"),
        guidance_source_ref=d.get("guidance_source_ref"),
        guidance_quote=d.get("guidance_quote"),
        guidance_as_of=d.get("guidance_as_of"),
        revisions=tuple(dict(r) for r in (d.get("revisions") or [])),
        reviewed_by=d.get("reviewed_by"),
        reviewed_at=d.get("reviewed_at"),
        citeable=None if d.get("citeable") is None else bool(d.get("citeable")),
        source_verified=None
        if d.get("source_verified") is None
        else bool(d.get("source_verified")),
        reporting_basis=d.get("reporting_basis"),
        actual_reporting_basis=d.get("actual_reporting_basis"),
        unit=d.get("unit"),
        actual_unit=d.get("actual_unit"),
        scope=d.get("scope"),
        actual_scope=d.get("actual_scope"),
    )


_DATA: Optional[Dict[str, Any]] = None
_PATH = Path(__file__).with_name("store.json")

# Customer-generated collections. store.json lives in the container and is rebuilt on every
# deploy, so with SQL auth these are mirrored to intellens_tenant_state (EFS/Postgres).
# GCI data (companies/outcomes/reviews/pending_extracts) is intentionally not mirrored.
TENANT_KEYS = (
    "orgs",
    "api_keys",
    "labeling_queue",
    "notes",
    "org_activity",
    "csm_tickets",
    "partner_feedback",
    "pilot_checklists",
    "pilot_requests",
    "radar_webhooks",
    "legal_attestations",
    "label_drafts",
)
_TENANT_SAVED: Dict[str, str] = {}


def _tenant_store_enabled() -> bool:
    from app.db.auth_db import use_db_auth

    return use_db_auth()


def _tenant_blob(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _restore_tenant_state(data: Dict[str, Any]) -> None:
    if not _tenant_store_enabled():
        return
    from app.db import auth_db

    for key, value in auth_db.load_tenant_state().items():
        if key not in TENANT_KEYS:
            continue
        _TENANT_SAVED[key] = _tenant_blob(value)
        if key == "api_keys":
            have = {row.get("key") for row in value}
            value = list(value) + [r for r in data.get("api_keys") or [] if r.get("key") not in have]
        data[key] = value


def _persist_tenant_state(data: Dict[str, Any]) -> None:
    if not _tenant_store_enabled():
        return
    from datetime import datetime, timezone

    from app.db import auth_db

    now = datetime.now(timezone.utc).isoformat()
    for key in TENANT_KEYS:
        if key not in data:
            continue
        blob = _tenant_blob(data[key])
        if _TENANT_SAVED.get(key) == blob:
            continue
        auth_db.put_tenant_state(key, data[key], now)
        _TENANT_SAVED[key] = blob


_DATA_LOCK = STORE_LOCK


def get_data() -> Dict[str, Any]:
    global _DATA
    if _DATA is not None:
        return _DATA
    # Published only once the stored citations are applied: a thread that reads a
    # half-loaded dataset sees promised rows without their quotes and scores them as None.
    with _DATA_LOCK:
        if _DATA is None:
            fresh = not _PATH.exists()
            data = build_dataset() if fresh else json.loads(_PATH.read_text())
            _restore_tenant_state(data)
            from app.services.guidance_review import apply_stored_binds
            from app.services.extract_pipeline import apply_extracted_outcomes

            apply_stored_binds(data)
            apply_extracted_outcomes(data)
            _ensure_nifty_seed_rows(data)
            _DATA = data
            if fresh:
                save_data()
    return _DATA


def _ensure_nifty_seed_rows(data: Dict[str, Any]) -> None:
    """Merge Nifty-extra demo GCI rows into an existing store without wiping crawl state."""
    fresh = build_dataset()
    have = {c["id"] for c in data.get("companies") or []}
    outcomes = data.setdefault("outcomes", {})
    added = False
    for c in fresh["companies"]:
        cid = c["id"]
        if cid in have:
            continue
        data["companies"].append(c)
        outcomes[cid] = fresh["outcomes"].get(cid, [])
        have.add(cid)
        added = True
    if added:
        _PATH.write_text(json.dumps(data, indent=2))


@locked
def save_data() -> None:
    data = get_data()
    _PATH.write_text(json.dumps(data, indent=2))
    _persist_tenant_state(data)


def reset_data() -> Dict[str, Any]:
    global _DATA
    _DATA = build_dataset()
    save_data()
    try:
        from app.services import labeling as lbl

        lbl.clear_sql_store()
    except Exception:
        pass
    return _DATA


def get_outcomes(company_id: str) -> List[GuidanceOutcome]:
    raw = get_data()["outcomes"].get(company_id, [])
    return [outcome_from_dict(d) for d in raw]


def list_companies() -> List[Dict[str, Any]]:
    return list(get_data()["companies"])


def clone_dataset() -> Dict[str, Any]:
    return copy.deepcopy(get_data())
