# AI handoff log

## Current baseline

The repository contains product/architecture decisions plus a minimal FastAPI domain skeleton.

### Implemented
- typed Trip request/response model;
- provider protocol for flights/places;
- mock flight provider;
- deterministic itinerary skeleton;
- taste-profile matching primitives;
- expense/share/transfer settlement primitives.

- (M0) SQLAlchemy schema + Alembic migration `0001` for trips, members, places (PostGIS), expenses, shares, transfers;
- (M0) `TripRepository` mapping rows ⇄ `Trip` domain model;
- (M0) provider contract test suite (flights, places), API + expense unit tests, PostGIS schema tests;
- (M0) GitHub Actions CI: ruff, `alembic check`, pytest against `postgis/postgis:16-3.4`, web `tsc --noEmit`.

### Contracts affected
- None changed. New: `app.db.repositories.TripRepository`, `app.config.Settings` (`DATABASE_URL`).

### Known gaps
- `POST /trips` still does not persist (wiring belongs to M1).
- Expense settlement algorithm not implemented yet (only `trip_cost`); planned for M5.
- No `users`/auth tables yet; `trip_members` are display names only.

### Next safe tasks
1. M1: persist `POST /trips`, add `GET/PATCH /trips/{id}` using `TripRepository` + `get_session`.
2. M1: traveller preferences + manual bookings tables (new migration).
3. Add place normalization model and mock provider fixtures; repository for `places`.
4. Build `/trips/{id}/itinerary` around persisted data.
5. Add Next.js create-trip form against the API.

### Context rule
Pick one task, read only its module + shared contract. Do not redesign unrelated modules.
