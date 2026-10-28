# PRD — Institutional terminal pass

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Decisions confirmed · **Date:** 2026-10-25 · **Restated, unchanged, in** `docs/BRD_ROLES.md`, `docs/PRD_ROLES.md`, and `docs/TRD_ROLES.md`  
**Source note:** *CiteAlpha: Product UI/UX Quick Overhaul*, 25 October 2026  
**Does not replace:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_SCREENER.md](PRD_SCREENER.md) · [PRD_HOMEPAGE.md](PRD_HOMEPAGE.md) · [PRD_WORKBENCH.md](PRD_WORKBENCH.md) · [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md)  
**Owners to extend:** `EvidenceTable.tsx`, `CompanyDetailPage.tsx`, `SourceViewer.tsx`, `SourceViewerContext.tsx`, `HomePage.tsx`, `NavMenu.tsx`, `App.tsx`, `TierBadge.tsx`, `GET /api/companies/{id}/gci`, `GET /api/companies/search`

This pass makes the screener and the dossier denser and faster to move through. It does not add a score, a route, a filing client, or a second evidence table. The five items below are the gaps against the 25 October note, set next to what already ships. Section 8 records the choices confirmed on 25 October 2026. Declined alternatives stay in the text so a later pass does not reopen them by accident.

A published GCI does not move because of this pass. Week, month, quarter, and year change chips stay on the citeable point-in-time rule already in the screener and dossier. The guest still reads the screener without an account, and still stops at 15 dossier opens.

---

## 1. What the analyst is trying to do

A PM has Infosys open and wants the constant-currency revenue row across FY22–FY26 in one glance, then the sentence in the filing that the latest cell came from, without losing the table. A coverage analyst wants the screener to open on names that already have a score, and to put an unscored name back with one control. A signed-in seat wants to type INFY and land on that dossier.

The homepage, the evaluation, the blog, and the plan page stay a public site. The screener, the dossier, Filing Search, the workbench, Disclosure Explorer, Holdings, and Financial Ninja are the working surface.

---

## 2. Already shipped — do not rebuild

| Already in the product | Where | What the October note assumed |
|---|---|---|
| Guidance is one table, not a stack of FY cards. Columns are period, metric in words, guided band, reported actual, outcome, points, promise source and date, result source and date. A row expands to both quotes. | `EvidenceTable.tsx`. Specified in [PRD_DOSSIER.md](PRD_DOSSIER.md) D1, D7 and behaviour 3. | “Annual cards for FY22, FY23, FY24.” That layout is gone. The remaining gap is the year-by-metric pivot. |
| Clicking a result source opens an in-app viewer. The viewer loads stored text, highlights the quote with `span_start` / `span_end`, closes on Escape, and keeps a link to the original filing and to `/c/{citationId}`. | `SourceViewer.tsx`, `HighlightedDocument`, `SourceViewerContext`. Dossier behaviour 4. Same viewer on Filing Search, the revision trail, and Disclosure Explorer. | “Opens an external SEC/NSE/BSE link in a new tab.” True for the **promise** link, which is still `<a target="_blank">`. The result link already stays in the app. The viewer is a centered dialog of about 820px, not a 60/40 pane, and it is extracted text, not a PDF page. |
| Character offsets are the citation geometry we store. | `citations.py`, outcome payload, `SourceTarget`. | Page number and a rectangle `[x, y, w, h]` are not on the outcome. Many India sources are transcripts and HTML, not a single PDF. |
| Confidence tiers `provisional`, `established`, and `deep` render beside a published score. Unscored names sort last. The score cell is empty or a coverage sentence. They are not ranked. | `TierBadge.tsx`, screener row, dossier header. [PRD_SCREENER.md](PRD_SCREENER.md) D3. Public Snapshot ranks `established` and `deep` only. | Three chips: Established (3+ closed periods), Provisional (1–2), Unscored. The live model also has `deep` (at least five closed periods and two metrics). An unscored row has no chip. |
| “Scored only” exists as a checkbox on the screener. It starts **off**. A sentence still says how many names are not scored. The choice is component state, so it clears when the dossier opens and the reader comes back. Copy for an “All companies” pill exists in `en.json` and is unused. | `HomePage.tsx` `scoredOnly`. | Default the list to scored names, with count pills. |
| Digits use `tabular-nums` on `.table`. The face is IBM Plex Sans. Cell padding is 10px × 12px. Numbers are left-aligned. | `styles.css`. Brand type is Source Serif + IBM Plex. | JetBrains Mono or Roboto Mono, 4px vertical padding, 25–30 rows on a 1080p screen, decimals lined up on the right. |
| An account preference `density` is `comfortable` or `compact`. Nothing on the screener or dossier reads it. | `AccountSettingsPage.tsx`, `auth.tsx`. | A compact mode on the research tables. |
| The Desk console tab is a separate dark, compact grid for ops (alerts, extract queue, labeling). It is not the screener and not the dossier. | `DeskConsole.tsx`, `/desk?tab=console`. | A terminal frame for the whole working surface. |
| One header serves the marketing home and every research route: GCI Screener, Research, Workspace, Pricing, Learn (blog, methodology, about, trust). | `App.tsx`, `NavMenu.tsx`. Homepage is `LandingPage.tsx` at `/`. | Marketing routes and a signed-in console with no marketing header. `app.citealpha.com` or `/console/` would duplicate routes that already exist. |
| Company search is `GET /api/companies/search`. The screener already narrows the loaded list. | `searchCompanies` in `api.ts`. Screener behaviour 4. | A command palette. There is no `Cmd+K`, no `/` shortcut, and no saved recent tickers. |
| The SEBI line sits on the screener and the dossier. The dossier’s one-sentence delivery record is the line a PM lifts. Methodology sits below the evidence table. | `Disclaimer`, dossier header. Compliance: the disclaimer stays on GCI surfaces. | Move explanations and the disclaimer out of the primary view into a popover. The disclaimer cannot disappear. The long coverage essay can. |
| Outcomes already return on `GET /api/companies/{id}/gci`, grouped in the client by reading `outcomes[]`. | `repository.get_company_gci`. | A new `/api/v1/companies/{ticker}/guidance-history` payload. A second endpoint would duplicate this response. The pivot is a view over the outcomes already returned. |
| Six public panels on the dossier. Accept, edit, and reject stay on the workbench. | [PRD_DOSSIER.md](PRD_DOSSIER.md) D6, D7. | A new guidance component beside the evidence table. |

