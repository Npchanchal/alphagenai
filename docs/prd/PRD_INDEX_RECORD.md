# PRD — Methodology, changelog, company, and trust

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Routes:** `/methodology`, `/changelog`, `/about`, `/trust`, plus `/help`, `/terms`, `/privacy`  
**Owners:** those pages, `score_changelog.json`, `score_ledger.jsonl`, Trust Center API  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_SNAPSHOT.md](PRD_SNAPSHOT.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md)

---

## Prime requirement — the pages a careful reader puts next to the number

Counsel, a journalist, and a Head of Research open these pages for a reason that is easy to respect. They want the rule, the history of a change, the name of the company that operates CiteAlpha, and a straight account of how the service is secured. The pages should read as a record. They should not read as a pitch, and they should not introduce a person who was never named.

### Methodology

The page says GCI runs from 0 to 100 on closed outcomes that cite both the promise and the later result. It defines met, exceeded, missed, dropped, and pending in words, with one worked example, and it says pending is left out of the average. It says a change versus last month exists only when the series can be cited. It names the exchanges and the regulator as the source of filings, and it does not imply they endorse the score. Limitations are on the page: a short history, companies that are listed and not yet scored, and rows left out when one of the two quotes is missing. A reader can reach the changelog and a company dossier from here without hunting.

### The changelog

Each entry has a date, a reason a person can say (a methodology change, a data correction, a new filing, a flag change), and what moved. When a level moved, the entry shows the old number and the new number. When nothing moved, it says the published levels were unchanged. The page is a document, newest date first, not a feed of badges. There is no edit button. An owner and a guest see the same entries.

### The company

About leads with the company panel. CiteAlpha is operated by Ocotillo Innovation Private Limited. Scores are independent of payment: a covered company cannot buy, edit, or delay its score. The contact is sales@citealpha.com, as a mail link. Links go to the security section and to Workflows. The panel names no colleague, because none has been supplied for the page. Sharing `/about#company` scrolls to that panel.

### Trust

Trust is written in the present tense. Independence is repeated in the same sentence as on About. The security section is a real article, `/trust#security`, and the link scrolls to it after the page has loaded its facts, not before, so the reader does not land in a blank. The controls listed are the ones this environment actually has. If a control is off here, the row says it is off. The page does not borrow a production claim for a machine that does not have it.

Help, terms, and privacy stay the pages they already are. These requirements do not rewrite the legal text.

On a phone the company panel and the security list are a single column. The mail link is large enough to tap. A long changelog entry wraps. The date stays with the entry.

## 3. Users

| Persona | Job |
|---|---|
| Head of Research or counsel | Read the rule and the changelog before relying on a level |
| Procurement | Open Trust at the security section |
| Journalist | Name the legal entity and the contact address without a biography that was not supplied |

## 3.1 Role requirements

Methodology, the changelog, About, and Trust read the same to a guest and to an owner. Nobody edits them from the page. A plan change and a counsel attest leave the number alone.

These pages are public. The text does not change by seat. No seat role has a control here that edits a score, a ledger row, or the changelog.

| Action | Signed out, guest, viewer, labeler, analyst, reviewer, admin, owner |
|---|---|
| Read methodology, the changelog, About, Trust, Help, terms, and privacy | Allowed |
| See the company panel: Ocotillo Innovation Private Limited and `sales@citealpha.com` | Allowed. The panel names no individual for any role |
| Open `/trust#security` and `/about#company` | Allowed. The security article scrolls into view after the trust payload loads |
| Edit methodology, append a changelog entry, or move a published GCI from these pages | Refused. No form and no write route on these pages |

A published move is an index operation: a ledger row and a changelog entry the same day, with one of the four reasons. It is not an `admin` or `owner` action on `/changelog`, and it is not a platform menu item that rewrites a level. Platform `compliance` reads Trust and attests terms in the admin portal. That attest does not change a score. Platform `billing` can change a plan. The plan change does not change a score.

