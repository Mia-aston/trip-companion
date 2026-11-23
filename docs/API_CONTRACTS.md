# API contracts

Source: plan v0.1 §12. Paths may change; **semantics may not change without updating this file first** (contract PR before implementation PR, see `docs/WORKFLOW.md`).

Conventions (MVP):
- All routes under `/v1`. JSON, snake_case. Times ISO-8601 with offset; dates `YYYY-MM-DD`.
- Money is `{ "amount": "128.62", "currency": "EUR" }` (string decimal, never float).
- Errors: `{ "error": { "code": "...", "message": "...", "details": [...] } }`; validation = 422, conflict with locked/booked items = 409, provider down = 503 with `stale: true` data if any.
- Volatile data carries `provenance: { source: "provider|user|ai", provider?, fetched_at?, expires_at? }`.
- Mutations that create money/booking rows accept `Idempotency-Key`.
- OpenAPI from FastAPI is the machine contract; TS types are generated from it (D-08).

| Method & path | Purpose | Milestone | Tier | Status |
|---|---|---|---|---|
| `POST /v1/trips` | create trip (variables in SCOPE.md) | M1 | MVP | skeleton exists at `/trips`, not persisted |
| `GET /v1/trips/{trip_id}` | load trip + members + stops + constraints + bookings | M1 | MVP | todo |
| `PATCH /v1/trips/{trip_id}` | edit trip fields | M1 | MVP | todo |
| `DELETE /v1/trips/{trip_id}` | delete trip (privacy) | M1 | MVP | todo |
| `POST/PATCH/DELETE /v1/trips/{trip_id}/members[/{id}]` | manage members | M1 | MVP | todo |
| `POST/PATCH/DELETE /v1/trips/{trip_id}/constraints[/{id}]` | must-do, avoid, dietary, windows | M1 | MVP | todo |
| `POST/PATCH/DELETE /v1/trips/{trip_id}/bookings[/{id}]` | manual bookings | M1 | MVP | todo |
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

## Core payloads (to be frozen as Pydantic models in CORE-001)

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
