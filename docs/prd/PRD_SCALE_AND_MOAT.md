# PRD — Scale, defensibility, and sector calibration pass

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Q1, Q4, and Q5 confirmed 30 October 2026. Q2 and Q3 open · **Date:** 2026-10-30  
**Source notes:** four slides dated 29 October 2026 (*Bronze / Silver / Gold Data Lake Architecture — 80TB Global Filing Infrastructure*; *CiteAlpha GCI — The 5th Trust Layer for Capital Markets*; *5-Layer Defensibility — How We Protect Our Guidance Intelligence*; logo artwork) and *Sector Coefficient Calibration & Phased Rollout Methodology* (METHODGCICALIB001, 11 pages)  
**Does not replace:** [PRD_INDEX_RECORD.md](PRD_INDEX_RECORD.md) · [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_SNAPSHOT.md](PRD_SNAPSHOT.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md) · [PRD_TERMINAL.md](PRD_TERMINAL.md)  
**Owners to extend:** `doc_store.py`, `exchange_filings.py`, `disclosures.py`, `metric_catalog.py`, `guidance_profile.py`, `score_policy.py`, `score_ledger.jsonl`, `publish_index_files.py`, `api/connector_routes.py`, `services/agent/public_api.py`, `EvidenceTable.tsx`, `SourceViewer.tsx`

The slides describe the right destination: a citable delivery record that desks build into their models, sold as data and later as an index. Most of that destination is already in the product at small scale. The Sector Coefficient PDF describes a different product. It replaces “did management deliver what it promised” with a weighted, optimised, partly secret performance model across 64 sector-region cells. That model cannot be published under our own index rules, and it would sit too close to a forecast for a product with no SEBI Research Analyst review.

So we do not need a new idea for the core. The wedge holds. We need fewer claims, a sector-by-sector labeling order, and three or four additions that make the existing record easier to cite and embed. Section 5 lists the new ideas worth having.

No published GCI moves because of this document. Every proposal that would touch a number goes through the ledger and changelog protocol in rule `index-integrity`.

---

## 1. What the materials propose

**Data lake.** Bronze holds 12 million original filings (65–80 TB) from NSE, BSE, SEC, and LSE on S3 in Mumbai with Glacier tiering. Silver runs Google Document AI OCR and BigQuery, filters to 200,000 guidance documents, and stores Parquet on GCS with AlloyDB. It powers Filing Search and a model pre-label. Gold holds 25,000 hand-labeled evidence points in Cloud SQL behind `GET /gci/{ticker}`. The slide says $600K of cloud credits pays for it, and that Gold is served only by API.

**Trust layer.** Four consumer products sit on one engine. Market Intelligence is a plugin showing what management promised against what it did. Trust Scoring is a credibility stamp for earnings risk. Indices are a GCI Leaders Index and a royalty on a credibility factor. Benchmarking compares guidance against peers. The sources are NSE, BSE, SEBI filings, and earnings calls.

**Five-layer defensibility.**
1. The data lake, kept as a trade secret in Glacier.
2. An evidence chain on every score: source PDF, page number, revision history, and validator id.
3. An Excel function `=CITEALPHA_GCI(ticker)` and free Filing Search for universities.
4. A v2 scorer that adds miss magnitude, revision pattern, a sector adjustment, and management tenure, with the weights kept proprietary.
5. Index licensing with royalties on fund AUM.

**Sector calibration (PDF).** A “Guidance Confidence Index” is computed as \(GCI = \Omega(C_t)\,\mathbf{1}^T\big((N_t P) \odot W_{sector,geo}\big) - \lambda_{sac}\max(0, -\partial P_{margin}/\partial t)\). It adds velocity, acceleration, an “earnings airpocket” flag, an Itô drift model, and a durability integral. Weights are fitted on an anchor company, validated on peers, and locked at a t-statistic above 3.0 with at least 82% accuracy in predicting misses one to two quarters ahead. The rollout runs over eight sectors and eight regions to 3,000 global stocks, dated Q1–Q3 2025. The UI adds a sector-region pill with percentiles, accounting-adjustment badges, and a four-part decomposition drawer.

