# PRD — Seats and the first screen each seat sees

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited
**Status:** final for the next development cycle · **Date:** 28 Oct 2026
**Business reason:** [BRD_ROLES.md](BRD_ROLES.md) · **Build:** [TRD_ROLES.md](TRD_ROLES.md)
**Carries:** the terminal behaviour confirmed on 25 Oct 2026 and the role-screen behaviour from the 28 Oct 2026 walk. Section 4 is the public-page behaviour. Section 7 is the working-surface behaviour (year view, docked source, density, palette, frame, scored-only).
**Owners to extend:** `entitlements.py`, `session_auth.py`, `OrgAdminPanel.tsx`, `HoldingsPage.tsx`, `DevelopersPage.tsx`, `CompanyDetailPage.tsx`, `EvidenceTable.tsx`, `SourceViewer.tsx`, `SourceViewerContext.tsx`, `DeskPage.tsx`, `AnalystPage.tsx`, `HomePage.tsx`, `RankingsPage.tsx`, `ResearchPage.tsx`, `NavMenu.tsx`, `App.tsx`, `TierBadge.tsx`, `LandingPage.tsx`, `styles.css`

A published GCI does not move because a seat was added. Accept still goes through the existing review route, and only a reviewer, an admin, or the owner may take the accept action after this PRD. Guest caps stay 15 dossier opens and 8 filing searches.

---

## 1. The person appointing the seat

An organisation owner opens Organisation settings → Invites. They type a work email and choose a role in words, not an id. The list is:

Viewer · Portfolio · Data · Investor relations · Oversight · Analyst · Labeler · Reviewer · Admin

Admin appears only for the owner. The owner cannot appoint another owner from this list. An organisation admin sees the same list without Admin.

Each option has one sentence under it, shown when it is selected:

| Label | Sentence |
|---|---|
| Viewer | Reads the screener, the dossiers, and Filing Search. |
| Portfolio | Reads the book and the screener. Cannot accept a figure onto the score. |
| Data | Reads the API and, on an Enterprise plan, downloads the file. Cannot accept a figure onto the score. |
| Investor relations | Reads and exports a pack for the companies you name. Cannot accept a figure onto the score. |
| Oversight | Reads this organisation’s audit trail. Cannot accept a figure, invite a seat, or open billing. |
| Analyst | Runs notes and prepares rows. A reviewer accepts a row before it can enter the score. |
| Labeler | Marks outcomes in the labeling queue. Cannot accept a row. |
| Reviewer | Accepts or sends back a row, and can do the analyst’s work. |
| Admin | Invites seats and runs the desk. Cannot appoint another admin. |

After the invite is accepted, the new person lands on the first screen in section 3. They can open the other rooms their seat allows. The landing is a default, not a lock.

Investor relations has a second step on the member row, only for the owner and the admin: “Companies this seat may pack”, a search of companies that already exist, saved as an allow-list. Empty is allowed. The member row then says “No company named yet”, and the IR person sees that sentence instead of a pack button.

## 2. Permission matrix

Features are still intersected with the plan. A blank cell is denied with 403 and no write.

| Feature | viewer | pm | data | ir | oversight | analyst | labeler | reviewer | admin, owner |
|---|---|---|---|---|---|---|---|---|---|
| Screener, dossier read | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| Filing Search | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| Cite-only chat, Analyst skills | | | | | | yes | | yes | yes |
| Holdings | | yes | | | | yes | | yes | yes |
| Financial Ninja | | | | | | yes | | yes | yes |
| Workbench read | | | | | | yes | yes | yes | yes |
| Workbench propose (extract into the queue) | | | | | | yes | | yes | yes |
| Accept a row onto the scored record | | | | | | | | yes | yes |
| Labeling queue | | | | | | | yes | yes | yes |
| Board pack for an allow-listed company | | | | yes | | yes | | yes | yes |
| Bulk data file (`em_export`, plan permitting) | | | yes | | | | | | yes |
| Read API | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| This org’s audit trail | | | | | yes | | | yes | yes |
| Invite seats, billing, house style, Analyst keys | | | | | | | | | yes |

`member` is stored as `viewer` and is not a label in the menu. Platform operator roles are unchanged and are not in this table.

