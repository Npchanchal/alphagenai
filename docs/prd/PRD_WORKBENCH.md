# PRD — Analyst Workbench

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/desk`  
**Owners:** `DeskPage.tsx`, `DeskConsole.tsx`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_ANALYST.md](PRD_ANALYST.md)

---

## Prime requirement — a person checking a quote before it becomes the score

A reviewer opens the Analyst Workbench with one company in mind and a queue of proposed figures. Their job is to look at the quote in the filing and accept it, fix it, or send it back. The screen should feel like a reading desk: the company stays put, the quote is on the page, and the decision is an explicit button with their name on it afterwards.

### The company stays pinned

The company picker is sticky. Changing company changes every tab. The address remembers the tab (`?tab=review`), so a refresh, a shared link, or the back button returns to the same company and the same job. Console, Review, Corpus, and Reports are the everyday tabs. Point-in-time, facts import, parameters, word map, vernacular, labeling, and feedback live under More, and More only lists what this person can actually open.

Console shows the same score, tier, and evidence as the public dossier, so the reviewer is looking at the record the outside world sees. A link to that dossier and a link back to the screener sit beside the picker.

### The review itself

Review lists the proposed rows for this company. Each row shows the metric in words, the period, the proposed band, and the quote. “Show in filing” opens the stored passage. Accept, edit, and reject are separate actions. Accept asks for nothing clever. It records who accepted it and when. Edit lets them correct the figure against the quote, and the correction is visible. Reject keeps the row out of the score and leaves the public number as it was.

A labeler can read this queue and cannot accept. The accept button is absent, and a line says acceptance sits with a reviewer. They still have the labeling queue, when the plan includes it, which is a different job: marking the outcome, not publishing the level. An analyst can accept a guidance row and does not see the labeling queue. A reviewer on a full desk sees both. A reviewer on a pilot sees labeling only when that pilot was granted it.

### The other jobs, in the same voice

Corpus is the stored documents for the pinned company, titled as filings, not as ids. Reports export a cited pack. The export names the template, and the file carries the disclaimer. Point-in-time draws a series only when it can be cited. Otherwise the tab says the series cannot be cited yet, and it does not draw a line to fill the chart. Parameters explain the published rules in the same words as the methodology page. They do not offer a private rescoring of the public index.

Word map, when the seat has it, is labeled experimental and is visually secondary. It is not introduced as the score. Vernacular, on a Desk plan and above, restates the factual record in the chosen language and keeps the disclaimer in that language. Facts import is called Facts import on the screen.

### A closed door

A guest or a viewer who opens the workbench, even on a direct link to the review tab, sees a short page: this is where a seat checks a figure against the filing, here is how to request an evaluation, and the queue is not half-loaded behind the message. On a phone the quote comes first, the decision buttons stay on screen, and the company picker does not scroll away.

## 3. Users

| Persona | Job |
|---|---|
| Reviewer or analyst on a seat that includes desk write | Open the queue, compare the quote, accept or reject |
| Quant on a seat that includes point-in-time export | Download a citeable series |
| Visitor | Sees the seat gate |

Labeling is further limited to the `labeling` feature: labeler, reviewer, admin, and owner, on Desk, Enterprise, and One-Stop, or on a pilot when `labeling_granted` is set. An analyst does not label.

## 3.1 Role requirements

The quote, the decision, and the pinned company are the reviewer’s job, described above. The table is which seat may accept, which may only read, and which finds the door closed with a plain explanation.

The page requires `desk`. Guest, viewer, and member do not have it. Labeler, analyst, reviewer, admin, and owner have it on Pilot and above, until a pilot term ends.

| Action | guest, viewer | labeler | analyst | reviewer | admin, owner |
|---|---|---|---|---|---|
| Open `/desk` and read Console | Gate. API for a desk read returns 403 | Allowed | Allowed | Allowed | Allowed |
| Read the review queue and the corpus | Refused | Allowed (`desk`) | Allowed | Allowed | Allowed |
| Accept, edit, or reject a guidance row; extract; paste or fetch a filing; import facts | Refused | 403. `desk_write` is absent | Allowed | Allowed | Allowed |
| Open the labeling queue and save a label | Refused | Allowed when the plan includes `labeling` | Refused. The analyst role has no `labeling` | Allowed when the plan includes `labeling` | Allowed when the plan includes `labeling` |
| Export an IC report | Refused | Refused. `ic_export` is absent | Allowed on Pilot and above | Allowed on Pilot and above | Allowed. Data-file export (`em_export`) is Enterprise and One-Stop only, and only for admin and owner |
| Open word map | Refused | Refused | Allowed when the plan includes `wordmap` (Pilot and above) | Allowed on those plans | Allowed on those plans |
| Open vernacular | Refused | Refused | Allowed on Desk, Enterprise, and One-Stop | Allowed on those plans | Allowed on those plans |
| Read parameters | Refused | Allowed | Allowed | Allowed | Allowed |
| Send feedback from the workbench | Refused. The tab sits behind `desk` | Allowed on Pilot and above | Allowed | Allowed | Allowed |

A viewer has `feedback` and does not have `desk`, so the workbench tab stays closed. The feedback API still accepts that viewer on Pilot and above. A guest has neither.

The menu omits an item the role cannot open. A direct `?tab=` still hits the server. The server returns 403 and does not write.

Word map’s API already requires `wordmap`. The More menu must list that tab only when the seat has `wordmap`, not merely because the seat has `desk`. Vernacular’s tab and `GET /api/vernacular/{company}` must follow `vernacular`. The labeling tab must follow `labeling`. The report export must follow `ic_export`. A desk read may stay on `desk`.

**WB-R1.** A labeler reads the queue and receives 403 on accept.  
**WB-R2.** An analyst on Desk accepts a guidance row and receives 403 on the labeling queue.  
**WB-R3.** A reviewer on Desk uses both the review queue and the labeling queue. A reviewer on a pilot without `labeling_granted` uses the review queue only.  
**WB-R4.** `em_export` succeeds for an Enterprise owner and returns 403 for an Enterprise analyst.  
**WB-R5.** A guest who opens `/desk?tab=review` sees the gate, and the queue is not requested.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | One workbench. Tabs stay in `DeskPage.tsx`. No second desk application. |
| D2 | The query string is the source of truth for the tab, so refresh and back keep the place. |
| D3 | Primary tabs are Console, Review, Corpus, and Reports. Further tabs (point-in-time, facts import, parameters, word map, vernacular, labeling, feedback, customer view) sit behind More. |
| D4 | Word map and experimental analytics stay behind their feature flags and carry an experimental label. They are not the GCI. |
| D5 | Facts import is the name on the page. The legacy internal name is not shown. |
| D6 | A guest or a plan without desk access gets `PlanAccessGate`, including on a direct `?tab=` link. |

## 5. What the workbench is not

- CiteAlpha Analyst’s skill runner. Running a skill and storing a project stay at `/analyst`. The workbench links there. It does not copy the skill list.
- A retail terminal.
- A place that applies an audit deduction because a keyword matched. Audit flags move the score only when a reviewer saves the flag with an identity and a source URL.

## 6. Behaviour

1. The page requires a desk seat. The company picker is sticky.
2. Console is the multi-pane view of the company the seat is on: score, tier, and the evidence, with the same numbers as the dossier.
3. Review lists extracted rows for the company. The reviewer sees the quote and the source. Accept, edit, and reject are explicit. Accept records the reviewer and the time.
4. Corpus is the stored documents for that company.
5. Reports export a cited pack. The export names the template and keeps the disclaimer.
6. Point-in-time shows a series only when it is citeable. Otherwise the page says the series cannot be cited.
7. Parameters explain the published scoring rules. They do not offer an unsaved local rescoring of the public index.
8. Vernacular text, when the plan includes it, restates the factual record and keeps the disclaimer.
9. Desk guides for buy-side, sell-side, quant, and IR are anchors on the products page, not extra workbench products.

## 7. Stories

**WB-1.** Given a reviewer accepts a guidance row whose quote is in the stored filing, when the dossier reloads, then the row can enter the score only if the matching actual citation is also present.

**WB-2.** Given a visitor opens `/desk?tab=review`, when the page loads, then the gate is shown and the queue is not.

**WB-3.** Given a point-in-time series is not citeable, when the point-in-time tab opens, then no synthetic history is drawn.

**WB-4.** Given the reviewer rejects a row, when the public GCI is read, then that row has not changed the published number.

**WB-5.** Given a labeler posts an accept, when the API answers, then the status is 403 and the public GCI is unchanged.

**WB-6.** Given an analyst on Desk opens the labeling queue, when the API answers, then the status is 403. Given a reviewer on the same desk opens it, then the queue is returned.

**WB-7.** Given an Enterprise analyst requests a data-file export, when the API answers, then the status is 403. Given an Enterprise owner requests the same export, then the file is returned.

## 8. Index integrity

Accept and reject are the governance path. A published move still appends the score ledger and the changelog. The workbench does not overwrite a prior ledger row.

## 9. Test plan

- Seat gate on `/desk` for a guest.
- Accepting a row records reviewer id and time.
- Public payload has no demo point-in-time series.
- Word map route returns 401 or the feature gate without the feature.

## 10. Files

`frontend/src/pages/DeskPage.tsx` · `frontend/src/components/DeskConsole.tsx` · `frontend/src/lib/deskPaths.ts` · review and labeling routes in `backend/app/api/routes.py`
