# Google for Startups — supporting pack

Two applications. File the first this week. Keep the second until Google posts the next India accelerator.

## 1 — Cloud credits (file now)

**Start here:** https://startup.google.com/cloud/  
**Eligibility detail:** https://cloud.google.com/startup/benefits

Public criteria have included: a real product, a company domain email, a Google Cloud billing account, founded within the last few years, and not already holding a large credit grant. AI startups have been offered a higher year-one credit than other startups. **Read the form.** If it requires a prior venture round and you do not have one, use the tier for companies that have a product and intend to raise. Do not invent a round to qualify.

### Before you click submit

- [ ] Google Cloud billing account in the company’s name. Billing ID written down.
- [ ] Email on the form uses the company domain, matching citealpha.com.
- [ ] Site loads. About and product pages describe the index, not a consumer trading app.
- [ ] You can explain, in the box they give you, the project in the deck. Paste the text below.
- [ ] You have not had a prior grant above their “new to the program” threshold. If you have, stop and disclose it.

### Paste into the product description

CiteAlpha publishes the Guidance Credibility Index for Indian listed companies. We extract quantified guidance from primary filings we store, match the later reported actual, and compute a 0–100 score from reviewer-accepted pairs. A row without the guidance citation is excluded. The product is live at https://citealpha.com. Example: https://citealpha.com/companies/infy. We are pre-revenue. Production hosting is AWS. We want credits to run a pinned Gemini extract against those accepted quotes and to report agreement, wrong-number, and wrong-period rates. Credits will not be used to move a published score automatically.

### Paste into “how will you use Google Cloud / Gemini”

1. Pin one Gemini model. Run it on 50 filings already in our store. Record token cost and the three error rates.  
2. If the wrong-period rate is low enough that reviewers can clear the queue, backfill stored Sensex filings. Reviewers still accept every quote that can affect a score.  
3. Re-run the 50-filing set on any model change before we accept the new model.  
4. Optional: cite-only answers in the analyst workflow, returning no answer when no stored passage supports it.

We will send Google a short written result. We are not requesting equity investment, a case study, or a logo.

## 2 — Next accelerator (do not file against the closed 2026 class)

When the next Google for Startups Accelerator: India page opens, use this email and a fresh form. The 2026 class wanted AI-first companies, Seed to Series A, with some traction, especially agentic workflows. You can meet “agentic” honestly: the system proposes quotes, refuses when the citation is missing, and does not publish on model output alone. You cannot meet “Series A traction” today. If the next page still requires venture funding or revenue, wait or apply only to credits.

Subject: CiteAlpha — next India accelerator — extract-and-refuse on Indian filings

Google for Startups team,

Please consider CiteAlpha for the next India cohort. We are an Indian company (Ocotillo Innovation Private Limited). The product at citealpha.com scores whether listed management delivered on quantified guidance. The model proposes spans from filings we store. Reviewers accept them. The index does not move because a model changed its mind.

We are pre-revenue. The project we want help with is a Gemini eval: span agreement, wrong number, wrong period, cost per filing. Production is on AWS; we are not applying in order to migrate for its own sake.

2026 applications are closed on your site. I will submit on the form when the next class opens. Credits application: {{submitted / not yet}}.

{{FOUNDER_NAME}} · {{EMAIL}} · {{PHONE}} · {{LINKEDIN}}

## Technical appendix (second PDF if the form allows one)

**Name.** Gemini quote eval for the Guidance Credibility Index.  
**Owner.** {{FOUNDER_NAME}}.  
**Data.** Filings already stored for Indian issuers. Public company disclosures. No personal data.  
**Label.** Human-accepted guidance span and human-accepted actual span, with period and metric.  
**Split.** Report rates on a frozen 50-filing set. Do not tune prompts on that set and then quote the same set as the result. If you tune, say so, and hold out another 50.  
**Decision rule.** Gemini does not publish. A reviewer does.  
**Cost note.** We will state cost per filing at the pinned price.  
**Residency.** Production data stays where it is (AWS, ap-south-1) unless a later contract says otherwise. The eval can run in a Google project without moving the system of record.

## Diligence Google may run

- Domain email and DNS.
- Company registration.
- Whether the site is a real product.
- Billing account identity.
- Sanctions / restricted-use questions. Answer them literally. This is public-company text, not consumer surveillance, not a credit score on a person.

## Do not

- Call this a fundraise in the credits form.
- Promise to move production off AWS.
- Ask for a quote from Google for the website.
- Apply to the April 2026 accelerator URL and hope. It is closed.
- Claim the Accel × Google 2026 cohort. That class has been announced, and we are not in it. A credits grant is independent.
