/**
 * Shared SEO helpers for prerender-seo.mjs (mirrors src/lib/seoJsonLd.ts + marketing bodies).
 */
import fs from "node:fs";
import path from "node:path";

export const SITE = "https://citealpha.com";
export const INDEXNOW_KEY = "c17e41fa2026a1b2c3d4e5f60718";

export function loadStructured(root) {
  const raw = fs.readFileSync(path.join(root, "src/lib/seo-structured-data.json"), "utf8");
  return JSON.parse(raw);
}

/** English UI strings, so crawler HTML carries the same sentences the page renders. */
export function loadEnglishStrings(root) {
  const strings = JSON.parse(fs.readFileSync(path.join(root, "src/i18n/locales/en.json"), "utf8"));
  return (key, vars = {}) => {
    const raw = strings[key];
    if (typeof raw !== "string") throw new Error(`prerender: missing English string ${key}`);
    return raw.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
  };
}

export function methodologyBodyHtml(t, esc) {
  const li = (key) => `<li>${esc(t(key))}</li>`;
  const labeled = (key) => `<li><strong>${esc(t(`${key}.label`))}</strong> ${esc(t(`${key}.text`))}</li>`;
  return `<main>
      <h1>${esc(t("method.page.title"))}</h1>
      <p class="seo-speakable">${esc(t("method.page.lede"))}</p>
      <h2>${esc(t("method.page.guidance.title"))}</h2>
      <ul>${li("method.page.guidance.i1")}${li("method.page.guidance.i2")}${li("method.page.guidance.i3")}</ul>
      <h2>${esc(t("method.page.review.title"))}</h2>
      <ul>${li("method.page.review.i1")}${li("method.page.review.i2")}${li("method.page.review.i3")}${li("method.page.review.i4")}</ul>
      <h2>${esc(t("method.page.sla.title"))}</h2>
      <p>${esc(t("method.page.sla.target", { days: 5, since: "2026-09-29" }))}</p>
      <h2>${esc(t("method.page.revisions.title"))}</h2>
      <p>${esc(t("method.page.revisions.p1"))}</p>
      <p>${esc(t("method.page.revisions.p2"))}</p>
      <p>${esc(t("method.page.revisions.example"))} <a href="${SITE}/companies/infy">${esc(t("method.page.revisions.exampleLink"))}</a></p>
      <h2>${esc(t("method.page.formula.title"))}</h2>
      <p>${esc(t("method.page.formula.intro"))}</p>
      <p>${esc(t("method.page.formula.philosophy"))}</p>
      <ul>
        ${labeled("method.page.formula.inside")}
        <li><strong>${esc(t("method.page.formula.outside.label"))}</strong> ${esc(t("method.page.formula.outside.text1"))} e<sup>−0.35·δ<sup>1.25</sup></sup>${esc(t("method.page.formula.outside.text2"))}</li>
        ${labeled("method.page.formula.beats")}
        ${labeled("method.page.formula.misses")}
      </ul>
      <p><strong>${esc(t("method.page.formula.floor.label"))}</strong> ${esc(t("method.page.formula.floor.text"))}</p>
      <p>${esc(t("method.page.formula.example"))}</p>
      <p><strong>${esc(t("method.page.formula.constants.label"))}</strong> ${esc(t("method.page.formula.constants.text"))}</p>
      <h2>${esc(t("method.page.company.title"))}</h2>
      <ul>
        ${labeled("method.page.company.metric")}
        ${labeled("method.page.company.company")}
        ${labeled("method.page.company.deductions")}
        ${labeled("method.page.company.comparable")}
        ${labeled("method.page.company.open")}
        ${li("method.page.company.history")}
      </ul>
      <p>${esc(t("method.page.company.record"))}</p>
      <p>${esc(t("method.page.company.changelog"))} <a href="${SITE}/changelog">${esc(t("footer.changelog"))}</a>. Every restatement is a new ledger row; earlier levels are not overwritten.</p>
      <h2>${esc(t("method.page.independence.title"))}</h2>
      <p>${esc(t("method.page.independence.text", { product: "CiteAlpha" }))}</p>
      <h2>${esc(t("method.page.limitations.title"))}</h2>
      <ul>${li("method.page.limitations.i1")}${li("method.page.limitations.i2")}${li("method.page.limitations.i3")}${li("method.page.limitations.i4")}${li("method.page.limitations.i5")}</ul>
      <h2>${esc(t("method.page.errors.title"))}</h2>
      <p>${esc(t("method.page.errors.before"))} <a href="mailto:sales@citealpha.com">sales@citealpha.com</a> ${esc(t("method.page.errors.after"))}</p>
      <p><a href="${SITE}/">${esc(t("method.page.back"))}</a> · <a href="${SITE}/trust">${esc(t("footer.trust"))}</a> · <a href="${SITE}/answers">${esc(t("footer.answers"))}</a></p>
      <p>Not investment advice.</p>
    </main>`;
}

const WORKFLOW_JOBS = [
  {
    id: "earnings-season",
    key: "earnings",
    links: [
      ["/companies/infy", "linkDossier"],
      ["/analyst", "linkMonitor"],
    ],
  },
  {
    id: "management-delivery",
    key: "delivery",
    links: [
      ["/tracker", "linkScreener"],
      ["/companies/infy", "linkEvidence"],
      ["/methodology", "linkMethod"],
    ],
  },
  {
    id: "coverage",
    key: "coverage",
    links: [
      ["/tracker", "linkScreener"],
      ["/rankings", "linkSnapshot"],
      ["/sights", "linkExplorer"],
    ],
  },
  {
    id: "desk-note",
    key: "note",
    links: [
      ["/analyst", "linkAnalyst"],
      ["/desk", "linkWorkbench"],
    ],
  },
];

