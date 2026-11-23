# API contracts

Source: plan v0.1 §12. Paths may change; **semantics may not change without updating this file first** (contract PR before implementation PR, see `docs/WORKFLOW.md`).

Conventions (MVP):
- All routes under `/v1`. JSON, snake_case. Instants ISO-8601 with offset on input, always returned in UTC (`Z`) (A-11); dates `YYYY-MM-DD`; wall-clock times `HH:MM:SS`.
- Money is `{ "amount": "128.62", "currency": "EUR" }` (string decimal, never float).
- Errors: `{ "error": { "code": "...", "message": "...", "details": [...] } }`; validation or invalid change = 422 (`validation_error`), unknown id = 404, clash with stored state (duplicate member, member with expenses, locked items) = 409 (`conflict`), provider down = 503 with `stale: true` data if any.
- Volatile data carries `provenance: { source: "provider|user|ai", provider?, fetched_at?, expires_at? }`.
- Mutations that create money/booking rows accept `Idempotency-Key`.
- OpenAPI from FastAPI is the machine contract; TS types are generated from it (A-08).

| Method & path | Purpose | Milestone | Tier | Status |
|---|---|---|---|---|
| `POST /v1/trips` | create trip (variables in SCOPE.md) | M1 | MVP | implemented, persisted (CORE-003) |
| `GET /v1/trips/{trip_id}` | load trip + members + stops + constraints + bookings | M1 | MVP | implemented (CORE-003) |
| `PATCH /v1/trips/{trip_id}` | edit trip fields; optional `stops` replaces all stops (A-13); merged trip re-validated → 422 | M1 | MVP | implemented (CORE-003) |
| `DELETE /v1/trips/{trip_id}` | delete trip (privacy) | M1 | MVP | implemented (CORE-003) |
| `POST/DELETE /v1/trips/{trip_id}/members[/{id}]` | manage members (PATCH: NICE) | M1 | MVP | implemented (CORE-003) |
| `POST/DELETE /v1/trips/{trip_id}/constraints[/{id}]` | must_do, avoid, time_window (A-09) | M1 | MVP | implemented (CORE-003) |
| `POST/DELETE /v1/trips/{trip_id}/bookings[/{id}]` | manual bookings (PATCH: NICE) | M1 | MVP | implemented (CORE-003) |
| `POST /v1/places/search` | text/nearby search → `Place[]` | M2 | MVP | todo |
| `GET /v1/places/{place_id}` | normalized details | M2 | MVP | todo |
| `POST /v1/routes/matrix` | travel times between places (internal use first) | M2 | MVP | todo |
| `POST /v1/trips/{trip_id}/itinerary/generate` | full plan → new plan_version | M3 | MVP | todo |
| `POST /v1/trips/{trip_id}/itinerary/regenerate` | partial regenerate (body in ARCHITECTURE.md) | M3 | MVP | todo |
| `GET /v1/trips/{trip_id}/itinerary?version=` | current/specific version | M3 | MVP | todo |
| `GET /v1/trips/{trip_id}/itinerary/diff?from=&to=` | version diff | M3 | MVP | todo |
| `POST /v1/trips/{trip_id}/itinerary/rollback` | restore a version | M3 | NICE | todo |
| `PATCH /v1/itinerary/items/{item_id}` | edit time/place | M3 | MVP | todo |
| `POST /v1/itinerary/items/{item_id}/lock` | lock/unlock (`{"locked": bool}`) | M3 | MVP | todo |
| `POST /v1/flights/search` | normalized `FlightOption[]` with expiry | M4 | MVP | todo |
| `POST /v1/trips/{trip_id}/transport/select` | selected offer → booking + time constraint | M4 | MVP | todo |
| `GET /v1/places/{place_id}/knowledge?moment=&lang=` | knowledge cards | M5 | MVP | todo |
| `GET /v1/places/{place_id}/food?trip_id=` | ranked restaurants with match % + why | M5 | MVP | todo |
| `GET /v1/places/{place_id}/photo-spots` | curated spots | M5 | MVP | todo |
| `GET/PUT /v1/me/taste-profile` | declared taste + dietary | M5 | MVP | todo |
| `POST /v1/trips/{trip_id}/expenses` | expense + splits | M6 | MVP | todo |
| `POST /v1/trips/{trip_id}/transfers` | member transfer | M6 | MVP | todo |
| `GET /v1/trips/{trip_id}/settlement?currency=` | recomputed settlement | M6 | MVP | todo |
| `GET /v1/trips/{trip_id}/today` | Today view | M7 | MVP | todo |
| `POST /v1/trips/{trip_id}/today/actions` | skip / late / replan-rest-of-day | M7 | MVP | todo |
| `DELETE /v1/me` | delete account data | M8 | MVP | todo |

## Core payloads (frozen in CORE-001)

Source of truth: `services/api/app/domain/trips/models.py`, `app/domain/shared/models.py` → `services/api/openapi.json` → `apps/web/src/types/api.gen.ts`. Full example: `services/api/tests/fixtures/egypt/trip_create.json`.

```jsonc
// TripCreate
{
  "title": "Egypt Nov 2026",
  "origin": "LON",
  "start_date": "2026-10-31", "end_date": "2026-11-06",
  "adults": 2, "children_ages": [], "infants": 0,
  "stops": [{"city": "Cairo", "nights": 3}, {"city": "Western Desert", "nights": 1}, {"city": "Luxor", "nights": 2}],
  "base_currency": "GBP", "settlement_currency": "GBP",
  "budget": {"total": {"amount": "2500.00", "currency": "GBP"}, "scope": "per_trip"},
  "pace": "balanced", "day_window": {"start": "08:00", "end": "21:00"},
  "interests": ["history", "photo", "food"],
  "mobility_needs": "none", "price_level": 2,
  "constraints": [{"kind": "must_do", "hardness": "hard", "payload": {"query": "Giza pyramids"}}]
}
```
