/**
 * Post-build: prerender route-specific HTML + generate sitemap.xml
 * so crawlers see correct title, canonical, robots, and crawlable body text.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  SITE,
  INDEXNOW_KEY,
  loadStructured,
  websiteJsonLd,
  extraJsonLdForPath,
  dossierDatasetJsonLd,
  dossierBodyHtml,
  dossierTitle,
  TIER_NAME,
  speakableJsonLd,
  breadcrumbJsonLd,
  blogSeoTitle,
  marketingBodyHtml,
  buildImageSitemap,
  buildRssFeed,
  pingIndexNow,
  loadEnglishStrings,
  methodologyBodyHtml,
  workflowsBodyHtml,
  changelogBodyHtml,
} from "./seo-shared.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DIST = path.join(ROOT, "dist");
const PUBLIC = path.join(ROOT, "public");
const BLOG_TS = path.join(ROOT, "src/lib/blogPosts.ts");
const SEO_ROUTES = path.join(ROOT, "src/lib/seoRoutes.json");
const GLOSSARY_TS = path.join(ROOT, "src/lib/glossary.ts");
const DOSSIER_SNAPSHOT = path.join(ROOT, "src/lib/seoDossiers.json");
const STRUCTURED = loadStructured(ROOT);
const T = loadEnglishStrings(ROOT);

/** Origins that serve published rows. A set PRERENDER_API_URL is the only source: a local API must not stand in for it. */
function prerenderApiBases() {
  const pinned = process.env.PRERENDER_API_URL?.trim();
  const bases = pinned ? [pinned] : ["http://127.0.0.1:8000", "http://api:8000"];
  return bases.map((base) => base.replace(/\/$/, ""));
}

/** GET a public API path from the first origin that answers; null when none does. */
async function fetchPublishedJson(apiPath, timeoutMs = 8000) {
  for (const base of prerenderApiBases()) {
    try {
      const res = await fetch(`${base}${apiPath}`, { signal: AbortSignal.timeout(timeoutMs) });
      if (res.ok) return { base, body: await res.json() };
    } catch {
      /* try next */
    }
  }
  return null;
}

/** Strict builds (PRERENDER_REQUIRE_API=1) stop rather than publish stale scores to crawlers. */
function requirePublishedApi() {
  return process.env.PRERENDER_REQUIRE_API === "1";
}

/** A dossier is indexable only with a published GCI; rows without one have no number to cite. */
function publishedDossiers(rows) {
  return (Array.isArray(rows) ? rows : []).filter((d) => d && d.gci_score != null);
}