---

## 2. Already shipped — do not rebuild

| In the materials | Already in the product | Gap that remains |
|---|---|---|
| Bronze: immutable original filings with metadata | `doc_store.py` keeps each filing once by `url_key` and `content_hash`, with `ingested_at`. India and SEC ingest return `already_stored` and skip the network. | Bodies sit on the task volume as `doc_text/<hash>.txt`. No S3 tier yet (section 4.6). |
| Silver: parsed, filtered, model pre-label, powers Filing Search | `disclosures.py` reads filings in 48,000-character pieces and caches each piece once. Filing Search is `/research`. | None for the concept. OCR is not used: India results and presentations are mostly text PDFs. |
| Gold: dual-cited rows behind an API | Hand-labeled outcomes with both quotes, `reviewed_by` and `reviewed_at`, the score ledger, `GET /api/v1/index/levels`, `/ledger`, and `/evidence`, plus daily CSV, Parquet, and SHA-256 index files (W9.2). | Depth. See section 3. |
| Original guidance, revisions as heatmap and candlestick, then actuals | `ThreadTimeline.tsx` (heatmap, `revisionCandle`) and `RevisionTimeline.tsx`. `revisions[]` on each outcome. | None. |
| Every point dated, matched, sourced, validated | Dual citation gate (W2.1), source verification job (W2.7), and the reviewer stamp on the dossier (W2.5). | None. |
| SHA-256 source hash and exact quote anchor. Refuse a score when the source cannot be verified. | `evidence_hashes` on every `OutcomeView`, `span_start` / `span_end`, `GET /api/v1/index/evidence?checksum=`. A row without both quotes is excluded rather than estimated. | None. |
| Validator id | `reviewed_by` on the row, `label_accept` in `audit.json`. | None. |
| Analysts cite a CiteAlpha link in reports | `/c/{citationId}` permalinks. Analyst Excel exports put a comment and a link on each sourced cell. | No live spreadsheet function (section 4.4). |
| Miss magnitude in the score | v3 and v4 score distance from the band: \(\exp(-\alpha\delta^\beta)\), with \(\gamma = 1.4\) on misses. | None. |
| Revision pattern | `guidance_profile` labels walk-down, walk-up, mixed, and stable. It is descriptive and deliberately outside the GCI. | None. |
| Margin sacrifice (revenue met by giving up margin) | Profile “divergences”: same-period revenue and margin on opposite sides of their ranges, both cited. | None. |
| Accounting normalisation, e.g. Ind AS 116 | Each outcome stores reporting basis, unit, and scope on both the guidance and the actual. When they differ, the row stays out of the score (changelog 2026-10-24). | No badge on the row (section 4.3). |
| FX scaling | Constant-currency and reported growth are separate metric ids and are never matched to each other (WS2.1). | None. |
| Version-controlled weights, backward-compatible history | `algorithm_id`, `ALGORITHM_REVISION`, an append-only ledger, and `/api/v1/index/levels?as_of=`. | None. |
| Trajectory of the score over time | Change chips for week, month, quarter, and year on citeable point-in-time series (at least four reviewed points). | None. |
| Benchmarking against peers | Analyst Peer Delivery Grid. Public Snapshot sector cuts of the published set. | A peer position on the dossier (section 5.3). |
| Methodology governance with an IOSCO posture | `docs/index/GCI_METHODOLOGY_v1.md`, `CORRECTIONS_POLICY.md`, `DATA_RIGHTS.md`. | External readers (W9.1), licence pack (W9.4), verification (W9.5). |

---

## 3. The claims measured against what is on file

