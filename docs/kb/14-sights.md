# 14 — CiteAlpha Sights

Parallel SKU: India disclosure research OS at `/sights/*`.

## Rule

Own brands only. Public IR + CiteAlpha labels + licensed APIs we pay for. No competitor trademarks in UI. No unlicensed broker PDF firehose. No expert-call marketplace.

## Surfaces

| Path | Name |
|---|---|
| `/sights` | Hub |
| `/sights/themes` | Delivery Themes |
| `/sights/street` | Street Context |
| `/sights/field` | Field Evidence |
| `/sights/grid` | Compare Grid |
| `/sights/deep-dive` | Deep Dive |
| `/sights/fundamentals` | Fundamentals Strip |
| `/sights/settings` | Enterprise links |

### Merged away (2026-10-17)

| Old path | Now | Why |
|---|---|---|
| `/sights/search` | `/research?scope=all` (Filing Search, All covered companies, India IR synonyms on) | Same backend as Filing Search |
| `/sights/ask` | `/research?tab=chat&scope=all` | Same cite-only chat |
| `/sights/boards` | `/research?tab=watch`; saved searches live on the Filing Search tab (`preferences.saved_queries`) | Same `preferences.watchlist` |
| `/sights/agents` | `/analyst` (Skills) | Four templates were ported to Skills in A2 |
| `/sights/export` | `/analyst` (exports + destinations) | Analyst exports carry the Evidence Receipt; destinations deliver to Slack/Teams/webhooks |

React routes and nginx both redirect (301 at nginx). `/api/sights/search` and `/ask` still answer with `superseded_by`; `/api/sights/agents*`, `/hooks`, `/export/{id}` return `410` with `moved_to`.

## Legal-safe variants (internal — never put competitor names in UI)

| Market-intel job (category) | CiteAlpha Sights variant | Legal tweak |
|---|---|---|
| Generative Search–style Q&A | **Sights Ask** | Cite-only over *our* India IR; refuse if empty |
| Generative Grid–style comps | **Compare Grid** | Prompts × *our* companies/docs; cite cells |
| Deep multi-doc reports | **Deep Dive** | Multi-step cite synthesis; no invented actuals |
| Broker / Wall Street Insights library | **Street Context** | Public filings + consensus APIs we license — **no** broker PDF host/proxy |
| Expert Insights / Tegus network | **Field Evidence** | Hand-labeled guidance↔actuals + citations — **no** expert-call brokerage |
| Sentiment / theme OS | **Delivery Themes** | met/miss/drop/pending labels only |
| Smart synonyms | **Business Lexicon** | India IR synonym expand — now the "Include India IR synonyms" option in Filing Search (`expand=true`) |
| Watchlists | Filing Search Watchlist tab | Watchlist + saved searches |
| Add-ins / connectors | CiteAlpha Analyst exports + destinations | Excel/PowerPoint/PDF/Markdown + webhook/Slack/Teams |

**Refuse forever (without counsel + written license):** competitor trademarks in chrome · unlicensed sell-side PDF corpus · expert-interview marketplace · “we replace [global market-intel OS]” · 500M+ doc claims · Buy/Hold.

## APIs

`/api/sights/meta`, `themes`, `street/{id}`, `field/{id}`, `grid`, `deep-dive`, `fundamentals/{id}`, `enterprise`. Deprecated aliases: `search`, `ask`. Retired (`410`): `agents`, `agents/run`, `hooks`, `export/{id}`.

Flags: `SIGHTS`, `SIGHTS_DEEP_DIVE`, `SIGHTS_GRID`, `SIGHTS_WEB_ASSIST` (off by default). `SIGHTS_AGENTS` was removed.

## Related

- One-pager: `docs/customer/skus/SIGHTS.md`
- Portfolio: `docs/PRODUCT_PORTFOLIO.md`
- Cite Research Terminal remains `/research` (Cite SKU)
