import structured from "./seo-structured-data.json";

export const SITE = structured.site;

type JsonLd = Record<string, unknown>;

type Founder = { name: string; jobTitle?: string; sameAs?: string[] };
type OrgData = {
  name: string;
  legalName: string;
  email: string;
  identifier?: Record<string, string>;
  address?: Record<string, string>;
  parentOrganization?: Record<string, string>;
  socialProfiles?: string[];
  founders?: Founder[];
};

const ORG = structured.org as OrgData;

/** Profiles on other sites only; a citealpha.com URL here tells a search engine nothing. */
export function externalUrls(urls: string[] | undefined): string[] {
  return (urls ?? []).filter((u) => Boolean(u) && u.startsWith("https://") && !u.startsWith(SITE));
}

export const SOCIAL_PROFILES = externalUrls(ORG.socialProfiles);

/** Same output as orgEntityFields in scripts/seo-shared.mjs. */
function orgEntityFields(): JsonLd {
  const founders = (ORG.founders ?? [])
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
    ...(ORG.identifier ? { identifier: { "@type": "PropertyValue", ...ORG.identifier } } : {}),
    ...(ORG.address ? { address: { "@type": "PostalAddress", ...ORG.address } } : {}),
    ...(ORG.parentOrganization ? { parentOrganization: { "@type": "Organization", ...ORG.parentOrganization } } : {}),
    ...(founders.length ? { founder: founders } : {}),
  };
}

export function orgJsonLd(): JsonLd {
  const sameAs = SOCIAL_PROFILES;
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: ORG.name,
    legalName: ORG.legalName,
    url: SITE,
    logo: `${SITE}/citealpha-logo.png`,
    description:
      "Guidance Credibility Index (GCI) — evidence-linked management guidance vs delivery for Indian equity desks. Not investment advice.",
    email: ORG.email,
    ...orgEntityFields(),
    ...(sameAs.length ? { sameAs } : {}),
  };
}

export function websiteJsonLd(): JsonLd {
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
      name: ORG.name,
      legalName: ORG.legalName,
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

/** Service, not SoftwareApplication: plans are quote-only, and an Offer without a price fails validation. */
export function serviceJsonLd(): JsonLd {
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
      name: ORG.name,
      legalName: ORG.legalName,
    },
  };
}

export function faqJsonLd(): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: structured.faq.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };
}

export function howToGciJsonLd(): JsonLd {
  const howTo = structured.howTo;
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

export function speakableJsonLd(pageUrl: string): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    url: pageUrl,
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: structured.speakable.cssSelector,
    },
  };
}

/** Breadcrumb trail for nested marketing / blog URLs. */
export function breadcrumbJsonLd(pathname: string, pageTitle: string): JsonLd | null {
  if (pathname === "/" || pathname.startsWith("/login") || pathname.startsWith("/register")) {
    return null;
  }
  const items: { name: string; path: string }[] = [{ name: "Home", path: "/" }];
  if (pathname.startsWith("/blog/")) {
    items.push({ name: "Blog", path: "/blog" });
    items.push({ name: pageTitle.replace(/ — CiteAlpha.*$/, ""), path: pathname });
  } else if (pathname.startsWith("/companies/")) {
    items.push({ name: "GCI Screener", path: "/tracker" });
    items.push({ name: pageTitle.replace(/ — CiteAlpha.*$/, ""), path: pathname });
  } else if (pathname.startsWith("/about/")) {
    items.push({ name: "About", path: "/about" });
    items.push({ name: pageTitle.replace(/ — CiteAlpha$/, ""), path: pathname });
  } else if (pathname.startsWith("/sights/")) {
    items.push({ name: "Disclosure Explorer", path: "/sights" });
    items.push({ name: pageTitle.replace(/ — CiteAlpha$/, ""), path: pathname });
  } else {
    items.push({ name: pageTitle.replace(/ — CiteAlpha.*$/, ""), path: pathname });
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

/** Extra JSON-LD blocks keyed by pathname (SPA + prerender parity). */
export function extraJsonLdForPath(pathname: string, pageTitle?: string): JsonLd[] {
  const blocks: JsonLd[] = [];
  // FAQPage lives on /answers only: the same questions marked up on several URLs compete with each other.
  if (pathname === "/") {
    blocks.push(orgJsonLd(), serviceJsonLd());
  } else if (pathname === "/about") {
    blocks.push(howToGciJsonLd());
  } else if (pathname === "/answers") {
    blocks.push(faqJsonLd());
  } else if (pathname === "/blog/what-is-guidance-credibility-index") {
    blocks.push(speakableJsonLd(`${SITE}/blog/what-is-guidance-credibility-index`));
  } else if (pathname === "/blog") {
    blocks.push(orgJsonLd());
  }
  if (pageTitle) {
    const crumbs = breadcrumbJsonLd(pathname, pageTitle);
    if (crumbs) blocks.push(crumbs);
  }
  return blocks;
}

const TIER_NAME: Record<string, string> = {
  provisional: "Provisional",
  established: "Established",
  deep: "Deep",
};

/** Same shape as `dossierDatasetJsonLd` in scripts/seo-shared.mjs (prerender). */
export function dossierDatasetJsonLd(input: {
  path: string;
  id: string;
  name: string;
  description: string;
  asOf?: string | null;
  gci: number | null;
  tier?: string | null;
}): JsonLd {
  const org = { "@type": "Organization", name: ORG.name, legalName: ORG.legalName, url: SITE };
  const measured: JsonLd[] = [
    {
      "@type": "PropertyValue",
      name: "Guidance Credibility Index (GCI)",
      minValue: 0,
      maxValue: 100,
      ...(input.gci != null ? { value: input.gci } : {}),
    },
  ];
  if (input.tier && TIER_NAME[input.tier]) {
    measured.push({ "@type": "PropertyValue", name: "Confidence tier", value: TIER_NAME[input.tier] });
  }
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `${input.name} Guidance Credibility Index (GCI)`,
    description: input.description,
    url: `${SITE}${input.path}`,
    creator: org,
    publisher: org,
    keywords: ["Guidance Credibility Index", "management guidance", "Indian listed companies", input.name],
    spatialCoverage: "India",
    measurementTechnique: `Quantified management guidance compared with the later reported result, each cited to its filing. Method: ${SITE}/methodology`,
    variableMeasured: measured,
    distribution: [
      {
        "@type": "DataDownload",
        encodingFormat: "application/json",
        contentUrl: `${SITE}/api/v1/companies/${input.id}/gci`,
      },
    ],
    license: `${SITE}/terms`,
    isAccessibleForFree: true,
    ...(input.asOf ? { dateModified: String(input.asOf).slice(0, 10) } : {}),
  };
}

export function blogSeoTitle(slug: string, title: string): string {
  if (slug === "what-is-guidance-credibility-index") {
    return "What is a Guidance Credibility Index (GCI)? — CiteAlpha";
  }
  return `${title} — CiteAlpha Blog`;
}

export function ogImageAltForPath(pathname: string, title: string): string {
  if (pathname === "/") {
    return "CiteAlpha — Guidance Credibility Index by Ocotillo Innovation Private Limited";
  }
  if (pathname.startsWith("/blog/")) {
    return `${title} — CiteAlpha Research Blog`;
  }
  return `${title} — CiteAlpha`;
}

export { structured as SEO_STRUCTURED };