// `--snapshot` runs before `vite build`: the bundle (seo.ts first paint) and the prerender
// below then read the same published dossier rows.
if (process.argv.includes("--snapshot")) {
  const hit = await fetchPublishedJson("/api/public/seo-dossiers");
  if (hit && Array.isArray(hit.body?.dossiers)) {
    const dossiers = publishedDossiers(hit.body.dossiers);
    fs.writeFileSync(DOSSIER_SNAPSHOT, `${JSON.stringify({ dossiers }, null, 2)}\n`);
    console.log(`seo snapshot: ${dossiers.length} published dossiers from ${hit.base}`);
  } else if (requirePublishedApi()) {
    throw new Error(
      "seo snapshot: no API answered /api/public/seo-dossiers. Set PRERENDER_API_URL to the deployed site, " +
        "or PRERENDER_REQUIRE_API=0 to ship the committed snapshot.",
    );
  } else {
    console.warn("seo snapshot: no API reachable; keeping the committed src/lib/seoDossiers.json");
  }
  process.exit(0);
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function loadSeoRoutes() {
  return JSON.parse(fs.readFileSync(SEO_ROUTES, "utf8"));
}

function parseBlogPosts() {
  const src = fs.readFileSync(BLOG_TS, "utf8");
  const posts = [];
  const chunks = src.split(/\n\s*{\s*\n\s*slug:\s*/).slice(1);

  function extractSections(text) {
    const sections = [];
    let i = 0;
    while (true) {
      const pIdx = text.indexOf("paragraphs:", i);
      if (pIdx < 0) break;
      const braceStart = text.lastIndexOf("{", pIdx);
      const objSlice = text.slice(braceStart, pIdx);
      const hm = objSlice.match(/heading:\s*"((?:[^"\\]|\\.)*)"/);
      const bracket = text.indexOf("[", pIdx);
      let depth = 0;
      let j = bracket;
      for (; j < text.length; j++) {
        if (text[j] === "[") depth++;
        else if (text[j] === "]") {
          depth--;
          if (depth === 0) {
            j++;
            break;
          }
        }
      }
      const arr = text.slice(bracket + 1, j - 1);
      const paragraphs = [];
      const pRe = /"((?:[^"\\]|\\.)*)"/g;
      let pm;
      while ((pm = pRe.exec(arr)) !== null) {
        paragraphs.push(pm[1].replace(/\\"/g, '"').replace(/\\n/g, "\n"));
      }
      if (paragraphs.length) {
        sections.push({
          heading: hm ? hm[1].replace(/\\"/g, '"') : undefined,
          paragraphs,
        });
      }
      i = j;
    }
    return sections;
  }

  for (const chunk of chunks) {
    const slugM = chunk.match(/^"([^"]+)"/);
    if (!slugM) continue;
    const titleM = chunk.match(/title:\s*"((?:[^"\\]|\\.)*)"/);
    const descM = chunk.match(/description:\s*\n?\s*"((?:[^"\\]|\\.)*)"/);
    const pubM = chunk.match(/published:\s*"([^"]+)"/);
    const updM = chunk.match(/updated:\s*"([^"]+)"/);
    if (!titleM || !descM || !pubM) continue;
    const secIdx = chunk.indexOf("sections:");
    const sections = secIdx >= 0 ? extractSections(chunk.slice(secIdx)) : [];
    posts.push({
      slug: slugM[1],
      title: titleM[1].replace(/\\"/g, '"'),
      description: descM[1].replace(/\\"/g, '"'),
      published: pubM[1],
      updated: updM ? updM[1] : pubM[1],
      sections,
    });
  }
  return posts;
}

function rootFallbackHtml(seo) {
  if ((seo.robots ?? "index,follow").includes("noindex") && !seo.bodyHtml) {
    return `<div id="root"></div>`;
  }
  if (seo.bodyHtml) {
    return `<div id="root">${seo.bodyHtml}</div>`;
  }
  return `<div id="root">
      <main>
        <h1>${esc(seo.title)}</h1>
        <p>${esc(seo.description)}</p>
      </main>
    </div>`;
}

function blogArticleHtml(post) {
  const parts = [
    `<article>`,
    `<h1>${esc(post.title)}</h1>`,
    `<p><strong>CiteAlpha Research · Ocotillo Innovation Private Limited</strong> · Published ${esc(post.published)}${post.updated && post.updated !== post.published ? ` · Updated ${esc(post.updated)}` : ""}</p>`,
    `<p class="seo-speakable">${esc(post.description)}</p>`,
  ];
  for (const sec of post.sections || []) {
    if (sec.heading) parts.push(`<h2>${esc(sec.heading)}</h2>`);
    for (const p of sec.paragraphs || []) parts.push(`<p>${esc(p)}</p>`);
  }
  parts.push(
    `<p><a href="${SITE}/blog">CiteAlpha Research Blog</a> · <a href="${SITE}/tracker">GCI Screener</a> · <a href="${SITE}/answers">FAQ</a></p>`,
    `</article>`,
  );
  return parts.join("\n      ");
}

function blogIndexHtml(posts) {
  const items = posts
    .map(
      (p) =>
        `<li><a href="${SITE}/blog/${esc(p.slug)}"><strong>${esc(p.title)}</strong></a> — ${esc(p.description)}</li>`,
    )
    .join("\n        ");
  return `<main>
      <h1>CiteAlpha Research Blog</h1>
      <p>Articles on guidance credibility, Indian earnings evidence trails, and institutional workflows — without Buy/Hold tips.</p>
      <ul>${items}</ul>
    </main>`;
}

