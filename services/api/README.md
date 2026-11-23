# API service

FastAPI application and domain orchestration.

Domain code must be vendor-neutral. Any vendor request/response translation belongs in `app/providers`.

## Layout

| Path | Owns |
|---|---|
| `app/domain/shared` | cross-module contracts (Money, Provenance, TimeWindow, enums) |
| `app/domain/*` | typed domain objects + pure logic (no DB, no vendors) |
| `app/api` | `/v1` routes + error envelope |
| `openapi.json` | committed API contract → web TS types (`scripts/export_openapi.py`) |
| `app/providers` | provider protocols, mocks, future vendor adapters |
| `app/db/models.py` | SQLAlchemy schema (PostgreSQL + PostGIS) |
| `app/db/repositories.py` | ORM row ⇄ domain object translation; only place that touches rows |
| `migrations/` | Alembic migrations (`alembic revision --autogenerate -m "..."`, then review) |
| `tests/` | unit + provider contract tests; `tests/db/` needs `TEST_DATABASE_URL` |

## Schema (migration `0001_initial_schema`)

- `trips` — checks: `end_date >= start_date`, travellers 1–20, pace enum.
- `trip_members` — unique `(trip_id, display_name)`.
- `places` — `geography(Point, 4326)` + GiST index; unique `(provider, provider_place_id)`.
- `expenses` (cost + payer), `expense_shares` (who owes what), `transfers` (member → member, never trip cost; sender ≠ recipient).
- Money is `numeric(14,2)` with ISO-4217 3-letter currency. Deleting a trip cascades to members/expenses/transfers.

## Adding a provider adapter

Add the instance to `FLIGHT_PROVIDERS` / `PLACES_PROVIDERS` in `tests/test_providers_contract.py`; it must pass the contract suite (use recorded fixtures, not live calls).

## Changing a contract

1. Edit models in `app/domain/**/models.py` (+ docs/API_CONTRACTS.md / DATA_MODEL.md).
2. `python scripts/export_openapi.py`
3. `cd ../../apps/web && npm run gen:types`
4. Commit `openapi.json` and `src/types/api.gen.ts` — CI fails if either is stale.
