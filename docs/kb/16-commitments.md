# 16 — Commitment Record

Dated, checkable commitments that are **not** numeric GCI guidance: commissioning dates, capex, deleveraging, order book, launches, corporate actions, operational and ESG targets. Plan: `docs/PLAN_CITEALPHA_ANALYST.md` §3.

**Never part of the GCI.** No ledger or changelog entry is needed for commitment changes; the GCI does not read this store (`test_commitments_do_not_change_gci`).

## Code

| Piece | File |
|---|---|
| Pure rules: types, states, Indian fiscal `period_end`, transitions, quiet-drop detection, plain-count summary | `backend/app/services/commitments.py` |
| Store (JSON, `INTELLENS_DATA_DIR/commitments.json`) | `backend/app/services/commitment_store.py` |
| Extractors `heuristic_v1` / `llm_v1` (verbatim-quote check) | `backend/app/services/commitment_extract.py` |
| Disclosure cycles + quiet-drop proposals | `backend/app/services/commitment_monitor.py` |
| Routes | `backend/app/api/analyst_routes.py` |
| Tests | `backend/tests/test_commitments.py` |

## Governance

1. Proposals land `unreviewed` (labeler, extractor or manual).
2. Only `reviewer` / `admin` / `owner` with `labeling` can accept, reject or close.
3. Every closing state needs a proof citation (quote, link, date). `quietly_dropped` needs two silent disclosure cycles after the last mention.
4. Public reads show accepted rows only. Summary is a sentence of counts — never a 0–100 number.
5. The company dossier shows the Commitment Record under its own heading, beside the GCI. An empty record is visible on a desk seat. A guest sees the panel only when a reviewed commitment exists.

## Coverage (A0 measure, 2026-10-03)

`python -m app.jobs.guidance_coverage` — Nifty 50: 2 of 50 companies have a guidance row with the guidance-side citation in our data (Sensex: 1 of 30). This measures labelling, not how many companies guide.
