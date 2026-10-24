import { getBlogMeta, listBlogMeta } from "./blogMeta";
import dossierSnap from "./seoDossiers.json";
import seoRoutes from "./seoRoutes.json";
import {
  blogSeoTitle,
  extraJsonLdForPath,
  websiteJsonLd,
  dossierDatasetJsonLd,
  breadcrumbJsonLd,
  SITE,
} from "./seoJsonLd";
import { formatDossierDate, formatScore } from "./score";

export type SeoConfig = {
  path: string;
  title: string;
  description: string;
  robots?: string;
  type?: "website" | "article";
  jsonLd?: Record<string, unknown>;
  extraJsonLd?: Record<string, unknown>[];
  ogImage?: string;
  ogImageAlt?: string;
};

type SeoRouteEntry = {
  path: string;
  title: string;
  description: string;
  robots?: string;
};

const DEFAULT: SeoConfig = {
  path: "/",
  title: "GCI by CiteAlpha — Guidance Credibility Index",
  description:
    "CiteAlpha GCI by Ocotillo Innovation Private Limited — management guidance vs delivery for Indian equity desks. Factual research product; not investment advice.",
};

const STATIC: Record<string, Omit<SeoConfig, "path">> = Object.fromEntries(
  (seoRoutes as SeoRouteEntry[]).map(({ path, ...rest }) => [path, rest]),
);

type DossierSnap = {
  id: string;
  title: string;
  description: string;
  path: string;
};

/** Hand-labeled dossiers already published for crawlers. First paint must match that HTML. */
const DOSSIER_BY_ID = new Map<string, DossierSnap>(
  ((dossierSnap as { dossiers?: DossierSnap[] }).dossiers ?? []).map((row) => [row.id, row]),
);

function cleanPath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) return pathname.replace(/\/+$/, "");
  return pathname;
}

function blogIndexJsonLd(): Record<string, unknown> {
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
    blogPost: listBlogMeta().map((p) => ({
      "@type": "BlogPosting",
      headline: p.title,
      url: `${SITE}/blog/${p.slug}`,
      datePublished: p.published,
      description: p.description,
    })),
  };
}

function blogPostJsonLd(post: NonNullable<ReturnType<typeof getBlogMeta>>): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.description,
    datePublished: post.published,
    dateModified: post.updated ?? post.published,
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
  };
}

/** Resolve SEO config for a React Router pathname. */
export function resolveSeo(pathname: string): SeoConfig {
  const path = cleanPath(pathname);

  if (path.startsWith("/blog/") && path !== "/blog") {
    const slug = path.slice("/blog/".length).replace(/\/$/, "");
    const post = getBlogMeta(slug);
    if (post) {
      const title = blogSeoTitle(slug, post.title);
      return {
        path: `/blog/${post.slug}`,
        title,
        description: post.description,
        type: "article",
        ogImageAlt: `${post.title} — CiteAlpha Research Blog`,
        jsonLd: blogPostJsonLd(post),
        extraJsonLd: extraJsonLdForPath(`/blog/${post.slug}`, title),
      };
    }
  }

  if (path.startsWith("/companies/")) {
    const id = path.slice("/companies/".length);
    const published =
      id && !id.includes("/")
        ? DOSSIER_BY_ID.get(id) ?? DOSSIER_BY_ID.get(id.toLowerCase())
        : undefined;
    if (published) {
      return {
        path: published.path,
        title: published.title,
        description: published.description,
        robots: "index,follow",
        ogImage: `${SITE}/api/og/${id}.png`,
        ogImageAlt: published.title,
      };
    }
    return {
      path,
      title: "Company GCI Dossier — CiteAlpha",
      description:
        "Company Guidance Credibility Index dossier with evidence trail. Factual research; not investment advice.",
      robots: "noindex,follow",
    };
  }

  if (path.startsWith("/c/")) {
    return {
      path,
      title: "Citation — CiteAlpha",
      description: "Evidence citation for a Guidance Credibility Index score point.",
      robots: "noindex,follow",
    };
  }

  if (path.startsWith("/sights")) {
    const hit = STATIC[path];
    if (!hit) {
      return {
        path,
        title: "Disclosure Explorer — CiteAlpha",
        description:
          "Compare public disclosures across Indian listed companies. Not investment advice.",
        robots: "noindex,follow",
      };
    }
    const title = hit.title;
    return {
      path,
      ...hit,
      ogImageAlt: title,
      extraJsonLd: extraJsonLdForPath(path, title),
    };
  }

  const staticHit = STATIC[path];
  if (staticHit) {
    const seo: SeoConfig = {
      path,
      ...staticHit,
      ogImageAlt: staticHit.title,
    };
    if (path === "/blog") {
      seo.jsonLd = blogIndexJsonLd();
    } else if (path === "/") {
      seo.jsonLd = websiteJsonLd();
    }
    seo.extraJsonLd = extraJsonLdForPath(path, staticHit.title);
    return seo;
  }

  return {
    ...DEFAULT,
    path,
    robots: "noindex,follow",
  };
}

/** Per-company SEO once the dossier payload is loaded (W5.1). */
export function dossierSeo(input: {
  id: string;
  name: string;
  gci: number | null;
  asOf?: string | null;
  dataQuality: string;
  recordSentence: string;
}): SeoConfig {
  const path = `/companies/${input.id}`;
  const asOfLabel = input.asOf ? formatDossierDate(input.asOf) : "";
  const scoreBit =
    input.gci == null ? "" : ` ${formatScore(input.gci)}`;
  const title = asOfLabel
    ? `${input.name} — Guidance Credibility Index (GCI)${scoreBit} · Data as of ${asOfLabel}`
    : `${input.name} — Guidance Credibility Index (GCI)${scoreBit}`.trim();
  const description = [
    input.recordSentence,
    asOfLabel ? `Data as of ${asOfLabel}.` : "",
    "Not investment advice.",
  ]
    .filter(Boolean)
    .join(" ");
  const indexable = input.dataQuality === "hand_labeled";
  const crumbs = breadcrumbJsonLd(path, input.name);
  return {
    path,
    title,
    description,
    robots: indexable ? "index,follow" : "noindex,follow",
    ogImage: `${SITE}/api/og/${input.id}.png`,
    ogImageAlt: title,
    jsonLd: dossierDatasetJsonLd({
      path,
      name: input.name,
      description,
      asOf: input.asOf,
      gci: input.gci,
    }),
    extraJsonLd: crumbs ? [crumbs] : [],
  };
}
