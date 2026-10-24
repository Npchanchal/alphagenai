"""One-shot or looping GCI refresh: python -m app.jobs.gci_refresh [--loop] [--once]

Prefer --via-api in Docker so refresh mutates the API container store
(scheduler and api do not share a volume by default).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.services.refresh import refresh_interval_hours, run_gci_refresh


def _maybe_guidance_review() -> None:
    flag = os.environ.get("INTELLENS_GUIDANCE_REVIEW", "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return
    try:
        from app.services.guidance_review import run_daily

        print(json.dumps({"guidance_review": run_daily()}), flush=True)
    except Exception as exc:  # noqa: BLE001 — review queue must not stop the refresh loop
        print(json.dumps({"guidance_review": "error", "detail": type(exc).__name__}), flush=True)


def _maybe_india_coverage() -> None:
    try:
        from app.services.india_coverage import run_daily_from_env

        report = run_daily_from_env()
        if report is not None:
            print(json.dumps({"india_coverage": report}), flush=True)
    except Exception as exc:  # noqa: BLE001 — coverage walk must not stop refresh
        print(json.dumps({"india_coverage": "error", "detail": type(exc).__name__}), flush=True)
    try:
        from app.services.us_coverage import run_daily_from_env as run_us

        report = run_us()
        if report is not None:
            print(json.dumps({"us_coverage": report}), flush=True)
    except Exception as exc:  # noqa: BLE001 — the US walk must not stop refresh
        print(json.dumps({"us_coverage": "error", "detail": type(exc).__name__}), flush=True)


def _maybe_ledger_digest() -> None:
    flag = os.environ.get("INTELLENS_LEDGER_DIGEST", "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return
    try:
        from app.services.ledger_digest import send_weekly

        print(json.dumps({"ledger_digest": send_weekly()}), flush=True)
    except Exception as exc:  # noqa: BLE001 — digest must not stop the refresh loop
        print(json.dumps({"ledger_digest": "error", "detail": type(exc).__name__}), flush=True)


def _run_via_api(
    base_url: str,
    *,
    limit: int,
    live: Optional[bool],
    auto_extract: Optional[bool],
    warm_fmp: Optional[bool],
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/api/ingest/refresh"
    key = (
        os.environ.get("INTELLENS_API_KEY")
        or os.environ.get("API_KEY")
        or "intellens-demo"
    )
    body: Dict[str, Any] = {"limit": limit}
    if live is not None:
        body["live"] = live
    if auto_extract is not None:
        body["auto_extract"] = auto_extract
    if warm_fmp is not None:
        body["warm_fmp"] = warm_fmp
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"http_{exc.code}", "detail": detail}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": "url_error", "detail": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001 — keep scheduler loop alive
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Live GCI data refresh (IR crawl + extract queue)")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--loop", action="store_true", help="Repeat every INTELLENS_REFRESH_HOURS (default 6)")
    p.add_argument("--once", action="store_true", help="Single run (default if --loop not set)")
    p.add_argument("--live", action="store_true", default=None, help="Force live IR HTTP fetch")
    p.add_argument("--catalog", action="store_true", help="Force catalog-only (no live HTTP)")
    p.add_argument("--no-extract", action="store_true")
    p.add_argument("--no-fmp", action="store_true")
    p.add_argument(
        "--via-api",
        metavar="BASE_URL",
        default=None,
        help="POST /api/ingest/refresh on API (e.g. http://api:8000) instead of in-process",
    )
    args = p.parse_args(argv)

    live: Optional[bool] = None
    if args.catalog:
        live = False
    elif args.live:
        live = True

    auto_extract = False if args.no_extract else None
    warm_fmp = False if args.no_fmp else None
    via = args.via_api or os.environ.get("INTELLENS_REFRESH_VIA_API")

    def _run() -> dict:
        if via:
            return _run_via_api(
                via,
                limit=args.limit,
                live=live,
                auto_extract=auto_extract,
                warm_fmp=warm_fmp,
            )
        return run_gci_refresh(
            limit=args.limit,
            live=live,
            auto_extract=auto_extract,
            warm_fmp=warm_fmp,
        )

    if args.loop:
        hours = refresh_interval_hours()
        print(
            json.dumps(
                {
                    "scheduler": "start",
                    "interval_hours": hours,
                    "note": "Ctrl+C to stop",
                }
            ),
            flush=True,
        )
        while True:
            try:
                report = _run()
            except Exception as exc:  # noqa: BLE001
                report = {"ok": False, "error": type(exc).__name__, "detail": str(exc)}
            print(json.dumps(report, indent=2), flush=True)
            _maybe_guidance_review()
            _maybe_india_coverage()
            _maybe_ledger_digest()
            ok = bool(report.get("ok"))
            # Full cadence on success; short backoff on failure so a blip doesn't wait 6h
            sleep_s = int(hours * 3600) if ok else min(120, max(30, int(hours * 60)))
            print(
                json.dumps({"scheduler": "sleep", "seconds": sleep_s, "after_ok": ok}),
                flush=True,
            )
            time.sleep(sleep_s)
    else:
        report = _run()
        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(json.dumps({"scheduler": "stopped"}), flush=True)
        sys.exit(0)
