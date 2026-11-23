# Architecture

Source: plan v0.1 §10, §13, §15, §17. Decisions: `docs/DECISIONS.md`.

## High-level (modular monolith)

```text
Browser / mobile web
   │
Next.js web app ──── typed REST/JSON (/v1) ────┐
                                               ▼
FastAPI application API
   ├── Domain services        trips · itinerary · recommendations · knowledge · expenses
   ├── Orchestration / AI     planner · partial-regenerator · explainer
   ├── Provider adapters      flights · places · routes · weather (NICE) · fx
   ▼
PostgreSQL + PostGIS   (pgvector only if D-04 says so; Redis/object storage optional, NEXT)
```

Start as a modular monolith. Split services only when ownership, scale or deploy cadence forces it (non-goal for v1).

## Layer rules

| Layer | Allowed | Not allowed |
|---|---|---|
| UI (`apps/web`) | render state, collect input, optimistic UI; API calls only in `src/lib` | provider credentials, business rules |
| API / controller (`app/api`) | auth, validation, request composition | recommendation/scoring logic |
| Domain (`app/domain/*`) | deterministic business rules, pure functions, typed objects | network calls, DB sessions, vendor SDKs |
| Orchestration (`app/orchestration`) | call domain + providers + LLM in a workflow | owning canonical data schema |
| Provider adapter (`app/providers/*`) | external API ⇄ normalized model translation | leaking provider payloads into domain/UI |
| Persistence (`app/db`) | repositories, transactions, migrations | recommendation prose |

Rule of thumb: `Skyscanner/Duffel response → FlightOption → itinerary engine`, never `Skyscanner response → itinerary engine`.

## Planning pipeline (generate)

1. Resolve trip state (constraints, bookings, locked items, current plan version)
2. Fetch/refresh required provider data (respect TTL)
3. Build candidate set
4. **Deterministic filtering**: closed, impossible travel time, hard constraints, dietary/avoid lists
5. Score candidates (deterministic)
6. LLM composes a **structured** plan (schema-constrained output) from feasible candidates only
7. **Validator** checks conflicts; on failure → retry with violations, or return error (never return an invalid plan)
8. Persist new `plan_version`
9. Generate short "why this plan" explanation

Steps 1–5, 7, 8 are code. The LLM is only in 6 and 9 and receives bounded context (the affected scope, not the whole trip history).

## Partial regeneration

1. Identify affected date/range + dependency graph (e.g. hotel check-out, transfer to airport)
2. Freeze confirmed bookings + locked items (and everything outside scope)
3. Remove only unlocked items in scope
4. Recompute candidates/routes inside the available time window
5. Generate replacement plan for the scope
6. Validate against flight/hotel/transport constraints
7. Write diff, keep old version for rollback

Contract example (MVP scope = one day):
```json
{
  "scope": {"date": "2026-11-06"},
  "change": "Remove Aswan; stay around Luxor downtown",
  "preserve": ["confirmed_bookings", "locked_items", "flight_departure"],
  "preferences": {"pace": "relaxed"}
}
```

## Reliability, caching, cost

| Area | Requirement | Tier |
|---|---|---|
| Freshness | every volatile provider snapshot has `fetched_at` + TTL; UI shows staleness | MVP |
| Caching | cache search/place/route by normalized request; never cache a fare beyond provider validity | MVP (DB-level) / NEXT (Redis) |
| Idempotency | create expense/transfer/booking accept `Idempotency-Key` | MVP |
| Fallback | provider failure → degraded state + stale label, never fabricated results | MVP |
| Rate limits | central provider client with retry/backoff + per-provider quota | MVP (retry) / M8 (quotas) |
| Tracing | one `trace_id` per plan generation; log provider calls + validator outcome | M8 |
| LLM cost | structured, bounded context; one-day scope sends one day | MVP |

## Environments

| Env | Purpose | Tier |
|---|---|---|
| local | laptop/cloud dev; **mock providers by default**; docker compose PostGIS | MVP |
| CI | GitHub Actions: lint, migrations check, tests on PostGIS, web typecheck | MVP (done) |
| staging | prod-like DB, sandbox provider keys, seeded Egypt trip | M8 |
| prod | strict secrets, backups, monitoring | post-M8 |

Hosting vendors (Vercel / container platform / managed Postgres+PostGIS) are implementation decisions, not domain dependencies.

## Target repo layout

```text
services/api/app/
  api/routes/          # thin controllers, /v1
  domain/              # trips, itinerary, recommendations, knowledge, expenses (pure)
  orchestration/       # planner, regenerator, explainer (M3+)
  providers/           # flights/, places/, routes/, fx/ — protocol + mock + live adapters
  db/                  # models, repositories, session
services/api/tests/
  fixtures/            # sanitized provider responses, Egypt scenario
apps/web/src/
  lib/                 # API client (only place that calls fetch)
  types/               # TS contracts — generated from OpenAPI (A-08)
```
`packages/contracts/` from the plan is replaced by OpenAPI-generated TS types (A-08) to avoid hand-maintained duplicates.
