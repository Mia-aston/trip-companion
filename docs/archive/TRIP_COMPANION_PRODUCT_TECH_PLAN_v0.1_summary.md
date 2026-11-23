# Trip Companion — Product & Technical Plan v0.1

**Status:** Documentation baseline before implementation  
**Date:** 23 Nov 2026  
**Primary stack:** Next.js + TypeScript; FastAPI + Python; PostgreSQL/PostGIS

## 1. Executive summary
Trip Companion is an AI-assisted travel workspace, not merely an itinerary generator. It should take dates, origin/destination or flexible preferences, search transport, build an editable itinerary, and enrich each stop with knowledge, food, photo and practical context. It must support partial regeneration when the user changes only part of a trip.

## 2. Product principles
- Plan from hard constraints first.
- LLM is a planner/ranker/explainer, not the source of live facts.
- Partial regeneration is the default.
- Explain why an itinerary or recommendation was chosen.
- Multi-currency expenses are native; transfers are not trip cost.
- Personalize food from explicit taste signals, never inferred race/ethnicity.
- Provider adapters isolate external APIs.
- User-visible volatile data carries provenance and freshness.

## 3. MVP
1. Create Trip + preferences.
2. Flight search + external booking link.
3. Place discovery + itinerary generation.
4. Editable itinerary with locked items and partial regeneration.
5. Place cards: Know / Eat / Photo / Practical.
6. Budget + split expenses + reimbursements + settlement.

### Non-goals for v1
- Direct ticketing/refunds.
- Social network.
- Race/ethnicity inference.
- Full accounting product.
- Microservices.

## 4. Core journey
### Before
Create trip → flight → accommodation → itinerary → lock bookings → prep → learn pack → budget.

### During
Today view with contextual actions: Know, Navigate, Eat, Photo, Practical.

### After
Reconcile actual spend, visited/skipped places, learning recap, trip summary, preference updates.

## 5. Core modules
- Trip Core
- Flights
- Places
- Routing
- Itinerary
- Knowledge
- Food taste engine
- Photo spots
- Budget/settlement
- During-trip
- Post-trip

## 6. Food recommendation rule
Do not classify reviewers as Asian/White/Black or infer race/ethnicity from names, photos or text. Build a `TasteProfile` from declared preferences and feedback. Extract non-sensitive review signals such as spice, sweetness, richness, texture, cuisine familiarity and authenticity claims.

## 7. Architecture
```text
Next.js Web
   ↓
FastAPI API
   ├── domain services
   ├── AI orchestration
   ├── provider adapters
   ↓
PostgreSQL + PostGIS
```
Start as a modular monolith.

## 8. Core entities
`users`, `taste_profiles`, `trips`, `trip_members`, `trip_constraints`, `transport_options`, `bookings`, `places`, `trip_places`, `itinerary_days`, `itinerary_items`, `knowledge_cards`, `photo_spots`, `restaurant_signals`, `expenses`, `expense_splits`, `transfers`, `plan_versions`, `provider_snapshots`.

## 9. Partial regeneration
1. Identify affected scope and dependencies.
2. Freeze confirmed bookings and locked items.
3. Remove only unlocked affected items.
4. Recompute candidate places/routes in available window.
5. Generate replacement plan.
6. Validate conflicts.
7. Persist a new plan version and diff.

## 10. Budget invariants
- Store original amount/currency.
- Converted values are derived.
- Payer is distinct from cost owner.
- Transfers/reimbursements are not trip cost.
- Settlement is recomputable from expenses + splits + transfers.

## 11. Suggested repo
```text
trip-companion/
  AGENTS.md
  README.md
  docs/
    PRODUCT.md
    ARCHITECTURE.md
    MODULES.md
    DECISIONS.md
    AI_HANDOFF.md
  apps/web/
  services/api/
    app/domain/
    app/providers/
    app/orchestration/
  packages/contracts/
  tests/
```

## 12. Roadmap
- M0 Documentation & contracts
- M1 Trip workspace
- M2 Places + routing
- M3 Itinerary engine
- M4 Flight search
- M5 Contextual recommendation
- M6 Budget & settlement
- M7 During-trip mode
- M8 Hardening

## 13. Golden scenario
Egypt trip: late Cairo arrival → Cairo/Giza → desert → Luxor → weather-sensitive balloon → remove Aswan → regenerate only 6 Nov as Luxor downtown while preserving hotel/flight/other days.

## 14. Definition of Done
- Issue + acceptance criteria exist.
- Contracts are current.
- Provider payloads do not leak beyond adapters.
- Tests cover happy/failure paths.
- AI output is schema-validated and post-validated.
- Freshness/provenance is handled.
- Privacy rules are respected.
- AI_HANDOFF is updated when project state changes.
- Egypt golden scenario continues to pass where relevant.

## 15. References
- Skyscanner Flights Live Prices: https://developers.skyscanner.net/docs/flights-live-prices/overview
- Google Places API (New): https://developers.google.com/maps/documentation/places/web-service/quick-reference
- Google Routes API: https://developers.google.com/maps/documentation/routes/quick-reference
- Duffel Offers: https://duffel.com/docs/api/offers
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
