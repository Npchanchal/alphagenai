# Gaps vs AlphaSense & Bloomberg — CiteAlpha (AlphaGenAI)

Sources: [AlphaSense](https://www.alpha-sense.com/), Bloomberg Asia / Terminal franchise, CiteAlpha product as of Research Terminal + GCI MVP.

**Rule:** Do not try to “become AlphaSense” or “become Bloomberg.” Close only gaps that strengthen **India guidance accountability** or adjacent research workflows buyers already ask for.

---

## Positioning snapshot

| | [AlphaSense](https://www.alpha-sense.com/) | Bloomberg (Asia site + Terminal) | **CiteAlpha** |
|---|---|---|---|
| Core job | AI market intelligence search + workflows over premium content | News (B2C Asia) + institutional market data / terminal (B2B) | **GCI** — management guidance vs delivery + evidence |
| Buyer | IB, HF, PE, AM, corporates, consulting | Consumers (news) + institutions (Terminal/data) | India buy-side / sell-side / EM API |
| Content scale | 500M+ docs, Tegus experts, broker research, internal content | Global news, quotes, estimates, economics | Sensex-30 seed; hand-labeled cohort partial |
| AI | Deep Research, GenAI with sentence-level citations | Terminal analytics + **ASKB** agentic AI (beta) | Cite-only chat + GCI over India IR corpus |
| Moat today | Content licensing + expert network + enterprise graph | Live data + Terminal network + news | **India GCI / labels / evidence** (whitespace) |

---

## B2B gaps (institutional)

### A. Where AlphaSense is ahead of CiteAlpha

| Gap | AlphaSense has | CiteAlpha today | Priority for us |
|---|---|---|---|
| **Content firehose** | Filings, broker research, 500M+ docs, partners | Small demo index + guidance corpus | High — ingest NSE/BSE filings + concalls at scale |
| **Expert network** | Tegus Expert Insights / live calls | Stub “expert” notes | Low — partner later; don’t rebuild Tegus |
| **Enterprise search quality** | Smart synonyms, ranking, firm internal content | Keyword demo search | High — vector + synonym search on India IR |
| **GenAI depth** | Deep Research, slide/Excel/PPT add-ins, anti-hallucination claims | Heuristic chat citing seed docs | Medium — LLM cite-only over *our* corpus |
| **Vertical solutions** | IB, HF, PE, AM, life sciences, energy… | One India equity research desk | Low — stay India equity GTM |
| **Trust / scale proof** | 7,000+ enterprises, case studies | Pilot packaging | Medium — 15–20 pilot desks |
| **Security / SSO / admin** | Enterprise Intelligence, Trust Center | API key demo | High before Desk convert |

### B. Where Bloomberg (Terminal / data) is ahead of CiteAlpha

| Gap | Bloomberg has | CiteAlpha today | Priority for us |
|---|---|---|---|
| **Live market data** | Quotes, depth, FX, rates | Demo tape only | **Don’t build** — integrate or “bring your terminal” |
| **Consensus estimates** | Street EE / broker mashup | Synthetic street vs real guidance | Medium — license or import consensus; keep GCI as differentiator |
| **News wire** | Global + Asia news franchise | Demo news/filings cards | Low — link-out or partner; not a newsroom |
| **Portfolio / OMS / analytics** | Full terminal workflow | None | **Don’t build** |
| **Asia macro / geopolitics desk** | Asia homepage themes, policy, markets | None | Low for MVP |
| **Distribution** | Ubiquitous on buyside desks | AWS demo IP / seats model | High — SSO, stable URL, procurement pack |

### C. Where CiteAlpha is ahead (defend / deepen)

| CiteAlpha advantage | AlphaSense | Bloomberg |
|---|---|---|
| **Scored guidance delivery (GCI 0–100)** | Not productized as India GCI | Not a management-credibility *index* |
| **Labels: met / exceeded / missed / dropped / pending** | Search/snippets, not longitudinal accountability score | Estimates ≠ management promise tracking |
| **Auditable evidence trail tied to score** | Citations in GenAI; different job | Data cells, not GCI |
| **India disclosure / IR-native beachhead** | Global content; India not the wedge | Global; India is one region |
| **SEBI-aware factual posture** | US-centric enterprise AI | News + terminal; different compliance story |

---

## B2C gaps (retail / consumer)

Bloomberg’s [Asia](https://www.bloomberg.com/asia) surface is largely **B2C news + engagement**; AlphaSense is **not B2C**.

| Gap | Bloomberg Asia / consumer | AlphaSense | CiteAlpha |
|---|---|---|---|
| Free/paid news site | Strong | N/A | None (by design) |
| Retail app / alerts | Brand + apps | N/A | Explicit non-goal in MVP |
| Social / newsletter funnel | Strong | Light (events/content marketing) | Weak |
| SEBI RA / advice risk | News editorial | N/A | **Must stay factual — no Buy/Hold retail** |

**B2C recommendation:** Do **not** chase Bloomberg Asia’s newsroom or a retail trading app. Optional later: vernacular **factual** GCI blurbs / broker badge (Year-2), still not advice.

---

## Gap map — what to close vs ignore

```text
CLOSE (builds moat)
  India filings/concall ingest → better Search
  LLM cite-only over labeled guidance corpus
  Full Sensex → Nifty hand labels
  SSO / VPC / stable customer URL
  Real consensus import (optional) next to GCI

COMPLEMENT (partner / integrate)
  Live quotes, deep news, Tegus-like experts
  Excel/PPT add-ins after desk habit exists

IGNORE (red ocean / wrong category)
  Replace AlphaSense content universe
  Replace Bloomberg Terminal
  B2C news portal or tip app
```

---

## Match / Differentiate / Refuse (AlphaSense inventory)

Rule: close only what strengthens **India guidance accountability**; never try to become a 500M-doc market-intel OS.

### Match (build or keep)

| AlphaSense thing | CiteAlpha posture |
|---|---|
| Sentence-level / source-linked citations | `cite_*`, quote, locator, copy, `/c/{id}` |
| Primary-source search (filings, transcripts) | Research Terminal over India IR corpus |
| Cite-only GenAI (no free-form invent) | Numbered cite-only chat; refuse if empty |
| Watchlists + company focus | Editable `preferences.watchlist` + Research watch + Tracker ★ |
| Enterprise SSO / admin / seats | OIDC path + Desk seats (needs live `OIDC_*`) |
| Security / Trust / Terms / Privacy | `/trust` Trust Center + `/terms` + `/privacy` |
| Pilot → paid packaging | Package / billing surfaces (PSP wiring is ops) |
| Pre-earnings / guidance prep | Promise brief — open promises + hit rate |
| IC memo / report with citations | Audit dossier / IC PDF |

### Differentiate (CiteAlpha owns the wedge)

| AlphaSense thing | CiteAlpha angle |
|---|---|
| Broad market intelligence search | **GCI** 0–100 |
| Deep Research multi-doc synthesis | Promise Threads + evidence trail |
| Sentiment / “story behind the call” | met / exceeded / missed / dropped / pending |
| Expert Insights (Tegus) | Hand-labeled Sensex outcomes |
| Generative Grid / comps | Sector GCI peers + Δ |
| Monitoring filings 24/7 | Guidance / actual refresh + alerts |
| SuperAnalyst Skills | Review queue + extract Accept/Edit/Reject |
| Vertical packs (IB/HF/PE/…) | One vertical: India equity desks |

### Refuse (explicit non-goals)

500M+ firehose · broker research · Tegus live calls · newsroom · live quotes / OMS · Buy–Hold–Sell · multi-industry corp packs · mobile-first research app (MVP).

**Changed 2026-10-03:** an always-on cited agent (SuperAnalyst-style), Excel/PPT export and connectors are now **in scope** as CiteAlpha Analyst, on public Indian disclosures plus user uploads only. See `docs/PLAN_CITEALPHA_ANALYST.md`.

**One-liner:** AlphaSense = *find anything, cite it*. CiteAlpha = *did management deliver, prove it*. CiteAlpha **Sights** (`/sights`) covers research-OS *jobs* with CiteAlpha brands (Sights Search, Ask, Compare Grid, Deep Dive, Street Context, Field Evidence) on **public IR + labels** — never unlicensed broker PDFs or expert-call brokerage. See `docs/customer/skus/SIGHTS.md` and `docs/kb/14-sights.md`.

---

## Match / Differentiate / Refuse (Bloomberg inventory)

Sources: [bloomberg.com](https://www.bloomberg.com/) (media) + [Bloomberg Professional / Terminal](https://professional.bloomberg.com/products/bloomberg-terminal/).

Rule: **complement the Terminal**; never rebuild quotes, OMS, risk, or a newsroom. Sell GCI as the accountability layer desks open *beside* Bloomberg.

### Match (same buyer need — our lane)

| Bloomberg thing | CiteAlpha posture | Why match |
|---|---|---|
| Company / security focus + watchlists | Tracker ★ + Research watch + Desk focus | Standard desk chrome |
| Research / intelligence on a name | Dossier + promise brief + citeable outcomes | Prep for earnings / IC — delivery track record |
| Alerts on what changed | Guidance / actual refresh + miss/drop alerts | Monitoring *promises*, not every tick |
| Messaging / “who said what” auditability | `cite_*` quote, locator, `/c/{id}`, IC footnote | Compliance-grade evidence (narrower corpus) |
| Enterprise SSO / seats / procurement hygiene | OIDC path, Desk seats, `/trust`, Terms/Privacy | Required to sit on a Bloomberg desk |
| Estimates *context* next to guidance | Street vs management guidance on brief / estimates tab | Import or license consensus; GCI stays the differentiator |
| API / embed into firm workflow | `/api/*`, EM export shape, API keys | Quant/platform embed — not B-PIPE |

### Differentiate (neighborhood overlap — CiteAlpha owns the wedge)

| Bloomberg thing | CiteAlpha angle | Do not copy as |
|---|---|---|
| Terminal “company overview” / fundamentals | **GCI 0–100** + labels (met / exceeded / missed / dropped / pending) | Another fundamentals sheet |
| Street consensus / EE | **Management promise vs subsequent actual** | Competing estimate vendor |
| News analytics / “what people are reading” | Evidence trail tied to score points | Sentiment / readership dashboard |
| Bloomberg Intelligence industry notes | India IR-native Promise Threads | Global sector research franchise |
| ASKB agentic AI over Terminal universe | Cite-only GenAI over *our* guidance corpus; refuse if empty | General Terminal chatbot |
| Launchpad multi-asset monitors | India equity GCI universe + peers + rankings | Multi-asset tape |
| Alternative data `{ALTD}` | Hand-labeled Sensex outcomes as moat | Foot-traffic / web KPI nowcasting |

**One-liner:** Bloomberg = *price it, trade it, read it*. CiteAlpha = *did management deliver, prove it*.

### Refuse (explicit non-goals)

| Bloomberg thing | CiteAlpha | Reason |
|---|---|---|
| Live quotes / depth / FX / rates | **Refuse** | Terminal monopoly; “bring your Terminal” |
| B-PIPE / Data License / SAPI as product | **Refuse** | Enterprise market-data feed war |
| BVAL / evaluated pricing | **Refuse** | Pricing utility, not GCI |
| AIM / OMS / execution (FIT, FXET, …) | **Refuse** | Trading stack |
| PORT / MARS / risk / collateral / XVA | **Refuse** | Risk OS |
| bloomberg.com newsroom + TV/Radio/Businessweek | **Refuse** | B2C media; SEBI tip risk if retailized |
| Instant Bloomberg network | **Refuse** | Social graph of finance |
| Multi-asset global coverage as MVP | **Refuse** | India equity beachhead first |
| Retail Buy / Hold / Sell on consumer site | **Refuse** | Compliance hard stop |

### Decision matrix (quick)

```text
                    MATCH          DIFFERENTIATE           REFUSE
Company focus       ████           GCI-bound
Alerts              ██             guidance misses
Citations/audit     ████
Enterprise admin    ██
Estimates context   ██             mgmt vs street
ASKB / Terminal AI                 ░░ cite-only GCI        ████ (as Terminal AI)
Quotes / B-PIPE                                            ████
OMS / AIM / PORT/MARS                                      ████
News / TV / B2C                                            ████
```

### Build order (Bloomberg-facing)

1. **Defend:** GCI + citeable India corpus (Sensex → Nifty).  
2. **Match:** promise brief, alerts, watchlist, Trust/SSO for desks that already have Terminal.  
3. **Differentiate:** rankings, peers, HITL extract — prove delivery better than EE alone.  
4. **Never:** quotes, OMS, risk, newsroom, “Bloomberg for India.”

---

## Commercial implication

| Buyer says | Don’t sell | Do sell |
|---|---|---|
| “We need AlphaSense” | Fake content scale | **CiteAlpha Search + GCI** on India names they cover |
| “We need Bloomberg” | Fake quotes/OMS | **GCI + estimates-vs-guidance** beside their Terminal |
| “One-stop research” | One-stop *market data* | **One-Stop Platform** = guidance accountability stack only |

---

## Near-term product backlog (from this gap analysis)

1. **Depth:** hand-label remaining Sensex IR accept + Nifty M3/M4 (analyst labor).  
2. **Search/Chat:** set `OPENAI_API_KEY` on ECS for live LLM extract + embeddings (plumbing shipped).  
3. **Enterprise:** register OIDC IdP; `SSO=true` + secrets (checklist on Desk CSM + `/trust`).  
4. **Estimates:** licensed consensus import (sample fixture is demo-gated).  
5. **Billing:** Razorpay merchant when ready (MSA pilot→Desk path shipped; no fake PSP).  
6. **B2C:** skip newsroom; optional vernacular factual cards only.

**Stepwise plan:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (Phases 0–8).

## Implementation status (code)

Phases **0–8 in repo** (v0.5.x): Sensex-30 hand_labeled coverage, document store + ingest, extract→commit, cite-only chat with numbered citations, editable watchlist prefs, Trust Center (`GET /api/trust`, `/trust`), feature flags, SSO OIDC path, consensus import, Nifty scaffold, sector benchmarks. See `/api/meta.implementation_phases`.