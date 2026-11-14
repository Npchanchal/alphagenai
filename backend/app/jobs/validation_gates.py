"""Validation gates for the GCI and the guidance profile.

    python -m app.jobs.validation_gates            # human summary
    python -m app.jobs.validation_gates --json     # full report
    python -m app.jobs.validation_gates --strict   # exit 1 if a hard gate fails

Gates (methodology page, docs/kb/03-scoring.md):
  2  Label stability    profile labels flip for < 5% of companies when the latest period is removed
  3  Floor sensitivity  published levels under a grid of width floors; reported, judged by a person
  4  Extraction audit   double review of >= 200 stratified rows, >= 95% exact (human; read from file)
  7  Point in time      promise dated before result, revisions in between, review after (hard gate)
  8  GCI Core shadow    v4 level beside the Core level per company; Core must replay identically

Gates 5 and 6 (event study, out-of-sample lift for advanced models) wait until the
established tier covers enough companies to power them.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from app.services import gci_scoring
from app.services.gci_scoring import GuidanceOutcome
from app.services.guidance_profile import closed_rows, in_year_revisions, results_vs_range

FLIP_LIMIT = 0.05
EXTRACTION_MIN_N = 200
EXTRACTION_MIN_EXACT = 0.95
RATE_FLOOR_GRID = (0.05, 0.10, 0.25, 0.50)
LEVEL_FLOOR_GRID = (0.01, 0.02)
EXTRACTION_AUDIT_PATH = Path(__file__).resolve().parents[1] / "data" / "extraction_audit.json"


def _scored_companies() -> Dict[str, List[GuidanceOutcome]]:
    from app.data.seed import get_outcomes, list_companies
    from app.services.score_policy import is_scoreable

    return {
        c["id"]: get_outcomes(c["id"])
        for c in list_companies()
        if is_scoreable(c.get("data_quality"))
    }


def _profile_labels(rows: Sequence[GuidanceOutcome]) -> Dict[str, Optional[str]]:
    closed = closed_rows(rows)
    return {
        "results": results_vs_range(closed)["label"],
        "revisions": in_year_revisions(closed)["label"],
    }


def gate_label_stability(companies: Dict[str, List[GuidanceOutcome]]) -> Dict[str, Any]:
    from app.services.changes import sort_periods

    checked = flips = 0
    detail = []
    for cid, rows in companies.items():
        periods = sort_periods(list({o.period for o in closed_rows(rows)}))
        if len(periods) < 2:
            continue
        full = _profile_labels(rows)
        if not any(full.values()):
            continue
        trimmed = _profile_labels([o for o in rows if o.period != periods[-1]])
        checked += 1
        changed = [k for k in full if full[k] != trimmed[k]]
        if changed:
            flips += 1
            detail.append({"company_id": cid, "changed": changed, "full": full, "trimmed": trimmed})
    rate = flips / checked if checked else None
    return {
        "gate": 2,
        "name": "Label stability",
        "companies_with_labels": checked,
        "flips": flips,
        "flip_rate": rate,
        "passed": None if rate is None else rate < FLIP_LIMIT,
        "not_run": rate is None,
        "detail": detail,
        "note": "No company has six closed figures yet, so no labels to test." if not checked else "",
    }


@contextmanager
def _floors(rate_pp: float, level_frac: float) -> Iterator[None]:
    saved = (gci_scoring.RATE_FLOOR_PP, gci_scoring.LEVEL_FLOOR_FRAC)
    gci_scoring.RATE_FLOOR_PP, gci_scoring.LEVEL_FLOOR_FRAC = rate_pp, level_frac
    try:
        yield
    finally:
        gci_scoring.RATE_FLOOR_PP, gci_scoring.LEVEL_FLOOR_FRAC = saved


def gate_floor_sensitivity(companies: Dict[str, List[GuidanceOutcome]]) -> Dict[str, Any]:
    grid = [(r, f) for r in RATE_FLOOR_GRID for f in LEVEL_FLOOR_GRID]
    table: Dict[str, Dict[str, Optional[float]]] = {}
    for cid, rows in companies.items():
        cells: Dict[str, Optional[float]] = {}
        for rate_pp, level_frac in grid:
            with _floors(rate_pp, level_frac):
                cells[f"{rate_pp:.2f}pp/{level_frac:.0%}"] = gci_scoring.compute_gci_v3_detail(
                    rows, version="v4"
                ).gci
        if any(v is not None for v in cells.values()):
            table[cid] = cells
    swings = {
        cid: round(max(v for v in cells.values() if v is not None) - min(v for v in cells.values() if v is not None), 1)
        for cid, cells in table.items()
    }
    current = f"{gci_scoring.RATE_FLOOR_PP:.2f}pp/{gci_scoring.LEVEL_FLOOR_FRAC:.0%}"
    return {
        "gate": 3,
        "name": "Floor sensitivity",
        "current": current,
        "levels": table,
        "max_swing": swings,
        "passed": None,
        "note": "Reported for review. A floor change that moves a published level needs a ledger row.",
    }


def gate_extraction_audit(path: Path = EXTRACTION_AUDIT_PATH) -> Dict[str, Any]:
    base = {"gate": 4, "name": "Extraction audit"}
    if not path.exists():
        return {**base, "passed": None, "not_run": True, "n": 0, "note": f"Record results in {path.name}."}
    rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
    n = len(rows)
    exact = sum(1 for r in rows if r.get("guided_match") and r.get("actual_match"))
    share = exact / n if n else 0.0
    return {
        **base,
        "n": n,
        "exact": exact,
        "exact_share": round(share, 3),
        "passed": n >= EXTRACTION_MIN_N and share >= EXTRACTION_MIN_EXACT,
        "note": "" if n >= EXTRACTION_MIN_N else f"Sample below {EXTRACTION_MIN_N} rows.",
    }


def pit_violations(rows: Sequence[GuidanceOutcome]) -> List[str]:
    """Problems that would mean a score used information before it existed."""
    out: List[str] = []
    for o in closed_rows(rows):
        tag = f"{o.period} {o.metric}"
        promise, result = o.guidance_as_of, o.as_of
        if promise and result and promise > result:
            out.append(f"{tag}: guidance dated {promise} after the result filing {result}")
        for rev in o.revisions or ():
            when = str(rev.get("as_of") or "")
            if when and promise and when < promise:
                out.append(f"{tag}: revision {when} before the opening guidance {promise}")
            if when and result and when > result:
                out.append(f"{tag}: revision {when} after the result filing {result}")
        if o.reviewed_at and result and o.reviewed_at < result:
            out.append(f"{tag}: reviewed {o.reviewed_at} before the result filing {result}")
    return out


def gate_point_in_time(companies: Dict[str, List[GuidanceOutcome]]) -> Dict[str, Any]:
    from app.data import doc_store

    found: Dict[str, List[str]] = {}
    for cid, rows in companies.items():
        problems = pit_violations(rows)
        if problems:
            found[cid] = problems
    late_docs = [
        d["doc_id"]
        for d in doc_store.list_documents(include_rejected=True)
        if d.get("ingested_at") and d.get("date") and str(d["ingested_at"])[:10] < str(d["date"])
    ]
    n = sum(len(v) for v in found.values()) + len(late_docs)
    return {
        "gate": 7,
        "name": "Point in time",
        "violations": n,
        "rows": found,
        "documents_ingested_before_filing_date": late_docs,
        "passed": n == 0,
    }


def issuance_times(rows: Sequence[GuidanceOutcome]) -> Dict[str, str]:
    """Stored public-availability date per guidance source URL. Reads the store; never fetches."""
    from app.data import doc_store

    urls = {o.guidance_source_url for o in rows} | {
        r.get("source_url") for o in rows for r in (o.revisions or ())
    }
    out: Dict[str, str] = {}
    for url in sorted(u for u in urls if u):
        held = doc_store.find_by_url(url)
        if held and held.get("public_available_at"):
            out[url] = str(held["public_available_at"])[:10]
    return out


def core_inputs(
    company_id: str,
    rows: Optional[Sequence[GuidanceOutcome]] = None,
    *,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Keyword arguments for ``compute_core_detail`` — the one place Core inputs are gathered."""
    from datetime import date

    from app.data.markets import company_market_id
    from app.data.seed import get_outcomes, list_companies
    from app.services.commitment_store import list_commitments
    from app.services.guidance_flags import applied_audit_flags

    company = next((c for c in list_companies() if c["id"] == company_id), None) or {}
    outcomes = list(rows if rows is not None else get_outcomes(company_id))
    return {
        "outcomes": outcomes,
        "company_id": company_id,
        "market_id": company_market_id(company or None),
        "regime": company.get("accounting_regime"),
        "fy_end_mmdd": company.get("fy_end_mmdd"),
        "audit_flags": applied_audit_flags(company_id),
        "commitments": list_commitments(company_id, include_unreviewed=False),
        "as_of": as_of or date.today().isoformat(),
        "issuance_times": issuance_times(outcomes),
    }


