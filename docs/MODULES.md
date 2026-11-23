# Modules and contracts

Cross-module communication uses typed domain objects, never DB rows or raw provider JSON.
Tiers per feature: `docs/SCOPE.md`. Issue IDs: `docs/ROADMAP.md`.

| Module | Owns | Inputs | Outputs | Code location | Milestone | Issues |
|---|---|---|---|---|---|---|
| trips (Trip Core) | trip, travellers, members, stops, preferences, constraints, bookings, plan versions | TripCreate (SCOPE variables) | Trip, TripConstraint[], Booking[] | `domain/trips`, `db` | M1 | CORE-001…004 |
| flights | transport discovery + selection | route, dates, pax (adults/children/infants), flight_prefs | FlightOption[] (with expiry) | `providers/flights`, `domain/transport` | M4 | FLIGHT-001…003 |
| places | POI lookup/details | query / location / category | Place[] | `providers/places`, `domain/places` | M2 | PLACE-001…002 |
| routing | travel times | Place pairs, mode | RouteMatrix | `providers/routes` | M2 | ROUTE-001 |
| itinerary | feasibility, schedule, locking, partial regeneration | Trip + constraints + bookings + candidates + RouteMatrix | PlanVersion(ItineraryDay[]), Diff, Violations | `domain/itinerary`, `orchestration` | M3 | ITIN-001…003, AI-001…002 |
| recommendations (food, photo) | taste matching, restaurant ranking, photo spots | TasteProfile, Place context, RestaurantSignals | Recommendation[] (score, why, provenance), PhotoSpot[] | `domain/recommendations` | M5 | FOOD-001…003, PHOTO-001 |
| knowledge | before/at/after cards | Place, moment, language | KnowledgeCard[] (sources, generated_at) | `domain/knowledge`, `orchestration` | M5 | KNOW-001 |
| expenses (Budget) | costs, splits, transfers, FX, settlement | Expense / Transfer events, FX rates | TripCost, Settlement | `domain/expenses`, `providers/fx` | M6 | BUD-001…002 |
| during-trip | Today view + quick actions | current plan version, now, location (optional) | TodayView, regenerate request | `domain/today` | M7 | UI-003 |
| post-trip | recap (NICE) | plan + actuals | Recap | — | NICE | — |

## Shared contracts (CORE-001)
`Money`, `Provenance`, `TimeWindow`, `GeoPoint`, `Pace`, `MobilityNeeds`, `DietaryRestriction`, `ConstraintKind/Hardness`.
These live in `app/domain/shared/` and are the only cross-module imports allowed besides a module's public service interface.