function injectSeo(html, seo) {
  const url = seo.path === "/" ? `${SITE}/` : `${SITE}${seo.path}`;
  const robots = seo.robots ?? "index,follow";
    const ogType = seo.type ?? "website";
  const ogAlt = esc(seo.ogImageAlt ?? seo.title);
  const ogImage = seo.ogImage ?? `${SITE}/og-image.png`;
  let out = html;
  out = out.replace(/<title>[^<]*<\/title>/, `<title>${esc(seo.title)}</title>`);
  out = out.replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/>/,
    `<meta name="description" content="${esc(seo.description)}" />`,
  );
  out = out.replace(
    /<meta\s+name="robots"\s+content="[^"]*"\s*\/>/,
    `<meta name="robots" content="${robots}" />`,
  );
  // Search Console and Bing read the verification tag from the served HTML; Bing does not run JavaScript.
  const verify = [
    ["google-site-verification", process.env.VITE_GSC_VERIFICATION],
    ["msvalidate.01", process.env.VITE_BING_VERIFICATION],
  ]
    .filter(([name, v]) => v?.trim() && !out.includes(`name="${name}"`))
    .map(([name, v]) => `<meta name="${name}" content="${esc(v.trim())}" />`);
  if (verify.length) out = out.replace("</head>", () => `    ${verify.join("\n    ")}\n  </head>`);
  out = out.replace(
    /<link\s+rel="canonical"\s+href="[^"]*"\s*\/>/,
    `<link rel="canonical" href="${url}" />`,
  );
  out = out.replace(
    /<meta\s+property="og:type"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:type" content="${ogType}" />`,
  );
  out = out.replace(
    /<meta\s+property="og:title"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:title" content="${esc(seo.title)}" />`,
  );
  out = out.replace(
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:description" content="${esc(seo.description)}" />`,
  );
  out = out.replace(
    /<meta\s+property="og:url"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:url" content="${url}" />`,
  );
  out = out.replace(
    /<meta\s+property="og:image"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:image" content="${esc(ogImage)}" />`,
  );
  if (out.includes('property="og:image:alt"')) {
    out = out.replace(
      /<meta\s+property="og:image:alt"\s+content="[^"]*"\s*\/>/,
      `<meta property="og:image:alt" content="${ogAlt}" />`,
    );
  }
  if (out.includes('name="twitter:image"')) {
    out = out.replace(
      /<meta\s+name="twitter:image"\s+content="[^"]*"\s*\/>/,
      `<meta name="twitter:image" content="${esc(ogImage)}" />`,
    );
  }
  out = out.replace(
    /<meta\s+name="twitter:title"\s+content="[^"]*"\s*\/>/,
    `<meta name="twitter:title" content="${esc(seo.title)}" />`,
  );
  out = out.replace(
    /<meta\s+name="twitter:description"\s+content="[^"]*"\s*\/>/,
    `<meta name="twitter:description" content="${esc(seo.description)}" />`,
  );

  const jsonBlocks = [];
  if (seo.jsonLd) jsonBlocks.push(seo.jsonLd);
  if (seo.extraJsonLd) jsonBlocks.push(...seo.extraJsonLd);
  if (jsonBlocks.length) {
    const block = jsonBlocks
      .map(
        (j, i) =>
          `<script type="application/ld+json" id="seo-prerender-jsonld-${i}">\n${JSON.stringify(j, null, 2)}\n    </script>`,
      )
      .join("\n    ");
    out = out.replace(/<script type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>\n?/g, "");
    out = out.replace("</head>", () => `    ${block}\n  </head>`);
  }

  const root = rootFallbackHtml(seo);
  if (out.includes('id="root"')) {
    out = out.replace(/<div id="root"><\/div>/, () => root);
  }
  out = out.replace(/<div id="seo-crawl-fallback"[\s\S]*?<\/div>/, "");
  return out;
}

function routeRel(routePath) {
  if (routePath === "/blog") return "blog/index.html";
  if (routePath.startsWith("/blog/")) return `blog/${routePath.slice("/blog/".length)}/index.html`;
  if (routePath === "/") return "index.html";
  if (routePath === "/app-shell") return "app-shell.html";
  return `${routePath.replace(/^\//, "")}/index.html`;
}

function writeRoute(seo, baseHtml) {
  const html = injectSeo(baseHtml, seo);
  const rel = routeRel(seo.path);
  const outPath = path.join(DIST, rel);
  if (rel !== "index.html" && !rel.endsWith("app-shell.html")) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
  }
  fs.writeFileSync(outPath, html);
  console.log("prerender", seo.path, "->", rel);
}

