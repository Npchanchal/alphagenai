/** Canonical legal entity for copyright / ownership chrome. */
export const LEGAL_ENTITY = "Ocotillo Innovation Private Limited";
export const PRODUCT_NAME = "CiteAlpha";
export const TAGLINE = "Beyond Guidance. Into Credibility.";
export const CONTACT_EMAIL = "sales@citealpha.com";
export const PUBLIC_DOMAIN = "citealpha.com";
/** Editorial byline for public research blog posts. */
export const BLOG_BYLINE = "CiteAlpha Research · Ocotillo Innovation Private Limited";

export function copyrightLine(year = new Date().getFullYear()): string {
  return `© ${year} ${LEGAL_ENTITY}. All rights reserved. ${PRODUCT_NAME} is a product of ${LEGAL_ENTITY}.`;
}

export function counselApproved(status?: string | null): boolean {
  return status === "counsel_approved";
}
