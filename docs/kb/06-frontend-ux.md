# 06 — Frontend UX

## Surfaces

| Page | File | Job |
|---|---|---|
| GCI Screener (`/tracker`) | `HomePage.tsx` | Universe table first; search/sort; alerts rail |
| Dossier | `CompanyDetailPage.tsx` | **Evidence-first**; sticky TOC; toast on review. The evidence table and promise-thread columns open on the latest period, with period and metric filters on the table. Promise threads are a heatmap: cumulative GCI, actual, revisions (expand for each step), opening guidance; latest year on the left. The thread chart reads older to newer, with the revision range as a bar and GCI on a 0–100 scale. A source click opens the filing beside the highlighted extract. Period documents and the period matrix stay latest period first |
| Analyst Workbench (`/desk`) | `DeskPage.tsx` + `DeskConsole.tsx` | Sticky company + `?tab=` · **Console** = multi-pane GCI terminal |
| Filing Search (`/research`) | `ResearchPage.tsx` | Modes via `?tab=`; cite-only chat |
| Package / Help | `PackagePage`, `HelpPage` | Tours, glossary, source policy, and captures of the screener, search, evidence, and period documents |
| About / Trust | `AboutPage`, `TrustPage` | Company story · procurement posture |
| Nav | `NavMenu.tsx` | Jobs, left to right: GCI Screener · Research (Filing Search, CiteAlpha Analyst, Public Snapshot) · Workspace (Analyst Workbench, Disclosure Explorer, Financial Ninja, Holdings) · Pricing · Learn (Workflows, methodology, changelog, blog, help, FAQ, about, Trust, API, status, press). Billing stays in the account menu. An admin bar (`AdminMenuBar`) sits under this nav only for an organisation owner, organisation admin, or platform role. |
| Blog | `BlogIndexPage`, `BlogPostPage` | SEO research articles (`/blog`) |

## Next development

Role seats and the screens they open are specified in `docs/BRD_ROLES.md`, `docs/PRD_ROLES.md`, and `docs/TRD_ROLES.md`. The 28 Oct 2026 walk that fed them is `docs/PLAN_ROLE_UX.md`. Density, the year pivot, and the docked citation pane stay in `docs/prd/PRD_TERMINAL.md`. This page stays the map of what ships today.

## Design rules (institutional)

1. One composition per viewport — not widget soup.
2. Brand **CiteAlpha** is a hero-level mark in the shell.
3. Fonts: Source Serif 4 + IBM Plex Sans (not Inter/Roboto defaults).
4. Paper/ink palette — no purple SaaS glow, no Buy/Hold chrome.
5. Cards only for interactive containers; prefer panels + typography.
6. Always show **level + Δ** (MoM/QoQ/YoY/PoP) when history exists.
7. Quality badges always visible (Hand-labeled vs Demo).
8. SEBI-oriented disclaimer on GCI and vernacular surfaces.

## Shared components

`EvidenceTable`, `ChangeChip`/`ChangeTriple`, `TabBar`, `CompanyPicker`, `QualityBadge`, `ScoreReveal`, `Toast`, `Skeleton`, `InfoTip`, `Disclaimer`, `CitationCard`, `SourceViewer` (citation click → highlighted document).

## API

Only via `lib/api.ts`. Styles: `styles.css` design tokens.

## Prompt for rebuilds

`docs/prompts/PROFESSIONAL_SITE_PROMPT.md`
