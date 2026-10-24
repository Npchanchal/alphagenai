"""Process new filings for CiteAlpha Analyst Monitors.

    python -m app.jobs.analyst_monitors            # process up to 50 new filings
    python -m app.jobs.analyst_monitors --status   # baseline / seen counts only
    python -m app.jobs.analyst_monitors --no-email

The first run records the current corpus as a baseline and runs nothing.
"""

from __future__ import annotations

import argparse
import json

from app.services.agent import monitors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--no-email", action="store_true")
    args = ap.parse_args()
    if args.status:
        print(json.dumps(monitors.status(), indent=2))
        return
    res = monitors.process_new_documents(limit=args.limit, deliver=not args.no_email)
    print(json.dumps({k: res.get(k) for k in ("baselined", "processed", "pending", "runs")}, indent=2))


if __name__ == "__main__":
    main()