function blogIndexJsonLd(posts) {
  return {
    "@context": "https://schema.org",
    "@type": "Blog",
    name: "CiteAlpha Research Blog",
    url: `${SITE}/blog`,
    publisher: {
      "@type": "Organization",
      name: "CiteAlpha",
      legalName: "Ocotillo Innovation Private Limited",
    },
    blogPost: posts.map((p) => ({
      "@type": "BlogPosting",
      headline: p.title,
      url: `${SITE}/blog/${p.slug}`,
      datePublished: p.published,
      description: p.description,
    })),
  };
}

/**
 * A static page gets a lastmod only from a date that means a content change: its own `sitemap.lastmod`,
 * or the newest published row it lists. The build day is not one — Google ignores a lastmod that moves every deploy.
 */
function buildSitemap(staticRoutes, posts, dossiers = [], lastmodByPath = {}) {
  const urls = [];
  for (const route of staticRoutes) {
    if (!route.sitemap || (route.robots ?? "index,follow").includes("noindex")) continue;
    urls.push({
      loc: route.path === "/" ? `${SITE}/` : `${SITE}${route.path}`,
      lastmod: route.sitemap.lastmod ?? lastmodByPath[route.path],
      changefreq: route.sitemap.changefreq,
      priority: route.sitemap.priority,
    });
  }
  for (const post of posts) {
    urls.push({
      loc: `${SITE}/blog/${post.slug}`,
      lastmod: post.updated,
      changefreq: "monthly",
      priority: "0.7",
    });
  }
  for (const d of dossiers) {
    urls.push({
      loc: `${SITE}${d.path}`,
      lastmod: d.as_of ? String(d.as_of).slice(0, 10) : undefined,
      changefreq: "weekly",
      priority: "0.8",
    });
  }
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ];
  for (const u of urls) {
    lines.push("  <url>", `    <loc>${u.loc}</loc>`);
    if (u.lastmod) lines.push(`    <lastmod>${u.lastmod}</lastmod>`);
    lines.push(`    <changefreq>${u.changefreq}</changefreq>`, `    <priority>${u.priority}</priority>`, "  </url>");
  }
  lines.push("</urlset>");
  return `${lines.join("\n")}\n`;
}


/** The published levels as plain text for llms-full.txt; written at build from the same rows as the dossiers. */
function llmsPublishedLevels(rows) {
  const lines = [
    "## Published GCI levels",
    "",
    `Every company with a published Guidance Credibility Index at the time this file was built (${rows.length}). Cite the company page, not this list. Any company not listed here has no published GCI.`,
    "",
  ];
  for (const d of rows) {
    const tier = TIER_NAME[d.confidence_tier] || "";
    const asOf = d.as_of ? String(d.as_of).slice(0, 10) : "";
    lines.push(
      `- ${d.name}${d.ticker ? ` (${d.ticker})` : ""}: GCI ${Number(d.gci_score).toFixed(1)}${tier ? `, ${tier} tier` : ""}${
        asOf ? `, data as of ${asOf}` : ""
      }. ${d.record_sentence || ""} ${SITE}${d.path}`,
    );
  }
  return `${lines.join("\n")}\n`;
}

/** Every published level with its tier and date, so "which companies have a GCI" is answerable from HTML. */
function publishedScoresHtml(rows) {
  const items = rows
    .map(
      (d) =>
        `<tr><td><a href="${SITE}${esc(d.path)}">${esc(d.name)}${d.ticker ? ` (${esc(d.ticker)})` : ""}</a></td><td>${Number(
          d.gci_score,
        ).toFixed(1)}</td><td>${esc(TIER_NAME[d.confidence_tier] || "")}</td><td>${esc(
          d.as_of ? String(d.as_of).slice(0, 10) : "",
        )}</td><td>${esc(d.record_sentence || "")}</td></tr>`,
    )
    .join("\n          ");
  return `<section>
      <h2>Published GCI levels</h2>
      <table>
        <thead><tr><th>Company</th><th>GCI</th><th>Confidence tier</th><th>Data as of</th><th>Delivery record</th></tr></thead>
        <tbody>
          ${items}
        </tbody>
      </table>
    </section>`;
}

/** Written by the `--snapshot` step from the published API, so it matches the bundle. */
function loadDossiers() {
  if (!fs.existsSync(DOSSIER_SNAPSHOT)) return [];
  const body = JSON.parse(fs.readFileSync(DOSSIER_SNAPSHOT, "utf8"));
  return publishedDossiers(body.dossiers);
}

