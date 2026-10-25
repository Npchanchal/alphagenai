# PRD — Homepage

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/`  
**Owners:** `LandingPage.tsx`, `LandingWorkedExample.tsx`, `LandingProof.tsx`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md) · [PRD_WORKFLOWS.md](PRD_WORKFLOWS.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md)

---

## Prime requirement — a first visit that shows the filing

A Head of Research, a portfolio manager, or a journalist has about a minute. They did not come to learn our vocabulary. They came to see whether management delivered, and to open the document. The homepage has to do that before it asks for a name, an email, or a seat.

Write every sentence the way a results release is written. The reader knows what constant-currency revenue growth is. They do not know a metric id, a feature flag, or the name of a file.

### The first screen

The headline says, in ordinary words, that GCI compares what management guided with what the company later reported, for Indian listed companies, and that every score opens to a filing. CiteAlpha is the product. The legal entity can wait for the footer.

The worked example is Infosys. Apollo Hospitals is the second tab only when that company has a closed trail with both quotes. The number on the page is the live company record. While it loads, one line says so. The panel does not flash a zero, a dash pretending to be a score, or a sample. If the record is not ready, the sentence is plain: this company does not yet have a closed result with both quotes.

Beside the score sits one closed question, the latest one that has both quotes, both links, a reported figure, and an outcome a person can say out loud. For Infosys that question is constant-currency revenue growth: guided 0–3%, reported 3.1%, exceeded, guidance dated 17 April 2025, result dated 23 April 2026. The reader sees the band, the reported figure, the word “exceeded”, both dates, a short quote from each filing, and a link on each quote. The link opens the filing. Under the answer, a text link goes to the Infosys dossier for the rest of the record.

### The filings beside it

“Latest stored filings” means the newest accepted filings, one row per source. A results release is preferred when the same morning also produced a transcript. The reader sees ticker, date, the kind of document, and a title they would recognise in a news list. The action on the row is “Open filing”. Six rows is enough.

A stored title that is only a metric id is rewritten before it is shown. `FY26 revenue_growth_pct` is shown as “FY26 Revenue growth %”. The reader never has to translate the id. The line under the list says these are the newest accepted filings, and that each row is one source.

### After they have seen a number

Four text links name jobs the reader already has: earnings season, whether management delivered, coverage, and a note in the desk’s own format. Each link opens that part of Workflows. They are not a fifth product.

Lower on the page, the outcome words (met, exceeded, missed, dropped, pending) are explained once, with a worked figure, not a formula on its own. Live coverage counts say how many companies are listed and how many have a published score. Then the evaluation form: name, work email, firm. One primary button. If the firm is missing, that field is the one that is marked, and nothing is sent. When the request succeeds, the page says it was received. It does not tell them a seat is open.

The ways forward are named in the order a reader needs them: GCI Screener, Public Snapshot, Filing Search, Analyst Workbench, Disclosure Explorer. Filing Search is described honestly. A visitor can search companies that already have a published score. A cite-only answer stays on a pilot seat.

### Phone, loading, and a thin record

Under 800 pixels the score and the filings stack in one column. The band, the reported figure, and the first filing link are readable without sideways scrolling. Tables that must be wide scroll inside themselves. The page does not shake while the company loads.

Every visitor sees the same worked score and the same filings, whether they are signed out or they run the desk. The form records a request. It does not change who they are.

## 3. Users

| Persona | What they do here |
|---|---|
| Head of Research, PM, sell-side analyst | Read the worked example and the cited question, then open the dossier or Filing Search |
| IR or compliance | Confirm the score is independent of payment and that the page makes no recommendation |
| Quant | Follow the API and methodology links. The page does not embed a factor file |

## 3.1 Role requirements

The scene above is the whole page. Roles do not get a different homepage. This table is only here so nobody later adds a private score for owners or a sample for guests.

The homepage is one page for every role. A guest and an owner see the same worked score, the same cited answer, and the same filings.

| Action | Signed out, guest, viewer, labeler, analyst, reviewer, admin, owner |
|---|---|
| Read the hero, the worked score, the cited answer, the filings, and the workflow links | Allowed |
| Submit the evaluation form | Allowed. The intake stores the request. It does not create an organisation, a seat, or a role |
| Change the published GCI, accept a row, or start a filing search | Not this page. Those actions stay on the dossier, the workbench, and Filing Search, under the roles in those documents |

An organisation `admin` or `owner`, or a platform role, may also see the admin bar. That bar is specified in [`docs/PRD_ADMIN.md`](../PRD_ADMIN.md) and does not change this page’s body.

**HP-R1.** The worked score and the filing list do not vary by role.  
**HP-R2.** Submitting the form leaves `GET /api/entitlements/me` unchanged for that browser.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | The worked example stays on Infosys, with Apollo Hospitals as the second tab when that company has a closed evidence trail. |
| D2 | The cited question uses the latest closed outcome that has both quotes, both URLs, a reported figure, and a label other than pending or pending guidance citation. |
| D3 | “Latest stored filings” is `GET /api/filings/recent`: accepted documents only, one row per source URL, preferring a results release over a transcript. Metric-extract rows are omitted. |
| D4 | A title that is only a metric id is shown with `publicDocTitle` (period and metric name). |
| D5 | The page links to `/workflows` anchors. It does not introduce a fifth product name. |
| D6 | The evaluation form posts to the existing pilot request. It does not create a seat by itself. |

## 5. What this page is not

- A ranked leaderboard. That is the Public Snapshot, and only for established and deep names.
- A search box over the whole market.
- A place for price charts, sentiment, or a Buy / Hold / Sell.
- Synthetic score history, including demo tapes and default anchors.

## 6. Behaviour

1. Hero states that GCI compares guidance with what was later reported, for Indian listed companies, and that every score opens to a filing.
2. The worked example loads the live company GCI. While it loads, the page says so. If the record is missing, the panel says the company does not yet have a closed result with both quotes.
3. The cited-answer panel shows the question, the guided band, the reported figure, the outcome label, both dates, both quotes, and both source links, then a link to `/companies/{id}`.
4. The filings panel lists up to six rows: ticker, date, document kind, public title, and “Open filing”.
5. Four text links go to `/workflows#earnings-season`, `#management-delivery`, `#coverage`, and `#desk-note`.
6. Below that, the page explains the outcome labels, the build steps, live coverage counts, the evaluation form, and the five product surfaces in this order: GCI Screener, Public Snapshot, Filing Search, Analyst Workbench, Disclosure Explorer.
7. Filing Search access copy says a visitor can search companies with a published GCI before an evaluation, and that cite-only chat stays on a pilot seat.
8. On a viewport under 800px the two proof panels stack in one column.