---

## 3. Guidance history — metric by year

### What is missing

For Infosys, constant-currency revenue growth is one row. The columns run from the latest closed year back: FY26, FY25, FY24, FY23, FY22. Each cell shows the guided band, the reported figure, and the outcome in words (met, exceeded, missed, dropped, pending). A pending cell stays visible and is not drawn as met. A cell with no row for that year is an em dash.

The last column is the track. It is built only from closed outcomes on that metric. Pending years are left out of the track.

The current cite-row table remains reachable. That table is still how a reader copies both dates, both quotes, and both links, and it is still the table the workbench review actions hang off. The pivot does not become a seventh panel. It is another arrangement of the same evidence panel.

### Grouping

Primary row is the metric in words, via `metricDisplayName()`. Never the metric id. Columns are periods present on that company, newest first. The client derives this from `outcomes` on the company payload. No new history endpoint.

### Confirmed — where the pivot sits

**Q1-A.** A toggle on the evidence panel: “By year” and “By row”. By year opens first. The cite-row table is one control away. The dossier stays within six panels.

Declined: By year as the only public view, with the cite-row table moved to the workbench (B). Pivot only on the workbench (C).

### Confirmed — what the track column shows

**Q2-A.** A short run of outcome words for that metric, oldest to newest among closed years. Example: Met · Met · Exceeded · Missed. Pending years are omitted. No segment bar. No numeric gap between the guided midpoint and the reported actual.

Score Δ (week, month, quarter, year) is not this column. Those chips stay on the citeable series rule.

---

## 4. Citation pane

### What is missing

Clicking a result quote, and clicking a promise quote, keeps the table on the left and opens the source on the right. Escape closes the pane. The quote in the stored text is highlighted from the character span we already keep. The original filing URL and the citation permalink stay in the pane.

Promise links today leave the app. They join the same pane.

### What we cannot pretend to have

There is no stored page rectangle. A highlight box on a PDF page requires either finding the quote inside a PDF we already stored, or a new extract that writes page coordinates. India guidance is often a transcript or an exchange HTML page. The text we store is the source the score already cites.

The browser does not fetch NSE, BSE, EDGAR, or the issuer site. If a PDF is shown, it is a file `doc_store` already holds, served by our API.

### Confirmed — what the right-hand pane renders

