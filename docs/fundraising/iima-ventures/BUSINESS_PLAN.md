# CiteAlpha — business plan for IIMA Ventures

**Prepared for:** IIMA Ventures incubation review  
**Date:** 23 October 2026  
**Entity:** Ocotillo Innovation Private Limited  
**Product:** CiteAlpha · Guidance Credibility Index (GCI)  
**Site:** https://citealpha.com  
**Company email:** sales@citealpha.com  
**Attachment:** [docs/PITCH_DECK.pptx](../../PITCH_DECK.pptx) (same narrative in [PITCH_DECK.html](../../PITCH_DECK.html))

Fill every `{{blank}}` before you submit. IIMA Ventures evaluates team quality first. A blank founder paragraph is a weaker application.

This plan is for incubation: business model, risks, and the help we want. It is not an equity pitch. List prices are from the customer pack. They are not revenue. The company is pre-revenue.

---

## Form answers

**1. Primary company email, for tool access**  
sales@citealpha.com

**2. Tools required, and use so far**

| Cloud | Role | Use so far |
|---|---|---|
| AWS | Production host, `ap-south-1` | In use. One ECS Fargate task (ARM64, 0.5 vCPU, 1 GB), load balancer, Route 53, certificate, CloudWatch, Secrets Manager, EFS, container registry. About **$40 a month** on a list-price inventory dated 28 September 2026, down from about $49 a month before the move to ARM64. Over seven days then: memory peaked near 15% of 1 GB, CPU averaged 2.8% with short spikes near 88%, and the load balancer saw roughly 1,500–15,000 requests a day. |
| Google (Gemini API) | Quote extraction, scored against reviewer-accepted quotes | The client can call Gemini. There is no Google Cloud project bill on file. A credits grant, if offered, pays for a pinned-model evaluation on filings we already store. It does not move a published score. |
| Azure | — | Not used. |

