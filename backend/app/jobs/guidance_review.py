"""Daily guidance-quote and later-filing review for one market.

    python -m app.jobs.guidance_review
    python -m app.jobs.guidance_review --market US --dry-run
    python -m app.jobs.guidance_review --force

Markets rotate by calendar day (India, United States, United Kingdom, …).
The job copies a citation only when that sentence is already in an accepted filing.
It does not invent a quote or an actual. Rows with no matching filing stay unscored.

On AWS the API task runs ``serve()`` when ``INTELLENS_GUIDANCE_REVIEW=1``: each day it
walks India and US filings, copies new stored filings to S3, then reviews one market.
A separate archive timer also copies to S3 on an interval so a long walk does not leave
a backlog until the next morning.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import date
from typing import List, Optional

from app.services.guidance_review import run_daily, seconds_until_next_run


def _india_walk() -> None:
    try:
        from app.services.india_coverage import run_daily_from_env

        coverage = run_daily_from_env()
        if coverage is not None:
            print(json.dumps({"india_coverage": coverage}), flush=True)
    except Exception as exc:  # noqa: BLE001 — coverage roll must not stop the review
        print(json.dumps({"india_coverage": "error", "detail": type(exc).__name__}), flush=True)


def _us_walk() -> None:
    try:
        from app.services.us_coverage import run_daily_from_env as run_us

        us = run_us()
        if us is not None:
            print(json.dumps({"us_coverage": us}), flush=True)
    except Exception as exc:  # noqa: BLE001 — the US walk must not stop the review
        print(json.dumps({"us_coverage": "error", "detail": type(exc).__name__}), flush=True)


def _archive_walk() -> None:
    try:
        from app.services.filing_archive import archive_pending

        report = archive_pending()
        if report.get("status") != "off":
            print(json.dumps({"filing_archive": report}), flush=True)
    except Exception as exc:  # noqa: BLE001 — the S3 copy must not stop the review
        print(json.dumps({"filing_archive": "error", "detail": type(exc).__name__}), flush=True)


def archive_interval_sec() -> int:
    """How often the S3 copy runs while a long India walk is still open (default 2 hours)."""
    try:
        return max(300, int(os.environ.get("INTELLENS_FILING_ARCHIVE_INTERVAL_SEC", "7200")))
    except ValueError:
        return 7200


def _archive_cron() -> None:
    """Copy newly stored filings to S3 on a timer so the backlog does not wait for the walk to end."""
    while True:
        time.sleep(archive_interval_sec())
        print(json.dumps({"filing_archive": "cron", "interval_sec": archive_interval_sec()}), flush=True)
        _archive_walk()


def serve() -> None:
    """Walk India and US filings side by side, archive to S3, run today's market, sleep until 02:30 IST."""
    try:
        from app.services.score_ledger import correct_release_withdrawals, record_methodology_release

        print(json.dumps({"ledger_corrections": correct_release_withdrawals()}), flush=True)
        print(json.dumps({"methodology_release": record_methodology_release()}), flush=True)
    except Exception as exc:  # noqa: BLE001 — the ledger step must not stop the walks
        print(json.dumps({"methodology_release": "error", "detail": type(exc).__name__}), flush=True)
    threading.Thread(target=_archive_cron, name="filing-archive-cron", daemon=True).start()
    # Clear any backlog left from the previous day before the walks start.
    _archive_walk()
    while True:
        # The two walks run side by side; shared stores are guarded by app.data.store_lock.
        us_walk = threading.Thread(target=_us_walk, name="us-coverage", daemon=True)
        us_walk.start()
        _india_walk()
        us_walk.join()
        _archive_walk()
        try:
            report = run_daily()
        except Exception as exc:  # noqa: BLE001 — keep the daily loop alive
            report = {"ok": False, "error": type(exc).__name__, "detail": str(exc)}
        print(json.dumps({"guidance_review": report}), flush=True)
        delay = seconds_until_next_run()
        print(json.dumps({"guidance_review": "sleep", "seconds": delay}), flush=True)
        time.sleep(delay)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", default=None, help="Market id, e.g. IN or US. Default: today's rotation.")
    parser.add_argument("--date", default=None, help="ISO date for the rotation. Default: today UTC.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Run even if this calendar day already ran.")
    parser.add_argument("--loop", action="store_true", help="Keep running; fire every day at 02:30 IST.")
    args = parser.parse_args(argv)
    if args.loop:
        serve()
        return 0
    day = date.fromisoformat(args.date) if args.date else None
    report = run_daily(day=day, market_id=args.market, dry_run=args.dry_run, force=args.force)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
