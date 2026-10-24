# Facts you may say (21 October 2026)

Source of truth for every deck in this folder. Illustrative prices are list prices from `docs/customer/PRICING.md`. They are not revenue.

## Identity

- **Product:** CiteAlpha. **Index:** Guidance Credibility Index (GCI), 0–100.
- **Legal entity:** Ocotillo Innovation Private Limited.
- **Site:** https://citealpha.com. **Sales:** sales@citealpha.com.
- **One sentence:** CiteAlpha scores whether the management of an Indian listed company delivered on quantified guidance, and attaches the filing that set the number and the filing that reported the result.
- **Buyer:** PMS, AIF, sell-side research, emerging-market quant desks.
- **Beachhead:** Sensex, then Nifty. Export later by API.

## What a score is

A published point has a guidance statement and a later actual. Each has its own date, metric, and source. Outcome labels are met, exceeded, missed, dropped, or pending. A row without the guidance citation is excluded. The company carries a confidence tier. The public changelog records why a published number moved.

Worked example you can show: https://citealpha.com/companies/infy

## What is live

- GCI Screener, company dossier, Analyst Workbench, Filing Search, Disclosure Explorer, public snapshot, Trust Center, methodology, changelog.
- REST API and org seats.
- Production hosting on AWS.
- The extract client can call Gemini or an OpenAI-compatible model. Production hosting is AWS. Do not tell Google or Accel that the estate already runs on Google Cloud.

## Coverage, said precisely

- Indian listed companies. Sensex is the scored universe. Nifty 50 is in progress.
- Public labeling target: Sensex 30 and Nifty 50 at established depth by **31 March 2027**. That date is a capacity target. It slips if analyst time is less than full-time.
- Many Sensex names are still shallow (one or two closed outcomes). Say that if asked. Do not say “full history on every Sensex name.”
- Extraction is a prototype. A human accepts the quote before it can score. Do not quote a precision percentage.

## Commercial

| Plan | List price | Status |
|---|---|---|
| Pilot | Complimentary, 30–60 days, up to 5 seats | Offered |
| Desk | ₹45,000 per seat per year | Illustrative |
| Enterprise API | ₹25–80 lakh per year | Illustrative |
| Single-contract stack | ₹40 lakh–₹1.2 crore per year | Illustrative, only if they ask for one vendor |

Year-1 plan in the business plan: 15–20 design-partner desks, convert some to paid seats, sign one or two API licenses. That is a plan, not a pipeline.

## Stage

- Pre-revenue. No customer count, no ARR, no waitlist size is on file. Leave those fields blank or write “pre-revenue.”
- No prior institutional round is recorded in this repo. If you have raised from friends, write the real number. If you have not, write “none.”

## Competition, for investors only

- **Marvin Labs** and **FinCatch** already score guidance versus results on US filings.
- **Tijori** structures Indian filing metrics. It does not publish this index.
- Screener.in, Trendlyne, Tickertape, and StockEdge are fundamentals or sentiment. Different product.
- Terminals (prices, consensus, transcripts) stay in the workflow. CiteAlpha is the delivery record next to them.
- Pitch line: India-localized guidance accountability. Never “world’s first.”

## Compliance

- Factual research product. No Buy / Hold / Sell.
- Retail signup and retail checkout stay off until a written SEBI Research Analyst memo says otherwise.
- Do not write “SEBI registered,” “SEBI cleared,” or “compliant with RA regulations.” Write: counsel review is in the use of funds; the product is sold to desks.

## Category proof you may cite

- The category exists in the US (Marvin, FinCatch).
- Indian institutional research spend is the beachhead. Global alternative-data market sizes in the business plan are directional (~$5–19B global; India alt-data often cited around a few hundred million dollars growing toward a few billion). If a partner asks for a source, open `docs/BUSINESS_PLAN.md` and say the figures are directional, not a commissioned TAM study.
- A funded India filings company (Tijori, Series A reported publicly around $9 million in 2025) shows that Indian disclosure data can raise capital. They are not this product.

## Two-minute talk track

> Equity desks still carry management guidance in memory. A miss three years ago does not show up in this quarter’s note. US products already score whether management hit the number. Indian filings, exchange formats, and mixed-language calls are not their book.
>
> CiteAlpha is that book for India. We take the quantified promise, match the later actual, and publish a 0–100 Guidance Credibility Index. Both filings sit on the point. The site is live. We are pre-revenue. The round pays for the labeling bench that gets Sensex and Nifty 50 to established depth, and for the first twenty desk pilots. Seats are forty-five thousand rupees a year. A data license is twenty-five to eighty lakh. We do not sell tips.

## Founder paragraph — write this yourself

Surge, Atoms, Antler, and YC fund the founder. Leave this blank in the file until it is true. Three or four sentences:

1. Years and the desk, company, or market you actually worked in.
2. The specific moment a guidance number was remembered wrong, or could not be cited.
3. How long you have been full-time on CiteAlpha.
4. Who writes the code. If a contractor wrote part of it, say so.

`{{FOUNDER_PARAGRAPH}}`

## Demo, twelve minutes

1. Open https://citealpha.com. Read the one-line definition on the home page.
2. Open Infosys: https://citealpha.com/companies/infy. Show one year: guided band, reported actual, two links.
3. Open the screener. Show the confidence tier next to a score. If a cell is a dash, say the history is not citeable yet.
4. Open https://citealpha.com/changelog. A published number has a reason when it moves.
5. Open Filing Search or Disclosure Explorer only if they ask about the analyst workflow. Stop if the answer would not have a citation.
6. Close on the pilot: five seats, Sensex, thirty to sixty days, no fee.

Login for a private demo, if you grant one: do not put the demo API key in a deck or an email.

## Attach with every equity process

- This deck, as PDF or a Google Slides link that is open to anyone with the link.
- https://citealpha.com and the Infosys dossier.
- Certificate of incorporation, PAN, GST, bank letter — when they ask, not in the first email.
- Cap table.
- A one-page methodology pointer: https://citealpha.com/methodology (or the in-product methodology page if the path differs; the public methodology is linked from the site footer).
