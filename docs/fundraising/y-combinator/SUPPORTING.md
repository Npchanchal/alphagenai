# Y Combinator — supporting pack

File the form. The deck does not replace it. Deadline for an on-time Winter 2027 decision: **2 November 2026, 8pm PT**.

**Apply:** https://www.ycombinator.com/apply  
**Deal:** https://www.ycombinator.com/deal  
**FAQ:** https://www.ycombinator.com/faq/

Write in short sentences. YC readers skim. Do not paste the word “platform.”

## Before you submit

- [ ] Founder video, one minute, YouTube unlisted. Script below. All founders on camera. If you are sole, just you.
- [ ] Demo video, under two minutes, unlisted. Script below. No music. No titles longer than the URL.
- [ ] Product link that opens with no password: https://citealpha.com and https://citealpha.com/companies/infy
- [ ] If any page needs a login, put the credentials in the form, not in the video.
- [ ] {{FOUNDER_PARAGRAPH}} is true and matches the video.
- [ ] You have decided you will do a US / Canada / Cayman / Singapore parent if accepted. If you will not, do not apply.
- [ ] Equity numbers add to 100. {{EQUITY_SPLIT}}
- [ ] “Have you taken investment?” matches {{PRIOR_CAPITAL}}. Safes, loans from parents, and grants count. Say them.

## Founder video, 60 seconds

“I’m {{FOUNDER_NAME}}, in {{CITY}}. This is CiteAlpha. We score whether the management of an Indian listed company delivered the number it guided. Both filings are attached to the score.

{{Two sentences of FOUNDER_PARAGRAPH: where you worked, and the moment the citation was missing.}}

The site is live. We have not charged a customer yet. I want YC because the next step is fifteen research desks and a parent company your lawyers already know how to set up. I write the code / {{the true split of who builds}}.”

Look at the camera. Do not read a longer script. Record twice and ship the second take.

## Demo video, 90 seconds

1. Home page. Read the definition once.
2. Infosys. One closed year. Point at the guided figure, the reported figure, and both links. Click one link so they see a real document.
3. Say: “If the guidance quote is missing, this row does not enter the score.”
4. Changelog. “When a published number moves, the reason is public.”
5. Stop. Do not tour settings, billing, or admin.

## Form answers — paste and then delete every {{ }}

**Company name.** CiteAlpha  
**URL.** https://citealpha.com  
**Demo.** https://www.youtube.com/watch?v={{DEMO_ID}}  
**Login.** Not required for the dossier above.  
**Where you live / where the company will be.** {{CITY}}, India / San Francisco during the batch, then {{CITY}}. The operating company stays in India. We will create the parent YC requires.  
**Describe the location choice.** Customers are Indian research desks. I should be in India most weeks of the pilot. I will be in San Francisco for the batch because that is where the program is.

**What is your company going to make?**  
A 0–100 index of whether Indian listed management delivered on quantified guidance. We store the filing, extract the guided number and the later actual, and show both sources. A reviewer accepts the quotes. The product also lets an analyst search those filings and get an answer only when a passage supports it. It is live.

**How far along are you?**  
Live in production: screener, company page, filing search, API, public changelog. Pre-revenue. Coverage is the Sensex, with a lot of names still on a short history, and Nifty 50 started. We show a confidence tier so a thin history is not dressed up as a deep one. Our published goal is established depth on Sensex 30 and Nifty 50 by 31 March 2027.

**How long have you been working on this? How much full-time?**  
{{Month and year you started}}. Full-time since {{date}}. {{If you had a job in parallel, say the overlap.}}

**Tech stack.**  
Python, FastAPI, Postgres-ready document store, React. Hosted on AWS. Models: an OpenAI-compatible API and a Gemini client. The model proposes quotes. It does not publish scores. I use Cursor to write the code. {{If a contractor wrote a part, name the part.}}

**Are people using it?**  
No paying users. The pages are public. I am not going to invent a waitlist.