| Claim | What is on file today | Consequence |
|---|---|---|
| 12 million filings, 65–80 TB | The walk reads Nifty 500 and S&P 500 filings dated from 1 January 2024, about six documents per company per fiscal year in India. Other markets are listing only. LSE has no walk. | Tens of thousands of documents, not millions. Quote the production count from `GET /api/ops/coverage-progress`. |
| 25,000 hand-labeled evidence points | About 106 hand-labeled outcome rows in `hand_labeled.py`. Six names published in production (Infosys 76.5, Cipla 65.5, Axis Bank 90.7, Adani Ports 58.7, Apollo Hospitals 60.4, HDFC Life 87.8). Locally, 2 of 5,557 listings carry a score. | Present 25,000 as a destination with a date. The public target is Sensex 30 and Nifty 50 at established depth by 31 March 2027, roughly 500 to 1,000 reviewed rows. |
| 5,000 companies × 20 years | Walk start date is January 2024 (changelog 2026-10-19). Most names will have two closed years plus quarters. | Do not say 20 years. |
| $600K cloud credits | No grant on file. Google advertises up to $350K over two years, subject to approval. `FACTS.md` says not to budget credits as if wired. | Remove the number. |
| GCP stack (Document AI, BigQuery, AlloyDB, Cloud Run) | Production is one ECS Fargate task (ARM, 0.5 vCPU, 1 GB) in `ap-south-1`, with JSON stores and an S3 bucket for index files. `FACTS.md`: do not tell Google or Accel the estate runs on Google Cloud. | A second cloud adds cross-provider egress, two IAM models, and a migration with no customer asking for it. |
| Bulk download of every filing | `exchange_filings` caps India fetches at 40,000 a day. At that cap, 12 million documents takes about 300 days of fetching. `DATA_RIGHTS.md`: we store a dated quote and a URL, and do not redistribute original PDFs on public pages. | Fetch what the GCI reads. Rule `source-once` already says this. |
| Raw filings as a trade secret | The filings are public. Anyone can download them. | The defensible asset is the reviewed pairs, the revision threads, and the dated ledger. Say that. |
| Page number on every citation | `extract_pdf_text` joins pages with a newline and discards page boundaries. Citations carry character offsets. | New, forward-only (section 4.5). |
| “Gold only served via API” | The screener, dossier, and Public Snapshot are public by design. Guests read published scores. | Declined. The public number is the marketing and the citation target. |
| “Earnings calls” as a source | Filed call transcripts only. Audio and video are not transcribed. | Say “filed call transcripts”. |
| “SEBI filings” as a source | Results, presentations, and transcripts are filed with NSE and BSE. SEBI holds offer documents. | Say “NSE and BSE filings”. |
| “Guidance Confidence Index” (PDF) | The index is the Guidance Credibility Index. | Rename throughout. |
| Rollout Q1–Q3 2025 (PDF) | Today is 30 October 2026. | The dates are stale. |

---

## 4. What fits — adopt, on the existing owners

### 4.1 Anchor, then peers, then the next sector (labeling order)

The PDF’s three-tier lifecycle is the right order for **labeling**, not for fitting weights. Infosys is already `deep`. Its Indian IT peers come next, then banks, then capital goods, then pharma and consumer. This matches WS3.3 in `docs/PLAN_WHITESPACE.md`, so WS3.3 becomes the first rung of the ladder rather than a separate list.

| Rung | Anchor | Peers to review | Exit |
|---|---|---|---|
| 1 India IT | Infosys (deep) | HCLTech, Wipro, Tech Mahindra, LTIMindtree, TCS | Every peer is `established`, or carries the coverage sentence `no_quantified_guidance` |
| 2 India banks | Axis Bank (provisional) | ICICI Bank, HDFC Bank, Kotak, SBI, IndusInd | Same |
| 3 Capital goods and infrastructure | Adani Ports (provisional) | L&T, Siemens, ABB, CG Power | Same |
| 4 Pharma and hospitals | Cipla, Apollo Hospitals | Sun Pharma, Dr Reddy’s, Lupin | Same |
| 5 Consumer and autos | — | HUL, ITC, Britannia, Maruti, Trent | Same |

A peer that does not publish numeric guidance is a finding, not a gap. The coverage job decides that, not this table. A name that never guides gets the sentence and no number, and the rung still closes.

US and other markets wait until the India rungs for Sensex and Nifty 50 are closed. The US walk keeps running provisional and unranked as it does today.

### 4.2 Sector metric map (what to read and label, not what to weight)

