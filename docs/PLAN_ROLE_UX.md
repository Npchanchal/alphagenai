# Plan — Role UX for the next development cycle

**Status:** research log · **Substance now carried in** `docs/BRD_ROLES.md`, `docs/PRD_ROLES.md`, and `docs/TRD_ROLES.md` · **Walked:** 28 Oct 2026 · **Owner:** `frontend-designer`
**Execute with:** `citealpha-expert-ux` on public pages · `citealpha-frontend-ux` on workbench and Filing Search · `index-integrity` and `public-copy-voice` on every number.
**Extends:** the per-job PRDs in `docs/prd/` and the confirmed terminal pass in `docs/prd/PRD_TERMINAL.md`. It does not replace them, and it does not open a new route, score, or filing client.

A published GCI does not move because of this plan. Week, month, quarter, and year chips stay on the citeable point-in-time rule. Guests still read the screener without an account and still stop at 15 dossier opens.

---

## 0. What “better” means here

Each role has one decision and a short clock. The page that role opens should answer that decision before it offers the rest of the product. Nielsen Norman’s guide for complex applications is the constraint: show the frequent action first, keep a fluid path into the specialist tools, and make the important fact visually salient. Progressive disclosure is the split: the first screen holds what that role uses every week; everything else is one obvious step away, on a route that already exists.

| Role | Clock | The decision | First screen they should get |
|---|---|---|---|
| Head of Research | Morning meeting, ~10 min | Is coverage deep enough to brief, and what arrived overnight? | Screener, opened on India, with one coverage sentence and the thin records visually quiet |
| Portfolio manager | Before the open, ~5 min | Did anything in the book change the delivery record? | Holdings, once a file exists: covered weight, named gaps, and what changed |
| Buy-side analyst | Under 60 seconds to a citable sentence | What was guided, what was reported, where are the two filings? | Dossier evidence, one metric across years |
| Sell-side associate | The afternoon before a print | What is still open, and what do I ask on the call? | CiteAlpha Analyst, grouped as “this print” rather than a skill catalogue |
| IR officer | Board pack, ~2 pages | What did we guide, what did we report, what is still open? | That company’s dossier, then the existing board scorecard export |
| Credit / compliance | A review sitting | Which commitment is open, who accepted the quote, when? | Workbench review for a reviewer; the commitment list for a reader |
| Quant / data | Before a backtest | What is the row, when did it become known, what is null and why? | API page: schema, a sample file, as-of versus available date |
| Journalist | A filing deadline, a few minutes | Can I quote this number, and can a reader reproduce it? | Public Snapshot or the dossier cite line: level, tier, as-of, two links |
| Guest | One minute on the homepage | Is this a real filing comparison? | Homepage worked example, then the screener |
| Reviewer | One quote | Does this figure match the filing? | Workbench, Review tab, company pinned |
| Org owner | Seat setup | Who can run a note, and when does the evaluation end? | Organisation settings, members and the term |

Research behind the clocks:

