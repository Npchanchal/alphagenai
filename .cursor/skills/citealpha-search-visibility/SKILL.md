---
name: citealpha-search-visibility
description: >-
  Audits and fixes how CiteAlpha appears to search engines, answer engines, AI
  assistants and agents (SEO, AEO, GEO, AIO, LLMO, AXO, SXO, VSO, CRO). Use when
  asked for an SEO or AI-visibility audit, when editing prerender-seo.mjs,
  seo-shared.mjs, seo.ts, seoJsonLd.ts, SeoHead, llms.txt, ai-catalog.json,
  sitemaps, robots.txt or nginx confs, when adding a public route, or when a
  crawler shows an old score, a soft 404 or a missing page body.
---

# Search and answer-engine visibility

Rule `seo-marketing` holds the standards. This skill is how to check them and where each fix belongs. Copy: `public-copy-voice`. Numbers: `index-integrity`. Brand marks: `brand-assets` (never touch).

## Owners — extend these, do not add siblings

| Concern | Owner |
|---|---|
| Crawler HTML per route, sitemaps, `llms-full` levels | `frontend/scripts/prerender-seo.mjs` (fetch + write) · `frontend/scripts/seo-shared.mjs` (pure builders) |
| Client meta, canonical, JSON-LD | `frontend/src/components/SeoHead.tsx` · `src/lib/seo.ts` · `src/lib/seoJsonLd.ts` · `src/lib/seoRoutes.json` · `src/lib/seo-structured-data.json` |
| Indexable dossiers, titles, delivery sentence | `backend/app/services/seo_public.py` → `/api/public/seo-dossiers` |
| OG cards | `backend/app/services/og_card.py` → `/api/og/{id}.png` |
| Answer-engine files | `frontend/public/{llms.txt,llms-full.txt,ai.txt}` · `public/.well-known/ai-catalog.json` |
| 404s, `/api/` precedence, `.well-known` | `frontend/nginx.fargate.conf` (prod) · `nginx.conf` (compose) · `nginx.aws.conf` · `nginx.spa-routes.conf` · `nginx.static.conf` |
| HEAD on public reads | `backend/app/services/head_requests.py` |
| Pilot form conversion | `frontend/src/components/PilotRequestForm.tsx` (`pilot_form_start`, `pilot_cta`) |

## Adding a public route

1. Route in `App.tsx`; if it is a new first segment, add it to `nginx.spa-routes.conf`.
2. Title and description in `seoRoutes.json` (sitemap entry if indexable).
3. Crawler body in `seo-shared.mjs` (`marketingBodyHtml`, or a `…BodyHtml(t, esc)` that reads `en.json`).
4. Link it from `llms.txt` only if an answer engine should cite it.

## Audit (live site)

```bash
SITE=https://citealpha.com
UA="Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"
# Words a non-JS crawler reads on each key page (a shell is < 100)
for p in / /tracker /methodology /workflows /changelog /answers /companies/infy; do
  printf "%-18s " "$p"; curl -s -A "$UA" "$SITE$p" | sed 's/<script[^>]*>.*<\/script>//g; s/<[^>]*>/ /g' | wc -w
done
# Soft 404s: these must be 404, not 200
for p in /no-such-page /.well-known/nothing.json /tracker-old; do curl -s -o /dev/null -w "%{http_code} $p\n" "$SITE$p"; done
# OG card and feeds answer GET and HEAD
for p in /api/og/infy.png /api/v1/index/changelog.rss /rss.xml; do
  curl -s -o /dev/null -w "GET %{http_code} %{content_type} $p\n" "$SITE$p"
  curl -sI -o /dev/null -w "HEAD %{http_code} $p\n" "$SITE$p"
done
# Sitemap: URL count, and no lastmod equal to today unless something changed today
curl -s $SITE/sitemap.xml | grep -c "<url>"; curl -s $SITE/sitemap.xml | grep -c "$(date +%F)"
# Dossier title carries GCI, tier and data date
curl -s $SITE/companies/infy | grep -o "<title>[^<]*</title>"
# Published levels for answer engines
curl -s $SITE/llms-full.txt | sed -n '/## Published GCI levels/,$p'
```

Check per page: one `<h1>`, canonical equals the URL, meta description has "Data as of" when a score shows, JSON-LD types match rule `seo-marketing`, no internal ids or banned words in the body.

## Local verification before handing back

```bash
cd frontend && PRERENDER_API_URL=https://citealpha.com PRERENDER_REQUIRE_API=1 npm run build
cd ../backend && .venv/bin/python -m pytest tests/test_seo_crawl_surface.py tests/test_seo_dossiers.py tests/test_public_copy_hygiene.py -q
cd ../frontend && npx vitest run src/lib
for c in nginx.fargate.conf nginx.conf nginx.aws.conf; do
  docker run --rm --add-host api:127.0.0.1 -v $PWD/$c:/etc/nginx/conf.d/default.conf:ro \
    -v $PWD/nginx.static.conf:/etc/nginx/snippets/static-cache.conf:ro \
    -v $PWD/nginx.spa-routes.conf:/etc/nginx/snippets/spa-routes.conf:ro nginx:1.27-alpine nginx -t
done
```

## Deploy order

The web image snapshots dossiers from the live API while building. When a change touches both `seo_public.py` and the prerender, deploy the API first, then rebuild the web image, or the crawler HTML keeps the old API wording until the next deploy. Deploys are the user's call (`citealpha-aws`).

## Needs the owner, not an agent

Social profile URLs for `sameAs`, a named author for blog bylines, new brand images or icons, translated URLs per language, pricing on public pages, and Core Web Vitals field data (PageSpeed / Search Console access).