Trust states the controls that are on for this environment. A role does not see a stronger security claim than the payload.

**IR-R1.** An owner and a guest receive the same methodology page and the same changelog entries.  
**IR-R2.** No seat can POST a changelog row from the public page.  
**IR-R3.** About and Trust render no staff name for any role.  
**IR-R4.** A plan change and a counsel attest leave the published GCI and the ledger untouched.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Methodology and `/changelog` describe the same events. A published move is also a ledger row. |
| D2 | Changelog reasons are `methodology`, `data_correction`, `new_filing`, and `flag_change`. |
| D3 | About includes a company panel: CiteAlpha is operated by Ocotillo Innovation Private Limited, scores are independent of payment, the contact is `sales@citealpha.com`, and links go to `/trust#security` and `/workflows`. No staff names are added. |
| D4 | Trust security is an article with id `security`. `/trust#security` scrolls to it after the trust payload loads. |
| D5 | Trust states current controls (HTTPS, HSTS, auth modes, headers) from the trust payload. It does not advertise a control that is off as if it were on. |
| D6 | Help, terms, and privacy stay the existing pages. This PRD does not rewrite the legal text. |

## 5. What these pages are not

- A team page.
- A status page for incidents. That remains `/status`.
- A second methodology that contradicts `docs/kb/03-scoring.md`. The knowledge base is the internal record. The public page is the reader’s record of the same rules.
- A place to edit a score.

## 6. Behaviour

### Methodology

1. States that GCI is 0–100 on closed, dual-cited outcomes.
2. Defines met, exceeded, missed, dropped, and pending.
3. States that a change chip exists only for a citeable series.
4. Links the exchanges and the regulator as sources of filings, not as endorsements.
5. States limitations: short history, listed names without a number, and rows left unscored when the promise and the result are not both cited.

### Changelog

1. `GET /api/v1/index/changelog` feeds `/changelog`.
2. Each entry has a date, a reason, and what moved, including a before and after when a level moved.
3. An entry that does not move a level says the published levels were unchanged.

### About

1. The company panel is above the longer story.
2. The contact is a mailto link.
3. `#company` scrolls to the panel.

### Trust

1. Sections include the product and legal entity, independence, how links leave the site, counsel versions, residency, tenancy, and security.
2. Independence repeats that a covered company cannot buy, edit, or delay its score.
3. The security list is the live payload: force HTTPS, HSTS, auth modes, response headers.

## 7. Stories

**IR-1.** Given a methodology change moves a published GCI, when that change ships, then the ledger has a row and `/changelog` has the same reason and the same before and after on that day.

**IR-2.** Given a reader opens `/about`, when the page loads, then the company panel names Ocotillo Innovation Private Limited and the contact address, and names no individual.

**IR-3.** Given a reader opens `/trust#security`, when the trust payload has loaded, then the security heading is in view.

**IR-4.** Given HSTS is off in the payload, when Trust renders, then the row says it is off for this environment. It does not say it is on.

**IR-5.** Given an owner and a guest open `/changelog`, when both pages load, then the entries match and neither page offers an edit.

**IR-6.** Given platform billing changes a desk’s plan, when the dossier is read, then the published GCI is the same number as before the plan change.

## 8. Index integrity

These pages are the explanation of the ledger. They do not compute a number. If the public changelog and the ledger disagree, the ledger is the book and the changelog is corrected the same day.

## 9. Test plan

- Changelog payload matches the ledger for a known methodology row.
- `about-company` and `trust-security` render.
- Hash scroll on `/trust#security` and `/about#company`.
- Public-copy hygiene: no recommendation language, no internal metric ids, no invented personal names.

## 10. Files

`frontend/src/pages/MethodologyPage.tsx` · `ChangelogPage.tsx` · `AboutPage.tsx` · `TrustPage.tsx` · `backend/app/data/score_changelog.json` · `backend/app/data/score_ledger.jsonl` · `docs/kb/03-scoring.md` · `docs/kb/12-compliance.md`
