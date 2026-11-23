# Roadmap

Aligned with plan v0.1 §19–20. Tiers: `docs/SCOPE.md`. Gates G0–G3: `docs/TESTING.md`. One milestone in progress at a time.

Each milestone lists: **MVP** (must ship to exit) · **Deferred** (NICE → after exit if small; NEXT → later round) · **Exit** (test that closes it).

---

## M0 — Documentation & contracts  ✅ done (23 Nov 2026)
**MVP**
- [x] Monorepo scaffold, API skeleton, mock flight/places providers
- [x] Postgres/PostGIS baseline schema + Alembic + DB tests (migration 0001)
- [x] Provider contract test suite; CI (lint, `alembic check`, PostGIS tests, web typecheck)
- [x] Split plan v0.1 into repo docs (SCOPE, PRODUCT, ARCHITECTURE, DATA_MODEL, API_CONTRACTS, TESTING, WORKFLOW, DECISIONS)
- [x] DOC-001 Owner review + freeze v0.1 docs; open-decision defaults accepted (23 Nov 2026)
- [x] CORE-001 Pydantic contracts for Trip (new variables), Member, Stop, Constraint, Booking, Money; `/v1` routes declared; TS types generated (A-08) — reviewed by owner

**Exit:** all open architecture questions tagged in DECISIONS.md with a default; core Pydantic/TS contracts reviewed. No feature code before this.

## M1 — Trip workspace  ⏳ in progress
**MVP issues:** ~~CORE-002 migration 0002 (trips change, stops, constraints, bookings, users minimal)~~ ✅ · ~~CORE-003 trips/members/stops/constraints/bookings API (`/v1`, persisted)~~ ✅ · ~~CORE-004 Egypt fixture loader~~ ✅ · UI-001 Create Trip flow (form + trip page, read-only lists)
**Deferred:** NICE trip duplication · NEXT sharing/roles, collaborative edit
**Exit (E1):** Egypt reference trip persists and reloads identically, without AI. API tests + UI smoke green.

## M2 — Places + routing
**MVP issues:** PLACE-001 normalized Place contract (hours, rating, price, accessibility, tz) + fixtures · PLACE-002 live places adapter (after D-02) · ROUTE-001 route matrix adapter (mock + live) · ITIN-001 candidate day builder (clustering by stop, day capacity from pace/window/mobility) · provider_snapshots + TTL
**Deferred:** NICE photos metadata, transit mode choice · NEXT multi-provider merge
**Exit (E2):** feasible day candidates with travel times for Egypt; late-arrival day has no sightseeing.

## M3 — Itinerary engine
**MVP issues:** ITIN-002 feasibility validator (hours, travel, overlaps, bookings, day window) · AI-001 structured itinerary output schema · AI-002 planner orchestration with fake LLM in tests · ITIN-003 locked items + partial regeneration (day scope) + plan_versions/diff · UI-002 itinerary editor (edit, lock, regenerate day)
**Deferred:** NICE rollback endpoint, drag-and-drop · NEXT multi-day re-flow, auto order optimisation
**Exit (E3, E3b):** remove Aswan → only 6 Nov changes; balloon cancel → only 5 Nov morning changes; validator green; diff stored.

## M4 — Flight search
**MVP issues:** FLIGHT-001 normalized flight contract (segments, fare, baggage, expiry) · FLIGHT-002 mock provider + fixtures (exists, extend) · FLIGHT-003 live adapter (after D-03) · select flight → booking + hard time constraint · UI flight options + external booking link
**Deferred:** NICE time-of-day / self-transfer filters · NEXT price alerts, flexible dates · NO ticketing
**Exit (E4):** selected arrival/departure changes day capacity correctly; expired offer forces re-search.

## M5 — Contextual recommendation
**MVP issues:** FOOD-001 TasteProfile + dietary schema · FOOD-002 review signal extractor (non-sensitive, schema-validated) · FOOD-003 restaurant ranker + "why" · KNOW-001 knowledge cards (before/at place) with sources · PHOTO-001 curated photo spot schema + read API · UI place drawer Know/Eat/Photo/Practical
**Deferred:** NICE after-trip cards · NEXT learned taste, user photo spots
**Exit (E5):** recommendations show provenance + why-match; privacy test asserts no sensitive inference fields exist or are used.

## M6 — Budget & settlement
**MVP issues:** BUD-001 expense + split model (migration: rename/extend 0001 tables) · BUD-002 transfers + settlement engine (property tests) · FX adapter + snapshots · UI budget page (cost / share / paid / transfers / remaining)
**Deferred:** NICE category budgets, CSV export · NEXT OCR, bank connectors · NO accounting package
**Exit (E6):** Egypt expense case reconciles; transfers not in trip cost; Σ net = 0.

## M7 — During-trip mode
**MVP issues:** UI-003 Today view (mobile-first) · skip / running late / replan rest of today (reuses ITIN-003 with "after now" scope)
**Deferred:** NICE nearby fallback, prep checklist, visited/skipped marking · NEXT offline, push
**Exit (E7):** user modifies today from a phone in ≤3 taps; departure untouched.

## M8 — Hardening
**MVP issues:** OPS-001 tracing + provider metrics · quotas/backoff · failure-mode tests · evals harness · auth (D-01) hardening + delete-my-data · staging with seeded Egypt trip · security review
**Exit (G4):** staging passes all golden slices and failure-mode tests.

---

## Next round (post-MVP backlog, not scheduled)
Destination inspiration from flexible dates · hotel search/booking · collaborative real-time editing · offline packs · community photo spots · receipt OCR + bank connectors · learned long-term taste · price alerts · native mobile app.
