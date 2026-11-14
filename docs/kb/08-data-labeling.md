# 08 — Data & Labeling

## Quality flags

| Flag | Meaning | External cite? |
|---|---|---|
| `hand_labeled` | Human-audited guidance vs actuals + sources | Yes |
| `extracted_verified` | Dual-cited quotes verified in stored filings by the extract/bind jobs; provisional, not ranked | Yes (provisional) |
| `demo_structured` | Synthetic-but-realistic seed | Demo only |
| `market_scaffold` | Universe row without deep GCI | No dossier depth |

## In-product workbench

Desk `?tab=labeling` (feature `labeling`): draft → submit → second reviewer accept. APIs under `/api/labeling/drafts`. When `USE_DB_AUTH` is on, drafts persist in `intellens_label_drafts` (SQLite/Postgres); otherwise JSON store. Accept merges outcomes (with `reviewed_by` / `reviewed_at`) and may promote `demo_structured` / `listing_provisional` → `hand_labeled` only when `source_url` + `quote_span` exist. Each accept appends a `label_accept` row to `audit.json` (submitter + reviewer). Does **not** rewrite `hand_labeled.py`. Two-person rule: submitter ≠ accepter unless admin/owner. Published rows in `hand_labeled.py` are single-analyst (`reviewed_by=analyst:nv`); `/methodology` and the Trust Center say so. The two-person rule applies to new workbench accepts, not to that file. Trust Center (`/api/trust.labeling_governance`) counts real `label_accept` rows. Desk CSM shows submitter/reviewer **ids** (no emails). Public dossiers show “Checked against the source documents · {date}”. A row counts when the fetch finds both quotes; a miss drops the row and is not queued. from the latest scored row’s `reviewed_at`.

Quality partner feedback (`wrong_band` / `wrong_period` / `wrong_label` / `missing_source`) enqueues a high-priority labeling-queue item. **GCI is not mutated** by feedback.

Nightly source verification (`python -m app.jobs.verify_sources --write`, also from live refresh when `INTELLENS_VERIFY_SOURCES=1`) fetches every `source_url` / `guidance_source_url` and checks that the recorded quote is on the page. Failures set `citeable=false`, enqueue `kind=source_verify_fail`, and are counted on Trust (`/api/trust.source_verification`). Four HTML press pages that do not yield a verifiable quote (HCLTech FY26, Maruti FY25 volume, JSW Steel FY25, Grasim FY25 volumes) are excluded until re-cited to a filing PDF.

Priority enqueue `POST /api/labeling/queue` remains ops SLA (Desk), not HL promotion. The queue (GET/POST/PATCH) is scoped to the caller's org; only platform admins (e.g. `X-API-Key: $INTELLENS_API_KEY`) see or act across orgs via `?org_id=`.

CSV import uses `docs/labeling/outcome_row_template.csv` columns and still creates drafts.

## Daily guidance review

`guidance-reviewer` (`.cursor/agents/guidance-reviewer.md`) runs `python -m app.jobs.guidance_review`. The calendar rotates markets, one per UTC day. The API process runs it when `INTELLENS_GUIDANCE_REVIEW=1` (02:30 IST). Each stock is reviewed on its own catalog metrics (sector plus the metrics it already files). A citation is copied only when one sentence of an accepted filing names that metric, uses its unit, and contains the recorded band. Our own labelling notes (`guided_text`, source tags) are stripped from stored excerpts first and never confirm a number. A promise is cited only from a filing dated before the period is half run (`OPENING_SHARE`); a result only from one dated after the period ends; one promise per period and metric. The row is stamped `reviewed_by=job:guidance_review` only after both sides verify against that text. A row with no matching filing stays unscored. If a published GCI moves, the job appends the score ledger (`new_filing`) and a changelog entry.

## Hand-label workflow (repo)

1. Follow `docs/LABELING_PLAYBOOK.md` and the wave runbook `docs/LABELING_RUNBOOK.md`.
2. P0 batch (10 Nifty-extra `demo_structured`): `docs/labeling/batch_p0_nifty_extra.csv`.
3. Outcome sheet columns: `docs/labeling/outcome_row_template.csv`.
4. Enqueue M2: `./scripts/labeling-enqueue-m2.sh` · status: `./scripts/labeling-status.sh`.
5. Edit `backend/app/data/hand_labeled.py` (Nifty-extra ids promote when present; `seed.py` sets `hand_labeled`).
6. Prefer official IR guidance-vs-actuals tables when available.
7. Always: bands, `source_url`, `source_ref`, `quote_span`, `as_of`, and (when scoring) `guidance_*` plus `reviewed_by` / `reviewed_at`.
8. Delete `backend/app/data/store.json` after edits; re-run pytest.
9. Update `docs/ACCURACY_ASSESSMENT.md` when cohort quality changes.

## Provisional

`listing_provisional` = coverage only. The extract job may promote to `extracted_verified` when both quotes verify in stored filings. Human gold (`hand_labeled`) still goes through the labeling queue. Never flip a quality flag without those outcomes.

## Never

- Invent actuals or quotes.
- Silently overwrite hand_labeled with demo generators.
- Ship Buy/Hold language in labels.

## Skills

`citealpha-labeling`, `citealpha-phase0-labeling`
