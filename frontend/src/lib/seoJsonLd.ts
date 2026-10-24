import structured from "./seo-structured-data.json";

export const SITE = structured.site;

type JsonLd = Record<string, unknown>;

const ORG = structured.org;

function orgSameAs(): string[] {
  const social = (ORG as { socialProfiles?: string[] }).socialProfiles ?? [];
  return [...ORG.sameAs, ...social.filter(Boolean)];
}

export function orgJsonLd(): JsonLd {
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
    sameAs: orgSameAs(),
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

export function softwareJsonLd(): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "CiteAlpha Guidance Credibility Index",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    url: SITE,
    description:
      "Evidence-linked Guidance Credibility Index (GCI) for Indian equity desks. Factual research product; not investment advice.",
    offers: {
      "@type": "Offer",
      url: `${SITE}/package`,
      priceCurrency: "INR",
      availability: "https://schema.org/OnlineOnly",
    },
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
  if (pathname === "/") {
    blocks.push(orgJsonLd(), softwareJsonLd(), faqJsonLd());
  } else if (pathname === "/about") {
    blocks.push(howToGciJsonLd());
  } else if (pathname === "/answers" || pathname === "/help") {
    blocks.push(faqJsonLd());
  } else if (pathname === "/blog/what-is-guidance-credibility-index") {
    blocks.push(faqJsonLd(), speakableJsonLd(`${SITE}/blog/what-is-guidance-credibility-index`));
  } else if (pathname === "/blog") {
    blocks.push(orgJsonLd());
  }
  if (pageTitle) {
    const crumbs = breadcrumbJsonLd(pathname, pageTitle);
    if (crumbs) blocks.push(crumbs);
  }
  return blocks;
}

export function dossierDatasetJsonLd(input: {
  path: string;
  name: string;
  description: string;
  asOf?: string | null;
  gci: number | null;
}): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `${input.name} Guidance Credibility Index (GCI)`,
    description: input.description,
    url: `${SITE}${input.path}`,
    creator: {
      "@type": "Organization",
      name: ORG.name,
      legalName: ORG.legalName,
    },
    variableMeasured: "Guidance Credibility Index",
    license: `${SITE}/terms`,
    isAccessibleForFree: true,
    ...(input.asOf ? { dateModified: String(input.asOf).slice(0, 10) } : {}),
    ...(input.gci != null
      ? {
          additionalProperty: {
            "@type": "PropertyValue",
            name: "GCI",
            value: input.gci,
          },
        }
      : {}),
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
