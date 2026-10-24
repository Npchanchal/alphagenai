import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { ogLocaleFor } from "../i18n/languages";
import { resolveSeo } from "../lib/seo";
import { getSeoOverride, subscribeSeoOverride } from "../lib/seoOverride";
import { SITE } from "../lib/seoJsonLd";

function upsertMeta(attr: "name" | "property", key: string, content: string) {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.content = content;
}

function upsertLink(rel: string, href: string, extra?: Record<string, string>) {
  let selector = `link[rel="${rel}"]`;
  if (extra?.hreflang) {
    selector = `link[rel="${rel}"][hreflang="${extra.hreflang}"]`;
  } else if (extra?.type) {
    selector = `link[rel="${rel}"][type="${extra.type}"]`;
  } else if (rel === "canonical") {
    selector = `link[rel="canonical"]`;
  }
  let el = document.head.querySelector(selector) as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.rel = rel;
    if (extra) {
      for (const [k, v] of Object.entries(extra)) el.setAttribute(k, v);
    }
    document.head.appendChild(el);
  }
  el.href = href;
}

function upsertJsonLd(id: string, data: Record<string, unknown> | null) {
  const existing = document.getElementById(id);
  if (!data) {
    existing?.remove();
    return;
  }
  let el = existing as HTMLScriptElement | null;
  if (!el) {
    el = document.createElement("script");
    el.type = "application/ld+json";
    el.id = id;
    document.head.appendChild(el);
  }
  el.textContent = JSON.stringify(data);
}

/** Per-route title, description, canonical, Open Graph, and JSON-LD for SPA SEO. */
export default function SeoHead() {
  const { pathname } = useLocation();
  const { lang } = useI18n();
  const [overrideTick, setOverrideTick] = useState(0);

  useEffect(() => subscribeSeoOverride(() => setOverrideTick((n) => n + 1)), []);

  useEffect(() => {
    const base = resolveSeo(pathname);
    const over = getSeoOverride();
    const seo = over && over.path === pathname ? { ...base, ...over } : base;
    const url = `${SITE}${seo.path === "/" ? "/" : seo.path}`;
    const ogImage = seo.ogImage ?? `${SITE}/og-image.png`;

    document.documentElement.lang = lang === "en" ? "en-IN" : lang;

    document.title = seo.title;

    const existingRobots =
      document.head.querySelector('meta[name="robots"]')?.getAttribute("content") ?? "";
    const canonicalNow =
      document.head.querySelector('link[rel="canonical"]')?.getAttribute("href") ?? "";
    const expectedUrl = `${SITE}${seo.path === "/" ? "/" : seo.path}`;
    const sameDocument = canonicalNow === expectedUrl || canonicalNow === `${expectedUrl}/`;
    let robots = seo.robots ?? "index,follow";
    // Prerendered dossiers are index,follow in the first HTML byte. Do not stamp noindex
    // over that tag before the company payload arrives — Google keeps the rendered robots tag.
    if (
      !(over && over.path === pathname) &&
      sameDocument &&
      pathname.startsWith("/companies/") &&
      existingRobots.includes("index,follow") &&
      !existingRobots.includes("noindex") &&
      robots.includes("noindex")
    ) {
      robots = "index,follow";
    }

    upsertMeta("name", "description", seo.description);
    upsertMeta("name", "robots", robots);
    upsertMeta("property", "og:type", seo.type ?? "website");
    upsertMeta("property", "og:site_name", "CiteAlpha");
    upsertMeta("property", "og:title", seo.title);
    upsertMeta("property", "og:description", seo.description);
    upsertMeta("property", "og:url", url);
    upsertMeta("property", "og:image", ogImage);
    upsertMeta("property", "og:image:alt", seo.ogImageAlt ?? seo.title);
    upsertMeta("property", "og:locale", ogLocaleFor(lang));
    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:title", seo.title);
    upsertMeta("name", "twitter:description", seo.description);
    upsertMeta("name", "twitter:image", ogImage);

    const twitterSite = import.meta.env.VITE_TWITTER_SITE?.trim();
    if (twitterSite) {
      upsertMeta("name", "twitter:site", twitterSite.startsWith("@") ? twitterSite : `@${twitterSite}`);
    }

    upsertLink("canonical", url);
    upsertLink("alternate", url, { hreflang: "x-default" });
    upsertLink("alternate", url, { hreflang: "en-IN" });
    upsertLink("alternate", `${SITE}/rss.xml`, { type: "application/rss+xml", title: "CiteAlpha Research Blog" });

    const gsc = import.meta.env.VITE_GSC_VERIFICATION?.trim();
    if (gsc) upsertMeta("name", "google-site-verification", gsc);

    const bing = import.meta.env.VITE_BING_VERIFICATION?.trim();
    if (bing) upsertMeta("name", "msvalidate.01", bing);

    upsertJsonLd("seo-jsonld-page", seo.jsonLd ?? null);

    document.querySelectorAll('script[id^="seo-jsonld-extra-"]').forEach((el) => el.remove());
    (seo.extraJsonLd ?? []).forEach((block, i) => {
      upsertJsonLd(`seo-jsonld-extra-${i}`, block);
    });
    const extraCount = seo.extraJsonLd?.length ?? 0;
    for (let i = extraCount; i < 8; i++) {
      upsertJsonLd(`seo-jsonld-extra-${i}`, null);
    }
  }, [pathname, lang, overrideTick]);

  return null;
}
