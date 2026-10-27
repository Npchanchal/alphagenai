# PRD — Financial Ninja

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/ninja` (`/ninja/indices`, `/ninja/tests`)  
**Owners:** `services/ninja.py`, `NinjaPage.tsx`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md)

---

## Prime requirement — arithmetic that cannot be mistaken for the index

An analyst opens Financial Ninja to do the valuation work next to the delivery record, on the same desk, without that arithmetic leaking onto the company page as if it were GCI. The page should feel like a worksheet: inputs they typed, a result that is labeled as theirs, and the published score left alone.

### The worksheet

`/ninja` is the valuation desk. The templates are the ones a desk already names: discounted cash flow, relative value, residual income, reverse discounted cash flow, and asset value. Each input is labeled with its unit. The result sits under the inputs, and the sentence on it is always the same idea, in plain words: this figure is yours, it is not the Guidance Credibility Index, and it is not a recommendation. That sentence is in the saved worksheet, not only on the screen.

Saving keeps the inputs and the result for this organisation, for that company and template. Reopening the page restores the latest save and lists earlier saves. Another desk does not see them. The published GCI is printed beside the figure and is not rewritten. Where the template has a rate, the page also shows that rate one point lower and one point higher. Those figures are the desk's arithmetic.

### Notes that earn an index, and counts that stay counts

`/ninja/indices` is the layer record: accounting, causality, conduct, and execution. An observation needs a source. Without one, the page asks for the source and does not store a floating claim. The share of notes marked supported appears only after three cited observations. With two, the page shows the two observations and says the share waits for a third.

Each layer also has five desk questions, scored 0 to 4, each with a quote, a source, a date, and a financial year. A layer level appears only when all five questions for that year are cited. The desk blend appears only when all four layers for that year are complete and that year has a delivery score on the published record. The blend is labeled as the desk's. It is not written to the company page as a level, and it does not enter the score ledger. The dossier shows the quotes only.

`/ninja/tests` counts the published delivery record: how often guidance was met, exceeded, missed. The count is a count. It does not become a price target, and it does not rewrite the GCI it counted.

On the company page, a seat that has Ninja or CiteAlpha Analyst may see their own latest cited note. It is marked as the desk’s note. The GCI above it is the published one. A guest does not see the note.

### The door

Ninja is included with the desk seat that has it. It is not a separate price, and the page does not sell itself. A guest sees what the worksheet is for, and how to request the seat. The input grid stays hidden until the seat is there. On a phone each template is one column, the result stays under the inputs, and the disclaimer stays with the result.

## 3. Users

| Persona | Job |
|---|---|
| Analyst on a desk seat | Run a worksheet, record a cited observation, read a count of the delivery record |
| Visitor | Sees the seat gate |

## 3.1 Role requirements

The worksheet is the analyst’s arithmetic, kept visibly separate from the published score. The table is who may open it. A guest hears what it is for. They do not get an empty grid.

The feature is `ninja`. It is added and removed with `holdings`: analyst, reviewer, admin, and owner, on an open approved pilot or on Desk, Enterprise, and One-Stop. Viewer, member, labeler, and guest do not have it.

| Action | guest, viewer, labeler | analyst, reviewer, admin, owner |
|---|---|---|
| Open `/ninja`, `/ninja/indices`, and `/ninja/tests` | Page gate. API 403 | Allowed while the plan above is open |
| Save a worksheet, record a cited observation, and read a delivery count | Refused | Allowed. The file stays on that organisation |
| Draw a layer index from fewer than three cited observations | Refused | Refused. No index number is returned |
| Store an observation that has no source | Refused | Refused |
| Show the desk’s latest cited note on the company page | Hidden | Shown when the seat has `ninja` or `analyst_agent`. The public GCI on that page is the published number |

A worksheet figure is labeled as the desk’s. No role can file it as the company’s GCI.

**NJ-R1.** A labeler on Desk sees the gate. An analyst on Desk opens the worksheet.  
**NJ-R2.** An ended pilot loses `ninja` with `holdings`.  
**NJ-R3.** One organisation’s worksheet is absent from another organisation’s company page.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Templates are discounted cash flow, relative, residual income, reverse discounted cash flow, and asset value. Inputs are the desk’s numbers. |
| D2 | Every worksheet result carries the sentence that the figure is the desk’s, is not the GCI, and is not a recommendation. |
| D3 | Layers are accounting, causality, conduct, and execution. The share of notes marked supported requires at least three cited observations. A desk layer level requires five cited questions for that year, each scored 0 to 4 with a source. The desk blend is not a published GCI. |
| D4 | Tests count published outcomes. They do not produce a price target. |
| D5 | Notes stay on the organisation’s Ninja file. |
| D6 | The page is behind `PlanAccessGate` for the Ninja feature. |

## 5. What Ninja is not

- A published score, a rank, or a recommendation.
- A data-vendor feed. The desk types the valuation inputs.
- A second evidence table. The evidence table remains the dossier.

## 6. Behaviour

1. `/ninja` is the valuation desk. `/ninja/indices` is the layer record. `/ninja/tests` is the delivery count.
2. Saving a worksheet stores inputs and the computed figure with the disclaimer line.
3. An observation without a source is refused.
4. Fewer than three observations does not draw an index.
5. The company page may show the latest cited note for that desk. The public GCI on that page is unchanged.

## 7. Stories

**NJ-1.** Given the desk enters cash flows and a discount rate, when the worksheet runs, then the result is labeled as the desk’s figure and the company’s published GCI is unchanged.

**NJ-2.** Given two observations on a layer, when the index is requested, then no index number is returned.

**NJ-3.** Given a guest opens `/ninja`, when the page loads, then the gate is shown.

**NJ-4.** Given a viewer and an analyst on Desk, when each opens `/ninja/tests`, then the viewer sees the gate and the analyst sees the delivery count.

**NJ-5.** Given an analyst saves a worksheet, when a guest opens that company’s dossier, then the published GCI is unchanged and the worksheet figure is absent.

## 8. Index integrity

Ninja does not call the scorer to publish. Tests read the published record.

## 9. Test plan

Worksheet disclaimer present. Observation without a source refused. Index withheld below three observations. No score-ledger append.

## 10. Files

`backend/app/services/ninja.py` · `backend/app/api/ninja_routes.py` · `frontend/src/pages/NinjaPage.tsx`