An analyst who could accept yesterday is told, on the review row, that acceptance sits with a reviewer. The button is absent. A direct `POST /api/review` with `action=accept` returns 403.

## 3. First screen, step by step

### 3.1 Portfolio

1. They sign in and land on `/holdings`.
2. If the plan does not include holdings, the page says the book opens on a Desk plan or above, and offers the screener. The paste box is not shown.
3. If no file has been saved, two sentences say what to paste (identifier, weight, and whether the line is cash, debt, or a fund). The button is Look through.
4. If a file exists, the page leads with covered weight, the weighted GCI of that weight, and the gap list (no published score, cash, debt, indirect, unknown). The paste box is below.
5. Under the gaps, “Since you last opened this” lists a new filing, an open guidance item, or a missed row for a held name, from records already stored. Empty is the sentence “Nothing new on the names this book can score.”
6. A row with no published score stays in the gap list. It is not given a number.
7. They can open the screener from the page. Starring a name on the screener adds it to this book. It does not accept a score.

### 3.2 Data

1. They sign in and land on `/developers`.
2. The first block is a field table for one published outcome: company, period, metric name, guided low, guided high, reported actual, outcome, promise date, result date, available date, tier, algorithm id. Null is described as null, with the coverage reason.
3. A sample download is the current published export, with its sha256. The page says a monitor and an upload do not write the index.
4. On a plan without `em_export`, the table and the path list still show, and the download says the file is on the Enterprise plan. The button is absent.
5. They do not see Invite, Billing, or Accept.

### 3.3 Investor relations

1. They sign in. If the allow-list has one company, they land on that dossier. If it has several, they land on a short list of those companies. If it is empty, they land on the screener with one line: “Your desk admin has not named a company for packs yet.”
2. On an allow-listed dossier the header is the public header. One text link says “Board pack”.
3. The pack is the existing board scorecard export: the delivery sentence, open items, closed outcomes, disclaimer, as-of date, evidence receipt. No peer rank and no recommendation.
4. Choosing Board pack on a company outside the list does nothing in the interface, and the API returns 403.
5. They do not see Accept, the labeling queue, or another organisation’s notes.

### 3.4 Oversight

1. They sign in and land on `/org/settings?section=audit`.
2. The page is this organisation’s audit events, newest first: who accepted or rejected a row, who exported a pack, who changed a seat. They cannot open Invites, Billing, or Destinations. Those items are omitted, not shown disabled.
3. A row that names a score shows the company, the old and new action, the person, and the time. It does not offer Accept.
4. They can open the public screener and Filing Search. Cite-only chat is the viewer’s explanation, not a box that fails.

### 3.5 Seats that already exist — home view only

| Seat | Lands on | What changes on the screen |
|---|---|---|
| Analyst | `/analyst` | First group is “This print”: Results Prep and Call Questions. Second is “Learn a name”. Third is “Board, credit, and events”. Run stays the one primary button. Accept is not on this page. |
| Reviewer | `/desk?tab=review` | The pinned company’s queue. Accept, edit, and reject stay. Console is one tab away. |
| Labeler | `/desk?tab=labeling` | The labeling queue. Accept is absent, with the existing line that acceptance sits with a reviewer. |
| Viewer, guest | `/tracker` | Unchanged entitlement. The screener fixes in section 4 apply to them too. |
| Owner, admin | `/tracker` | The coverage sentence is the kicker. The admin bar is the one they already have. |

A head of research who should appoint seats is an owner or an admin. They are not a new landing.

## 4. Public pages these seats share

These are the same pages for every seat. A journalist and a PM read them without a special role. The live evidence is the 28 Oct walk. The working-surface speed pass is section 7. Where the two touch the same control, this section and section 7 are one behaviour, as reconciled in the BRD.

### 4.1 One meaning of “published”

The homepage, the screener, the snapshot, and the reading room use one count: how many companies have a published GCI, and how many of those are established or deep. A provisional row is a record the reader can open. It is not a rank they can quote.

On 28 Oct those four surfaces disagreed: the homepage said 57 scored and 2 of 30 on the Sensex; the snapshot said n=0 citeable and then listed six provisional names; Filing Search’s control listed Infosys and Cipla; the Sensex screener showed two numeric scores and then pipeline sentences.

