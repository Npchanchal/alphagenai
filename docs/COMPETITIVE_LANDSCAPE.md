# Competitive Landscape — Products on the Path to GCI

Products already shipping pieces of the journey toward a **Guidance Credibility Index** (management promises vs delivery). CiteAlpha whitespace: **India-first** guidance accountability scoring.

## Closest (already do “promises vs delivery”)

| Product | What they implemented | Gap vs CiteAlpha |
|---|---|---|
| [Marvin Labs](https://www.marvin-labs.com/features/guidance-tracking/) | Full **Guidance Tracking**: extract forward-looking statements → restatement history → score met / missed / exceeded / dropped → management accuracy & discipline scores | US/global coverage focus; not India NSE/BSE–native |
| FinCatch | Prior guidance graded significantly missed → exceeded vs actuals; trend over time | SEC/global transcripts; not India-first |

These are the nearest finished products to the GCI idea.

### Marvin Labs (detail)

- Captures official + informal forward-looking statements (filings, calls, PR, investor days, Q&A).
- Threads restatements of the same commitment over time.
- When the period closes: labels met / exceeded / missed / dropped.
- Rolls up into company-level accuracy scores; integrates with earnings-review agents.
- Also ships: AI Analyst Chat, Deep Research Agents, daily sentiment 0–100.
- Positioning: primary-source workflow for institutional analysts (complements a terminal; not real-time quotes/consensus).

### FinCatch (detail)

- Compares guided figures against actuals.
- Outcome categories: significantly missed / missed / met / exceeded / significantly exceeded.
- Explicit use case: size positions more aggressively when management has a strong hit rate (e.g. met/exceeded EPS in 11 of last 12 quarters).

---

## Same road, different mile marker

| Product | Piece they built | How it helps the path |
|---|---|---|
| **Tijori Finance** | Filings-derived alternative metrics; powers Zerodha Console “Stock Insights” | India evidence spine; funded proof (~$9.28M Series A, Nov 2025) |
| **AlphaSense** (+ Sentieo, Tegus) | Search + AI research + expert transcripts (Tegus was >$100M ARR pre-acquisition) | Enterprise research copilot; could add guidance later |
| **Bloomberg / FactSet / LSEG / S&P Capital IQ** | Estimates, transcripts, terminals | Consensus & market data — not a management credibility *index* |
| **Trendlyne StratQ** | Scores, estimates, India retail/pro tools | Sentiment/estimates layer, not accountability scoring |
| **Screener.in / Tickertape / StockEdge / Finology / Trade Brains** | Fundamentals + screens | Ratios/history; no guidance-vs-actual engine |

---

## CiteAlpha / AlphaHunter assets (own stepping stones)

| Asset | Role on the path |
|---|---|
| **AlphaHunter Excel spine** | Facts + `guidance_change` / actuals tables (Sensex-30 research ops) |
| **CiteAlpha Wordmap v20** | Sentiment, notes, evidence UI, Accept/Edit/Reject feedback loop |
| **GCI MVP (this repo)** | Score + evidence-trail calculator (seed/demo data today) |

---

## Maturity map

```text
Filings/data  →  Sentiment/notes  →  Guidance extract  →  Match vs actuals  →  Credibility score
   Tijori           Trendlyne           Marvin              Marvin/FinCatch       Marvin (US)
   Screener         Wordmap v20         (not India yet)     (not India yet)       ← CiteAlpha GCI target
   AlphaSense       AlphaSense
```

| Stage | Global leaders | India today |
|---|---|---|
| 1. Structured filings / alt metrics | Many | Tijori, Screener |
| 2. Sentiment / AI research notes | AlphaSense, Marvin, Trendlyne | Trendlyne, Wordmap v20 |
| 3. Guidance extraction | Marvin, FinCatch | **Whitespace** |
| 4. Guidance vs actual matching | Marvin, FinCatch | **Whitespace** |
| 5. Longitudinal credibility index | Marvin (US) | **CiteAlpha target** |

---

## Strategic read

- **Globally:** Marvin Labs (and FinCatch) already implemented the destination category.
- **In India:** Tijori + research UIs are on the road but stop before a scored guidance-accountability index.
- **Pitch correctly:** “India-localized guidance tracking,” not “world’s first.”
- **Do not compete first on:** generic sentiment dashboards or Buy/Hold generators (red ocean + SEBI sensitivity).

## Related docs

- [Business plan](BUSINESS_PLAN.md)
- [Product definition](PRODUCT_DEFINITION.md)
- [Regional markets](REGIONAL_MARKETS.md)
- [Accuracy assessment](ACCURACY_ASSESSMENT.md)
- [Whitespace implementation plan](PLAN_WHITESPACE.md)
