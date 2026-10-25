# PRD — Workflows

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/workflows`  
**Owners:** `WorkflowsPage.tsx`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_ANALYST.md](PRD_ANALYST.md) · [PRD_SCREENER.md](PRD_SCREENER.md) · [PRD_SIGHTS.md](PRD_SIGHTS.md)

---

## Prime requirement — four jobs, each with a door that opens the right room

A reader who clicked “earnings season” on the homepage should land in a short article that tells them what to open, with Infosys as the worked example, and a link that goes there. Workflows is that map. It is read in a few minutes. It does not become a product of its own, and it does not show a new score.

### How the page is read

The title says these are the jobs a desk already does, and that a score still comes only from a guidance quote and the later reported figure. A contents line jumps to each job. The address can be shared: `/workflows#earnings-season`, `#management-delivery`, `#coverage`, `#desk-note`. Opening one of those links scrolls that article under the sticky header, so the heading is not hidden behind the bar.

Each article is a lede, a short body, and text links. Earnings season points at the Infosys dossier and at monitors in CiteAlpha Analyst, and it says a Coverage Monitor quotes the new filing and leaves the published score to the reviewer. Management delivery points at the screener, the Infosys evidence, and the methodology. Coverage points at the screener, the Public Snapshot, and Disclosure Explorer, and it says a listing is not yet a score. The desk-note article points at CiteAlpha Analyst and the workbench, and it says an upload stays on the project until a reviewer accepts a figure.

The page ends by pointing at plans. It does not embed a checkout.

### The same page for everyone

A guest and an owner read the same four articles. The difference shows up when they follow a link. The dossier, the screener, the snapshot, and methodology open for anyone. Analyst and the workbench open for a seat, and a visitor who follows those links sees that seat’s own explanation, not a dead end. On a phone the articles stack, the contents line wraps, and the heading they jumped to sits below the bar.

## 3. Users

| Persona | Job |
|---|---|
| Head of Research | Pick the job and land on the dossier, the screener, Explorer, Analyst, or the workbench |
| Visitor | Read the page with no seat. Links that need a seat show that seat’s gate on arrival |

## 3.1 Role requirements

Everyone reads the same four articles. The table is what happens when they follow a link, because that is the moment the page either opens the dossier or explains the seat.

`/workflows` is public. Every role reads the same four sections. The link opens the destination, and that destination applies its own role.

| Link | Signed out, guest | viewer | labeler | analyst, reviewer, admin, owner |
|---|---|---|---|---|
| Infosys dossier, the screener, the snapshot, methodology | The public page. A guest still has the 15-open cap on later dossiers | The public page | The public page | The public page |
| Disclosure Explorer browse | Allowed | Allowed | Allowed | Allowed |
| CiteAlpha Analyst, including monitors | Gate on arrival | Gate | Gate | The analyst page, on Pilot and above |
| Analyst Workbench | Gate | Gate | The workbench, read. Accept still needs `desk_write`, which the labeler does not have | The workbench, including write, on Pilot and above |
| Plans | The public plans page | The public plans page | The public plans page | The public plans page |

The page does not preview a seat’s private note, a holdings file, or a worksheet.

**WF-R1.** A guest and an owner read the same four sections.  
**WF-R2.** A viewer who follows the Analyst link sees the Analyst gate, then can use Filing Search because the viewer has `research`.  
**WF-R3.** A labeler who follows the workbench link can read the queue and cannot accept a row.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Four sections, stable anchors: `#earnings-season`, `#management-delivery`, `#coverage`, `#desk-note`. |
| D2 | The page is linked from Learn and from the homepage. Hash navigation scrolls the section into view under the sticky header. |
| D3 | Earnings season points at the Infosys dossier and at monitors in CiteAlpha Analyst. The body says a Coverage Monitor quotes the new filing and does not publish a score. |
| D4 | Management delivery points at the screener, the Infosys evidence table, and methodology. |
| D5 | Coverage points at the screener, the Public Snapshot, and Disclosure Explorer, and says a listing is not a score. |
| D6 | The desk-note section points at CiteAlpha Analyst and the workbench. It says an upload stays on the project and a reviewer accepts a figure before it enters the score. |
| D7 | The page ends at plans, not at a new checkout. |

## 5. What Workflows is not

- A fifth application with its own data.
- A promise that every filing produces a revised score.
- A team page or a case study written as fiction.

## 6. Behaviour

1. The title and lede say the jobs use routes that already exist, and that a score still comes only from a guidance quote and the later reported figure.
2. A contents row jumps to each anchor.
3. Each article has a lede, a body, and text links.
4. `/workflows#desk-note` and the other hashes land on that article after the page loads.
5. The page is in the sitemap and in `seoRoutes.json`.

## 7. Stories

**WF-1.** Given the reader opens `/workflows#coverage`, when the page has loaded, then the coverage article is at the top of the content area.

**WF-2.** Given the reader follows “Infosys evidence”, when the dossier opens, then the evidence table is the Infosys record.

**WF-3.** Given the reader follows “Monitors in CiteAlpha Analyst” without a seat, when Analyst loads, then the seat gate is shown.

**WF-4.** Given a viewer follows the workbench link, when the page loads, then the workbench gate is shown.

**WF-5.** Given a labeler follows the workbench link and an analyst follows the Analyst link, when both pages load, then the labeler sees the workbench and the analyst sees the skills.

## 8. Index integrity

The page states the scoring rule and does not display a new number of its own.

## 9. Test plan

- Route test id `workflows-page`.
- Each `workflow-{id}` is present.
- Public-copy hygiene on the workflow strings.
- Hash scroll leaves the heading below the sticky bar.

## 10. Files

`frontend/src/pages/WorkflowsPage.tsx` · `frontend/src/components/NavMenu.tsx` · `frontend/src/components/SiteFooter.tsx` · `frontend/src/lib/seoRoutes.json` · `frontend/public/sitemap.xml`
