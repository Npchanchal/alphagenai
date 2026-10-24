"""Daily guidance-quote and later-filing review for one market.

    python -m app.jobs.guidance_review
    python -m app.jobs.guidance_review --market US --dry-run
    python -m app.jobs.guidance_review --force

Markets rotate by calendar day (India, United States, United Kingdom, …).
The job copies a citation only when that sentence is already in an accepted filing.
It does not invent a quote or an actual. Rows with no matching filing stay unscored.
"""

from __future__ import annotations

import argparse
import json
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


def serve() -> None:
    """Walk India and US filings side by side, run today's market, then sleep until 02:30 IST each day."""
    try:
        from app.services.score_ledger import correct_release_withdrawals, record_methodology_release

        print(json.dumps({"ledger_corrections": correct_release_withdrawals()}), flush=True)
        print(json.dumps({"methodology_release": record_methodology_release()}), flush=True)
    except Exception as exc:  # noqa: BLE001 — the ledger step must not stop the walks
        print(json.dumps({"methodology_release": "error", "detail": type(exc).__name__}), flush=True)
    while True:
        # The two walks run side by side; shared stores are guarded by app.data.store_lock.
        us_walk = threading.Thread(target=_us_walk, name="us-coverage", daemon=True)
        us_walk.start()
        _india_walk()
        us_walk.join()
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
