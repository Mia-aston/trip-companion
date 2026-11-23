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
6. A `Planner` composes a **structured** plan (`ProposedPlan`) from feasible candidates only — `GreedyPlanner` (deterministic) in MVP; an LLM planner with schema-constrained output plugs into the same interface later (D-07)
7. **Validator** checks conflicts; on failure → retry with violations, or return error (never return an invalid plan)
8. Persist new `plan_version`
9. Generate short "why this plan" explanation

Steps 1–5, 7, 8 are always code. An LLM may only ever run in 6 and 9, with bounded context (the affected scope, not the whole trip history), and its output goes through the same validator.

## Day capacity (M2)

Deterministic, pure (`app/domain/itinerary/days.py`). For each date of the trip:

1. **Stop of the day:** the stop with `arrive_on <= date < leave_on`; the last date belongs to the last stop. Times use the stop's timezone.
2. **Available window** = `day_window` (e.g. 08:00–21:00), then cut by:
   - arrival flight (first `flight` booking): available from `ends_at + 90 min` (immigration, bags, transfer);
   - departure flight (last `flight` booking): available until `starts_at − 180 min` (transfer + check-in);
   - other bookings on that date (activities, transport, check-out) are **blocked intervals** inside the window; `tentative` counts, `cancelled` doesn't;
   - `time_window` constraints are blocked intervals too.
3. **Capacity minutes** = free minutes in the window × utilisation:
   pace `relaxed 0.6 · balanced 0.75 · packed 0.9`; × 0.8 if `mobility_needs != none`; × 0.85 if any child under 6 or infants. Under 60 free minutes → capacity 0 (no sightseeing).
4. **Candidates:** places of the stop (within 25 km of the stop base), not excluded by `avoid`, open for at least the typical visit inside the window on that weekday (unknown hours → allowed, flagged), wheelchair-inaccessible places dropped when `mobility_needs = wheelchair`.
   Score = 0.5 interest match + 0.2 rating + 0.2 must-do bonus − 0.1 travel penalty (travel minutes from base / 60, capped at 1). A candidate fits if `travel there + visit + travel back ≤ capacity`.
4b. **Transfer day** (first day of stop 2+): time before the arriving transport booking belongs to the previous stop; without such a booking the day carries a note asking for it.
4c. A **must-do covered by an activity booking** (title match) counts as met.
5. **Output** `DayPlanInput`: date, stop, window, blocked intervals, capacity, ranked candidates (place, score, visit minutes, travel minutes, reasons), unmet must-dos. ITIN-002 (M3) turns this into a schedule.

## Itinerary engine (M3)

### Plan model
- A trip has **plan versions** `1, 2, 3…`; each is an immutable full snapshot (days → items). Edits never mutate a version: they write the next one (A-19).
- Every item has a stable `item_key` (UUID) that survives across versions; the diff between two versions is computed by `item_key`: `added`, `removed`, `changed` (time / place / lock), `unchanged`.
- Item kinds: `place` (a visit), `booking` (mirrors a trip booking; always locked), `transfer` (travel between items, computed), `meal`, `custom` (user free text, e.g. "Aswan day trip"), `free`.
- `source`: `planner`, `user`, `booking`. Booking items are generated from trip bookings on every version and cannot be edited through the itinerary.

### Planner contract (AI-001)
`Planner.compose(PlannerContext) -> ProposedPlan`.
- `PlannerContext` (bounded): for each day in scope — the `DayPlanInput` from ITIN-001 (window, blocked intervals, capacity, top 15 candidates), fixed items (bookings + locked + out-of-scope), preferences (pace, interests), exclusions.
- `ProposedPlan`: `days[] { date, items[] { kind, place_id?, title, start "HH:MM", end "HH:MM", why } }` + `explanation` — local wall-clock times in the stop's timezone; the orchestrator converts to UTC.
- **GreedyPlanner** (MVP, deterministic): per day, walk the ranked candidates; place each must-do first, then by score; start at the earliest free slot after the previous item + drive travel time; keep the visit inside opening hours and outside blocked/fixed intervals; insert a `meal` block (60 min) around 12:30–14:00 and a 19:00–20:30 dinner if the window covers it; stop when capacity is used. `why` = the candidate's reasons.

### Validator (ITIN-002) — pure; errors block persisting, warnings are shown
| Rule | Severity | Check |
|---|---|---|
| V1 window | error | non-booking items inside the day window |
| V2 overlap | error | no two items overlap within a day |
| V3 travel | error | gap between consecutive located items ≥ drive time (route matrix) |
| V4 hours | error | `place` item fully inside opening hours (unknown hours → warning) |
| V5 bookings | error | every confirmed/tentative booking on that date appears as an unchanged locked `booking` item |
| V6 locked | error | locked items identical to the previous version |
| V7 must-do | warning | each hard must-do is scheduled on some day (or covered by a booking) |
| V8 avoid | error | no `avoid`ed place is scheduled |
| V9 capacity | warning | sum of visit minutes ≤ day capacity |

The orchestrator never persists a plan with errors: it returns 422 with the violations (A-21).

### Regenerate contract (ITIN-003, MVP = one day)
```json
{
  "scope": {"date": "2026-11-06"},
  "remove_item_keys": ["…aswan item key…"],
  "exclude_place_ids": [],
  "stay_within_m": 3000,
  "pace": "relaxed",
  "note": "Remove Aswan; stay around Luxor downtown"
}
```
- Always preserved (not optional): bookings, locked items, everything outside the scope (A-20).
- Removed: unlocked items in scope, plus `remove_item_keys`. Replacement comes from the planner over the day's candidates filtered by `exclude_place_ids` and `stay_within_m` (distance from the stop base).
- `note` is stored as the version's `reason`; it is not interpreted in MVP (free-text interpretation needs an LLM, NEXT).

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