**3. Pitch deck**  
`docs/PITCH_DECK.pptx`, attached with this plan. Twelve-minute demo if they ask: home page, [Infosys dossier](https://citealpha.com/companies/infy), screener with the confidence tier, [changelog](https://citealpha.com/changelog).

---

## 1. The company

CiteAlpha scores whether the management of an Indian listed company delivered on quantified guidance, and attaches the filing that set the number and the filing that reported the result.

A published point is 0–100. It has a guidance statement and a later actual. Each has its own date, metric, and source. Outcome labels are met, exceeded, missed, dropped, or pending. A row without the guidance citation is excluded. The company carries a confidence tier. When a published number moves, the public changelog records why.

Worked example: https://citealpha.com/companies/infy

The buyer is a PMS, an AIF, a sell-side research desk, or an emerging-market quant desk. The beachhead is Sensex, then Nifty. Export is an API, after the India book is deep enough to license.

Stage: product live, pre-revenue, {{PRIOR_CAPITAL: “none” if no institutional round}}. Incorporated {{INCORPORATION_DATE}}. CIN {{CIN}}.

---

## 2. The problem, and who pays

An equity desk still carries management guidance in memory. A miss three years ago does not show up in this quarter’s note. The promise and the later actual sit in two filings, often a year apart, sometimes in a mixed-language call.

US products already score whether management hit the number. Indian exchange formats and those calls are not their book. Indian terminals and screeners cover prices, fundamentals, or tone. They do not publish this delivery record.

The person who pays is the research head who has to put a citation in a note, or the quant desk that wants the same history as a file. The retail reader is not the customer. Signup for retail stays off until a written SEBI Research Analyst memo says otherwise. We do not sell Buy, Hold, or Sell.

---

## 3. What is live

- GCI Screener, company dossier, Analyst Workbench, Filing Search, Disclosure Explorer, public snapshot, Trust Center, methodology, changelog.
- REST API and organisation seats.
- Production hosting on AWS.
- A model may propose the guidance sentence and the later actual. A reviewer accepts both. The score is computed from accepted rows.

Coverage, said precisely: Indian listed companies. Sensex is the scored universe. Nifty 50 is in progress. Many Sensex names are still shallow (one or two closed outcomes). The public labeling target is Sensex 30 and Nifty 50 at established depth by **31 March 2027**. That date is a capacity target. It slips if analyst time is less than full-time. Extraction is a prototype. A human accepts the quote before it can score. We do not quote a precision percentage.

---

## 4. Opportunity

The market figures in the internal business plan are directional, not a commissioned study: global alternative data on the order of $5–19 billion, and India alternative data often cited around a few hundred million dollars growing toward a few billion. We do not underwrite the company on those ranges.

The buyer list we can name is the SEBI register, as published on 22 October 2026 ([recognised intermediaries](https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognised=yes&intmId=15)):

| Register | Count |
|---|---|
| Portfolio managers | 542 |
| Alternative investment funds | 2,045 |
| Research analysts | 2,304 |
| Mutual funds | 61 |

Year one does not call that list. The plan is **15–20 design-partner desks**. That is a founder-time limit, not a market-size limit. A funded India filings company (Tijori, Series A reported publicly around $9 million in 2025) shows that Indian disclosure data can raise capital. They structure filing metrics. They do not publish this index.

PMS assets are large and mostly not our book. SEBI’s report for 31 August 2026 shows discretionary listed-equity assets inside a much larger debt and retirement total. We sell a research seat and a data license. We do not manage money, and we do not quote that AUM as our market.

---

## 5. Business model

Four offers. Prices are illustrative, exclusive of GST, and quoted on an order form. Nothing below is booked.

| Offer | Who it is for | Price | Status |
|---|---|---|---|
| Pilot | One desk, up to 5 seats, Sensex, 30–60 days | Complimentary | Offered |
| Desk | Research team, annual prepaid | ₹45,000 per seat per year | List price |
| Enterprise API | Quant or platform embed, history and redistribution set in the contract | ₹25–80 lakh per year | List price |
| Single contract | A desk that wants one vendor for the stack | ₹40 lakh–₹1.2 crore per year | Only if they ask |

A small desk at five seats is **₹2.25 lakh a year**. An eight-seat team is **₹3.6 lakh**. One API license at the floor of the range is **₹25 lakh**, about ten small desks. Seats are how a research head builds a weekly habit. The license is how the company becomes a business. We will not hide that in a seat-count slide.

**Planning case for the twelve months after pilots start.** This is arithmetic on the list prices. It is not a pipeline.

| Line | Assumption | Amount |
|---|---|---|
| Pilots opened | 18 desks | ₹0 |
| Paid conversion | 6 desks, one-third of 18, 5 seats each | ₹13.5 lakh |
| API | 1 license at the floor | ₹25 lakh |
| Planning total | | **₹38.5 lakh** |

If week-four use is weak, conversion is zero and the total is zero. Hosting does not depend on that outcome. The live AWS stack is about $40 a month. The production configuration for all markets and paying desks is about $354 a month, and the three environments together are about $536 a month, set out in section 8.4. The company mailbox and product email are about $22 a month, section 8.5. The large costs are reviewer time and a securities-counsel memo. Model calls for the filing history from 2022 are in section 8. On the production reader they are a small fraction of one desk seat. {{MONTHLY_BURN}} goes here once it is taken from the bank, even if the burn is personal savings.

Gross margin on a delivered seat is high once the row exists. The investment is the row: a human-accepted guidance quote, a human-accepted actual, period and metric fixed, source on both sides. That history is what a second desk cannot download from a screener.

Year-1 commercial plan, repeated so the arithmetic stays tied to it: 15–20 design-partner desks, convert some to paid seats, sign one or two API licenses.

---

## 6. Eighteen months

| When | Milestone | How we will know |
|---|---|---|
| Now | Live product, shallow history on many Sensex names | Public dossier and changelog |
| Through 31 March 2027 | Sensex 30, then Nifty 50, at established depth | Confidence tier on the name, both citations on every scored row |
| Same window | 15–20 pilots, founder-led | A named desk, five seats, a start date |
| Day 60 of a pilot | Habit test | At least three analysts still opening it weekly, and one note that cites a filing from the dossier |
| After the habit test | Paid seats at ₹45,000 | An order form, not a verbal yes |
| Inside the year | One or two API conversations | A written scope: history depth and redistribution |

A seller is hired after three desks are in a pilot. Before that, the founder sells.

---

## 7. Why a desk stays

Marvin Labs and FinCatch already score guidance versus results on US filings. That is category proof, and it is their book. Tijori structures Indian filing metrics. Screener.in, Trendlyne, Tickertape, and StockEdge are fundamentals or tone. Terminals keep prices, consensus, and transcripts. CiteAlpha is the delivery record next to them.

The part that takes time is the accepted Indian row. A model can propose a span. It does not publish. A reviewer does. A disagreement does not change a published score. Copying the screen is easier than copying five years of accepted pairs.

---

## 8. Technology and cost, filings from 2022

Production stays on AWS in `ap-south-1`. The audited footprint is one environment, about $40 a month. Development today runs on a laptop, and there is no separate testing stack. Section 8.4 is the cost of running development, testing, and production on AWS so the filing work from 2022 can be built, checked, and published without sharing one database. There is no second region and no Azure estate. The same Word file as this plan is [CiteAlpha_IIMA_Ventures_Business_Plan.docx](CiteAlpha_IIMA_Ventures_Business_Plan.docx).

The history the index is built on starts **1 January 2022**. The India walk is about 20,000 model calls for the Nifty 500. The global walk is about 14,000 calls for the S&P 500. Sensex 30 is about 1,200 calls and sits inside the Nifty 500 count. A stored filing is not sent again.

The tables below put those calls into the year the filing belongs to. The window is 1 January 2022 through 23 October 2026, 1,757 days. Each year’s calls are that year’s share of the days. 2026 is ten months. 2027 is a full year of new filings only. This is a planning split of the walk, not a count of calls already billed in 2022, 2023, 2024, or 2025.

### 8.1 Filings from 2022, by year

| Year | Days | Sensex 30 | Nifty 50 | India — Nifty 500 | Global — S&P 500 | India + global |
|---|---:|---:|---:|---:|---:|---:|
| 2022 | 365 | 250 | 416 | 4,155 | 2,909 | 7,064 |
| 2023 | 365 | 249 | 415 | 4,155 | 2,908 | 7,063 |
| 2024 | 366 | 250 | 417 | 4,166 | 2,916 | 7,082 |
| 2025 | 365 | 249 | 415 | 4,155 | 2,908 | 7,063 |
| 2026, to 23 Oct | 296 | 202 | 337 | 3,369 | 2,359 | 5,728 |
| **History, 2022–23 Oct 2026** | **1,757** | **1,200** | **2,000** | **20,000** | **14,000** | **34,000** |
| 2027, new filings only | 365 | 249 | 415 | 4,155 | 2,908 | 7,063 |

Sensex 30 and Nifty 50 are slices of the Nifty 500. They are not added on top of it.

### 8.2 What one call costs

Vendors publish one US-dollar rate card. A 2022 filing and a 2026 filing have the same token price. India costs more in a year only because that year has more Indian filings. Prices were read on 23 October 2026. Rupees use the FBIL rate of ₹94.9432 per dollar.

One read is 13,000 input tokens. The planning output is 1,500 tokens. Gemini bills low-reasoning tokens as output, so the Gemini case uses 3,500 output tokens. The reader cap is 8,192 output tokens. The ceiling for one pass of both books is in the rate table.

| Model | Input / 1M | Output / 1M | Where it sits |
|---|---:|---:|---|
| Gemini 3.8 Flash, Flex, through 31 Dec 2026 | $0.375 | $1.875 | Production reader |
| Gemini 3.8 Flash, Flex, from 1 Jan 2027 | $0.75 | $3.75 | Same reader, introductory price ends |
| Gemini 3.8 Flash, Standard, through 31 Dec 2026 | $0.75 | $3.75 | Full-speed tier |
| Claude Haiku 5.5 | $0.10 | $0.50 | Comparable Claude extract. Not wired in production |
| Claude Sonnet 5.5 | $2.00 | $10.00 | Second pass on a disputed span |
| Claude Opus 5.5 | $4.00 | $20.00 | Top of the Claude card |
| ChatGPT gpt-4.1-mini | $0.40 | $1.60 | The model the client uses when the call is not Gemini |
| ChatGPT gpt-4o-mini | $0.15 | $0.60 | Chat default when Gemini is off |
| ChatGPT gpt-5-mini | $0.25 | $2.00 | Current small ChatGPT API model |
| ChatGPT gpt-5.6-sol | $4.00 | $20.00 | Current flagship, short-context rate |

### 8.3 Cost of the 2022–2026 history, and of 2027

Planning case. Each cell is that year’s filings. The history row is one pass of everything since 1 January 2022. 2027 uses the post-introductory Gemini Flex price. Claude and ChatGPT stay on the rate card above.

**Google Gemini 3.8 Flash, Flex**

| Year | Sensex 30 | India — Nifty 500 | Global — S&P 500 | India + global |
|---|---:|---:|---:|---:|
| 2022 | $2.86 · ₹272 | $47.52 · ₹4,512 | $33.27 · ₹3,159 | $80.79 · ₹7,670 |
| 2023 | $2.85 · ₹271 | $47.52 · ₹4,512 | $33.26 · ₹3,158 | $80.78 · ₹7,670 |
| 2024 | $2.86 · ₹272 | $47.65 · ₹4,524 | $33.35 · ₹3,166 | $81.00 · ₹7,690 |
| 2025 | $2.85 · ₹271 | $47.52 · ₹4,512 | $33.26 · ₹3,158 | $80.78 · ₹7,670 |
| 2026, to 23 Oct | $2.31 · ₹219 | $38.53 · ₹3,658 | $26.98 · ₹2,562 | $65.51 · ₹6,220 |
| **History** | **$13.72 · ₹1,303** | **$229 · ₹21,718** | **$160 · ₹15,203** | **$389 · ₹36,921** |
| 2027, new filings, new price | $5.70 · ₹541 | $95.05 · ₹9,024 | $66.52 · ₹6,316 | $161.57 · ₹15,340 |

**Anthropic Claude Haiku 5.5**

| Year | Sensex 30 | India — Nifty 500 | Global — S&P 500 | India + global |
|---|---:|---:|---:|---:|
| 2022 | $0.51 · ₹48 | $8.52 · ₹809 | $5.96 · ₹566 | $14.48 · ₹1,375 |
| 2023 | $0.51 · ₹48 | $8.52 · ₹809 | $5.96 · ₹566 | $14.48 · ₹1,375 |
| 2024 | $0.51 · ₹48 | $8.54 · ₹811 | $5.98 · ₹568 | $14.52 · ₹1,379 |
| 2025 | $0.51 · ₹48 | $8.52 · ₹809 | $5.96 · ₹566 | $14.48 · ₹1,375 |
| 2026, to 23 Oct | $0.41 · ₹39 | $6.91 · ₹656 | $4.84 · ₹460 | $11.74 · ₹1,115 |
| **History** | **$2.46 · ₹234** | **$41.00 · ₹3,893** | **$28.70 · ₹2,725** | **$69.70 · ₹6,618** |
| 2027, new filings | $0.51 · ₹48 | $8.52 · ₹809 | $5.96 · ₹566 | $14.48 · ₹1,375 |

**OpenAI ChatGPT — gpt-4.1-mini**

| Year | Sensex 30 | India — Nifty 500 | Global — S&P 500 | India + global |
|---|---:|---:|---:|---:|
| 2022 | $1.90 · ₹180 | $31.58 · ₹2,998 | $22.11 · ₹2,099 | $53.69 · ₹5,098 |
| 2023 | $1.89 · ₹179 | $31.58 · ₹2,998 | $22.10 · ₹2,098 | $53.68 · ₹5,097 |
| 2024 | $1.90 · ₹180 | $31.66 · ₹3,006 | $22.16 · ₹2,104 | $53.82 · ₹5,110 |
| 2025 | $1.89 · ₹179 | $31.58 · ₹2,998 | $22.10 · ₹2,098 | $53.68 · ₹5,097 |
| 2026, to 23 Oct | $1.54 · ₹146 | $25.60 · ₹2,431 | $17.93 · ₹1,702 | $43.53 · ₹4,133 |
| **History** | **$9.12 · ₹866** | **$152 · ₹14,431** | **$106 · ₹10,102** | **$258 · ₹24,533** |
| 2027, new filings | $1.89 · ₹179 | $31.58 · ₹2,998 | $22.10 · ₹2,098 | $53.68 · ₹5,097 |

**OpenAI ChatGPT — gpt-5-mini**

| Year | Sensex 30 | India — Nifty 500 | Global — S&P 500 | India + global |
|---|---:|---:|---:|---:|
| 2022 | $1.56 · ₹148 | $25.97 · ₹2,466 | $18.18 · ₹1,726 | $44.15 · ₹4,192 |
| 2023 | $1.56 · ₹148 | $25.97 · ₹2,466 | $18.18 · ₹1,726 | $44.14 · ₹4,191 |
| 2024 | $1.56 · ₹148 | $26.04 · ₹2,472 | $18.23 · ₹1,731 | $44.26 · ₹4,202 |
| 2025 | $1.56 · ₹148 | $25.97 · ₹2,466 | $18.18 · ₹1,726 | $44.14 · ₹4,191 |
| 2026, to 23 Oct | $1.26 · ₹120 | $21.06 · ₹2,000 | $14.74 · ₹1,399 | $35.80 · ₹3,399 |
| **History** | **$7.50 · ₹712** | **$125 · ₹11,868** | **$87.50 · ₹8,308** | **$213 · ₹20,175** |
| 2027, new filings | $1.56 · ₹148 | $25.97 · ₹2,466 | $18.18 · ₹1,726 | $44.14 · ₹4,191 |

A second pass of the whole 2022–2026 history on a flagship, at the 8,192-token cap, is about $7,300 · ₹7.0 lakh on Claude Opus 5.5 or ChatGPT gpt-5.6-sol, and about $3,700 · ₹3.5 lakh on Claude Sonnet 5.5. That is the top of the card. It is not the production path.

### 8.4 AWS for development, testing, and production

The model bills in section 8.3 are paid to Google, Anthropic, or OpenAI. They are not on the AWS invoice. AWS is the host: the site, the filing store, and the job that sends those calls. The September 2026 inventory is one production stack in `ap-south-1`. Cost Explorer was not enabled for that audit, so the $40 is a list-price total of the live resources, not an exported invoice.

| Piece of the live stack | About USD / month |
|---|---:|
| ECS Fargate, 1 task, ARM64, 0.5 vCPU, 1 GB | 10.60 |
| Application load balancer | 17.45 |
| Public IPv4 (load balancer and the task) | 10.95 |
| Route 53 zone for citealpha.com | 0.50 |
| Secrets Manager, CloudWatch, EFS, container registry | 0.88 |
| **Production, as audited** | **40** |

CPU on that task averaged 2.8% over the sample week, with short spikes near 88%. Memory peaked near 15% of 1 GB. One pass of the 2022–2026 history is about 34,000 calls and a few hours of work. Filing text for that pass is about 1.5 GB. The current task can run that pass. It is the wrong shape once desks are on the site and both markets refresh every day.

The production configuration below is sized for that operating load. Fifteen to twenty desks, then about thirty named seats and one API, are tens of people on the site, not thousands. The India walk and the S&P 500 walk already run side by side. A third 500-name market, run at the same time, adds one more worker of the same size, about $42.41 a month, $509 a year, ₹48,318. The site tasks do not change for that market.

What changes from the $40 stack, and why:

- Two site tasks, each 1 vCPU and 2 GB, so a task restart does not take the site down and a scoring spike does not sit on the only CPU.
- One worker, 2 vCPU and 4 GB, so the daily walks are not on the same task as the desks.
- PostgreSQL on RDS, Multi-AZ, with one read replica. Two tasks cannot share the single file the live stack uses for accounts. The replica takes API reads off the primary while a walk is writing.
- Tasks on private addresses, with a NAT gateway in each of two zones, so a zone failure does not also remove the way out to the model APIs.
- A web application firewall on the load balancer.
- 50 GB of file storage for the filing text of both books, and 50 GB of database storage on the primary and on the replica.

List prices, 730 hours a month. Fargate ARM64 in Mumbai is the rate already used for the live task, $0.02383 per vCPU-hour and $0.00261 per GB-hour. RDS PostgreSQL `db.t4g.small` is $0.042 an hour single-AZ and $0.084 Multi-AZ, as published for Mumbai on 19 October 2026. NAT is $0.056 an hour in Mumbai, and $0.056 per GB processed. Public IPv4 is $0.005 an hour. gp3 storage is $0.115 per GB-month single-AZ and $0.230 Multi-AZ. EFS Standard in Mumbai is $0.330 per GB-month. The load balancer figure is the audited base. WAF is $5 for one list plus $1 for each of five rules.

| Production line | USD / month |
|---|---:|
| Site, 2 tasks, 1 vCPU, 2 GB each | 42.41 |
| Walk worker, 1 task, 2 vCPU, 4 GB | 42.41 |
| RDS PostgreSQL, Multi-AZ, db.t4g.small | 61.32 |
| Read replica, single-AZ, same size | 30.66 |
| Database storage, 50 GB on the primary pair and 50 GB on the replica | 17.25 |
| NAT gateways, two zones | 81.76 |
| NAT data, about 20 GB | 1.12 |
| Public IPv4, load balancer and both NAT gateways | 14.60 |
| Application load balancer | 17.45 |
| Web application firewall | 10.00 |
| Filing store, 50 GB | 16.50 |
| DNS, secrets, logs, image registry | 18.10 |
| **Production for markets and customers** | **353.58** |

That is $4,243 a year, ₹4,02,840. It is a planning configuration. It is not what the account is running today.

Testing is a single-zone copy used to rehearse a release: one site task, one small worker, one single-AZ database, one NAT gateway, and its own load balancer. About $143 a month, $1,715 a year, ₹1,62,820. Development stays on the audited small stack, $40 a month, so a sample walk has somewhere to run that is not production. The DNS zone and the image registry stay shared.

| Environment | USD / month | USD / year | Rupees / year |
|---|---:|---:|---:|
| Production, markets and customers | 353.58 | 4,243 | ₹4,02,840 |
| Testing, single zone | 142.91 | 1,715 | ₹1,62,820 |
| Development, audited small stack | 40 | 480 | ₹45,573 |
| **All three** | **536.49** | **6,438** | **₹6,11,233** |

Rupees use ₹94.9432 per dollar.

| Work | Model, Gemini Flex, India + S&P 500 | AWS | Other tools (section 8.5) | Together |
|---|---:|---:|---:|---:|
| Read filings from 2022 through 23 Oct 2026, once | $389 · ₹36,921 | The current task can do this pass, $40 · ₹3,798 | Subscriptions, not a per-filing charge | $429 · ₹40,719 |
| One operating year at 2026 prices | $81 · ₹7,690 | $6,438 · ₹6,11,233 | $258.48 · ₹24,541 | $6,777.48 · ₹6,43,464 |
| 2027 operating year | $161.57 · ₹15,340 | $6,438 · ₹6,11,233 | $258.48 · ₹24,541 | $6,858.05 · ₹6,51,114 |

Running the full history again in development and again in testing multiplies the model column, not the AWS column. The plan is one production pass of 2022–2026, and a 50-filing sample in development and testing.

### 8.5 Other tools, licenses, and subscriptions

The product sends email. It does not send SMS, voice, or WhatsApp, so Twilio’s messaging products are not a line in this plan. Slack and Teams delivery posts to the customer’s own webhook. SSO uses the customer’s identity provider. The database, the web framework, and the certificate are open source or included with AWS. None of those is a separate license.

Two email products are different jobs. Hostinger is the company mailbox: citealpha.com mail already points there, and `sales@citealpha.com` is the address on this application. SendGrid is the application mailer: verify, password reset, invite, weekly digest, and monitor notes. The mailer speaks SMTP. It is not pointed at a host in production today, so these are list prices for the tool we would turn on, not an invoice we have paid.

A year of twenty desks, with a few digest recipients each, password mail, and monitor notes, is on the order of 10,000 messages. That sits inside SendGrid Essentials at 50,000 messages a month. The Hostinger Starter mailbox allows on the order of 1,000 messages a day for a person at the inbox. It is the wrong pipe for the product mail.

| Tool | Job | Needed | List price | Year |
|---|---|---|---:|---:|
| Hostinger Business Email, Starter, 1 mailbox | `sales@citealpha.com` and company mail. Renewal rate, not the introductory sale. | Yes. DNS already points at Hostinger. | $1.59 / month | $19.08 · ₹1,812 |
| Twilio SendGrid Email API, Essentials, 50,000 messages | Product mail over SMTP | Yes, once the 60-day trial of 100 messages a day ends | $19.95 / month | $239.40 · ₹22,729 |
| Twilio SMS, voice, WhatsApp | Not a feature | No | US SMS list starts at $0.0083 a message. India is a different card. | $0 |
| Google Analytics 4 | Site measurement, named in the privacy notice | Optional. Free if turned on. | $0 | $0 |
| Plausible | Privacy-friendly measurement, also named in the notice | Optional. Not required to run the product. | From $9 / month | $108 · ₹10,254 if we turn it on |
| **Required, mailbox plus product mail** | | | **$21.54 / month** | **$258.48 · ₹24,541** |

Prices read on 23 October 2026 from Hostinger’s business-email page (Starter renewal $1.59 a mailbox a month), Twilio’s SendGrid Email API page (Essentials from $19.95 a month; the 50,000-message tier is $19.95), Twilio’s communications price card, and Plausible’s published Starter price. Rupees use ₹94.9432 per dollar. Plausible is left out of the required total. Adding it would take the year to $366.48 · ₹34,795.

AWS Simple Email Service can send the same product mail for about $0.10 per 1,000 messages, about $1 a year at this volume, because the mailer is plain SMTP. The table uses SendGrid so the email API is a named subscription. We would not pay both.

The project worth a credit grant is narrow: pin one Gemini version, run it on 50 filings already stored, and report span agreement, wrong-number rate, wrong-period rate, and cost per filing. That sample replaces the token allowance in these tables. Reviewers still accept every quote that can affect a score. Production data stays on AWS unless a later contract says otherwise.

---

## 9. Team

{{FOUNDER_NAME}}, {{CITY}}. {{PHONE}}. {{EMAIL}}. {{LINKEDIN}}.

{{FOUNDER_PARAGRAPH — four sentences: the desk or market you worked in; the specific guidance number that was remembered wrong or could not be cited; how long you have been full-time on CiteAlpha; who writes the code.}}

{{COFOUNDERS: “Sole founder” is an acceptable answer.}}  
Equity: {{EQUITY_SPLIT}}.  
Full-time: {{yes, or the true schedule}}.  
Other incubators or grants: {{list any signed program, or “none”}}.

---

## 10. Risks we want examined

| Risk | What is true now | What would change the plan |
|---|---|---|
| Habit | No paying desk | Ten pilots with no week-four use means the commercial plan is wrong. We stop selling seats and revisit the workflow before hiring. |
| Depth | Many Sensex names have one or two closed outcomes | A desk that needs a full history will not convert. The March 2027 target is the response. It moves if reviewer time is part-time. |
| Extraction | Prototype. No precision percentage | A model proposes. A person accepts. We will not publish from model output alone to look more complete. |
| Regulation | Factual product, sold to desks. Counsel review is open | We will not write “SEBI registered” or “SEBI cleared.” Retail stays off until a written memo. |
| Copying | The screen is describable | The accepted history is the asset. We spend time on history. |
| Concentration | One API license dominates the planning case | Two small licenses, or more seats, matter more than a single ₹80 lakh hope. The floor case is ₹25 lakh and is still only a plan. |

---

## 11. What we are asking IIMA Ventures for

Incubation support, on the terms of the programme we are applying to. We are not asking IIMA Ventures to value the company, to endorse an index level, or to introduce us as a recommendation engine.

1. A mentor who has bought or produced institutional equity research, and who will attack the seat price, the pilot length, and the week-four test.
2. Introductions to research heads or PMS investment offices in the alumni network. We will send the pilot terms ourselves. Five serious conversations beat a long list.
3. One working session on the SEBI Research Analyst boundary, with someone who has advised a research product. The memo itself is paid counsel, not a classroom conclusion.
4. If the cohort includes partner cloud credits, Gemini capacity for the 50-filing evaluation in section 8. Production hosting remains AWS.
5. Introductions to investors only after three pilots show week-four use. A deck before that habit is a different meeting, and it is not this application.

If the programme offers a grant, the grant pays reviewer time toward the March 2027 coverage target and the counsel memo. It does not pay advertising.

---

## 12. What we will report

A one-page monthly note: names deepened, pilots opened, pilots still in use in week four, cash left. No customer logos of firms that have not replied. No change to a published score without a changelog row.

---

## Demo, if there is a room

1. https://citealpha.com — one-line definition.
2. https://citealpha.com/companies/infy — one year, guided band, reported actual, two links.
3. Screener — confidence tier beside the number. A dash means the history is not citeable yet.
4. https://citealpha.com/changelog — a published number has a reason when it moves.
5. Close on the pilot: five seats, Sensex, thirty to sixty days, no fee.

Do not put an API key in this document or in the application email.