**Revenue.**  
None. Intended revenue is an annual seat at ₹45,000 (about $500) and a data license at ₹25–80 lakh a year (about $30–95k). Illustrative list prices. First step is a free 60-day pilot for a research desk.

**Why this idea? Domain expertise?**  
{{FOUNDER_PARAGRAPH}}  
I know people need it because the table already exists in every initiation note. It is built by hand, and it is wrong when the analyst changes.

**Competitors. What do you understand that they don’t?**  
Marvin Labs and FinCatch score guidance against results for US companies. Indian products (Screener, Trendlyne, Tijori) stop at reported numbers or sentiment. A chat product will answer this question in prose and still miss the earlier year’s guided range. The thing that matters is a row someone accepted, with the period and the metric fixed, that a desk can cite next year. That row is Indian, and it is slow to create. We are spending the company on creating it.

**How do you make money? How much could you make?**  
Seats plus a license. A 10-analyst desk is about ₹4.5 lakh a year. I would rather have 30 desks and 3 licenses than 3,000 light users. Three licenses at the low end of the list price are about ₹75 lakh a year, before seats. We are at zero. I am not going to give you a year-five number.

**Other ideas.**  
{{One or two real ideas you almost built, or “none.” YC reads this. A blank is fine. A fake idea is not.}}

**Incubators.**  
{{None. Or name Antler / Surge / anyone you have signed. If you only plan to apply, say “applying in parallel, nothing signed.”}}

**Legal entities.**  
Ocotillo Innovation Private Limited, India, incorporated {{INCORPORATION_DATE}}. No US entity yet. Willing to form the parent YC invests in, with the Indian company as the operating subsidiary.

**Equity.**  
{{EQUITY_SPLIT}}. Option pool: {{size, or “none yet”}}. Anyone else promised shares: {{no, or who}}.

**Investment so far.**  
{{PRIOR_CAPITAL}}. Include the instrument.

**Who writes code?**  
{{Name}}. {{“All of the product code is mine” or the true exception.}}

**How long have the founders known each other?**  
{{If sole: “I am the only founder.” If not: the truth, including whether you have met in person.}}

**What convinced you to apply?**  
The product is built and the users are not. YC is the shortest path I know to fifteen honest desk conversations and to a parent company US funds will follow. {{Name anyone who told you to apply, or say nobody did.}}

**Coding-agent transcript, if the form still asks.**  
Export one real session where you shipped a scoring or citation change. Do not export a session that contains secrets, customer data, or the demo API key. Optional. A proud session beats a polished one.

## Interview, ten minutes

They will interrupt. Practice being interrupted.

- Open on the Infosys row. You should be able to explain one year without looking.
- “Who is the user?” An analyst writing a note. Not “fintech.”
- “Why will they pay?” The table takes hours and is not reusable. ₹45,000 is inside a research budget. We have not proven they will switch. The pilot is the test.
- “Why are you the one?” Founder paragraph. Three sentences. Then stop defending it.
- “What’s the moat?” Accepted rows. Say how many you can stand behind today, the real count from the product, not a round number from memory. If you do not know it the night before, look it up on the site’s own coverage figures.
- “Regulatory?” Not advice. Not retail. Lawyer is in the budget. You will not pretend the memo is done.
- “Flip?” Yes.

## Parent company, only after a yes

YC’s published position: they invest in US, Canada, Cayman, and Singapore corporations. The Indian company usually becomes a subsidiary. IP can sit in either place; that is a lawyer’s recommendation, not a slide. Cost and tax are why you wait for their introduction rather than flipping speculatively this week. Do not flip before acceptance just to “look ready.”

## Do not

- Miss 2 November 2026 if you want the December decision date.
- Put a co-founder on the form who is not committed.
- Claim revenue, LOIs, or “in talks with HDFC” unless a named person at that firm has replied in writing. A call list is not traction.
- Say “world’s first.”
- Attach the family-office memo or the angel hockey stick. There isn’t one. Don’t make one tonight.