**Q3-A.** Dock the current text viewer. The table stays on the left. Stored text, with the quote highlighted from the character span, sits on the right at about 60/40. The pane closes on Escape. “Open original” and “Copy citation link” stay in the pane. No PDF page, and no new extract for a rectangle.

Declined for this pass: a PDF highlight when the stored file is a PDF (B), and a new extract that stores a page rectangle (C).

Controls that apply to A and B: close, Escape, copy the existing `/c/{citationId}` link, open the original URL. Full screen is a wider dock, not a second viewer. Download is the stored file when we have one, not a fresh fetch from the exchange.

The same `openSource()` call is the only entry. Filing Search, the revision trail, and Disclosure Explorer use it too. A dock on those pages follows the dossier, so a reader does not learn two citation gestures.

---

## 5. Density and type

### What is missing

On a 1920×1080 screen the screener table shows at least 25 company rows without scrolling the window. The table itself may scroll. Numbers and percents sit on the right. Metric names sit on the left. Fiscal periods and tickers use tabular figures.

### Confirmed — type and default density

**Q4-A.** Compact is the default on the screener and the dossier. IBM Plex Sans stays the face for numbers, with `tabular-nums` and right alignment. Tickers and fiscal periods use IBM Plex Mono. The account control still offers Comfortable, and this pass applies that preference when it is set. JetBrains Mono and Roboto Mono are not added.

Methodology copy that explains row counts moves out of the table. The one-sentence delivery record on the dossier stays. It is the record, not a banner.

### Confirmed — disclaimer and coverage prose

**Q5-A.** One disclaimer line remains at the foot of the screener and the dossier: factual research, no recommendation. The longer coverage note (“N not yet scored…”) goes away once the filter pills state the same fact. The disclaimer is not collapsed behind an info control.

---

## 6. Command palette and the frame around the app

### Command palette

From a working route, `Cmd+K` on macOS and `Ctrl+K` elsewhere opens a palette. `/` opens it when the focus is not in a text field. The palette searches companies through `GET /api/companies/search` and lists the tools already in the nav (GCI Screener, Filing Search, CiteAlpha Analyst, Public Snapshot, Analyst Workbench, Disclosure Explorer, Holdings, Financial Ninja). Choosing a company opens `/companies/{id}`. Choosing a tool opens that route.

Recent companies are the last few ids this browser opened, kept in `localStorage`. They are suggestions when the palette is empty. They are not a watchlist and they do not change a score.

The palette does not search API keys. Point-in-time keys stay on the developer and account pages.

### Confirmed — how far the palette reaches

**Q6-A.** Companies and existing tools only. Recent companies are remembered in this browser. Saved screens such as “margin misses” are not palette commands. There is no ticker box fixed in the header.

### Confirmed — marketing header and working header

The screener stays open to a guest. A signed-out reader on `/tracker` is not sent to a login wall.

**Q7-A.** Two frames on the same host. Marketing routes (`/`, `/products`, `/blog`, `/about`, `/trust`, `/press`, `/pilot`, `/methodology`, `/changelog`, `/help`) keep today’s header. Working routes (`/tracker`, `/companies`, `/research`, `/analyst`, `/rankings`, `/desk`, `/sights`, `/ninja`, `/holdings`) use a short frame: mark, palette hint, account. Pricing, Blog, and Learn are not in that frame. A text link “CiteAlpha” returns to `/`. Signed-out readers on a working route see the short frame plus Sign in. No `/console` prefix and no `app.` host.

Admin and organisation settings keep the admin bar they already have. This pass does not redraw them.

---

## 7. Screener filter and status chips

### Filter

The control is two pills, with counts taken from the list already loaded: “Scored only (57)” and “All (5,051)”. The figures are the live counts for the index on screen, not a fixed example. The choice is written on the URL (`scored=1` or `scored=0`) so opening Infosys and coming back restores it. Sort and the index stay as they are.

Unscored rows, when shown, still sort after scored rows. They still have no rank and no fabricated score.

### Confirmed — which list opens first

**Q8-A.** Scored only is the default on every index, including NSE All and BSE All. “All” is one pill away. On a broad master the first screen may be a short scored list, with the rest of the names behind that pill. The empty scored state says no scored companies are in this index yet and leaves “All” visible.

### Chips

A published row keeps the tier words the index already uses. An unscored row can carry a chip that says “Not scored” instead of a bare em dash. The chip is not a rank. Sample data stays on the quality badge that already exists. It is not a fourth confidence tier.

