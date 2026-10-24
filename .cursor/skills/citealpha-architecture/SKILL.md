---
name: citealpha-architecture
description: >-
  Explains or evolves CiteAlpha system architecture (services layering, data
  flow, feature flags). Use when planning refactors, new services, or
  documenting structure.
---

# CiteAlpha Architecture

## Steps

1. Read `docs/kb/02-architecture.md`.
2. Keep scoring pure; I/O in repository/API.
3. Extend the owner in `docs/kb/19-reuse-and-source-once.md`. Load `citealpha-reuse-sources` before a new service or fetch. Read `doc_store` before calling NSE, BSE, EDGAR, or a model.
4. Document new modules in kb + this skill’s mental model.
5. Flag remaining depth gaps (LLM doc store, live feeds) honestly vs demos; auth/billing/Postgres are shipped — see `citealpha-production`.

## Layering

`routes → services → data/store` · Frontend `pages → components → lib/api.ts`.
