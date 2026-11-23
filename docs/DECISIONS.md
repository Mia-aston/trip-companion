# Decisions

Changing an architecture/product assumption requires an entry here **before** code continues.
Accepted long-form ADRs live in `docs/decisions/`.

## Accepted
| ID | Decision | Ref |
|---|---|---|
| ADR-0001 | Modular monorepo (web + API + docs), modular monolith API | `decisions/0001-monorepo.md` |
| A-02 | PostgreSQL 16 + PostGIS; `geography(Point,4326)` for places; Alembic migrations with deterministic constraint names | migration 0001 |
| A-03 | Split docs in `docs/` are the source of truth; plan v0.1 archived in `docs/archive/` | this PR |
| A-04 | Scope tiers MVP / NICE / NEXT / NO with change rule | `SCOPE.md` |
| A-05 (was D-09) | Settlement: `net = paid - share + sent - received` (plan v0.1 sign corrected) | `DATA_MODEL.md` |
| A-06 (was D-10) | Egypt fixture: 31 Oct 23:30 CAI → 6 Nov 22:30 LXR, members Mia + QA, GBP | `TESTING.md` |
| A-07 (was D-11) | Travellers (`adults`, `children_ages`, `infants`) drive planning/fares; `members` drive money | `SCOPE.md` |
| A-08 (was D-08) | TS types generated from FastAPI OpenAPI (`openapi-typescript`); no hand-written `packages/contracts/` | CORE-001 |
| A-09 | Trip-level `dietary` and `mobility_needs` are trip fields; `trip_constraints` hold `must_do`, `avoid`, `time_window` only | CORE-001 |
| A-10 | M1 API is declared under `/v1` in CORE-001; unimplemented routes return 501 until CORE-003 | CORE-001 |
| A-11 | Instants (`starts_at`, `fetched_at`, …) require an offset on input and are normalized to UTC; clients display them in the stop's `timezone`. Matches `timestamptz` storage so data round-trips exactly | CORE-002 |
| A-13 | `PATCH /v1/trips/{id}` may send `stops` to replace the whole stop list (only way to change trip length); bookings must not point at removed stops. Explicit `null` clears optional fields | CORE-003 |
| A-14 | API allows browser origins from `CORS_ORIGINS` (default localhost:3000); web calls the API directly from the client in M1 | UI-001 |
| A-15 | Day capacity rules (buffers 90/180 min, pace utilisation, mobility/children factors, 60-min floor, scoring weights) as in ARCHITECTURE.md#day-capacity-m2; tunable constants in one module | M2 |
| A-16 | Stop base location comes from the places provider (`city` place for the stop's city) until stops get explicit coordinates | M2 |
| A-17 | Provider results cached in Postgres (places upsert, search snapshots 24 h, places/routes 7 days); stale cached data is returned when the provider loses a record; providers chosen by `PLACES_PROVIDER` / `ROUTES_PROVIDER` | M2 |
| A-18 | MVP planner is deterministic (`GreedyPlanner`); an LLM planner is a NICE adapter behind the same `Planner` interface once D-07 is decided, and must pass the same validator | M3 |
| A-19 | Plan versions are immutable full snapshots; every edit writes a new version; diffs use stable `item_key`s | M3 |
| A-20 | Regenerate always preserves bookings, locked items, the user's own items unless listed in `remove_item_keys`, and out-of-scope days (not configurable); MVP scope = one day; structured options only (`remove_item_keys`, `exclude_place_ids`, `stay_within_m`, `pace`), `note` stored not interpreted | M3 |
| A-21 | A plan with validator errors is never persisted (422 + violations); warnings are stored on the version | M3 |
| A-12 | `trips.owner_id` is nullable until auth lands (D-01, M8); members/constraints keep insertion order via `position` | CORE-002 |

## Open (default applies until decided)
Defaults below were accepted by the owner on 23 Nov 2026 (DOC-001); they stay open only for the vendor/tech choice.

| ID | Decision needed | Default until decided | Needed by |
|---|---|---|---|
| D-01 | Auth provider | simple email/OAuth abstraction; domain not bound to vendor; M1 runs single-user dev auth | M1 (stub), M8 (real) |
| D-02 | Map rendering + places provider (Google Places New?) | map rendering separate from place data adapter; verify EEA terms before production | M2 live adapter |
| D-03 | Live flight provider for MVP (Skyscanner vs Duffel) | mock adapter; choose after access/cost check | M4 live adapter |
| D-04 | Vector search (pgvector) | not added until semantic retrieval clearly beats relational filters | M5 |
| D-05 | Photo spot sourcing | curated only; user submissions after a moderation flow exists (NEXT) | M5 |
| D-06 | FX source | provider adapter; finalized expenses may freeze the historical rate | M6 |
| D-07 | LLM provider + structured output mechanism | provider-agnostic `Planner` interface; fake planner in tests | M3 |
| D-12 | Supported UI/content languages for MVP | en + vi | M5 |