export function workflowsBodyHtml(t, esc) {
  const jobs = WORKFLOW_JOBS.map((job) => {
    const links = job.links
      .map(([to, label]) => `<a href="${SITE}${to}">${esc(t(`workflows.${job.key}.${label}`))}</a>`)
      .join(" · ");
    return `<article id="${job.id}">
        <h2>${esc(t(`workflows.${job.key}.title`))}</h2>
        <p>${esc(t(`workflows.${job.key}.lede`))}</p>
        <p>${esc(t(`workflows.${job.key}.body`))}</p>
        <p>${links}</p>
      </article>`;
  }).join("\n      ");
  return `<main>
      <p>${esc(t("workflows.kicker"))}</p>
      <h1>${esc(t("workflows.title"))}</h1>
      <p class="seo-speakable">${esc(t("workflows.lede"))}</p>
      ${jobs}
      <p><a href="${SITE}/products#plans">${esc(t("workflows.pricing"))}</a></p>
      <p>Not investment advice.</p>
    </main>`;
}

/** Changelog and ledger as published by /api/v1/index/*, newest first, same columns as the page. */
export function changelogBodyHtml(t, esc, { entries = null, ledger = null, names = {} } = {}) {
  const nameOf = (id) => names[id] || String(id).toUpperCase();
  const reason = (r) => {
    try {
      return t(`changelog.reason.${r}`);
    } catch {
      return r;
    }
  };
  const score = (v) => (v == null ? "—" : Number(v).toFixed(1));
  const companyLink = (id) => `<a href="${SITE}/companies/${esc(id)}">${esc(nameOf(id))}</a>`;

  let entriesHtml = `<p>${esc(t("changelog.empty"))}</p>`;
  if (entries && entries.length) {
    entriesHtml = `<ol>
        ${entries
          .map(
            (e) =>
              `<li><time datetime="${esc(e.date)}">${esc(e.date)}</time> · ${esc(reason(e.reason))}${
                e.companies?.length ? ` · ${e.companies.map(companyLink).join(", ")}` : ""
              }<p>${esc(e.change)}</p></li>`,
          )
          .join("\n        ")}
      </ol>`;
  }

  let ledgerHtml = `<p>${esc(t("changelog.ledger.empty"))}</p>`;
  if (ledger && ledger.length) {
    const cols = ["date", "company", "from", "to", "tier", "reason", "by"]
      .map((c) => `<th>${esc(t(`changelog.ledger.cols.${c}`))}</th>`)
      .join("");
    const rows = ledger
      .map(
        (r) =>
          `<tr><td><time datetime="${esc(r.as_of)}">${esc(r.as_of)}</time> ${esc(r.dataset_version || "")}</td><td>${companyLink(
            r.company_id,
          )}</td><td>${score(r.prior_gci)}</td><td>${score(r.gci)}</td><td>${
            r.confidence_tier ? esc(t(`tier.${r.confidence_tier}`)) : esc(t("tier.unscored"))
          }</td><td>${esc(reason(r.reason))}</td><td>${esc(r.by || "")}</td></tr>`,
      )
      .join("\n          ");
    ledgerHtml = `<table>
        <thead><tr>${cols}</tr></thead>
        <tbody>
          ${rows}
        </tbody>
      </table>`;
  }

  return `<main>
      <p>${esc(t("changelog.kicker"))}</p>
      <h1>${esc(t("changelog.title"))}</h1>
      <p class="seo-speakable">${esc(t("changelog.lede"))}</p>
      ${entriesHtml}
      <h2>${esc(t("changelog.ledger.title"))}</h2>
      <p>${esc(t("changelog.ledger.lede"))}</p>
      ${ledgerHtml}
      <p>${esc(t("changelog.api"))} · <a href="${SITE}/api/v1/index/changelog.rss">RSS</a> · <a href="${SITE}/methodology">Methodology</a></p>
      <p>Not investment advice.</p>
    </main>`;
}

/** Profiles on other sites only; a citealpha.com URL tells a search engine nothing about the entity. */
const externalUrls = (urls) => (urls ?? []).filter((u) => Boolean(u) && u.startsWith("https://") && !u.startsWith(SITE));

/** Entity facts beyond the name: registration number, city, parent company, founders. Same output as seoJsonLd.ts. */
export function orgEntityFields(org) {
  const founders = (org.founders ?? [])
    .filter((f) => f?.name)
    .map((f) => {
      const sameAs = externalUrls(f.sameAs);
      return {
        "@type": "Person",
        name: f.name,
        ...(f.jobTitle ? { jobTitle: f.jobTitle } : {}),
        ...(sameAs.length ? { sameAs } : {}),
      };
    });
  return {
    ...(org.identifier ? { identifier: { "@type": "PropertyValue", ...org.identifier } } : {}),
    ...(org.address ? { address: { "@type": "PostalAddress", ...org.address } } : {}),
    ...(org.parentOrganization ? { parentOrganization: { "@type": "Organization", ...org.parentOrganization } } : {}),
    ...(founders.length ? { founder: founders } : {}),
  };
}

export function orgJsonLd(data) {
  const org = data.org;
  const sameAs = externalUrls(org.socialProfiles);
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: org.name,
    legalName: org.legalName,
    url: SITE,
    logo: `${SITE}/citealpha-logo.png`,
    description:
      "Guidance Credibility Index (GCI) — evidence-linked management guidance vs delivery for Indian equity desks. Not investment advice.",
    email: org.email,
    ...orgEntityFields(org),
    ...(sameAs.length ? { sameAs } : {}),
  };
}

export function websiteJsonLd(data) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "CiteAlpha",
    url: `${SITE}/`,
    description:
      "Guidance Credibility Index (GCI) for Indian equity desks — evidence-linked management guidance vs delivery. Not investment advice.",
    inLanguage: "en-IN",
    publisher: {
      "@type": "Organization",
      name: data.org.name,
      legalName: data.org.legalName,
    },
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${SITE}/research?q={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  };
}

export function serviceJsonLd(data) {
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    name: "CiteAlpha Guidance Credibility Index",
    serviceType: "Equity research data",
    url: SITE,
    description:
      "Evidence-linked Guidance Credibility Index (GCI) for Indian equity desks. Factual research product; not investment advice.",
    areaServed: "IN",
    audience: { "@type": "BusinessAudience", audienceType: "Institutional equity research desks" },
    provider: {
      "@type": "Organization",
      name: data.org.name,
      legalName: data.org.legalName,
    },
  };
}

