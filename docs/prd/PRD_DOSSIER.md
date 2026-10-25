# PRD — Company dossier

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/companies/:id`  
**Owners:** `CompanyDetailPage.tsx`, `EvidenceTable.tsx`, `repository.get_company_gci`  
**Related:** [PRD_SCREENER.md](PRD_SCREENER.md) · [PRD_WORKBENCH.md](PRD_WORKBENCH.md)

---

## Prime requirement — one company, ready to cite

An analyst opens a dossier to write a sentence they can stand behind. An IR officer opens it to see their own filings quoted back. A guest opens it because the screener made them curious. All three need the same thing in the first glance: the score if there is one, how much evidence sits under it, and the row that proves the latest closed year.

### The header, then the evidence

The header carries the company, the ticker, and the sector. The GCI is the large number. The tier sits beside it in words. Under that: “Data as of” the review date, who reviewed it and when, and one sentence a PM can lift. Something a person would actually write: “Met or beat revenue guidance in 5 of 6 closed years; missed FY24.” A change chip appears only when the series can be cited.

The evidence table is the first panel. Methodology and any secondary chart sit below it. Six panels is the public page. The columns a reader needs are the period, the metric in words (“Revenue growth %”, never the id), the guided low and high, the reported actual, the outcome in plain language, the guidance source and its date, and the result source and its date. Expanding a row shows both quotes. Each source opens the filing, and the passage can be highlighted. The original link stays available for someone who wants the exchange page itself.

For Infosys, the FY26 constant-currency revenue row shows guided 0–3%, reported 3.1%, exceeded, and both dates. That row is the standard for every other company.

### When there is no score yet

Apollo Hospitals can have hand-labeled rows and still have no published GCI. The page shows the evidence that exists and does not print a number. The header says why, in the coverage sentence, rather than leaving a blank that looks like a broken page. A row that has the result and not the promise is shown as not scored. It is left out of the average. Pending years are visible and excluded. If the promise and the result were reported on different bases, the row stays out and the page says so.

An unknown company is a simple not-found page with a way back to the screener. It is not a zero.

### The guest who has read enough

A guest may open 15 dossiers. The count is of companies, and the page does not surprise them on the sixteenth. When the cap is reached, the next open explains that the reading limit is 15 companies and offers the evaluation. It does not tease a blurred score. A viewer on a desk is not capped. Accept, edit, and reject never appear on this page. A seat that can review sees a text link to the workbench, not a button that changes the public number in place.

A private note, for a seat that has CiteAlpha Analyst or Financial Ninja, is clearly theirs. The public score above it does not move when they type.

On a phone the header and the one-sentence record fit without sideways scrolling. The evidence table scrolls inside itself, with the period held so the reader does not lose the year.

## 3. Users

| Persona | Job |
|---|---|
| Analyst writing a note | Copy the band, the actual, the label, and the two links |
| IR officer | See the company’s own filings cited back to it |
| Guest | Read scored dossiers up to the open cap. Cannot accept a row |

## 3.1 Role requirements

The dossier a guest reads is the dossier an owner reads. The cap, the private note, and the link through to review are the only differences, and each one should be obvious on the page rather than discovered as an error.

The evidence and the published number are public. Write actions are not.

| Action | Signed out, guest | viewer, member | labeler | analyst | reviewer | admin, owner |
|---|---|---|---|---|---|---|
| Read the score, the tier, the sentence, and the evidence table | Allowed. A guest stops after 15 opens (`guest_dossier_cap`) | Allowed, no open cap | Allowed | Allowed | Allowed | Allowed |
| Open both source links | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |
| Accept, edit, or reject a row on this page | Refused. No control | Refused | Refused | Refused. The page may link to the workbench when the seat has `desk_write` | Same as analyst | Same as analyst |
| Save a private note on the company | Refused | Refused | The control is hidden. The note is for a seat with `analyst_agent` or `ninja` | Allowed when the seat has `analyst_agent` or `ninja` | Same | Same |
| Read another person’s note | Refused. A note is stored for the signed-in actor | Refused | Refused | Refused | Refused | Refused |

The note control follows `analyst_agent` or `ninja`. The write route today requires `desk`, which a labeler has, so a direct save by a labeler must be refused the same way the hidden control already is.

A platform `super` follows the Desk feature set in [the seat model](README.md#seat-model), so the workbench link and the private note follow that set. The published GCI on the page stays the public number for every role.

**DO-R1.** The 15-open cap applies to a guest and to a signed-out browser. It does not apply to a viewer.  
**DO-R2.** A labeler reads the dossier and cannot accept a row. Accept stays with `desk_write`, which the analyst, reviewer, admin, and owner roles carry when the plan includes the workbench.  
**DO-R3.** A private note is stored for the signed-in actor. A guest, a viewer, and a different analyst do not see it. A labeler’s direct save is refused.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Evidence is the first panel. Methodology and secondary charts do not sit above it. |
| D2 | A closed row is scored only when both citations exist. A row missing the guidance citation is `pending_guidance_cite` and is excluded from the composite. It may still be shown as not scored. |
| D3 | Outcome labels are met, exceeded, missed, dropped, and pending. Pending is excluded from the average. |
| D4 | The guided band and the reported figure each keep their own unit, date, and URL. If both reporting bases are filled and they differ, the row stays outside the score. |
| D5 | Guest dossier opens increment through `bump_guest_dossier`. The cap is 15. The API returns `guest_dossier_cap`. |
| D6 | Accept, edit, and reject of a guidance figure are workbench actions. The public dossier does not expose them. |
| D7 | Public dossier stays within six panels. |

## 5. What the dossier is not

- A price page or a target-price page.
- A sentiment or word map for a guest. Word map stays behind the seat that has that feature, and it is labeled experimental.
- A holdings look-through or a valuation worksheet.
- A second score. The number is the published GCI.

## 6. Behaviour

1. `GET /api/companies/{id}/gci` returns the company, `gci_score` or null, `confidence_tier`, `coverage_status`, `coverage_reason`, `as_of`, `algorithm_id`, and outcomes.
2. An unknown id returns 404. A listed company with no score returns the coverage sentence instead of a fabricated number.
3. The evidence table columns are period, metric name (never the raw id), guided low and high, reported actual, label, guidance source and date, result source and date.
4. A source link opens the filing. An in-app source viewer may highlight the quote. The original URL remains available.
5. The header states data as of the review date, the tier, and one sentence such as how many closed years were met or missed.
6. Δ chips follow the same citeable-series rule as the screener.
7. After 15 guest opens, the next open explains the cap and links to the evaluation. It does not show a partial score invented for the gate.

## 7. Stories

**DO-1.** Given Infosys FY26 constant-currency revenue was guided 0–3% and reported 3.1%, when the dossier opens, then that row shows both figures, both dates, and the label exceeded.

**DO-2.** Given a row has an actual citation and no guidance citation, when the composite is computed, then the row is excluded and the page does not treat it as met.

**DO-3.** Given a guest has opened 15 dossiers, when they open another, then the API returns `guest_dossier_cap` and the page offers the evaluation.

**DO-4.** Given Apollo Hospitals has hand-labeled rows and no published GCI, when the dossier opens, then the page shows the evidence that exists and does not print a score.

**DO-5.** Given a guest has opened 15 dossiers and a viewer on the same desk has not, when each opens one more company, then the guest receives `guest_dossier_cap` and the viewer receives the dossier.

**DO-6.** Given a labeler opens the dossier, when the page renders, then accept, edit, and reject are absent. The evidence matches the guest view of the same company.

## 8. Index integrity

Changing a published number on this page is a ledger event: company, as-of, algorithm, dataset version, GCI, tier, and reason. The methodology changelog and `/changelog` move the same day. Reasons are `methodology`, `data_correction`, `new_filing`, or `flag_change`.

## 9. Test plan

- Score consistency between dossier and screener.
- A row without a guidance citation is excluded.
- Guest cap returns `guest_dossier_cap` on the 16th open.
- No synthetic history fields in the public payload.

## 10. Files

`frontend/src/pages/CompanyDetailPage.tsx` · `frontend/src/components/EvidenceTable.tsx` · `backend/app/services/repository.py` (`get_company_gci`) · `backend/app/services/session_auth.py` (`bump_guest_dossier`) · `GET /api/companies/{id}/gci`
