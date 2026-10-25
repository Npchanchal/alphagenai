# PRD — CiteAlpha Analyst

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/analyst`  
**Owners:** `services/agent/*`, `AnalystPage.tsx`, `app/skills/*.json`  
**Related:** [PRD_WORKBENCH.md](PRD_WORKBENCH.md) · [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md) · [PRD_ADMIN.md](../PRD_ADMIN.md)

---

## Prime requirement — a note the morning a filing lands

An analyst opens CiteAlpha Analyst because a filing came in and the note has to go out in the desk’s format, with the quote still attached. They pick a skill, they pick a company or a project, and they read a draft that shows its sources. They should always be able to tell three things apart: the published GCI, the filing that just arrived, and a figure they typed themselves.

### Choosing the work

The page opens on the skills and the last runs, not on a settings form. The skill names are jobs (“coverage”, “earnings note”), not file names. The company, the watchlist, or the project is chosen before Run. Run is the one primary button. While the note is being written, the button shows that it is working, and a second click does not start a twin.

The finished note has sections, numbered claims, and a source on each claim. A claim the sources do not support is dropped, and the note says a claim was dropped rather than leaving a hole the analyst has to discover in committee. Opening a source shows the passage. The run is saved, and the address can be shared inside the desk as `/analyst?run=`.

### The morning after a filing

A Coverage Monitor watches a company, a watchlist, or a project. The first time it runs, it learns what is already stored and stays quiet. Later, a new filing with a link produces a note: what was filed, which guidance is still open, and the delivery record as it stands. The email to the owner, when an address is set, is that note and a link back to the run. The email does not say the score was revised. The score moves only after a reviewer accepts a figure on the workbench.

The feed is a list of these runs, newest first, with the company and the time in the row. Empty is a sentence: no filing has arrived since the monitor was set.

### Private papers

A project holds the desk’s uploads, the analyst’s own memory of the name, and the house format. An upload is searched inside the project. It does not appear on the public dossier as if the company had filed it. Memory is labeled as the analyst’s focus. It is never printed as a citation. A model figure the analyst stores is labeled as theirs, with the assumptions beside it. The published GCI on the company page is unchanged when they save it.

Export is Excel, PowerPoint, PDF, or Markdown. Whatever the house colours, the file still carries the disclaimer, the data-as-of date, the run id, and the Evidence Receipt. A reader of the PDF can find the filing without calling the analyst.

### Who is in the room

A visitor who opens `/analyst` sees a short explanation of what a seat adds, and a way to request an evaluation or to sign in. They do not see a skill list they cannot run. A labeler, who works on the workbench, sees the same door. An analyst sees the skills.

House style, destinations, and Analyst keys are the owner’s and the admin’s job. An analyst who opens settings can read the current style. The controls that change it, or that mint a key, are absent for them. A key is shown once, with a sentence that it will not be shown again. Destinations are Slack, Teams, or a web address the desk already uses, tested with one button that says whether the test arrived.

On a phone the run is readable as a document. The skill picker stacks. Export remains available. The page does not become a dashboard of cards with no paragraph to read.

## 3. Users

| Persona | Job |
|---|---|
| Analyst on a pilot or desk seat | Run a skill, read the feed, open a saved run |
| Org owner or admin | Set house style, destinations, and Analyst API keys |
| Reviewer | Accept a guidance figure on the workbench before it can enter the score. The analyst upload does not do that |
| Visitor | Sees the seat gate. No run, no upload, no monitor |

## 3.1 Role requirements

The note, the monitor, and the export are the analyst’s morning, described above. The table says who is let into that room, who may change the house format, and who may accept a commitment. A person who is turned away sees the explanation, not an empty skill list.

Opening CiteAlpha Analyst requires `analyst_agent`. Viewer, member, labeler, guest, and a signed-out visitor do not have it. Analyst, reviewer, admin, and owner have it when the plan is Pilot, Desk, Enterprise, or One-Stop. An ended pilot falls back to `tracker` and loses it.

| Action | guest, viewer, labeler | analyst | reviewer | admin, owner |
|---|---|---|---|---|
| Open `/analyst`, run a skill, read the feed, create a project, upload, and create a monitor | Page gate. API 403 `analyst_agent` | Allowed | Allowed | Allowed |
| Read house style | Refused with the page | Allowed | Allowed | Allowed |
| Change house style, mint or revoke an Analyst API key, add or remove a destination | Refused | 403. The detail says only an organisation admin or owner can manage connectors | 403, same detail | Allowed |
| Accept or close a commitment | Refused | 403, even with a labeling grant. The detail says only a reviewer can accept or close a commitment | Allowed when the plan includes `labeling` | Allowed when the plan includes `labeling` |
| Include unreviewed proposals in a run | Refused | Omitted. The flag is honoured only when the seat also has `labeling` | Allowed when `labeling` is on the plan | Allowed when `labeling` is on the plan |

`labeling` is on Desk, Enterprise, and One-Stop. On Pilot it is added only when the organisation has `labeling_granted`. A reviewer on an ordinary pilot cannot accept a commitment until that grant is on.

Monitors, projects, uploads, and runs are stored for the organisation. Another organisation receives 404. A labeler is not a shortcut into this route: labeling lives on the workbench.

**AN-R1.** Viewer, labeler, and guest get the gate and a 403, with no run row written.  
**AN-R2.** Analyst keys, destinations, and house-style writes are `admin` and `owner` only.  
**AN-R3.** Commitment accept is `reviewer`, `admin`, or `owner`, and only with `labeling`. An analyst’s 403 does not change the commitment.  
**AN-R4.** A monitor on one organisation is invisible to another organisation.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | One agent stack. Skills, monitors, projects, uploads, exports, digest, and destinations stay in `services/agent/`. Retired Sights agents and export return 410 with `moved_to`. |
| D2 | Tools are read-only. The verifier drops a claim that the tools did not return. |
| D3 | A monitor’s first run records documents already stored and does not fire. Later, only ingested filings with a URL count as new. Generated excerpts do not. |
| D4 | On a new filing the processor may queue commitment proposals as unreviewed. It runs the skill, quotes that filing, saves the run, and emails the monitor owner when an address is set. It does not accept the commitment and does not write a GCI. |
| D5 | Coverage Monitor sections are recent filings, open guidance, open commitments, and the delivery record. Copy must not say the note always contains a revision or a new score. |
| D6 | A project belongs to one organisation. Another org receives 404. Memory is labeled analyst focus and is never cited. A model figure is the analyst’s number, with assumptions and sources. |
| D7 | House style changes logo, colours, and footer. Every export still carries the disclaimer, data as of, the run id, and the Evidence Receipt. |
| D8 | The weekly digest replaces the Radar digest. The old Radar routes return 410. |

## 5. What Analyst is not

- The public GCI. `get_gci` on the connector returns published numbers only.
- A second mail system. Mail uses `services/mailer.py`.
- A place to appoint seats. That is the organisation admin menu.
- Sentiment, a price target, or a recommendation.

## 6. Behaviour

1. `/analyst` is behind `PlanAccessGate`. `?run=` opens a saved run.
2. The analyst picks a skill and a company, a watchlist, or a project. The run shows sections, numbered claims, and sources.
3. Monitors are created with a scope of company, watchlist, or project. The feed lists runs. Email links back to `/analyst?run=`.
4. Uploads are parsed and searched inside the project. They do not enter the public document store as a scored filing.
5. Exports are Excel, PowerPoint, PDF, and Markdown.
6. Owners and admins manage destinations (Slack, Teams, HTTPS webhook) and org API keys. Keys are shown once and stored as a hash.
7. Public API v1 and the MCP server expose skills, published GCI, commitments, filing search, and runs. They do not expose operator routes.

## 7. Stories

**AN-1.** Given a new ingested filing with a URL, when a Coverage Monitor matches that company, then the run quotes the filing, lists open guidance, and restates the delivery record, and the published GCI is unchanged.

**AN-2.** Given the monitor has never run, when filings already exist, then they are marked seen and no note is sent.

**AN-3.** Given an analyst stores a model figure on a project, when a reader opens the public dossier, then the published score is unchanged.

**AN-4.** Given a visitor opens `/analyst`, when the gate renders, then no skill runs.

**AN-5.** Given an export, when it is downloaded, then the Evidence Receipt and the disclaimer are present regardless of house style.

**AN-6.** Given a labeler and an analyst on the same pilot, when each opens `/analyst`, then the labeler sees the gate and the analyst sees the skills.

**AN-7.** Given an analyst posts a house-style change or a new Analyst key, when the API answers, then the status is 403 and the stored style and key list are unchanged.

**AN-8.** Given an analyst accepts a commitment, when the API answers, then the status is 403. Given a reviewer on a plan that includes `labeling` accepts the same commitment with the quote in the filing, then the acceptance is stored.

## 8. Index integrity

Analyst outputs cite. They do not append the score ledger. A reviewer still accepts a figure on the workbench before it can enter the score.

## 9. Test plan

`backend/tests/test_analyst_*.py` for skills, monitors, projects, exports, connectors, house style, and the compliance sign-off. A monitor test asserts no GCI write.

## 10. Files

`backend/app/services/agent/` · `backend/app/skills/` · `frontend/src/pages/AnalystPage.tsx` · `frontend/src/pages/analyst/AnalystSettings.tsx` · `docs/kb/17-analyst-agent.md`