export const TIER_NAME = { provisional: "Provisional", established: "Established", deep: "Deep" };

/** Same shape as `dossierDatasetJsonLd` in src/lib/seoJsonLd.ts. */
export function dossierDatasetJsonLd(data, d) {
  const org = { "@type": "Organization", name: data.org.name, legalName: data.org.legalName, url: SITE };
  const measured = [
    {
      "@type": "PropertyValue",
      name: "Guidance Credibility Index (GCI)",
      minValue: 0,
      maxValue: 100,
      ...(d.gci_score != null ? { value: d.gci_score } : {}),
    },
  ];
  if (TIER_NAME[d.confidence_tier]) {
    measured.push({ "@type": "PropertyValue", name: "Confidence tier", value: TIER_NAME[d.confidence_tier] });
  }
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `${d.name} Guidance Credibility Index (GCI)`,
    description: d.description,
    url: `${SITE}${d.path}`,
    creator: org,
    publisher: org,
    keywords: ["Guidance Credibility Index", "management guidance", "Indian listed companies", d.name],
    spatialCoverage: "India",
    measurementTechnique: `Quantified management guidance compared with the later reported result, each cited to its filing. Method: ${SITE}/methodology`,
    variableMeasured: measured,
    distribution: [
      {
        "@type": "DataDownload",
        encodingFormat: "application/json",
        contentUrl: `${SITE}/api/v1/companies/${d.id}/gci`,
      },
    ],
    license: `${SITE}/terms`,
    isAccessibleForFree: true,
    ...(d.as_of ? { dateModified: String(d.as_of).slice(0, 10) } : {}),
  };
}

const UNIT_SUFFIX = { pct: "%", inr_cr: " ₹ cr", days: " days" };

function fmtValue(v, unit) {
  if (v == null) return "—";
  const n = Number(v);
  const shown = Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  return `${shown}${UNIT_SUFFIX[unit] ?? ""}`;
}

function fmtBand(r) {
  if (r.guided_low != null && r.guided_high != null && r.guided_low !== r.guided_high) {
    return `${fmtValue(r.guided_low, "")}–${fmtValue(r.guided_high, r.unit)}`;
  }
  return fmtValue(r.guided_value ?? r.guided_low ?? r.guided_high, r.unit);
}

const OUTCOME = { met: "Met", exceeded: "Exceeded", missed: "Missed" };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-04-23" → "23 Apr 2026", as seo_public.format_as_of prints it. */
export function fmtAsOf(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!m) return "";
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

/** Same words as seo_public.dossier_title, built here so a build against an older API still shows the tier. */
export function dossierTitle(d) {
  const bits = [`${d.name} — Guidance Credibility Index (GCI)`];
  if (d.gci_score != null) {
    bits[0] += ` ${Number(d.gci_score).toFixed(1).replace(/\.0$/, "")}`;
    if (TIER_NAME[d.confidence_tier]) bits.push(TIER_NAME[d.confidence_tier]);
  }
  const asOf = fmtAsOf(d.as_of);
  if (asOf) bits.push(`Data as of ${asOf}`);
  return bits.join(" · ");
}

/** Crawler body for a published dossier: the number with its tier and date, then every scored row with both filings. */
export function dossierBodyHtml(d, esc) {
  const ticker = d.ticker ? ` (${esc(d.ticker)})` : "";
  const score = d.gci_score != null ? Number(d.gci_score).toFixed(1) : null;
  const tier = TIER_NAME[d.confidence_tier];
  const asOf = fmtAsOf(d.as_of);
  const headline = score
    ? `${esc(d.name)} has a Guidance Credibility Index (GCI) of ${score}${tier ? `, confidence tier ${tier}` : ""}${
        asOf ? `, data as of ${esc(asOf)}` : ""
      }.`
    : "";
  const rows = (d.evidence || [])
    .map(
      (r) => `<tr><td>${esc(r.period)}</td><td>${esc(r.metric)}</td><td>${esc(fmtBand(r))}</td><td>${esc(
        fmtValue(r.actual_value, r.unit),
      )}</td><td>${esc(OUTCOME[r.outcome] || r.outcome)}</td><td><a href="${esc(r.guidance_source_url)}">Guidance${
        r.guidance_as_of ? `, ${esc(r.guidance_as_of)}` : ""
      }</a>${r.guidance_quote ? ` “${esc(r.guidance_quote)}”` : ""}</td><td><a href="${esc(r.source_url)}">Result${
        r.as_of ? `, ${esc(r.as_of)}` : ""
      }</a>${r.actual_quote ? ` “${esc(r.actual_quote)}”` : ""}</td></tr>`,
    )
    .join("\n          ");
  const table = rows
    ? `<h2>Guidance versus reported results</h2>
      <table>
        <thead><tr><th>Period</th><th>Metric</th><th>Guided</th><th>Reported</th><th>Outcome</th><th>Guidance filing</th><th>Results filing</th></tr></thead>
        <tbody>
          ${rows}
        </tbody>
      </table>`
    : "";
  return `<main>
      <h1>${esc(d.name)}${ticker} — Guidance Credibility Index (GCI)</h1>
      ${headline ? `<p class="seo-speakable">${headline}</p>` : ""}
      <p class="seo-speakable">${esc(d.record_sentence || d.description)}</p>
      ${table}
      <p><a href="${SITE}/companies/${esc(d.id)}">Open the full evidence trail</a> · <a href="${SITE}/tracker">GCI Screener</a> · <a href="${SITE}/methodology">Methodology</a> · <a href="${SITE}/changelog?company=${esc(d.id)}">Score changelog</a></p>
      <p>Not investment advice.</p>
    </main>`;
}

export function faqJsonLd(data) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: data.faq.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: { "@type": "Answer", text: item.answer },
    })),
  };
}