async function loadChangelog(dossiers) {
  const [entries, ledger, companies] = await Promise.all([
    fetchPublishedJson("/api/v1/index/changelog"),
    fetchPublishedJson("/api/v1/index/ledger?limit=500"),
    fetchPublishedJson("/api/v1/companies", 30000),
  ]);
  if ((!entries || !ledger) && requirePublishedApi()) {
    throw new Error("prerender: /api/v1/index/changelog or /ledger did not answer; the changelog would ship empty.");
  }
  const names = {};
  for (const d of dossiers) names[d.id] = d.name;
  if (Array.isArray(companies?.body)) {
    for (const c of companies.body) if (c?.id && c?.name) names[c.id] = c.name;
  }
  return {
    entries: entries?.body?.entries ?? null,
    ledger: ledger?.body?.rows ? [...ledger.body.rows].reverse() : null,
    names,
  };
}

const baseHtml = fs.readFileSync(path.join(DIST, "index.html"), "utf8");
const staticRoutes = loadSeoRoutes();
const posts = parseBlogPosts();
const dossiers = loadDossiers();
const changelog = await loadChangelog(dossiers);
let prerenderCount = 0;
const indexNowUrls = [];

for (const route of staticRoutes) {
  const seo = { path: route.path, ...route, ogImageAlt: route.title };
  if (route.path === "/") {
    seo.jsonLd = websiteJsonLd(STRUCTURED);
  }
  if (route.path === "/blog") {
    seo.jsonLd = blogIndexJsonLd(posts);
    seo.bodyHtml = blogIndexHtml(posts);
  }
  const marketingBody = marketingBodyHtml(route.path, {
    glossaryPath: GLOSSARY_TS,
    structuredData: STRUCTURED,
    esc,
    t: T,
  });
  if (marketingBody) seo.bodyHtml = marketingBody;
  if (route.path === "/methodology") seo.bodyHtml = methodologyBodyHtml(T, esc);
  if (route.path === "/workflows") seo.bodyHtml = workflowsBodyHtml(T, esc);
  if (route.path === "/changelog") seo.bodyHtml = changelogBodyHtml(T, esc, changelog);
  if ((route.path === "/tracker" || route.path === "/rankings") && dossiers.length) {
    seo.bodyHtml = `${seo.bodyHtml || ""}\n${publishedScoresHtml(dossiers)}`;
  }
  seo.extraJsonLd = extraJsonLdForPath(route.path, STRUCTURED, route.title);
  writeRoute(seo, baseHtml);
  if (!((route.robots ?? "index,follow").includes("noindex"))) {
    indexNowUrls.push(route.path === "/" ? `${SITE}/` : `${SITE}${route.path}`);
  }
  prerenderCount += 1;
}

for (const post of posts) {
  const title = blogSeoTitle(post);
  const extras = [];
  if (post.slug === "what-is-guidance-credibility-index") {
    extras.push(speakableJsonLd(`${SITE}/blog/${post.slug}`, STRUCTURED));
  }
  const crumbs = breadcrumbJsonLd(`/blog/${post.slug}`, title);
  if (crumbs) extras.push(crumbs);
  const seo = {
    path: `/blog/${post.slug}`,
    title,
    description: post.description,
    type: "article",
    ogImageAlt: `${post.title} — CiteAlpha Research Blog`,
    bodyHtml: blogArticleHtml(post),
    extraJsonLd: extras,
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      headline: post.title,
      description: post.description,
      datePublished: post.published,
      dateModified: post.updated,
      author: {
        "@type": "Organization",
        name: "CiteAlpha",
        legalName: "Ocotillo Innovation Private Limited",
      },
      publisher: {
        "@type": "Organization",
        name: "CiteAlpha",
        logo: { "@type": "ImageObject", url: `${SITE}/citealpha-logo.png` },
      },
      mainEntityOfPage: `${SITE}/blog/${post.slug}`,
      image: `${SITE}/og-image.png`,
    },
  };
  writeRoute(seo, baseHtml);
  indexNowUrls.push(`${SITE}/blog/${post.slug}`);
  prerenderCount += 1;
}