The PDF’s sector vectors are useful as a checklist of what each sector actually guides on. Add a `sectors` tag to entries in `metric_catalog.py`. The walk and the labeling playbook use it to know which statements to look for in a bank filing versus an IT filing. The scorer does not read the tag.

| Sector | Guided metrics we already score or should add to the catalogue | From the PDF, not guidance, so not GCI |
|---|---|---|
| IT services | Constant-currency revenue growth, operating margin | Utilisation, attrition, deal TCV. These are reported, rarely guided. They can be monitored commitments. |
| Banks | Loan growth, NIM, credit cost, cost-to-income | GNPA, PCR, CET1 levels. Guided only sometimes. When guided, they score, with `direction: lower` for GNPA and credit cost. |
| Pharma | Revenue growth, EBITDA margin, R&D spend as % of revenue (`two_sided`) | USFDA Form 483 counts and ANDA approvals. These are regulatory events, not promises. They belong in event filings. |
| FMCG | Volume growth, EBITDA margin | Rural and urban demand ratio, realisation drift. These are commentary, not quantified guidance. |

### 4.3 “How this number is built” inside the evidence row

The PDF’s four-tier drawer keeps three of its four tiers once the regional multiplier is dropped. When a row expands in `EvidenceTable.tsx`, it shows:

1. Row points and the label, with the band after the width floor.
2. Its recency weight and its metric weight in the composite, or “context only, not in the composite” (from `score_meta().composite_weights`).
3. Any analyst-set audit deduction, with who set it and the source.
4. Both evidence hashes and the filing’s `ingested_at`.
5. A basis badge when the guidance and actual record a reporting basis (for example “Ind AS, consolidated” or “constant currency”).

This is a view over data the API already returns. It is not a seventh dossier panel and not a new endpoint.

### 4.4 Spreadsheet function (planned leftover A6) — built 30 October 2026

Excel custom functions in a shared-runtime add-in served from `/office/` (`frontend/public/office/`). Every value comes from `GET /api/v1/sheet` on the existing owners, `api/connector_routes.py` and `services/agent/public_api.py`.

- `=CITEALPHA.GCI("INFY")` returns the level on the dossier (76.5 today). A company with no published GCI shows `#N/A`, and the error message carries the coverage sentence. A custom function cannot write a cell comment, so the reason travels on the error instead.
- `=CITEALPHA.TIER("INFY")` returns Provisional, Established, or Deep. `=CITEALPHA.ASOF("INFY")` returns the data-as-of date.
- An optional second argument is a date: `=CITEALPHA.GCI("INFY", "2026-10-01")` reads the ledger for the level published on or before that day. With a date, `ASOF` returns the day that level was published. A date cell works as well as a typed date.
- `=CITEALPHA.RECORD("INFY")` returns the one-sentence delivery record, or the coverage sentence. `=CITEALPHA.LINK("INFY")` returns the dossier address.
- The add-in uses an org API key with `read_api`, saved in its pane, and shares the public API's per-key rate limit. Calls are batched up to 50 tickers and cached for ten minutes. A request without a key gets 401.

The function returns only published levels. It never computes a number in the client and always returns the tier beside the level, so a provisional name is never read as ranked. The manifest is offered from CiteAlpha Analyst settings, beside API keys. It is not yet listed in Microsoft AppSource.

### 4.5 Page number on citations, for newly stored PDFs

When `exchange_filings.extract_pdf_text` reads a PDF, it records the character offset where each page starts, stored with the document in `doc_store`. The source viewer then says “page 14” beside the highlighted quote. No rectangle, consistent with PRD_TERMINAL Q3.

Documents already stored keep character offsets only. Their PDF bytes are not stored, and rule `source-once` forbids refetching them for this. The page appears as filings are next ingested.

### 4.6 Storage, when the store outgrows the task volume

Keep AWS `ap-south-1`. Map the slide’s vocabulary onto the owners rather than building a second stack:

