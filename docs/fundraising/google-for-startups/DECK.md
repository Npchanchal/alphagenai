# Google for Startups — program brief

**This is not an equity pitch.** Do not attach a valuation, a cheque ask, or a “₹5 crore” slide.

**What is actually open.** The Google for Startups Accelerator: India class of 2026 closed applications on 19 April 2026 and ran from June toward a September graduation. Do not apply to that class.

**What to file now.** Google for Startups Cloud, equity-free credits. AI startups have been offered up to **$250,000 in year one and a path toward $350,000 over two years**, subject to eligibility and approval. Read the live numbers at https://startup.google.com/cloud/ and https://cloud.google.com/startup/benefits before you submit. A later accelerator cohort, when Google posts one, gets the second email in the supporting pack.

**Entity.** Ocotillo Innovation Private Limited · citealpha.com · {{FOUNDER_NAME}}

---

## 1 — What we want

Equity-free Google Cloud and Gemini credits, and a technical reviewer for one project: **quote extraction on Indian filings, scored against human-accepted quotes.**

We are not asking Google for equity, a cloud commitment letter, or a customer introduction in this application.

## 2 — The product, in one screen

CiteAlpha publishes a Guidance Credibility Index for Indian listed companies. A model may propose the guidance sentence and the later actual. A reviewer accepts both. The score is computed from accepted rows. If the guidance quote is absent, the row does not enter the index.

Live example: https://citealpha.com/companies/infy

## 3 — The technical project

**Question.** On filings we already store, how often does Gemini propose the same span a reviewer accepted, and how often does it propose the wrong period or the wrong number?

**Method.**  
- Corpus: documents already in our store. We do not refetch a filing we hold.  
- Model: Gemini, one pinned version.  
- Labels: reviewer-accepted guidance quotes and actual quotes.  
- Metrics: span agreement, wrong number, wrong period. Wrong period is reported separately.  
- A disagreement does not change a published score.

**Why Gemini.** The client already has a Gemini path. Production hosting is AWS today. This project adds a measured extract path. It is not a migration proposal dressed up as a research project.

## 4 — What the credits would pay for

| Work | Why it is cloud spend |
|---|---|
| A 50-filing calibration batch | Know real token cost before a backfill |
| Backfill of guidance quotes on stored Sensex filings | The labeling target depends on this |
| Re-run of the eval when a model version changes | So a model update cannot silently move quotes |
| Cite-only answers that return no passage when the store has none | Refusal is part of the product |

Credits do not pay salaries. The reviewer bench is a separate, equity-funded plan. If credits are declined, the product still runs on the current host.

## 5 — Who we are

{{FOUNDER_NAME}}, {{CITY}}. {{FOUNDER_PARAGRAPH}}  
Company: Ocotillo Innovation Private Limited, incorporated {{INCORPORATION_DATE}}.  
Stage: product live, pre-revenue, pre-institutional-round ({{PRIOR_CAPITAL}}).  
We fit a “building, not yet venture-funded” credits tier if that is the tier they assign. We will not claim a round we have not closed.

## 6 — What we will report back

A three-page note: sample size, agreement rate, wrong-number rate, wrong-period rate, cost per filing, and whether we pinned Gemini for production extract. We will send it whether the rates are flattering or not.

## 7 — What we will not ask Google to endorse

- The index level of any company.
- A regulatory conclusion.
- A comparison that names other vendors in a press quote.
- Migration off AWS as a condition of the credits.

## 8 — Contact

{{FOUNDER_NAME}} · {{EMAIL}} · {{PHONE}} · {{LINKEDIN}}  
Company domain email: sales@citealpha.com  
Site: https://citealpha.com

**Say, if there is a call:** “Please judge the eval design. The fundraise is a different conversation and it is not with you.”