export function howToGciJsonLd(data) {
  const howTo = data.howTo;
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: howTo.name,
    description: howTo.description,
    step: howTo.steps.map((s, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: s.name,
      text: s.text,
    })),
  };
}

export function speakableJsonLd(pageUrl, data) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    url: pageUrl,
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: data.speakable.cssSelector,
    },
  };
}

export function breadcrumbJsonLd(routePath, pageTitle) {
  if (routePath === "/" || routePath.startsWith("/login") || routePath.startsWith("/register")) {
    return null;
  }
  if ((pageTitle || "").includes("Page not found")) return null;
  const items = [{ name: "Home", path: "/" }];
  if (routePath.startsWith("/blog/")) {
    items.push({ name: "Blog", path: "/blog" });
    items.push({ name: String(pageTitle).replace(/ — CiteAlpha.*$/, ""), path: routePath });
  } else if (routePath.startsWith("/companies/")) {
    items.push({ name: "GCI Screener", path: "/tracker" });
    items.push({ name: String(pageTitle).replace(/ — CiteAlpha.*$/, ""), path: routePath });
  } else if (routePath.startsWith("/about/")) {
    items.push({ name: "About", path: "/about" });
    items.push({ name: String(pageTitle).replace(/ — CiteAlpha$/, ""), path: routePath });
  } else if (routePath.startsWith("/sights/")) {
    items.push({ name: "Disclosure Explorer", path: "/sights" });
    items.push({ name: String(pageTitle).replace(/ — CiteAlpha$/, ""), path: routePath });
  } else {
    items.push({ name: String(pageTitle).replace(/ — CiteAlpha.*$/, ""), path: routePath });
  }
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: item.path === "/" ? `${SITE}/` : `${SITE}${item.path}`,
    })),
  };
}

export function extraJsonLdForPath(routePath, data, pageTitle) {
  const blocks = [];
  // FAQPage lives on /answers only: the same questions marked up on several URLs compete with each other.
  if (routePath === "/") {
    blocks.push(orgJsonLd(data), serviceJsonLd(data));
  } else if (routePath === "/about") {
    blocks.push(howToGciJsonLd(data));
  } else if (routePath === "/answers") {
    blocks.push(faqJsonLd(data));
  } else if (routePath === "/blog") {
    blocks.push(orgJsonLd(data));
  }
  if (pageTitle) {
    const crumbs = breadcrumbJsonLd(routePath, pageTitle);
    if (crumbs) blocks.push(crumbs);
  }
  return blocks;
}

export function blogSeoTitle(post) {
  if (post.slug === "what-is-guidance-credibility-index") {
    return "What is a Guidance Credibility Index (GCI)? — CiteAlpha";
  }
  return `${post.title} — CiteAlpha Blog`;
}

/** Parse GLOSSARY + HELP_SECTIONS from glossary.ts for crawlable Help HTML. */
export function parseGlossary(glossaryPath) {
  const src = fs.readFileSync(glossaryPath, "utf8");
  const glossary = {};
  const entryRe =
    /(\w+):\s*\{\s*\n\s*id:\s*"([^"]+)",\s*\n\s*term:\s*"((?:[^"\\]|\\.)*)",\s*\n\s*tip:\s*"((?:[^"\\]|\\.)*)"/g;
  let m;
  while ((m = entryRe.exec(src)) !== null) {
    glossary[m[1]] = {
      id: m[2],
      term: m[3].replace(/\\"/g, '"'),
      tip: m[4].replace(/\\"/g, '"'),
    };
  }

  const sections = [];
  const secRe =
    /\{\s*\n\s*title:\s*"([^"]+)",\s*\n\s*ids:\s*\[([\s\S]*?)\],?\s*\n\s*\}/g;
  while ((m = secRe.exec(src)) !== null) {
    const ids = [...m[2].matchAll(/"([^"]+)"/g)].map((x) => x[1]);
    sections.push({ title: m[1], ids });
  }
  return { glossary, sections };
}

export function helpBodyHtml(glossaryPath, esc) {
  const { glossary, sections } = parseGlossary(glossaryPath);
  const parts = [
    `<main>`,
    `<h1>Help &amp; Glossary for GCI Workflows — CiteAlpha</h1>`,
    `<p class="seo-speakable">CiteAlpha Help explains Guidance Credibility Index vocabulary, outcome labels, and desk workflows for Indian equity research. Factual research product — not investment advice.</p>`,
    `<p>Start with the <a href="${SITE}/tracker">GCI Screener</a>, <a href="${SITE}/about">About</a>, or the canonical <a href="${SITE}/blog/what-is-guidance-credibility-index">GCI definition</a>. Contact <a href="mailto:sales@citealpha.com">sales@citealpha.com</a> for an evaluation.</p>`,
  ];
  for (const sec of sections) {
    const rows = sec.ids.map((id) => glossary[id]).filter(Boolean);
    if (!rows.length) continue;
    parts.push(`<h2>${esc(sec.title)}</h2>`, `<dl>`);
    for (const row of rows) {
      parts.push(`<dt>${esc(row.term)}</dt><dd>${esc(row.tip)}</dd>`);
    }
    parts.push(`</dl>`);
  }
  parts.push(`</main>`);
  return parts.join("\n      ");
}

export function answersBodyHtml(data, esc) {
  const items = data.faq
    .map(
      (f) =>
        `<dt>${esc(f.question)}</dt><dd class="seo-speakable">${esc(f.answer)}</dd>`,
    )
    .join("\n        ");
  return `<main>
      <h1>CiteAlpha Answers — Guidance Credibility Index FAQ</h1>
      <p class="seo-speakable">Short answers about the Guidance Credibility Index (GCI) for Indian equity desks. Factual research — not investment advice.</p>
      <dl class="landing-faq">
        ${items}
      </dl>
      <p><a href="${SITE}/blog/what-is-guidance-credibility-index">Full GCI definition</a> · <a href="${SITE}/blog/sentiment-vs-guidance-delivery">GCI vs sentiment</a> · <a href="${SITE}/pilot">Request an evaluation</a></p>
    </main>`;
}

