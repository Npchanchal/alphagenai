"""Walk S&P 500 results releases on SEC EDGAR since 2022, read them, and reconcile.

    python -m app.jobs.us_coverage --company us_nvda us_cat
    python -m app.jobs.us_coverage --limit 25

Reads text only (8-K Exhibit 99). A number publishes only when the promise and
the result are both quoted word for word from the stored releases.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from app.services import disclosures
from app.services.us_coverage import process_company, roll_daily


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--company", nargs="*", default=None, help="US listing ids, e.g. us_nvda")
    ap.add_argument("--limit", type=int, default=None, help="Walk at most N names")
    args = ap.parse_args(argv)
    if args.company:
        results = [process_company(cid) for cid in args.company]
        ledger = disclosures.log_moves(
            args.company,
            lead="Filing walk read SEC results releases since 2022 and matched promises to reported results.",
        )
        print(json.dumps({"ok": True, "results": results, "ledger_rows": ledger}, indent=1, default=str))
        return 0
    report = roll_daily(max_companies=args.limit)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
