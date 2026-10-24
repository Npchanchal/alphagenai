"""CLI: python -m app.jobs.classify_india_coverage [--cohort nifty50] [--limit N]

    python -m app.jobs.classify_india_coverage --live --company tcs infy

Walks a cohort (or named companies), optionally ingesting/extracting, and stamps
coverage_status. With --live, filings since 2022 are read and promises matched to results.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from app.services import disclosures
from app.services.india_coverage import COHORTS, roll_cohort, universe_coverage


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Classify India listing GCI coverage")
    p.add_argument("--cohort", default="nifty50", choices=[*COHORTS, "all"])
    p.add_argument("--company", nargs="*", default=None, help="Listing ids; overrides --cohort")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--live", action="store_true")
    p.add_argument("--no-extract", action="store_true")
    p.add_argument("--no-discover", action="store_true", help="With --live, skip NSE discovery")
    p.add_argument("--summary", action="store_true", help="Print universe tallies only")
    args = p.parse_args(argv)
    if args.summary:
        print(json.dumps(universe_coverage(), indent=2))
        return 0
    report = roll_cohort(
        args.cohort,
        limit=args.limit,
        live=args.live,
        extract=not args.no_extract,
        discover=args.live and not args.no_discover,
        company_ids=args.company or None,
    )
    if args.live:
        report["ledger_rows"] = disclosures.log_moves(
            [r["company_id"] for r in report.get("results") or []],
            lead="Filing walk read exchange filings since 2022 and matched promises to reported results.",
        )
    slim = {k: v for k, v in report.items() if k != "results"}
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
