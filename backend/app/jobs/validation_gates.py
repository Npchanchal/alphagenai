"""Validation gates for the GCI and the guidance profile.

    python -m app.jobs.validation_gates            # human summary
    python -m app.jobs.validation_gates --json     # full report
    python -m app.jobs.validation_gates --strict   # exit 1 if a hard gate fails

Gates (methodology page, docs/kb/03-scoring.md):
  2  Label stability    profile labels flip for < 5% of companies when the latest period is removed
  3  Floor sensitivity  published levels under a grid of width floors; reported, judged by a person
  4  Extraction audit   double review of >= 200 stratified rows, >= 95% exact (human; read from file)
  7  Point in time      promise dated before result, revisions in between, review after (hard gate)

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


def run() -> Dict[str, Any]:
    companies = _scored_companies()
    gates = [
        gate_label_stability(companies),
        gate_floor_sensitivity(companies),
        gate_extraction_audit(),
        gate_point_in_time(companies),
    ]
    return {"gates": gates, "hard_fail": any(g["gate"] == 7 and g["passed"] is False for g in gates)}


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
