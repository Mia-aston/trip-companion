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

## M1 — Trip workspace  ✅ done (merged via #10, 23 Nov 2026)
**MVP issues:** ~~CORE-002 migration 0002 (trips change, stops, constraints, bookings, users minimal)~~ ✅ · ~~CORE-003 trips/members/stops/constraints/bookings API (`/v1`, persisted)~~ ✅ · ~~CORE-004 Egypt fixture loader~~ ✅ · ~~UI-001 Create Trip flow (form + trip page, read-only lists)~~ ✅
**Deferred:** NICE trip duplication · NEXT sharing/roles, collaborative edit
**Exit (E1):** Egypt reference trip persists and reloads identically, without AI. API tests + UI smoke green. — met.

## M2 — Places + routing  ✅ done (merged via #10, 23 Nov 2026)
Everything runs on **mock providers + fixtures**; live adapters wait for D-02 and do not block the exit.

**MVP issues (in order)**
1. ✅ PLACE-001 — normalized `Place` contract (categories, opening hours, rating, price level, wheelchair access, timezone, typical visit, provenance) + `is_open()`; mock provider over Egypt fixtures; provider contract suite updated.
2. ✅ ROUTE-001 — `RouteMatrix` contract (walk / drive) + mock adapter (haversine × detour factor ÷ mode speed); contract suite.
3. ✅ ITIN-001 — candidate day builder (pure): per date → stop, available window (day window ∩ flight/booking constraints), capacity from pace / mobility / party, ranked feasible candidates with travel time from the stop base. Rules: `docs/ARCHITECTURE.md#day-capacity-m2`.
4. ✅ PLACE-003 — persistence + API: migration 0003 (places columns, `provider_snapshots` with TTL, `route_legs`), `POST /v1/places/search`, `GET /v1/places/{id}`, `GET /v1/trips/{id}/day-candidates`.

**Deferred:** PLACE-002 live places adapter + ROUTE-002 live routes adapter (after D-02; contract suite must pass) · NICE photos metadata, transit mode · NEXT multi-provider merge
**Exit (E2):** for the Egypt trip, every day has a capacity and ranked feasible candidates with travel times; 31 Oct (late arrival) and 6 Nov after the airport cut-off have zero sightseeing capacity; must-dos (Giza pyramids) appear on a Cairo day; closed places never appear on that weekday.

## M3 — Itinerary engine  ✅ exit met on UI-002 PR (pending merge)
Rules: `docs/ARCHITECTURE.md#itinerary-engine-m3`. One PR per issue, each based on `main`, merged before the next starts.

**MVP issues (in order)**
1. ✅ M3 doc pass — itinerary tables, validator rules, planner contract, regenerate contract, E3 fixture.
2. ✅ ITIN-002 + AI-001 — `ProposedPlan` schema (structured planner output), `validate()` (pure, rules V1–V9), `GreedyPlanner` (deterministic, no LLM) behind the `Planner` interface. Property test: validator never accepts overlaps / out-of-window items.
3. ✅ AI-002 — migration 0004 (`plan_versions`, `itinerary_days`, `itinerary_items`), plan repository, orchestration (day inputs → planner → validator → persist → explanation), `POST …/itinerary/generate`, `GET …/itinerary`, `GET …/itinerary/diff`.
4. ✅ ITIN-003 — item edits (`PATCH`, lock, add custom item, delete), `POST …/itinerary/regenerate` (day scope), diff by stable `item_key` → **E3, E3b**.
5. ✅ UI-002 — itinerary editor: generate, day list, lock toggle, remove/add item, "regenerate this day" (pace, stay-near radius, exclude), version note + diff summary; Playwright.

**Deferred:** NICE LLM planner adapter (needs D-07; same `Planner` interface, must pass the same validator), rollback endpoint, drag-and-drop, meal suggestions from food engine (M5) · NEXT multi-day re-flow, route-order optimisation, free-text change interpretation
**Exit (E3, E3b):** on the Egypt trip, removing the user-added "Aswan day trip" and regenerating 6 Nov "around Luxor downtown" changes only 6 Nov unlocked items; every other day, all bookings and locked items are identical; 22:30 departure respected; a new plan version with a diff is stored; validator has no errors. Cancelling the balloon booking and regenerating 5 Nov replaces only the morning block.

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
