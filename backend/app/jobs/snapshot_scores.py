"""Snapshot published GCI levels into the score ledger.

    python -m app.jobs.snapshot_scores                 # print current levels (JSON), no write
    python -m app.jobs.snapshot_scores --write \
        --reason methodology --note "..." --by analyst:nv   # append changed levels

Rule `index-integrity`: run before and after any change that can move a number.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from app.services import repository, score_ledger


def current_levels() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in repository.list_company_summaries():
        out.append(
            {
                "company_id": c.id,
                "ticker": c.ticker,
                "gci": c.gci_score,
                "confidence_tier": c.confidence_tier,
                "closed_periods": c.closed_periods,
                "metrics_scored": c.metrics_scored,
                "as_of": c.as_of,
                "algorithm_id": c.algorithm_id,
                "data_quality": c.data_quality,
            }
        )
    return out


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="append changed levels to the ledger")
    ap.add_argument("--reason", default="snapshot", choices=score_ledger.REASONS)
    ap.add_argument("--note", default="")
    ap.add_argument("--by", default="job:snapshot_scores")
    ap.add_argument("--as-of", default=None, help="ISO date; default today (UTC)")
    args = ap.parse_args(argv)

    if not args.write:
        json.dump(current_levels(), sys.stdout, indent=1)
        sys.stdout.write("\n")
        return 0

    rows = score_ledger.snapshot_rows(
        reason=args.reason, note=args.note, by=args.by, as_of=args.as_of
    )
    n = score_ledger.append_many(rows)
    from app.data import audit_log

    audit_log.record(
        "score_recalculation",
        actor=args.by,
        role="system",
        detail={"reason": args.reason, "changed": len(rows), "appended": n, "as_of": args.as_of},
    )
    json.dump(
        {"appended": n, "rows": [r.to_json() for r in rows]},
        sys.stdout,
        indent=1,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