The snapshot heading and the table are the same claim. While no name is established or deep, the heading says this is a delivery record, and every provisional row is labeled provisional. The page title matches that mode. It does not say “Quarterly” over an unranked table. When at least 20 names are established or deep, the heading may say rank, and provisional names stay out of that rank.

The cite control copies one sentence: company, GCI, tier, as-of, the delivery sentence, and the dossier URL. Copying a provisional row includes the word provisional. No login.

Filing Search’s company list is the published-GCI list, or the page says which narrower set it is and why.

### 4.2 Screener, first paint

A guest opens on an India index. The document title names that index. Markets other than India are not on the public control. A signed-in preference may remember an India index. It does not reopen a market the page has said is unscored.

The kicker is the coverage sentence for the index on screen, the same sentence the homepage already prints. “Scored only (n)” and “All (n)” are pills with live counts, on the URL, defaulting to scored only, including NSE All and BSE All. The longer essay under the table goes away once the pills state the count. One disclaimer line stays at the foot: factual research, no recommendation.

The tier chip on an unscored row says “Not scored”. It is quiet, it is not a rank, and it is not a fourth tier. The score cell carries one coverage sentence: what is missing, the promise, the later result, or both. It does not say “Demo”, “Hand-labeled” on a row with no score, or a pipeline stage such as “result not yet matched” or “filings not yet read”. Sample data is called sample data, on the quality badge, and only when that row is sample data.

Sort stays as it is. A closed-results-then-GCI sort, so that Axis Bank at 90.7 with one closed result does not sit above Infosys at 76.5 with five, is recorded as an owner decision and is not part of this build. Unscored rows still sort after scored rows. They have no rank and no fabricated score. A citeable change chip is still an em dash when the series is not citeable.

### 4.3 Dossier a guest can finish

The header stays: company, ticker, sector, GCI, tier, data as of, reviewer stamp, one delivery sentence.

The metric strip leads with the level and the unit. On Infosys that is constant-currency revenue growth, 3.1%. A change versus the prior year’s growth rate, if it is shown, is named as a change in the growth rate. It is not shown as a revenue decline. The −26.2% figure that was on the page is that kind of misreading, and it goes.

Guest panels are six: header, delivery record, evidence, revisions, how calculated, footer. Promise threads are the revision view, not a seventh essay. GCI trend, metric-change bars, and score history leave the guest page. The year arrangement in section 7 is inside the evidence panel, not a new panel.

Delivery chips are met, exceeded, missed, and pending. A zero chip is omitted, including Unmapped and Pending guidance cite. “Not citeable” becomes the coverage sentence. Outcome words are the methodology words, not raw enums.

Column headers stay Promise and Result, with the date under the link. When the promise date is after the result date, as on the Infosys FY25 operating-margin row (promise 28 Jul 2026, result 17 Apr 2025), the row is flagged “Promise date is after the result date” and stays out of any new average. The dates are not swapped. The published 76.5 is unchanged until a reviewer accepts a correction.

### 4.4 Rooms whose introductions still describe what moved

Filing Search drops the expert chip. Chat, snapshot, news, and watchlist stay as seat tabs, with the explanation a viewer already gets.

The Explorer hub lede names the live rooms: themes, street context, field evidence, compare, deep dive, fundamentals. Street, Field, and Fundamentals appear in “Open a surface”. Compare reads “One question, several companies, each cell opens the filing.” Search, boards, and agents are not described as rooms on this hub.

Homepage cards match the rooms. The snapshot card says delivery record, and rank only once the threshold is met. It does not say “by sector”. The workbench card says plans. The explorer card does not say Beta or boards.

Workflows stays four articles. It does not become a calendar. Once the portfolio and analyst landings exist, the articles point at those screens for a seat and keep the public links for a guest.

## 5. What each seat is refused, in words

The refusal is a sentence on the page they opened, plus 403 on the direct call.

