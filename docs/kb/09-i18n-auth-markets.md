# 09 — i18n, Auth & Markets

## Markets

- Deep GCI: **IN + SENSEX** (and labeled Sensex names).
- Other markets/indexes may be **scaffold** — show honest banner; do not fake GCI depth.
- Preferences: default market/index via session prefs.
- **Site-wide market picker** (2026-10-28): topbar `MarketSelect` and the Screener market select both write `default_market` + `default_index` through `useMarketChoice` (`frontend/src/lib/markets.ts`); Screener, Filing Search, Workbench and Account read it. Pickers offer only markets and indexes flagged `listed` by `/api/markets` (`markets.market_is_listed` / `index_is_listed`): since 2026-10-29 all twelve markets: **IN** (all India indexes), **US** (S&P 500), **GB** (FTSE 100), **JP** (Nikkei 225), **HK** (Hang Seng), **CN** (CSI 300), **EU** (Euro Stoxx 50, DAX, CAC 40), **SG** (STI), **AU** (S&P/ASX 200), **KR** (KOSPI 200), **BR** (Ibovespa), **CA** (S&P/TSX 60). DJI, NDX, TOPIX and SSEC hold anchor tags only and stay unlisted. A market without a listing file falls back to constituent pads and never reaches a picker. Companies outside India show as listed, not scored, until both quotes check out in their own filings.
- **Market scope per plan** (2026-10-28): choosing a market in the picker never changes access. A seat whose plan does not cover the market sees it marked "outside plan" ("part in plan" for one Indian exchange); scores stay readable and seat tools show `PlanScopeNotice`. Rules and matrix: `docs/kb/13-commercial.md` and `docs/prd/PRD_COMMERCIAL.md` §3.2.

## i18n

- UI strings: `frontend/src/i18n/`
- Vernacular GCI blurbs: `GET /api/vernacular/{id}?lang=` (en/hi/ta/gu/mr/ja templates)
- Always pair vernacular with disclaimer.

## Auth

- Register / login / guest continue — **Terms + Privacy acceptance required** (`accept_terms`).
- Public register is **B2B desk only** (creates a Pilot org from `org_name`). `account_type=retail` returns 403 until counsel attests `sebi_retail` (W8.1 / D1, 2026-09-29).
- Write APIs: session Bearer **or** `X-API-Key` (org-scoped). Effective access = **intersection** of org plan features and user role (`GET /api/entitlements/me`).
- Plans: `guest` · `retail` (not sold) · `pilot` · `desk` · `enterprise` · `onestop`. Shipped roles: `guest` · `viewer` · `analyst` · `labeler` · `reviewer` · `admin` · `owner` · `pm` · `data` · `oversight` · `ir`. Behaviour: `docs/PRD_ROLES.md`.
- Guest: Tracker + dossier read (15 dossier opens / session) then a **paywall modal** (`guest_dossier_cap`) pointing at register / Pilot / Package. No Desk writes, chat, labeling, or feedback. Register merges `guest_token` prefs.
- Design-partner invite → viewer + feedback, 60-day token.
- Seat ladder: `viewer` · `pm` · `data` · `ir` · `oversight` · `analyst` · `labeler` · `reviewer` · `admin` · `owner`. There are no custom per-desk roles. The **owner** appoints and removes `admin`. An **admin** invites and changes the working seats, not another admin. Nobody assigns `owner` from the desk. Accept is `reviewer`, `admin`, or `owner`. The `ir` seat carries `company_scope` (set by the desk admin on the member-role route) and exports board packs for those companies only. `oversight` reads the desk audit trail (`org_audit`): seat changes, review decisions, and pack exports, each with the person. Login lands each seat on its job (`frontend/src/lib/seatLanding.ts`); a bookmark is not redirected.
- A desk session or API key reads and writes only its own organisation: org snapshot, members, invites, checklist, CSM, SLA, audit, reviews, and MSA signing (another desk's invoice id returns 404). `?org=` on `/api/audit` cannot name another desk. A key with `platform_admin_role` may cross desks on those routes; the operator portal remains `/admin`. Product analytics (`/api/analytics/events`), schema migrate, and counsel attest require a platform operator. `POST /api/orgs/pilot` is the platform operator or the local `intellens-demo` key.
- Approving a pilot request opens the desk and emails `owner_email` an accept-invite link as **admin** (`orgs.invite_recorded_owner`). Register still opens a separate desk. Resend: `POST /api/admin/portal/orgs/{id}/owner-invite`. The pilot term is not enforced; delete the user to end the seat.
- SSO: stub/OIDC (`/api/auth/sso/*`) — production OIDC is ops follow-up.
- Orgs/seats: `GET /api/orgs/{id}`, `GET /api/orgs/me` · legal: `/api/legal/*`.
- Platform admin portal: `/admin` · `/api/admin/portal/*` · roles `super|ops|compliance|billing|support` — see `docs/kb/15-admin-portal.md`.
- Owner: **Ocotillo Innovation Private Limited** (see footer / `/api/legal/meta`).
- **Protected team accounts** (`backend/app/data/protected_users.json`, `services/protected_users.py`): one per org role (`owner|admin|reviewer|analyst|labeler|viewer`, emails `<role>.team@citealpha.com`) in org `citealpha-team` on the `desk` plan. On every API start they are created if missing and their org, role and active status are put back; a password the user changed is kept. Org admins get `400` on revoke or role change. Manifest holds salted PBKDF2 hashes only. Off switch: `CITEALPHA_PROTECTED_USERS=0` (tests set it off). Production `auth.db` lives on EFS; local Docker keeps it inside the container, so a rebuild wipes other local accounts.

## Docs

`docs/I18N_AUTH_MARKETS.md`, `docs/PRODUCTION_B2B_B2C.md`, `docs/prompts/I18N_AUTH_MARKETS_PROMPT.md`, `docs/REGIONAL_MARKETS.md`
