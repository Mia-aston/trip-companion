# API service

FastAPI application and domain orchestration.

Domain code must be vendor-neutral. Any vendor request/response translation belongs in `app/providers`.

## Layout

| Path | Owns |
|---|---|
| `app/domain/*` | typed domain objects + pure logic (no DB, no vendors) |
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