### Confirmed — tier words on the chip

**Q9-A.** Keep Provisional, Established, and Deep. Add “Not scored” where the tier cell is empty. No emoji. Colour follows the existing tier colours, and “Not scored” is quiet. Deep stays on the screener and the dossier. `score_policy` and the Public Snapshot rule do not change.

The note’s green, amber, and white emoji marks are not used. The product chrome does not use emoji as status.

---

## 8. Decisions confirmed

Confirmed 25 October 2026. Q8 was chosen as scored-only on every index, including the broad masters.

| # | Confirmed |
|---|---|
| Q1 | Toggle on the evidence panel. “By year” opens first. “By row” keeps the cite-row table. |
| Q2 | Track column is outcome words for closed years on that metric. |
| Q3 | Docked stored text and the existing character highlight. No PDF rectangle in this pass. |
| Q4 | Compact is the default. IBM Plex, tabular numbers, right-aligned. Comfortable remains in account settings. |
| Q5 | One disclaimer line stays. The coverage essay leaves once the pills state the count. |
| Q6 | Palette searches companies and existing tools only. |
| Q7 | Short frame on working routes, same host. The guest screener stays open. |
| Q8 | “Scored only” is the default on every index. “All” is one pill away. |
| Q9 | Keep Provisional, Established, and Deep. Add “Not scored”. No emoji. |

---

## 9. Acceptance

1. Infosys constant-currency revenue growth reads across closed years in one row, newest year first, with guided band, reported figure, and outcome in each cell. A year with no row is an em dash. A pending year is not labeled met.
2. The cite-row table is still available under the option chosen in Q1. Both quotes, both dates, and both URLs still copy from it.
3. A promise click and a result click open the pane chosen in Q3. The table remains visible. Escape closes the pane. The original URL still opens.
4. The screener in the density chosen in Q4 shows at least 25 rows on a 1920×1080 viewport without scrolling the window.
5. Financial figures in the screener and the dossier use tabular figures. Decimal columns line up.
6. Returning from a dossier restores the scored-only pill, because it is on the URL.
7. An unscored name has no GCI and no rank. A citeable change chip is still an em dash when the series is not citeable.
8. The disclaimer line is present on the screener and the dossier under option Q5-A or Q5-C.
9. `Cmd+K` / `Ctrl+K` opens the palette from a working route and reaches a company through the existing search.
10. No new guidance-history route. No second source viewer. No change to a published GCI, tier rule, or score ledger.

---

## 10. Stories

**TM-1.** Given Infosys has constant-currency revenue for more than one closed year, when the year view opens, then those years are columns on one metric row, newest first.

**TM-2.** Given a cell is pending the guidance citation, when the year view renders it, then the cell is not labeled met and the track column ignores it.

**TM-3.** Given a result quote and a promise quote on the same row, when each is activated, then both open the citation pane and the evidence stays on screen.

**TM-4.** Given the reader opens a dossier from the screener and uses the back control, when the screener returns, then the scored-only choice matches the URL they left.

**TM-5.** Given a company has no published GCI, when it is shown, then the score cell is empty and the row is not ranked.

**TM-6.** Given focus is not in a text field, when the reader presses the palette shortcut, then company search uses `GET /api/companies/search`.

---

## 11. Files

Extend only:

- `frontend/src/components/EvidenceTable.tsx` and `frontend/src/pages/CompanyDetailPage.tsx` — year view beside the cite-row table.
- `frontend/src/components/SourceViewer.tsx` and `frontend/src/lib/SourceViewerContext.tsx` — docked pane. Callers of `openSource` stay as they are.
- `frontend/src/pages/HomePage.tsx` — pills, URL, density class.
- `frontend/src/components/TierBadge.tsx` — “Not scored” only if Q9 says so.
- `frontend/src/components/NavMenu.tsx` and `frontend/src/App.tsx` — frame and palette.
- `frontend/src/styles.css` — compact table metrics. IBM Plex only, unless Q4-C is chosen.
- `frontend/src/i18n/locales/en.json` — pill and track copy. The unused `screener.filter.all` string is the one to use.

Do not add `GuidancePivotMatrix`, a `useCitationDrawer` context, `cmdk` as a second palette if a small list will do, `/console` routes, or `/api/v1/companies/{ticker}/guidance-history`.

Tests stay on the owners: dossier evidence, screener filter, source viewer, and the public-copy check. No score-consistency change is expected, and that test still runs.