## 7. Stories

**HP-1.** Given Infosys has a closed revenue-growth outcome with both filings, when the homepage loads, then the cited panel states the guided band, the reported figure, and both dates, and each source link opens the filing.

**HP-2.** Given the document store holds several metric extracts dated the same day, when the filings panel loads, then those extracts are absent and each row is a distinct accepted source.

**HP-3.** Given a stored title is `FY26 revenue_growth_pct`, when it is rendered, then the page shows the period and “Revenue growth %”.

**HP-4.** Given the visitor submits the evaluation form with name, work email, and firm, when the request succeeds, then the existing pilot intake records it. The page does not claim a seat was opened.

**HP-5.** Given an analyst and a guest open `/` on the same day, when both pages have loaded, then the worked GCI, the cited figures, and the filing rows match.

## 8. Index integrity

The worked score and the cited answer come from `GET /api/companies/{id}/gci`. The page does not compute a score. A missing dual citation removes the row from the cited panel rather than filling a number.

## 9. Test plan

- Homepage renders `landing-worked-example`, `landing-cited-answer`, and `landing-recent-filings`.
- `GET /api/filings/recent` returns no filing text, no metric-id title, and unique URLs (`tests/test_reading_room.py`).
- Public-copy hygiene passes on the new strings.

## 10. Files

`frontend/src/pages/LandingPage.tsx` · `frontend/src/components/LandingWorkedExample.tsx` · `frontend/src/components/LandingProof.tsx` · `frontend/src/lib/score.ts` (`publicDocTitle`) · `backend/app/data/doc_store.py` (`recent_filings`) · `GET /api/filings/recent`