export function marketingBodyHtml(routePath, opts = {}) {
  const { glossaryPath, structuredData, esc, t } = opts;
  const hero = t
    ? {
        kicker: esc(t("landing.hero.kicker")),
        title: esc(t("landing.hero.title")),
        lede: esc(t("landing.hero.lede", { product: "CiteAlpha" })),
      }
    : null;
  const bodies = {
    "/": `<main>
      <p>${hero?.kicker ?? ""}</p>
      <h1 class="seo-speakable">${hero?.title ?? ""}</h1>
      <p class="seo-speakable">${hero?.lede ?? ""}</p>
      <p><a href="${SITE}/pilot"><strong>Request an evaluation</strong></a> · <a href="${SITE}/companies/infy">Or see a scored company (Infosys)</a></p>
      <p>Built for: <a href="${SITE}/products#desk-buy-side">Buy-side</a> · <a href="${SITE}/products#desk-sell-side">Sell-side research</a> · <a href="${SITE}/products#desk-quant">Quant / data</a> · <a href="${SITE}/products#desk-ir-compliance">IR &amp; compliance</a></p>
      <h2>Worked example: Infosys revenue growth guidance vs actuals</h2>
      <p>Each April, management guided full-year revenue growth in constant currency. Each year links two filed Infosys results releases (SEC Form 6-K): the one that set the guidance and the one that reported the actual.</p>
      <ul>
        <li>FY22 — guided 12–14%, actual 19.7% — <strong>exceeded</strong> (reported 2022-04-13). Guidance given 2021-04-14: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749121000030/exv99w01.htm">“Revenue growth guidance of 12%-14% in constant currency”</a> · Actual reported 2022-04-13: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749122000020/exv99w01.htm">“Revenues in CC terms grew by 19.7% YoY”</a></li>
        <li>FY23 — guided 13–15%, actual 15.4% — <strong>exceeded</strong> (reported 2023-04-13). Guidance given 2022-04-13: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749122000020/exv99w01.htm">“Revenue growth of 13%-15% in constant currency”</a> · Actual reported 2023-04-13: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749123000027/exv99w01.htm">“industry-leading growth of 15.4% in constant currency”</a></li>
        <li>FY24 — guided 4–7%, actual 1.4% — <strong>missed</strong> (reported 2024-04-18). Guidance given 2023-04-13: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749123000027/exv99w01.htm">“Revenue growth of 4%-7% in constant currency”</a> · Actual reported 2024-04-18: <a href="https://www.sec.gov/Archives/edgar/data/1067491/000106749124000016/exv99w01.htm">“Revenues in CC terms grew by 1.4% YoY”</a></li>
      </ul>
      <p>Infosys changed its guidance during each of these years: FY22 was raised three times to 19.5%–20.0%, FY23 to 16.0%–16.5%, and FY24 was cut to 1.5%–2.0%. We score against the original April guidance and show every revision, with its own filing, next to it. Against the final range, FY23 was a miss.</p>
      <p>Why doesn't a big beat score 100? GCI measures promise-keeping discipline, not forecast accuracy. Guidance of 12–14% against an actual of 19.7% scores about 62. A wide beat is scored on how reliable the promise was. A beat never scores below 60. A miss the same distance below the range scores 0. <a href="${SITE}/methodology">Full methodology</a> · <a href="${SITE}/companies/infy">Open the full Infosys evidence trail</a>.</p>
      <h2>What is a Guidance Credibility Index?</h2>
      <p>GCI is a 0–100 score of promise-keeping against a company's own quantified guidance — revenue bands, margins, volumes, capex. It tracks that promise, not forecast accuracy, sentiment, or share price. Each guided number gets one outcome once the period closes: met, exceeded, missed, dropped, or pending.</p>
      <h2>How we build a score</h2>
      <ol>
        <li><strong>Sources</strong> — NSE and BSE filings, company IR decks and guidance tables, earnings-call transcripts.</li>
        <li><strong>What counts as guidance</strong> — a number or range for a named metric and period, from a filing, results release or call transcript. Commentary without a number is left out. If guidance is raised or cut during the year, we score against the original number and show every revision next to it.</li>
        <li><strong>Verification</strong> — each guidance quote and each reported actual is kept with its document link and date. The row counts only when a fetch of both documents contains those quotes.</li>
        <li><strong>Scoring</strong> — GCI scores promise-keeping, not forecast accuracy. Each closed result earns 0–100 points for where it landed against its own guided range; misses lose points faster than beats. A wide range reaches 100 more easily than a tight one. Scores are not adjusted by sector. Open periods don't count until results are filed.</li>
        <li><strong>Independence</strong> — payment never influences a score or when it changes. Covered companies cannot buy, edit or delay their score.</li>
      </ol>
      <h2>Coverage today</h2>
      <ul>
        <li>Sensex companies plus early Nifty 50 names are scored when both quotes are found on the cited filings, once they have at least one closed result. Only these carry a GCI.</li>
        <li>A small set of companies have sample data for walkthroughs — not scored, not for citation.</li>
        <li>Other NSE/BSE listings can be browsed but are not yet scored.</li>
        <li>Point-in-time API for design partners: every data point carries the date it became known and whether it can be cited.</li>
      </ul>
      <h2>Explore the product</h2>
      <p>Each tool is labeled by what it does and who can use it today.</p>
      <ul>
        <li><a href="${SITE}/tracker"><strong>GCI Screener</strong></a> (Screen · Live · free preview) — screen covered companies by GCI score and change, with quality badges on every row.</li>
        <li><a href="${SITE}/desk"><strong>Analyst Workbench</strong></a> (Review &amp; export · Live · pilot and paid seats) — check extracted guidance against its source, then export cited reports and point-in-time data.</li>
        <li><a href="${SITE}/research"><strong>Filing Search</strong></a> (Search one company · Live · registered users) — search one company's filings and transcripts; answers only when a source can be cited.</li>
        <li><a href="${SITE}/sights"><strong>Disclosure Explorer</strong></a> (Compare companies · Live · browse free) — themes, street context, field evidence, compare, deep dive, and fundamentals. Each cell opens the filing.</li>
        <li><a href="${SITE}/rankings"><strong>Public Snapshot</strong></a> (Share · Live · public, no login) — public GCI snapshot; no recommendation labels.</li>
      </ul>
      <p><a href="${SITE}/answers">FAQ</a> · <a href="${SITE}/products#plans">Packages</a> · <a href="${SITE}/pilot">Request an evaluation</a> · <a href="${SITE}/trust">Trust Center</a></p>
    </main>`,
    "/pilot": `<main>
      <h1>Request a CiteAlpha evaluation</h1>
      <p class="seo-speakable">Time-boxed evaluation for Indian equity desks: the published scores with their filings, the Analyst Workbench, and Filing Search. Share firm details — we follow up within one business day. Not investment advice.</p>
      <p>The evaluation includes GCI Screener access, evidence trails with quality badges, and optional API discussion. Read the <a href="${SITE}/trust">Trust Center</a> and <a href="${SITE}/blog/what-is-guidance-credibility-index">GCI definition</a> before requesting.</p>
      <p>Contact: <a href="mailto:sales@citealpha.com">sales@citealpha.com</a> · <a href="${SITE}/products#plans">View packages</a></p>
    </main>`,
    "/press": `<main>
      <h1>CiteAlpha Press &amp; Brand — Ocotillo Innovation</h1>
      <p>CiteAlpha is a product of <strong>Ocotillo Innovation Private Limited</strong>. We publish the Guidance Credibility Index (GCI) — evidence-linked management guidance vs delivery for Indian equity desks. Factual research infrastructure; not investment advice.</p>
      <h2>Boilerplate</h2>
      <p cite="https://citealpha.com/blog/what-is-guidance-credibility-index">Guidance Credibility Index (GCI): an evidence-linked score of whether listed management delivered on quantified guidance versus subsequent actuals, with primary sources attached. CiteAlpha · citealpha.com · sales@citealpha.com</p>
      <h2>Key links</h2>
      <ul>
        <li><a href="${SITE}/blog/what-is-guidance-credibility-index">Canonical GCI definition</a></li>
        <li><a href="${SITE}/trust">Trust Center</a></li>
        <li><a href="${SITE}/llms.txt">llms.txt</a> · <a href="${SITE}/llms-full.txt">llms-full.txt</a> · <a href="${SITE}/ai.txt">AI use policy</a> · <a href="${SITE}/.well-known/ai-catalog.json">Agent catalog</a></li>
      </ul>
      <p>Media inquiries: <a href="mailto:sales@citealpha.com">sales@citealpha.com</a></p>
    </main>`,
    "/desk": `<main>
      <h1>Analyst Workbench: Review Guidance Before It Scores — GCI by CiteAlpha</h1>
      <p class="seo-speakable">Workspace where analysts check guidance extracted from filings, review new documents, and export cited reports and point-in-time data for Indian equity research. A short guided walkthrough opens on the first visit. Not investment advice.</p>
      <h2>What the Workbench is for</h2>
      <ul>
        <li>Open a company from the GCI Screener and check each guidance figure against the filing it came from.</li>
        <li>Accept or reject an extracted figure before it can enter a published score.</li>
        <li>Export cited reports, and point-in-time GCI history through the API, beside your market terminal.</li>
      </ul>
      <p><a href="${SITE}/tracker">Open GCI Screener</a> · <a href="${SITE}/products#features">Tier features</a> · <a href="${SITE}/products#plans">Packages</a></p>
    </main>`,
    "/research": `<main>
      <h1>Filing Search: Cite-Only Search of Indian Company Filings — CiteAlpha</h1>
      <p class="seo-speakable">Search IR filings and transcripts for one Indian company or across all covered companies, with India IR synonyms and cite-only answers that refuse invented actuals. Complements the GCI Screener. Not a price feed and not investment advice.</p>
      <h2>Capabilities</h2>
      <ul>
        <li>Search results filings, investor decks and call transcripts; every hit links to its source.</li>
        <li>Answers are given only when a filing can be cited; otherwise the search says the figure is not on file.</li>
        <li>A watchlist keeps the companies a desk follows in one place. No tips, no recommendations.</li>
      </ul>
      <p><a href="${SITE}/tracker">GCI Screener</a> · <a href="${SITE}/desk">Analyst Workbench</a> · <a href="${SITE}/help">Help &amp; glossary</a></p>
    </main>`,
    "/products": `<main>
      <h1>Products and Plans: GCI Screener, CiteAlpha Analyst, Filing Search &amp; API — CiteAlpha</h1>
      <p class="seo-speakable">What Indian equity desks get from CiteAlpha and how to buy it: GCI Screener, CiteAlpha Analyst, Filing Search, Disclosure Explorer, Analyst Workbench and the API, on a Pilot, a Desk seat or Enterprise API. Evidence-first research — not Buy/Hold/Sell recommendations.</p>
      <ul>
        <li><strong>GCI Screener</strong> — company GCI with the guidance and result filings behind every scored period.</li>
        <li><strong>CiteAlpha Analyst</strong> — cited workflows exported to Excel, PowerPoint or PDF in a desk's house style.</li>
        <li><strong>Filing Search and Disclosure Explorer</strong> — cite-only search and answers over NSE/BSE filings and transcripts.</li>
        <li><strong>Plans</strong> — Pilot (time-boxed), Desk seat, Enterprise API. Request a quote; there is no self-serve checkout.</li>
      </ul>
      <p><a href="${SITE}/pilot">Request an evaluation</a> · <a href="mailto:sales@citealpha.com">sales@citealpha.com</a> · <a href="${SITE}/developers">API reference</a></p>
    </main>`,
    "/rankings": `<main>
      <h1>Public Snapshot: GCI for Indian Listings — GCI by CiteAlpha</h1>
      <p class="seo-speakable">Public, no-login snapshot of Guidance Credibility Index scores for covered Indian listings. Evidence-linked delivery scores with honest quality badges — not investment recommendations.</p>
      <p>The snapshot shows the delivery record of every published GCI. A company is ranked only once it reaches the Established tier. Every scored row links to the guidance quote, the reported figure, its outcome, and both filings.</p>
      <p><a href="${SITE}/tracker">Full GCI Screener</a> · <a href="${SITE}/blog/hand-labeled-vs-demo-data">Hand-labeled vs demo data</a> · <a href="${SITE}/about">About GCI</a></p>
    </main>`,
    "/sights": `<main>
      <h1>Disclosure Explorer: Compare Indian Company Disclosures — CiteAlpha</h1>
      <p class="seo-speakable">Compare public disclosures across Indian listed companies: delivery themes, street context, field evidence, Compare Grid and deep dives. Not investment advice.</p>
      <ul>
        <li><a href="${SITE}/sights/themes"><strong>Delivery themes</strong></a> — recurring topics in management commentary, each linked to its filing.</li>
        <li><a href="${SITE}/sights/grid"><strong>Compare Grid</strong></a> — several companies side by side on the same disclosure questions.</li>
        <li>Search and cite-only answers across all covered companies are in <a href="${SITE}/research">Filing Search</a>.</li>
      </ul>
      <p><a href="${SITE}/tracker">GCI Screener</a> · <a href="${SITE}/products">Product portfolio</a></p>
    </main>`,
    "/analyst": `<main>
      <h1>CiteAlpha Analyst — Cited workflows for Indian equity desks</h1>
      <p class="seo-speakable">Cited research workflows for Indian equity desks, exported to Excel, PowerPoint, or PDF. Every claim stays tied to a filing. Not investment advice.</p>
      <ul>
        <li>Run a desk workflow on a covered company and keep each statement attached to its source.</li>
        <li>Export the same note to Excel, PowerPoint, or PDF in the desk's house style.</li>
        <li>Search across filings lives in <a href="${SITE}/research">Filing Search</a>. Scores live on the <a href="${SITE}/tracker">GCI Screener</a>.</li>
      </ul>
      <p><a href="${SITE}/products">Products and plans</a> · <a href="${SITE}/pilot">Request a pilot</a> · <a href="${SITE}/methodology">Methodology</a></p>
    </main>`,
    "/sights/themes": `<main>
      <h1>Delivery themes — Disclosure Explorer</h1>
      <p class="seo-speakable">Recurring topics in Indian company management commentary, each linked to the filing it came from. Not investment advice.</p>
      <p>Themes are a way to read the same disclosure idea across covered companies without leaving the source behind. Open a company dossier when you need the Guidance Credibility Index and the guidance-versus-result table.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/sights/grid">Compare Grid</a> · <a href="${SITE}/tracker">GCI Screener</a></p>
    </main>`,
    "/sights/street": `<main>
      <h1>Street context — Disclosure Explorer</h1>
      <p class="seo-speakable">Street context placed next to Indian company disclosures, with the source attached. Not investment advice.</p>
      <p>Use this page to read what was said in public beside the filing it refers to. CiteAlpha does not redistribute sell-side notes.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/research">Filing Search</a> · <a href="${SITE}/trust">Trust Center</a></p>
    </main>`,
    "/sights/field": `<main>
      <h1>Field evidence — Disclosure Explorer</h1>
      <p class="seo-speakable">Labeled guidance outcomes and the citations behind them, for Indian listed companies. Not investment advice.</p>
      <p>Each labeled outcome opens to the guidance statement and the later reported result. The company score, when one is published, is on the dossier.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/methodology">Methodology</a> · <a href="${SITE}/tracker">GCI Screener</a></p>
    </main>`,
    "/sights/grid": `<main>
      <h1>Compare Grid — Disclosure Explorer</h1>
      <p class="seo-speakable">The same disclosure question across covered Indian companies. Every cell is cited. Not investment advice.</p>
      <p>Ask one question of several names and read the cited answers side by side. Cells that cannot be sourced are refused rather than filled in.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/sights/deep-dive">Deep dive</a> · <a href="${SITE}/research">Filing Search</a></p>
    </main>`,
    "/sights/deep-dive": `<main>
      <h1>Deep dive — Disclosure Explorer</h1>
      <p class="seo-speakable">One topic across one Indian company's filings, with every claim cited. Not investment advice.</p>
      <p>A deep dive stays on a single company and a single topic. Claims that are not in the filings are left out.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/sights/themes">Delivery themes</a> · <a href="${SITE}/companies/infy">Infosys dossier</a></p>
    </main>`,
    "/sights/fundamentals": `<main>
      <h1>Fundamentals — Disclosure Explorer</h1>
      <p class="seo-speakable">Filing-backed fundamentals for one Indian company, beside its Guidance Credibility Index dossier. Not investment advice.</p>
      <p>The strip is a reading aid for the filings already on the dossier. The Guidance Credibility Index itself is the delivery record, not a forecast.</p>
      <p><a href="${SITE}/sights">Disclosure Explorer</a> · <a href="${SITE}/tracker">GCI Screener</a> · <a href="${SITE}/methodology">Methodology</a></p>
    </main>`,
    "/404": `<main>
      <h1>Page not found</h1>
      <p>That URL is not on CiteAlpha. Use the links below to reach the Guidance Credibility Index (GCI) product, documentation, or support pages.</p>
      <p><a href="${SITE}/tracker"><strong>Open GCI Screener</strong></a> · <a href="${SITE}/">Home</a> · <a href="${SITE}/about">About</a> · <a href="${SITE}/blog">Blog</a> · <a href="${SITE}/help">Help</a> · <a href="${SITE}/answers">FAQ</a> · <a href="${SITE}/pilot">Request an evaluation</a></p>
    </main>`,
    "/about": `<main>
      <h1>About CiteAlpha — GCI by Ocotillo Innovation</h1>
      <p>CiteAlpha publishes the Guidance Credibility Index (GCI): a 0–100 score of whether Indian listed management delivered on its quantified guidance. It is a delivery record, not a sentiment score, a rating, or a price terminal.</p>
      <h2>How GCI is built</h2>
      <ol>
        <li><strong>Collect</strong> — NSE and BSE filings, company results releases and investor decks, call transcripts.</li>
        <li><strong>Extract</strong> — a number or range for a named metric and period; a reviewer accepts each figure.</li>
        <li><strong>Match</strong> — the later reported figure for the same metric and period.</li>
        <li><strong>Score</strong> — each closed result is met, exceeded or missed, and rolls into the company GCI with a dated history.</li>
        <li><strong>Cite</strong> — every point opens to both filings.</li>
      </ol>
      <p><a href="${SITE}/tracker">Open GCI Screener</a> · <a href="${SITE}/blog/what-is-guidance-credibility-index">GCI definition</a></p>
    </main>`,
    "/tracker": `<main>
      <h1>GCI Screener: Guidance Credibility Scores for Indian Listed Companies</h1>
      <p class="seo-speakable">Screen Indian listed companies by Guidance Credibility Index. Coverage starts with the Sensex; a company carries a score only once its guidance quote and the later reported figure are both cited. Most NSE and BSE listings are shown as not yet scored.</p>
      <ul>
        <li>Each score with its confidence tier and the date it was last updated.</li>
        <li>Evidence trail: guidance quote, reported figure, outcome, and both filings.</li>
        <li>A data-quality badge on every row, so sample data is never mistaken for a score.</li>
      </ul>
      <p><a href="${SITE}/rankings">Public Snapshot</a> · <a href="${SITE}/desk">Analyst Workbench</a> · <a href="${SITE}/blog/what-is-guidance-credibility-index">What is GCI?</a></p>
    </main>`,
    "/trust": `<main>
      <h1>Trust Center for Institutional Buyers — CiteAlpha</h1>
      <p>Security, legal, and citation posture for desks evaluating CiteAlpha (Ocotillo Innovation Private Limited). Honest status — not marketing over-claims.</p>
      <ul>
        <li>Product identity and sales@citealpha.com contact.</li>
        <li>Claim hygiene: evidence trails required; demo vs hand-labeled badged.</li>
        <li>AI use policy: <a href="${SITE}/ai.txt">ai.txt</a> · <a href="${SITE}/llms.txt">llms.txt</a> · <a href="${SITE}/llms-full.txt">llms-full.txt</a> · <a href="${SITE}/.well-known/ai-catalog.json">Agent catalog</a></li>
      </ul>
      <p><a href="${SITE}/products#plans">Packages</a> · <a href="${SITE}/blog/trust-center-checklist-institutional-buyers">Buyer checklist</a></p>
    </main>`,
  };

  if (routePath === "/help" && glossaryPath && esc) {
    return helpBodyHtml(glossaryPath, esc);
  }
  if (routePath === "/answers" && structuredData && esc) {
    return answersBodyHtml(structuredData, esc);
  }
  return bodies[routePath] || null;
}