def core_shadow_rows(companies: Dict[str, List[GuidanceOutcome]]) -> List[Dict[str, Any]]:
    """Published v4 level beside GCI Core (locked v2.4), v2.4-R2, the delivery ruleset and the v2.5 proposals."""
    out: List[Dict[str, Any]] = []
    for cid, rows in sorted(companies.items()):
        kw = core_inputs(cid, rows)
        outcomes = kw.pop("outcomes")
        market = kw["market_id"]
        v4 = gci_scoring.compute_gci_v3_detail(outcomes, audit_flags=kw["audit_flags"], version="v4").gci
        core = gci_scoring.compute_core_detail(outcomes, ruleset=gci_scoring.CORE_RULESET_LOCKED, **kw)
        again = gci_scoring.compute_core_detail(outcomes, ruleset=gci_scoring.CORE_RULESET_LOCKED, **kw)
        r2 = gci_scoring.compute_core_detail(outcomes, ruleset=gci_scoring.CORE_RULESET_R2, **kw)
        delivery = gci_scoring.compute_core_detail(outcomes, ruleset=gci_scoring.CORE_RULESET_DELIVERY, **kw)
        proposal = gci_scoring.compute_core_detail(outcomes, ruleset=gci_scoring.CORE_RULESET_PROPOSAL, **kw)
        level = core["composite_gci"]
        diff = None if v4 is None or level is None else round(level - v4, 1)
        out.append(
            {
                "company_id": cid,
                "market_id": market,
                "v4_gci": v4,
                "core_gci": level,
                "core_basis": core["composite_basis"],
                "core_quant_gci": core["quant_gci"],
                "core_qual_low": core["qual_low"],
                "core_qual_high": core["qual_high"],
                "r2_gci": r2["headline_gci"],
                "r2_headline_rule": r2["headline_rule"],
                "delivery_gci": delivery["composite_gci"],
                "proposal_gci": proposal["composite_gci"],
                "difference": diff,
                "core_tier": core["confidence_tier"],
                "core_status": core["calculation_status"],
                "publication_status": core["publication_status"],
                "reason_counts": core["reason_counts"],
                "deterministic": core["input_digest"] == again["input_digest"]
                and core["composite_exact"] == again["composite_exact"]
                and core["quant_gci_exact"] == again["quant_gci_exact"],
            }
        )
    return out


