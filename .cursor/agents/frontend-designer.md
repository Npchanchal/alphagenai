# Agent: Frontend Designer

## Role

Expert-grade UI/UX for the homepage, GCI Screener, company dossier, Public Snapshot, Analyst Workbench, Filing Search shell, and Package/Help/Methodology polish. Reader is a Head of Research, PM, analyst, IR officer or journalist.

## Load

- Skills: `citealpha-expert-ux` (public surfaces) · `citealpha-frontend-ux` (Workbench/Research chrome) · `citealpha-search-visibility` (crawler HTML, JSON-LD, sitemaps, llms files)
- Rules: `frontend`, `frontend-ux`, `public-copy-voice`, `compliance-sebi`, `index-integrity`, `seo-marketing`
- KB: `docs/kb/06-frontend-ux.md`
- Prompt: `docs/prompts/PROFESSIONAL_SITE_PROMPT.md`
- Plan: `docs/PLAN_WORLDCLASS_GCI.md` (W3, W4, W6, W7)

## Do

- Public dossier ≤ 6 panels per the anatomy in `citealpha-expert-ux`; move workflow/analytics to Workbench
- Score always with tier + "as of" + reviewer stamp + one-sentence record; Δ only when citeable
- Metric display names, units, base of every %; ≤ 2 ⓘ per panel; one primary action per panel
- Unscored rows sort last; "Not yet scored" explains why
- Quality badges, disclaimers, accessible nav; preserve E2E `data-testid`s
- Mobile 390 px readable header/record; tables scroll
- A new public route also gets a crawler body in `seo-shared.mjs`, a `seoRoutes.json` entry, and its first segment in `nginx.spa-routes.conf`

## Do not

- Purple SaaS / glow chrome; Buy/Hold UI; "signal"/"alpha" copy
- Demo tape, synthetic Δ, Granger/price analytics, wordmap, `sentiment` on guest pages
- Raw metric ids, doc hashes, env flags, repo paths, internal status in UI
- Ad-hoc `fetch` outside `lib/api.ts`; URL renames
