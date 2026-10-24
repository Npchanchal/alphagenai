# Accel Atoms — supporting pack

**Apply:** https://apply.accel-atoms.com/  
**Program:** https://atoms.accel.com/ai  
**2026 cohort announcement:** https://atoms.accel.com/news/meet-the-startups-in-ai-cohort-2026  
**Google partnership note:** https://atoms.accel.com/news/ai-cohort-2026-with-google

File even though the 2026 class is chosen. Their form says an AI application is considered when the next AI cohort starts, and that you may re-apply when the facts change.

## What you are actually requesting

| Item | Ask |
|---|---|
| Capital | $1–2 million |
| Co-invest | Google AI Futures Fund, only if the next cohort includes it |
| Technical | A Gemini production extract plus a written eval against accepted quotes |
| Credits | Whatever the next cohort offers. Do not underwrite the plan on credits |
| Customers | One introduction to a research desk after the eval is real |

## Form answers

**LinkedIn.** {{LINKEDIN}} — update it so the last role matches the founder paragraph.

**One sentence.**  
CiteAlpha turns Indian filings into a guidance-delivery index. The model may propose a quote. It may not publish a score.

**What is the AI, specifically?**  
Extraction of quantified guidance and of the matching actual, over NSE/BSE and issuer PDFs we have already stored. A second path is cite-only question answering that returns no answer when the passage is absent. The index math is deterministic. Gemini is supported in the client. The production extract path we will lock for the cohort is Gemini, measured against reviewer-accepted rows.

**Stage.**  
Live product. Pre-revenue. Incorporated in India as Ocotillo Innovation Private Limited.

**Why India / why Accel.**  
The corpus is Indian primary disclosure. Accel sees the institutional buyer in India. The Google relationship, if offered again, is the right lab for the eval: early Gemini access, and people who have shipped extraction. We are not applying because the slide says AI.

**Founder.**  
{{FOUNDER_PARAGRAPH}}

**Traction.**  
citealpha.com is in production. Example row: citealpha.com/companies/infy. Changelog is public. No revenue. No invented user counts.

**Use of funds.**  
45% reviewer bench (this is also the eval team). 35% design partners. 20% inference, counsel, finance.

## Technical memo (attach as a second PDF, two pages)

**Title:** Gemini extract eval — what we will measure

**Setup.**  
Take filings already in our document store. Run the current extract prompt on Gemini. Compare each proposed guidance quote and each proposed actual quote to the reviewer-accepted span. Report agreement, wrong-number, and wrong-period as separate rates. A wrong-period error is worse than a paraphrase.

**Rules.**  
- A chunk we have already extracted is not sent again.  
- A model disagreement does not move a published score.  
- The eval set is the accepted rows, not a synthetic exam.  
- We will show Accel the miss rate.

**What we want from Google, if the cohort offers it.**  
- Gemini access current at the time of the cohort, for extract, not for a chatbot.  
- One engineer who has opinions about long-document quoting.  
- Credits applied to this batch, after we know the real token cost on a 50-filing sample.

**What we will not do.**  
- Fine-tune a model on customer prompts. There are no customers yet.  
- Claim the production estate has migrated off AWS.  
- Ship an answer that is not tied to a stored passage.

## Cover note

Subject: CiteAlpha — next Atoms AI cohort — filings extract with a refuse rule

Accel Atoms team,

I am applying for the next AI cohort. CiteAlpha is live at citealpha.com. We score whether Indian listed management delivered on quantified guidance. The model proposes quotes from filings we store. A reviewer accepts them. A row without the guidance quote does not score.

I am asking for $1–2 million. If the next cohort is again a Google AI Futures Fund co-invest, we will run the production extract on Gemini and report the miss rate against accepted rows. The 2026 cohort is already seated; please hold this for the next one. I am happy to re-file when you open it.

{{FOUNDER_NAME}} · {{PHONE}} · {{EMAIL}} · {{LINKEDIN}}  
Ocotillo Innovation Private Limited · {{CITY}}

## Diligence

- Architecture: model proposes, human accepts, score is arithmetic. One page, from the memo above.
- Current monthly AWS and model bill. Real invoice.
- IP assignment.
- Cap table. {{EQUITY_SPLIT}} {{PRIOR_CAPITAL}}
- A sample of five accepted rows and five rejected extracts, redacted only if a contract requires it. Public filings need no redaction. This sample is the best thing you can hand a technical partner.

## Do not

- Claim membership in the 2026 cohort, or that Google has agreed to co-invest the next one.
- Send a generic “AI copilot for finance” deck. They have read it.
- Attach a roadmap of agents, wordmaps, and sentiment. Those are not the raise.
