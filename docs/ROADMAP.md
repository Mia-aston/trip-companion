# Roadmap

## M0 — foundation
- monorepo, API skeleton, typed domain models;
- Postgres/PostGIS schema;
- provider interfaces + mocks;
- CI/tests.

## M1 — trip workspace
- create/edit trip;
- traveller preferences;
- manual bookings;
- editable itinerary.

## M2 — places + itinerary engine
- place search/detail adapter;
- candidate scoring;
- opening-hours and travel-time constraints;
- partial itinerary regeneration.

## M3 — flights
- flight provider adapter;
- normalized fare/segment/baggage model;
- select flight into trip constraints;
- external booking link only for MVP.

## M4 — recommendations
- taste profile;
- restaurant ranking;
- photo spots;
- knowledge cards: before/during/after.

## M5 — budget
- multi-currency expenses;
- payer/share split;
- transfers;
- settlement;
- actual vs estimate reconciliation.

## M6 — during-trip mode
- today timeline;
- nearby context-aware actions;
- disruption/replan of one block without regenerating the whole trip.