| Layer | Owner | Move when |
|---|---|---|
| Bronze (documents) | `doc_store.py` | Move bodies to S3 behind the same `find_by_url` / `find_by_hash` / `upsert_document` calls once the text store passes 20 GB or the document index slows startup. Lifecycle to Glacier Instant Retrieval after 180 days. |
| Silver (extracts) | `disclosures/{id}.json`, `llm_extract_ledger.json` | Stays as-is until Postgres lands for analyst stores (kb 19 planned leftover). Then same database, not a second one. |
| Gold (published) | `hand_labeled*.py`, `score_ledger.jsonl`, index files | Ledger stays append-only. Index files already upload to S3 when `INTELLENS_INDEX_S3_BUCKET` is set. Apply that bucket. |

Google credits, if granted, pay for the pinned Gemini extraction evaluation already described in `docs/fundraising/google-for-startups/`. They do not move the estate.

---

## 5. New ideas worth adding (not in the materials)

These serve the same goals as the slides (depth, citation, embedding, licensing) and fit the index rules.

### 5.1 Back-calculated levels for licensees

An index licence needs history. Our ledger starts in September 2026. Every reviewed row already has a result filing date, so the level a company would have carried on any past date can be rebuilt from rows whose actual was filed on or before that date. Gate 7 already proves that a promise predates its result.

- File: `gci_backcalc_<as_of>.parquet`, built by `publish_index_files.py`, labelled `series_kind = "back_calculated"` in every row.
- Licensee download only. Never on the screener, the dossier, the snapshot, or a change chip. Rule `index-integrity` still forbids it on public surfaces.
- The methodology page says back-calculated history exists for licensees and how it is built.

Without this, no fund can backtest a GCI index before 2029.

### 5.2 Who made the promise

The slide’s “management tenure” belongs in the record, not in the weight. When a guidance quote comes from a filed transcript, store the speaker’s name and role (CEO or CFO) from the transcript line. The profile can then say “Under the current CFO since FY24: met 3 of 4” and split the record when management changes. This is descriptive and never feeds the GCI (`test_profile_does_not_move_gci`).

### 5.3 Peer position, gated on depth

Instead of “88th percentile global IT services”, the dossier header shows a plain position among published peers: “2nd of 6 established Indian IT names.” It appears only when the sector has at least five `established` or `deep` names, and only for a company that is itself `established` or above. Below that it does not render. No cross-region percentile.

### 5.4 Measure the replication cost instead of asserting it

The slide claims 6,250 hours to replicate (25,000 points at 15 minutes). We already log submit and accept times in `audit.json`. Report the median review minutes per accepted row and the count of reviewed dual-cited rows on Trust. The moat number then grows with the data and can be checked.

### 5.5 Academic seat (optional)

The slide’s free Filing Search for universities becomes a plan, not an open door. An `academic` org plan with `tracker`, `research`, and `read_api`, a verified `.ac.in` or `.edu` domain, and a citation request (“GCI by CiteAlpha, data as of …”). It reuses entitlements and the existing guest caps logic. Platform billing approves it.

---

## 6. Declined — with the reason