#: O-02: share of quant-routed families that must compute before a Core level may publish.
CORE_MIN_COMPUTABLE_SHARE = 0.6
#: Gates a person signs off outside the code; each points at its checklist section.
CORE_MANUAL_GATES = (
    ("G-05", "Security review, backups and restore test", "security"),
    ("G-06", "Legal and compliance review: terminology, disclaimers, data licences", "legal"),
    ("G-07", "API documentation for every Core route", "api-docs"),
    ("G-08", "Support process for data-correction requests", "support"),
)
CORE_CHECKLIST = "docs/review/GCI_Core_Release_Checklist.md"


def core_release_gates(company_id: str, *, ruleset: Optional[str] = None, signed_off: Sequence[str] = ()) -> Dict[str, Any]:
    """WF-06: every gate a Core level must pass before a publication request can be approved."""
    from app.services import score_ledger
    from app.services.score_policy import RANKABLE_TIERS

    kw = core_inputs(company_id)
    outcomes = kw.pop("outcomes")
    rs = ruleset or gci_scoring.CORE_DEFAULT_RULESET
    first = gci_scoring.compute_core_detail(outcomes, ruleset=rs, **kw)
    again = gci_scoring.compute_core_detail(outcomes, ruleset=rs, **kw)
    # Replay from the serialised snapshot, as a licensee would, not from the objects in memory.
    replay = score_ledger.replay_payload(score_ledger.snapshot_payload(
        company_id,
        as_of=kw["as_of"],
        algorithm_id=first["algorithm_id"],
        dataset_version="pending",
        gci=first["headline_gci"],
        confidence_tier=first["confidence_tier"],
    ))
    share = first["coverage"]["computable_share"]
    pending = {c: n for c, n in first["reason_counts"].items() if c in ("UNREVIEWED", "PENDING_GUIDANCE_CITE", "QUOTE_OFFSET_MISMATCH")}
    gates: List[Dict[str, Any]] = [
        {
            "id": "G-01",
            "name": "Methodology version approved for publication",
            "passed": gci_scoring.CORE_ENGINE_APPROVED,
            "detail": f"{first['algorithm_id']} ({gci_scoring.CORE_REVISION})",
        },
        {
            "id": "G-02",
            "name": "Calculation replays identically",
            "passed": first["input_digest"] == again["input_digest"]
            and first["headline_exact"] == again["headline_exact"]
            and replay["matches"],
            "detail": f"{first['input_digest']}; snapshot replay {replay['replayed_gci']} vs {first['headline_gci']}",
        },
        {
            "id": "G-03",
            "name": "Coverage and confidence tier",
            "passed": first["headline_gci"] is not None
            and share is not None
            and share >= CORE_MIN_COMPUTABLE_SHARE
            and first["confidence_tier"] in RANKABLE_TIERS,
            "detail": f"computable share {share}, minimum {CORE_MIN_COMPUTABLE_SHARE}; tier {first['confidence_tier']}",
        },
        {
            "id": "G-04",
            "name": "Every guidance row reviewed and dual-cited",
            "passed": not pending,
            "detail": pending or "none pending",
        },
    ]
    for gid, name, section in CORE_MANUAL_GATES:
        gates.append({
            "id": gid,
            "name": name,
            "passed": gid in signed_off,
            "manual": True,
            "detail": f"{CORE_CHECKLIST}#{section}",
        })
    return {
        "company_id": company_id,
        "ruleset": rs,
        "algorithm_id": first["algorithm_id"],
        "level": first["headline_gci"],
        "passed": all(g["passed"] for g in gates),
        "failed": [g["id"] for g in gates if not g["passed"]],
        "gates": gates,
    }


