"""Copy stored filings and transcripts to the per-exchange S3 buckets.

    python -m app.jobs.archive_filings --dry-run
    python -m app.jobs.archive_filings --limit 500

Reads the document store only. A document already in the archive ledger is not uploaded again.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from app.services.filing_archive import archive_pending


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="At most this many documents, newest first.")
    parser.add_argument("--dry-run", action="store_true", help="Count what would be uploaded, per exchange.")
    args = parser.parse_args(argv)
    report = archive_pending(limit=args.limit, dry_run=args.dry_run)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report.get("status") in ("ok", "dry_run", "off") else 1


if __name__ == "__main__":
    raise SystemExit(main())