| They tried | They see |
|---|---|
| Portfolio, and the plan has no holdings | “The book opens on a Desk plan or above.” A link to the screener. |
| Data, and the plan has no file export | “The file is on the Enterprise plan.” The field table stays. |
| Investor relations, empty allow-list, Board pack | “Your desk admin has not named a company for packs yet.” |
| Investor relations, company outside the list | 403. No pack. |
| Oversight opens Invites or Billing | The item is not in the menu. A direct URL is the existing settings denial. |
| Analyst presses Accept | The control is absent. The line says a reviewer accepts the row. |
| Anyone accepts from a seat without that right | 403, and the published number is unchanged. |

## 6. Stories

**PR-1.** Given an owner invites a portfolio manager, when that person accepts and the plan includes holdings, then `/holdings` shows covered weight, the weighted published GCI, and the named gaps, and Accept is absent everywhere they can open.

**PR-2.** Given an analyst submits an accept to `POST /api/review`, then the response is 403 and the company’s published GCI is unchanged.

**PR-3.** Given a reviewer accepts the same row, then the response is 200, the audit event names them, and the score ledger records the change if the published number moves.

**PR-4.** Given an IR seat’s allow-list is Infosys only, when they open HDFC Bank and request a pack, then the pack is refused.

**PR-5.** Given a data seat on Enterprise, when they open `/developers`, then the field table is first and the sample file downloads. Given the same seat on Pilot, the download is replaced by the Enterprise sentence.

**PR-6.** Given an oversight seat opens organisation settings, then audit is visible and Invites and Billing are not.

**PR-7.** Given a guest opens `/tracker`, then the index is an India index and the title matches it.

**PR-8.** Given the snapshot has no established or deep name, when a journalist reads the heading and the first row, then both say the row is a delivery record and the tier is provisional.

## 7. Working surface — the 25 Oct terminal pass

A PM has Infosys open and wants constant-currency revenue across the closed years in one glance, then the sentence in the filing, without losing the table. A coverage analyst wants the list to open on names that already have a score. A signed-in seat wants to type INFY and land on that dossier.

This section does not add a score, a route, a filing client, or a second evidence table. Guest caps stay. Change chips stay on the citeable series rule.

### 7.1 By year, inside the evidence panel

“By year” opens first. “By row” is one control away. The cite-row table remains how a reader copies both dates, both quotes, and both links, and it remains the table review actions hang off.

For Infosys, constant-currency revenue growth is one row. Columns run from the latest year back: FY26, FY25, FY24, FY23, FY22. Each cell shows the guided band, the reported figure, and the outcome in words (met, exceeded, missed, dropped, pending). A pending cell is visible and is not labeled met. A year with no row is an em dash. The metric name is the display name, never the metric id. Columns are the periods on that company, newest first, derived in the client from `outcomes` on the company payload. There is no new history endpoint.

The last column is the track: outcome words for closed years on that metric, oldest to newest. Example: Met · Met · Exceeded · Missed. Pending years are omitted. There is no segment bar and no numeric gap versus the guided midpoint.

Declined: by year as the only public view, and a pivot that exists only on the workbench.

### 7.2 Citation pane

A promise click and a result click keep the table on the left and open the stored text on the right, about 60/40. The quote is highlighted from the character span already stored. Escape closes the pane. “Open original” and “Copy citation link” stay. Full screen is a wider dock, not a second viewer. Download is the stored file when one is held, not a fresh fetch from the exchange.

Promise links join this pane. Today they leave the app.

The same open-source call is the only entry. Filing Search, the revision trail, and Disclosure Explorer dock the same way, so a reader learns one gesture.

Declined: a highlight box on a PDF page, and a new extract that stores a page rectangle. India guidance is often a transcript or exchange HTML. The text already stored is the source the score cites. The browser does not fetch NSE, BSE, EDGAR, or the issuer site.

### 7.3 Density, type, disclaimer

Compact is the default on the screener and the dossier. On a 1920×1080 screen the screener shows at least 25 company rows without scrolling the window. The table itself may scroll. Numbers and percents sit on the right. Metric names sit on the left. Fiscal periods and tickers use tabular figures.

IBM Plex Sans stays the face for numbers, with tabular figures. Tickers and fiscal periods use IBM Plex Mono. The account control still offers Comfortable, and this pass applies that preference when it is set. JetBrains Mono and Roboto Mono are not added.