for (const d of dossiers) {
  const crumbs = breadcrumbJsonLd(d.path, d.name);
  const seo = {
    path: d.path,
    title: dossierTitle(d),
    description: d.description,
    robots: "index,follow",
    ogImage: `${SITE}/api/og/${d.id}.png`,
    ogImageAlt: dossierTitle(d),
    bodyHtml: dossierBodyHtml(d, esc),
    jsonLd: dossierDatasetJsonLd(STRUCTURED, d),
    extraJsonLd: crumbs ? [crumbs] : [],
  };
  writeRoute(seo, baseHtml);
  indexNowUrls.push(`${SITE}${d.path}`);
  prerenderCount += 1;
}

{
  let shell = injectSeo(baseHtml, {
    path: "/",
    title: "CiteAlpha",
    description:
      "CiteAlpha Guidance Credibility Index — evidence-linked management guidance vs delivery for Indian equity desks. Not investment advice.",
    robots: "noindex,follow",
    bodyHtml: "",
  });
  shell = shell.replace(/<script\b[^>]*type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>/gi, "");
  shell = shell.replace(/<script\b[^>]*id="seo-prerender-jsonld[^"]*"[^>]*>[\s\S]*?<\/script>/gi, "");
  // Unknown URLs are noindex. A canonical to the homepage would pass that noindex onto the page answer engines should index.
  shell = shell.replace(/\s*<link\s+rel="canonical"\s+href="[^"]*"\s*\/?>/g, "");
  shell = shell.replace(/\s*<meta\s+property="og:url"\s+content="[^"]*"\s*\/?>/g, "");
  if (!/name="robots" content="noindex/.test(shell)) {
    shell = shell.replace(/<meta\s+name="robots"\s+content="[^"]*"\s*\/?>/, '<meta name="robots" content="noindex,follow" />');
  }
  if (/rel="canonical"|property="og:url"/.test(shell)) {
    throw new Error("app-shell must not declare a canonical URL");
  }
  fs.writeFileSync(path.join(DIST, "app-shell.html"), shell);
  console.log("prerender /app-shell -> app-shell.html");
  prerenderCount += 1;
}

const newest = (dates) => dates.filter(Boolean).map((d) => String(d).slice(0, 10)).sort().pop();
const scoresChanged = newest((changelog.entries ?? []).map((e) => e.date));
const sitemap = buildSitemap(staticRoutes, posts, dossiers, {
  "/changelog": scoresChanged,
  "/tracker": scoresChanged,
  "/rankings": scoresChanged,
  "/blog": newest(posts.map((p) => p.updated || p.published)),
});
const imageSitemap = buildImageSitemap(posts, dossiers);
const rss = buildRssFeed(posts);
fs.writeFileSync(path.join(DIST, "sitemap.xml"), sitemap);
fs.writeFileSync(path.join(PUBLIC, "sitemap.xml"), sitemap);
fs.writeFileSync(path.join(DIST, "sitemap-images.xml"), imageSitemap);
fs.writeFileSync(path.join(PUBLIC, "sitemap-images.xml"), imageSitemap);
fs.writeFileSync(path.join(DIST, "rss.xml"), rss);
fs.writeFileSync(path.join(PUBLIC, "rss.xml"), rss);
fs.writeFileSync(path.join(PUBLIC, `${INDEXNOW_KEY}.txt`), `${INDEXNOW_KEY}\n`);
fs.writeFileSync(path.join(DIST, `${INDEXNOW_KEY}.txt`), `${INDEXNOW_KEY}\n`);
fs.copyFileSync(path.join(PUBLIC, "robots.txt"), path.join(DIST, "robots.txt"));
if (fs.existsSync(path.join(PUBLIC, "ai.txt"))) {
  fs.copyFileSync(path.join(PUBLIC, "ai.txt"), path.join(DIST, "ai.txt"));
}
fs.writeFileSync(
  path.join(DIST, "llms-full.txt"),
  `${fs.readFileSync(path.join(PUBLIC, "llms-full.txt"), "utf8").trimEnd()}\n\n${llmsPublishedLevels(dossiers)}`,
);

console.log(
  `prerender-seo: ${prerenderCount} routes, sitemap: ${sitemap.split("<url>").length - 1} urls, posts: ${posts.length}`,
);

await pingIndexNow(indexNowUrls);
