---
name: citealpha-guidance-review
description: >-
  Binds guidance quotes and later-filing quotes from accepted filings, one
  market per day, with no analyst step. Use when checking a promise citation,
  a result filing, a source_unverified row, or the daily guidance review job.
---

# Guidance review

A row is scored only when both sides are cited from filing text already stored: the guidance statement and the later filing that reports the actual.

## Schedule

The API process runs the job when `INTELLENS_GUIDANCE_REVIEW=1`. Docker Compose and the ECS task set that flag. At startup the job runs today's market, then sleeps until 02:30 IST (21:00 UTC). A stamp file stops a second write the same UTC day.

```bash
cd backend && PYTHONPATH=. python -m app.jobs.guidance_review --dry-run
cd backend && PYTHONPATH=. python -m app.jobs.guidance_review --market IN --dry-run
```

The calendar rotates `IN → US → GB → JP → HK → CN → EU → SG → AU → KR → BR → CA`, one market per UTC day. Do not install a crontab entry.

## What it binds

Hand-labeled companies in that market only.

Each stock is reviewed on its own parameter set: core catalog metrics, plus the sector metrics in `metric_catalog.py` for that company's sector (a bank includes NIM and loan growth; an IT company includes constant-currency revenue and R&D, not NIM). Metrics the stock already files are included even when the sector label does not list them.

A row files only when one sentence of the accepted filing names that metric, uses its unit (`%` / percent for a percent metric, crore / Rs / INR for capex), and contains every recorded band endpoint when the row has both. Stored excerpts carry our `guided_text` and source tag beside the filing quote; those are stripped first and never confirm a number, and only the filing sentence is copied. A promise is cited only from a filing dated before the period is half run; a result only from one dated after the period ends. One promise per period and metric. The guided number has to be a promise: a band, or a figure different from the reported actual. A result copied into the guidance fields stays unscored. Generated "Auto corpus pack" documents are not filings. The four HTML press pages that failed source verification stay unscored. An open period is left open.

| Gap | What the job does |
|---|---|
| `missing_guidance_cite` | Copies `guidance_quote` when the filing names this metric and contains its guided number, in the metric's unit |
| `missing_later_filing` | Copies `quote_span` when the results filing names this metric and contains `actual_value` in that unit |
| `awaiting_later_filing` | Leaves the row. No actual is invented |
| `source_unverified` | Points the row at an accepted filing only when that filing contains the recorded quote and satisfies the metric rule |

`reviewed_by` is `job:guidance_review` only when both quotes are in accepted filing text. Anything else stays unscored. If a published GCI moves, the job appends the score ledger (`new_filing`) and a changelog entry. Bound rows are also written to `guidance_review_outcomes.json` on `INTELLENS_DATA_DIR`, and reloaded after a new image replaces `store.json`.
