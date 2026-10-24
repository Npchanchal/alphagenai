"""CLI: python -m app.jobs.extract_india_guidance [--cohort nifty50] [--limit N]

Writer: ``disclosures.process_company`` (verbatim guidance and a later actual).
Does not call ``extract_pipeline.extract_company``. A paused or unconfigured
model leaves filings unread.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from app.services.india_coverage import cohort_ids, process_company


def walk(company_ids: List[str]) -> dict:
    """Read stored filings for these companies through the disclosure writer."""
    results = [process_company(cid, live=False, extract=True, discover=False) for cid in company_ids]
    return {
        "ok": True,
        "writer": "disclosures",
        "companies": len(company_ids),
        "results": results,
    }


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Extract India guidance from accepted filings")
    p.add_argument("--cohort", default="nifty50", choices=["nifty50", "in1000", "nse_all", "bse_only", "all"])
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-relabel", action="store_true", help="Accepted for compatibility; the disclosure writer has no relabel pass")
    args = p.parse_args(argv)
    ids = cohort_ids(args.cohort)
    if args.limit:
        ids = ids[: args.limit]
    report = walk(ids)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