def gate_core_shadow(companies: Dict[str, List[GuidanceOutcome]]) -> Dict[str, Any]:
    rows = core_shadow_rows(companies)
    compared = [r for r in rows if r["difference"] is not None]
    nondeterministic = [r["company_id"] for r in rows if not r["deterministic"]]
    future = [r["company_id"] for r in rows if r["reason_counts"].get("FUTURE_SOURCE")]
    return {
        "gate": 8,
        "name": "GCI Core shadow",
        "compared": len(compared),
        "mean_abs_difference": round(sum(abs(r["difference"]) for r in compared) / len(compared), 1)
        if compared
        else None,
        "nondeterministic": nondeterministic,
        "future_source": future,
        "rows": rows,
        # Hard failures block promotion; otherwise a person decides from the table.
        "passed": False if nondeterministic else None,
        "note": (
            "Core is shadow. Promotion needs this table reviewed, a ledger snapshot, and a "
            "methodology changelog entry (docs/PLAN_GCI_CORE.md)."
        ),
    }


def run() -> Dict[str, Any]:
    companies = _scored_companies()
    gates = [
        gate_label_stability(companies),
        gate_floor_sensitivity(companies),
        gate_extraction_audit(),
        gate_point_in_time(companies),
        gate_core_shadow(companies),
    ]
    hard = any(g["gate"] in (7, 8) and g["passed"] is False for g in gates)
    return {"gates": gates, "hard_fail": hard}


def _summary(report: Dict[str, Any]) -> str:
    lines = []
    for g in report["gates"]:
        state = "not run" if g.get("not_run") else {True: "pass", False: "FAIL", None: "for review"}[g["passed"]]
        lines.append(f"Gate {g['gate']} ({g['name']}): {state}")
        if g.get("note"):
            lines.append(f"  {g['note']}")
        if g["gate"] == 3:
            for cid, swing in g["max_swing"].items():
                lines.append(f"  {cid}: swing {swing} pts across the grid")
        if g["gate"] == 7 and g["violations"]:
            for cid, problems in g["rows"].items():
                lines.extend(f"  {cid}: {p}" for p in problems)
        if g["gate"] == 8:
            for r in g["rows"]:
                if r["v4_gci"] is not None or r["core_gci"] is not None:
                    lines.append(f"  {r['company_id']}: v4 {r['v4_gci']} · Core {r['core_gci']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    report = run()
    if args.json:
        json.dump(report, sys.stdout, indent=1)
        sys.stdout.write("\n")
    else:
        print(_summary(report))
    return 1 if args.strict and report["hard_fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