/** Each <loc> is a page; its <image:image> entries are the images that page shows or shares. */
export function buildImageSitemap(posts, dossiers = []) {
  const urls = [
    {
      loc: `${SITE}/`,
      images: [{ loc: `${SITE}/og-image.png`, title: "CiteAlpha Guidance Credibility Index" }],
    },
  ];
  for (const post of posts) {
    urls.push({
      loc: `${SITE}/blog/${post.slug}`,
      images: [{ loc: `${SITE}/og-image.png`, title: post.title }],
    });
  }
  for (const d of dossiers) {
    urls.push({
      loc: `${SITE}${d.path}`,
      images: [{ loc: `${SITE}/api/og/${d.id}.png`, title: `${d.name} Guidance Credibility Index (GCI)` }],
    });
  }
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
  ];
  for (const u of urls) {
    lines.push("  <url>", `    <loc>${u.loc}</loc>`);
    for (const img of u.images) {
      lines.push("    <image:image>", `      <image:loc>${img.loc}</image:loc>`, `      <image:title>${escXml(img.title)}</image:title>`, "    </image:image>");
    }
    lines.push("  </url>");
  }
  lines.push("</urlset>");
  return `${lines.join("\n")}\n`;
}

export function buildRssFeed(posts) {
  const items = posts
    .slice()
    .sort((a, b) => String(b.updated || b.published).localeCompare(String(a.updated || a.published)))
    .map((p) => {
      const link = `${SITE}/blog/${p.slug}`;
      return `    <item>
      <title>${escXml(p.title)}</title>
      <link>${link}</link>
      <guid isPermaLink="true">${link}</guid>
      <pubDate>${toRfc822(p.published)}</pubDate>
      <description>${escXml(p.description)}</description>
    </item>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>CiteAlpha Research Blog</title>
    <link>${SITE}/blog</link>
    <description>Articles on guidance credibility, Indian earnings evidence trails, and institutional workflows — without Buy/Hold tips.</description>
    <language>en-IN</language>
    <atom:link href="${SITE}/rss.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>
`;
}

function escXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function toRfc822(isoDate) {
  const d = new Date(`${isoDate}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toUTCString();
}

/** Opt-in (INDEXNOW=1): a build-time ping would announce pages before they are deployed. */
export async function pingIndexNow(urls) {
  if (process.env.INDEXNOW !== "1" || process.env.SKIP_INDEXNOW === "1") return;
  const host = "citealpha.com";
  const keyLocation = `${SITE}/${INDEXNOW_KEY}.txt`;
  const body = JSON.stringify({
    host,
    key: INDEXNOW_KEY,
    keyLocation,
    urlList: urls.slice(0, 100),
  });
  const endpoints = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
  ];
  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body,
      });
      console.log("indexnow ping:", endpoint, res.status, res.statusText);
    } catch (err) {
      console.warn("indexnow ping skipped:", endpoint, err.message);
    }
  }
}