| Proposal | Why not |
|---|---|
| Sector × region weight matrices \(W_{sector,geo}\), the Hadamard core score, and fitted weights | GCI scores delivery against a stated band. The PDF’s core sums weighted performance levels (NIM, GNPA, attrition, Form 483 counts). That is a fundamentals score, which is the dashboard the wedge says we are not. Sector shrinkage was removed on 2026-09-28 (decision D5). |
| Fitting weights to predict misses one to two quarters ahead, with ≥82% accuracy and t > 3.0 per cell | It turns the index into a forecast, which needs SEBI Research Analyst review. kb 03 already rejected a market-calibrated loss on 2026-10-18 because it “turns GCI into a price model”. The data cannot support it either: five peers × two or three closed years × four metrics is about 40–60 rows per cell, fitting four weights plus regional terms. That is 64 cells. The 82% figure has no data behind it. |
| Proprietary weighting logic | A citable index publishes its rule. Our own layer 2 (the citation standard) and the IOSCO posture in `GCI_METHODOLOGY_v1.md` require a reader to rebuild the number from the evidence. The moat is reviewed history, not secret constants. |
| Guidance velocity, acceleration, “earnings airpocket” flag, Itô drift, durability integral | Most scores move once a year on a closed period. Derivatives of a step series with four points are noise. An “airpocket warning” is a forward-looking signal for the same reason as above. Recency weighting already covers durability. Gate 6 stands: an advanced construct ships only if it beats the plain measure out of sample. |
| Margin-sacrifice penalty and consistency multiplier inside the score | Both exist as descriptive profile items (divergences, revisions). Moving them into the GCI changes what the number means without new evidence. |
| Management tenure as a score factor | Kept as description (5.2). |
| 3,000 global stocks across eight regions | India first, export by API later (rule `citealpha-core`). The US walk stays provisional and unranked. |
| 12 million filing Bronze lake, OCR, BigQuery, AlloyDB, Cloud SQL | We would fetch filings the GCI never reads, against exchange caps and our own data-rights note. A second cloud adds cost and a migration with no customer pull. Section 4.6 is the scaling path. |
| Gold served only by API | The public dossier and snapshot are how the number gets cited. |
| ETF royalty and a GCI Leaders Index now | Needs `established` depth on a basket (Sensex and Nifty 50, 31 March 2027 target), back-calculated history (5.1), the licence pack (W9.4), external verification (W9.5), and counsel’s view on SEBI (Index Providers) Regulations 2024 registration and its net-worth condition. Section 8 lists the gates. |
| “Trojan horse distribution”, “credibility stamp for earnings risk” | Internal phrases. The second implies a prediction. |

---

## 7. What decks and the site may say

`docs/fundraising/FACTS.md` remains the source of truth. These slides should be corrected before they go to anyone.

| Do not say | Say |
|---|---|
| 12 million filings, 80 TB data lake | “We store each filing the index reads, once, with its hash and the date we read it.” Then the production count. |
| 25,000 hand-labeled evidence points | The live count of reviewed dual-cited rows, and the target: Sensex 30 and Nifty 50 at established depth by 31 March 2027. |
| 5,000 companies × 20 years | “Nifty 500 and S&P 500 filings from January 2024; Sensex is the scored universe.” |
| $600K cloud credits, built on GCP | “Hosted on AWS in Mumbai.” Credits only once granted, and only for the extraction evaluation. |
| Trade secret in Glacier | “The defensible asset is the reviewed record: promise, revisions, result, reviewer, and date, in an append-only ledger.” |
| We keep the weighting proprietary | “The method is published. Every number can be rebuilt from its two filings.” |
| ETF-ready, royalty on AUM | “Daily index files with checksums and a point-in-time ledger. Index licensing follows external verification.” |
| Guidance Confidence Index | Guidance Credibility Index (GCI) |
| SEBI filings, earnings calls | NSE and BSE filings, filed call transcripts |
| India’s first | “India-localised guidance accountability.” Marvin Labs and FinCatch exist in the US. |

The logo images in the attachments are artwork only. Brand assets in the repository do not change (rule `brand-assets`).

---

## 8. Gates before the index and licensing story is true

| Gate | Owner | Evidence |
|---|---|---|
| 8 Sensex names at `established` | WS3.3 | `guidance_coverage --index SENSEX` printed into `PLAN_WHITESPACE.md` §8 |
| Rung 1 (India IT) closed | Section 4.1 | Every peer `established` or `no_quantified_guidance` |
| Sensex 30 and Nifty 50 at `established` | Labeling bench | Public target 31 March 2027 |
| Methodology read by one quant and one compliance reader | W9.1 | Sign-off on file |
| Licence pack: display, redistribution, derived use, attribution | W9.4 | Counsel-reviewed |
| Independent re-check of a 30-row sample | W9.5 | Pass rate on Trust |
| Back-calculated levels file | Section 5.1 | Built, labelled, licensee-only, test proves it never reaches a public route |
| Event study and out-of-sample lift | kb 03 gates 5 and 6 | Only after enough `established` names |
| Counsel memo on index-provider registration | Compliance | Written memo before any fund conversation |

---

## 9. Decisions