- A buy-side morning is a funnel. The analyst asks what changed, then protects an hour for the primary document. The memo a PM will read separates the filing, the management statement, and the analyst’s own figure. ([day-in-the-life playbook](https://alpha-analyst.com/blog/day-in-the-life-of-an-investment-analyst-a-realistic-playbook), [buy-side workflow](https://weconvene.com/buy-side-research-workflow-process-reg-fd-and-platform-guide/))
- A head of research owns coverage: who covers what, what is stale, and the auditable record of notes. They do not re-screen the universe to learn that. ([OpenIM SD-02.7](https://openinvestmentmodel.org/model/bd-02-securities-research-and-selection/sd-02.7-research-management-and-coverage/), [coverage decisions sit with the head of research](https://www.mediobancaresearch.com/img/directive_production_distribution_investment_research_reports.pdf))
- An IR board pack is short. Directors ask what was guided, what was reported, and where the external view diverges. Two pages, then they ask for more. ([CIRI on board reports](https://ciri.imiscloud.com/common/Uploaded%20files/CIRI%20advisors/CIRI%20advisor%20-%20IR%20Board%20Reports.pdf), [CGI: board papers focus on what matters](https://cgi.org.uk/media/kagbmcd3/cgi_boardreporting_17july.pdf))
- A journalist’s citation is an instruction to repeat the measurement: publisher, series, period, retrieval date, and a permalink. A projection must not be printed as an outturn. ([StatCite](https://statcite.com/guide), [AFP sourcing principles](https://www.afp.com/sites/default/files/afp_-_twenty_principles_of_sourcing_-_july_2024.pdf))
- A quant buyer starts from the dictionary: a point-in-time anchor, a null with a reason, and a sample file. A tour of the UI does not answer that. ([point-in-time feed notes](https://feeds-techdocs.insiderscore.com/holdings_feeds/institutional_feeds.html))
- Complex software stays learnable when the first screen is the frequent task and the specialist tools stay one labeled step away. ([NN/g, complex applications](https://www.nngroup.com/articles/complex-application-design/), [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/))

---

## 1. Already decided — do not reopen

`docs/prd/PRD_TERMINAL.md` (confirmed 25 Oct 2026) already specifies the analyst speed pass:

- Evidence toggle: “By year” first, “By row” one control away. Same panel, same payload.
- A docked source pane (about 60/40) for both the promise and the result. Stored text, character highlight, Escape to close.
- Compact density by default on the screener and the dossier. Comfortable stays in account settings.
- “Scored only” as the default, on the URL, with live counts.
- `Cmd+K` / `Ctrl+K` for companies and existing tools.
- A short frame on working routes. Marketing routes keep today’s header.

This plan assumes that pass. Items below are the role gaps it does not cover. Where both touch `EvidenceTable.tsx` or `HomePage.tsx`, the trust fixes in section 3 land in the same change as the terminal pass so a reader never sees a year-pivot sitting on a misleading change.

---

## 2. What the live site does today

Signed-out walk of https://citealpha.com on 28 Oct 2026. Counts are what the pages printed that day.

| Surface | What a signed-out reader gets | Role fit |
|---|---|---|
| `/` | Headline, Infosys / Apollo tabs, four workflow links, live coverage (“2 of 30 Sensex companies scored”, “57 companies scored in total”, “10 companies have sample data”), evaluation form with a role field | Strong for a first visit. The product cards below still say the snapshot is “by sector”, the workbench copy says “Packages”, and Disclosure Explorer is marked Beta and described as boards. |
| `/tracker` | Title says Sensex. This session’s first paint was **US · S&P 500**: 503 names, every row unscored, GCI cell “SEC results releases since Jan 2024 not yet read”. India → BSE Sensex then showed 30 names. Axis Bank 90.7 (provisional, 1 closed result) sorted above Infosys 76.5 (provisional, 5). Quality filter still offers Hand-labeled and Demo. Twelve markets remain on the control. | A head of research cannot trust the first screen. A PM scanning GCI sees the thinnest record at the top. |
| `/companies/infy` | Header is the right sentence: 76.5, provisional, data as of 23 Apr 2026, reviewed 29 Sept 2026, “Met or beat Revenue growth (constant currency) % guidance in 4 of 5 closed years; missed FY24.” Evidence table has both dates and Copy cite. | The analyst can cite. The same page then shows a metric bar “3.1, YoY −26.2%” on a growth rate, zero-count chips for Unmapped and Pending guidance cite, and the words “not citeable”. That is past the six public panels. |
| `/rankings` | Kicker “citeable only”. Body: “As of 2026-10-27 · n=0 citeable” and “Provisional scores … are excluded.” The table under that sentence lists Infosys, HDFC Life, Adani Ports, Apollo Hospitals, Axis Bank, and Cipla, every row **Provisional**. CSV and permalink are present. | A journalist cannot tell whether the table is quotable. |
| `/research` | Reading room is honest: eight searches, Infosys selected, cite-only chat behind a seat. The company control’s text listed Infosys and Cipla. Document-type chips include **expert**. | The associate’s question box is in the right place. “Published” here, on the snapshot, and on the homepage are three different sets. |
| `/sights` | Subnav: Hub, Themes, Street, Field, Compare, Deep Dive, Fundamentals, Settings. The lede still says search, cited answers, boards, and desk agents. “Open a surface” lists three rooms. Compare Grid is “Same prompts across names”. | A PM who came to compare a sector has to translate the page. |
| `/analyst` | Gate names the jobs (results prep, ramp, call questions, board scorecard, peer delivery, India event briefs) and points at login, register, and plans. No fake skill list. | Right door. The seat, once inside, still meets a flat catalogue (see section 4). |
| `/workflows` | Four articles and links. Same page for a guest and an owner. | A map, which is what the PRD asked for. It is not the morning itself. |
| `/products` | Desk guides exist in `deskPaths.ts`: buy-side, sell-side, quant, IR / compliance. Homepage links to them. | The guides describe jobs. The working screens do not yet open in that job’s order. |

Seat surfaces were not signed into. Their shape is the shipped PRD: workbench (`PRD_WORKBENCH`), Analyst (`PRD_ANALYST`), holdings (`PRD_HOLDINGS`), Financial Ninja (`PRD_NINJA`), organisation settings, and `/admin`. The enhancements below stay inside those owners.

---

## 3. Trust fixes — before any role chrome

These are the places a careful reader would quote the wrong thing. They are presentation and labeling. They do not rescore.

### RX-0.1 One meaning of “published” on every public page

Homepage: 57 scored, 2 of 30 on the Sensex. Snapshot: n=0 citeable, then six provisional rows. Filing Search reading room: Infosys and Cipla on the control. Screener Sensex: two numeric scores, then rows that say guidance is still being checked, with a Hand-labeled badge and zero closed results.

**Change.** One sentence, from the same counts the homepage already loads, on the screener, the snapshot, and the reading room: how many companies have a published GCI, how many of those are established or deep, and that a provisional row is a record you can open and not a rank you can quote. The snapshot table either shows provisional rows and says so in the heading, or it shows the established/deep set and the empty state when that set is empty. The heading and the table have to be the same claim.

**Owner.** `RankingsPage.tsx`, `HomePage.tsx`, `ResearchPage.tsx`. No new rankings payload.

**Done when.** A journalist can read the snapshot headline aloud and it matches the rows. Filing Search’s company list is the published-GCI list, or the page says which narrower set it is and why.

### RX-0.2 A change of a growth rate is labeled as a change of that rate

On the Infosys dossier the metric strip prints revenue growth as **3.1** and **YoY −26.2%**. That −26.2% is the change in the growth rate, not a fall in revenue. The same page’s delivery sentence (4 of 5 years met or beat, missed FY24) is the line a PM should see.

**Change.** The metric strip leads with the level and the unit (“constant-currency revenue growth, 3.1%”). A change versus the prior year’s growth rate, if it stays, is named as a change in the growth rate. The public dossier drops the extra trend panels that repeat score history under the evidence (GCI trend, metric-change bars, score history) so the guest page returns to the six panels in `citealpha-expert-ux`: header, delivery record, evidence, revisions, how calculated, footer. Promise threads stay as the revision view, not as a seventh essay.

**Owner.** `CompanyDetailPage.tsx`. The year-by-metric toggle from `PRD_TERMINAL` is the evidence panel’s other arrangement, not an extra panel.

**Done when.** The Infosys page no longer shows a percent that a PM can misread as a revenue decline. Guest heading count is the six panels.

### RX-0.3 Unscored rows say why, once

Sensex rows under the two scores say “Guidance found, being checked against results” or “FY26 result not yet matched to a filing”, with quality **Hand-labeled** and closed results **0**. The US list says “SEC results releases since Jan 2024 not yet read” inside the GCI cell. The quality filter still offers Demo.

**Change.** The score cell is “Not yet scored” plus one coverage sentence already used on the dossier (what is missing: the promise, the later result, or both). The quality badge appears when a score or a sample-data row is actually on screen. Sample data is called sample data. Pipeline stage names stay off the public cell.

**Owner.** `HomePage.tsx`, `en.json` screener strings.

**Done when.** An unscored Sensex row can be read without learning an internal stage name. The quality control has no “Demo” option.

### RX-0.4 Dates that a reader will question stay visible and flagged

The Infosys FY25 operating-margin row shows a promise date of **28 Jul 2026** and a result date of **17 Apr 2025**. The table does not say which document is which beyond the column header, and it does not mark a promise that is dated after the result.

**Change.** Column headers stay “Promise” and “Result”, with the date under the link. When the promise date is after the result date, the row carries a short review flag (“Promise date is after the result date”) and stays out of any new average. This plan does not swap the dates and does not rescore the row. A reviewer clears the flag on the workbench by accepting the corrected quote.

**Owner.** `EvidenceTable.tsx` for the flag. The correction itself stays on the workbench review tab.

**Done when.** That Infosys row shows the flag. The published 76.5 is unchanged until a reviewer accepts a correction through the existing ledger path.

### RX-0.5 Internal status words leave the public dossier

The delivery record prints Exceeded 4, Met 1, Missed 1, and also Dropped 0, Pending 8, Unmapped 0, Pending guidance cite 0. Result cells say “not citeable”.

**Change.** Chips are met, exceeded, missed, and pending, and a zero chip is omitted. “Not citeable” becomes the same coverage sentence as RX-0.3 (“result not on a cited filing yet”). Enum-style labels in the evidence table render as the words the methodology already uses.

**Owner.** `CompanyDetailPage.tsx`, `EvidenceTable.tsx`.

---

## 4. Role enhancements — same routes, different first screen

No new application. A role changes the order and the default of a page that already has an owner.

### RX-1 Head of Research — coverage before the sort

**Job.** At the morning meeting they need: how many names in the index have a published score, how many are still a listing, and whether a thin record is leading the sort.

**Today.** The homepage states “2 of 30 Sensex companies scored”. The screener hides that under filters, twelve market choices, and a GCI sort that puts Axis Bank (one closed result, 90.7) above Infosys (five closed results, 76.5). The document title stays “Sensex” when the body is another market. This session’s first paint was the US list; the repo default is India (`preferences.default_market ?? "IN"`). Whatever stored that US preference, the title and the body disagreed.

**Enhancement.**

- The screener kicker is the homepage coverage sentence for the index on screen.
- A guest opens on India. Markets other than India leave the public control. A signed-in preference may remember an India index. It does not reopen a market the page has already said is unscored.
- The document title follows the index on screen.
- **Decision for the owner (not settled by the terminal pass).** Default sort becomes closed results, then GCI, so a one-period 90.7 does not read as the best record. Tier stays in the row. This is a sort, not a rank. Public Snapshot remains the only rank, and only for established and deep.

**Owner.** `HomePage.tsx`.

**Done when.** A guest landing on `/tracker` sees the Sensex (or the India index the page names), the coverage sentence, and no US constituents. The title matches the table.

### RX-2 Portfolio manager — the book is the morning, the screener is discovery

**Job.** What changed in the names they hold. A single blended number that treats cash as scored will be ignored. Gaps have to be named. ([PRD_HOLDINGS](prd/PRD_HOLDINGS.md) already requires covered weight, the weighted GCI of that weight, and a gap list.)

**Today.** Holdings is a paste box. The screener is a universe. Nothing connects “I starred these” to “what filed overnight”.

**Enhancement.** After a file is saved, `/holdings` opens on three lines: covered weight, weighted published GCI, and a gap list (no score yet, cash, debt, indirect, unknown). Under that, a “Since last visit” list built only from records the product already stores: a new filing on a held name, an open guidance item, a delivery row whose outcome is missed. Empty is a sentence. The paste box is the secondary control. The screener star, for a seat that has holdings, adds the name to that book; for everyone else it stays the watchlist on Filing Search.

**Owner.** `HoldingsPage.tsx`, `services/holdings.py`. The change list reads the document store and the published outcomes. It does not write a GCI.

**Done when.** A PM with a saved file sees the gaps and the changes without pasting again. A name with no published score appears in the gap list and has no invented level.

### RX-3 Buy-side analyst — already the dossier; finish the terminal pass

The 60-second path is screener → dossier → both quotes. RX-0.2 and the terminal pass (year pivot, docked source, compact rows, scored-only default, palette) are this role’s enhancement. Nothing further until those are on the page.

**Done when.** `PRD_TERMINAL` acceptance items 1–10 hold, and RX-0.2 holds on Infosys.

### RX-4 Sell-side associate — skills grouped by the week, not by file name

**Job.** Before a print: what is open, what changed since the last call, what to ask. After the print: a note in the desk’s format with the quote attached. The skills already exist: Results Prep Pack, Earnings-Call Question Pack, Coverage Monitor, Company Ramp, Company note.

**Today.** The signed-out gate is clear. The seat page opens on the full skill list (`AnalystPage.tsx`), including DRHP, USFDA, rating tracker, debate map, diligence room, and weekly driver review, all at the same weight.

**Enhancement.** The first group is “This print”: Results Prep and Call Questions, with the company or the watchlist chosen before Run. The second is “Learn a name”: Company Ramp and Company note. The third is “Board, credit, and events”: Board Scorecard, Peer Delivery Grid, and the India event skills. Monitors and the feed stay where they are. Run remains the one primary button. A skill that needs a project says so before Run, as the PRD already requires.

**Owner.** `AnalystPage.tsx`. No new skill file.

**Done when.** An analyst seat sees “This print” without scrolling past event skills. A visitor still sees the gate, not the list.

### RX-5 IR officer — a two-page pack from the company they already have open

**Job.** Board and management want what was guided, what was reported, what was revised in the year, and what is still open. Peer color is context. A subscription must not look like it can move the score. CIRI’s own guidance is to keep the pack short and to let directors ask for the rest.

**Today.** The dossier is the right record. The board export is a skill (`board_scorecard`) and a workbench report template, two rooms away from the company page. Vernacular restatement sits under Workbench → More.

**Enhancement.** On the dossier, a seat with Analyst sees one text link: “Board pack”. It runs the existing board scorecard for this company and exports the PDF or slides the skill already produces (disclaimer, as-of, evidence receipt). The pack leads with the one-sentence delivery record, the open items, and the closed outcomes. It does not add a peer rank. The public page keeps the independence sentence already on About: payment does not change a score. Hindi or another shipped locale, when the seat has vernacular, is a second file of the same facts, not a second score.

**Owner.** `CompanyDetailPage.tsx` link only. Export stays `services/agent/exports.py` and the `board_scorecard` skill.

**Done when.** From Infosys, a seated IR user reaches a pack that quotes the FY26 constant-currency row (guided 0–3%, reported 3.1%, exceeded) and does not invent a recommendation.

### RX-6 Credit and compliance — the queue is the product

**Job.** Which figure was accepted, by whom, and which commitment is still open. A score is optional.

**Today.** The workbench is specified as a reading desk with the company pinned and Review as an everyday tab, beside Console, Corpus, and Reports. Labeling, parameters, word map, vernacular, facts import, and feedback sit under More. That split is right and easy to lose because twelve tabs still exist in `DeskPage.tsx`.

**Enhancement.** A reviewer who opens `/desk` lands on `?tab=review` for the pinned company. Console remains one tab away for someone checking the public record. Accept, edit, and reject stay the only decisions on Review. A labeler still sees the queue without Accept. Word map stays behind its experimental label. No new compliance route: the commitment list already on the company and in Admin → commitments is the reader’s view, with the reviewer id and date.

**Owner.** `DeskPage.tsx` default tab for the reviewer role.

**Done when.** A reviewer link from a dossier opens Review, not Console. The public number changes only after Accept, as it does now.

### RX-7 Quant — the API page is a dictionary

**Job.** Column names, the date the row became knowable, what null means, a sample of real rows, and the statement that a monitor or an upload does not write the index.

**Today.** `/developers` introduces the API. Point-in-time lives on the workbench and correctly refuses to draw a line when the series cannot be cited. The buyer still has to tour the product to learn the row.

**Enhancement.** The first block on `/developers` is a field table for the published outcome: company, period, metric name, guided low, guided high, reported actual, outcome, promise date, result date, available date, tier, algorithm id. A sample file is the current published rows (the same export the Data SKU already serves), with a sha256. Null stays null, with the coverage reason. As-of and available-date are both named, so a backtest can filter on when the row existed.

**Owner.** `DevelopersPage.tsx` and the existing export. No second factor API.

**Done when.** A buyer can describe a row without opening the workbench. The sample contains no synthetic history.

### RX-8 Journalist — the cite line is the product

**Job.** Quote a level with its tier, its as-of date, and a link a reader can open. Leave if the page is a rank the data does not support.

**Today.** “Cite this page” is on the dossier footer, with methodology and changelog. The snapshot offers CSV and a permalink, then contradicts itself (RX-0.1). The page title “Guidance Credibility Quarterly” over an unranked provisional table is the line they would paste.

**Enhancement.** After RX-0.1, each snapshot row’s permalink is the dossier URL plus the as-of date already on the page. The cite control copies one sentence in the dossier’s voice: company, GCI, tier, as-of, and the delivery sentence, then the URL. No login. The title of the page matches the mode (delivery record, or rank once twenty names are established or deep).

**Owner.** `RankingsPage.tsx`, reusing the dossier cite action.

**Done when.** Copying a row produces a sentence that includes “provisional” when the tier is provisional, and does not call the table a rank.

### RX-9 Guest and the homepage — stop describing rooms that moved

The homepage is the right first minute. Adjust the cards so they match the rooms:

- Public Snapshot card: delivery record, rank only once the threshold is met. Drop “by sector” until a sector cut is on that page.
- Workbench card: “plans”, not “Packages”.
- Disclosure Explorer card: themes, street context, field evidence, compare, deep dive, fundamentals. Drop “Beta” and “boards”.
- Explorer hub lede matches that list. Street, Field, and Fundamentals appear in “Open a surface”, in the words a PM uses. “Same prompts across names” becomes “One question, several companies, each cell opens the filing”.

**Owner.** `LandingPage.tsx`, the sights hub page, `en.json`.

### RX-10 Filing Search — the chip that implies a product we do not have

Document-type chips are all, guidance, transcript, filing, news, **expert**. Field evidence is the hand-labeled record. There is no expert-call library.

**Change.** Remove the expert chip, or rename it to the document type actually in the store. The reading-room lede drops “hand-labeled dossiers” and “unscored GCI placeholders” in favour of the published-GCI sentence from RX-0.1. Chat, snapshot, news, and watchlist stay visible as seat tabs, with the explanation the PRD already specifies.

**Owner.** `ResearchPage.tsx`.

### RX-11 Workflows stay a map

`/workflows` does not become a calendar or a fifth app. Once RX-2 and RX-4 exist, the four articles point at those first screens (holdings for a book, Analyst “This print” for a note) and keep today’s public links for a guest. Earnings dates, if added later, are a list of known result dates beside the existing monitor link, not a new data product.

---

## 5. Order of work

| Slice | Items | Touches | Gate |
|---|---|---|---|
| A. Quotable | RX-0.1, RX-0.2, RX-0.5, RX-8 title | Snapshot, dossier, reading room | A journalist’s headline matches the table. Infosys shows no growth-rate “YoY” that reads as revenue. |
| B. First screen | RX-0.3, RX-1, RX-9, RX-10 | Screener, homepage, Explorer hub, Filing Search | Guest `/tracker` is India. Unscored cells use one coverage sentence. Explorer lede matches the rooms. |
| C. Seats | RX-2, RX-4, RX-5, RX-6 | Holdings, Analyst, dossier link, workbench default tab | PM, associate, IR, and reviewer each land on the job named above. |
| D. Buyer | RX-7, RX-0.4 | Developers, evidence flag | Sample file matches the dictionary. The inverted Infosys date is flagged, not silently swapped. |
| Parallel | Terminal pass | Screener density, year pivot, source pane, palette, short frame | `PRD_TERMINAL` acceptance. Slice A on the same files ships with it. |

Slice A is the next development to pick up. B can follow in the same cycle. C and D wait on a seat to click through.

---

## 6. Stories

**RX-S1.** Given the snapshot has zero established or deep names, when a journalist opens `/rankings`, then the heading calls the table a delivery record and every provisional row is labeled provisional.

**RX-S2.** Given Infosys constant-currency revenue growth is 3.1%, when the dossier renders the metric strip, then the level is 3.1% and no figure reads as a 26% revenue decline.

**RX-S3.** Given a guest opens `/tracker`, when the table paints, then the index is an India index, the title names that index, and an unscored GCI cell does not contain a pipeline stage.

**RX-S4.** Given an analyst seat opens `/analyst`, when the page loads, then Results Prep and Call Questions are in the first group.

**RX-S5.** Given a reviewer opens `/desk`, when the page loads, then the tab is Review for the pinned company.

**RX-S6.** Given a holdings file is saved, when the PM returns to `/holdings`, then covered weight, the weighted published GCI, and the named gaps are on screen before the paste box.

**RX-S7.** Given the Infosys FY25 operating-margin promise date is after the result date, when the evidence table renders, then the row is flagged and the published GCI is unchanged.

---

## 7. Out of scope

- A new route, host, or “console” for any role. Working versus marketing frames are the terminal pass.
- Buy, Hold, Sell, or a rank of provisional names.
- A team research-management system, a coverage-assignment directory, or an earnings calendar as its own product.
- Expert-call content, sell-side PDF hosting, or a document type that implies either.
- A PDF highlight rectangle. Declined in the terminal pass.
- Any change to a published number, tier rule, or score ledger, except a later reviewer Accept that already has a ledger path.
- Reopening terminal questions Q1–Q9.

---

## 8. Progress log

| Date | Note |
|---|---|
| 2026-10-28 | Walk of production, signed out: homepage, screener (US list, then India Sensex), Infosys dossier, Public Snapshot, Filing Search, Disclosure Explorer hub, Analyst gate. Seat pages taken from the shipped PRDs. Research notes in section 0. |
