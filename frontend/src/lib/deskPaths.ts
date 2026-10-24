/**
 * Persona pathways under Products — India equity desks, not industry verticals.
 * Shared by Products page + Products nav submenu.
 */
export type DeskGuide = {
  id: string;
  /** Anchor id on /products (desk-{id}) */
  hash: string;
  title: string;
  blurb: string;
  /** SKU names in portfolio order relevance */
  skus: string[];
  primary: { to: string; label: string };
  links: { to: string; label: string }[];
};

export const DESK_GUIDES: DeskGuide[] = [
  {
    id: "buy-side",
    hash: "desk-buy-side",
    title: "Buy-side",
    blurb:
      "Screen chronic guidance misses and drill into evidence — GCI first, Radar for revisions.",
    skus: ["Score", "Radar"],
    primary: { to: "/tracker", label: "Open GCI Screener" },
    links: [
      { to: "/tracker", label: "Radar alerts in the GCI Screener" },
      { to: "/rankings", label: "Public Snapshot" },
    ],
  },
  {
    id: "sell-side",
    hash: "desk-sell-side",
    title: "Sell-side / research ops",
    blurb:
      "Cite primary guidance↔actuals in notes; Filing Search for cite-only answers.",
    skus: ["Cite", "Score"],
    primary: { to: "/research", label: "Open Filing Search" },
    links: [
      { to: "/sights", label: "Disclosure Explorer" },
      { to: "/tracker", label: "GCI Screener" },
      { to: "/analyst", label: "CiteAlpha Analyst" },
    ],
  },
  {
    id: "quant",
    hash: "desk-quant",
    title: "Quant / data",
    blurb:
      "Point-in-time guidance outcomes and factor export — backtestable, not a tip sheet.",
    skus: ["Data", "Score"],
    primary: { to: "/developers", label: "API and data exports" },
    links: [
      { to: "/products#plans", label: "Enterprise API plan" },
      { to: "/help", label: "API help" },
    ],
  },
  {
    id: "ir-compliance",
    hash: "desk-ir-compliance",
    title: "IR / compliance / credit",
    blurb:
      "Promise ledger and IR Mirror — what was committed, status, and peer context. A subscription never changes how a company is scored or when its score updates.",
    skus: ["Ledger", "Radar"],
    primary: { to: "/tracker", label: "Open a company ledger from the GCI Screener" },
    links: [
      { to: "/analyst", label: "Monitors in CiteAlpha Analyst" },
      { to: "/trust", label: "Trust Center" },
    ],
  },
];
