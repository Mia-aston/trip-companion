# Architecture

## High-level

```text
Next.js web
   |
FastAPI API
   |
   +-- Trip service
   +-- Flight search service -------- provider interface -> flight adapter(s)
   +-- Places service --------------- provider interface -> places adapter(s)
   +-- Itinerary engine
   +-- Recommendation engine
   |     +-- food taste matching
   |     +-- photo spots
   |     +-- knowledge cards
   +-- Expense/settlement service
   |
PostgreSQL + PostGIS (+ pgvector later)
```

## Rule: provider normalization

Every external API response must be translated into internal models before it enters planning logic. This lets providers be replaced without rewriting the product.

Example:

`Skyscanner/Duffel response -> FlightOption -> itinerary engine`

not:

`Skyscanner response -> itinerary engine`

## Rule: deterministic constraints before LLM

Hard constraints are calculated in code first:
- arrival/departure windows;
- opening hours;
- travel time;
- booking commitments;
- check-in/out;
- user mobility constraints;
- fixed must-dos.

The LLM receives feasible candidates and composes/explains a plan. It should not be asked to invent feasible hours from memory.

## Context isolation

Each domain should expose a small service interface and typed objects. A model working on one domain should be able to ignore vendor internals and unrelated domains.