One disclaimer line remains at the foot of the screener and the dossier. It is not collapsed behind an info control. The one-sentence delivery record stays. It is the record, not a banner.

### 7.4 Palette and frame

From a working route, Cmd+K on macOS and Ctrl+K elsewhere opens a palette. `/` opens it when focus is not in a text field. The palette searches companies through the existing company search and lists the tools already in the nav: GCI Screener, Filing Search, CiteAlpha Analyst, Public Snapshot, Analyst Workbench, Disclosure Explorer, Holdings, Financial Ninja. Choosing a company opens `/companies/{id}`. Choosing a tool opens that route.

Recent companies are the last few ids this browser opened, kept in local storage. They are suggestions when the palette is empty. They are not a watchlist and they do not change a score. The palette does not search API keys.

Declined: saved screens as palette commands, and a ticker box fixed in the header.

Marketing routes (`/`, `/products`, `/blog`, `/about`, `/trust`, `/press`, `/pilot`, `/methodology`, `/changelog`, `/help`) keep today’s header. Working routes (`/tracker`, `/companies`, `/research`, `/analyst`, `/rankings`, `/desk`, `/sights`, `/ninja`, `/holdings`) use a short frame: mark, palette hint, account. Pricing, Blog, and Learn are not in that frame. A text link “CiteAlpha” returns home. A signed-out reader on a working route sees the short frame plus Sign in, and is not sent to a login wall. There is no `/console` prefix and no separate host.

Admin and organisation settings keep the admin bar. This pass does not redraw them. Seat landings in section 3 use these same routes. A bookmark is not redirected.

### 7.5 Screener pills and the “Not scored” chip

Two pills, counts from the list already loaded: “Scored only (n)” and “All (n)”. The figures are the live counts for the index on screen. The choice is on the URL (`scored=1` or `scored=0`). Scored only is the default on every India index, including NSE All and BSE All. The empty scored state says no scored companies are in this index yet and leaves “All” visible.

A published row keeps Provisional, Established, or Deep. An unscored row may show “Not scored” in the tier cell. Colour follows the existing tier colours, and “Not scored” is quiet. Deep stays. No emoji.

### 7.6 Stories for this surface

**TM-1.** Given Infosys has constant-currency revenue for more than one closed year, when the year view opens, then those years are columns on one metric row, newest first.

**TM-2.** Given a cell is pending the guidance citation, when the year view renders it, then the cell is not labeled met and the track column ignores it.

**TM-3.** Given a result quote and a promise quote on the same row, when each is activated, then both open the citation pane and the evidence stays on screen.

**TM-4.** Given the reader opens a dossier from the screener and comes back, when the screener returns, then the scored-only choice matches the URL they left.

**TM-5.** Given a company has no published GCI, when it is shown, then the score cell has no number and the row is not ranked.

**TM-6.** Given focus is not in a text field, when the reader presses the palette shortcut on a working route, then company search uses the existing company search.

### 7.7 Acceptance

1. Infosys constant-currency revenue growth reads across closed years in one row, newest year first, with guided band, reported figure, and outcome in each cell. A year with no row is an em dash. A pending year is not labeled met.
2. The cite-row table is one control away. Both quotes, both dates, and both URLs still copy from it.
3. A promise click and a result click open the docked pane. The table remains visible. Escape closes the pane. The original URL still opens.
4. The screener in compact density shows at least 25 rows on a 1920×1080 viewport without scrolling the window.
5. Financial figures in the screener and the dossier use tabular figures. Decimal columns line up on the right.
6. Returning from a dossier restores the scored-only pill, because it is on the URL.
7. An unscored name has no GCI and no rank. A citeable change chip is still an em dash when the series is not citeable.
8. The disclaimer line is present on the screener and the dossier.
9. Cmd+K / Ctrl+K opens the palette from a working route and reaches a company through the existing search.
10. No new guidance-history route. No second source viewer. No change to a published GCI, tier rule, or score ledger.

## 8. Out of scope

Anything in section 7 of the BRD. Also: a role switcher that grants a second seat’s permissions, a per-user theme, and a new route per seat. Landings use the routes already in the app.