Q1, Q4, and Q5 were confirmed on 30 October 2026. Declined alternatives stay in the table so a later pass does not reopen them by accident.

| # | Question | Decision | Declined or still open |
|---|---|---|---|
| Q1 | Sector calibration model from the PDF | **Confirmed.** Decline the fitted weights and the prediction target. Adopt the rollout ladder (4.1) and the sector metric map (4.2). | Declined: a pilot-only experimental construct behind gate 6. Declined: adopting the model as the scorer. |
| Q2 | Data platform | **Open.** Recommended: stay on AWS and move `doc_store` bodies to S3 on the trigger in 4.6. | Alternative: plan a GCP migration if a credits grant arrives. |
| Q3 | Index licensing timing | **Open.** Recommended: build back-calculated levels (5.1) now, and hold any fund or ETF talk until section 8 is green. | Alternative: start fund conversations now on the published set. |
| Q4 | First new build | **Confirmed.** Spreadsheet function (4.4). | Later, in any order: score decomposition (4.3), back-calculated levels (5.1), page numbers (4.5), who made the promise (5.2). |
| Q5 | Deck corrections | **Confirmed.** Correct the three slides to section 7 before external use. Section 7 lines are in `docs/fundraising/FACTS.md`. | Declined: internal only. Declined: leave as is. |

---

## 10. Acceptance

1. No published GCI, tier rule, or ledger row changes because of this document.
2. `metric_catalog.py` carries a `sectors` tag. `gci_scoring.py` does not read it (test).
3. The evidence row shows recency weight, metric weight or “context only”, audit deduction with source, both hashes, and a basis badge when present. Still six dossier panels.
4. `=CITEALPHA.GCI("INFY")` returns the same number as the dossier and `levels`. An unscored name returns `#N/A` with the coverage sentence. A request without an org key is refused. Done: `tests/test_sheet_function.py`.
5. A newly stored PDF citation shows a page number. An older document shows none and was not refetched.
6. Back-calculated levels exist only in a licensee file labelled `back_calculated`. `tests/test_index_integrity.py` fails if the label reaches a public route.
7. Peer position renders only with at least five `established` or `deep` peers in the sector.

## 11. Stories

**SM-1.** Given HCLTech has three closed years on constant-currency revenue and operating margin, both dual-cited and reviewed, when the tier is computed, then it is `established` and rung 1 counts it.

**SM-2.** Given a peer has no numeric guidance in its filings since January 2024, when coverage runs, then the dossier shows the sentence and no number, and rung 1 still closes.

**SM-3.** Given an analyst types `=CITEALPHA.GCI("INFY")` with an org key, when the sheet recalculates, then the cell shows 76.5, and `=CITEALPHA.LINK("INFY")` returns the Infosys dossier address.

**SM-4.** Given a licensee downloads back-calculated levels, when they read a row dated 2025-06-30, then the level uses only rows whose result filing is dated on or before 2025-06-30.

**SM-5.** Given a company is `provisional`, when its dossier renders, then no peer position appears.

## 12. Files

Extend only:

- `backend/app/data/metric_catalog.py`: `sectors` tag.
- `frontend/src/components/EvidenceTable.tsx`: decomposition in the expanded row.
- `api/connector_routes.py`, `services/agent/public_api.py`, `frontend/public/office/`: spreadsheet function. Built.
- `backend/app/services/exchange_filings.py`, `backend/app/data/doc_store.py`: page offsets on new PDFs; S3 body storage behind the same calls.
- `frontend/src/components/SourceViewer.tsx`: page label.
- `backend/app/jobs/publish_index_files.py`: back-calculated file.
- `backend/app/services/guidance_profile.py`: speaker attribution (description only).
- `docs/PLAN_WHITESPACE.md`: WS3.3 points at rung 1.
- `docs/fundraising/FACTS.md`: section 7 lines, once Q5 is confirmed.

Do not add `sector_weights.py`, a `W_sector` table, a velocity or acceleration service, a GCP client, a second document store, or a `/gci/{ticker}` route beside `/api/companies/{id}/gci` and `/api/v1/index/levels`.
