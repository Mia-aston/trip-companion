# API service

FastAPI application and domain orchestration.

Domain code must be vendor-neutral. Any vendor request/response translation belongs in `app/providers`.

## Layout

| Path | Owns |
|---|---|
| `app/domain/shared` | cross-module contracts (Money, Provenance, TimeWindow, enums) |
| `app/domain/*` | typed domain objects + pure logic (no DB, no vendors) |
| `app/api` | `/v1` routes (thin: validate → rules → repository) + error envelope |
| `app/domain/trips/rules.py` | Trip rules needing current state (PATCH merge, member/booking checks) |
| `app/domain/shared/errors.py` | `NotFound` / `Conflict` / `InvalidChange` → 404 / 409 / 422 |
| `openapi.json` | committed API contract → web TS types (`scripts/export_openapi.py`) |
| `app/providers` | provider protocols, mocks, future vendor adapters |
| `app/db/models.py` | SQLAlchemy schema (PostgreSQL + PostGIS) |
| `app/db/repositories.py` | ORM row ⇄ domain object translation; only place that touches rows |
| `migrations/` | Alembic migrations (`alembic revision --autogenerate -m "..."`, then review) |
| `tests/` | unit + provider contract tests; `tests/db/` needs `TEST_DATABASE_URL` |

## Schema (migrations `0001`, `0002`)

- `users` — minimal account (D-01); `email` unique.
- `trips` — CORE-001 contract: travellers (`adults`, `children_ages`, `infants`, party ≤ 20, infants ≤ adults), currencies, budget (all-or-nothing), pace, day window, interests, dietary, mobility, price level, `flight_prefs` JSONB, nullable `owner_id`.
- `trip_stops` — ordered multi-city stops; unique `(trip_id, seq)`; `leave_on = arrive_on + nights`.
- `trip_members` — unique `(trip_id, lower(display_name))`; role, currency_pref, `position` keeps order.
- `trip_constraints` — kind `must_do|avoid|time_window`; kind-specific fields in `payload` JSONB (validated by the contract on read).
- `bookings` — manual bookings; `ends_at >= starts_at`; cost all-or-nothing.
- `places` — `geography(Point, 4326)` + GiST index; unique `(provider, provider_place_id)`.
- `expenses` (cost + payer), `expense_shares` (who owes what), `transfers` (member → member, never trip cost; sender ≠ recipient). Money `numeric(14,2)` + ISO-4217.
- Deleting a trip cascades to all children. Instants are `timestamptz` and come back as UTC (A-11).

`TripRepository` (`app/db/repositories.py`) persists the Trip aggregate: `add`, `get`, `save` (scalars + stops), `delete`, and `add_/remove_` member, constraint, booking. `get_session` commits per request and rolls back on any error.

## Adding a provider adapter

Add the instance to `FLIGHT_PROVIDERS` / `PLACES_PROVIDERS` in `tests/test_providers_contract.py`; it must pass the contract suite (use recorded fixtures, not live calls).

## Dev data

`python scripts/seed_egypt.py` loads the Egypt golden trip into `DATABASE_URL` (idempotent; `--reset` recreates it).

## Changing a contract

1. Edit models in `app/domain/**/models.py` (+ docs/API_CONTRACTS.md / DATA_MODEL.md).
2. `python scripts/export_openapi.py`
3. `cd ../../apps/web && npm run gen:types`
4. Commit `openapi.json` and `src/types/api.gen.ts` — CI fails if either is stale.
